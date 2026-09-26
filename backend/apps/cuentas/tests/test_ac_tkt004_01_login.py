"""AC-TKT004-01: login por pasos, anti enumeración y bloqueo progresivo.

Trazabilidad: FEAT-029..032, FLOW-010, STATE-003/004, RULE-017, AC-029, AC-055, AC-056, AC-106,
AC-115; THREAT-001, THREAT-017, THREAT-018, THREAT-020, THREAT-027.
"""

from __future__ import annotations

import base64
import statistics
import time
from datetime import date, timedelta

import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.contenido.models import PaginaInstitucional
from apps.contenido.tests.fabricas import crear_contenido
from apps.cuentas import mfa, services
from apps.cuentas.models import CuentaCodigoRecuperacion, CuentaStaff, EstadoCuenta, RolCuenta
from apps.cuentas.tests.conftest import (
    BASE,
    CONTRASENA,
    IP,
    RED_IP,
    crear_staff,
    entrar,
    post,
    problema,
)

pytestmark = pytest.mark.django_db

NUEVA = "otra-frase-bastante-larga-para-el-panel"


def _login(cliente, usuario, contrasena, **extra):
    return post(
        cliente, "/auth/login", {"usuario": usuario, "contrasena": contrasena, **extra}, REMOTE_ADDR=IP
    )


# ---------------------------------------------------------------------------
# Login por pasos completo (credencial → MFA → cambio → autorización)
# ---------------------------------------------------------------------------
def test_AC_TKT004_01_login_simple_editora_activa(cliente, editora, logs_json):
    respuesta = _login(cliente, "editora.uno", CONTRASENA, siguiente="/panel/contenidos/destinos")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["paso_pendiente"] == "NINGUNO"
    assert cuerpo["usuario"] == "editora.uno"
    assert cuerpo["rol"] == "EDITOR"
    assert cuerpo["mfa_obligatorio"] is False
    assert cuerpo["redireccion"] == "/panel/contenidos/destinos"
    evento = EventoAuditoria.objects.get(accion="LOGIN_OK")
    assert evento.actor_id == editora.cuenta.pk
    assert evento.ip_truncada == RED_IP
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.last_login is not None
    # THREAT-020: ni la contraseña ni el cuerpo del login llegan a los logs.
    assert CONTRASENA not in logs_json.texto()


def test_AC_TKT004_01_flujo_completo_cuenta_nueva_de_editor(cliente_admin):
    alta = post(cliente_admin, "/cuentas", {"usuario": "nuevo.editor", "nombre_visible": "Nuevo", "rol": "EDITOR"})
    assert alta.status_code == 201
    temporal = alta.json()["contrasena_temporal"]
    nuevo = Client(raise_request_exception=False)

    paso = _login(nuevo, "nuevo.editor", temporal).json()
    assert paso["paso_pendiente"] == "CAMBIO_CREDENCIAL"
    # Mientras haya paso pendiente, el resto del panel responde el código del paso.
    problema(post(nuevo, "/auth/mfa/activacion"), 403, "cambio_credencial_requerido")
    problema(post(nuevo, "/auth/autorizacion", {"decision": "AUTORIZO", "version_politica": "1.0"}), 403, "cambio_credencial_requerido")

    cambio = post(nuevo, "/auth/contrasena", {"contrasena_actual": temporal, "contrasena_nueva": NUEVA})
    assert cambio.status_code == 200
    assert cambio.json()["paso_pendiente"] == "AUTORIZACION"
    problema(nuevo.get(f"{BASE}/cuentas"), 403, "autorizacion_requerida")

    politica = nuevo.get(f"{BASE}/auth/autorizacion").json()
    assert politica["version_politica"] == "1.0"
    assert politica["url_politica"] == "/politica-de-tratamiento-de-datos"
    assert politica["otorgada_en"] is None

    problema(post(nuevo, "/auth/autorizacion", {"decision": "AUTORIZO", "version_politica": "0.9"}), 409, "conflicto_version")
    final = post(nuevo, "/auth/autorizacion", {"decision": "AUTORIZO", "version_politica": "1.0"})
    assert final.status_code == 200
    assert final.json()["paso_pendiente"] == "NINGUNO"
    cuenta = CuentaStaff.objects.get(usuario="nuevo.editor")
    assert cuenta.estado == EstadoCuenta.ACTIVA
    assert cuenta.autorizacion_version_politica == "1.0"
    assert cuenta.debe_cambiar_credencial is False
    acciones = set(EventoAuditoria.objects.filter(actor=cuenta).values_list("accion", flat=True))
    assert {"LOGIN_OK", "CAMBIO_CREDENCIAL", "AUTORIZACION_ACEPTADA"} <= acciones


