"""Consultas de lectura del panel editorial (Skill_Backend §4.3): listados paginados de
contenido por tipo (AP-20/AP-21), usadas por `panel_views.py`. Solo lectura; las mutaciones viven
en `apps.contenido.services`.
"""

from __future__ import annotations

from django.db.models import Q, QuerySet

from apps.contenido.models import Contenido


def listar_por_tipo(
    tipo: str, *, estado: str | None = None, texto: str | None = None
) -> QuerySet[Contenido]:
    qs = Contenido.objects.filter(tipo=tipo).select_related("actualizado_por")
    if estado:
        qs = qs.filter(estado_editorial=estado)
    if texto:
        qs = qs.filter(Q(titulo__icontains=texto) | Q(slug__icontains=texto))
    return qs.order_by("-actualizado_en", "-id")
