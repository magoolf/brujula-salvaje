from django.apps import AppConfig


class MediosConfig(AppConfig):
    """Medios (imágenes saneadas) y sus derivados (DATA-016)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.medios"
    label = "medios"
