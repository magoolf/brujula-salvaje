"""Consultas de lectura del inicio y de la configuración del sitio (DATA-021/022/023, AP-01)."""

from __future__ import annotations

from typing import Any

from django.db.models import Prefetch

from apps.contenido.models import Contenido
from apps.inicio.models import (
    ID_SINGLETON,
    ConfigInicio,
    ConfigSitio,
    DestacadoInicio,
    SeccionInicio,
)
from apps.medios.selectors import derivados_ordenados, medios_publicos

MARCA_POR_DEFECTO = "Brújula Salvaje"


def config_sitio() -> ConfigSitio:
    """Singleton sembrado por inicio.0001; si faltara, valores por defecto sin Responsable."""
    return ConfigSitio.objects.filter(pk=ID_SINGLETON).first() or ConfigSitio(
        nombre_marca=MARCA_POR_DEFECTO, texto_descargo=""
    )


def nombre_marca() -> str:
    marca = ConfigSitio.objects.filter(pk=ID_SINGLETON).values_list("nombre_marca", flat=True)
    return marca.first() or MARCA_POR_DEFECTO


def hero_medio_id() -> int | None:
    return (
        ConfigInicio.objects.filter(pk=ID_SINGLETON).values_list("hero_medio_id", flat=True).first()
    )


def hero() -> dict[str, Any] | None:
    """Bloque principal del inicio; None si no está configurado o su medio no está DISPONIBLE
    (RULE-005): el público nunca ve un medio sin licencia ni crédito."""
    config = ConfigInicio.objects.filter(pk=ID_SINGLETON).first()
    if config is None:
        return None
    medio = medios_publicos().filter(pk=config.hero_medio_id).first()
    if medio is None:
        return None
    return {
        "hero_titular": config.hero_titular,
        "hero_subtitulo": config.hero_subtitulo,
        "hero_medio": medio,
    }


def ids_destacados(seccion: str) -> list[int]:
    """Ids de contenido destacados en una sección, en su orden (el filtro PUBLICADO lo aplica
    quien los carga)."""
    return list(
        DestacadoInicio.objects.filter(seccion=seccion)
        .order_by("orden", "id")
        .values_list("contenido_id", flat=True)
    )


def config_inicio_panel() -> ConfigInicio | None:
    """Singleton para el panel (TKT-057) con todo lo que pinta `ConfigInicioPanel` cargado en 2
    consultas: el autor de la última edición y el medio del hero con su licencia (JOIN) y sus
    derivados (prefetch). El panel ve el medio en cualquier estado (no se filtra DISPONIBLE)."""
    return (
        ConfigInicio.objects.filter(pk=ID_SINGLETON)
        .select_related("actualizado_por", "hero_medio__licencia")
        .prefetch_related(Prefetch("hero_medio__derivados", queryset=derivados_ordenados()))
        .first()
    )


def destacados_panel() -> dict[str, list[Contenido]]:
    """Contenidos destacados por sección (en su orden), en UNA consulta con su contenido (JOIN):
    alimenta `*_ids` y `referencias.contenidos` de `ConfigInicioPanel` sin N+1 (TKT-057). No
    filtra por estado: el panel debe ver también los destacados retirados o en borrador."""
    secciones: dict[str, list[Contenido]] = {seccion: [] for seccion in SeccionInicio.values}
    filas = DestacadoInicio.objects.select_related("contenido").order_by("orden", "id")
    for destacado in filas:
        secciones[destacado.seccion].append(destacado.contenido)
    return secciones
