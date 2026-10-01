"""TKT-012: configuración de inicio y del sitio por HTTP real tras compartir los Mixin
{X}Campos entre entrada y salida (alineación del esquema generado con contracts/openapi.yaml).

- La salida conserva sus campos y la entrada aplica las restricciones del contrato
  (`uniqueItems` de los destacados, `minItems`/`maxItems`, texto sin NUL, Id sin desbordar).
- Configuración del sitio: solo ADMINISTRADOR (autorización vertical).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from apps.contenido.tests import publicos
from apps.inicio.tests.test_ac_tkt006_05_inicio_configuracion_tablero import _mundo_minimo

pytestmark = pytest.mark.django_db


def _json(cliente: Client, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
    return getattr(cliente, metodo)(ruta, cuerpo, content_type="application/json")


def _cuerpo_inicio() -> dict[str, Any]:
    mundo = _mundo_minimo()
    return {
        "hero_titular": "Explora",
        "hero_subtitulo": "Aventura con criterio",
        "hero_medio_id": publicos.medio().pk,
        "destinos_ids": mundo["destinos"],
        "itinerarios_ids": mundo["itinerarios"],
        "guias_ids": mundo["guias"],
    }


def test_TKT012_config_inicio_obtener_y_actualizar(cliente_editora: Client) -> None:
    publicos.config_inicio()
    cuerpo = _cuerpo_inicio()
    respuesta = _json(cliente_editora, "put", "/api/v1/panel/inicio", cuerpo)
    assert respuesta.status_code == 200, respuesta.content
    datos = respuesta.json()
    assert datos["destinos_ids"] == cuerpo["destinos_ids"]
    assert set(datos) >= {"actualizado_en", "actualizado_por", "referencias"}
    assert cliente_editora.get("/api/v1/panel/inicio").json()["guias_ids"] == cuerpo["guias_ids"]


@pytest.mark.parametrize(
    ("campo", "transformar"),
    [
        ("destinos_ids", lambda ids: [ids[0], *ids[:-1]]),  # repetido (uniqueItems)
        ("guias_ids", lambda ids: ids[:2]),  # menos de 3 (minItems)
        ("hero_titular", lambda _v: "con\x00nul"),
        ("hero_medio_id", lambda _v: 2**63),
    ],
)
def test_TKT012_config_inicio_aplica_restricciones_del_contrato(
    cliente_editora: Client, campo: str, transformar: Any
) -> None:
    publicos.config_inicio()
    cuerpo = _cuerpo_inicio()
    cuerpo[campo] = transformar(cuerpo[campo])
    respuesta = _json(cliente_editora, "put", "/api/v1/panel/inicio", cuerpo)
    assert respuesta.status_code == 400, respuesta.content
    assert campo in respuesta.json()["errors"]


def test_TKT012_configuracion_sitio_solo_administrador(
    cliente_editora: Client, cliente_admin: Client
) -> None:
    cuerpo = {
        "nombre_marca": "Brújula Salvaje",
        "lema": "Viaja con criterio",
        "texto_descargo": "Información orientativa.",
        "responsable_nombre": "Equipo editorial",
    }
    assert _json(cliente_editora, "put", "/api/v1/panel/configuracion", cuerpo).status_code == 403
    respuesta = _json(cliente_admin, "put", "/api/v1/panel/configuracion", cuerpo)
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["lema"] == "Viaja con criterio"
    assert respuesta.json()["responsable_domicilio"] is None
    leida = cliente_admin.get("/api/v1/panel/configuracion")
    assert leida.status_code == 200
    assert leida.json()["nombre_marca"] == "Brújula Salvaje"

    invalida = _json(
        cliente_admin, "put", "/api/v1/panel/configuracion", cuerpo | {"lema": "a\x00b"}
    )
    assert invalida.status_code == 400, invalida.content
    assert "lema" in invalida.json()["errors"]
