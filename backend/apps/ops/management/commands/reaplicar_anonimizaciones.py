"""Comando reaplicar_anonimizaciones (scripts/ops/post-restore-local.sh, ADR-DB-004 §4)."""

from argparse import ArgumentParser
from typing import Any

from apps.ops.management.tarea import ComandoTarea


class Command(ComandoTarea):
    help = "Reaplica el libro de anonimizaciones tras una restauración."
    nombre = "reaplicar_anonimizaciones"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--libro-vacio-confirmado",
            action="store_true",
            help=(
                "Instalación sin eventos: no falla con LIBRO_AUSENTE (decisión humana, "
                "ADR-DB-004 §4.4)."
            ),
        )

    def opciones_trabajo(self, options: dict[str, Any]) -> dict[str, Any]:
        return {"libro_vacio_confirmado": bool(options.get("libro_vacio_confirmado"))}
