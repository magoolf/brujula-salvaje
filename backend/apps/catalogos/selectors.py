"""Consultas de lectura de catálogos para el sitio público (DATA-001/002/008/020, RULE-012)."""

from __future__ import annotations

from collections.abc import Collection

from django.db.models import QuerySet

from apps.catalogos.models import CategoriaGuia, Escala, NivelEscala, Pais, Region


def niveles(escala: Escala) -> QuerySet[NivelEscala]:
    return NivelEscala.objects.filter(escala=escala).order_by("nivel")


def todos_los_niveles() -> list[NivelEscala]:
    return list(NivelEscala.objects.order_by("escala", "nivel"))


def existe_region(slug: str) -> bool:
    return Region.objects.filter(slug=slug, activo=True).exists()


def existe_pais(slug: str) -> bool:
    return Pais.objects.filter(slug=slug, activo=True).exists()


def existe_categoria(slug: str) -> bool:
    return CategoriaGuia.objects.filter(slug=slug, activo=True).exists()


def categoria_activa(slug: str) -> CategoriaGuia | None:
    return CategoriaGuia.objects.filter(slug=slug, activo=True).first()


def regiones_con_paises(region_ids: Collection[int], pais_ids: Collection[int]) -> list[Region]:
    """Regiones activas indicadas con sus países activos indicados (facetas, RULE-019)."""
    regiones = list(
        Region.objects.filter(pk__in=region_ids, activo=True).order_by("orden", "nombre")
    )
    paises = Pais.objects.filter(pk__in=pais_ids, activo=True).order_by("nombre")
    por_region: dict[int, list[Pais]] = {}
    for pais in paises:
        por_region.setdefault(pais.region_id, []).append(pais)
    for region in regiones:
        region.paises_publicos = por_region.get(region.pk, [])  # type: ignore[attr-defined]
    return regiones
