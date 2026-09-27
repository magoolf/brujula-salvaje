"""DEC-AUTO-215 / CHG-API-002 (OBS-QA004-06): iniciar la activación de MFA exige la contraseña.

POST /api/v1/panel/auth/mfa/activacion (panelIniciarActivacionMfa), también con paso pendiente
CONFIGURAR_MFA: sin cuerpo → 400; contraseña incorrecta → 401 credenciales_invalidas sin cerrar
la sesión y auditada como LOGIN_FALLIDO; 5 fallos → 429 con Retry-After; correcta → 200 con
otpauth_uri; MFA activo → 409; sin CSRF → 403 csrf_invalido.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.auditoria.models import EventoAuditoria
from apps.cuentas import mfa
from apps.cuentas.models import CuentaStaff, EstadoCuenta, RolCuenta
from apps.cuentas.tests.conftest import BASE, CONTRASENA, IP, crear_staff, entrar, post, problema

pytestmark = pytest.mark.django_db
RUTA = "/auth/mfa/activacion"


def test_DEC_AUTO_215_sin_cuerpo_o_con_campos_invalidos_es_400(cliente_editora):
    assert "contrasena" in problema(post(cliente_editora, RUTA), 400, "validacion")["errors"]
    assert (
        "contrasena"
        in problema(post(cliente_editora, RUTA, {"contrasena": ""}), 400, "validacion")["errors"]
    )
    assert (
        "contrasena"
        in problema(post(cliente_editora, RUTA, {"contrasena": "x" * 129}), 400, "validacion")[
            "errors"
        ]
    )
    assert (
        "contrasena"
        in problema(post(cliente_editora, RUTA, {"contrasena": "con\x00nul"}), 400, "validacion")[
            "errors"
        ]
    )
    problema(
        post(cliente_editora, RUTA, {"contrasena": CONTRASENA, "otro": 1}),
        400,
        "campo_no_permitido",
    )


def test_DEC_AUTO_215_contrasena_incorrecta_401_sin_cerrar_la_sesion(
    cliente_editora, editora, logs_json
):
    clave = cliente_editora.cookies["sessionid"].value
    respuesta = post(cliente_editora, RUTA, {"contrasena": "no-es-la-mia"}, REMOTE_ADDR=IP)
    problema(respuesta, 401, "credenciales_invalidas")
    # La sesión sigue válida y no se rota.
    assert cliente_editora.get(f"{BASE}/auth/sesion").status_code == 200
    assert cliente_editora.cookies["sessionid"].value == clave
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.intentos_fallidos == 1
    assert editora.cuenta.secreto_mfa is None
    evento = EventoAuditoria.objects.filter(accion="LOGIN_FALLIDO", actor=editora.cuenta).get()
    assert evento.resultado == "FALLO"
    assert evento.ip_truncada == "203.0.113.0/24"
    assert "no-es-la-mia" not in logs_json.texto()  # el cuerpo nunca se registra


def test_DEC_AUTO_215_cinco_fallos_bloquean_con_retry_after(cliente_editora, editora):
    for _ in range(4):
        problema(post(cliente_editora, RUTA, {"contrasena": "mal"}), 401, "credenciales_invalidas")
    quinto = post(cliente_editora, RUTA, {"contrasena": "mal"})
    problema(quinto, 429, "acceso_bloqueado_temporalmente")
    assert int(quinto["Retry-After"]) > 14 * 60
    # Bloqueada, ni siquiera la contraseña correcta sirve; el login tampoco.
    problema(
        post(cliente_editora, RUTA, {"contrasena": CONTRASENA}),
        429,
        "acceso_bloqueado_temporalmente",
    )
    login = post(
        Client(),
        "/auth/login",
        {"usuario": "editora.uno", "contrasena": CONTRASENA},
        REMOTE_ADDR=IP,
    )
    problema(login, 429, "acceso_bloqueado_temporalmente")
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.estado == EstadoCuenta.BLOQUEADA_TEMPORAL
    assert EventoAuditoria.objects.filter(accion="BLOQUEO", actor=editora.cuenta).count() == 1


def test_DEC_AUTO_215_correcta_devuelve_uri_y_sustituye_el_secreto_provisional(
    cliente_editora, editora
):
    primero = post(cliente_editora, RUTA, {"contrasena": CONTRASENA})
    assert primero.status_code == 200
    cuerpo = primero.json()
    assert cuerpo["otpauth_uri"].startswith("otpauth://totp/")
    assert cuerpo["clave_secreta"] not in cuerpo["otpauth_uri"].split("secret=")[0]
    segundo = post(cliente_editora, RUTA, {"contrasena": CONTRASENA}).json()["clave_secreta"]
    assert segundo != cuerpo["clave_secreta"]
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.mfa_activo is False  # no se activa hasta confirmar
    assert mfa.descifrar_secreto(editora.cuenta.secreto_mfa) == segundo
    # El código del primer secreto (descartado) ya no confirma la activación.
    viejo = mfa.codigo_totp(cuerpo["clave_secreta"], mfa.periodo_actual())
    nuevo = mfa.codigo_totp(segundo, mfa.periodo_actual())
    if viejo != nuevo:
        problema(
            post(cliente_editora, "/auth/mfa/activacion/confirmar", {"codigo": viejo}),
            400,
            "validacion",
        )
    assert (
        post(cliente_editora, "/auth/mfa/activacion/confirmar", {"codigo": nuevo}).status_code
        == 200
    )


def test_DEC_AUTO_215_con_mfa_activo_409(admin):
    cliente = Client(raise_request_exception=False)
    entrar(cliente, admin)
    problema(post(cliente, RUTA, {"contrasena": CONTRASENA}), 409, "transicion_invalida")
    admin.cuenta.refresh_from_db()
    assert admin.cuenta.intentos_fallidos == 0


def test_DEC_AUTO_215_tambien_con_paso_configurar_mfa(cliente):
    crear_staff("admin.sin.mfa", rol=RolCuenta.ADMINISTRADOR, con_mfa=False)
    paso = post(
        cliente,
        "/auth/login",
        {"usuario": "admin.sin.mfa", "contrasena": CONTRASENA},
        REMOTE_ADDR=IP,
    )
    assert paso.json()["paso_pendiente"] == "CONFIGURAR_MFA"
    problema(post(cliente, RUTA, {"contrasena": "mal"}), 401, "credenciales_invalidas")
    assert cliente.get(f"{BASE}/auth/sesion").json()["paso_pendiente"] == "CONFIGURAR_MFA"
    assert post(cliente, RUTA, {"contrasena": CONTRASENA}).status_code == 200
    assert CuentaStaff.objects.get(usuario="admin.sin.mfa").secreto_mfa is not None


def test_DEC_AUTO_215_sin_csrf_403(editora):
    cliente = Client(enforce_csrf_checks=True, raise_request_exception=False)
    token = cliente.get(f"{BASE}/auth/csrf").cookies["csrftoken"].value
    datos = {"usuario": "editora.uno", "contrasena": CONTRASENA}
    assert post(cliente, "/auth/login", datos, HTTP_X_CSRFTOKEN=token).status_code == 200
    problema(post(cliente, RUTA, {"contrasena": CONTRASENA}), 403, "csrf_invalido")
    assert (
        post(cliente, RUTA, {"contrasena": CONTRASENA}, HTTP_X_CSRFTOKEN=token).status_code == 200
    )
