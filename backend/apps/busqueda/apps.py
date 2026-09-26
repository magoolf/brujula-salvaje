from django.apps import AppConfig


class BusquedaConfig(AppConfig):
    """Extensiones, funciones de normalización y documento de búsqueda (ADR-DB-003)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.busqueda"
    label = "busqueda"