def test_AC_TKT004_01_flujo_completo_administrador_con_mfa_obligatorio(cliente_admin):
    alta = post(cliente_admin, "/cuentas", {"usuario": "nueva.admin", "nombre_visible": "Admin", "rol": "ADMINISTRADOR"})
    temporal = alta.json()["contrasena_temporal"]
    nueva = Client(raise_request_exception=False)
    assert _login(nueva, "nueva.admin", temporal).json()["paso_pendiente"] == "CAMBIO_CREDENCIAL"
    cambio = post(nueva, "/auth/contrasena", {"contrasena_actual": temporal, "contrasena_nueva": NUEVA})
    assert cambio.json()["paso_pendiente"] == "CONFIGURAR_MFA"
    assert cambio.json()["mfa_obligatorio"] is True
    problema(post(nueva, "/auth/autorizacion", {"decision": "AUTORIZO", "version_politica": "1.0"}), 403, "configuracion_mfa_requerida")

    inicio = post(nueva, "/auth/mfa/activacion").json()
    assert inicio["otpauth_uri"].startswith("otpauth://totp/")
    secreto = inicio["clave_secreta"]
    problema(post(nueva, "/auth/mfa/activacion/confirmar", {"codigo": "000000"}), 400, "validacion")
    codigo = mfa.codigo_totp(secreto, mfa.periodo_actual())
    confirmada = post(nueva, "/auth/mfa/activacion/confirmar", {"codigo": codigo})
    assert confirmada.status_code == 200
    codigos = confirmada.json()["codigos"]
    assert len(codigos) == 10
    cuenta = CuentaStaff.objects.get(usuario="nueva.admin")
    # Solo se guardan hashes de los códigos y el secreto cifrado (nunca en claro).
    hashes = set(CuentaCodigoRecuperacion.objects.filter(cuenta=cuenta).values_list("hash_codigo", flat=True))
    assert not set(codigos) & hashes
    assert secreto.encode() not in bytes(cuenta.secreto_mfa)

    assert nueva.get(f"{BASE}/auth/sesion").json()["paso_pendiente"] == "AUTORIZACION"
    assert post(nueva, "/auth/autorizacion", {"decision": "AUTORIZO", "version_politica": "1.0"}).json()["paso_pendiente"] == "NINGUNO"

    # Nuevo acceso: paso MFA; el panel responde 401 mfa_requerido hasta verificarlo.
    otra = Client(raise_request_exception=False)
    assert _login(otra, "nueva.admin", NUEVA).json()["paso_pendiente"] == "MFA"
    problema(otra.get(f"{BASE}/cuentas"), 401, "mfa_requerido")
    assert otra.get(f"{BASE}/auth/sesion").json()["paso_pendiente"] == "MFA"
    problema(post(otra, "/auth/mfa/verificar", {"codigo": "123456"}), 401, "mfa_invalido")
    # Un código de recuperación sirve una sola vez.
    assert post(otra, "/auth/mfa/verificar", {"codigo": codigos[0]}).json()["paso_pendiente"] == "NINGUNO"
    tercera = Client(raise_request_exception=False)
    _login(tercera, "nueva.admin", NUEVA)
    problema(post(tercera, "/auth/mfa/verificar", {"codigo": codigos[0]}), 401, "mfa_invalido")
    assert post(tercera, "/auth/mfa/verificar", {"codigo": codigos[1]}).status_code == 200
    problema(post(tercera, "/auth/mfa/verificar", {"codigo": codigos[2]}), 403, "permiso_denegado")


def test_AC_TKT004_01_no_autorizo_cierra_la_sesion(cliente):
    staff = crear_staff("pendiente.autoriza", autorizada=False, estado=EstadoCuenta.PENDIENTE_ACTIVACION)
    assert _login(cliente, "pendiente.autoriza", CONTRASENA).json()["paso_pendiente"] == "AUTORIZACION"
    respuesta = post(cliente, "/auth/autorizacion", {"decision": "NO_AUTORIZO", "version_politica": "1.0"})
    assert respuesta.status_code == 204
    assert respuesta.cookies["sessionid"].value == ""
    problema(cliente.get(f"{BASE}/auth/sesion"), 401, "no_autenticado")
    staff.cuenta.refresh_from_db()
    assert staff.cuenta.autorizacion_otorgada_en is None
    assert EventoAuditoria.objects.filter(accion="LOGOUT", actor=staff.cuenta).exists()


