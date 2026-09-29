"""AC-TKT005-04 (throttling público) y AC-TKT005-07 (THREAT del sitio público).

- 04: perfiles x-limite-tasa publico-lectura (120/min), publico-busqueda (30/min) y
  publico-aleatorio (30/min) por IP truncada; 429 limite_tasa problem+json con Retry-After.
- 07: THREAT-008 (inyección), THREAT-009 (DoS), THREAT-010 (reflejo de q), THREAT-011
  (enumeración de borradores), THREAT-019 (divulgación), THREAT-020 (logs), THREAT-023 (rutas).
"""

from __future__ import annotations

from typing import Any

import pytest

from apps.contenido.models import Contenido
from apps.contenido.tests.conftest import PUBLICO

pytestmark = pytest.mark.django_db

IP_A = "198.51.100.10"
IP_A_MISMA_RED = "198.51.100.200"
IP_B = "192.0.2.10"


def _get(api, ruta: str, ip: str = IP_A, **parametros: Any):
    return api.get(f"{PUBLICO}{ruta}", parametros, REMOTE_ADDR=ip)


# ---------------------------------------------------------------------------
# AC-TKT005-04: limitación de tasa efectiva y 429 conforme
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("ruta", "parametros", "limite"),
    [
        ("/busqueda", {"q": "cocuy"}, 30),
        ("/destinos/aleatorio", {}, 30),
        ("/escalas", {}, 120),
    ],
)
def test_AC_TKT005_04_limite_por_perfil_y_429_conforme(
    api, mundo, conforme, ruta, parametros, limite
):
    for _ in range(limite):
        assert _get(api, ruta, **parametros).status_code == 200
    # Misma red /24 → misma cuota (clave HMAC de la IP truncada).
    bloqueada = _get(api, ruta, ip=IP_A_MISMA_RED, **parametros)
    assert bloqueada.status_code == 429
    assert bloqueada["Content-Type"] == "application/problem+json"
    assert int(bloqueada["Retry-After"]) >= 1
    assert bloqueada["Cache-Control"] == "no-store"
    assert bloqueada.json()["code"] == "limite_tasa"
    conforme("Problem", bloqueada.json())
    # Otra red conserva su cuota.
    assert _get(api, ruta, ip=IP_B, **parametros).status_code == 200


def test_AC_TKT005_04_parametros_invalidos_tambien_consumen_cuota(api, mundo):
    for _ in range(30):
        assert _get(api, "/busqueda", q="x").status_code == 400
    assert _get(api, "/busqueda", q="cocuy").status_code == 429


def test_AC_TKT005_04_perfiles_independientes(api, mundo):
    for _ in range(30):
        _get(api, "/busqueda", q="cocuy")
    assert _get(api, "/busqueda", q="cocuy").status_code == 429
    assert _get(api, "/destinos").status_code == 200
    assert _get(api, "/destinos/aleatorio").status_code == 200


# ---------------------------------------------------------------------------
# THREAT-011: enumeración de borradores y retirados
# ---------------------------------------------------------------------------
def _sin_traza(respuesta) -> dict[str, Any]:
    cuerpo = dict(respuesta.json())
    cuerpo.pop("trace_id")
    return cuerpo


def test_AC_TKT005_07_THREAT_011_borrador_indistinguible_de_inexistente(api, mundo):
    borrador = _get(api, f"/destinos/{mundo['borrador'].contenido.slug}")
    inexistente = _get(api, "/destinos/no-existe-jamas")
    assert borrador.status_code == inexistente.status_code == 404
    assert _sin_traza(borrador) == _sin_traza(inexistente)
    tipo_borrador = _get(api, f"/tipos-aventura/{mundo['tipo_borrador'].contenido.slug}")
    assert tipo_borrador.status_code == 404


def test_AC_TKT005_07_THREAT_011_sin_acceso_por_id(api, mundo):
    assert _get(api, f"/destinos/{mundo['cocuy'].pk}").status_code == 404
    assert _get(api, "/destinos", id=str(mundo["cocuy"].pk)).status_code == 400


# ---------------------------------------------------------------------------
# THREAT-008 / THREAT-010: inyección y reflejo en la búsqueda y los filtros
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "q",
    [
        "'; DROP TABLE contenido; --",
        "cocuy & !trek | kayak:*",
        "cocuy <-> glaciar",
        "a' OR '1'='1",
        "%_\\\\ () [] {}",
        "<script>alert(1)</script>",
        "ñandú ÅÉÎ 日本 🏔️",
    ],
)
def test_AC_TKT005_07_THREAT_008_busqueda_trata_q_como_dato(api, mundo, q):
    antes = Contenido.objects.count()
    respuesta = _get(api, "/busqueda", q=q)
    assert respuesta.status_code == 200
    assert Contenido.objects.count() == antes
    # THREAT-010: q nunca se refleja en la respuesta.
    assert q.encode() not in respuesta.content
    assert "q" not in respuesta.json()


