"""Registro de eventos de auditoría (FEAT-046, DATA-025, THREAT-013, ADR-DB-004 §1).

- Solo inserción: app_rw no tiene UPDATE, DELETE ni TRUNCATE y un trigger lo impide también al
  propietario. La única excepción es la seudonimización al anonimizar una cuenta, que se hace
  con la función SECURITY DEFINER app.fn_auditoria_seudonimizar.
- El evento se inserta en la MISMA transacción que la acción auditada (DB_HANDOFF).
- Nunca se guardan valores: `campos_cambiados` lleva solo nombres de campos. La IP solo se guarda
  truncada (/24 o /48, tipo cidr) y solo en los eventos de autenticación (REQ-057).
"""

from __future__ import annotations

from collections.abc import Iterable

from django.db import connection

from apps.auditoria.models import (
    ACCIONES_CON_IP,
    AccionAuditoria,
    EventoAuditoria,
    ResultadoAuditoria,
)
from apps.core.throttling import red_truncada
from apps.cuentas.models import CuentaStaff

ETIQUETA_DESCONOCIDO = "desconocido"
ETIQUETA_SISTEMA = "sistema"
_LARGO_ETIQUETA = 60
_LARGO_TITULO = 150
# Mismo seudónimo que pone app.fn_auditoria_seudonimizar (0002_inmutabilidad, ADR-DB-004 §1).
PREFIJO_SEUDONIMO = "Cuenta anonimizada #"


def etiqueta_de_actor(actor_id: int | None) -> str:
    """Etiqueta del actor para `actor_etiqueta` (ActorRef.etiqueta: "Usuario o seudónimo").

    - Sin actor o con una cuenta inexistente: 'desconocido' (DB_HANDOFF, ADR-DB-004 §1.5).
    - Cuenta con usuario: su nombre de usuario (igual que `apps.cuentas.services._auditar`).
    - Cuenta sin usuario: solo una cuenta ANONIMIZADA puede no tenerlo (ck_cuenta_staff_identidad),
      así que recibe el mismo seudónimo que la seudonimización; nunca se guarda PII suya.

    Una sola consulta por clave primaria, y solo cuando el llamante no pasa la etiqueta.
    """
    if actor_id is None:
        return ETIQUETA_DESCONOCIDO
    filas = list(CuentaStaff.objects.filter(pk=actor_id).values_list("usuario", flat=True)[:1])
    if not filas:
        return ETIQUETA_DESCONOCIDO
    usuario = filas[0]
    return str(usuario) if usuario else f"{PREFIJO_SEUDONIMO}{actor_id}"


def registrar_evento(
    *,
    accion: AccionAuditoria | str,
    resultado: ResultadoAuditoria | str = ResultadoAuditoria.EXITO,
    actor_id: int | None = None,
    actor_etiqueta: str | None = None,
    tipo_entidad: str | None = None,
    entidad_id: int | None = None,
    entidad_titulo: str | None = None,
    campos_cambiados: Iterable[str] | None = None,
    ip: str | None = None,
) -> EventoAuditoria:
    """Inserta un evento. La IP del cliente se trunca y solo se guarda si la acción lo admite.

    Sin `actor_etiqueta` explícita, la etiqueta se resuelve desde la cuenta del actor
    (`etiqueta_de_actor`), con el mismo criterio que los eventos de cuentas (TKT-058, AC-030).
    """
    etiqueta = actor_etiqueta or etiqueta_de_actor(actor_id)
    campos = sorted(set(campos_cambiados)) if campos_cambiados is not None else None
    return EventoAuditoria.objects.create(
        actor_id=actor_id,
        actor_etiqueta=etiqueta[:_LARGO_ETIQUETA],
        accion=str(accion),
        resultado=str(resultado),
        tipo_entidad=tipo_entidad,
        entidad_id=entidad_id,
        entidad_titulo=entidad_titulo[:_LARGO_TITULO] if entidad_titulo else None,
        campos_cambiados=campos,
        ip_truncada=red_truncada(ip) if accion in ACCIONES_CON_IP else None,
    )


def seudonimizar_eventos_de_cuenta(cuenta_id: int) -> int:
    """Sustituye la etiqueta del actor por un seudónimo y anula su IP (cuenta ANONIMIZADA)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT app.fn_auditoria_seudonimizar(%s)", [cuenta_id])
        fila = cursor.fetchone()
    return int(fila[0]) if fila else 0


def purgar_eventos_caducados() -> int:
    """Purga los eventos con más de 365 días (ADR-DB-004 §1.3) con la función SECURITY DEFINER
    app.fn_auditoria_purgar(): el corte lo fija la BD, no el llamante. Devuelve las filas
    purgadas."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT app.fn_auditoria_purgar()")
        fila = cursor.fetchone()
    return int(fila[0]) if fila else 0
