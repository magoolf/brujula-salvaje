"""Consultas de lectura de medios para el panel (AP-22, Skill_Backend §4.3).

Separado de `selectors.py` (biblioteca pública, solo DISPONIBLES) porque el panel necesita ver
todos los estados y datos internos (Skill_Backend Regla 01: el panel nunca accede al ORM
directamente, siempre a través de un selector o un service).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from django.db.models import Count, Exists, OuterRef, Q, QuerySet

from apps.contenido.models import Contenido, ContenidoMedio, EstadoEditorial
from apps.inicio.models import ConfigInicio
from apps.medios.models import Medio


def listar_panel(
    *,
    estado: str | None = None,
    licencia: str | None = None,
    en_uso: bool | None = None,
    texto: str | None = None,
) -> QuerySet[Medio]:
    qs = Medio.objects.select_related("licencia").prefetch_related("derivados")
    if estado:
        qs = qs.filter(estado=estado)
    if licencia:
        qs = qs.filter(licencia__codigo=licencia)
    if texto:
        qs = qs.filter(
            Q(texto_alternativo__icontains=texto)
            | Q(autor_credito__icontains=texto)
            | Q(titulo_interno__icontains=texto)
        )
    if en_uso is not None:
        usado = Q(Exists(Contenido.objects.filter(portada_id=OuterRef("pk")))) | Q(
            Exists(ContenidoMedio.objects.filter(medio_id=OuterRef("pk")))
        )
        qs = qs.filter(usado) if en_uso else qs.exclude(usado)
    return qs.order_by("-subido_en", "-id")


@dataclass(frozen=True)
class ResumenUsos:
    """`MedioPanel.numero_usos` y `MedioPanel.en_uso_publicado` de un medio (TKT-068)."""

    numero_usos: int
    en_uso_publicado: bool


SIN_USOS = ResumenUsos(numero_usos=0, en_uso_publicado=False)


def resumen_usos(medio_ids: Iterable[int]) -> dict[int, ResumenUsos]:
    """Resumen de usos de un LOTE de medios en 3 consultas agregadas, sin importar su tamaño
    (TKT-068: antes `MedioPanelSerializer` hacía `services.usos` + `services._en_uso_publicado`
    por medio, 6 consultas cada uno -- N+1 en el listado del panel).

    Mismos valores que esas dos funciones (prueba de equivalencia en
    `tests/test_tkt068_usos_por_lote.py`):
    - `numero_usos` = `len(services.usos(id))`: contenidos con el medio de portada + filas de
      galería (`ContenidoMedio`) + 1 si es el hero de inicio (fila única aunque el singleton
      existiera más de una vez);
    - `en_uso_publicado` = `services._en_uso_publicado(id)`: portada o galería de un contenido
      PUBLICADO, o hero de inicio (sin estado editorial: cuenta siempre como publicado).
    Un id sin usos no aparece en el resultado: el llamante usa `SIN_USOS`."""
    ids = {int(i) for i in medio_ids}
    if not ids:
        return {}
    publicado = EstadoEditorial.PUBLICADO
    totales: dict[int, list[int]] = {}  # id -> [usos, usos en publicado]

    def acumular(medio_id: int, usos: int, publicados: int) -> None:
        fila = totales.setdefault(medio_id, [0, 0])
        fila[0] += usos
        fila[1] += publicados

    portadas = (
        Contenido.objects.filter(portada_id__in=ids)
        .values("portada_id")
        .annotate(n=Count("pk"), pub=Count("pk", filter=Q(estado_editorial=publicado)))
        .order_by()
    )
    for fila in portadas:
        acumular(fila["portada_id"], fila["n"], fila["pub"])
    galerias = (
        ContenidoMedio.objects.filter(medio_id__in=ids)
        .values("medio_id")
        .annotate(n=Count("pk"), pub=Count("pk", filter=Q(contenido__estado_editorial=publicado)))
        .order_by()
    )
    for fila in galerias:
        acumular(fila["medio_id"], fila["n"], fila["pub"])
    heroes = ConfigInicio.objects.filter(hero_medio_id__in=ids).values_list(
        "hero_medio_id", flat=True
    )
    for hero_id in set(heroes):
        acumular(hero_id, 1, 1)
    return {
        medio_id: ResumenUsos(numero_usos=usos, en_uso_publicado=publicados > 0)
        for medio_id, (usos, publicados) in totales.items()
    }
