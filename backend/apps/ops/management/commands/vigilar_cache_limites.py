"""Comando vigilar_cache_limites (infra/scheduler/crontab, DEVOPS_HANDOFF §19.3.6)."""

from apps.ops.management.tarea import ComandoTarea


class Command(ComandoTarea):
    help = "Alerta si app.cache_limites supera el umbral de filas o de tamaño en disco."
    nombre = "vigilar_cache_limites"
