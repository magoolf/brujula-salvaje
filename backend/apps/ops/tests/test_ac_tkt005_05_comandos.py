"""AC-TKT005-05: comandos del planificador idempotentes, con advisory lock y registro.

Nombres exactos de infra/scheduler/crontab y scripts/ops/post-restore-local.sh (RSK-OPS-030):
purgar_ops, purgar_sesiones, reindexar_busqueda y verificar_busqueda. purgar_ops purga además
las entradas caducadas de cache_limites (RSK-QA004-02) y la idempotencia vencida (DEC-AUTO-127).
"""

from __future__ import annotations

import io
from datetime import timedelta

import psycopg
import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.utils import timezone

from apps.busqueda.models import BusquedaDocumento
from apps.contenido.tests.fabricas import crear_cuenta, huella
from apps.cuentas.models import SesionPanel
from apps.cuentas.sesiones import SessionStore
from apps.ops import services
from apps.ops.models import (
    IdempotenciaPeticion,
    OpsEjecucionTarea,
    ResultadoTarea,
    TareaProgramada,
)

pytestmark = pytest.mark.django_db

COMANDOS = {
    "purgar_ops": TareaProgramada.PURGA_OPS,
    "purgar_sesiones": TareaProgramada.PURGA_SESIONES,
    "reindexar_busqueda": TareaProgramada.REINDEX_BUSQUEDA,
    "verificar_busqueda": TareaProgramada.VERIFICACION_BUSQUEDA,
}


def _ejecutar(nombre: str) -> str:
    salida = io.StringIO()
    call_command(nombre, stdout=salida)
    return salida.getvalue()


def _registros(tarea: str) -> list[OpsEjecucionTarea]:
    return list(OpsEjecucionTarea.objects.filter(tarea=tarea).order_by("id"))


def _conexion_externa() -> psycopg.Connection:
    datos = connection.settings_dict
    return psycopg.connect(
        host=datos["HOST"],
        port=datos["PORT"],
        user=datos["USER"],
        password=datos["PASSWORD"],
        dbname=datos["NAME"],
        autocommit=True,
    )


@pytest.mark.parametrize(("nombre", "tarea"), sorted(COMANDOS.items()))
def test_AC_TKT005_05_registra_exito_y_es_idempotente(mundo, nombre, tarea):
    _ejecutar(nombre)
    _ejecutar(nombre)
    registros = _registros(tarea)
    assert [r.resultado for r in registros] == [ResultadoTarea.EXITO, ResultadoTarea.EXITO]
    assert all(r.finalizado_en is not None for r in registros)
    assert registros[0].filas_afectadas == registros[1].filas_afectadas or nombre in (
        "purgar_ops",
        "purgar_sesiones",
    )


@pytest.mark.parametrize(("nombre", "tarea"), sorted(COMANDOS.items()))
def test_AC_TKT005_05_sin_lock_sale_con_0_y_no_hace_nada(db, nombre, tarea):
    with _conexion_externa() as otra:
        otra.execute("SELECT pg_advisory_lock(hashtext(%s))", [str(tarea)])
        salida = _ejecutar(nombre)
    assert "otro proceso tiene el lock" in salida
    assert _registros(tarea) == []
    # Liberado el lock (la otra conexión se cerró), vuelve a ejecutarse.
    _ejecutar(nombre)
    assert len(_registros(tarea)) == 1