def test_AC_TKT004_01_cambio_de_version_de_politica_pide_autorizar_de_nuevo(cliente, editora):
    contenido = crear_contenido("PAGINA")
    PaginaInstitucional.objects.create(
        contenido=contenido,
        clave="POLITICA_DATOS",
        cuerpo="<p>Política</p>",
        version_documento="2.0",
        vigente_desde=date(2026, 10, 1),
    )
    assert _login(cliente, "editora.uno", CONTRASENA).json()["paso_pendiente"] == "AUTORIZACION"
    vigente = cliente.get(f"{BASE}/auth/autorizacion").json()
    assert vigente["version_politica"] == "2.0"
    assert vigente["version_otorgada"] == "1.0"
    assert post(cliente, "/auth/autorizacion", {"decision": "AUTORIZO", "version_politica": "2.0"}).json()["paso_pendiente"] == "NINGUNO"


# ---------------------------------------------------------------------------
# Anti enumeración (THREAT-018) y cuentas no operativas
# ---------------------------------------------------------------------------
def _sin_traza(respuesta) -> dict:
    cuerpo = respuesta.json()
    cuerpo.pop("trace_id")
    return cuerpo


def test_AC_TKT004_01_misma_respuesta_para_usuario_inexistente_y_contrasena_erronea(cliente, editora):
    erronea = _login(cliente, "editora.uno", "contrasena-incorrecta")
    inexistente = _login(cliente, "no.existe", "contrasena-incorrecta")
    desactivada = crear_staff("ya.no.esta", estado=EstadoCuenta.DESACTIVADA)
    de_baja = _login(cliente, "ya.no.esta", desactivada.contrasena)
    for respuesta in (erronea, inexistente, de_baja):
        problema(respuesta, 401, "credenciales_invalidas")
    assert _sin_traza(erronea) == _sin_traza(inexistente) == _sin_traza(de_baja)
    fallidos = EventoAuditoria.objects.filter(accion="LOGIN_FALLIDO").order_by("id")
    assert [e.actor_etiqueta for e in fallidos] == ["editora.uno", "desconocido", "ya.no.esta"]
    assert all(e.ip_truncada == RED_IP for e in fallidos)


def test_AC_TKT004_01_tiempos_equivalentes_con_y_sin_cuenta(cliente, editora):
    def medir(usuario: str) -> float:
        tiempos = []
        for _ in range(3):
            inicio = time.perf_counter()
            with pytest.raises(services.CredencialesInvalidas):
                services.iniciar_sesion(usuario, "contrasena-incorrecta", IP)
            tiempos.append(time.perf_counter() - inicio)
        return statistics.median(tiempos)

    con_cuenta = medir("editora.uno")
    sin_cuenta = medir("persona.inexistente")
    # Ambos caminos ejecutan un hash completo: la mediana no difiere en más del doble.
    assert 0.5 < con_cuenta / sin_cuenta < 2.0


def test_AC_TKT004_01_usuario_se_normaliza(cliente, editora):
    assert _login(cliente, "  Editora.UNO ", CONTRASENA).status_code == 200


