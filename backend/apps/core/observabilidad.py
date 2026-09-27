"""Logging JSON estructurado (structlog) y OpenTelemetry opcional.

Reglas (Skill_Backend §12.3, REQ-057, THREAT-020):
- Una línea JSON por evento en stdout, con `trace_id` de la petición.
- Nunca IP del cliente, cuerpos de petición, cookies, credenciales ni query strings.
- Los errores de BD (psycopg/Django) nunca llevan su mensaje al log: puede contener valores de
  las filas en el DETAIL de PostgreSQL (NV-02). Se registra tipo, SQLSTATE y constraint.
- OpenTelemetry solo si OTEL_SDK_DISABLED=false; sus spans no llevan query string.
"""

from __future__ import annotations

import logging
import sys
import traceback
from collections.abc import MutableMapping
from typing import Any

import psycopg
import structlog
from django.conf import settings
from django.db import Error as ErrorBdDjango
from django.http import HttpRequest

# Claves que nunca deben salir en un log, vengan de donde vengan.
CLAVES_PROHIBIDAS = frozenset(
    {
        "ip",
        "remote_addr",
        "client_ip",
        "x_forwarded_for",
        "request",
        "query",
        "query_string",
        "q",
        "password",
        "contrasena",
        "token",
        "cookie",
        "cookies",
        "authorization",
        "body",
        "cuerpo",
    }
)


def eliminar_claves_sensibles(
    _logger: Any, _metodo: str, evento: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for clave in list(evento):
        if clave.lower() in CLAVES_PROHIBIDAS:
            del evento[clave]
    return evento


# ---------------------------------------------------------------------------
# NV-02: los errores de la base de datos llevan en su mensaje el DETAIL de PostgreSQL, que
# puede contener valores de las filas (p. ej. "Key (usuario)=(...) already exists"). En los
# logs se sustituye ese mensaje por el tipo, el SQLSTATE y el nombre de la constraint.
# ---------------------------------------------------------------------------
_MAXIMO_CADENA = 16


def _excepcion_de(exc_info: Any) -> BaseException | None:
    if isinstance(exc_info, BaseException):
        return exc_info
    if isinstance(exc_info, tuple) and len(exc_info) == 3:
        return exc_info[1] if isinstance(exc_info[1], BaseException) else None
    if exc_info is True:
        return sys.exc_info()[1]
    return None


def _cadena(exc: BaseException) -> list[BaseException]:
    """Excepción y sus causas/contextos, de la más antigua a la más reciente."""
    cadena: list[BaseException] = []
    actual: BaseException | None = exc
    while actual is not None and actual not in cadena and len(cadena) < _MAXIMO_CADENA:
        cadena.append(actual)
        actual = actual.__cause__ or (None if actual.__suppress_context__ else actual.__context__)
    return list(reversed(cadena))


def _es_error_bd(exc: BaseException) -> bool:
    return isinstance(exc, (ErrorBdDjango, psycopg.Error))


def _mensaje_seguro(exc: BaseException) -> str:
    """Mensaje de un error de BD sin valores: SQLSTATE y constraint (nombres de esquema)."""
    origen = exc if isinstance(exc, psycopg.Error) else exc.__cause__
    if isinstance(origen, psycopg.Error):
        sqlstate = origen.sqlstate or "desconocido"
        constraint = origen.diag.constraint_name
        sufijo = f", constraint {constraint}" if constraint else ""
        return f"[detalle omitido: sqlstate {sqlstate}{sufijo}]"
    return "[detalle omitido]"


def traza_sin_datos_bd(exc: BaseException) -> str:
    """Traza de la excepción en la que los mensajes de los errores de BD van saneados."""
    partes: list[str] = []
    for indice, elemento in enumerate(_cadena(exc)):
        if indice:
            partes.append("\nLa excepción anterior provocó la siguiente:\n\n")
        partes.append("Traceback (most recent call last):\n")
        partes.extend(traceback.format_tb(elemento.__traceback__))
        tipo = type(elemento)
        nombre = f"{tipo.__module__}.{tipo.__qualname__}"
        mensaje = _mensaje_seguro(elemento) if _es_error_bd(elemento) else str(elemento)
        partes.append(f"{nombre}: {mensaje}\n")
    return "".join(partes)


def sanear_excepciones_bd(
    _logger: Any, _metodo: str, evento: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Sustituye exc_info por una traza saneada si la cadena contiene un error de BD."""
    exc = _excepcion_de(evento.get("exc_info"))
    if exc is None or not any(_es_error_bd(e) for e in _cadena(exc)):
        return evento
    evento.pop("exc_info", None)
    evento["exception"] = traza_sin_datos_bd(exc)
    return evento


def _procesadores_comunes() -> list[Any]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        eliminar_claves_sensibles,
    ]


def configurar_structlog() -> None:
    structlog.configure(
        processors=[
            *_procesadores_comunes(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def formateador_json() -> logging.Formatter:
    """Formatter de logging.dictConfig (settings.LOGGING) que emite JSON."""
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_procesadores_comunes(),
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            sanear_excepciones_bd,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )


# ---------------------------------------------------------------------------
# OpenTelemetry
# ---------------------------------------------------------------------------
_ATRIBUTOS_URL = ("http.url", "url.full", "http.target")


def _sin_query(span: Any, request: HttpRequest) -> None:
    """request_hook de DjangoInstrumentor: sustituye las URL del span por la ruta sin query."""
    if not span or not span.is_recording():
        return
    for atributo in _ATRIBUTOS_URL:
        span.set_attribute(atributo, request.path)
    span.set_attribute("url.query", "")


def configurar_otel() -> bool:
    """Instrumenta Django y psycopg si OTEL_SDK_DISABLED=false. Devuelve si quedó activo."""
    if settings.OTEL_SDK_DISABLED:
        return False

    from opentelemetry import trace
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    proveedor = TracerProvider(
        resource=Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
    )
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        proveedor.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(proveedor)
    DjangoInstrumentor().instrument(request_hook=_sin_query)
    PsycopgInstrumentor().instrument(enable_commenter=False)
    return True
