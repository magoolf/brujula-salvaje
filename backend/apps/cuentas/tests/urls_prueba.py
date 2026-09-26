"""URLconf solo para pruebas (NV-02): una vista DRF que provoca un IntegrityError con PII."""

from __future__ import annotations

from django.db import transaction
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contenido.tests.fabricas import crear_cuenta
from config.urls import handler400, handler403, handler404, handler500
from config.urls import urlpatterns as base

__all__ = ["handler400", "handler403", "handler404", "handler500", "urlpatterns"]

USUARIO_PII = "persona.real-nv02"


class VistaCuentaDuplicada(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        with transaction.atomic():
            crear_cuenta(USUARIO_PII)
            crear_cuenta(USUARIO_PII)  # UNIQUE(usuario) -> IntegrityError con el valor en DETAIL
        return Response({"ok": True})


urlpatterns = [*base, path("prueba/cuenta-duplicada", VistaCuentaDuplicada.as_view())]