# ---------------------------------------------------------------------------
# Bloqueo progresivo (DEC-AUTO-049/102, THREAT-001)
# ---------------------------------------------------------------------------
def test_AC_TKT004_01_cinco_fallos_bloquean_15_min_y_luego_30(cliente, editora):
    for _ in range(4):
        problema(_login(cliente, "editora.uno", "mal"), 401, "credenciales_invalidas")
    quinto = problema(_login(cliente, "editora.uno", "mal"), 429, "acceso_bloqueado_temporalmente")
    assert quinto["status"] == 429
    respuesta = _login(cliente, "editora.uno", CONTRASENA)  # correcta, pero bloqueada
    problema(respuesta, 429, "acceso_bloqueado_temporalmente")
    assert 14 * 60 < int(respuesta["Retry-After"]) <= 15 * 60 + 1
    cuenta = editora.cuenta
    cuenta.refresh_from_db()
    assert cuenta.estado == EstadoCuenta.BLOQUEADA_TEMPORAL
    assert cuenta.bloqueos_consecutivos == 1
    assert EventoAuditoria.objects.filter(accion="BLOQUEO", actor=cuenta).count() == 1

    # Se cumple el bloqueo: vuelve a ACTIVA; otros 5 fallos → bloqueo de 30 min. Se vacía la
    # caché de límites por IP (10/min, perfil panel-login), que si no respondería 429 limite_tasa.
    cache.clear()
    CuentaStaff.objects.filter(pk=cuenta.pk).update(bloqueado_hasta=timezone.now() - timedelta(seconds=1))
    for _ in range(4):
        problema(_login(cliente, "editora.uno", "mal"), 401, "credenciales_invalidas")
    cuenta.refresh_from_db()
    assert cuenta.estado == EstadoCuenta.ACTIVA
    respuesta = _login(cliente, "editora.uno", "mal")
    problema(respuesta, 429, "acceso_bloqueado_temporalmente")
    assert 29 * 60 < int(respuesta["Retry-After"]) <= 30 * 60 + 1

    # Cumplido el segundo bloqueo, un acceso correcto reinicia la progresión.
    cache.clear()
    CuentaStaff.objects.filter(pk=cuenta.pk).update(bloqueado_hasta=timezone.now() - timedelta(seconds=1))
    assert _login(cliente, "editora.uno", CONTRASENA).status_code == 200
    cuenta.refresh_from_db()
    assert (cuenta.intentos_fallidos, cuenta.bloqueos_consecutivos, cuenta.bloqueado_hasta) == (0, 0, None)


def test_AC_TKT004_01_limite_por_ip_en_login(cliente):
    # THREAT-001: además del bloqueo por usuario, 10 intentos/min por IP (perfil panel-login).
    for indice in range(10):
        _login(cliente, f"usuario{indice}", "mal")
    problema(_login(cliente, "otro.usuario", "mal"), 429, "limite_tasa")


def test_AC_TKT004_01_bloqueo_tambien_para_usuario_inexistente(cliente):
    respuestas = [_login(cliente, "fantasma", "mal") for _ in range(5)]
    for respuesta in respuestas[:4]:
        problema(respuesta, 401, "credenciales_invalidas")
    problema(respuestas[4], 429, "acceso_bloqueado_temporalmente")
    problema(_login(cliente, "fantasma", "mal"), 429, "acceso_bloqueado_temporalmente")
    assert EventoAuditoria.objects.filter(accion="BLOQUEO", actor__isnull=True).count() == 1


def test_AC_TKT004_01_cuenta_pendiente_bloqueada_vuelve_a_pendiente(cliente):
    staff = crear_staff("pendiente.bloq", estado=EstadoCuenta.PENDIENTE_ACTIVACION, debe_cambiar=True)
    for _ in range(5):
        _login(cliente, "pendiente.bloq", "mal")
    CuentaStaff.objects.filter(pk=staff.cuenta.pk).update(bloqueado_hasta=timezone.now() - timedelta(seconds=1))
    assert _login(cliente, "pendiente.bloq", CONTRASENA).json()["paso_pendiente"] == "CAMBIO_CREDENCIAL"
    staff.cuenta.refresh_from_db()
    assert staff.cuenta.estado == EstadoCuenta.PENDIENTE_ACTIVACION


def test_AC_TKT004_01_fallos_del_segundo_factor_cuentan_y_bloquean(cliente, admin):
    assert _login(cliente, "admin.principal", CONTRASENA).json()["paso_pendiente"] == "MFA"
    for _ in range(4):
        problema(post(cliente, "/auth/mfa/verificar", {"codigo": "000000"}), 401, "mfa_invalido")
    problema(post(cliente, "/auth/mfa/verificar", {"codigo": "000000"}), 429, "acceso_bloqueado_temporalmente")
    # El bloqueo cierra la sesión parcial.
    problema(cliente.get(f"{BASE}/auth/sesion"), 401, "no_autenticado")
    admin.cuenta.refresh_from_db()
    assert admin.cuenta.estado == EstadoCuenta.BLOQUEADA_TEMPORAL


