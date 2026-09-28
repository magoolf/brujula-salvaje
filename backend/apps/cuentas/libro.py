"""Libro de anonimizaciones v2 (ADR-DB-004 §4.1-§4.5, CHG-DB-003, DEC-AUTO-260..264).

Fichero de texto append-only fuera de las copias de la BD, con una línea por transición de cuenta:
`cuenta_id;EVENTO;YYYY-MM-DDTHH:MM:SSZ`, EVENTO ∈ DESACTIVADA | REACTIVADA | ANONIMIZADA. Solo ids,
nunca PII. Las líneas que empiezan por `#` son de control (`#REPARACION;<fecha>`).

- Escritura (§4.2): DENTRO de la transacción de la operación y como último paso, tras comprobar
  RULE-015 (`SET CONSTRAINTS app.trg_cuenta_admin_minimo IMMEDIATE`); O_APPEND + O_NOFOLLOW +
  modo 0640, flock exclusivo, reparación de una cola sin salto de línea, un único write() y fsync.
  Cualquier OSError deshace la operación (fail-closed) y el cliente recibe un 503 genérico.
- Lectura (§4.3): O_NOFOLLOW + flock compartido; fichero regular no escribible por "otros". El
  último evento de una cuenta es su última línea válida en el ORDEN DEL FICHERO; la desactivación
  vigente es la última DESACTIVADA posterior a la última REACTIVADA. Una cola sin salto de línea o
  una línea mal formada seguida de #REPARACION se ignoran con aviso; cualquier otra línea mal
  formada hace el libro CORRUPTO.
"""

from __future__ import annotations

import os
import re
import stat
import sys
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from django.conf import settings
from django.db import connection

from apps.core.exceptions import ErrorApi

if TYPE_CHECKING:
    from collections.abc import Iterator


logger = structlog.get_logger("brujula.cuentas")

DESACTIVADA = "DESACTIVADA"
REACTIVADA = "REACTIVADA"
ANONIMIZADA = "ANONIMIZADA"
EVENTOS = (DESACTIVADA, REACTIVADA, ANONIMIZADA)
FORMATO_FECHA = "%Y-%m-%dT%H:%M:%SZ"
PREFIJO_REPARACION = "#REPARACION;"
MARGEN_FUTURO = timedelta(minutes=5)
MODO = 0o640
_LINEA = re.compile(
    r"^([1-9][0-9]{0,18});(DESACTIVADA|REACTIVADA|ANONIMIZADA);"
    r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z)$"
)
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_BINARIO = getattr(os, "O_BINARY", 0)

LIBRO_AUSENTE = "LIBRO_AUSENTE"
LIBRO_ILEGIBLE = "LIBRO_ILEGIBLE"
LIBRO_CORRUPTO = "LIBRO_CORRUPTO"


class LibroNoEscrito(ErrorApi):
    """No se pudo escribir la línea: la operación se deshace y responde 503 genérico."""

    codigo = "servicio_no_disponible"


class ErrorLibro(Exception):  # noqa: N818 (nombre de dominio)
    def __init__(self, codigo: str, lineas: list[int] | None = None) -> None:
        self.codigo = codigo
        self.lineas = lineas or []
        detalle = f" lineas={','.join(map(str, self.lineas[:20]))}" if self.lineas else ""
        super().__init__(f"{codigo}{detalle}")


def ruta() -> Path:
    return Path(settings.LIBRO_ANONIMIZACIONES_PATH)


def fecha_libro(momento: datetime) -> str:
    return momento.astimezone(UTC).strftime(FORMATO_FECHA)


if sys.platform == "win32":  # pragma: no cover - desarrollo en Windows: sin flock

    @contextmanager
    def _flock(fd: int, exclusivo: bool) -> Iterator[None]:
        yield

else:  # POSIX (contenedores Linux)
    import fcntl

    @contextmanager
    def _flock(fd: int, exclusivo: bool) -> Iterator[None]:
        fcntl.flock(fd, fcntl.LOCK_EX if exclusivo else fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)


def _ultimo_byte(camino: Path) -> bytes:
    fd = os.open(camino, os.O_RDONLY | _NOFOLLOW | _CLOEXEC | _BINARIO)
    try:
        tamano = os.fstat(fd).st_size
        if tamano == 0:
            return b""
        os.lseek(fd, tamano - 1, os.SEEK_SET)
        return os.read(fd, 1)
    finally:
        os.close(fd)


