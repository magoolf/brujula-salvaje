"""TKT-011 (RSK-QA004-02, RSK-OPS-032, DEVOPS_HANDOFF §19.3.6): comando vigilar_cache_limites.

Misma consulta y mismos umbrales por defecto que infra/ops/cache_limites_tamano.sql (solo
lectura, propiedad de DevOps, no se toca en este ticket): >50 000 filas o >64 MiB (tabla +
índices + TOAST) en `cache_limites`. Sigue el contrato común de apps.ops.management.tarea /
apps.ops.services (lock consultivo, registro en ops_ejecucion_tarea, exit != 0 si falla) que ya
prueba test_ac_tkt005_05_comandos.py; aquí solo se cubre lo propio de este comando.
"""

from __future__ import annotations

import io

import psycopg
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.utils import timezone

from apps.ops import services
from apps.ops.models import OpsEjecucionTarea, ResultadoTarea, TareaProgramada

pytestmark = pytest.mark.django_db

NOMBRE = "vigilar_cache_limites"
TAREA = TareaProgramada.VIGILAR_CACHE_LIMITES


def _ejecutar() -> str:
    salida = io.StringIO()
    call_command(NOMBRE, stdout=salida)
    return salida.getvalue()


def _registros() -> list[OpsEjecucionTarea]:
    return list(OpsEjecucionTarea.objects.filter(tarea=TAREA).order_by("id"))


def _insertar_filas(n: int, *, caducadas: int = 0) -> None:
    """Inserta `n` filas reales en cache_limites (esquema de createcachetable); las primeras
    `caducadas` ya vencieron."""
    ahora = timezone.now()
    pasada = ahora - timezone.timedelta(minutes=5)
    futura = ahora + timezone.timedelta(hours=1)
    with connection.cursor() as cursor:
        for i in range(n):
            expira = pasada if i < caducadas else futura
            cursor.execute(
                "INSERT INTO cache_limites (cache_key, value, expires) VALUES (%s, %s, %s)",
                [f"limite:tkt011:{i}", "1", expira],
            )


def test_AC_TKT011_bajo_umbral_exito_con_recuento_exacto(db):
    _insertar_filas(7, caducadas=3)

    salida = _ejecutar()

    assert "EXITO" in salida
    registro = _registros()[-1]
    assert registro.resultado == ResultadoTarea.EXITO
    # Recuento EXACTO (COUNT(*)), no una estimación de pg_class.reltuples: las filas se acaban de
    # insertar en esta misma transacción de prueba, sin ANALYZE, así que reltuples seguiría
    # marcando 0 y este assert fallaría si el comando usara la estimación.
    assert registro.filas_afectadas == 7
    assert registro.detalle.startswith("filas=7 caducadas=3 bytes=")
    assert "max_filas=50000 max_bytes=67108864" in registro.detalle


def test_AC_TKT011_supera_max_filas_falla_con_exit_no_cero(db, settings):
    settings.CACHE_LIMITES_MAX_FILAS = 2
    _insertar_filas(3)

    with pytest.raises(CommandError, match="filas=3"):
        _ejecutar()

    registro = _registros()[-1]
    assert registro.resultado == ResultadoTarea.FALLO
    assert "max_filas=2" in registro.detalle


def test_AC_TKT011_supera_max_bytes_falla_aunque_haya_pocas_filas(db, settings):
    settings.CACHE_LIMITES_MAX_BYTES = 1
    _insertar_filas(1)

    with pytest.raises(CommandError, match="filas=1"):
        _ejecutar()

    registro = _registros()[-1]
    assert registro.resultado == ResultadoTarea.FALLO
    assert "max_bytes=1" in registro.detalle


def test_AC_TKT011_dentro_de_ambos_umbrales_no_falla_por_defecto(db):
    """Sin overrides de settings: getattr(settings, ..., <por defecto>) cae en los valores de
    services.CACHE_LIMITES_MAX_FILAS_POR_DEFECTO / _MAX_BYTES_POR_DEFECTO (DEVOPS_HANDOFF §19.3.6),
    sin que este ticket haya tocado backend/config/settings/base.py."""
    from django.conf import settings as django_settings

    assert not hasattr(django_settings, "CACHE_LIMITES_MAX_FILAS")
    assert not hasattr(django_settings, "CACHE_LIMITES_MAX_BYTES")

    _insertar_filas(5)
    _ejecutar()

    registro = _registros()[-1]
    assert registro.resultado == ResultadoTarea.EXITO
    assert (
        f"max_filas={services.CACHE_LIMITES_MAX_FILAS_POR_DEFECTO} "
        f"max_bytes={services.CACHE_LIMITES_MAX_BYTES_POR_DEFECTO}"
    ) in registro.detalle


def test_AC_TKT011_registra_exito_y_es_idempotente(db):
    _ejecutar()
    _ejecutar()
    registros = _registros()
    assert [r.resultado for r in registros] == [ResultadoTarea.EXITO, ResultadoTarea.EXITO]
    assert all(r.finalizado_en is not None for r in registros)
    assert registros[0].filas_afectadas == registros[1].filas_afectadas == 0


def test_AC_TKT011_sin_lock_sale_con_0_y_no_hace_nada(db):
    datos = connection.settings_dict
    with psycopg.connect(
        host=datos["HOST"],
        port=datos["PORT"],
        user=datos["USER"],
        password=datos["PASSWORD"],
        dbname=datos["NAME"],
        autocommit=True,
    ) as otra:
        otra.execute("SELECT pg_advisory_lock(hashtext(%s))", [str(TAREA)])
        salida = _ejecutar()
    assert "otro proceso tiene el lock" in salida
    assert _registros() == []
    # Liberado el lock (la otra conexión se cerró), vuelve a ejecutarse.
    _ejecutar()
    assert len(_registros()) == 1
