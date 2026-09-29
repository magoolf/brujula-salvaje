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
from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from apps.busqueda import selectors as busqueda_selectors
from apps.busqueda import services as busqueda_services
from apps.ops.models import IdempotenciaPeticion, OpsEjecucionTarea, ResultadoTarea, TareaProgramada

logger = structlog.get_logger("brujula.ops")

RETENCION_OPS = timedelta(days=30)
LARGO_DETALLE = 500

# DEVOPS_HANDOFF.md §19.3.6, mismos valores por defecto que infra/ops/cache_limites_tamano.sql
# (-v max_filas / -v max_bytes). No están en settings (fuera de archivos_permitidos de TKT-011):
# se leen con getattr(settings, ..., <valor por defecto de aquí>), así que si algún día se añaden
# a settings se respetan sin ampliar el alcance de este ticket.
CACHE_LIMITES_MAX_FILAS_POR_DEFECTO = 50_000
CACHE_LIMITES_MAX_BYTES_POR_DEFECTO = 67_108_864  # 64 MiB


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


# anonimizar_cuentas y reaplicar_anonimizaciones comparten lock: nunca se solapan (§4.3).
CLAVE_LOCK = {
    TareaProgramada.ANONIMIZACION_CUENTAS: "CUENTAS_LIBRO",
    TareaProgramada.REAPLICAR_ANONIMIZACIONES: "CUENTAS_LIBRO",
}


def ejecutar(tarea: TareaProgramada, trabajo: Callable[[], Resultado]) -> Ejecucion:
    """Ejecuta `trabajo` con lock consultivo y registro. Lanza TareaFallida si no tuvo éxito."""
    clave = CLAVE_LOCK.get(tarea, str(tarea))
    if not _tomar_lock(clave):
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
        _soltar_lock(clave)


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
    resultado = busqueda_services.reindexar_todo()
    return Resultado(
        filas=resultado.documentos,
        detalle=f"documentos={resultado.documentos} omitidos={resultado.omitidos}",
        exito=resultado.omitidos == 0,
    )


def verificar_busqueda() -> Resultado:
    """VERIFICACION_BUSQUEDA: recuento de publicados en alcance = filas del índice."""
    estado = busqueda_selectors.estado_indice()
    detalle = (
        f"publicados={estado.publicados} indexados={estado.indexados} "
        f"faltan={estado.faltan} sobran={estado.sobran}"
    )
    return Resultado(filas=estado.indexados, detalle=detalle, exito=estado.coherente)


def vigilar_cache_limites() -> Resultado:
    """VIGILAR_CACHE_LIMITES (RSK-QA004-02, RSK-OPS-032, DEVOPS_HANDOFF §19.3.6): alerta si
    `cache_limites` (tabla UNLOGGED, throttling/bloqueos, TTL <= 1 h) supera el umbral de filas o
    el de tamaño en disco (tabla + índices + TOAST). Misma consulta y mismos umbrales por defecto
    que `infra/ops/cache_limites_tamano.sql` (solo lectura, propiedad de DevOps, no se modifica).

    Ese script SQL también contempla el rol `readonly`, que por diseño no tiene SELECT sobre
    `cache_limites` (ADR-DB-001) y por eso recurre a la estimación de `pg_class.reltuples`. Este
    comando corre con la conexión habitual de Django (`DB_USER` por defecto `app_rw`), que SÍ
    tiene SELECT sobre la tabla (DB_HANDOFF roles.app_rw: "... y cache_limites"; lo confirma
    también `purgar_ops()`, que ya hace DELETE sobre ella con esta misma conexión): el recuento de
    filas es siempre un COUNT(*) exacto, sin necesidad de ese fallback de estimación.
    """
    max_filas = getattr(settings, "CACHE_LIMITES_MAX_FILAS", CACHE_LIMITES_MAX_FILAS_POR_DEFECTO)
    max_bytes = getattr(settings, "CACHE_LIMITES_MAX_BYTES", CACHE_LIMITES_MAX_BYTES_POR_DEFECTO)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*), count(*) FILTER (WHERE expires < now()), "
            "pg_total_relation_size('cache_limites') FROM cache_limites"
        )
        filas, caducadas, tamano_bytes = cursor.fetchone()
    supera_umbral = filas > max_filas or tamano_bytes > max_bytes
    detalle = (
        f"filas={filas} caducadas={caducadas} bytes={tamano_bytes} "
        f"max_filas={max_filas} max_bytes={max_bytes}"
    )
    return Resultado(filas=filas, detalle=detalle, exito=not supera_umbral)


