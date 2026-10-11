"""Memoria de valores derivados que vive lo que dura el bloque atómico en curso (TKT-062).

Una operación que audita muchas entidades en un mismo bloque `transaction.atomic()` (p. ej. un
retiro en cascada de hasta 212 entidades) no debe repetir la misma consulta por cada evento
(OBS-QA058-01). El ámbito de la memoria es el bloque atómico más interno con savepoint (o la
transacción exterior si no hay savepoints), y se descarta sola:

- la transacción exterior se identifica con un marcador registrado por `transaction.on_commit`;
  Django vacía esa lista al confirmar o deshacer la transacción (y quita las entradas de un
  savepoint que se deshace), así que si el marcador ya no está, la memoria es de una transacción
  anterior y se tira entera;
- cada savepoint tiene un nombre único dentro de su transacción exterior (`savepoint_state`), así
  que un bloque anidado nuevo (otra operación de servicio) empieza con su memoria vacía;
- fuera de una transacción (autocommit) no hay memoria: cada llamada consulta.

Es un caché por proceso, conexión y bloque atómico: no es estado entre peticiones (Skill_Backend
§12.4). El llamante es responsable de `olvidar` una entrada cuando el dato cambia dentro del mismo
bloque. Infraestructura: no importa nada de `apps/` (Regla 10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.db import DEFAULT_DB_ALIAS, connections, transaction

_ATRIBUTO = "_brujula_memoria_transaccion"


class _Marcador:
    """Hook de `on_commit` sin efecto: solo marca a qué transacción pertenece la memoria."""

    def __call__(self) -> None:
        return None


@dataclass
class _Memoria:
    marcador: _Marcador
    # ámbito (nombre del savepoint más interno, "" = transacción exterior) -> espacio -> valores
    ambitos: dict[str, dict[str, dict[Any, Any]]] = field(default_factory=dict)


def _vigente(conexion: Any, marcador: _Marcador) -> bool:
    return any(entrada[1] is marcador for entrada in conexion.run_on_commit)


def _ambito(conexion: Any) -> str:
    for sid in reversed(conexion.savepoint_ids):
        if sid is not None:
            return str(sid)
    return ""


def _memoria(conexion: Any, using: str) -> _Memoria:
    memoria: _Memoria | None = getattr(conexion, _ATRIBUTO, None)
    if memoria is None or not _vigente(conexion, memoria.marcador):
        memoria = _Memoria(marcador=_Marcador())
        transaction.on_commit(memoria.marcador, using=using)
        setattr(conexion, _ATRIBUTO, memoria)
    return memoria


def memoria_de_transaccion(espacio: str, using: str = DEFAULT_DB_ALIAS) -> dict[Any, Any] | None:
    """Diccionario del `espacio` en el bloque atómico en curso; None fuera de una transacción."""
    conexion = connections[using]
    if not conexion.in_atomic_block:
        return None
    ambitos = _memoria(conexion, using).ambitos
    return ambitos.setdefault(_ambito(conexion), {}).setdefault(espacio, {})


def olvidar(espacio: str, clave: Any, using: str = DEFAULT_DB_ALIAS) -> None:
    """Descarta `clave` del `espacio` en TODOS los ámbitos de la transacción en curso (un dato que
    cambia deja de valer también en los bloques exteriores que lo memorizaron)."""
    memoria: _Memoria | None = getattr(connections[using], _ATRIBUTO, None)
    if memoria is not None:
        for espacios in memoria.ambitos.values():
            espacios.get(espacio, {}).pop(clave, None)
