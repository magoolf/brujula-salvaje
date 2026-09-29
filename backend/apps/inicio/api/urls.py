"""Rutas /api/v1/panel/{tablero,inicio,configuracion} (contracts/openapi.yaml)."""

from __future__ import annotations

from django.urls import path

from apps.inicio.api import views

app_name = "inicio"

urlpatterns = [
    path("tablero", views.Tablero.as_view(), name="tablero"),
    path("inicio", views.ConfigInicioView.as_view(), name="inicio"),
    path("configuracion", views.ConfiguracionSitioView.as_view(), name="configuracion"),
]
