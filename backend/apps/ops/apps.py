from django.apps import AppConfig


class OpsConfig(AppConfig):
    """Operación: tareas, idempotencia, caché de límites y vista de usos de medios (ADR-DB-005)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ops"
    label = "ops"
