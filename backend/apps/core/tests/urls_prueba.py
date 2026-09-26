"""URLconf solo para pruebas: vistas que provocan cada tipo de error."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, RequestDataTooBig, SuspiciousOperation
from django.http import Http404, HttpRequest, HttpResponse
from django.urls import path
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import ErrorApi
from apps.core.throttling import LimitePorAmbito
from config.urls import handler400, handler403, handler404, handler500
from config.urls import urlpatterns as base

__all__ = ["handler400", "handler403", "handler404", "handler500", "urlpatterns"]


class DiaSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=5)


class EntradaSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    dias = DiaSerializer(many=True)

    def validate(self, attrs):
        if attrs.get("nombre") == "prohibido":
            raise serializers.ValidationError("Nombre no permitido.")
        return attrs


class _Abierta(APIView):
    permission_classes = [AllowAny]


class VistaValidacion(_Abierta):
    def post(self, request: Request) -> Response:
        EntradaSerializer(data=request.data).is_valid(raise_exception=True)
        return Response({"ok": True})


class VistaSoloGet(_Abierta):
    def get(self, request: Request) -> Response:
        return Response({"ok": True})


class VistaFalloDrf(_Abierta):
    def get(self, request: Request) -> Response:
        raise RuntimeError("fallo forzado con dato-sensible")


class VistaNoEncontradoDjango(_Abierta):
    def get(self, request: Request) -> Response:
        raise Http404


class VistaPermisoDjango(_Abierta):
    def get(self, request: Request) -> Response:
        raise PermissionDenied


class VistaCargaGrande(_Abierta):
    def get(self, request: Request) -> Response:
        raise RequestDataTooBig


class VistaErrorApi(_Abierta):
    def get(self, request: Request) -> Response:
        raise ErrorApi(
            codigo="conflicto_version",
            cabeceras={"X-Prueba": "1"},
            extra={"usos": [], "code": "no_debe_pisar"},
        )


class VistaDenegadaPorDefecto(APIView):
    def get(self, request: Request) -> Response:
        return Response({"ok": True})


class LimitePrueba(LimitePorAmbito):
    THROTTLE_RATES = {"prueba": "2/min"}


class VistaLimitada(_Abierta):
    throttle_scope = "prueba"
    throttle_classes = [LimitePrueba]

    def get(self, request: Request) -> Response:
        return Response({"ok": True})


class VistaPaginada(GenericAPIView):
    permission_classes = [AllowAny]
    tamano_pagina = 24

    def get(self, request: Request) -> Response:
        pagina = self.paginate_queryset(list(range(30)))
        return self.get_paginated_response(pagina)


def vista_django_falla(request: HttpRequest) -> HttpResponse:
    raise RuntimeError("fallo forzado fuera de DRF")


def vista_django_prohibida(request: HttpRequest) -> HttpResponse:
    raise PermissionDenied


def vista_django_sospechosa(request: HttpRequest) -> HttpResponse:
    raise SuspiciousOperation("x")


def vista_django_grande(request: HttpRequest) -> HttpResponse:
    raise RequestDataTooBig("x")


@csrf_protect
def vista_django_csrf(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok")


urlpatterns = [
    *base,
    path("prueba/validacion", VistaValidacion.as_view()),
    path("prueba/solo-get", VistaSoloGet.as_view()),
    path("prueba/fallo-drf", VistaFalloDrf.as_view()),
    path("prueba/no-encontrado", VistaNoEncontradoDjango.as_view()),
    path("prueba/permiso", VistaPermisoDjango.as_view()),
    path("prueba/carga-grande", VistaCargaGrande.as_view()),
    path("prueba/error-api", VistaErrorApi.as_view()),
    path("prueba/denegada", VistaDenegadaPorDefecto.as_view()),
    path("prueba/limitada", VistaLimitada.as_view()),
    path("prueba/paginada", VistaPaginada.as_view()),
    path("prueba/django-falla", vista_django_falla),
    path("prueba/django-prohibida", vista_django_prohibida),
    path("prueba/django-sospechosa", vista_django_sospechosa),
    path("prueba/django-grande", vista_django_grande),
    path("prueba/django-csrf", vista_django_csrf),
]
