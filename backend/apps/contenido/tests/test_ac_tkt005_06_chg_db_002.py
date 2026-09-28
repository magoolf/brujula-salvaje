"""AC-TKT005-06 (CHG-DB-002, DB_HANDOFF v1.2 plan n=16..19, DEC-AUTO-203/204).

- medio: app_rw sin DELETE/TRUNCATE (42501) y trg_medio_sin_borrado también para el propietario
  (23001); medio_derivado conserva DELETE.
- subtipos 1:1: trg_subtipo_guarda_borrado rechaza el DELETE directo del subtipo de un contenido
  publicado alguna vez o de una página; el borrado de borradores sigue funcionando.
- catálogos y singletons de configuración: app_rw sin DELETE ni TRUNCATE; destacado_inicio sí.
- las cuatro migraciones son reversibles (estado v1.1 ↔ v1.2).
"""

from __future__ import annotations

from datetime import date

import psycopg
import pytest
from django.db import IntegrityError, ProgrammingError, connection, transaction

from apps.contenido.models import (
    Coleccion,
    Contenido,
    Destino,
    Guia,
    Itinerario,
    PaginaInstitucional,
    TerminoGlosario,
    TipoAventura,
)
from apps.contenido.tests.fabricas import (
    campos_publicado,
    como_rol,
    crear_contenido,
    crear_medio,
)
from apps.ops.tests.test_ac_tkt003_migraciones import (
    BD_MIGRACIONES,
    _conectar,
    _manage,
    bd_vacia,  # noqa: F401 (fixture reutilizada)
)

pytestmark = pytest.mark.django_db

SUBTIPOS = {
    "TIPO": (TipoAventura, "tipo_aventura"),
    "DESTINO": (Destino, "destino"),
    "ITINERARIO": (Itinerario, "itinerario"),
    "GUIA": (Guia, "guia"),
    "COLECCION": (Coleccion, "coleccion"),
    "TERMINO": (TerminoGlosario, "termino_glosario"),
}
CATALOGOS = ("region", "pais", "categoria_guia", "licencia", "nivel_escala")
SINGLETONS = ("config_inicio", "config_sitio")


def _error_bd(sql: str, parametros: list) -> psycopg.Error:
    with pytest.raises(IntegrityError) as error, transaction.atomic(), connection.cursor() as c:
        c.execute(sql, parametros)
    causa = error.value.__cause__
    assert isinstance(causa, psycopg.Error)
    return causa


def _privilegio(tabla: str, privilegio: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT has_table_privilege('app_rw', %s, %s)", [f"app.{tabla}", privilegio])
        return bool(cursor.fetchone()[0])


# ---------------------------------------------------------------------------
# medios.0002_sin_borrado
# ---------------------------------------------------------------------------
def test_AC_TKT005_06_medio_sin_borrado_para_app_rw_y_propietario():
    medio = crear_medio()
    assert _privilegio("medio", "DELETE") is False
    assert _privilegio("medio", "TRUNCATE") is False
    assert _privilegio("medio", "UPDATE") is True
    assert _privilegio("medio_derivado", "DELETE") is True
    with como_rol("app_rw") as cursor, pytest.raises(ProgrammingError) as error:
        cursor.execute("DELETE FROM app.medio WHERE id = %s", [medio.pk])
    assert error.value.__cause__.sqlstate == "42501"

    causa = _error_bd("DELETE FROM app.medio WHERE id = %s", [medio.pk])
    assert causa.sqlstate == "23001"
    assert causa.diag.constraint_name == "trg_medio_sin_borrado"
    with pytest.raises(IntegrityError), transaction.atomic():
        medio.delete()
    assert type(medio).objects.filter(pk=medio.pk).exists()


def test_AC_TKT005_06_medio_derivado_se_borra_con_app_rw():
    medio = crear_medio()
    derivado = medio.derivados.create(
        formato="WEBP", ancho_px=800, alto_px=600, ruta="derivados/x-800.webp",
        peso_bytes=1000, sha256="a" * 64,
    )  # fmt: skip
    with como_rol("app_rw") as cursor:
        cursor.execute("DELETE FROM app.medio_derivado WHERE id = %s", [derivado.pk])
        assert cursor.rowcount == 1


# ---------------------------------------------------------------------------
# contenido.0003_guardas_subtipos
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("tipo", sorted(SUBTIPOS))
def test_AC_TKT005_06_subtipo_de_contenido_publicado_alguna_vez_no_se_borra(tipo):
    modelo, tabla = SUBTIPOS[tipo]
    contenido = crear_contenido(tipo, **campos_publicado(tipo))
    modelo.objects.create(contenido=contenido)
    causa = _error_bd(f"DELETE FROM app.{tabla} WHERE contenido_id = %s", [contenido.pk])  # noqa: S608  # nosec B608 (tabla de la constante SUBTIPOS)
    assert causa.sqlstate == "23001"
    assert causa.diag.constraint_name == "trg_subtipo_guarda_borrado"
    assert modelo.objects.filter(pk=contenido.pk).exists()


def test_AC_TKT005_06_subtipo_de_retirado_tampoco_se_borra():
    retirado = crear_contenido(
        "DESTINO",
        estado_editorial="RETIRADO",
        primera_publicacion_en="2026-09-01T00:00:00Z",
        retirado_en="2026-09-02T00:00:00Z",
        motivo_retiro="Prueba",
        fecha_ultima_revision=date(2026, 9, 1),
    )
    Destino.objects.create(contenido=retirado)
    causa = _error_bd("DELETE FROM app.destino WHERE contenido_id = %s", [retirado.pk])
    assert causa.diag.constraint_name == "trg_subtipo_guarda_borrado"


def test_AC_TKT005_06_pagina_institucional_no_se_borra_ni_en_borrador():
    pagina = crear_contenido("PAGINA")
    PaginaInstitucional.objects.create(
        contenido=pagina, clave="AVISO_LEGAL", cuerpo="<p>Texto</p>",
        version_documento="1.0", vigente_desde=date(2026, 9, 1),
    )  # fmt: skip
    causa = _error_bd("DELETE FROM app.pagina_institucional WHERE contenido_id = %s", [pagina.pk])
    assert causa.diag.constraint_name == "trg_subtipo_guarda_borrado"


def test_AC_TKT005_06_borradores_nunca_publicados_se_siguen_borrando():
    # Directo sobre el subtipo, por ORM (Collector) y por SQL en cascada.
    directo = crear_contenido("GUIA")
    Guia.objects.create(contenido=directo)
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM app.guia WHERE contenido_id = %s", [directo.pk])
        assert cursor.rowcount == 1

    orm = crear_contenido("DESTINO")
    Destino.objects.create(contenido=orm)
    Contenido.objects.filter(pk=orm.pk).delete()
    assert not Destino.objects.filter(pk=orm.pk).exists()

    sql = crear_contenido("TIPO")
    TipoAventura.objects.create(contenido=sql)
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM app.contenido WHERE id = %s", [sql.pk])
    assert not TipoAventura.objects.filter(pk=sql.pk).exists()


def test_AC_TKT005_06_funciones_de_trigger_con_search_path_seguro():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT p.proname, p.proconfig, p.prosecdef FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'app' "
            "AND p.proname IN ('fn_medio_sin_borrado', 'fn_subtipo_guarda_borrado')"
        )
        filas = {nombre: (config, secdef) for nombre, config, secdef in cursor.fetchall()}
        cursor.execute(
            "SELECT c.relname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
            "WHERE t.tgname = 'trg_subtipo_guarda_borrado' AND t.tgenabled = 'O'"
        )
        tablas = sorted(fila[0] for fila in cursor.fetchall())
    seguro = ["search_path=pg_catalog, app, pg_temp"]
    assert filas == {
        "fn_medio_sin_borrado": (seguro, False),
        "fn_subtipo_guarda_borrado": (seguro, False),
    }
    assert tablas == sorted([t for _m, t in SUBTIPOS.values()] + ["pagina_institucional"])


