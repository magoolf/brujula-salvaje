"""Fixtures y utilidades de las pruebas de acceso al panel y cuentas (TKT-004).

Todas las cuentas y contraseñas son ficticias. La política vigente es la de respaldo de los
settings ("1.0") salvo que una prueba cree la página POLITICA_DATOS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from django.conf import settings
from django.test import Client
from django.utils import timezone

from apps.cuentas import mfa
from apps.cuentas.models import CuentaStaff, EstadoCuenta, RolCuenta

CONTRASENA = "frase-de-prueba-muy-larga-2026"
IP = "203.0.113.77"
RED_IP = "203.0.113.0/24"
BASE = "/api/v1/panel"


@dataclass
class Staff:
    cuenta: CuentaStaff
    contrasena: str
    secreto: str | None = None

    def codigo(self, desplazamiento: int = 0) -> str:
        assert self.secreto is not None
        return mfa.codigo_totp(self.secreto, mfa.periodo_actual() + desplazamiento)


def crear_staff(
    usuario: str,
    *,
    rol: str = RolCuenta.EDITOR,
    estado: str = EstadoCuenta.ACTIVA,
    con_mfa: bool | None = None,
    debe_cambiar: bool = False,
    autorizada: bool = True,
    contrasena: str = CONTRASENA,
) -> Staff:
    """Cuenta lista para entrar. Un Administrador lleva MFA por defecto (DEC-AUTO-119)."""
    if con_mfa is None:
        con_mfa = rol == RolCuenta.ADMINISTRADOR
    cuenta = CuentaStaff(
        usuario=usuario,
        nombre_visible=f"Nombre de {usuario}",
        rol=rol,
        estado=estado,
        debe_cambiar_credencial=debe_cambiar,
    )
    if autorizada:
        cuenta.autorizacion_otorgada_en = timezone.now()
        cuenta.autorizacion_version_politica = settings.POLITICA_TRATAMIENTO_VERSION_RESPALDO
    secreto = None
    if con_mfa:
        secreto = mfa.nuevo_secreto()
        cuenta.secreto_mfa = mfa.cifrar_secreto(secreto)
        cuenta.mfa_activo = True
    if estado in (EstadoCuenta.DESACTIVADA, EstadoCuenta.ANONIMIZADA):
        cuenta.desactivado_en = timezone.now()
    cuenta.set_password(contrasena)
    cuenta.save()
    return Staff(cuenta=cuenta, contrasena=contrasena, secreto=secreto)


def entrar(cliente: Client, staff: Staff, desplazamiento: int = 0, **extra: Any) -> Any:
    """Login completo (con el segundo factor si la cuenta lo tiene).

    Un mismo código TOTP no se acepta dos veces: para volver a entrar con la misma cuenta en una
    prueba se usa un periodo posterior de la ventana (desplazamiento=1).
    """
    respuesta = cliente.post(
        f"{BASE}/auth/login",
        {"usuario": staff.cuenta.usuario, "contrasena": staff.contrasena, **extra},
        content_type="application/json",
        REMOTE_ADDR=IP,
    )
    assert respuesta.status_code == 200, respuesta.content
    if respuesta.json()["paso_pendiente"] == "MFA":
        respuesta = cliente.post(
            f"{BASE}/auth/mfa/verificar",
            {"codigo": staff.codigo(desplazamiento)},
            content_type="application/json",
            REMOTE_ADDR=IP,
        )
        assert respuesta.status_code == 200, respuesta.content
    return respuesta


def problema(respuesta: Any, estado: int, codigo: str) -> dict[str, Any]:
    assert respuesta.status_code == estado, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
    cuerpo: dict[str, Any] = respuesta.json()
    assert cuerpo["code"] == codigo, cuerpo
    assert cuerpo["trace_id"] == respuesta["X-Trace-Id"]
    return cuerpo


def post(cliente: Client, ruta: str, datos: Any = None, **extra: Any) -> Any:
    return cliente.post(
        f"{BASE}{ruta}", datos if datos is not None else {}, content_type="application/json", **extra
    )


@pytest.fixture
def admin(db: Any) -> Staff:
    return crear_staff("admin.principal", rol=RolCuenta.ADMINISTRADOR)


@pytest.fixture
def editora(db: Any) -> Staff:
    return crear_staff("editora.uno")


@pytest.fixture
def cliente_admin(admin: Staff) -> Client:
    cliente = Client(raise_request_exception=False)
    entrar(cliente, admin)
    return cliente


@pytest.fixture
def cliente_editora(editora: Staff) -> Client:
    cliente = Client(raise_request_exception=False)
    entrar(cliente, editora)
    return cliente
