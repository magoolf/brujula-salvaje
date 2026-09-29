"""Rutas /api/v1/panel/medios/** (contracts/openapi.yaml, tag panel-medios)."""

from __future__ import annotations

from django.urls import path

from apps.medios.api import views

app_name = "medios"

urlpatterns = [
    path("medios", views.ListaMedios.as_view(), name="medios"),
    path("medios/<int:id>", views.DetalleMedio.as_view(), name="medio"),
    path("medios/<int:id>/archivo", views.ArchivoMedio.as_view(), name="medio-archivo"),
    path("medios/<int:id>/usos", views.UsosMedio.as_view(), name="medio-usos"),
    path("medios/<int:id>/retirar", views.RetirarMedio.as_view(), name="medio-retirar"),
    path("medios/<int:id>/reactivar", views.ReactivarMedio.as_view(), name="medio-reactivar"),
]
