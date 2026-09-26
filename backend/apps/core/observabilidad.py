"""Logging JSON estructurado (structlog) y OpenTelemetry opcional.

Reglas (Skill_Backend §12.3, REQ-057, THREAT-020):
- Una línea JSON por evento en stdout, con `trace_id` de la petición.
- Nunca IP del cliente, cuerpos de petición, cookies, credenciales ni query strings.
- OpenTelemetry solo si OTEL_SDK_DISABLED=false; sus spans no llevan query string.
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog
from django.conf import settings
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
