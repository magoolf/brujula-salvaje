"""AC_TKT012_01: el esquema generado por drf-spectacular declara las mismas restricciones que
`contracts/openapi.yaml` en las categorías que oasdiff marcaba como WARNING (563 antes de
TKT-012): `pattern`, `maxItems`/`minItems`, `uniqueItems`, `contentMediaType`, `format`, tipo
y el cuerpo multipart de la subida de medios.

El conteo real de oasdiff se comprueba en CI (paso "contrato: gate por operación + oasdiff");
estas pruebas fijan, sin el binario, una muestra representativa de cada categoría para que una
regresión del esquema se detecte ya en pytest. Las restricciones también se APLICAN en la
validación real (ver `test_tkt012_panel_http_ciclo.py::test_TKT012_restricciones_del_contrato_se_
aplican_en_la_entrada`): el contrato manda.
"""

from __future__ import annotations

from functools import cache
from typing import Any

import pytest

from apps.contenido.tests.conftest import contrato
from apps.core.esquema import GeneradorContrato

_SIN_DESCRIPCION = ("description", "title", "readOnly", "writeOnly")


@cache
def _generado() -> dict[str, Any]:
    return GeneradorContrato().get_schema(request=None, public=True)  # type: ignore[no-any-return]


def _limpio(esquema: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in esquema.items() if k not in _SIN_DESCRIPCION}


def _propiedad(doc: dict[str, Any], componente: str, propiedad: str) -> dict[str, Any]:
    """La propiedad sin textos descriptivos y con `items: {$ref}` resuelto (el contrato usa
    componentes como `Mes` o `Id` que drf-spectacular expande en línea)."""
    esquema = _limpio(doc["components"]["schemas"][componente]["properties"][propiedad])
    items = esquema.get("items")
    if isinstance(items, dict) and "$ref" in items:
        nombre = items["$ref"].rsplit("/", 1)[-1]
        esquema["items"] = _limpio(doc["components"]["schemas"][nombre])
    return esquema


@pytest.mark.parametrize(
    ("componente", "propiedad"),
    [
        # contentMediaType + pattern sin NUL (request/response-property-content-media-type-changed)
        ("DestinoCampos", "descripcion_experta"),
        ("DestinoCampos", "como_llegar"),
        # texto plano con pattern (response-property-pattern-removed)
        ("DestinoCampos", "resumen"),
        ("DestinoCampos", "clima"),
        # number sin format (response-property-type-changed)
        ("DestinoCampos", "latitud"),
        # uniqueItems + maxItems (response-property-unique-items-unset / max-items-unset)
        ("DestinoCampos", "meses_mejor_epoca"),
        # oneOf [$ref, null] (response-property-one-of-added)
        ("UsoMedio", "estado_editorial"),
    ],
)
def test_AC_TKT012_01_propiedad_generada_igual_al_contrato(componente: str, propiedad: str) -> None:
    assert _propiedad(_generado(), componente, propiedad) == _propiedad(
        contrato(), componente, propiedad
    )


def test_AC_TKT012_01_lista_de_ids_unica_y_limitada_como_el_contrato() -> None:
    """`Id` del contrato es un $ref (`integer`, `int64`, `minimum: 1`, sin `maximum`); el generado
    lo expande en línea con exactamente esas restricciones."""
    generado = _propiedad(_generado(), "DestinoCampos", "tipos_ids")
    esperado = _propiedad(contrato(), "DestinoCampos", "tipos_ids")
    assert generado["uniqueItems"] is esperado["uniqueItems"] is True
    assert generado["maxItems"] == esperado["maxItems"] == 12
    id_contrato = _limpio(contrato()["components"]["schemas"]["Id"])
    assert _limpio(generado["items"]) == id_contrato
    assert "maximum" not in generado["items"]


def test_AC_TKT012_01_url_de_fuente_http_con_formato_uri() -> None:
    """Única diferencia admitida: `minLength: 1` en el generado (dirección request), que el
    `pattern: '^https?://...'` del contrato ya implica (la cadena vacía nunca casa con él)."""
    generado = _propiedad(_generado(), "FuenteEntradaRequest", "url")
    esperado = _propiedad(contrato(), "FuenteEntrada", "url")
    assert generado.pop("minLength", 1) == 1
    assert esperado["pattern"].startswith("^https?://")
    assert generado == esperado


def test_AC_TKT012_01_subida_de_medios_es_objeto_multipart_con_archivos() -> None:
    """Antes `string/binary` (el único ERROR, ignorado por DEC-AUTO-920) y `archivos` ausente."""
    cuerpo = _generado()["paths"]["/api/v1/panel/medios"]["post"]["requestBody"]
    ref = cuerpo["content"]["multipart/form-data"]["schema"]["$ref"]
    esquema = _generado()["components"]["schemas"][ref.rsplit("/", 1)[-1]]
    esperado = contrato()["components"]["schemas"]["SubidaMediosEntrada"]
    assert esquema["type"] == esperado["type"] == "object"
    assert esquema["required"] == esperado["required"] == ["archivos"]
    archivos = esquema["properties"]["archivos"]
    assert archivos["type"] == "array"
    assert (archivos["minItems"], archivos["maxItems"]) == (1, 10)
