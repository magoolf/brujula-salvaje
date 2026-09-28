"""Tareas programadas de operación (FEAT-048, ADR-DB-004, ADR-DB-005 §1, DEC-AUTO-090/144).

Contrato común de todos los comandos del planificador (infra/scheduler/crontab):
- Exclusión mutua con pg_try_advisory_lock(hashtext('<TAREA>')): si otro proceso la tiene, el
  comando sale con código 0 sin hacer nada (y sin registrar).
- Registro en ops_ejecucion_tarea: EN_CURSO al empezar; EXITO o FALLO con filas afectadas al
  terminar. `detalle` solo lleva recuentos o el tipo de error, nunca PII (REQ-057, THREAT-020).
- Idempotentes: repetirlos no cambia el resultado (DELETE por condición temporal, reconstrucción).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

import structlog
from django.db import connection, transaction
from django.utils import timezone

from apps.busqueda import selectors as busqueda_selectors
from apps.busqueda import services as busqueda_services
from apps.ops.models import IdempotenciaPeticion, OpsEjecucionTarea, ResultadoTarea, TareaProgramada

logger = structlog.get_logger("brujula.ops")

RETENCION_OPS = timedelta(days=30)
LARGO_DETALLE = 500


@dataclass(frozen=True)
class Resultado:
    filas: int | None
    detalle: str | None = None
    exito: bool = True


class TareaFallida(Exception):  # noqa: N818 (nombre de dominio)
    """La tarea terminó y quedó registrada como FALLO (p. ej. índice de búsqueda incoherente)."""


@dataclass(frozen=True)
class Ejecucion:
    ejecutada: bool
    registro: OpsEjecucionTarea | None = None


def _tomar_lock(tarea: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(hashtext(%s))", [tarea])
        fila = cursor.fetchone()
    return bool(fila and fila[0])


def _soltar_lock(tarea: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))", [tarea])


def ejecutar(tarea: TareaProgramada, trabajo: Callable[[], Resultado]) -> Ejecucion:
    """Ejecuta `trabajo` con lock consultivo y registro. Lanza TareaFallida si no tuvo éxito."""
    if not _tomar_lock(tarea):
        logger.info("tarea_omitida_lock_ocupado", tarea=str(tarea))
        return Ejecucion(ejecutada=False)
    inicio = time.perf_counter()
    try:
        registro = OpsEjecucionTarea.objects.create(tarea=tarea)
        try:
            resultado = trabajo()
        except Exception as exc:
            _cerrar(registro, ResultadoTarea.FALLO, None, f"error: {type(exc).__name__}")
            logger.error("tarea_fallida", tarea=str(tarea), tipo=type(exc).__name__)
            raise
        estado = ResultadoTarea.EXITO if resultado.exito else ResultadoTarea.FALLO
        _cerrar(registro, estado, resultado.filas, resultado.detalle)
        logger.info(
            "tarea_finalizada",
            tarea=str(tarea),
            resultado=str(estado),
            filas=resultado.filas,
            duration_ms=round((time.perf_counter() - inicio) * 1000, 1),
        )
        if not resultado.exito:
            raise TareaFallida(resultado.detalle or str(tarea))
        return Ejecucion(ejecutada=True, registro=registro)
    finally:
        _soltar_lock(tarea)


def _cerrar(
    registro: OpsEjecucionTarea, resultado: str, filas: int | None, detalle: str | None
) -> None:
    registro.resultado = resultado
    registro.filas_afectadas = filas
    registro.detalle = detalle[:LARGO_DETALLE] if detalle else None
    registro.finalizado_en = timezone.now()
    registro.save(update_fields=["resultado", "filas_afectadas", "detalle", "finalizado_en"])


# ---------------------------------------------------------------------------
# Trabajos
# ---------------------------------------------------------------------------
def purgar_ops() -> Resultado:
    """PURGA_OPS (DEC-AUTO-127, RSK-QA004-02): registro de tareas > 30 días, claves de
    idempotencia vencidas y entradas caducadas de la caché de límites/bloqueos."""
    ahora = timezone.now()
    with transaction.atomic():
        tareas, _ = OpsEjecucionTarea.objects.filter(iniciado_en__lt=ahora - RETENCION_OPS).delete()
        claves, _ = IdempotenciaPeticion.objects.filter(expira_en__lte=ahora).delete()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM cache_limites WHERE expires < %s", [ahora])
            cache = cursor.rowcount
    return Resultado(
        filas=tareas + claves + cache,
        detalle=f"ops={tareas} idempotencia={claves} cache={cache}",
    )


def purgar_sesiones() -> Resultado:
    """PURGA_SESIONES (ADR-DB-004 §2): sesiones del panel expiradas, con el motor de sesiones
    del panel (apps.cuentas.sesiones.SessionStore.clear_expired, API pública de Django)."""
    from apps.cuentas.sesiones import SessionStore

    SessionStore.clear_expired()
    return Resultado(filas=None, detalle="sesiones expiradas eliminadas")


def reindexar_busqueda() -> Resultado:
    """REINDEX_BUSQUEDA (ADR-DB-003 §2): DELETE + INSERT del índice en una transacción."""
    documentos = busqueda_services.reindexar_todo()
    return Resultado(filas=documentos, detalle=f"documentos={documentos}")


def verificar_busqueda() -> Resultado:
    """VERIFICACION_BUSQUEDA: recuento de publicados en alcance = filas del índice."""
    estado = busqueda_selectors.estado_indice()
    detalle = (
        f"publicados={estado.publicados} indexados={estado.indexados} "
        f"faltan={estado.faltan} sobran={estado.sobran}"
    )
    return Resultado(filas=estado.indexados, detalle=detalle, exito=estado.coherente)


TRABAJOS: dict[str, tuple[TareaProgramada, Callable[[], Resultado]]] = {
    "purgar_ops": (TareaProgramada.PURGA_OPS, purgar_ops),
    "purgar_sesiones": (TareaProgramada.PURGA_SESIONES, purgar_sesiones),
    "reindexar_busqueda": (TareaProgramada.REINDEX_BUSQUEDA, reindexar_busqueda),
    "verificar_busqueda": (TareaProgramada.VERIFICACION_BUSQUEDA, verificar_busqueda),
}
