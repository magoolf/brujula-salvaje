"""TKT-034: permisos del panel (apps.cuentas.permisos).

Deny-by-default por paso pendiente de la sesión (STATE-004, Blueprint §12), códigos del contrato
por paso, sesión expirada frente a anónima, cálculo del paso una sola vez por petición y su
recálculo tras cambiar la cuenta, y rol de Administrador leído de la BD (THREAT-004, AC-105).
Trazabilidad: TKT-OPS-022 (módulo crítico > 95 %), Skill_Backend §8.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.db import connection
from django.test import Client, RequestFactory
from django.test.utils import CaptureQueriesContext
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.exceptions import ErrorApi
from apps.cuentas.autenticacion import ATRIBUTO_EXPIRADA, abrir_sesion
from apps.cuentas.models import CuentaStaff, RolCuenta
from apps.cuentas.permisos import (
    CODIGO_POR_PASO,
    TODOS_LOS_PASOS,
    SesionPanel,
    SoloAdministrador,
    cuenta_de,
    olvidar_paso,
    paso_de,
)
from apps.cuentas.services import Paso
from apps.cuentas.sesiones import SessionStore
from apps.cuentas.tests.conftest import BASE, Staff, crear_staff, entrar, problema

pytestmark = pytest.mark.django_db


def _peticion(
    cuenta: CuentaStaff | None = None,
    *,
    mfa_verificado: bool = True,
    expirada: bool = False,
    metodo: str = "get",
    **extra: Any,
) -> Request:
    """Petición DRF tal como la deja AutenticacionSesionPanel (cuenta o anónima + sesión)."""
    peticion = getattr(RequestFactory(), metodo)(f"{BASE}/prueba", **extra)
    peticion.session = SessionStore()
    if cuenta is not None:
        abrir_sesion(peticion.session, cuenta, mfa_verificado=mfa_verificado, redireccion="/panel")
    if expirada:
        setattr(peticion, ATRIBUTO_EXPIRADA, True)
    drf = Request(peticion)
    drf.user = cuenta  # anónima: None (UNAUTHENTICATED_USER de los settings)
    return drf


class _Vista(APIView):
    """Vista sin pasos_permitidos declarados: rige el valor por defecto (solo NINGUNO)."""


def _vista(pasos: frozenset[Paso] | None = None) -> APIView:
    vista = _Vista()
    if pasos is not None:
        vista.pasos_permitidos = pasos  # type: ignore[attr-defined]
    return vista


def _codigo(error: pytest.ExceptionInfo[ErrorApi]) -> tuple[int, str]:
    return error.value.status_code, error.value.codigo


# Cuenta que deja la sesión en cada paso pendiente (orden SCR-030 -> 031 -> 032 -> 033).
_CUENTA_POR_PASO: dict[Paso, dict[str, Any]] = {
    Paso.NINGUNO: {},
    Paso.MFA: {"con_mfa": True},
    Paso.CAMBIO_CREDENCIAL: {"debe_cambiar": True},
    Paso.CONFIGURAR_MFA: {"rol": RolCuenta.ADMINISTRADOR, "con_mfa": False},
    Paso.AUTORIZACION: {},  # autorizó una versión anterior de la política (ver abajo)
}


def _peticion_en_paso(paso: Paso) -> Request:
    staff = crear_staff(f"cuenta.{paso.lower()}", **_CUENTA_POR_PASO[paso])
    if paso is Paso.AUTORIZACION:
        CuentaStaff.objects.filter(pk=staff.cuenta.pk).update(autorizacion_version_politica="0.1")
        staff.cuenta.refresh_from_db()
    return _peticion(staff.cuenta, mfa_verificado=paso != Paso.MFA)


# ---------------------------------------------------------------------------
# cuenta_de: anónima frente a expirada
# ---------------------------------------------------------------------------
def test_TKT034_cuenta_de_devuelve_la_cuenta_autenticada(editora: Staff):
    assert cuenta_de(_peticion(editora.cuenta)) == editora.cuenta


def test_TKT034_sin_cuenta_responde_no_autenticado():
    with pytest.raises(ErrorApi) as error:
        cuenta_de(_peticion())
    assert _codigo(error) == (401, "no_autenticado")


def test_TKT034_con_la_sesion_recien_expirada_responde_sesion_expirada():
    with pytest.raises(ErrorApi) as error:
        cuenta_de(_peticion(expirada=True))
    assert _codigo(error) == (401, "sesion_expirada")


def test_TKT034_una_sesion_con_cuenta_que_no_se_autentico_no_pasa(editora: Staff):
    # La sesión guarda la cuenta, pero la autenticación la descartó (p. ej. desactivada).
    peticion = _peticion(editora.cuenta)
    peticion.user = None
    with pytest.raises(ErrorApi) as error:
        cuenta_de(peticion)
    assert _codigo(error) == (401, "no_autenticado")


# ---------------------------------------------------------------------------
# paso_de / olvidar_paso
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("paso", list(Paso), ids=[p.value for p in Paso])
def test_TKT034_el_paso_pendiente_se_deriva_de_la_cuenta_y_la_sesion(paso: Paso):
    assert paso_de(_peticion_en_paso(paso)) is paso


def test_TKT034_sin_mfa_verificado_en_la_sesion_el_paso_es_mfa(admin: Staff):
    assert paso_de(_peticion(admin.cuenta, mfa_verificado=False)) is Paso.MFA
    assert paso_de(_peticion(admin.cuenta, mfa_verificado=True)) is Paso.NINGUNO


def test_TKT034_el_paso_se_calcula_una_vez_por_peticion_y_se_recalcula_al_olvidarlo(
    editora: Staff,
):
    peticion = _peticion(editora.cuenta)
    assert paso_de(peticion) is Paso.NINGUNO

    # La cuenta cambia durante la petición (p. ej. un administrador fuerza el cambio).
    CuentaStaff.objects.filter(pk=editora.cuenta.pk).update(debe_cambiar_credencial=True)
    editora.cuenta.debe_cambiar_credencial = True
    with CaptureQueriesContext(connection) as consultas:
        assert paso_de(peticion) is Paso.NINGUNO  # memorizado: sin consultas
    assert len(consultas) == 0

    olvidar_paso(peticion)
    assert paso_de(peticion) is Paso.CAMBIO_CREDENCIAL


def test_TKT034_olvidar_el_paso_sin_haberlo_calculado_no_falla(editora: Staff):
    peticion = _peticion(editora.cuenta)
    olvidar_paso(peticion)
    olvidar_paso(peticion)
    assert paso_de(peticion) is Paso.NINGUNO


def test_TKT034_paso_de_sin_cuenta_responde_no_autenticado():
    with pytest.raises(ErrorApi) as error:
        paso_de(_peticion())
    assert _codigo(error) == (401, "no_autenticado")


# ---------------------------------------------------------------------------
# SesionPanel: deny-by-default por paso
# ---------------------------------------------------------------------------
def test_TKT034_todos_los_pasos_tienen_codigo_del_contrato():
    assert frozenset(CODIGO_POR_PASO) == TODOS_LOS_PASOS == frozenset(Paso)


def test_TKT034_sin_pasos_pendientes_la_vista_por_defecto_permite(editora: Staff):
    assert SesionPanel().has_permission(_peticion(editora.cuenta), _vista()) is True


@pytest.mark.parametrize(
    ("paso", "esperado"),
    [
        (Paso.MFA, (401, "mfa_requerido")),
        (Paso.CAMBIO_CREDENCIAL, (403, "cambio_credencial_requerido")),
        (Paso.CONFIGURAR_MFA, (403, "configuracion_mfa_requerida")),
        (Paso.AUTORIZACION, (403, "autorizacion_requerida")),
    ],
    ids=lambda v: v.value if isinstance(v, Paso) else v[1],
)
def test_TKT034_con_un_paso_pendiente_la_vista_por_defecto_deniega_con_su_codigo(
    paso: Paso, esperado: tuple[int, str]
):
    with pytest.raises(ErrorApi) as error:
        SesionPanel().has_permission(_peticion_en_paso(paso), _vista())
    assert _codigo(error) == esperado


def test_TKT034_una_vista_de_paso_intermedio_deniega_a_quien_no_tiene_ese_paso(editora: Staff):
    with pytest.raises(ErrorApi) as error:
        SesionPanel().has_permission(_peticion(editora.cuenta), _vista(frozenset({Paso.MFA})))
    assert _codigo(error) == (403, "permiso_denegado")


@pytest.mark.parametrize("paso", list(Paso), ids=[p.value for p in Paso])
def test_TKT034_una_vista_de_todos_los_pasos_permite_cualquier_paso(paso: Paso):
    assert SesionPanel().has_permission(_peticion_en_paso(paso), _vista(TODOS_LOS_PASOS))


def test_TKT034_sesion_panel_sin_sesion_deniega_aunque_la_vista_admita_todos_los_pasos():
    with pytest.raises(ErrorApi) as error:
        SesionPanel().has_permission(_peticion(expirada=True), _vista(TODOS_LOS_PASOS))
    assert _codigo(error) == (401, "sesion_expirada")


# ---------------------------------------------------------------------------
# SoloAdministrador: el rol sale de la BD, nunca de la petición (THREAT-004)
# ---------------------------------------------------------------------------
def test_TKT034_solo_administrador_permite_al_administrador(admin: Staff):
    assert SoloAdministrador().has_permission(_peticion(admin.cuenta), _vista()) is True


def test_TKT034_solo_administrador_deniega_a_la_editora_aunque_la_peticion_diga_admin(
    editora: Staff,
):
    peticion = _peticion(
        editora.cuenta,
        metodo="post",
        data={"rol": RolCuenta.ADMINISTRADOR, "es_administrador": True},
        content_type="application/json",
        HTTP_X_ROL=RolCuenta.ADMINISTRADOR,
    )
    with pytest.raises(ErrorApi) as error:
        SoloAdministrador().has_permission(peticion, _vista())
    assert _codigo(error) == (403, "permiso_denegado")


def test_TKT034_solo_administrador_sin_cuenta_responde_no_autenticado():
    with pytest.raises(ErrorApi) as error:
        SoloAdministrador().has_permission(_peticion(), _vista())
    assert _codigo(error) == (401, "no_autenticado")


def test_TKT034_un_administrador_degradado_pierde_el_acceso_en_la_siguiente_peticion(
    admin: Staff,
):
    crear_staff("admin.segunda", rol=RolCuenta.ADMINISTRADOR)  # siempre queda un administrador
    cliente = Client(raise_request_exception=False)
    entrar(cliente, admin)
    assert cliente.get(f"{BASE}/cuentas").status_code == 200

    CuentaStaff.objects.filter(pk=admin.cuenta.pk).update(rol=RolCuenta.EDITOR)

    problema(cliente.get(f"{BASE}/cuentas"), 403, "permiso_denegado")
