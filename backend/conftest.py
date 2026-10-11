"""Fixtures comunes de pytest (PostgreSQL real, BD de pruebas test_brujula)."""

from __future__ import annotations

import io
import json
import logging
import time
from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from django.core.management import call_command
from django.db import connection
from django.test import Client
from psycopg import sql

from apps.core.observabilidad import formateador_json

# BDs efímeras (TKT-061, DEC-AUTO-1100): plazo máximo para que una BD quede libre al crearla o
# eliminarla. Cada intento de PostgreSQL ya espera hasta 5 s a que salgan las demás sesiones.
PLAZO_BD_EFIMERA_S = 60.0
_PAUSA_REINTENTO_S = 0.5


def _conectar_admin() -> psycopg.Connection:
    """Conexión autocommit a la BD de pruebas con las credenciales de Django (sin superusuario)."""
    datos = connection.settings_dict
    return psycopg.connect(
        host=datos["HOST"],
        port=datos["PORT"],
        user=datos["USER"],
        password=datos["PASSWORD"],
        dbname=datos["NAME"],
        autocommit=True,
    )


def _sesiones_en(admin: psycopg.Connection, nombre: str) -> list[tuple[Any, ...]]:
    return admin.execute(
        "SELECT pid, usename, backend_type, application_name, state FROM pg_stat_activity "
        "WHERE datname = %s AND pid <> pg_backend_pid()",
        [nombre],
    ).fetchall()


def _cerrar_sesiones_propias(admin: psycopg.Connection, nombre: str) -> None:
    # Solo sesiones cliente del MISMO rol en la BD efímera (restos de los subprocesos de la prueba):
    # nunca procesos ajenos (autovacuum, otros roles): exigirían pg_signal_backend o superusuario.
    admin.execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = %s AND usename = current_user AND backend_type = 'client backend' "
        "AND pid <> pg_backend_pid()",
        [nombre],
    )


def _con_reintento(
    admin: psycopg.Connection, sentencia: sql.Composed, ocupada: str, *, efimera: bool
) -> None:
    """Ejecuta CREATE/DROP DATABASE reintentando, con plazo acotado, mientras la BD esté en uso.

    Solo en la BD efímera (efimera=True) se cierran las sesiones propias; en template1 se espera.
    """
    limite = time.monotonic() + PLAZO_BD_EFIMERA_S
    while True:
        try:
            admin.execute(sentencia)
            return
        except psycopg.errors.ObjectInUse:
            if time.monotonic() >= limite:
                raise AssertionError(
                    f"{ocupada} sigue en uso tras {PLAZO_BD_EFIMERA_S:.0f} s: "
                    f"{_sesiones_en(admin, ocupada)}"
                ) from None
            if efimera:
                _cerrar_sesiones_propias(admin, ocupada)
            time.sleep(_PAUSA_REINTENTO_S)


def eliminar_bd_efimera(nombre: str) -> None:
    """Elimina una BD efímera de pruebas sin DROP ... WITH (FORCE).

    FORCE intenta terminar TODAS las sesiones de la BD y, sin superusuario ni pg_signal_backend
    (CI y local usan app_migrator), falla con InsufficientPrivilege si hay un proceso de otro rol:
    el autovacuum worker que analiza la BD recién migrada (TKT-061). El DROP simple, en cambio,
    pide al autovacuum que salga (sin comprobar privilegios) y espera a las demás sesiones; si
    aun así queda alguna, se cierran solo las sesiones propias y se reintenta con plazo acotado.
    """
    with _conectar_admin() as admin:
        _con_reintento(
            admin,
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(nombre)),
            nombre,
            efimera=True,
        )


def crear_bd_efimera(nombre: str) -> None:
    """Crea (desde cero) una BD vacía desde template1 (esquemas app/ext de INFRA-DB-000)."""
    eliminar_bd_efimera(nombre)
    with _conectar_admin() as admin:
        _con_reintento(
            admin,
            sql.SQL("CREATE DATABASE {} TEMPLATE template1").format(sql.Identifier(nombre)),
            "template1",
            efimera=False,
        )


class BdEfimera:
    """BDs vacías de una prueba: se crean desde template1 y se eliminan al final sin forzar."""

    def __init__(self) -> None:
        self.creadas: list[str] = []

    def __call__(self, nombre: str) -> None:
        self.creadas.append(nombre)
        crear_bd_efimera(nombre)

    def eliminar(self, nombre: str) -> None:
        eliminar_bd_efimera(nombre)

    def eliminar_todas(self) -> None:
        """Intenta eliminar TODAS las BDs aunque alguna falle o agote el plazo (OBS-QA061-01).

        Así un fallo no deja huérfanas las demás; al final se falla con el diagnóstico agregado.
        """
        fallos: list[str] = []
        for nombre in dict.fromkeys(reversed(self.creadas)):
            try:
                eliminar_bd_efimera(nombre)
            except Exception as error:  # se agregan y se relanzan al final
                fallos.append(f"{nombre}: {type(error).__name__}: {error}")
        if fallos:
            raise AssertionError(
                f"No se pudieron eliminar {len(fallos)} BD efímera(s): " + " | ".join(fallos)
            )


@pytest.fixture
def bd_efimera() -> Iterator[BdEfimera]:
    """Factoría de BDs vacías que se eliminan al terminar la prueba (también si falla)."""
    bds = BdEfimera()
    yield bds
    bds.eliminar_todas()


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
