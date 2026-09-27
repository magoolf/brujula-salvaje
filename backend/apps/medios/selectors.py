"""Consultas de lectura de medios para el sitio público (RULE-005, THREAT-019, AP-11).

Solo los medios DISPONIBLES aparecen en la API pública: un medio en otro estado se omite (la
imagen vale None). Nunca se exponen datos del staff (subido_por) ni la ruta del original.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Prefetch, QuerySet

from apps.medios.models import EstadoMedio, Medio, MedioDerivado


def derivados_ordenados() -> QuerySet[MedioDerivado]:
    return MedioDerivado.objects.order_by("formato", "ancho_px", "id")


def medios_publicos() -> QuerySet[Medio]:
    """Medios DISPONIBLES con su licencia y derivados (sin N+1)."""
    return (
        Medio.objects.filter(estado=EstadoMedio.DISPONIBLE)
        .select_related("licencia")
        .prefetch_related(Prefetch("derivados", queryset=derivados_ordenados()))
    )


def prefetch_imagen(ruta: str) -> Prefetch[str, QuerySet[Any], str]:
    """Prefetch de una FK a medio: si el medio no está DISPONIBLE, el atributo queda en None."""
    return Prefetch(ruta, queryset=medios_publicos())
