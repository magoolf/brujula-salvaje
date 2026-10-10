"""TKT-061: BD efímera de las pruebas de migraciones con teardown robusto sin superusuario.

La causa del fallo intermitente en CI era DROP DATABASE ... WITH (FORCE) con app_migrator (sin
superusuario ni pg_signal_backend) mientras un autovacuum worker analizaba la BD recién migrada:
PostgreSQL no deja terminar ese proceso (InsufficientPrivilege). El helper de backend/conftest.py
usa DROP simple (el servidor hace salir al autovacuum sin comprobar privilegios), cierra solo las
sesiones propias que queden y reintenta con plazo acotado. Estas pruebas fijan ese contrato.
"""

from __future__ import annotations

import psycopg
import pytest
from django.db import connection

pytestmark = pytest.mark.django_db

BD = "tkt061_prueba_bd_efimera"


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


def _existe(nombre_bd: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM pg_database WHERE datname = %s", [nombre_bd])
        return cursor.fetchone() == (1,)


def test_TKT061_el_rol_de_pruebas_no_es_superusuario_ni_puede_terminar_procesos_ajenos():
    # Condición de CI (DB_USER=app_migrator): por eso WITH (FORCE) no puede con el autovacuum.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolsuper, pg_has_role(current_user, 'pg_signal_backend', 'USAGE') "
            "FROM pg_roles WHERE rolname = current_user"
        )
        assert cursor.fetchone() == (False, False)


def test_TKT061_crea_bd_vacia_desde_template1_y_la_elimina(bd_efimera):
    bd_efimera(BD)
    assert _existe(BD)
    with _conectar(BD) as bd:
        esquemas = bd.execute(
            "SELECT count(*) FROM pg_namespace WHERE nspname IN ('app', 'ext')"
        ).fetchone()
    assert esquemas == (2,)
    bd_efimera.eliminar(BD)
    assert not _existe(BD)


def test_TKT061_elimina_aunque_quede_una_sesion_propia_abierta(bd_efimera):
    # Simula la sesión de un subproceso "manage.py" que aún no ha salido del servidor.
    bd_efimera(BD)
    rezagada = _conectar(BD)
    try:
        bd_efimera.eliminar(BD)
        assert not _existe(BD)
        with pytest.raises(psycopg.OperationalError):
            rezagada.execute("SELECT 1")
    finally:
        rezagada.close()


def test_TKT061_recrear_sustituye_una_bd_previa_con_sesion_propia(bd_efimera):
    # Arranque tras una ejecución interrumpida: la BD previa existe y tiene una sesión abierta.
    bd_efimera(BD)
    with _conectar(BD) as previa:
        previa.execute("CREATE TABLE app.marca_previa (id int)")
    rezagada = _conectar(BD)
    try:
        bd_efimera(BD)
        with _conectar(BD) as nueva:
            marca = nueva.execute("SELECT to_regclass('app.marca_previa')").fetchone()
        assert marca == (None,)
    finally:
        rezagada.close()


def test_TKT061_no_usa_drop_database_forzado(bd_efimera, monkeypatch):
    sentencias: list[str] = []
    original = psycopg.Connection.execute

    def registrar(self, consulta, *args, **kwargs):
        texto = consulta if isinstance(consulta, str) else consulta.as_string(self)
        sentencias.append(texto)
        return original(self, consulta, *args, **kwargs)

    monkeypatch.setattr(psycopg.Connection, "execute", registrar)
    bd_efimera(BD)
    bd_efimera.eliminar(BD)
    monkeypatch.undo()
    ddl = [s for s in sentencias if "DATABASE" in s.upper()]
    assert any(s.startswith("DROP DATABASE") for s in ddl)
    assert not [s for s in ddl if "FORCE" in s.upper()]
