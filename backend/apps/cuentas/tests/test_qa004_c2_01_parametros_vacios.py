"""Regresión de QA004-C2-01 (AC-113, DEC-AUTO-105): parámetros de consulta vacíos o repetidos.

La lista de parámetros sale de contracts/openapi.yaml: CADA parámetro de consulta de CADA
operación del ticket, vacío o solo con espacios, responde 400 parametro_invalido indicando el
parámetro (antes DRF lo trataba como ausente y respondía 200 sin filtrar). Ninguno es de tipo
array, así que repetirlo también es 400. Además se comprueba que el contrato no declara
allowEmptyValue en ningún parámetro (si lo hiciera, la vista debe usar `admite_vacio`).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from django.conf import settings

from apps.core.exceptions import ParametroInvalido
from apps.core.parametros import validar_parametros
from apps.cuentas.tests.conftest import problema

pytestmark = pytest.mark.django_db

PREFIJOS_TKT004 = ("/api/v1/panel/auth/", "/api/v1/panel/cuentas", "/api/v1/panel/auditoria")
VALIDOS = {
    "estado": "ACTIVA",
    "rol": "EDITOR",
    "pagina": "1",
    "desde": "2026-01-01T00:00:00Z",
    "hasta": "2030-01-01T00:00:00Z",
    "actor_id": "1",
    "accion": "LOGIN_OK",
    "tipo_entidad": "CUENTA",
    "resultado": "EXITO",
}


def _contrato() -> dict:
    ruta = Path(settings.BASE_DIR).parent / "contracts" / "openapi.yaml"
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def _resolver(contrato: dict, parametro: dict) -> dict:
    if "$ref" in parametro:
        nombre = parametro["$ref"].rsplit("/", 1)[-1]
        return contrato["components"]["parameters"][nombre]
    return parametro


def _parametros_de_consulta() -> list[tuple[str, str, dict]]:
    contrato = _contrato()
    casos = []
    for ruta, item in contrato["paths"].items():
        if not ruta.startswith(PREFIJOS_TKT004) or "{" in ruta:
            continue
        comunes = item.get("parameters", [])
        for metodo, op in item.items():
            if metodo != "get":
                continue
            for parametro in [*comunes, *op.get("parameters", [])]:
                definicion = _resolver(contrato, parametro)
                if definicion.get("in") == "query":
                    casos.append((ruta, definicion["name"], definicion))
    return casos


CASOS = _parametros_de_consulta()


def test_QA004_C2_01_el_contrato_tiene_los_parametros_esperados():
    nombres = {(ruta, nombre) for ruta, nombre, _ in CASOS}
    assert nombres == {
        ("/api/v1/panel/cuentas", "estado"),
        ("/api/v1/panel/cuentas", "rol"),
        ("/api/v1/panel/cuentas", "pagina"),
        *(
            ("/api/v1/panel/auditoria", nombre)
            for nombre in (
                "desde",
                "hasta",
                "actor_id",
                "accion",
                "tipo_entidad",
                "resultado",
                "pagina",
            )
        ),
    }
    for _ruta, _nombre, definicion in CASOS:
        assert not definicion.get("allowEmptyValue")
        assert definicion.get("schema", {}).get("type") != "array"


@pytest.mark.parametrize(
    ("ruta", "nombre", "definicion"), CASOS, ids=[f"{r}?{n}" for r, n, _ in CASOS]
)
@pytest.mark.parametrize("valor", ["", "   "])
def test_QA004_C2_01_parametro_vacio_es_400(cliente_admin, ruta, nombre, definicion, valor):
    respuesta = cliente_admin.get(ruta, {nombre: valor})
    assert nombre in problema(respuesta, 400, "parametro_invalido")["errors"]


@pytest.mark.parametrize(
    ("ruta", "nombre", "definicion"), CASOS, ids=[f"{r}?{n}" for r, n, _ in CASOS]
)
def test_QA004_C2_01_parametro_repetido_es_400(cliente_admin, ruta, nombre, definicion):
    respuesta = cliente_admin.get(f"{ruta}?{nombre}={VALIDOS[nombre]}&{nombre}={VALIDOS[nombre]}")
    assert nombre in problema(respuesta, 400, "parametro_invalido")["errors"]


@pytest.mark.parametrize(
    ("ruta", "nombre", "definicion"), CASOS, ids=[f"{r}?{n}" for r, n, _ in CASOS]
)
@pytest.mark.parametrize("posicion", ["inicio", "medio", "final"])
def test_QA004_C3_01_parametro_con_nul_es_400(cliente_admin, ruta, nombre, definicion, posicion):
    # DEC-AUTO-217 (CHG-API-002): U+0000 se rechaza en cualquier entrada, antes de parsear
    # (p. ej. desde=2030-01-01T00:00:00Z%00basura daba 200).
    valido = VALIDOS[nombre]
    valor = {
        "inicio": f"\x00{valido}",
        "medio": f"{valido[:1]}\x00{valido[1:]}",
        "final": f"{valido}\x00basura",
    }[posicion]
    respuesta = cliente_admin.get(ruta, {nombre: valor})
    assert nombre in problema(respuesta, 400, "parametro_invalido")["errors"]


@pytest.mark.parametrize(
    ("ruta", "nombre", "definicion"), CASOS, ids=[f"{r}?{n}" for r, n, _ in CASOS]
)
def test_QA004_C2_01_parametro_valido_es_200(cliente_admin, ruta, nombre, definicion):
    assert cliente_admin.get(ruta, {nombre: VALIDOS[nombre]}).status_code == 200


def test_QA004_C2_01_validar_parametros_multiples_y_admite_vacio():
    from django.http import QueryDict

    validar_parametros(QueryDict("duracion=A&duracion=B"), {"duracion"}, multiples={"duracion"})
    validar_parametros(QueryDict("texto="), {"texto"}, admite_vacio={"texto"})
    with pytest.raises(ParametroInvalido) as error:
        validar_parametros(QueryDict("duracion=A&duracion="), {"duracion"}, multiples={"duracion"})
    assert error.value.errors == {"duracion": ["El parámetro no puede estar vacío."]}
    validar_parametros({"pagina": "2"}, {"pagina"})  # Mapping simple sin getlist