def test_AC_TKT004_01_contrasena_correcta_no_reinicia_el_contador_si_falta_el_mfa(cliente, admin):
    _login(cliente, "admin.principal", CONTRASENA)
    post(cliente, "/auth/mfa/verificar", {"codigo": "000000"})
    _login(cliente, "admin.principal", CONTRASENA)
    admin.cuenta.refresh_from_db()
    assert admin.cuenta.intentos_fallidos == 1


def test_AC_TKT004_01_totp_no_se_reutiliza(admin):
    uno = Client(raise_request_exception=False)
    _login(uno, "admin.principal", CONTRASENA)
    codigo = admin.codigo()
    assert post(uno, "/auth/mfa/verificar", {"codigo": codigo}).status_code == 200
    dos = Client(raise_request_exception=False)
    _login(dos, "admin.principal", CONTRASENA)
    problema(post(dos, "/auth/mfa/verificar", {"codigo": codigo}), 401, "mfa_invalido")


# ---------------------------------------------------------------------------
# Redirección segura (AC-115, THREAT-017) y validación de la entrada
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("siguiente", "esperada"),
    [
        ("/panel/medios", "/panel/medios"),
        ("/panel", "/panel"),
        (None, "/panel"),
        ("https://malicioso.example/panel", "/panel"),
        ("//malicioso.example", "/panel"),
        ("/panel//malicioso.example", "/panel"),
        ("/panel/../destinos", "/panel"),
        ("/panel/%2F%2Fmal", "/panel"),
        ("/destinos", "/panel"),
        ("javascript:alert(1)", "/panel"),
    ],
)
def test_AC_TKT004_01_siguiente_solo_rutas_bajo_panel(cliente, editora, siguiente, esperada):
    respuesta = _login(cliente, "editora.uno", CONTRASENA, siguiente=siguiente)
    assert respuesta.json()["redireccion"] == esperada
    assert cliente.get(f"{BASE}/auth/sesion").json()["redireccion"] == esperada


def test_AC_TKT004_01_login_rechaza_campos_desconocidos_y_vacios(cliente, editora):
    problema(_login(cliente, "editora.uno", CONTRASENA, rol="ADMINISTRADOR"), 400, "campo_no_permitido")
    problema(post(cliente, "/auth/login", {"usuario": "", "contrasena": ""}), 400, "validacion")
    problema(post(cliente, "/auth/login", ["no", "es", "objeto"]), 400, "validacion")


# ---------------------------------------------------------------------------
# Credencial propia (FEAT-031, RULE-017)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("nueva", "campo"),
    [
        ("corta", "contrasena_nueva"),
        ("password1234", "contrasena_nueva"),  # lista local de comprometidas
        ("editora.uno-2026-larga", "contrasena_nueva"),  # contiene el usuario
        ("nombredeeditora.uno", "contrasena_nueva"),
        (CONTRASENA, "contrasena_nueva"),  # igual a la actual
    ],
)
def test_AC_TKT004_01_politica_de_contrasena(cliente_editora, nueva, campo):
    respuesta = post(cliente_editora, "/auth/contrasena", {"contrasena_actual": CONTRASENA, "contrasena_nueva": nueva})
    assert campo in problema(respuesta, 400, "validacion")["errors"]


def test_AC_TKT004_01_contrasena_actual_erronea(cliente_editora):
    respuesta = post(cliente_editora, "/auth/contrasena", {"contrasena_actual": "no-es-esta", "contrasena_nueva": NUEVA})
    assert "contrasena_actual" in problema(respuesta, 400, "validacion")["errors"]


def test_AC_TKT004_01_cambio_voluntario_de_contrasena(cliente_editora, editora):
    respuesta = post(cliente_editora, "/auth/contrasena", {"contrasena_actual": CONTRASENA, "contrasena_nueva": NUEVA})
    assert respuesta.status_code == 200
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.check_password(NUEVA)
    assert NUEVA not in editora.cuenta.password


