"""Mantenimiento del índice de búsqueda busqueda_documento (ADR-DB-003 §2, DEC-AUTO-086).

- `indexar(contenido_id)`: upsert si el contenido está PUBLICADO y es de un tipo buscable; si no,
  borra su fila. Lo usa el servicio de publicación (TKT-006) en la MISMA transacción que
  publicar, actualizar, retirar, reactivar o eliminar (RULE-001 por construcción).
- `reindexar_todo()`: reconstrucción idempotente (DELETE + INSERT en una transacción); la usa el
  comando reindexar_busqueda (tras restauraciones, migraciones de configuración y a demanda).
Pesos: A título, B resumen, C nombres de país y de tipos, D cuerpo en texto plano. El HTML del
texto enriquecido se convierte a texto plano aquí, antes de indexar.
"""

from __future__ import annotations

import html
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import structlog
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection, transaction
from django.db.models import Prefetch, QuerySet
from django.utils.html import strip_tags

from apps.busqueda.models import TIPOS_BUSCABLES, BusquedaDocumento
from apps.contenido import selectors as contenido_selectors
from apps.contenido.models import (
    Contenido,
    DiaItinerario,
    EstadoEditorial,
    TipoAventura,
    TipoContenido,
)

T = TipoContenido
logger = structlog.get_logger("brujula.busqueda")
CONFIG = "app.es_unaccent"
_VECTOR = " || ".join(
    f"setweight(to_tsvector('{CONFIG}', %s), '{peso}')" for peso in ("A", "B", "C", "D")
)
# Solo constantes internas en la sentencia; todos los valores van parametrizados.
_PLANTILLA_UPSERT = (
    "INSERT INTO busqueda_documento (contenido_id, tipo_contenido, slug, titulo, titulo_norm, "
    "resumen, pais_nombre, documento, actualizado_en) "
    "VALUES (%s, %s, %s, %s, app.f_normalizar(%s), %s, %s, <vector>, now()) "
    "ON CONFLICT (contenido_id) DO UPDATE SET tipo_contenido = EXCLUDED.tipo_contenido, "
    "slug = EXCLUDED.slug, titulo = EXCLUDED.titulo, titulo_norm = EXCLUDED.titulo_norm, "
    "resumen = EXCLUDED.resumen, pais_nombre = EXCLUDED.pais_nombre, "
    "documento = EXCLUDED.documento, actualizado_en = now()"
)
_UPSERT = _PLANTILLA_UPSERT.replace("<vector>", _VECTOR)


@dataclass(frozen=True)
class Documento:
    contenido_id: int
    tipo: str
    slug: str
    titulo: str
    resumen: str | None
    pais: str | None
    nombres: str
    cuerpo: str


def texto_plano(*fragmentos: str | None) -> str:
    """HTML saneado (RULE-022) → texto plano para el vector de búsqueda."""
    return " ".join(html.unescape(strip_tags(f)) for f in fragmentos if f).strip()


def _tipos(ruta: str) -> Prefetch[str, QuerySet[Any], str]:
    publicados = TipoAventura.objects.filter(
        contenido__estado_editorial=EstadoEditorial.PUBLICADO
    ).select_related("contenido")
    return Prefetch(ruta, queryset=publicados, to_attr="tipos_indexables")


def _candidatos(ids: Iterable[int] | None = None) -> QuerySet[Contenido]:
    qs = Contenido.objects.filter(
        estado_editorial=EstadoEditorial.PUBLICADO, tipo__in=TIPOS_BUSCABLES
    )
    if ids is not None:
        qs = qs.filter(pk__in=list(ids))
    return qs.select_related(
        "destino__pais", "itinerario__destino__pais", "guia", "tipo_aventura"
    ).prefetch_related(
        _tipos("destino__tipos_aventura"),
        _tipos("itinerario__tipos_aventura"),
        _tipos("guia__tipos_aventura"),
        Prefetch("itinerario__dias", queryset=DiaItinerario.objects.order_by("numero_dia")),
    )


def _nombres_tipos(subtipo: object) -> list[str]:
    return [t.contenido.titulo for t in getattr(subtipo, "tipos_indexables", [])]


