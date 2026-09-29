"""Comando purgar_ops (infra/scheduler/crontab)."""

from apps.ops.management.tarea import ComandoTarea


class Command(ComandoTarea):
    help = "Purga ops_ejecucion_tarea > 30 días, idempotencia vencida y caché caducada."
    nombre = "purgar_ops"
