"""Fixtures de las pruebas de la API pública (TKT-005) y del panel editorial (TKT-006).

- `mundo`: conjunto de contenido publicado coherente (apps/contenido/tests/publicos.py) con el
  índice de búsqueda reconstruido.
- `conforme`: valida un cuerpo JSON contra un componente de contracts/openapi.yaml (JSON Schema
  2020-12, dialecto de OAS 3.1), como hace schemathesis con response_schema_conformance.
- `cliente_editora`/`editora`: sesión real de panel (login + CSRF vía `apps.cuentas.tests.conftest`,
  mismo patrón que `apps/auditoria/tests/conftest.py`) para pruebas HTTP end-to-end del panel
  editorial (TKT-006, QA ciclo 1/3: BUG-1/BUG-2 solo se detectaron con una petición HTTP real
  contra Postgres, nunca con una llamada directa a `services.py`).
"""

from __future__ import annotations

from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

import pytest
import yaml
from django.conf import settings
from django.test import Client
from jsonschema import Draft202012Validator

from apps.busqueda.services import reindexar_todo
from apps.contenido.tests import publicos
from apps.cuentas.tests.conftest import cliente_editora, editora  # noqa: F401 (fixtures de pytest)

PUBLICO = "/api/v1/publico"


@cache
def contrato() -> dict[str, Any]:
    ruta = Path(settings.BASE_DIR).parent / "contracts" / "openapi.yaml"
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def validar_contra(componente: str, cuerpo: Any) -> list[str]:
    documento = dict(contrato())
    esquema = {"$ref": f"#/components/schemas/{componente}", "components": documento["components"]}
    validador = Draft202012Validator(esquema)
    return [f"{list(e.absolute_path)}: {e.message}" for e in validador.iter_errors(cuerpo)]


@pytest.fixture
def conforme() -> Callable[[str, Any], None]:
    def comprobar(componente: str, cuerpo: Any) -> None:
        errores = validar_contra(componente, cuerpo)
        assert errores == [], errores[:10]

    return comprobar


@pytest.fixture
def api() -> Client:
    return Client(raise_request_exception=False)


@pytest.fixture
def mundo(db: None) -> dict[str, Any]:
    datos = publicos.mundo()
    reindexar_todo()
    return datos
