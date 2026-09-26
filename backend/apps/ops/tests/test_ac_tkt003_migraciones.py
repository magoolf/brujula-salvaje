"""AC-TKT003-01: migraciones desde BD vacía, sin cambios pendientes y reversibles.

Se crea una BD nueva desde template1 (esquemas app/ext y privilegios de INFRA-DB-000 en modo
prueba), se migra con app_migrator en un subproceso, se revierte app a app hasta cero, se
comprueba que no queda ningún objeto y se vuelve a migrar. Al final la BD se elimina.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connection

BACKEND = Path(settings.BASE_DIR)
BD_MIGRACIONES = "tkt003_prueba_migraciones"
# Orden inverso al plan de migraciones (DB_HANDOFF plan_migraciones n=12..1).
APPS_EN_ORDEN_INVERSO = [
    "ops",
    "busqueda",
    "auditoria",
    "inicio",
    "contenido",
    "medios",
    "catalogos",
    "cuentas",
]


def _conectar(nombre_bd: str) -> psycopg.Connection:
    datos = connection.settings_dict
    return psycopg.connect(
        host=datos["HOST"],
        port=datos["PORT"],
        user=datos["USER"],
        password=datos["PASSWORD"],
        dbname=nombre_bd,
        autocommit=True,
    )


def _manage(*args: str) -> subprocess.CompletedProcess[str]:
    entorno = dict(os.environ)
    entorno.update({"DJANGO_SETTINGS_MODULE": "config.settings.test", "DB_NAME": BD_MIGRACIONES})
    return subprocess.run(  # noqa: S603 (argumentos fijos, sin shell)
        [sys.executable, "manage.py", *args, "--noinput"],
        cwd=BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def _objetos_app(bd: psycopg.Connection) -> dict[str, int]:
    consultas = {
        "tablas": "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'app' AND c.relkind IN ('r', 'v') AND c.relname <> 'django_migrations'",
        "funciones": "SELECT count(*) FROM pg_proc p JOIN pg_namespace n "
        "ON n.oid = p.pronamespace WHERE n.nspname = 'app'",
        "extensiones": "SELECT count(*) FROM pg_extension WHERE extname IN ('unaccent', 'pg_trgm')",
        "configuraciones": "SELECT count(*) FROM pg_ts_config "
        "WHERE cfgnamespace = 'app'::regnamespace",
    }
    resultado = {}
    for clave, sql in consultas.items():
        fila = bd.execute(sql).fetchone()
        assert fila is not None
        resultado[clave] = fila[0]
    return resultado


@pytest.fixture
def bd_vacia():
    with _conectar(connection.settings_dict["NAME"]) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {BD_MIGRACIONES} WITH (FORCE)")
        admin.execute(f"CREATE DATABASE {BD_MIGRACIONES} TEMPLATE template1")
    try:
        yield
    finally:
        with _conectar(connection.settings_dict["NAME"]) as admin:
            admin.execute(f"DROP DATABASE IF EXISTS {BD_MIGRACIONES} WITH (FORCE)")


@pytest.mark.django_db
def test_AC_TKT003_01_migrate_desde_cero_revertir_y_volver_a_migrar(bd_vacia):
    migrar = _manage("migrate")
    assert migrar.returncode == 0, migrar.stderr
    with _conectar(BD_MIGRACIONES) as bd:
        tras_migrar = _objetos_app(bd)
    assert tras_migrar["tablas"] == 39  # 38 tablas + v_medio_uso
    assert tras_migrar["extensiones"] == 2
    assert tras_migrar["configuraciones"] == 1

    for app in APPS_EN_ORDEN_INVERSO:
        revertir = _manage("migrate", app, "zero")
        assert revertir.returncode == 0, (app, revertir.stderr)
    with _conectar(BD_MIGRACIONES) as bd:
        assert _objetos_app(bd) == {
            "tablas": 0,
            "funciones": 0,
            "extensiones": 0,
            "configuraciones": 0,
        }
        pendientes = bd.execute("SELECT count(*) FROM app.django_migrations").fetchone()
        assert pendientes == (0,)

    remigrar = _manage("migrate")
    assert remigrar.returncode == 0, remigrar.stderr
    with _conectar(BD_MIGRACIONES) as bd:
        assert _objetos_app(bd) == tras_migrar
        recuentos = bd.execute(
            "SELECT (SELECT count(*) FROM app.region), (SELECT count(*) FROM app.config_sitio)"
        ).fetchone()
        assert recuentos == (7, 1)


@pytest.mark.django_db
def test_AC_TKT003_01_makemigrations_sin_cambios_pendientes():
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)


@pytest.mark.django_db
def test_AC_TKT003_01_todas_las_migraciones_aplicadas_en_la_bd_de_pruebas():
    filas = connection.introspection.connection.cursor()
    filas.execute("SELECT app, name FROM app.django_migrations")
    aplicadas = set(filas.fetchall())
    for esperada in [
        ("busqueda", "0001_extensiones_funciones"),
        ("cuentas", "0001_inicial"),
        ("catalogos", "0001_inicial"),
        ("catalogos", "0002_semilla"),
        ("medios", "0001_inicial"),
        ("contenido", "0001_inicial"),
        ("contenido", "0002_integridad_sql"),
        ("inicio", "0001_inicial"),
        ("auditoria", "0001_inicial"),
        ("auditoria", "0002_inmutabilidad"),
        ("busqueda", "0002_inicial"),
        ("ops", "0001_inicial"),
    ]:
        assert esperada in aplicadas
