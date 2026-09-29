"""Consultas de búsqueda pública (AP-10, RULE-018, ADR-DB-003 §3, DEC-AUTO-048).

- tsquery por prefijo construida en la BD con app.f_tsquery_prefijo: solo tokens alfanuméricos
  normalizados, sin sintaxis del usuario (THREAT-008); todo va parametrizado.
- Ranking ts_rank_cd(documento, tsq, 32); agrupación por tipo con row_number(); respaldo difuso
  por trigramas sobre titulo_norm si la búsqueda de texto no devuelve nada.
- statement_timeout de 2 s en la transacción de búsqueda (THREAT-009).
- El texto buscado nunca se registra en los logs (THREAT-020, AC-116): no se pasa a ningún logger.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from django.db import connection, transaction

from apps.busqueda.models import TIPOS_BUSCABLES, BusquedaDocumento
from apps.contenido import selectors as contenido_selectors
from apps.contenido.models import TipoContenido
from apps.medios.selectors import prefetch_imagen

T = TipoContenido
GRUPOS: dict[str, str] = {
    "destinos": T.DESTINO,
    "itinerarios": T.ITINERARIO,
    "guias": T.GUIA,
    "tipos": T.TIPO,
}
MAX_POR_GRUPO = 10
MAX_COINCIDENCIAS = 5000  # por grupo (OBS-05): un tipo no deja sin resultados a otro
TIMEOUT_BUSQUEDA = "2s"
UMBRAL_SIMILITUD = "0.3"

_FTS = """
WITH consulta AS (SELECT app.f_tsquery_prefijo(%(q)s) AS tsq),
coincidencias AS (
  SELECT d.contenido_id, d.tipo_contenido, d.titulo_norm,
         ts_rank_cd(d.documento, consulta.tsq, 32) AS rango
    FROM busqueda_documento d, consulta
   WHERE consulta.tsq IS NOT NULL AND d.documento @@ consulta.tsq
     AND (%(tipo)s::text IS NULL OR d.tipo_contenido = %(tipo)s::text)
)
SELECT contenido_id, tipo_contenido, posicion, total FROM (
  SELECT contenido_id, tipo_contenido,
         row_number() OVER (PARTITION BY tipo_contenido
                            ORDER BY rango DESC, titulo_norm, contenido_id) AS posicion,
         count(*) OVER (PARTITION BY tipo_contenido) AS total
    FROM coincidencias
) AS agrupadas
 WHERE posicion <= %(limite)s
 ORDER BY tipo_contenido, posicion
"""

_DIFUSA = """
SELECT contenido_id, tipo_contenido, posicion, total FROM (
  SELECT contenido_id, tipo_contenido,
         row_number() OVER (PARTITION BY tipo_contenido
                            ORDER BY ext.similarity(titulo_norm, app.f_normalizar(%(q)s)) DESC,
                                     titulo_norm, contenido_id) AS posicion,
         count(*) OVER (PARTITION BY tipo_contenido) AS total
    FROM busqueda_documento
   WHERE titulo_norm OPERATOR(ext.%%) app.f_normalizar(%(q)s)
     AND (%(tipo)s::text IS NULL OR tipo_contenido = %(tipo)s::text)
) AS agrupadas
 WHERE posicion <= %(limite)s
 ORDER BY tipo_contenido, posicion
"""


@dataclass
class ResultadoBusqueda:
    tipo: str
    slug: str
    titulo: str
    resumen: str | None
    pais: str | None
    portada: Any


def _coincidencias(texto: str, tipo: str | None) -> list[tuple[int, str, int, int]]:
    parametros = {"q": texto, "tipo": tipo, "limite": MAX_COINCIDENCIAS}
    with transaction.atomic(), connection.cursor() as cursor:
        # SET LOCAL acotado a esta consulta: se restaura el valor previo al terminar, también si
        # la búsqueda corre dentro de una transacción mayor.
        cursor.execute(
            "SELECT current_setting('statement_timeout'), "
            "set_config('statement_timeout', %s, true)",
            [TIMEOUT_BUSQUEDA],
        )
        previo = cursor.fetchone()[0]
        try:
            cursor.execute(_FTS, parametros)
            filas = cursor.fetchall()
            if not filas:
                cursor.execute(
                    "SELECT set_config('pg_trgm.similarity_threshold', %s, true)",
                    [UMBRAL_SIMILITUD],
                )
                cursor.execute(_DIFUSA, parametros)
                filas = cursor.fetchall()
        finally:
            cursor.execute("SELECT set_config('statement_timeout', %s, true)", [previo])
    return [(int(f[0]), str(f[1]), int(f[2]), int(f[3])) for f in filas]


def resultados_por_ids(ids: Sequence[int]) -> list[ResultadoBusqueda]:
    """Filas del índice (solo publicados) con su portada DISPONIBLE, en el orden de `ids`."""
    documentos = (
        BusquedaDocumento.objects.filter(
            contenido_id__in=list(ids),
        )
        .filter(
            contenido_id__in=contenido_selectors.contenidos_visibles().values("pk"),
        )
        .select_related("contenido")
        .prefetch_related(prefetch_imagen("contenido__portada"))
    )
    por_id = {d.contenido_id: d for d in documentos}
    return [
        ResultadoBusqueda(
            tipo=d.tipo_contenido,
            slug=d.slug,
            titulo=d.titulo,
            resumen=d.resumen,
            pais=d.pais_nombre,
            portada=d.contenido.portada,
        )
        for d in (por_id[pk] for pk in ids if pk in por_id)
    ]


def buscar_agrupado(texto: str) -> dict[str, Any]:
    """Hasta 10 resultados por grupo y el total de cada grupo (FEAT-016)."""
    filas = _coincidencias(texto, None)
    totales = dict.fromkeys((str(t) for t in TIPOS_BUSCABLES), 0)
    elegidos: list[int] = []
    for contenido_id, tipo, posicion, total in filas:
        totales[tipo] = total
        if posicion <= MAX_POR_GRUPO:
            elegidos.append(contenido_id)
    resultados = resultados_por_ids(elegidos)
    grupos = {
        nombre: {"total": totales[tipo], "resultados": [r for r in resultados if r.tipo == tipo]}
        for nombre, tipo in GRUPOS.items()
    }
    return {"total": sum(totales.values()), "grupos": grupos}


def buscar_ids_grupo(texto: str, tipo: str) -> list[int]:
    """Todos los ids de un grupo por relevancia ("Ver todos"); se paginan en la vista."""
    return [contenido_id for contenido_id, _t, _p, _n in _coincidencias(texto, tipo)]


@dataclass(frozen=True)
class EstadoIndice:
    publicados: int
    indexados: int
    faltan: int
    sobran: int

    @property
    def coherente(self) -> bool:
        return self.faltan == 0 and self.sobran == 0 and self.publicados == self.indexados


def estado_indice() -> EstadoIndice:
    """Invariante de ADR-DB-003: contenido visible y buscable = filas del índice (sin PII)."""
    publicados = set(
        contenido_selectors.contenidos_visibles()
        .filter(tipo__in=TIPOS_BUSCABLES)
        .values_list("pk", flat=True)
    )
    indexados = set(BusquedaDocumento.objects.values_list("contenido_id", flat=True))
    return EstadoIndice(
        publicados=len(publicados),
        indexados=len(indexados),
        faltan=len(publicados - indexados),
        sobran=len(indexados - publicados),
    )