@pytest.mark.parametrize(
    "parametros",
    [
        {"region": "x' OR 1=1 --"},
        {"tipo": "../../etc/passwd"},
        {"mes": "1; DROP TABLE destino"},
        {"orden": "titulo; DELETE"},
        {"q": "cocuy\x00"},
    ],
)
def test_AC_TKT005_07_THREAT_008_filtros_contra_dominios_cerrados(api, mundo, parametros):
    ruta = "/busqueda" if "q" in parametros else "/destinos"
    respuesta = _get(api, ruta, **parametros)
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "parametro_invalido"
    for valor in parametros.values():
        assert valor.encode() not in respuesta.content


# ---------------------------------------------------------------------------
# THREAT-009: consultas costosas y paginación profunda
# ---------------------------------------------------------------------------
def test_AC_TKT005_07_THREAT_009_limites_de_consulta(api, mundo):
    assert _get(api, "/busqueda", q="x" * 101).status_code == 400
    assert _get(api, "/destinos", pagina="10001").status_code == 400
    assert _get(api, "/destinos", pagina="9999").status_code == 404
    assert _get(api, "/destinos", tipo=[f"t{i}" for i in range(13)]).status_code == 400
    assert _get(api, "/destinos", tamano_pagina="1000").status_code == 400
    assert _get(api, "/destinos/mapa").json()["tamano_pagina"] == 500


# ---------------------------------------------------------------------------
# THREAT-019: sin ids internos ni datos del staff; sin cookies (RULE-029)
# ---------------------------------------------------------------------------
PROHIBIDAS = {
    "id",
    "contenido_id",
    "creado_por",
    "actualizado_por",
    "subido_por",
    "archivo_saneado_ruta",
    "huella_sha256",
    "sha256_saneado",
    "estado_editorial",
    "version",
    "titulo_interno",
}


def _claves(nodo: Any) -> set[str]:
    if isinstance(nodo, dict):
        return set(nodo) | {c for v in nodo.values() for c in _claves(v)}
    if isinstance(nodo, list):
        return {c for v in nodo for c in _claves(v)}
    return set()


def test_AC_TKT005_07_THREAT_019_sin_ids_ni_datos_del_staff(api, mundo):
    rutas = [
        "/inicio",
        "/indice",
        "/destinos",
        "/destinos/mapa",
        f"/destinos/{mundo['cocuy'].contenido.slug}",
        f"/destinos/{mundo['retirado'].contenido.slug}",
        f"/itinerarios/{mundo['ruta_cocuy'].contenido.slug}",
        f"/guias/{mundo['guia_equipo'].contenido.slug}",
        f"/tipos-aventura/{mundo['tipos'][0].contenido.slug}",
        f"/colecciones/{mundo['coleccion'].contenido.slug}",
        "/creditos",
        "/glosario",
        "/busqueda?q=trekking",
    ]
    for ruta in rutas:
        respuesta = api.get(f"{PUBLICO}{ruta}")
        assert respuesta.status_code in (200, 410), ruta
        assert _claves(respuesta.json()).isdisjoint(PROHIBIDAS), ruta
        assert not respuesta.cookies, ruta
        assert "Set-Cookie" not in respuesta.headers, ruta
        assert len(respuesta["X-Trace-Id"]) == 32
        assert respuesta["X-Content-Type-Options"] == "nosniff"
        assert "frame-ancestors 'none'" in respuesta["Content-Security-Policy"]


def test_AC_TKT005_07_THREAT_019_urls_de_derivados_publicas_sin_rutas_internas(api, mundo):
    ficha = api.get(f"{PUBLICO}/destinos/{mundo['cocuy'].contenido.slug}").json()
    urls = [d["url"] for d in ficha["portada"]["derivados"]]
    assert urls
    assert all(u.startswith("/media/publico/derivados/") for u in urls)
    assert "originales" not in api.get(f"{PUBLICO}/creditos").content.decode()


# ---------------------------------------------------------------------------
# THREAT-020 / AC-116: el texto buscado no se registra
# ---------------------------------------------------------------------------
def test_AC_TKT005_07_THREAT_020_texto_buscado_fuera_de_los_logs(api, mundo, logs_json):
    secreto = "palabraclaveunica"
    _get(api, "/busqueda", q=secreto)
    _get(api, "/busqueda/destinos", q=secreto)
    _get(api, "/busqueda", q="x")  # 400: tampoco se registra
    texto = logs_json.texto()
    assert secreto not in texto
    lineas = [linea for linea in logs_json() if linea.get("event") == "peticion"]
    assert {linea["endpoint"] for linea in lineas} == {
        "/api/v1/publico/busqueda",
        "/api/v1/publico/busqueda/<grupo:grupo>",
    }
    assert all("?" not in linea["endpoint"] for linea in lineas)


# ---------------------------------------------------------------------------
# THREAT-023: rutas con slug fuera de patrón
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "ruta",
    [
        "/destinos/..%2F..%2Fetc%2Fpasswd",
        "/destinos/Con-Mayusculas",
        "/destinos/slug_con_guion_bajo",
        "/guias/-empieza-con-guion",
        "/paginas/..",
        "/busqueda/DESTINOS?q=cocuy",
    ],
)
def test_AC_TKT005_07_THREAT_023_slug_fuera_de_patron_404(api, mundo, ruta):
    respuesta = api.get(f"{PUBLICO}{ruta}")
    assert respuesta.status_code == 404
    assert respuesta["Content-Type"] == "application/problem+json"
