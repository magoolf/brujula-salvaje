"""Consultas de lectura del inicio y de la configuración del sitio (DATA-021/022/023, AP-01)."""

from __future__ import annotations

from apps.inicio.models import ID_SINGLETON, ConfigInicio, ConfigSitio, DestacadoInicio
from apps.medios.selectors import prefetch_imagen

MARCA_POR_DEFECTO = "Brújula Salvaje"


def config_sitio() -> ConfigSitio:
    """Singleton sembrado por inicio.0001; si faltara, valores por defecto sin Responsable."""
    return ConfigSitio.objects.filter(pk=ID_SINGLETON).first() or ConfigSitio(
        nombre_marca=MARCA_POR_DEFECTO, texto_descargo=""
    )


def nombre_marca() -> str:
    marca = ConfigSitio.objects.filter(pk=ID_SINGLETON).values_list("nombre_marca", flat=True)
    return marca.first() or MARCA_POR_DEFECTO


def config_inicio() -> ConfigInicio | None:
    """Bloque principal; hero_medio queda en None si el medio no está DISPONIBLE (RULE-005)."""
    return (
        ConfigInicio.objects.filter(pk=ID_SINGLETON)
        .prefetch_related(prefetch_imagen("hero_medio"))
        .first()
    )


def ids_destacados(seccion: str) -> list[int]:
    """Ids de contenido destacados en una sección, en su orden (el filtro PUBLICADO lo aplica
    quien los carga)."""
    return list(
        DestacadoInicio.objects.filter(seccion=seccion)
        .order_by("orden", "id")
        .values_list("contenido_id", flat=True)
    )
