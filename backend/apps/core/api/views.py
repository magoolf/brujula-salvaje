"""Vistas de core: salud (FEAT-048, AC-064) y manejadores de error de Django en RFC 9457."""

from __future__ import annotations

import structlog
from django.core.exceptions import RequestDataTooBig
from django.db import DatabaseError
from django.http import HttpRequest, JsonResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import selectors
from apps.core.api.serializers import EstadoSaludSerializer, ProblemSerializer
from apps.core.exceptions import ServicioNoDisponible
from apps.core.problemas import MEDIA_TYPE_PROBLEMA, respuesta_problema

logger = structlog.get_logger("brujula.salud")

_OK = {"status": "ok"}


class _VistaSalud(APIView):
    # Sin autenticación ni límite de tasa: la usan las sondas de Docker y del proxy.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []


class SaludLive(_VistaSalud):
    @extend_schema(
        operation_id="saludLive",
        summary="Proceso vivo",
        tags=["salud"],
        auth=[],
        responses={200: EstadoSaludSerializer},
    )
    def get(self, request: Request) -> Response:
        # Sin acceso a la base de datos: solo indica que el proceso responde.
        return Response(_OK)


class SaludReady(_VistaSalud):
    @extend_schema(
        operation_id="saludReady",
        summary="Dependencias alcanzables (BD y, si existe, broker)",
        tags=["salud"],
        auth=[],
        responses={
            200: EstadoSaludSerializer,
            (503, MEDIA_TYPE_PROBLEMA): OpenApiResponse(
                ProblemSerializer, description="503 servicio_no_disponible (THREAT-028)."
            ),
        },
    )
    def get(self, request: Request) -> Response:
        try:
            disponible = selectors.base_datos_disponible()
        except DatabaseError as exc:
            logger.warning("readiness_bd_no_disponible", tipo=type(exc).__name__)
            disponible = False
        if not disponible:
            raise ServicioNoDisponible()
        return Response(_OK)


# ---------------------------------------------------------------------------
# Manejadores de Django (rutas fuera de DRF): handler400/403/404/500 y CSRF_FAILURE_VIEW
# ---------------------------------------------------------------------------
def solicitud_invalida(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    if isinstance(exception, RequestDataTooBig):
        return respuesta_problema("carga_demasiado_grande")
    return respuesta_problema("validacion")


def permiso_denegado(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return respuesta_problema("permiso_denegado")


def no_encontrado(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return respuesta_problema("no_encontrado")


def error_servidor(request: HttpRequest) -> JsonResponse:
    return respuesta_problema("error_interno")


def csrf_fallido(request: HttpRequest, reason: str = "") -> JsonResponse:
    return respuesta_problema("csrf_invalido")