# ---------------------------------------------------------------------------
# catalogos.0003_sin_borrado e inicio.0002_sin_borrado
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("tabla", CATALOGOS + SINGLETONS)
def test_AC_TKT005_06_catalogos_y_configuracion_sin_delete_para_app_rw(tabla):
    assert _privilegio(tabla, "DELETE") is False
    assert _privilegio(tabla, "TRUNCATE") is False
    assert _privilegio(tabla, "UPDATE") is True
    assert _privilegio(tabla, "INSERT") is True
    with como_rol("app_rw") as cursor, pytest.raises(ProgrammingError) as error:
        cursor.execute(f"DELETE FROM app.{tabla} WHERE false")  # noqa: S608  # nosec B608 (tabla de constantes)
    assert error.value.__cause__.sqlstate == "42501"


def test_AC_TKT005_06_destacado_inicio_conserva_delete():
    assert _privilegio("destacado_inicio", "DELETE") is True


# ---------------------------------------------------------------------------
# Reversibilidad (plan n=16..19)
# ---------------------------------------------------------------------------
def _estado(bd: psycopg.Connection) -> tuple:
    fila = bd.execute(
        "SELECT "
        "(SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_medio_sin_borrado'), "
        "(SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_subtipo_guarda_borrado'), "
        "(SELECT count(*) FROM pg_proc WHERE proname IN "
        "   ('fn_medio_sin_borrado', 'fn_subtipo_guarda_borrado')), "
        "has_table_privilege('app_rw', 'app.medio', 'DELETE'), "
        "has_table_privilege('app_rw', 'app.region', 'DELETE'), "
        "has_table_privilege('app_rw', 'app.nivel_escala', 'DELETE'), "
        "has_table_privilege('app_rw', 'app.config_sitio', 'DELETE'), "
        "has_table_privilege('app_rw', 'app.destacado_inicio', 'DELETE')"
    ).fetchone()
    assert fila is not None
    return tuple(fila)


def test_AC_TKT005_06_migraciones_chg_db_002_reversibles(bd_vacia):  # noqa: F811
    migrar = _manage("migrate")
    assert migrar.returncode == 0, migrar.stderr
    v12 = (1, 7, 2, False, False, False, False, True)
    v11 = (0, 0, 0, True, True, True, True, True)
    with _conectar(BD_MIGRACIONES) as bd:
        assert _estado(bd) == v12
    for app, destino in (
        ("medios", "0001_inicial"),
        ("contenido", "0002_integridad_sql"),
        ("catalogos", "0002_semilla"),
        ("inicio", "0001_inicial"),
    ):
        revertir = _manage("migrate", app, destino)
        assert revertir.returncode == 0, (app, revertir.stderr)
    with _conectar(BD_MIGRACIONES) as bd:
        assert _estado(bd) == v11
    remigrar = _manage("migrate")
    assert remigrar.returncode == 0, remigrar.stderr
    with _conectar(BD_MIGRACIONES) as bd:
        assert _estado(bd) == v12
