"""TKT-063: pruebas de migraciones sin DROP ... WITH (FORCE) y teardown agregado (OBS-QA061-01).

- test_ac_tkt003_migraciones (ops) y test_ac_tkt005_06_chg_db_002 (contenido) usan la fixture
  bd_efimera de backend/conftest.py (TKT-061): ya no existe la fixture bd_vacia con FORCE, que
  fallaba con InsufficientPrivilege (app_migrator sin superusuario) si un autovacuum worker
  estaba en la BD temporal.
- BdEfimera.eliminar_todas intenta eliminar TODAS las BDs aunque una agote el plazo y falla al
  final con el diagnóstico agregado.
"""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

import psycopg
import pytest
from django.conf import settings
from django.db import connection

from apps.contenido.tests import test_ac_tkt005_06_chg_db_002 as pruebas_contenido
from apps.ops.tests import test_ac_tkt003_migraciones as pruebas_ops

pytestmark = pytest.mark.django_db

BD_LIBRE = "tkt063_prueba_libre"
BD_OCUPADA = "tkt063_prueba_ocupada"


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


def _sql_forzado(ruta: Path) -> list[str]:
    """Literales de texto (no docstrings) con DROP/DATABASE ... FORCE en un módulo de pruebas."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    docstrings = {
        id(nodo.body[0].value)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        and nodo.body
        and isinstance(nodo.body[0], ast.Expr)
        and isinstance(nodo.body[0].value, ast.Constant)
    }
    return [
        nodo.value
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant)
        and isinstance(nodo.value, str)
        and id(nodo) not in docstrings
        and "FORCE" in nodo.value.upper()
        and "DATABASE" in nodo.value.upper()
    ]


def test_TKT063_pruebas_de_migraciones_usan_bd_efimera_sin_force():
    for modulo, prueba in (
        (pruebas_ops, pruebas_ops.test_AC_TKT003_01_migrate_desde_cero_revertir_y_volver_a_migrar),
        (pruebas_contenido, pruebas_contenido.test_AC_TKT005_06_migraciones_chg_db_002_reversibles),
    ):
        assert list(inspect.signature(prueba).parameters) == ["bd_efimera"]
        assert not hasattr(modulo, "bd_vacia")
    # Ninguna prueba del backend conserva DROP DATABASE ... WITH (FORCE) en su código.
    backend = Path(settings.BASE_DIR)
    con_force = {
        str(ruta.relative_to(backend)): literales
        for ruta in [backend / "conftest.py", *(backend / "apps").rglob("test*.py")]
        if (literales := _sql_forzado(ruta))
    }
    assert con_force == {}


def test_TKT063_eliminar_todas_continua_tras_agotar_el_plazo_y_agrega_el_diagnostico(
    bd_efimera, monkeypatch
):
    modulo = sys.modules[type(bd_efimera).__module__]
    bd_efimera(BD_LIBRE)
    bd_efimera(BD_OCUPADA)  # se elimina primero (orden inverso): su fallo no debe cortar el resto
    # Sesión que no se puede cerrar (como la de un proceso ajeno): se anula el cierre de sesiones
    # propias y se acorta el plazo para que BD_OCUPADA agote el plazo de verdad.
    monkeypatch.setattr(modulo, "_cerrar_sesiones_propias", lambda admin, nombre: None)
    monkeypatch.setattr(modulo, "PLAZO_BD_EFIMERA_S", 0.1)
    rezagada = _conectar(BD_OCUPADA)
    try:
        with pytest.raises(AssertionError) as error:
            bd_efimera.eliminar_todas()
        mensaje = str(error.value)
        assert "No se pudieron eliminar 1 BD efímera(s)" in mensaje
        assert BD_OCUPADA in mensaje
        assert "sigue en uso" in mensaje
        assert BD_LIBRE not in mensaje
        assert not _existe(BD_LIBRE)
        assert _existe(BD_OCUPADA)
    finally:
        rezagada.close()
        monkeypatch.undo()
    bd_efimera.eliminar_todas()  # ya sin la sesión: idempotente y sin errores
    assert not _existe(BD_OCUPADA)


def test_TKT063_eliminar_todas_agrega_todos_los_fallos_y_no_repite_bds(bd_efimera, monkeypatch):
    modulo = sys.modules[type(bd_efimera).__module__]
    llamadas: list[str] = []

    def falla(nombre: str) -> None:
        llamadas.append(nombre)
        if nombre == "b":
            raise psycopg.errors.InsufficientPrivilege("sin privilegio")
        raise AssertionError(f"{nombre} sigue en uso tras 60 s: []")

    bds = type(bd_efimera)()
    bds.creadas = ["a", "b", "a", "c"]
    monkeypatch.setattr(modulo, "eliminar_bd_efimera", falla)
    with pytest.raises(AssertionError) as error:
        bds.eliminar_todas()
    assert llamadas == ["c", "a", "b"]
    mensaje = str(error.value)
    assert "No se pudieron eliminar 3 BD efímera(s)" in mensaje
    assert "b: InsufficientPrivilege: sin privilegio" in mensaje
    assert "c: AssertionError: c sigue en uso" in mensaje
