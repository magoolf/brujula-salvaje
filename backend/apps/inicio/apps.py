from django.apps import AppConfig


class InicioConfig(AppConfig):
    """Configuración de inicio y del sitio y destacados (DATA-021, DATA-022, DATA-023)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inicio"
    label = "inicio"
