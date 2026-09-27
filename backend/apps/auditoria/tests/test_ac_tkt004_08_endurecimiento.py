"""AC-TKT004-08 (CHG-DB-002, OBS-QA003-05): auditoria.0003_endurecimiento.

- Toda función SECURITY DEFINER de app fija search_path 'pg_catalog, app, pg_temp', pertenece a
  app_migrator y solo app_rw puede ejecutarla.
- revision_contenido es inmutable también para el propietario (trigger) y para app_rw (42501).
"""

from __future__ import annotations

import psycopg
import pytest
from django.db import IntegrityError, ProgrammingError, connection, transaction

from apps.auditoria.models import MotivoRevision, RevisionContenido
from apps.contenido.tests.fabricas import como_rol, crear_contenido

pytestmark = pytest.mark.django_db


def test_AC_TKT004_08_funciones_security_definer_endurecidas():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT p.proname, p.proconfig, pg_get_userbyid(p.proowner), "
            "has_function_privilege('app_rw', p.oid, 'EXECUTE'), "
            "has_function_privilege('readonly', p.oid, 'EXECUTE'), "
            "has_function_privilege('app_backup', p.oid, 'EXECUTE') "
            "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'app' AND p.prosecdef"
        )
        filas = cursor.fetchall()
    assert {fila[0] for fila in filas} == {"fn_auditoria_purgar", "fn_auditoria_seudonimizar"}
    for nombre, config, propietario, rw, lectura, copia in filas:
        assert config == ["search_path=pg_catalog, app, pg_temp"], nombre
        assert propietario == "app_migrator", nombre
        assert (rw, lectura, copia) == (True, False, False), nombre


def _revision() -> RevisionContenido:
    contenido = crear_contenido("DESTINO")
    return RevisionContenido.objects.create(
        contenido=contenido,
        tipo_contenido="DESTINO",
        numero_revision=1,
        motivo=MotivoRevision.PUBLICACION,
        instantanea={"titulo": "x"},
    )


@pytest.mark.parametrize(
    ("sentencia", "sqlstate"),
    [
        ("UPDATE app.revision_contenido SET motivo = 'RETIRO' WHERE id = %s", "23514"),
        ("DELETE FROM app.revision_contenido WHERE id = %s", "23001"),
    ],
)
def test_AC_TKT004_08_revision_inmutable_para_el_propietario(sentencia, sqlstate):
    revision = _revision()
    with (
        pytest.raises(IntegrityError) as error,
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(sentencia, [revision.pk])
    causa = error.value.__cause__
    assert isinstance(causa, psycopg.Error)
    assert causa.sqlstate == sqlstate
    assert causa.diag.constraint_name == "trg_revision_inmutable"


@pytest.mark.parametrize(
    "sentencia",
    [
        "UPDATE app.revision_contenido SET motivo = 'RETIRO' WHERE id = %s",
        "DELETE FROM app.revision_contenido WHERE id = %s",
    ],
)
def test_AC_TKT004_08_revision_inmutable_para_app_rw(sentencia):
    revision = _revision()
    with como_rol("app_rw") as cursor, pytest.raises(ProgrammingError) as error:
        cursor.execute(sentencia, [revision.pk])
    assert error.value.__cause__.sqlstate == "42501"
