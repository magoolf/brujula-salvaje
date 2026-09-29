"""Comando purgar_sesiones (infra/scheduler/crontab)."""

from apps.ops.management.tarea import ComandoTarea


class Command(ComandoTarea):
    help = "Elimina las sesiones del panel expiradas."
    nombre = "purgar_sesiones"
