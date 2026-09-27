"""AC-TKT004-08 (CHG-DB-002, DB_HANDOFF v1.2, OBS-QA003-01/05): cuenta_staff no se borra.

- app_rw no tiene DELETE ni TRUNCATE sobre cuenta_staff (42501);
- el trigger trg_cuenta_sin_borrado rechaza el borrado también para el propietario (23001);
- el ORM tampoco borra (excepción de dominio o IntegrityError del trigger) y no deja efectos;
- las migraciones cuentas.0002 y auditoria.0003 son reversibles.
"""

from __future__ import annotations

import psycopg
import pytest
from django.db import IntegrityError, ProgrammingError, connection, transaction

from apps.contenido.tests.fabricas import como_rol, crear_cuenta
from apps.cuentas.models import (
    BorradoCuentaProhibidoError,
    CuentaCodigoRecuperacion,
    CuentaStaff,
    RolCuenta,
    SesionPanel,
)
from apps.cuentas.sesiones import SessionStore
from apps.ops.tests.test_ac_tkt003_migraciones import (
    BD_MIGRACIONES,
    _conectar,
    _manage,
    bd_vacia,  # noqa: F401 (fixture reutilizada)
)

pytestmark = pytest.mark.django_db


def _admin_con_dependencias() -> CuentaStaff:
    admin = crear_cuenta("admin.unica.chg", rol=RolCuenta.ADMINISTRADOR)
    CuentaCodigoRecuperacion.objects.create(cuenta=admin, hash_codigo="h" * 64)
    tienda = SessionStore()
    tienda.create()
    SesionPanel.objects.filter(session_key=tienda.session_key).update(cuenta=admin)
    return admin


def test_AC_TKT004_08_app_rw_no_puede_borrar_ni_truncar_cuentas():
    admin = _admin_con_dependencias()
    with como_rol("app_rw") as cursor:
        cursor.execute(
            "SELECT has_table_privilege('app_rw', 'app.cuenta_staff', 'DELETE'), "
            "has_table_privilege('app_rw', 'app.cuenta_staff', 'TRUNCATE'), "
            "has_table_privilege('app_rw', 'app.cuenta_staff', 'UPDATE')"
        )
        assert cursor.fetchone() == (False, False, True)
    with como_rol("app_rw") as cursor, pytest.raises(ProgrammingError) as error:
        cursor.execute("DELETE FROM app.cuenta_staff WHERE id = %s", [admin.pk])
    assert error.value.__cause__.sqlstate == "42501"
    with como_rol("app_rw") as cursor, pytest.raises(ProgrammingError) as error:
        cursor.execute("TRUNCATE app.cuenta_staff CASCADE")
    assert error.value.__cause__.sqlstate == "42501"
    assert CuentaStaff.objects.filter(rol=RolCuenta.ADMINISTRADOR).count() == 1


def test_AC_TKT004_08_trigger_rechaza_el_borrado_del_propietario():
    admin = _admin_con_dependencias()
    with (
        pytest.raises(IntegrityError) as error,
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("DELETE FROM app.cuenta_staff WHERE id = %s", [admin.pk])
    causa = error.value.__cause__
    assert isinstance(causa, psycopg.Error)
    assert causa.sqlstate == "23001"
    assert causa.diag.constraint_name == "trg_cuenta_sin_borrado"
    assert CuentaStaff.objects.filter(pk=admin.pk).exists()


def test_AC_TKT004_08_orm_no_borra_y_no_deja_efectos():
    admin = _admin_con_dependencias()
    # Instancia: excepción de dominio (subclase de IntegrityError) antes de tocar la BD.
    with pytest.raises(BorradoCuentaProhibidoError):
        admin.delete()
    # QuerySet: el colector borra primero sesiones y códigos; el trigger aborta y todo se deshace.
    with pytest.raises(IntegrityError), transaction.atomic():
        CuentaStaff.objects.filter(pk=admin.pk).delete()
    assert CuentaStaff.objects.filter(pk=admin.pk).exists()
    assert SesionPanel.objects.filter(cuenta=admin).count() == 1
    assert CuentaCodigoRecuperacion.objects.filter(cuenta=admin).count() == 1


def test_AC_TKT004_08_triggers_de_cuenta_con_search_path_seguro():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT p.proconfig FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'app' AND p.proname = 'fn_cuenta_sin_borrado'"
        )
        assert cursor.fetchone()[0] == ["search_path=pg_catalog, app, pg_temp"]
        cursor.execute(
            "SELECT tgenabled FROM pg_trigger WHERE tgname = 'trg_cuenta_sin_borrado' "
            "AND tgrelid = 'app.cuenta_staff'::regclass"
        )
        assert cursor.fetchone() == ("O",)


def _estado_chg_db_002(bd: psycopg.Connection) -> tuple:
    fila = bd.execute(
        "SELECT "
        "(SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_cuenta_sin_borrado'), "
        "(SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_revision_inmutable'), "
        "has_table_privilege('app_rw', 'app.cuenta_staff', 'DELETE'), "
        "(SELECT proconfig FROM pg_proc WHERE proname = 'fn_auditoria_purgar')"
    ).fetchone()
    assert fila is not None
    return tuple(fila)


def test_AC_TKT004_08_migraciones_chg_db_002_reversibles(bd_vacia):  # noqa: F811
    migrar = _manage("migrate")
    assert migrar.returncode == 0, migrar.stderr
    v12 = (1, 1, False, ["search_path=pg_catalog, app, pg_temp"])
    v11 = (0, 0, True, ["search_path=pg_catalog, app"])
    with _conectar(BD_MIGRACIONES) as bd:
        assert _estado_chg_db_002(bd) == v12
    for app, destino in (("cuentas", "0001_inicial"), ("auditoria", "0002_inmutabilidad")):
        revertir = _manage("migrate", app, destino)
        assert revertir.returncode == 0, (app, revertir.stderr)
    with _conectar(BD_MIGRACIONES) as bd:
        assert _estado_chg_db_002(bd) == v11
    remigrar = _manage("migrate")
    assert remigrar.returncode == 0, remigrar.stderr
    with _conectar(BD_MIGRACIONES) as bd:
        assert _estado_chg_db_002(bd) == v12
