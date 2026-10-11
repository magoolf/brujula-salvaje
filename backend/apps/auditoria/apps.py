from django.apps import AppConfig


class AuditoriaConfig(AppConfig):
    """Auditoría inmutable y revisiones de contenido (DATA-025, DATA-026, ADR-DB-004)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auditoria"
    label = "auditoria"

    def ready(self) -> None:
        # TKT-067: una petición HTTP nunca hereda la etiqueta de proceso (`auditar_como_sistema`).
        from django.core.signals import request_finished, request_started

        from apps.auditoria import contexto

        request_started.connect(contexto.al_iniciar_peticion, dispatch_uid="auditoria.contexto.ini")
        request_finished.connect(
            contexto.al_terminar_peticion, dispatch_uid="auditoria.contexto.fin"
        )
