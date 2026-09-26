from django.apps import AppConfig


class CatalogosConfig(AppConfig):
    """Catálogos: regiones, países, categorías de guía, licencias y escalas."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalogos"
    label = "catalogos"
