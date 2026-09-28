"""Comando purgar_auditoria (infra/scheduler/crontab, scripts/ops/post-restore-local.sh)."""

from apps.ops.management.tarea import ComandoTarea


class Command(ComandoTarea):
    help = "Purga los eventos de auditoría con más de 365 días."
    nombre = "purgar_auditoria"
