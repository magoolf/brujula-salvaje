"""Consultas de lectura de la auditoría (FLOW-016, AP-23; Skill_Backend §4.3).

Orden: ocurrido_en descendente (índice ix_evento_auditoria_ocurrido) y id descendente para que
la paginación sea estable. El filtro por actor usa ix_evento_auditoria_actor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db.models import QuerySet

from apps.auditoria.models import EventoAuditoria


@dataclass(frozen=True)
class FiltrosAuditoria:
    desde: datetime | None = None
    hasta: datetime | None = None
    actor_id: int | None = None
    accion: str | None = None
    tipo_entidad: str | None = None
    resultado: str | None = None


def listar_eventos(filtros: FiltrosAuditoria) -> QuerySet[EventoAuditoria]:
    eventos = EventoAuditoria.objects.all()
    if filtros.desde is not None:
        eventos = eventos.filter(ocurrido_en__gte=filtros.desde)
    if filtros.hasta is not None:
        eventos = eventos.filter(ocurrido_en__lte=filtros.hasta)
    if filtros.actor_id is not None:
        eventos = eventos.filter(actor_id=filtros.actor_id)
    if filtros.accion:
        eventos = eventos.filter(accion=filtros.accion)
    if filtros.tipo_entidad:
        eventos = eventos.filter(tipo_entidad=filtros.tipo_entidad)
    if filtros.resultado:
        eventos = eventos.filter(resultado=filtros.resultado)
    return eventos.order_by("-ocurrido_en", "-id")
