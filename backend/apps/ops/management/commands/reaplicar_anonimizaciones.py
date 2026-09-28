"""Comando reaplicar_anonimizaciones (scripts/ops/post-restore-local.sh, ADR-DB-004 §4)."""

from apps.ops.management.tarea import ComandoTarea


class Command(ComandoTarea):
    help = "Reaplica el libro de anonimizaciones tras una restauración."
    nombre = "reaplicar_anonimizaciones"
