"""TKT-032 (F4, AC_TKT032_04): `GET /api/v1/panel/tablero` por HTTP real (antes solo se probaba el
servicio, y `apps/inicio/api/views.py` líneas 35-37 quedaban sin ejercer). La alerta de
Responsable sin definir es solo para el Administrador (FEAT-049); la respuesta cumple el
componente `Tablero` del contrato."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from apps.contenido.models import EstadoEditorial
from apps.contenido.tests import publicos
from apps.contenido.tests.conftest import validar_contra

pytestmark = pytest.mark.django_db

RUTA = "/api/v1/panel/tablero"


def _codigos(cuerpo: dict[str, Any]) -> set[str]:
    return {alerta["code"] for alerta in cuerpo["alertas"]}


@pytest.mark.parametrize(
    ("cliente", "ve_alerta_responsable"),
    [("cliente_editora", False), ("cliente_admin", True)],
)
def test_AC_TKT032_04_tablero_por_http_segun_rol(
    request: pytest.FixtureRequest, cliente: str, ve_alerta_responsable: bool
) -> None:
    publicos.termino("Vivac", [], estado=EstadoEditorial.PUBLICADO)
    publicos.termino("Collado", [], estado=EstadoEditorial.BORRADOR)
    http: Client = request.getfixturevalue(cliente)

    respuesta = http.get(RUTA)

    assert respuesta.status_code == 200, respuesta.content
    cuerpo = respuesta.json()
    assert validar_contra("Tablero", cuerpo) == []
    terminos = next(c for c in cuerpo["conteos"] if c["tipo"] == "TERMINO")
    assert (terminos["publicado"], terminos["borrador"]) == (1, 1)
    assert ("responsable_sin_definir" in _codigos(cuerpo)) is ve_alerta_responsable


def test_AC_TKT032_04_tablero_sin_sesion_es_401(client: Client) -> None:
    respuesta = client.get(RUTA)
    assert respuesta.status_code == 401
    assert respuesta["Content-Type"] == "application/problem+json"
