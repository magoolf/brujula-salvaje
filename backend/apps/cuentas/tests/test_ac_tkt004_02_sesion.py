"""AC-TKT004-02: sesión del panel (ADR-API-001 §2 y §5, DEC-AUTO-049/089/101).

Cookies con sus atributos, CSRF obligatorio en métodos no seguros, rotación del identificador,
expiración por inactividad (30 min) y absoluta (12 h), y logout que invalida en sesion_panel.
Trazabilidad: FEAT-029, STATE-004, AC-107, AC-109, AC-119, RULE-029; THREAT-002, THREAT-003.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.cuentas.autenticacion import CLAVE_ULTIMA_ACTIVIDAD
from apps.cuentas.models import SesionPanel
from apps.cuentas.sesiones import CLAVE_AUTENTICADO_EN, SessionStore
from apps.cuentas.tests.conftest import BASE, CONTRASENA, IP, entrar, post, problema

pytestmark = pytest.mark.django_db

NUEVA = "otra-frase-bastante-larga-para-el-panel"


def _clave(cliente: Client) -> str:
    return cliente.cookies["sessionid"].value


def _mover_en_el_tiempo(cliente: Client, **campos: timedelta) -> None:
    """Retrasa las marcas de la sesión (simula el paso del tiempo)."""
    tienda = SessionStore(session_key=_clave(cliente))
    for clave, delta in campos.items():
        tienda[clave] = (datetime.fromisoformat(tienda[clave]) - delta).isoformat()
    tienda.save()


def test_AC_TKT004_02_cookie_de_sesion_con_atributos_del_adr(cliente, editora):
    respuesta = entrar(cliente, editora)
    cookie = respuesta.cookies["sessionid"]
    assert cookie["httponly"] is True
    assert cookie["secure"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["path"] == "/api/v1/panel/"
    fila = SesionPanel.objects.get(session_key=cookie.value)
    assert fila.cuenta_id == editora.cuenta.pk
    assert fila.autenticado_en is not None
    # La expiración de la fila es la de inactividad (<= 30 min).
    assert fila.expire_date <= timezone.now() + timedelta(minutes=30, seconds=5)


def test_AC_TKT004_02_respuestas_del_panel_no_store_y_noindex(cliente_editora):
    respuesta = cliente_editora.get(f"{BASE}/auth/sesion")
    assert respuesta["Cache-Control"] == "no-store"
    assert respuesta["X-Robots-Tag"] == "noindex, nofollow"
    assert "frame-ancestors 'none'" in respuesta["Content-Security-Policy"]


def test_AC_TKT004_02_rutas_publicas_no_fijan_cookies(cliente):
    respuesta = cliente.get("/health/live")
    assert not respuesta.cookies
    assert "Vary" not in respuesta or "Cookie" not in respuesta["Vary"]


# ---------------------------------------------------------------------------
# CSRF (THREAT-003)
# ---------------------------------------------------------------------------
def test_AC_TKT004_02_csrf_obligatorio_en_login_y_operaciones_de_cambio(editora):
    cliente = Client(enforce_csrf_checks=True, raise_request_exception=False)
    datos = {"usuario": "editora.uno", "contrasena": CONTRASENA}
    problema(post(cliente, "/auth/login", datos), 403, "csrf_invalido")
    token = cliente.get(f"{BASE}/auth/csrf").cookies["csrftoken"].value
    problema(post(cliente, "/auth/login", datos, HTTP_X_CSRFTOKEN="token-falso"), 403, "csrf_invalido")
    assert post(cliente, "/auth/login", datos, HTTP_X_CSRFTOKEN=token).status_code == 200
    # Con sesión: sin cabecera → 403; GET no la necesita.
    problema(post(cliente, "/auth/sesion/renovar"), 403, "csrf_invalido")
    problema(post(cliente, "/auth/logout"), 403, "csrf_invalido")
    assert cliente.get(f"{BASE}/auth/sesion").status_code == 200
    assert post(cliente, "/auth/logout", HTTP_X_CSRFTOKEN=token).status_code == 204


def test_AC_TKT004_02_csrf_rechaza_origen_no_confiable(editora):
    cliente = Client(enforce_csrf_checks=True, raise_request_exception=False)
    token = cliente.get(f"{BASE}/auth/csrf").cookies["csrftoken"].value
    respuesta = post(
        cliente,
        "/auth/login",
        {"usuario": "editora.uno", "contrasena": CONTRASENA},
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="https://malicioso.example",
    )
    problema(respuesta, 403, "csrf_invalido")


# ---------------------------------------------------------------------------
# Rotación del identificador (THREAT-002)
# ---------------------------------------------------------------------------
def test_AC_TKT004_02_rota_la_sesion_al_autenticarse_verificar_mfa_y_cambiar_contrasena(admin):
    cliente = Client(raise_request_exception=False)
    post(cliente, "/auth/login", {"usuario": "admin.principal", "contrasena": CONTRASENA}, REMOTE_ADDR=IP)
    parcial = _clave(cliente)
    assert post(cliente, "/auth/mfa/verificar", {"codigo": admin.codigo()}).status_code == 200
    completa = _clave(cliente)
    assert completa != parcial
    assert not SesionPanel.objects.filter(session_key=parcial).exists()

    # Un segundo login rota otra vez; la sesión anterior deja de existir.
    entrar(cliente, admin, desplazamiento=1)
    assert _clave(cliente) != completa
    assert not SesionPanel.objects.filter(session_key=completa).exists()

    antes = _clave(cliente)
    respuesta = post(cliente, "/auth/contrasena", {"contrasena_actual": CONTRASENA, "contrasena_nueva": NUEVA})
    assert respuesta.status_code == 200
    assert _clave(cliente) != antes


def test_AC_TKT004_02_cambiar_contrasena_invalida_las_otras_sesiones(editora):
    uno = Client(raise_request_exception=False)
    dos = Client(raise_request_exception=False)
    entrar(uno, editora)
    entrar(dos, editora)
    assert SesionPanel.objects.filter(cuenta=editora.cuenta).count() == 2
    post(uno, "/auth/contrasena", {"contrasena_actual": CONTRASENA, "contrasena_nueva": NUEVA})
    assert SesionPanel.objects.filter(cuenta=editora.cuenta).count() == 1
    problema(dos.get(f"{BASE}/auth/sesion"), 401, "no_autenticado")
    assert uno.get(f"{BASE}/auth/sesion").status_code == 200


# ---------------------------------------------------------------------------
# Expiración (AC-109)
# ---------------------------------------------------------------------------
def test_AC_TKT004_02_expira_por_inactividad_a_los_30_min(cliente_editora):
    clave = _clave(cliente_editora)
    _mover_en_el_tiempo(cliente_editora, **{CLAVE_ULTIMA_ACTIVIDAD: timedelta(minutes=31)})
    problema(cliente_editora.get(f"{BASE}/auth/sesion"), 401, "sesion_expirada")
    assert not SesionPanel.objects.filter(session_key=clave).exists()
    problema(cliente_editora.get(f"{BASE}/auth/sesion"), 401, "no_autenticado")


def test_AC_TKT004_02_expira_a_las_12_h_aunque_haya_actividad(cliente_editora):
    _mover_en_el_tiempo(cliente_editora, **{CLAVE_AUTENTICADO_EN: timedelta(hours=12, seconds=1)})
    problema(post(cliente_editora, "/auth/sesion/renovar"), 401, "sesion_expirada")


def test_AC_TKT004_02_consultar_no_renueva_y_renovar_si(cliente_editora):
    _mover_en_el_tiempo(cliente_editora, **{CLAVE_ULTIMA_ACTIVIDAD: timedelta(minutes=10)})
    antes = cliente_editora.get(f"{BASE}/auth/sesion").json()
    despues = cliente_editora.get(f"{BASE}/auth/sesion").json()
    assert antes["expira_inactividad_en"] == despues["expira_inactividad_en"]
    renovada = post(cliente_editora, "/auth/sesion/renovar").json()
    assert renovada["expira_inactividad_en"] > antes["expira_inactividad_en"]
    assert renovada["expira_absoluta_en"] == antes["expira_absoluta_en"]


def test_AC_TKT004_02_renovar_nunca_supera_las_12_h(cliente_editora):
    _mover_en_el_tiempo(cliente_editora, **{CLAVE_AUTENTICADO_EN: timedelta(hours=11, minutes=50)})
    post(cliente_editora, "/auth/sesion/renovar")
    fila = SesionPanel.objects.get(session_key=_clave(cliente_editora))
    estado = cliente_editora.get(f"{BASE}/auth/sesion").json()
    absoluta = datetime.fromisoformat(estado["expira_absoluta_en"].replace("Z", "+00:00"))
    assert fila.expire_date <= absoluta + timedelta(seconds=1)


def test_AC_TKT004_02_expiracion_de_login_no_bloquea_un_nuevo_acceso(cliente_editora, editora):
    _mover_en_el_tiempo(cliente_editora, **{CLAVE_ULTIMA_ACTIVIDAD: timedelta(hours=1)})
    assert entrar(cliente_editora, editora).status_code == 200


# ---------------------------------------------------------------------------
# Logout (FLOW-010 paso 8)
# ---------------------------------------------------------------------------
def test_AC_TKT004_02_logout_invalida_en_sesion_panel(cliente_editora, editora):
    clave = _clave(cliente_editora)
    respuesta = post(cliente_editora, "/auth/logout", REMOTE_ADDR=IP)
    assert respuesta.status_code == 204
    assert respuesta.cookies["sessionid"].value == ""
    assert not SesionPanel.objects.filter(session_key=clave).exists()
    evento = EventoAuditoria.objects.get(accion="LOGOUT")
    assert evento.actor_id == editora.cuenta.pk
    assert evento.ip_truncada == "203.0.113.0/24"
    # Reutilizar la cookie antigua no sirve (la sesión ya no existe en el servidor).
    viejo = Client(raise_request_exception=False)
    viejo.cookies["sessionid"] = clave
    problema(viejo.get(f"{BASE}/auth/sesion"), 401, "no_autenticado")


def test_AC_TKT004_02_sin_sesion_el_panel_responde_401(cliente):
    problema(cliente.get(f"{BASE}/auth/sesion"), 401, "no_autenticado")
    problema(post(cliente, "/auth/logout"), 401, "no_autenticado")
    problema(post(cliente, "/auth/mfa/verificar", {"codigo": "123456"}), 401, "no_autenticado")


def test_AC_TKT004_02_sesion_con_datos_corruptos_es_anonima(cliente):
    tienda = SessionStore()
    tienda["panel_cuenta_id"] = "no-es-un-id"
    tienda.create()
    cliente.cookies["sessionid"] = tienda.session_key
    problema(cliente.get(f"{BASE}/auth/sesion"), 401, "no_autenticado")
