from django.apps import AppConfig


class ContenidoConfig(AppConfig):
    """Supertipo contenido, subtipos 1:1 y relaciones polimórficas (ADR-DB-002)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contenido"
    label = "contenido"
