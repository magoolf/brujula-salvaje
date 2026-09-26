"""Paginación por número de página (DEC-AUTO-104/105, Skill_Backend Regla 11).

- Parámetro `pagina` (base 1, máx. 10000); sin parámetro de tamaño (THREAT-009): cada vista fija
  `tamano_pagina` (24 público, 50 panel, 48 medios...).
- Página fuera de rango → 404 `pagina_fuera_de_rango`; `pagina` inválida → 400 `parametro_invalido`.
- Envoltorio: {total, pagina, tamano_pagina, total_paginas, siguiente, anterior, resultados},
  con enlaces relativos (uri-reference).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from django.core.paginator import Page, Paginator
from rest_framework.pagination import BasePagination
from rest_framework.response import Response

from apps.core.exceptions import PaginaFueraDeRango, ParametroInvalido

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

PARAMETRO_PAGINA = "pagina"
PAGINA_MAXIMA = 10000
TAMANO_POR_DEFECTO = 24


class PaginacionNumerada(BasePagination):
    def __init__(self) -> None:
        self.pagina: Page[Any] | None = None
        self.request: Request | None = None
        self.tamano = TAMANO_POR_DEFECTO

    def paginate_queryset(
        self, queryset: Any, request: Request, view: APIView | None = None
    ) -> list[Any]:
        self.request = request
        self.tamano = int(getattr(view, "tamano_pagina", TAMANO_POR_DEFECTO))
        numero = _numero_pagina(request.query_params.get(PARAMETRO_PAGINA))
        paginador: Paginator[Any] = Paginator(queryset, self.tamano)
        if numero > paginador.num_pages:
            raise PaginaFueraDeRango()
        self.pagina = paginador.page(numero)
        return list(self.pagina.object_list)

    def _enlace(self, numero: int) -> str:
        if self.request is None:
            raise RuntimeError("paginate_queryset no se ha ejecutado")
        parametros = {k: v for k, v in self.request.query_params.items() if k != PARAMETRO_PAGINA}
        parametros[PARAMETRO_PAGINA] = str(numero)
        return f"{self.request.path}?{urlencode(parametros)}"

    def get_paginated_response(self, data: Sequence[Any]) -> Response:
        if self.pagina is None:
            raise RuntimeError("paginate_queryset no se ha ejecutado")
        pagina = self.pagina
        return Response(
            {
                "total": pagina.paginator.count,
                "pagina": pagina.number,
                "tamano_pagina": self.tamano,
                "total_paginas": pagina.paginator.num_pages if pagina.paginator.count else 0,
                "siguiente": self._enlace(pagina.next_page_number()) if pagina.has_next() else None,
                "anterior": (
                    self._enlace(pagina.previous_page_number()) if pagina.has_previous() else None
                ),
                "resultados": list(data),
            }
        )

    def get_paginated_response_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        enlace = {"type": ["string", "null"], "format": "uri-reference"}
        return {
            "type": "object",
            "required": [
                "total",
                "pagina",
                "tamano_pagina",
                "total_paginas",
                "siguiente",
                "anterior",
                "resultados",
            ],
            "properties": {
                "total": {"type": "integer", "minimum": 0},
                "pagina": {"type": "integer", "minimum": 1},
                "tamano_pagina": {"type": "integer", "minimum": 1},
                "total_paginas": {"type": "integer", "minimum": 0},
                "siguiente": enlace,
                "anterior": enlace,
                "resultados": schema,
            },
        }


def _numero_pagina(valor: str | None) -> int:
    if valor is None:
        return 1
    if valor.isdigit() and 1 <= int(valor) <= PAGINA_MAXIMA:
        return int(valor)
    raise ParametroInvalido(
        errors={PARAMETRO_PAGINA: [f"Debe ser un entero entre 1 y {PAGINA_MAXIMA}."]}
    )
