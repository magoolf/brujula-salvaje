from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Infraestructura transversal (Skill_Backend Regla 10: no importa nada de otras apps)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"

    def ready(self) -> None:
        from apps.core.observabilidad import configurar_structlog

        configurar_structlog()
