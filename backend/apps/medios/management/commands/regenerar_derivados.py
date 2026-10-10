"""Comando `regenerar_derivados` (TKT-048).

Vuelve a codificar los derivados responsivos de los medios existentes con los parámetros actuales
de `apps.medios.services.PARAMETROS_CODIFICACION` (los derivados creados antes de TKT-048 usan los
valores por defecto de Pillow y su AVIF suele pesar más que el WebP). Usa el servicio real
`regenerar_derivados`, que trabaja desde el original saneado, conserva las rutas (las URL
publicadas no cambian) y es idempotente: ejecutarlo dos veces seguidas no reescribe nada la
segunda vez.

    python manage.py regenerar_derivados              # todos los medios
    python manage.py regenerar_derivados --medio 12 --medio 15
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.core.exceptions import NoEncontrado
from apps.medios import services
from apps.medios.models import Medio


class Command(BaseCommand):
    help = "Regenera los derivados de imagen con los parámetros de codificación actuales (TKT-048)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--medio",
            action="append",
            type=int,
            default=None,
            help="Id del medio a regenerar (repetible). Sin él, todos los medios.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        ids: list[int] = options["medio"] or list(
            Medio.objects.order_by("pk").values_list("pk", flat=True)
        )
        total = services.ResultadoRegeneracion()
        omitidos = 0
        for medio_id in ids:
            try:
                resultado = services.regenerar_derivados(medio_id)
            except NoEncontrado as exc:
                raise CommandError(f"No existe el medio {medio_id}.") from exc
            omitidos += resultado.omitido
            total.creados += resultado.creados
            total.actualizados += resultado.actualizados
            total.sin_cambios += resultado.sin_cambios
            total.eliminados += resultado.eliminados
        self.stdout.write(
            f"Medios: {len(ids)} (omitidos sin original: {omitidos}). Derivados creados: "
            f"{total.creados}, actualizados: {total.actualizados}, sin cambios: "
            f"{total.sin_cambios}, eliminados por peso: {total.eliminados}."
        )
