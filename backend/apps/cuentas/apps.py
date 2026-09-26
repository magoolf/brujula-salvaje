from django.apps import AppConfig


class CuentasConfig(AppConfig):
    """Cuentas del staff, códigos de recuperación y sesiones del panel (DATA-024, STATE-004)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cuentas"
    label = "cuentas"
