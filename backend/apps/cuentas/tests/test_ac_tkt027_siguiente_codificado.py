"""AC-TKT027: `siguiente` del login con segmentos de punto o separadores codificados.

Trazabilidad: AC-115, THREAT-017, TKT-004, TKT-010 (QA FALLO-03, parte backend).
El validador es una función pura de la capa de negocio (services.redireccion_segura); la vista
solo delega. Las pruebas unitarias cubren la función y las de integración el login por HTTP.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.cuentas import services
from apps.cuentas.tests.conftest import BASE, CONTRASENA, IP, post, problema

POR_DEFECTO = services.REDIRECCION_POR_DEFECTO

# AC_TKT027_01: segmentos de punto codificados (simple, mayúsculas, mixtos, doble codificación),
# barras y barras invertidas codificadas y parámetros de ruta (';').
PUNTOS_CODIFICADOS = [
    "/panel/%2e%2e/destinos",
    "/panel/%2E%2E/%2E%2E/destinos",
    "/panel/.%2e/destinos",
    "/panel/%2e./destinos",
    "/panel/%252e%252e/destinos",
    "/panel/%25252e%25252e/destinos",
    "/panel/%2e%2e%2fdestinos",
    "/panel/..%2fdestinos",
    "/panel/%5c..%5cdestinos",
    "/panel/..;/destinos",
    "/panel/%2e/destinos",
    "/panel/medios/%2e%2e/%2e%2e/destinos",
    "/panel/%252f%252fmalicioso.example",
    "/panel/%25%32%65%25%32%65/destinos",
    "/panel/%ff%fe",
    "/panel/%00",
    "/panel/%0a",
    "/panel/%3f",
]

# AC_TKT027_02: variantes externas que ya se rechazaban.
EXTERNAS = [
    "//evil.com",
    "/\\evil.com",
    "/\\\\evil.com",
    "https://evil.com/panel",
    "javascript:alert(1)",
    "%2F%2Fevil.com",
    "/%2F%2Fevil.com",
    "\\\\evil.com",
    "\\\\\\\\evil.com",
    "http:/evil.com",
    "/panel@evil.com",
    "/panel//evil.com",
    "/panel/\\evil.com",
    "/panelx",
    "/destinos",
]

# AC_TKT027_03: rutas internas legítimas que se conservan tal cual.
INTERNAS = [
    "/panel",
    "/panel/",
    "/panel/cuenta",
    "/panel/medios/123",
    "/panel/medios/123/",
    "/panel/contenido/destinos",
    "/panel/contenido/destinos.v2",
]

# Las query no se admitían antes de TKT-027 y siguen sin admitirse (AC_TKT027_03): destino por
# defecto, sin cambio de comportamiento.
CON_QUERY = ["/panel/contenido/destinos?estado=BORRADOR", "/panel#x"]


# ---------------------------------------------------------------------------
# Unitarias de la función pura
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("siguiente", PUNTOS_CODIFICADOS)
def test_AC_TKT027_01_puntos_y_separadores_codificados_van_al_destino_por_defecto(siguiente):
    assert services.redireccion_segura(siguiente) == POR_DEFECTO


@pytest.mark.parametrize("siguiente", EXTERNAS)
def test_AC_TKT027_02_externas_siguen_rechazadas(siguiente):
    assert services.redireccion_segura(siguiente) == POR_DEFECTO


@pytest.mark.parametrize("siguiente", INTERNAS)
def test_AC_TKT027_03_rutas_internas_se_conservan(siguiente):
    assert services.redireccion_segura(siguiente) == siguiente


@pytest.mark.parametrize("siguiente", CON_QUERY)
def test_AC_TKT027_03_query_sin_cambio_de_comportamiento(siguiente):
    assert services.redireccion_segura(siguiente) == POR_DEFECTO


@pytest.mark.parametrize("siguiente", [None, ""])
def test_AC_TKT027_03_vacio_va_al_destino_por_defecto(siguiente):
    assert services.redireccion_segura(siguiente) == POR_DEFECTO


def test_AC_TKT027_03_caracteres_seguros_codificados_se_devuelven_canonicos():
    # %61 = 'a', %2D = '-': se valida y se devuelve la forma decodificada, nunca otra cosa.
    assert services.redireccion_segura("/panel/medios/%61%2D1") == "/panel/medios/a-1"
    assert services.redireccion_segura("/panel/a%2eb") == "/panel/a.b"


def test_AC_TKT027_01_codificacion_que_no_se_estabiliza_se_rechaza():
    # Cada "25" anidado exige una decodificación más (%252561 → %2561 → %61 → a); más allá del
    # máximo no se sigue decodificando.
    assert services.redireccion_segura("/panel/%252561") == "/panel/a"
    assert services.redireccion_segura("/panel/%" + "25" * 8 + "61") == POR_DEFECTO


@pytest.mark.parametrize("ruta", ["/panelx", "/otra/panel", "/panel//x", "/panel/./x"])
def test_AC_TKT027_01_es_ruta_panel_rechaza_por_si_sola(ruta):
    # Defensa en profundidad: la comprobación de la forma canónica no depende del patrón previo.
    assert services._es_ruta_panel(ruta) is False


@pytest.mark.parametrize("siguiente", PUNTOS_CODIFICADOS + EXTERNAS + INTERNAS + CON_QUERY)
def test_AC_TKT027_01_el_resultado_nunca_sale_de_panel(siguiente):
    resultado = services.redireccion_segura(siguiente)
    assert resultado == POR_DEFECTO or resultado.startswith(POR_DEFECTO + "/")
    assert "%" not in resultado
    assert all(segmento not in {".", ".."} for segmento in resultado.split("/"))
    assert "//" not in resultado and "\\" not in resultado


# ---------------------------------------------------------------------------
# Integración HTTP del login (AC_TKT027_04)
# ---------------------------------------------------------------------------
def _login(cliente, usuario, siguiente, **extra):
    return post(
        cliente,
        "/auth/login",
        {"usuario": usuario, "contrasena": CONTRASENA, "siguiente": siguiente},
        REMOTE_ADDR=IP,
        **extra,
    )


def _esperado(siguiente):
    return siguiente if siguiente in INTERNAS else POR_DEFECTO


@pytest.mark.django_db
@pytest.mark.parametrize("siguiente", PUNTOS_CODIFICADOS + EXTERNAS + INTERNAS + CON_QUERY)
def test_AC_TKT027_04_login_http_por_familia(cliente, editora, siguiente):
    respuesta = _login(cliente, "editora.uno", siguiente)
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["redireccion"] == _esperado(siguiente)
    assert cliente.get(f"{BASE}/auth/sesion").json()["redireccion"] == _esperado(siguiente)


@pytest.mark.django_db
def test_AC_TKT027_04_csrf_sigue_exigido_con_siguiente_codificado(editora):
    cliente = Client(enforce_csrf_checks=True, raise_request_exception=False)
    problema(_login(cliente, "editora.uno", "/panel/%2e%2e/destinos"), 403, "csrf_invalido")
    token = cliente.get(f"{BASE}/auth/csrf").cookies["csrftoken"].value
    respuesta = _login(cliente, "editora.uno", "/panel/%2e%2e/destinos", HTTP_X_CSRFTOKEN=token)
    assert respuesta.status_code == 200
    assert respuesta.json()["redireccion"] == POR_DEFECTO


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("siguiente", "esperada"),
    [("/panel/%252e%252e/destinos", POR_DEFECTO), ("/panel/medios/123", "/panel/medios/123")],
)
def test_AC_TKT027_04_mfa_conserva_el_destino_validado(cliente, admin, siguiente, esperada):
    respuesta = _login(cliente, "admin.principal", siguiente)
    assert respuesta.json()["paso_pendiente"] == "MFA"
    assert respuesta.json()["redireccion"] == esperada
    respuesta = post(cliente, "/auth/mfa/verificar", {"codigo": admin.codigo()}, REMOTE_ADDR=IP)
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["paso_pendiente"] == "NINGUNO"
    assert respuesta.json()["redireccion"] == esperada


@pytest.mark.django_db
def test_AC_TKT027_04_throttling_del_login_sin_regresion(cliente):
    # THREAT-001: 10 intentos/min por IP (perfil panel-login), con o sin `siguiente`.
    for indice in range(10):
        problema(
            _login(cliente, f"usuario{indice}", "/panel/%2e%2e/destinos"),
            401,
            "credenciales_invalidas",
        )
    problema(_login(cliente, "otro.usuario", "/panel/medios"), 429, "limite_tasa")
