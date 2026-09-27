"""Ruta /api/v1/panel/auditoria (contracts/openapi.yaml)."""

from django.urls import path

from apps.auditoria.api.views import ListaAuditoria

app_name = "auditoria"

urlpatterns = [
    path("auditoria", ListaAuditoria.as_view(), name="auditoria"),
]
