"""TKT-060 (ADR-DB-004 §1.5 y §4.3, DB_HANDOFF): los comandos de gestión que auditan lo hacen con
`actor_etiqueta = 'sistema'` y actor_id NULL; los que no auditan no registran ningún evento.

Cobertura por comando (cargar_semilla en apps/contenido/tests/test_tkt060_*):
- anonimizar_cuentas: ya cubierto por
  test_AC_TKT005_05_anonimizar_cuentas_registra_y_es_idempotente.
- reaplicar_anonimizaciones: desactivación y anonimización reproducidas (aquí).
- purgar_auditoria, purgar_ops, purgar_sesiones, reindexar_busqueda, verificar_busqueda,
  vigilar_cache_limites y regenerar_derivados: no auditan (aquí).
"""

from __future__ import annotations

import io
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.auditoria.models import AccionAuditoria, EventoAuditoria
from apps.auditoria.services import ETIQUETA_SISTEMA
from apps.cuentas.models import CuentaStaff, EstadoCuenta, RolCuenta
from apps.cuentas.tests.conftest import (  # noqa: F401 (fixture de pytest)
    crear_staff,
    libro_anonimizaciones,
)

pytestmark = pytest.mark.django_db

T0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
COMANDOS_SIN_AUDITORIA = [
    "purgar_auditoria",
    "purgar_ops",
    "purgar_sesiones",
    "reindexar_busqueda",
    "verificar_busqueda",
    "vigilar_cache_limites",
    "regenerar_derivados",
]


def _f(momento: datetime) -> str:
    return momento.strftime("%Y-%m-%dT%H:%M:%SZ")


def _etiquetas(accion: str, cuenta: CuentaStaff) -> list[tuple[int | None, str]]:
    return list(
        EventoAuditoria.objects.filter(accion=accion, entidad_id=cuenta.pk).values_list(
            "actor_id", "actor_etiqueta"
        )
    )


def test_TKT060_reaplicar_anonimizaciones_audita_como_sistema(
    libro_anonimizaciones: Path,  # noqa: F811
) -> None:
    crear_staff("admin.tkt060", rol=RolCuenta.ADMINISTRADOR)
    activa = crear_staff("rel.tkt060.activa").cuenta
    desactivada = crear_staff("rel.tkt060.desactivada", estado=EstadoCuenta.DESACTIVADA).cuenta
    CuentaStaff.objects.filter(pk=desactivada.pk).update(desactivado_en=T0)
    # Bytes, no texto: en Windows write_text pondría CRLF y el libro sería LIBRO_CORRUPTO.
    libro_anonimizaciones.write_bytes(
        (
            f"{activa.pk};DESACTIVADA;{_f(T0)}\n"
            f"{desactivada.pk};DESACTIVADA;{_f(T0)}\n"
            f"{desactivada.pk};ANONIMIZADA;{_f(T0)}\n"
        ).encode()
    )
    if os.name == "posix":
        libro_anonimizaciones.chmod(0o640)

    call_command("reaplicar_anonimizaciones", stdout=io.StringIO())

    assert _etiquetas(AccionAuditoria.CUENTA_DESACTIVAR, activa) == [(None, ETIQUETA_SISTEMA)]
    assert _etiquetas(AccionAuditoria.CUENTA_ANONIMIZAR, desactivada) == [(None, ETIQUETA_SISTEMA)]


@pytest.mark.parametrize("nombre", COMANDOS_SIN_AUDITORIA)
def test_TKT060_comandos_que_no_auditan_no_registran_eventos(nombre: str) -> None:
    antes = EventoAuditoria.objects.count()

    call_command(nombre, stdout=io.StringIO())

    assert EventoAuditoria.objects.count() == antes
