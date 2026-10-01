"""TKT-032: `PUT /api/v1/panel/medios/{id}` (catalogar) sin 500 por errores de BD.

- F1 (AC_TKT032_01): vaciar alt, crédito o licencia de un medio DISPONIBLE violaba
  `ck_medio_disponible` (500). RULE-005/STATE-002 no tienen transición DISPONIBLE →
  PENDIENTE_METADATOS: es una regla de negocio incumplida → 422 `regla_negocio` (documentado para
  la operación), sin cambios. Una licencia inexistente (FK DEFERRABLE, fallaba en el COMMIT) o
  fuera de bigint → 400 `validacion`.
- INFO (QA de TKT-012): `fuente_url: ""` no casa con el patrón del contrato (`^https?://`) y la BD
  la rechazaba (`ck_medio_fuente_url`, 500) → 400 `validacion`; `null` sigue valiendo.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.test import Client

from apps.contenido.tests import publicos
from apps.contenido.tests.fabricas import forzar_diferidas
from apps.medios.models import EstadoMedio, Medio

pytestmark = pytest.mark.django_db

BASE = "/api/v1/panel/medios"


def _put(cliente: Client, medio: Medio, cuerpo: dict[str, Any]) -> Any:
    return cliente.put(f"{BASE}/{medio.pk}", cuerpo, content_type="application/json")


def _problema(respuesta: Any, estado: int, codigo: str) -> dict[str, Any]:
    assert respuesta.status_code == estado, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
    cuerpo: dict[str, Any] = respuesta.json()
    assert cuerpo["code"] == codigo
    assert len(cuerpo["trace_id"]) == 32
    return cuerpo


def _sin_excepciones(logs: Callable[[], list[dict[str, Any]]]) -> None:
    forzar_diferidas("ALL")  # nada inválido queda pendiente para el COMMIT
    assert not [r for r in logs() if r.get("event") == "excepcion_no_controlada"]


@pytest.mark.parametrize(
    ("cuerpo", "clave"),
    [
        ({"autor_credito": None}, "autor_credito"),
        ({"texto_alternativo": None}, "texto_alternativo"),
        ({"licencia_id": None}, "licencia_id"),
        ({"texto_alternativo": ""}, "texto_alternativo"),
        ({"autor_credito": None, "licencia_id": None}, "licencia_id"),
    ],
)
def test_AC_TKT032_01_vaciar_requisito_de_medio_disponible_es_422(
    cliente_editora: Client,
    logs_json: Callable[[], list[dict[str, Any]]],
    cuerpo: dict[str, Any],
    clave: str,
) -> None:
    medio = publicos.medio()
    antes = (medio.texto_alternativo, medio.autor_credito, medio.licencia_id)

    problema = _problema(_put(cliente_editora, medio, cuerpo), 422, "regla_negocio")

    assert clave in problema["errors"]
    medio.refresh_from_db()
    assert medio.estado == EstadoMedio.DISPONIBLE
    assert (medio.texto_alternativo, medio.autor_credito, medio.licencia_id) == antes
    _sin_excepciones(logs_json)


@pytest.mark.parametrize("licencia_id", [99_999_999, 2**63 + 5])
def test_AC_TKT032_01_licencia_inexistente_o_fuera_de_rango_es_400(
    cliente_editora: Client, logs_json: Callable[[], list[dict[str, Any]]], licencia_id: int
) -> None:
    medio = publicos.medio(estado=EstadoMedio.PENDIENTE_METADATOS, licencia=None)

    problema = _problema(
        _put(cliente_editora, medio, {"licencia_id": licencia_id}), 400, "validacion"
    )

    assert "licencia_id" in problema["errors"]
    medio.refresh_from_db()
    assert medio.licencia_id is None
    _sin_excepciones(logs_json)


def test_AC_TKT032_INFO_fuente_url_vacia_es_400_y_null_sigue_valiendo(
    cliente_editora: Client, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    medio = publicos.medio(fuente_url="https://example.org/foto")

    problema = _problema(_put(cliente_editora, medio, {"fuente_url": ""}), 400, "validacion")
    assert "fuente_url" in problema["errors"]
    medio.refresh_from_db()
    assert medio.fuente_url == "https://example.org/foto"

    borrada = _put(cliente_editora, medio, {"fuente_url": None})
    assert borrada.status_code == 200, borrada.content
    assert borrada.json()["fuente_url"] is None

    nueva = _put(cliente_editora, medio, {"fuente_url": "http://example.org/otra"})
    assert nueva.status_code == 200, nueva.content
    assert nueva.json()["fuente_url"] == "http://example.org/otra"
    _sin_excepciones(logs_json)


def test_AC_TKT032_01_catalogar_disponible_sin_vaciar_requisitos_sigue_siendo_200(
    cliente_editora: Client,
) -> None:
    """Regresión: editar campos no exigidos (pie de foto) de un DISPONIBLE sigue funcionando."""
    medio = publicos.medio()
    respuesta = _put(cliente_editora, medio, {"pie_de_foto": "Amanecer en el páramo"})
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["estado"] == EstadoMedio.DISPONIBLE
