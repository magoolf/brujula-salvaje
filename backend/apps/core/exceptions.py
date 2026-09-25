"""Excepciones de negocio y manejador DRF que responde RFC 9457 (Skill_Backend §6 y §12.1).

Toda excepción controlada hereda de `ErrorApi`. Las excepciones de DRF y de Django se traducen
al catálogo cerrado de `code`. Cualquier otra excepción se registra (con trace_id y traza) y se
responde como 500 `error_interno` sin detalles técnicos (ALT-025, THREAT-028).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import structlog
from django.core.exceptions import PermissionDenied as PermisoDjango
from django.core.exceptions import RequestDataTooBig
from django.http import Http404
from rest_framework import exceptions as drf
from rest_framework.response import Response
from rest_framework.settings import api_settings

from apps.core.problemas import CATALOGO, MEDIA_TYPE_PROBLEMA, cuerpo_problema

logger = structlog.get_logger("brujula.errores")

_CLAVE_GENERAL = "_general"


class ErrorApi(drf.APIException):
    """Base de las excepciones controladas. `codigo` pertenece a problemas.CATALOGO."""

    codigo = "error_interno"

    def __init__(
        self,
        detalle: str | None = None,
        *,
        codigo: str | None = None,
        errors: dict[str, list[str]] | None = None,
        cabeceras: Mapping[str, str] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        self.codigo = codigo or self.codigo
        if self.codigo not in CATALOGO:
            raise ValueError(f"code fuera del catálogo: {self.codigo}")
        estado, _titulo, detalle_defecto = CATALOGO[self.codigo]
        self.status_code = estado
        self.detalle = detalle
        self.errors = errors or {}
        self.cabeceras = dict(cabeceras or {})
        self.extra = dict(extra or {})
        super().__init__(detail=detalle or detalle_defecto, code=self.codigo)


class ParametroInvalido(ErrorApi):
    codigo = "parametro_invalido"


class NoEncontrado(ErrorApi):
    codigo = "no_encontrado"


class PaginaFueraDeRango(ErrorApi):
    codigo = "pagina_fuera_de_rango"


class ServicioNoDisponible(ErrorApi):
    codigo = "servicio_no_disponible"


# Traducción de excepciones de DRF (se busca por herencia, en orden).
_TRADUCCION_DRF: tuple[tuple[type[drf.APIException], str], ...] = (
    (drf.ValidationError, "validacion"),
    (drf.ParseError, "validacion"),
    (drf.NotAuthenticated, "no_autenticado"),
    (drf.AuthenticationFailed, "no_autenticado"),
    (drf.PermissionDenied, "permiso_denegado"),
    (drf.NotFound, "no_encontrado"),
    (drf.MethodNotAllowed, "metodo_no_permitido"),
    (drf.UnsupportedMediaType, "tipo_medio_no_soportado"),
    (drf.Throttled, "limite_tasa"),
)


def normalizar_errores(detalle: Any, prefijo: str = "") -> dict[str, list[str]]:
    """Convierte el `detail` de DRF en {campo: [mensajes]} con notación de puntos.

    Los errores no asociados a un campo van en `_general` (contrato, Problem.errors).
    """
    resultado: dict[str, list[str]] = {}

    def agregar(clave: str, mensaje: Any) -> None:
        resultado.setdefault(clave or _CLAVE_GENERAL, []).append(str(mensaje))

    def fusionar(otro: dict[str, list[str]]) -> None:
        for clave, mensajes in otro.items():
            resultado.setdefault(clave, []).extend(mensajes)

    if isinstance(detalle, Mapping):
        for clave, valor in detalle.items():
            es_general = str(clave) in (api_settings.NON_FIELD_ERRORS_KEY, _CLAVE_GENERAL)
            if es_general and not prefijo:
                subclave = _CLAVE_GENERAL
            elif es_general:
                subclave = prefijo
            else:
                subclave = f"{prefijo}.{clave}" if prefijo else str(clave)
            fusionar(normalizar_errores(valor, subclave))
    elif isinstance(detalle, list | tuple):
        for indice, elemento in enumerate(detalle):
            if isinstance(elemento, Mapping | list | tuple):
                subclave = f"{prefijo}.{indice}" if prefijo else str(indice)
                fusionar(normalizar_errores(elemento, subclave))
            else:
                agregar(prefijo, elemento)
    else:
        agregar(prefijo, detalle)
    return resultado


def _respuesta(
    codigo: str,
    *,
    detalle: str | None = None,
    errors: dict[str, list[str]] | None = None,
    cabeceras: Mapping[str, str] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Response:
    cuerpo = cuerpo_problema(codigo, detalle=detalle, errors=errors, extra=dict(extra or {}))
    return Response(
        cuerpo,
        status=cuerpo["status"],
        headers=dict(cabeceras or {}),
        content_type=MEDIA_TYPE_PROBLEMA,
    )


def _codigo_drf(exc: drf.APIException) -> str:
    for clase, codigo in _TRADUCCION_DRF:
        if isinstance(exc, clase):
            return codigo
    for codigo, (estado, _titulo, _detalle) in CATALOGO.items():
        if estado == exc.status_code:
            return codigo
    return "error_interno"


def manejador_excepciones(exc: Exception, context: Mapping[str, Any]) -> Response:
    """EXCEPTION_HANDLER de DRF: toda respuesta de error es application/problem+json."""
    # Igual que el manejador por defecto de DRF: marca para rollback las transacciones atómicas.
    # Import diferido: rest_framework.views importa los settings de DRF (evita ciclos).
    from rest_framework.views import set_rollback

    set_rollback()
    if isinstance(exc, Http404):
        exc = NoEncontrado()
    elif isinstance(exc, PermisoDjango):
        exc = ErrorApi(codigo="permiso_denegado")
    elif isinstance(exc, RequestDataTooBig):
        exc = ErrorApi(codigo="carga_demasiado_grande")

    if isinstance(exc, ErrorApi):
        return _respuesta(
            exc.codigo,
            detalle=exc.detalle,
            errors=exc.errors,
            cabeceras=exc.cabeceras,
            extra=exc.extra,
        )

    if isinstance(exc, drf.APIException):
        codigo = _codigo_drf(exc)
        cabeceras: dict[str, str] = {}
        errors: dict[str, list[str]] | None = None
        if isinstance(exc, drf.ValidationError):
            errors = normalizar_errores(exc.detail)
        espera = getattr(exc, "wait", None) if isinstance(exc, drf.Throttled) else None
        if espera is not None:
            cabeceras["Retry-After"] = str(max(1, math.ceil(espera)))
        return _respuesta(codigo, errors=errors, cabeceras=cabeceras)

    vista = context.get("view")
    logger.error(
        "excepcion_no_controlada",
        vista=type(vista).__name__ if vista is not None else None,
        tipo=type(exc).__name__,
        exc_info=exc,
    )
    return _respuesta("error_interno")
