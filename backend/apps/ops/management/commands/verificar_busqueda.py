"""Comando verificar_busqueda (infra/scheduler/crontab)."""

from apps.ops.management.tarea import ComandoTarea


class Command(ComandoTarea):
    help = "Comprueba que publicados en alcance = filas del índice de búsqueda."
    nombre = "verificar_busqueda"
