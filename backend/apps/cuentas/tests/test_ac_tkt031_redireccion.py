"""AC-TKT031: seguimiento de la QA de TKT-027 sobre el destino tras el login del panel.

Trazabilidad: TKT-027, AC-115, THREAT-017 (DEC-AUTO-942).
- OBS-01: /panel/acceso (y lo que cuelga de él, también codificado) nunca es destino; igual que el
  cliente (frontend core/auth/destino-seguro.ts).
- OBS-02: '/' y '\\' codificadas (%2f, %5c, en mayúsculas y doble codificación) → /panel.
- OBS-04: dentro del límite del contrato (LoginEntrada.siguiente maxLength 2000), un `siguiente`
  inválido nunca impide el login: se ignora y se devuelve /panel. Por encima de 2000 caracteres el
  contrato exige 400 `validacion` y se mantiene (CHG propuesto en el reporte del ticket).
- OBS-05: la redirección guardada en sesión se revalida al leerla.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.test import Client

from apps.cuentas import services
from apps.cuentas.sesiones import SessionStore
from apps.cuentas.tests.conftest import BASE, CONTRASENA, IP, post, problema

POR_DEFECTO = services.REDIRECCION_POR_DEFECTO
CLAVE_REDIRECCION = "panel_redireccion"

# AC_TKT031_01: el formulario de acceso y sus formas codificadas que se canonizan a él.
ACCESO = [
    "/panel/acceso",
    "/panel/acceso/",
    "/panel/acceso/mfa",
    "/panel/acceso/a/b/",
    "/panel/%61cceso",
    "/panel/acces%6f",
    "/panel/acces%6F/",
    "/panel/%2561cceso",
    "/panel/%252561cceso/x",
    "/panel/%61%63%63%65%73%6f",
]

# Rutas parecidas que no son el formulario de acceso: se conservan (mismo criterio que el cliente).
PARECIDAS = ["/panel/accesos", "/panel/accesox", "/panel/cuenta/acceso", "/panel/medios/acceso/"]

# AC_TKT031_02: separadores codificados. Sin _SEPARADOR_CODIFICADO, '%2f' fabricaría un segmento
# nuevo y válido ('/panel/medios/123'), así que estos casos detectan su eliminación.
SEPARADORES = [
    "/panel/medios%2f123",
    "/panel/medios%2F123",
    "/panel/medios%252f123",
    "/panel/medios%252F123",
    "/panel/medios%25252f123",
    "/panel/a%5cb",
    "/panel/a%5Cb",
    "/panel/a%255cb",
    "/panel/a%255Cb",
    "/panel/medios%5c123",
]
MATAN_MUTANTE = ["/panel/medios%2f123", "/panel/medios%2F123", "/panel/medios%252f123"]


# ---------------------------------------------------------------------------
# Unitarias de la función pura
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("siguiente", ACCESO)
def test_AC_TKT031_01_formulario_de_acceso_va_al_destino_por_defecto(siguiente):
    assert services.redireccion_segura(siguiente) == POR_DEFECTO


@pytest.mark.parametrize("siguiente", PARECIDAS)
def test_AC_TKT031_01_rutas_parecidas_se_conservan(siguiente):
    assert services.redireccion_segura(siguiente) == siguiente


@pytest.mark.parametrize("ruta", ["/panel", "/panel/", "/panel/cuenta", "/panel/accesos"])
def test_AC_TKT031_01_es_formulario_acceso_solo_con_primer_segmento_acceso(ruta):
    assert services._es_formulario_acceso(ruta) is False


@pytest.mark.parametrize("siguiente", SEPARADORES)
def test_AC_TKT031_02_separadores_codificados_van_al_destino_por_defecto(siguiente):
    assert services.redireccion_segura(siguiente) == POR_DEFECTO


@pytest.mark.parametrize("siguiente", MATAN_MUTANTE)
def test_AC_TKT031_02_sin_el_control_de_separadores_el_caso_seria_aceptado(monkeypatch, siguiente):
    # Prueba de mutación: si se elimina _SEPARADOR_CODIFICADO, el valor se aceptaría como
    # '/panel/medios/123'; el control es lo único que lo rechaza.
    monkeypatch.setattr(services, "_SEPARADOR_CODIFICADO", services.re.compile(r"(?!)"))
    assert services.redireccion_segura(siguiente) == "/panel/medios/123"


@pytest.mark.parametrize(
    "siguiente",
    [
        "/x" * 1000,  # 2000 caracteres, fuera de /panel
        "/panel/" + "%2e%2e/" * 284 + "abcde",  # 2000 caracteres
        "/panel/acceso/" + "a" * 1986,  # 2000 caracteres
        "/panel/" + "a" * 1992 + "?",  # 2000 caracteres, con query
    ],
)
def test_AC_TKT031_03_invalido_hasta_el_limite_va_al_destino_por_defecto(siguiente):
    assert len(siguiente) == 2000
    assert services.redireccion_segura(siguiente) == POR_DEFECTO


# ---------------------------------------------------------------------------
# Integración HTTP del login y de la sesión
# ---------------------------------------------------------------------------
def _login(cliente, usuario, siguiente):
    return post(
        cliente,
        "/auth/login",
        {"usuario": usuario, "contrasena": CONTRASENA, "siguiente": siguiente},
        REMOTE_ADDR=IP,
    )


def _sesion(cliente):
    respuesta = cliente.get(f"{BASE}/auth/sesion")
    assert respuesta.status_code == 200, respuesta.content
    return respuesta.json()


@pytest.mark.django_db
@pytest.mark.parametrize("siguiente", ACCESO + SEPARADORES[:4])
def test_AC_TKT031_01_login_http_paso_ninguno(cliente, editora, siguiente):
    respuesta = _login(cliente, "editora.uno", siguiente)
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["paso_pendiente"] == "NINGUNO"
    assert respuesta.json()["redireccion"] == POR_DEFECTO
    assert _sesion(cliente)["redireccion"] == POR_DEFECTO


@pytest.mark.django_db
@pytest.mark.parametrize("siguiente", ["/panel/acceso", "/panel/%2561cceso/", "/panel/a%5Cb"])
def test_AC_TKT031_01_login_http_paso_mfa(cliente, admin, siguiente):
    respuesta = _login(cliente, "admin.principal", siguiente)
    assert respuesta.json()["paso_pendiente"] == "MFA"
    assert respuesta.json()["redireccion"] == POR_DEFECTO
    respuesta = post(cliente, "/auth/mfa/verificar", {"codigo": admin.codigo()}, REMOTE_ADDR=IP)
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["paso_pendiente"] == "NINGUNO"
    assert respuesta.json()["redireccion"] == POR_DEFECTO
    assert _sesion(cliente)["redireccion"] == POR_DEFECTO


@pytest.mark.django_db
def test_AC_TKT031_01_login_http_ruta_parecida_se_conserva(cliente, editora):
    respuesta = _login(cliente, "editora.uno", "/panel/accesos")
    assert respuesta.json()["redireccion"] == "/panel/accesos"


@pytest.mark.django_db
def test_AC_TKT031_03_siguiente_invalido_en_el_limite_no_impide_el_login(cliente, editora):
    siguiente = "/panel/acceso/" + "%2e" * 662
    assert len(siguiente) == 2000
    respuesta = _login(cliente, "editora.uno", siguiente)
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["redireccion"] == POR_DEFECTO


@pytest.mark.django_db
def test_AC_TKT031_03_siguiente_valido_en_el_limite_se_conserva(cliente, editora):
    siguiente = "/panel/" + "a" * 1993
    assert len(siguiente) == 2000
    assert _login(cliente, "editora.uno", siguiente).json()["redireccion"] == siguiente


@pytest.mark.django_db
@pytest.mark.parametrize("longitud", [2001, 2048])
def test_AC_TKT031_03_por_encima_del_contrato_se_mantiene_el_400(cliente, editora, longitud):
    # contracts/openapi.yaml LoginEntrada.siguiente: maxLength 2000 → 400 `validacion` (sin CHG).
    siguiente = "/panel/" + "a" * (longitud - 7)
    cuerpo = problema(_login(cliente, "editora.uno", siguiente), 400, "validacion")
    assert "siguiente" in cuerpo["errors"]
    assert settings.SESSION_COOKIE_NAME not in cliente.cookies


# ---------------------------------------------------------------------------
# Revalidación de la redirección guardada (OBS-05)
# ---------------------------------------------------------------------------
def _alterar_redireccion(cliente, valor):
    """Simula una sesión abierta con reglas anteriores: escribe el destino sin pasar el filtro."""
    tienda = SessionStore(session_key=cliente.cookies[settings.SESSION_COOKIE_NAME].value)
    tienda[CLAVE_REDIRECCION] = valor
    tienda.save()


GUARDADAS_INVALIDAS = [
    "/panel/acceso",
    "/panel/%2e%2e/destinos",
    "/panel/medios%2f123",
    "https://evil.example/panel",
    "//evil.example",
    "",
    12345,
    None,
]


@pytest.mark.django_db
@pytest.mark.parametrize("valor", GUARDADAS_INVALIDAS)
def test_AC_TKT031_04_sesion_guardada_se_revalida_al_leerla(cliente, editora, valor):
    assert _login(cliente, "editora.uno", "/panel/medios").status_code == 200
    _alterar_redireccion(cliente, valor)
    assert _sesion(cliente)["redireccion"] == POR_DEFECTO


@pytest.mark.django_db
def test_AC_TKT031_04_sesion_guardada_valida_se_conserva(cliente, editora):
    assert _login(cliente, "editora.uno", "/panel/medios").status_code == 200
    _alterar_redireccion(cliente, "/panel/contenido/destinos")
    assert _sesion(cliente)["redireccion"] == "/panel/contenido/destinos"


@pytest.mark.django_db
@pytest.mark.parametrize("valor", ["/panel/acceso", "/panel/%2e%2e/destinos", "//evil.example"])
def test_AC_TKT031_04_paso_mfa_revalida_la_redireccion_guardada(cliente, admin, valor):
    respuesta = _login(cliente, "admin.principal", "/panel/medios")
    assert respuesta.json()["paso_pendiente"] == "MFA"
    _alterar_redireccion(cliente, valor)
    respuesta = post(cliente, "/auth/mfa/verificar", {"codigo": admin.codigo()}, REMOTE_ADDR=IP)
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["redireccion"] == POR_DEFECTO


# ---------------------------------------------------------------------------
# Sin regresión (AC_TKT031_05): CSRF y throttling del login
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_AC_TKT031_05_csrf_sigue_exigido(editora):
    cliente = Client(enforce_csrf_checks=True, raise_request_exception=False)
    problema(_login(cliente, "editora.uno", "/panel/acceso"), 403, "csrf_invalido")
    token = cliente.get(f"{BASE}/auth/csrf").cookies["csrftoken"].value
    respuesta = post(
        cliente,
        "/auth/login",
        {"usuario": "editora.uno", "contrasena": CONTRASENA, "siguiente": "/panel/acceso"},
        REMOTE_ADDR=IP,
        HTTP_X_CSRFTOKEN=token,
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["redireccion"] == POR_DEFECTO


@pytest.mark.django_db
def test_AC_TKT031_05_throttling_del_login_sin_regresion(cliente):
    for indice in range(10):
        problema(
            _login(cliente, f"usuario{indice}", "/panel/acceso"), 401, "credenciales_invalidas"
        )
    problema(_login(cliente, "otro.usuario", "/panel/medios%2f1"), 429, "limite_tasa")