def purgar_auditoria() -> Resultado:
    """PURGA_AUDITORIA (ADR-DB-004 §1.3): eventos > 365 días con app.fn_auditoria_purgar()."""
    from apps.auditoria.services import purgar_eventos_caducados

    purgados = purgar_eventos_caducados()
    return Resultado(filas=purgados, detalle=f"eventos={purgados}")


def _ids(ids: list[int]) -> str:
    return ",".join(map(str, ids[:30])) + ("..." if len(ids) > 30 else "")


def _detalle(partes: dict[str, list[int]], extra: list[str] | None = None) -> str:
    texto = " ".join(
        [
            f"{motivo}={len(ids)}" + (f"[{_ids(ids)}]" if ids else "")
            for motivo, ids in partes.items()
        ]
        + (extra or [])
    )
    return texto[:LARGO_DETALLE]


def anonimizar_cuentas() -> Resultado:
    """ANONIMIZACION_CUENTAS (ADR-DB-004 §2 y §4.3): desactivación vigente de más de 30 días."""
    from apps.cuentas import libro
    from apps.cuentas.services import anonimizar_cuentas_vencidas

    try:
        r = anonimizar_cuentas_vencidas()
    except libro.ErrorLibro as error:
        return Resultado(filas=0, detalle=str(error)[:LARGO_DETALLE], exito=False)
    detalle = _detalle(
        {"anonimizadas": r.anonimizadas, "OMITIDA_REACTIVADA": r.omitidas_reactivada},
        ["LIBRO_AUSENTE_SOLO_BD"] if r.libro_ausente else None,
    )
    return Resultado(filas=len(r.anonimizadas), detalle=detalle)


def reaplicar_anonimizaciones(*, libro_vacio_confirmado: bool = False) -> Resultado:
    """REAPLICAR_ANONIMIZACIONES (ADR-DB-004 §4.3-§4.4): relectura del libro tras restaurar.

    LIBRO_AUSENTE/ILEGIBLE/CORRUPTO → FALLO sin cambios (exit != 0); avisos → EXITO con detalle.
    """
    from apps.cuentas import libro
    from apps.cuentas.services import reaplicar_libro_anonimizaciones

    try:
        r = reaplicar_libro_anonimizaciones(libro_vacio_confirmado=libro_vacio_confirmado)
    except libro.ErrorLibro as error:
        return Resultado(filas=0, detalle=str(error)[:LARGO_DETALLE], exito=False)
    partes = {
        "desactivadas": r.desactivadas,
        "anonimizadas": r.anonimizadas,
        "alineadas": r.alineadas,
        **r.avisos(),
        "inexistentes": r.inexistentes,
    }
    extra = [f"avisos_libro={len(r.avisos_libro)}"] if r.avisos_libro else None
    return Resultado(
        filas=len(r.desactivadas) + len(r.anonimizadas) + len(r.alineadas),
        detalle=_detalle(partes, extra),
    )


TRABAJOS: dict[str, tuple[TareaProgramada, Callable[..., Resultado]]] = {
    "anonimizar_cuentas": (TareaProgramada.ANONIMIZACION_CUENTAS, anonimizar_cuentas),
    "purgar_auditoria": (TareaProgramada.PURGA_AUDITORIA, purgar_auditoria),
    "purgar_ops": (TareaProgramada.PURGA_OPS, purgar_ops),
    "reaplicar_anonimizaciones": (
        TareaProgramada.REAPLICAR_ANONIMIZACIONES,
        reaplicar_anonimizaciones,
    ),
    "purgar_sesiones": (TareaProgramada.PURGA_SESIONES, purgar_sesiones),
    "reindexar_busqueda": (TareaProgramada.REINDEX_BUSQUEDA, reindexar_busqueda),
    "verificar_busqueda": (TareaProgramada.VERIFICACION_BUSQUEDA, verificar_busqueda),
    "vigilar_cache_limites": (TareaProgramada.VIGILAR_CACHE_LIMITES, vigilar_cache_limites),
}