def test_AC_TKT005_05_purgar_ops_tareas_idempotencia_y_cache(db):
    ahora = timezone.now()
    vieja = OpsEjecucionTarea.objects.create(tarea=TareaProgramada.PURGA_AUDITORIA)
    OpsEjecucionTarea.objects.filter(pk=vieja.pk).update(iniciado_en=ahora - timedelta(days=31))
    reciente = OpsEjecucionTarea.objects.create(tarea=TareaProgramada.PURGA_AUDITORIA)
    cuenta = crear_cuenta("operador.ops")
    comunes = {
        "cuenta": cuenta,
        "operacion": "panelCrearDestino",
        "codigo_http": 201,
        "cuerpo_respuesta": {"ok": True},
    }
    vencida = IdempotenciaPeticion.objects.create(
        clave="00000000-0000-4000-8000-000000000001", huella_peticion=huella("a"), **comunes
    )
    IdempotenciaPeticion.objects.filter(pk=vencida.pk).update(
        creado_en=ahora - timedelta(hours=30), expira_en=ahora - timedelta(hours=6)
    )
    vigente = IdempotenciaPeticion.objects.create(
        clave="00000000-0000-4000-8000-000000000002", huella_peticion=huella("b"), **comunes
    )
    cache.set("limite:prueba:caducada", 1, timeout=1)
    cache.set("limite:prueba:vigente", 1, timeout=600)
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE cache_limites SET expires = %s WHERE cache_key LIKE %s",
            [ahora - timedelta(minutes=5), "%limite:prueba:caducada"],
        )

    salida = _ejecutar("purgar_ops")

    assert "idempotencia=1" in salida
    assert "cache=1" in salida
    assert not OpsEjecucionTarea.objects.filter(pk=vieja.pk).exists()
    assert OpsEjecucionTarea.objects.filter(pk=reciente.pk).exists()
    assert not IdempotenciaPeticion.objects.filter(pk=vencida.pk).exists()
    assert IdempotenciaPeticion.objects.filter(pk=vigente.pk).exists()
    assert cache.get("limite:prueba:vigente") == 1
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM cache_limites WHERE cache_key LIKE %s", ["%prueba%"])
        assert cursor.fetchone()[0] == 1
    registro = _registros(TareaProgramada.PURGA_OPS)[-1]
    assert registro.filas_afectadas == 3
    assert registro.detalle == "ops=1 idempotencia=1 cache=1"


def test_AC_TKT005_05_purgar_sesiones_solo_las_expiradas(db):
    viva, muerta = SessionStore(), SessionStore()
    viva.create()
    muerta.create()
    SesionPanel.objects.filter(session_key=muerta.session_key).update(
        expire_date=timezone.now() - timedelta(minutes=1)
    )
    _ejecutar("purgar_sesiones")
    claves = set(SesionPanel.objects.values_list("session_key", flat=True))
    assert viva.session_key in claves
    assert muerta.session_key not in claves


def test_AC_TKT005_05_reindexar_y_verificar_busqueda(mundo):
    BusquedaDocumento.objects.all().delete()
    with pytest.raises(CommandError, match="faltan=11"):
        _ejecutar("verificar_busqueda")
    fallo = _registros(TareaProgramada.VERIFICACION_BUSQUEDA)[-1]
    assert fallo.resultado == ResultadoTarea.FALLO
    assert fallo.detalle == "publicados=11 indexados=0 faltan=11 sobran=0"
    salida = _ejecutar("reindexar_busqueda")
    assert "documentos=11" in salida
    assert BusquedaDocumento.objects.count() == 11
    _ejecutar("verificar_busqueda")
    assert _registros(TareaProgramada.VERIFICACION_BUSQUEDA)[-1].resultado == ResultadoTarea.EXITO


def test_AC_TKT005_05_error_inesperado_queda_registrado_como_fallo(db, monkeypatch, logs_json):
    def roto() -> services.Resultado:
        raise ValueError("detalle-interno-no-registrable")

    monkeypatch.setitem(services.TRABAJOS, "purgar_ops", (TareaProgramada.PURGA_OPS, roto))
    with pytest.raises(ValueError, match="detalle-interno"):
        _ejecutar("purgar_ops")
    registro = _registros(TareaProgramada.PURGA_OPS)[-1]
    assert (registro.resultado, registro.detalle) == (ResultadoTarea.FALLO, "error: ValueError")
    assert "detalle-interno-no-registrable" not in logs_json.texto()
    # El lock se liberó aunque la tarea fallara.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(hashtext('PURGA_OPS'))")
        assert cursor.fetchone()[0] is True
        cursor.execute("SELECT pg_advisory_unlock(hashtext('PURGA_OPS'))")
