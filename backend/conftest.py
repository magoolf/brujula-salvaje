"""Fixtures comunes de pytest (PostgreSQL real, BD de pruebas test_brujula)."""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from django.core.management import call_command
from django.test import Client

from apps.core.observabilidad import formateador_json


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup: None, django_db_blocker: Any) -> None:
    # cache_limites (UNLOGGED, RunSQL) llega con la migración ops.0001 de TKT-003. Hasta entonces
    # la BD de pruebas la crea con createcachetable (no hace nada si la tabla ya existe).
    with django_db_blocker.unblock():
        call_command("createcachetable", verbosity=0)


@pytest.fixture
def cliente() -> Client:
    """Cliente que devuelve la respuesta de error en vez de relanzar la excepción."""
    return Client(raise_request_exception=False)


@pytest.fixture
def logs_json() -> Iterator[Callable[[], list[dict[str, Any]]]]:
    """Captura, como JSON, lo que los loggers de la aplicación y de Django escriben."""
    flujo = io.StringIO()
    manejador = logging.StreamHandler(flujo)
    manejador.setFormatter(formateador_json())
    loggers = [logging.getLogger(nombre) for nombre in ("brujula", "django")]
    for logger in loggers:
        logger.addHandler(manejador)

    def leer() -> list[dict[str, Any]]:
        return [json.loads(linea) for linea in flujo.getvalue().splitlines() if linea.strip()]

    leer.texto = flujo.getvalue  # type: ignore[attr-defined]
    yield leer
    for logger in loggers:
        logger.removeHandler(manejador)
