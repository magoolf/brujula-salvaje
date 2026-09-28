"""Comando reindexar_busqueda (infra/scheduler/crontab)."""

from apps.ops.management.tarea import ComandoTarea


class Command(ComandoTarea):
    help = "Reconstruye el índice de búsqueda (DELETE + INSERT, idempotente)."
    nombre = "reindexar_busqueda"
