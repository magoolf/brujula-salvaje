"""AC-TKT004-09 (parte en pytest): el esquema generado cubre las operaciones del ticket, todas
están en contracts/openapi.yaml y ninguna ruta del contrato queda implementada solo en parte.

El diff semántico (oasdiff breaking --fail-on WARN) y schemathesis se ejecutan fuera de pytest
(gate de CI y evidencia del ticket).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from django.conf import settings

from apps.core.esquema import GeneradorContrato, _sin_envoltorio_readonly

METODOS = {"get", "put", "post", "delete", "patch"}
OPERACIONES_TKT004 = {
    "panelObtenerCsrf",
    "panelIniciarSesion",
    "panelVerificarMfa",
    "panelCerrarSesion",
    "panelObtenerSesion",
    "panelRenovarSesion",
    "panelCambiarContrasena",
    "panelObtenerAutorizacion",
    "panelRegistrarAutorizacion",
    "panelIniciarActivacionMfa",
    "panelConfirmarActivacionMfa",
    "panelDesactivarMfa",
    "panelRegenerarCodigosRecuperacion",
    "panelListarCuentas",
    "panelCrearCuenta",
    "panelObtenerCuenta",
    "panelActualizarCuenta",
    "panelRestablecerContrasenaCuenta",
    "panelRestablecerMfaCuenta",
    "panelDesactivarCuenta",
    "panelReactivarCuenta",
    "panelAnonimizarCuenta",
    "panelListarAuditoria",
}


def _operaciones(doc: dict) -> dict[tuple[str, str], str]:
    normalizar = lambda ruta: re.sub(r"\{[^}]+\}", "{}", ruta)  # noqa: E731
    return {
        (normalizar(ruta), metodo): op["operationId"]
        for ruta, item in doc["paths"].items()
        for metodo, op in item.items()
        if metodo in METODOS
    }


@pytest.fixture(scope="module")
def esquemas() -> tuple[dict, dict]:
    contrato_ruta = Path(settings.BASE_DIR).parent / "contracts" / "openapi.yaml"
    contrato = yaml.safe_load(contrato_ruta.read_text(encoding="utf-8"))
    generado = GeneradorContrato().get_schema(request=None, public=True)
    return contrato, generado


def test_AC_TKT004_09_operaciones_del_ticket_generadas_y_documentadas(esquemas):
    contrato, generado = esquemas
    c, g = _operaciones(contrato), _operaciones(generado)
    assert OPERACIONES_TKT004 <= set(g.values())
    assert set(g) <= set(c), sorted(set(g) - set(c))
    for clave, operation_id in g.items():
        assert c[clave] == operation_id
    # Rutas completas: si se implementa una ruta, todas sus operaciones del contrato.
    rutas_g = {ruta for ruta, _ in g}
    parciales = sorted(clave for clave in set(c) - set(g) if clave[0] in rutas_g)
    assert parciales == []


def test_AC_TKT004_09_convenciones_estructurales_del_contrato(esquemas):
    _contrato, generado = esquemas
    item = generado["paths"]["/api/v1/panel/cuentas/{id}"]
    assert [p["name"] for p in item["parameters"]] == ["id"]
    assert "parameters" not in item["get"]
    componentes = generado["components"]["schemas"]
    assert componentes["PaginaCuenta"]["allOf"][0] == {"$ref": "#/components/schemas/PaginaMeta"}
    assert componentes["ProblemaValidacion"]["allOf"][0] == {"$ref": "#/components/schemas/Problem"}
    assert componentes["Cuenta"]["properties"]["rol"] == {"$ref": "#/components/schemas/Rol"}
    conflicto = generado["paths"]["/api/v1/panel/cuentas"]["post"]["responses"]["409"]
    assert conflicto["content"]["application/problem+json"]["schema"] == {
        "$ref": "#/components/schemas/ProblemaConUsos"
    }


def test_sin_envoltorio_readonly_conserva_otras_composiciones():
    compuesto = {"allOf": [{"$ref": "#/a"}, {"type": "object"}]}
    assert _sin_envoltorio_readonly(compuesto) == compuesto
    assert _sin_envoltorio_readonly([{"allOf": [{"$ref": "#/a"}], "readOnly": True}]) == [
        {"$ref": "#/a"}
    ]
