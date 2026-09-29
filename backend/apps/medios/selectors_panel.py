"""Consultas de lectura de medios para el panel (AP-22, Skill_Backend §4.3).

Separado de `selectors.py` (biblioteca pública, solo DISPONIBLES) porque el panel necesita ver
todos los estados y datos internos (Skill_Backend Regla 01: el panel nunca accede al ORM
directamente, siempre a través de un selector o un service).
"""

from __future__ import annotations

from django.db.models import Exists, OuterRef, Q, QuerySet

from apps.contenido.models import Contenido, ContenidoMedio
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
