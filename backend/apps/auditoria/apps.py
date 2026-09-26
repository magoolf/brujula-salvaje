from django.apps import AppConfig


class AuditoriaConfig(AppConfig):
    """Auditoría inmutable y revisiones de contenido (DATA-025, DATA-026, ADR-DB-004)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auditoria"
    label = "auditoria"
