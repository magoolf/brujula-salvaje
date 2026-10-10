"""TKT-058 (AC-030): la etiqueta del actor es su usuario o seudónimo, nunca '#<id>'.

`ActorRef.etiqueta` es "Usuario o seudónimo" (contracts/openapi.yaml) y AC-030 exige que cada
acción quede "registrada con usuario". Antes, los llamantes que no pasaban la etiqueta (acciones
editoriales: CONFIG_SITIO, CONFIG_INICIO, CREAR, TAXONOMIA, PUBLICAR, EDITAR_MEDIO...) guardaban
'#<id>' y SCR-046 mostraba "#44" en la columna Actor.
"""

from __future__ import annotations

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.auditoria.models import AccionAuditoria, EventoAuditoria
from apps.auditoria.services import (
    ETIQUETA_DESCONOCIDO,
    PREFIJO_SEUDONIMO,
    etiqueta_de_actor,
    registrar_evento,
    seudonimizar_eventos_de_cuenta,
)
from apps.catalogos import services as catalogos
from apps.cuentas.models import CuentaStaff, EstadoCuenta
from apps.cuentas.tests.conftest import BASE

pytestmark = pytest.mark.django_db
RUTA = f"{BASE}/auditoria"

# Acciones editoriales cuyos llamantes (contenido, medios, catalogos, inicio) no pasan etiqueta.
ACCIONES_EDITORIALES = [
    AccionAuditoria.CREAR,
    AccionAuditoria.EDITAR,
    AccionAuditoria.PUBLICAR,
    AccionAuditoria.ACTUALIZAR_PUBLICACION,
    AccionAuditoria.RETIRAR,
    AccionAuditoria.REACTIVAR,
    AccionAuditoria.ELIMINAR_BORRADOR,
    AccionAuditoria.RESTAURAR_REVISION,
    AccionAuditoria.SUBIR_MEDIO,
    AccionAuditoria.EDITAR_MEDIO,
    AccionAuditoria.RETIRAR_MEDIO,
    AccionAuditoria.CONFIG_INICIO,
    AccionAuditoria.CONFIG_SITIO,
    AccionAuditoria.TAXONOMIA,
]


def _anonimizar_en_bd(cuenta: CuentaStaff) -> None:
    """Deja la cuenta ANONIMIZADA cumpliendo ck_cuenta_staff_anonimizada."""
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


@pytest.mark.parametrize("accion", ACCIONES_EDITORIALES, ids=lambda a: str(a))
def test_AC_030_accion_editorial_registrada_con_usuario(editora, accion):
    evento = registrar_evento(accion=accion, actor_id=editora.cuenta.pk, entidad_id=1)
    evento.refresh_from_db()
    assert evento.actor_etiqueta == "editora.uno"
    assert evento.actor_id == editora.cuenta.pk


@pytest.mark.parametrize("accion", list(AccionAuditoria), ids=lambda a: str(a))
def test_AC_030_ninguna_accion_guarda_id_como_etiqueta(admin, accion):
    evento = registrar_evento(accion=accion, actor_id=admin.cuenta.pk)
    evento.refresh_from_db()
    assert evento.actor_etiqueta == "admin.principal"
    assert not evento.actor_etiqueta.startswith("#")


def test_AC_030_taxonomia_desde_el_servicio_y_en_scr046(cliente_admin, editora):
    """Flujo real (catalogos sin etiqueta) y la columna Actor de SCR-046 (GET auditoría)."""
    catalogos.crear_region(
        editora.cuenta.pk,
        {"nombre": "Región TKT-058", "slug": "region-tkt-058", "continente": "ASIA"},
    )
    cuerpo = cliente_admin.get(f"{RUTA}?accion=TAXONOMIA").json()
    assert cuerpo["total"] == 1
    assert cuerpo["resultados"][0]["actor"] == {
        "id": editora.cuenta.pk,
        "etiqueta": "editora.uno",
    }


def test_AC_030_etiqueta_explicita_prevalece_sin_consulta_extra(editora):
    with CaptureQueriesContext(connection) as consultas:
        evento = registrar_evento(
            accion=AccionAuditoria.CUENTA_DESACTIVAR,
            actor_id=editora.cuenta.pk,
            actor_etiqueta="sistema",
        )
    assert evento.actor_etiqueta == "sistema"
    assert len(consultas) == 1  # solo el INSERT


def test_AC_030_resolver_la_etiqueta_cuesta_una_consulta(editora):
    with CaptureQueriesContext(connection) as consultas:
        registrar_evento(accion=AccionAuditoria.EDITAR, actor_id=editora.cuenta.pk)
    assert len(consultas) == 2  # SELECT usuario por PK + INSERT


def test_AC_030_sin_actor_sigue_siendo_desconocido_sin_consulta():
    with CaptureQueriesContext(connection) as consultas:
        assert etiqueta_de_actor(None) == ETIQUETA_DESCONOCIDO
    assert len(consultas) == 0
    evento = registrar_evento(accion=AccionAuditoria.LOGIN_FALLIDO, resultado="FALLO")
    assert evento.actor_etiqueta == ETIQUETA_DESCONOCIDO


def test_AC_030_cuenta_inexistente_es_desconocido():
    assert etiqueta_de_actor(987654321) == ETIQUETA_DESCONOCIDO


def test_THREAT_013_cuenta_anonimizada_recibe_el_seudonimo_no_pii(editora):
    cuenta = editora.cuenta
    _anonimizar_en_bd(cuenta)
    evento = registrar_evento(accion=AccionAuditoria.CUENTA_ANONIMIZAR, actor_id=cuenta.pk)
    assert evento.actor_etiqueta == f"{PREFIJO_SEUDONIMO}{cuenta.pk}"
    assert "editora" not in evento.actor_etiqueta


def test_THREAT_013_la_etiqueta_resuelta_se_seudonimiza_al_anonimizar(editora):
    """La etiqueta nueva (usuario = PII) la sustituye la función SECURITY DEFINER existente."""
    cuenta = editora.cuenta
    evento = registrar_evento(accion=AccionAuditoria.PUBLICAR, actor_id=cuenta.pk)
    assert evento.actor_etiqueta == "editora.uno"
    _anonimizar_en_bd(cuenta)
    assert seudonimizar_eventos_de_cuenta(cuenta.pk) == 1
    evento.refresh_from_db()
    assert evento.actor_etiqueta == f"{PREFIJO_SEUDONIMO}{cuenta.pk}"
    assert not EventoAuditoria.objects.filter(actor_etiqueta="editora.uno").exists()