# ---------------------------------------------------------------------------
# MFA propio (FEAT-030)
# ---------------------------------------------------------------------------
def test_AC_TKT004_01_mfa_opcional_del_editor_activar_regenerar_y_desactivar(cliente_editora, editora):
    problema(post(cliente_editora, "/auth/mfa/codigos-recuperacion", {"codigo": "123456"}), 409, "transicion_invalida")
    problema(post(cliente_editora, "/auth/mfa/activacion/confirmar", {"codigo": "123456"}), 409, "transicion_invalida")
    secreto = post(cliente_editora, "/auth/mfa/activacion").json()["clave_secreta"]
    assert post(cliente_editora, "/auth/mfa/activacion/confirmar", {"codigo": mfa.codigo_totp(secreto, mfa.periodo_actual())}).status_code == 200
    problema(post(cliente_editora, "/auth/mfa/activacion"), 409, "transicion_invalida")
    problema(post(cliente_editora, "/auth/mfa/codigos-recuperacion", {"codigo": "000000"}), 400, "validacion")
    nuevos = post(cliente_editora, "/auth/mfa/codigos-recuperacion", {"codigo": mfa.codigo_totp(secreto, mfa.periodo_actual() + 1)})
    assert len(nuevos.json()["codigos"]) == 10
    problema(post(cliente_editora, "/auth/mfa/desactivar", {"contrasena": "mal", "codigo": nuevos.json()["codigos"][0]}), 400, "validacion")
    problema(post(cliente_editora, "/auth/mfa/desactivar", {"contrasena": CONTRASENA, "codigo": "AAAA-AAAA"}), 400, "validacion")
    assert post(cliente_editora, "/auth/mfa/desactivar", {"contrasena": CONTRASENA, "codigo": nuevos.json()["codigos"][0]}).status_code == 204
    editora.cuenta.refresh_from_db()
    assert (editora.cuenta.mfa_activo, editora.cuenta.secreto_mfa) == (False, None)
    assert not CuentaCodigoRecuperacion.objects.filter(cuenta=editora.cuenta).exists()
    acciones = list(EventoAuditoria.objects.filter(actor=editora.cuenta).values_list("accion", flat=True))
    assert "MFA_ACTIVAR" in acciones and "MFA_DESACTIVAR" in acciones
    problema(post(cliente_editora, "/auth/mfa/desactivar", {"contrasena": CONTRASENA, "codigo": "123456"}), 409, "transicion_invalida")


def test_AC_TKT004_01_administrador_no_puede_desactivar_su_mfa(cliente_admin, admin):
    respuesta = post(cliente_admin, "/auth/mfa/desactivar", {"contrasena": CONTRASENA, "codigo": admin.codigo(1)})
    problema(respuesta, 409, "mfa_obligatorio")


def test_AC_TKT004_01_totp_cumple_rfc_6238():
    # RFC 6238, apéndice B: secreto ASCII "12345678901234567890", T=59 s → 94287082 (8 dígitos).
    secreto = base64.b32encode(b"12345678901234567890").decode()
    assert mfa.codigo_totp(secreto, 59 // 30) == "287082"
    assert mfa.verificar_totp(secreto, "287082", instante=59) == 1
    assert mfa.verificar_totp(secreto, "287082", instante=59 + 30) == 1  # ventana ±1
    assert mfa.verificar_totp(secreto, "287082", instante=59 + 90) is None


def test_AC_TKT004_01_secreto_ilegible_no_autentica(cliente, admin, logs_json):
    CuentaStaff.objects.filter(pk=admin.cuenta.pk).update(secreto_mfa=b"no-es-fernet")
    _login(cliente, "admin.principal", CONTRASENA)
    problema(post(cliente, "/auth/mfa/verificar", {"codigo": admin.codigo()}), 401, "mfa_invalido")
    assert "mfa_secreto_ilegible" in logs_json.texto()


def test_AC_TKT004_01_no_hay_cuentas_por_defecto(db):
    # THREAT-027: las migraciones no crean ninguna cuenta.
    assert CuentaStaff.objects.count() == 0
    assert RolCuenta.ADMINISTRADOR == "ADMINISTRADOR"


def test_AC_TKT004_01_csrf_emite_cookie_legible(cliente):
    respuesta = cliente.get(f"{BASE}/auth/csrf")
    assert respuesta.status_code == 204
    cookie = respuesta.cookies["csrftoken"]
    assert cookie["path"] == "/"
    assert cookie["samesite"] == "Lax"
    assert cookie["secure"] is True
    assert not cookie["httponly"]
    assert "sessionid" not in respuesta.cookies


def test_AC_TKT004_01_entrar_helper_con_mfa(admin):
    cliente = Client(raise_request_exception=False)
    assert entrar(cliente, admin).json()["paso_pendiente"] == "NINGUNO"
