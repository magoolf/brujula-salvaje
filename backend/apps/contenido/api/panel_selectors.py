"""Consultas de lectura del panel editorial (Skill_Backend §4.3): listados paginados de
contenido por tipo (AP-20/AP-21), usadas por `panel_views.py`. Solo lectura; las mutaciones viven
en `apps.contenido.services`.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.db.models import Prefetch, Q, QuerySet

from apps.catalogos.models import CategoriaGuia, Pais
from apps.contenido.models import Contenido, TipoContenido
from apps.core.miniaturas import medio_miniatura
from apps.medios.models import Medio
from apps.medios.selectors import derivados_ordenados

T = TipoContenido
# maxItems de `ContenidoPanelMeta.referencias` (contracts/openapi.yaml). Los campos editables ya
# los acotan (portada + galería ≤ 31, relaciones + elementos ≤ 112...); el corte es defensivo.
MAX_MEDIOS = 60
MAX_CONTENIDOS = 200
MAX_TERMINOS = 50
MAX_TAXONOMIAS = 100


def listar_por_tipo(
    tipo: str, *, estado: str | None = None, texto: str | None = None
) -> QuerySet[Contenido]:
    qs = Contenido.objects.filter(tipo=tipo).select_related("actualizado_por")
    if estado:
        qs = qs.filter(estado_editorial=estado)
    if texto:
        qs = qs.filter(Q(titulo__icontains=texto) | Q(slug__icontains=texto))
    return qs.order_by("-actualizado_en", "-id")


def _unicos(valores: Iterable[Any]) -> list[Any]:
    """Sin None ni repetidos, en el orden de la primera aparición."""
    vistos: dict[Any, None] = {}
    for valor in valores:
        if valor is not None:
            vistos.setdefault(valor, None)
    return list(vistos)


def referencias_panel(campos: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """`ContenidoPanelMeta.referencias` (TKT-062): datos de visualización de los ids que
    referencian los campos editables (`services.campos_editables`) de un contenido, en un número
    FIJO de consultas (sin N+1): 1 para todos los contenidos referenciados (relacionados, destino,
    destinos, elementos de colección, términos y tipos de aventura), 2 para los medios (licencia
    por JOIN + derivados) y 1 para el país o la categoría. Criterio (DEC-AUTO-1170):

    - `medios`: portada y galería, en ese orden; `MedioMiniatura` con el criterio de inicio
      (`apps.core.miniaturas`); un medio sin derivados se omite (DEC-AUTO-1081).
    - `contenidos`: relacionados, destino (itinerario), destinos (guía) y elementos (colección),
      en ese orden y sin repetir, con su estado real (el panel ve borradores y retirados).
    - `terminos`: los términos de glosario vinculados ({id, termino}).
    - `taxonomias`: país (PAIS), categoría de guía (CATEGORIA) y tipos de aventura (TIPO).
    """
    medio_ids = _unicos([campos.get("portada_id"), *(campos.get("galeria_ids") or [])])
    contenido_ids = _unicos(
        [
            *(r["id"] for r in campos.get("relaciones") or []),
            campos.get("destino_id"),
            *(campos.get("destinos_ids") or []),
            *(e["contenido_id"] for e in campos.get("elementos") or []),
        ]
    )
    termino_ids = _unicos(campos.get("terminos_ids") or [])
    tipo_ids = _unicos([*(campos.get("tipos_ids") or []), campos.get("tipo_principal_id")])

    filas: dict[int, Contenido] = {}
    todos = {*contenido_ids, *termino_ids, *tipo_ids}
    if todos:
        filas = {
            c.pk: c
            for c in Contenido.objects.filter(pk__in=todos).only(
                "id", "tipo", "titulo", "slug", "estado_editorial"
            )
        }
    return {
        "medios": _medios(medio_ids)[:MAX_MEDIOS],
        "contenidos": [
            {
                "tipo": c.tipo,
                "id": c.pk,
                "titulo": c.titulo,
                "slug": c.slug,
                "estado_editorial": c.estado_editorial,
            }
            for c in (filas.get(i) for i in contenido_ids)
            if c is not None
        ][:MAX_CONTENIDOS],
        "terminos": [
            {"id": c.pk, "termino": c.titulo}
            for c in (filas.get(i) for i in termino_ids)
            if c is not None and c.tipo == T.TERMINO
        ][:MAX_TERMINOS],
        "taxonomias": [
            *_catalogo("PAIS", Pais, campos.get("pais_id")),
            *_catalogo("CATEGORIA", CategoriaGuia, campos.get("categoria_id")),
            *(
                {"clase": "TIPO", "id": c.pk, "nombre": c.titulo}
                for c in (filas.get(i) for i in tipo_ids)
                if c is not None and c.tipo == T.TIPO
            ),
        ][:MAX_TAXONOMIAS],
    }


def _medios(ids: list[int]) -> list[dict[str, Any]]:
    if not ids:
        return []
    por_id = {
        m.pk: m
        for m in Medio.objects.filter(pk__in=ids)
        .select_related("licencia")
        .prefetch_related(Prefetch("derivados", queryset=derivados_ordenados()))
    }
    miniaturas = (medio_miniatura(por_id[i]) for i in ids if i in por_id)
    return [m for m in miniaturas if m is not None]


def _catalogo(clase: str, modelo: type[Pais] | type[CategoriaGuia], id: int | None) -> list[Any]:
    if id is None:
        return []
    nombres = list(modelo.objects.filter(pk=id).values_list("nombre", flat=True)[:1])
    return [{"clase": clase, "id": id, "nombre": nombres[0]}] if nombres else []
