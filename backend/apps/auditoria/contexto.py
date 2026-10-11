"""Contexto de proceso para la etiqueta del actor de auditoría (TKT-067, AC-030, ADR-DB-004 §1.5).

Un proceso sin cuenta humana (carga semilla, tareas) audita a través de servicios del panel que
no aceptan `actor_etiqueta` y reciben `actor_id=None`; sin más información `registrar_evento` les
pondría 'desconocido'. `auditar_como_sistema()` declara, solo mientras dura el bloque, que esos
eventos sin actor ni etiqueta los origina el sistema (DEC-AUTO-1034):

    with auditar_como_sistema():
        call_command("cargar_semilla")

Aislamiento:
- Se guarda en un `ContextVar`: cada hilo arranca con su propio contexto vacío, así que el bloque
  nunca alcanza a otros hilos (p. ej. los workers que atienden peticiones HTTP).
- Además, cada petición HTTP neutraliza el contexto mientras se atiende (señales
  `request_started`/`request_finished`, conectadas en `AuditoriaConfig.ready`): aunque una
  petición se procese en el MISMO hilo que un bloque activo (cliente de pruebas), sus eventos sin
  actor siguen recibiendo 'desconocido'.
- `reset(token)` en `finally` restaura el valor anterior también si el bloque lanza una excepción.

Nunca sustituye a un actor real ni a una etiqueta explícita: `registrar_evento` solo lo consulta
cuando no recibe ninguno de los dos.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

from apps.core.actores import ETIQUETA_SISTEMA

_ETIQUETA_PROCESO: ContextVar[str | None] = ContextVar(
    "auditoria_etiqueta_proceso", default=None
)
# Token de la neutralización abierta por la petición en curso (None fuera de una petición).
_TOKEN_PETICION: ContextVar[Token[str | None] | None] = ContextVar(
    "auditoria_token_peticion", default=None
)


@contextmanager
def auditar_como_sistema() -> Iterator[None]:
    """Los eventos sin actor ni etiqueta registrados dentro del bloque llevan 'sistema'."""
    token = _ETIQUETA_PROCESO.set(ETIQUETA_SISTEMA)
    try:
        yield
    finally:
        _ETIQUETA_PROCESO.reset(token)


def etiqueta_de_proceso() -> str | None:
    """Etiqueta del proceso en curso, o None fuera de un bloque `auditar_como_sistema()`."""
    return _ETIQUETA_PROCESO.get()


def al_iniciar_peticion(**_kwargs: Any) -> None:
    """`request_started`: la petición se atiende sin etiqueta de proceso."""
    _TOKEN_PETICION.set(_ETIQUETA_PROCESO.set(None))


def al_terminar_peticion(**_kwargs: Any) -> None:
    """`request_finished`: devuelve al hilo la etiqueta que tenía antes de la petición."""
    token = _TOKEN_PETICION.get()
    if token is None:
        return
    _TOKEN_PETICION.set(None)
    try:
        _ETIQUETA_PROCESO.reset(token)
    except (ValueError, RuntimeError):
        # Token de otro contexto (servidor que emite las señales en contextos distintos, p. ej.
        # ASGI) o ya usado: ese contexto se descarta con la petición; no hay nada que restaurar.
        pass