def _fsync_directorio(directorio: Path) -> None:
    if os.name != "posix":  # pragma: no cover - Windows no abre directorios
        return
    fd = os.open(directorio, os.O_RDONLY | _CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def escribir(cuenta_id: int, evento: str, momento: datetime) -> None:
    """Añade una línea de forma durable, dentro de la transacción en curso (§4.2)."""
    if evento not in EVENTOS:
        raise ValueError(evento)
    # RULE-015 diferida: se comprueba ya, para no escribir una transición que no se confirmará.
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS app.trg_cuenta_admin_minimo IMMEDIATE")
    camino = ruta()
    linea = f"{cuenta_id};{evento};{fecha_libro(momento)}\n"
    try:
        nuevo = not camino.exists()
        if os.name != "posix" and camino.is_symlink():  # pragma: no cover - sin O_NOFOLLOW
            raise OSError("enlace simbólico")
        fd = os.open(
            camino,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT | _NOFOLLOW | _CLOEXEC | _BINARIO,
            MODO,
        )
        try:
            with _flock(fd, exclusivo=True):
                datos = linea
                if not nuevo and _ultimo_byte(camino) not in (b"", b"\n"):
                    datos = f"\n{PREFIJO_REPARACION}{fecha_libro(momento)}\n{linea}"
                os.write(fd, datos.encode("utf-8"))
                os.fsync(fd)
        finally:
            os.close(fd)
        if nuevo:
            _fsync_directorio(camino.parent)
    except OSError as exc:
        logger.error(
            "libro_anonimizaciones_no_escrito", cuenta_id=cuenta_id, tipo=type(exc).__name__
        )
        raise LibroNoEscrito() from None


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------
@dataclass
class EstadoLibro:
    """Resumen de una cuenta: último evento y desactivación vigente (fD)."""

    ultimo: str
    fecha_ultimo: datetime
    desactivacion_vigente: datetime | None


@dataclass
class Lectura:
    cuentas: dict[int, EstadoLibro] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)


def _abrir_para_leer(camino: Path) -> int:
    try:
        if camino.is_symlink():
            raise ErrorLibro(LIBRO_ILEGIBLE)
        fd = os.open(camino, os.O_RDONLY | _NOFOLLOW | _CLOEXEC | _BINARIO)
    except FileNotFoundError:
        raise ErrorLibro(LIBRO_AUSENTE) from None
    except OSError:
        raise ErrorLibro(LIBRO_ILEGIBLE) from None
    info = os.fstat(fd)
    escribible_por_otros = os.name == "posix" and bool(info.st_mode & stat.S_IWOTH)
    if not stat.S_ISREG(info.st_mode) or escribible_por_otros:
        os.close(fd)
        raise ErrorLibro(LIBRO_ILEGIBLE)
    return fd


def _leer_bytes(camino: Path) -> bytes:
    fd = _abrir_para_leer(camino)
    try:
        with _flock(fd, exclusivo=False):
            partes = []
            while bloque := os.read(fd, 65536):
                partes.append(bloque)
            return b"".join(partes)
    except OSError:
        raise ErrorLibro(LIBRO_ILEGIBLE) from None
    finally:
        with suppress(OSError):
            os.close(fd)


def _evento(linea: str) -> tuple[int, str, datetime] | None:
    coincidencia = _LINEA.match(linea)
    if coincidencia is None:
        return None
    try:
        fecha = datetime.strptime(coincidencia[3], FORMATO_FECHA).replace(tzinfo=UTC)
    except ValueError:
        return None
    return int(coincidencia[1]), coincidencia[2], fecha


def leer(ahora: datetime | None = None) -> Lectura:
    """Lee y valida el libro completo. Lanza ErrorLibro (AUSENTE, ILEGIBLE o CORRUPTO)."""
    try:
        texto = _leer_bytes(ruta()).decode("utf-8")
    except UnicodeDecodeError:
        raise ErrorLibro(LIBRO_CORRUPTO) from None
    lineas = texto.split("\n")
    cola_incompleta = lineas[-1] != ""
    lectura = Lectura()
    eventos: dict[int, list[tuple[str, datetime]]] = {}
    corruptas: list[int] = []
    for indice, linea in enumerate(lineas):
        numero = indice + 1
        if linea == "" or linea.startswith("#"):
            continue
        evento = _evento(linea)
        if evento is None:
            if indice == len(lineas) - 1 and cola_incompleta:
                lectura.avisos.append(f"COLA_INCOMPLETA:{numero}")
            elif indice + 1 < len(lineas) and lineas[indice + 1].startswith(PREFIJO_REPARACION):
                lectura.avisos.append(f"LINEA_REPARADA:{numero}")
            else:
                corruptas.append(numero)
            continue
        if indice == len(lineas) - 1 and cola_incompleta:
            # Línea bien formada pero sin '\n': escritura en curso o interrumpida (§4.3).
            lectura.avisos.append(f"COLA_INCOMPLETA:{numero}")
            continue
        cuenta_id, nombre, fecha = evento
        eventos.setdefault(cuenta_id, []).append((nombre, fecha))
    if corruptas:
        raise ErrorLibro(LIBRO_CORRUPTO, corruptas)
    limite_futuro = (ahora or datetime.now(UTC)) + MARGEN_FUTURO
    for cuenta_id, lista in eventos.items():
        fechas = [fecha for _nombre, fecha in lista]
        if any(b < a for a, b in pairwise(fechas)):
            lectura.avisos.append(f"FECHAS_NO_MONOTONAS:{cuenta_id}")
        if any(fecha > limite_futuro for fecha in fechas):
            lectura.avisos.append(f"FECHA_FUTURA:{cuenta_id}")
        vigente: datetime | None = None
        for nombre, fecha in lista:
            if nombre == REACTIVADA:
                vigente = None
            elif nombre == DESACTIVADA:
                vigente = fecha
        ultimo, fecha_ultimo = lista[-1]
        lectura.cuentas[cuenta_id] = EstadoLibro(ultimo, fecha_ultimo, vigente)
    for aviso in lectura.avisos:
        logger.warning("libro_anonimizaciones_aviso", aviso=aviso)
    return lectura
