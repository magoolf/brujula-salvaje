"""Identificador de traza W3C (traceparent) por petición.

- Un `traceparent` entrante válido (versión 00) se propaga: su trace-id es el de la petición.
- Uno ausente o inválido se sustituye por un trace-id aleatorio de 128 bits.
- Si OpenTelemetry está activo, manda el trace-id del span actual (que ya extrajo el traceparent).
El valor se expone en la cabecera X-Trace-Id, en el `trace_id` de los errores y en los logs.
"""

from __future__ import annotations

import re
import secrets
from contextvars import ContextVar, Token

_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}$")
_TRACE_ID_NULO = "0" * 32
_PARENT_ID_NULO = "0" * 16

_trace_id_actual: ContextVar[str | None] = ContextVar("trace_id_actual", default=None)


def extraer_trace_id(traceparent: str | None) -> str | None:
    """Trace-id de un traceparent W3C válido, o None si falta o es inválido."""
    if not traceparent:
        return None
    coincidencia = _TRACEPARENT.fullmatch(traceparent.strip())
    if coincidencia is None:
        return None
    trace_id, parent_id = coincidencia.groups()
    if trace_id == _TRACE_ID_NULO or parent_id == _PARENT_ID_NULO:
        return None
    return trace_id


def nuevo_trace_id() -> str:
    while True:
        valor = secrets.token_hex(16)
        if valor != _TRACE_ID_NULO:
            return valor


def trace_id_otel() -> str | None:
    """Trace-id del span activo de OpenTelemetry, si hay uno válido."""
    from opentelemetry import trace

    contexto = trace.get_current_span().get_span_context()
    if not contexto.is_valid:
        return None
    return format(contexto.trace_id, "032x")


def fijar_trace_id(trace_id: str) -> Token[str | None]:
    return _trace_id_actual.set(trace_id)


def restaurar_trace_id(token: Token[str | None]) -> None:
    _trace_id_actual.reset(token)


def trace_id_actual() -> str:
    """Trace-id de la petición en curso (o uno nuevo fuera de una petición)."""
    return _trace_id_actual.get() or nuevo_trace_id()