def documento_de(contenido: Contenido) -> Documento:
    """Campos del documento derivado según el tipo (ADR-DB-003 §2)."""
    pais: str | None = None
    nombres: list[str] = []
    if contenido.tipo == T.DESTINO:
        d = contenido.destino
        pais = d.pais.nombre if d.pais is not None else None
        resumen = d.resumen
        nombres = _nombres_tipos(d)
        cuerpo = texto_plano(
            d.descripcion_experta, d.clima, d.como_llegar, d.seguridad_riesgos, d.sostenibilidad
        )
    elif contenido.tipo == T.ITINERARIO:
        i = contenido.itinerario
        destino = i.destino
        pais = destino.pais.nombre if destino is not None and destino.pais is not None else None
        resumen = i.resumen
        nombres = _nombres_tipos(i)
        dias = [f"{dia.titulo} {dia.actividades} {dia.consejos or ''}" for dia in i.dias.all()]
        cuerpo = texto_plano(*dias, i.riesgos_seguridad)
    elif contenido.tipo == T.GUIA:
        g = contenido.guia
        resumen = g.resumen
        nombres = _nombres_tipos(g)
        cuerpo = texto_plano(g.cuerpo)
    else:
        t = contenido.tipo_aventura
        resumen = t.resumen
        cuerpo = texto_plano(t.descripcion)
    return Documento(
        contenido_id=contenido.pk,
        tipo=contenido.tipo,
        slug=contenido.slug,
        titulo=contenido.titulo,
        resumen=resumen,
        pais=pais,
        nombres=" ".join(filter(None, [pais, *nombres])),
        cuerpo=cuerpo,
    )


def _guardar(documentos: Iterable[Documento]) -> int:
    filas = [
        (
            doc.contenido_id,
            doc.tipo,
            doc.slug,
            doc.titulo,
            doc.titulo,
            doc.resumen,
            doc.pais,
            doc.titulo,
            doc.resumen or "",
            doc.nombres,
            doc.cuerpo,
        )
        for doc in documentos
    ]
    if filas:
        with connection.cursor() as cursor:
            cursor.executemany(_UPSERT, filas)
    return len(filas)


def _ids_indexables() -> set[int]:
    """Contenido visible en la API pública y de un tipo buscable (misma regla que el detalle)."""
    return set(
        contenido_selectors.contenidos_visibles()
        .filter(tipo__in=TIPOS_BUSCABLES)
        .values_list("pk", flat=True)
    )


def _documento_o_none(contenido: Contenido) -> Documento | None:
    try:
        return documento_de(contenido)
    except (ObjectDoesNotExist, AttributeError) as exc:
        logger.warning(
            "busqueda_documento_omitido", contenido_id=contenido.pk, tipo=type(exc).__name__
        )
        return None


def indexar(contenido_id: int) -> bool:
    """Upsert del documento si es público y buscable; si no, lo elimina. True si queda indexado."""
    with transaction.atomic():
        contenido = _candidatos([contenido_id]).first()
        documento = None
        if contenido is not None and contenido_selectors.es_visible(contenido_id):
            documento = _documento_o_none(contenido)
        if documento is None:
            BusquedaDocumento.objects.filter(contenido_id=contenido_id).delete()
            return False
        _guardar([documento])
        return True


@dataclass(frozen=True)
class ResultadoReindex:
    documentos: int
    omitidos: int


def reindexar_todo() -> ResultadoReindex:
    """DELETE + INSERT en una transacción (idempotente).

    Un registro publicado pero incoherente (sin fila de subtipo, o no visible en la API pública)
    no aborta la reconstrucción: se omite, se registra su id (sin PII) y se cuenta (OBS-04).
    """
    with transaction.atomic():
        BusquedaDocumento.objects.all().delete()
        visibles = _ids_indexables()
        documentos: list[Documento] = []
        omitidos = 0
        for contenido in _candidatos():
            if contenido.pk not in visibles:
                logger.warning(
                    "busqueda_documento_omitido", contenido_id=contenido.pk, tipo="no_visible"
                )
                omitidos += 1
                continue
            documento = _documento_o_none(contenido)
            if documento is None:
                omitidos += 1
                continue
            documentos.append(documento)
        return ResultadoReindex(documentos=_guardar(documentos), omitidos=omitidos)
