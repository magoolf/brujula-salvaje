"""TKT-012: taxonomías del panel por HTTP real tras compartir los Mixin {X}Campos entre entrada y
salida (alineación del esquema generado con contracts/openapi.yaml).

- Las salidas siguen devolviendo exactamente los mismos campos (`id` + {X}Campos).
- Las restricciones del contrato se aplican en la entrada (el contrato manda): URL legal
  http(s) en licencias (antes cualquier texto), texto sin NUL, slug con patrón.
- Escalas: lista (5 + 4 niveles) y edición de un nivel.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from apps.catalogos.models import Continente, NivelEscala, Region

pytestmark = pytest.mark.django_db

BASE = "/api/v1/panel/taxonomias"


def _json(cliente: Client, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
    return getattr(cliente, metodo)(ruta, cuerpo, content_type="application/json")


def _licencia(**cambios: Any) -> dict[str, Any]:
    return {
        "codigo": "CC-BY-SA-9.0",
        "nombre": "Licencia de prueba",
        "url_texto_legal": "https://example.org/licencia",
        "requiere_atribucion": True,
        "compatible_publicacion": True,
        "activo": True,
    } | cambios


def test_TKT012_licencia_crear_obtener_actualizar_y_listar(cliente_admin: Client) -> None:
    creada = _json(cliente_admin, "post", f"{BASE}/licencias", _licencia())
    assert creada.status_code == 201, creada.content
    cuerpo = creada.json()
    assert set(cuerpo) == {
        "id", "codigo", "nombre", "url_texto_legal", "requiere_atribucion",
        "compatible_publicacion", "activo",
    }  # fmt: skip
    ruta = f"{BASE}/licencias/{cuerpo['id']}"
    assert cliente_admin.get(ruta).json() == cuerpo

    actualizada = _json(cliente_admin, "put", ruta, _licencia(nombre="Renombrada"))
    assert actualizada.status_code == 200, actualizada.content
    assert actualizada.json()["nombre"] == "Renombrada"

    lista = cliente_admin.get(f"{BASE}/licencias")
    assert lista.status_code == 200
    assert cuerpo["id"] in {r["id"] for r in lista.json()["resultados"]}


@pytest.mark.parametrize(
    "cambios",
    [
        {"url_texto_legal": "ftp://example.org/licencia"},
        {"url_texto_legal": "javascript:alert(1)"},
        {"nombre": "con\x00nul"},
        {"codigo": "minusculas"},
    ],
)
def test_TKT012_licencia_aplica_las_restricciones_del_contrato(
    cliente_admin: Client, cambios: dict[str, Any]
) -> None:
    respuesta = _json(cliente_admin, "post", f"{BASE}/licencias", _licencia(**cambios))
    assert respuesta.status_code == 400, respuesta.content
    assert set(cambios) <= set(respuesta.json()["errors"])


def test_TKT012_region_y_pais_por_http(cliente_admin: Client) -> None:
    region = _json(
        cliente_admin,
        "post",
        f"{BASE}/regiones",
        {
            "nombre": "Región HTTP",
            "slug": "region-http",
            "continente": Continente.ASIA,
            "orden": 3,
            "activo": True,
        },
    )
    assert region.status_code == 201, region.content
    assert set(region.json()) == {"id", "nombre", "slug", "continente", "orden", "activo"}

    pais = _json(
        cliente_admin,
        "post",
        f"{BASE}/paises",
        {
            "nombre": "País HTTP",
            "slug": "pais-http",
            "codigo_iso2": "QZ",
            "region_id": region.json()["id"],
            "activo": True,
        },
    )
    assert pais.status_code == 201, pais.content
    assert pais.json()["region_id"] == region.json()["id"]

    invalido = _json(
        cliente_admin,
        "post",
        f"{BASE}/paises",
        {
            "nombre": "Otro",
            "slug": "Slug Invalido",
            "codigo_iso2": "qz",
            "region_id": 2**63,
            "activo": True,
        },
    )
    assert invalido.status_code == 400, invalido.content
    assert {"slug", "codigo_iso2", "region_id"} <= set(invalido.json()["errors"])


def test_TKT012_categoria_guia_por_http(cliente_admin: Client) -> None:
    creada = _json(
        cliente_admin,
        "post",
        f"{BASE}/categorias-guia",
        {
            "nombre": "Categoría HTTP",
            "slug": "categoria-http",
            "descripcion": "Descripción",
            "orden": 9,
            "activo": True,
        },
    )
    assert creada.status_code == 201, creada.content
    ruta = f"{BASE}/categorias-guia/{creada.json()['id']}"
    assert cliente_admin.get(ruta).json()["orden"] == 9
    campos = {k: v for k, v in creada.json().items() if k != "id"}
    fuera_de_rango = _json(cliente_admin, "put", ruta, campos | {"orden": 1001})
    assert fuera_de_rango.status_code == 400, fuera_de_rango.content
    assert list(fuera_de_rango.json()["errors"]) == ["orden"]


def test_TKT012_escalas_listar_y_editar_nivel(cliente_admin: Client) -> None:
    escalas = cliente_admin.get(f"{BASE}/escalas")
    assert escalas.status_code == 200, escalas.content
    assert (len(escalas.json()["dificultad"]), len(escalas.json()["presupuesto"])) == (5, 4)
    nivel = NivelEscala.objects.order_by("id").first()
    assert nivel is not None
    respuesta = _json(
        cliente_admin,
        "put",
        f"{BASE}/escalas/{nivel.pk}",
        {"etiqueta": "Muy fácil", "descripcion": "Apto para todos"},
    )
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["etiqueta"] == "Muy fácil"


def test_TKT012_region_inexistente_es_404(cliente_admin: Client) -> None:
    assert not Region.objects.filter(pk=987654).exists()
    assert cliente_admin.get(f"{BASE}/regiones/987654").status_code == 404
