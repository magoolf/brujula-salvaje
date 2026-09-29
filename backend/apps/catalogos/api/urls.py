"""Rutas /api/v1/panel/taxonomias/** (contracts/openapi.yaml, tag panel-configuracion)."""

from __future__ import annotations

from django.urls import path

from apps.catalogos.api import views

app_name = "catalogos"

urlpatterns = [
    path("taxonomias/regiones", views.ListaRegiones.as_view(), name="regiones"),
    path("taxonomias/regiones/<int:id>", views.DetalleRegion.as_view(), name="region"),
    path("taxonomias/paises", views.ListaPaises.as_view(), name="paises"),
    path("taxonomias/paises/<int:id>", views.DetallePais.as_view(), name="pais"),
    path("taxonomias/categorias-guia", views.ListaCategoriasGuia.as_view(), name="categorias-guia"),
    path(
        "taxonomias/categorias-guia/<int:id>",
        views.DetalleCategoriaGuia.as_view(),
        name="categoria-guia",
    ),
    path("taxonomias/licencias", views.ListaLicencias.as_view(), name="licencias"),
    path("taxonomias/licencias/<int:id>", views.DetalleLicencia.as_view(), name="licencia"),
    path("taxonomias/escalas", views.Escalas.as_view(), name="escalas"),
    path("taxonomias/escalas/<int:id>", views.ActualizarNivelEscala.as_view(), name="escala"),
]
