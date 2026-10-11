"""TKT-062, OBS-QA058-01: `registrar_evento` sin etiqueta resuelve la del actor UNA vez por bloque
atómico (memoria por transacción, `apps.core.memoria_transaccion`), no una vez por evento: una
cascada de hasta 212 eventos del mismo actor hacía 212 SELECT.

La memoria nunca sirve una etiqueta obsoleta: se descarta al terminar el bloque y
`seudonimizar_eventos_de_cuenta` olvida la cuenta que se anonimiza (THREAT-013).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.auditoria.models import AccionAuditoria
from apps.auditoria.services import (
    PREFIJO_SEUDONIMO,
    etiqueta_de_actor,
    registrar_evento,
    seudonimizar_eventos_de_cuenta,
)
from apps.core import memoria_transaccion
from apps.cuentas.models import CuentaStaff, EstadoCuenta

pytestmark = pytest.mark.django_db

CASCADA = 212


def _selects_de_cuenta(consultas: CaptureQueriesContext) -> int:
    return sum(
        1
        for q in consultas.captured_queries
        if q["sql"].startswith("SELECT") and '"cuenta_staff"' in q["sql"]
    )


def _anonimizar_en_bd(cuenta: CuentaStaff) -> None:
    CuentaStaff.objects.filter(pk=cuenta.pk).update(
        usuario=None,
        nombre_visible=None,
        secreto_mfa=None,
        mfa_activo=False,
        last_login=None,
        password="!inutilizable",  # nosec B106 (hash inutilizable)
        estado=EstadoCuenta.ANONIMIZADA,
        desactivado_en=timezone.now(),
        anonimizado_en=timezone.now(),
    )


def test_TKT062_cascada_de_212_eventos_hace_un_solo_select(editora: Any, admin: Any) -> None:
    with CaptureQueriesContext(connection) as consultas, transaction.atomic():
        eventos = [
            registrar_evento(
                accion=AccionAuditoria.RETIRAR,
                actor_id=(editora if i % 2 else admin).cuenta.pk,
                entidad_id=i + 1,
            )
            for i in range(CASCADA)
        ]
    # 2 actores distintos: 2 SELECT (uno por actor), no 212.
    assert _selects_de_cuenta(consultas) == 2
    assert {e.actor_etiqueta for e in eventos} == {"editora.uno", "admin.principal"}


def test_TKT062_cada_bloque_atomico_nuevo_vuelve_a_resolver(editora: Any) -> None:
    """Dos operaciones (dos `atomic`) no comparten memoria: un cambio entre ellas se ve."""
    with CaptureQueriesContext(connection) as consultas:
        for _ in range(2):
            with transaction.atomic():
                registrar_evento(accion=AccionAuditoria.EDITAR, actor_id=editora.cuenta.pk)
                registrar_evento(accion=AccionAuditoria.EDITAR, actor_id=editora.cuenta.pk)
    assert _selects_de_cuenta(consultas) == 2

    _anonimizar_en_bd(editora.cuenta)
    with transaction.atomic():
        evento = registrar_evento(accion=AccionAuditoria.EDITAR, actor_id=editora.cuenta.pk)
    assert evento.actor_etiqueta == f"{PREFIJO_SEUDONIMO}{editora.cuenta.pk}"


def test_TKT062_THREAT_013_seudonimizar_olvida_la_etiqueta_memorizada(editora: Any) -> None:
    """Flujo de anonimización: tras seudonimizar, los eventos del mismo bloque llevan el
    seudónimo, nunca el usuario memorizado antes (PII)."""
    cuenta = editora.cuenta
    with transaction.atomic():
        antes = registrar_evento(accion=AccionAuditoria.PUBLICAR, actor_id=cuenta.pk)
        assert antes.actor_etiqueta == "editora.uno"
        _anonimizar_en_bd(cuenta)
        seudonimizar_eventos_de_cuenta(cuenta.pk)
        despues = registrar_evento(accion=AccionAuditoria.PUBLICAR, actor_id=cuenta.pk)
    assert despues.actor_etiqueta == f"{PREFIJO_SEUDONIMO}{cuenta.pk}"
    antes.refresh_from_db()
    assert antes.actor_etiqueta == f"{PREFIJO_SEUDONIMO}{cuenta.pk}"


def test_TKT062_cuenta_inexistente_no_se_memoriza(editora: Any) -> None:
    with transaction.atomic():
        assert etiqueta_de_actor(987654321) == "desconocido"
        memoria = memoria_transaccion.memoria_de_transaccion("auditoria.etiqueta_de_actor")
        assert memoria is not None
        assert 987654321 not in memoria
        assert etiqueta_de_actor(editora.cuenta.pk) == "editora.uno"
        assert memoria == {editora.cuenta.pk: "editora.uno"}


def test_TKT062_rollback_descarta_la_memoria(editora: Any) -> None:
    """Un savepoint deshecho se lleva el marcador de la memoria: la siguiente lectura consulta."""
    with transaction.atomic():
        try:
            with transaction.atomic():
                etiqueta_de_actor(editora.cuenta.pk)
                raise RuntimeError("deshacer")
        except RuntimeError:
            pass
        with CaptureQueriesContext(connection) as consultas:
            assert etiqueta_de_actor(editora.cuenta.pk) == "editora.uno"
    assert _selects_de_cuenta(consultas) == 1
