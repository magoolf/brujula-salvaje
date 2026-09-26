"""Middleware transversal: traza W3C, cabeceras de seguridad de la API y log de peticiones."""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable

import structlog
from django.conf import settings
from django.http import HttpRequest, HttpResponseBase

from apps.core.trazas import (
    extraer_trace_id,
    fijar_trace_id,
    nuevo_trace_id,
    restaurar_trace_id,
    trace_id_otel,
)

Siguiente = Callable[[HttpRequest], HttpResponseBase]

logger = structlog.get_logger("brujula.peticiones")

CABECERA_TRAZA = "X-Trace-Id"
_PREFIJO_PANEL = "/api/v1/panel/"
_PREFIJO_SALUD = "/health/"


class TrazaMiddleware:
    """Fija el trace_id de la petición (traceparent W3C) y lo devuelve en X-Trace-Id."""

    def __init__(self, get_response: Siguiente) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        trace_id = (
            trace_id_otel()
            or extraer_trace_id(request.headers.get("traceparent"))
            or nuevo_trace_id()
        )
        token = fijar_trace_id(trace_id)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        try:
            response = self.get_response(request)
        finally:
            structlog.contextvars.clear_contextvars()
            restaurar_trace_id(token)
        response[CABECERA_TRAZA] = trace_id
        return response


class CabecerasSeguridadMiddleware:
    """Cabeceras globales del contrato (THREAT-014/015, AC-119) que Django no pone por sí solo."""

    def __init__(self, get_response: Siguiente) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", settings.API_CONTENT_SECURITY_POLICY)
        response.headers.setdefault("Permissions-Policy", settings.API_PERMISSIONS_POLICY)
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.path.startswith(_PREFIJO_PANEL):
            response["Cache-Control"] = "no-store"
            response["X-Robots-Tag"] = "noindex, nofollow"
        elif request.path.startswith(_PREFIJO_SALUD):
            response["Cache-Control"] = "no-store"
        return response


def seudonimo_usuario(request: HttpRequest) -> str | None:
    """user_id seudonimizado (HMAC) de la cuenta autenticada; None si es anónima."""
    usuario = getattr(request, "user", None)
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        return None
    clave = settings.THROTTLE_HMAC_KEY.encode()
    return hmac.new(clave, f"log|{usuario.pk}".encode(), hashlib.sha256).hexdigest()[:16]


class RegistroPeticionMiddleware:
    """Una línea JSON por petición: trace_id, método, ruta (patrón, sin query), estado y duración.

    No registra la IP, la query string, cabeceras ni cuerpos (REQ-057, THREAT-020).
    """

    def __init__(self, get_response: Siguiente) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        inicio = time.perf_counter()
        response = self.get_response(request)
        duracion_ms = round((time.perf_counter() - inicio) * 1000, 1)
        coincidencia = request.resolver_match
        endpoint = f"/{coincidencia.route}" if coincidencia is not None else "<no_resuelta>"
        estado = response.status_code
        nivel = "error" if estado >= 500 else "warning" if estado >= 400 else "info"
        getattr(logger, nivel)(
            "peticion",
            metodo=request.method,
            endpoint=endpoint,
            status=estado,
            duration_ms=duracion_ms,
            user_id=seudonimo_usuario(request),
        )
        return response
