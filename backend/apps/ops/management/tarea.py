"""Base de los comandos del planificador (infra/scheduler/crontab, DEVOPS_HANDOFF §6)."""

from __future__ import annotations

from typing import Any, ClassVar

from django.core.management.base import BaseCommand, CommandError

from apps.ops import services


class ComandoTarea(BaseCommand):
    """Ejecuta el trabajo `nombre` de apps.ops.services con lock consultivo y registro.

    Códigos de salida: 0 si termina con éxito o si otro proceso tiene el lock; 1 si falla
    (queda registrada como FALLO en ops_ejecucion_tarea).
    """

    nombre: ClassVar[str] = ""

    def handle(self, *args: Any, **options: Any) -> None:
        tarea, trabajo = services.TRABAJOS[self.nombre]
        try:
            ejecucion = services.ejecutar(tarea, trabajo)
        except services.TareaFallida as exc:
            raise CommandError(f"{self.nombre}: {exc}") from None
        except Exception as exc:
            # OBS-06: el detalle ya quedó en el log JSON (tarea_fallida, sin mensajes de la BD) y
            # en ops_ejecucion_tarea; stderr solo lleva el tipo, sin traceback ni datos.
            raise CommandError(f"{self.nombre}: error inesperado ({type(exc).__name__})") from None
        if not ejecucion.ejecutada:
            self.stdout.write(f"{self.nombre}: otro proceso tiene el lock; no se hace nada.")
            return
        registro = ejecucion.registro
        detalle = registro.detalle if registro is not None else ""
        self.stdout.write(f"{self.nombre}: EXITO ({detalle})")
