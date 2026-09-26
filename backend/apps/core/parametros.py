"""Validación de parámetros de consulta (DEC-AUTO-105, AC-113, THREAT-008).

Un parámetro desconocido, repetido o fuera de dominio responde 400 `parametro_invalido` (nunca
500 ni se ignora en silencio). Cada vista declara los parámetros que admite.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from apps.core.exceptions import ParametroInvalido, normalizar_errores

MENSAJE_NO_ADMITIDO = "Parámetro no admitido."
MENSAJE_REPETIDO = "El parámetro solo puede aparecer una vez."


def validar_parametros(query_params: Mapping[str, Any], permitidos: Collection[str]) -> None:
    """Rechaza parámetros desconocidos o repetidos."""
    errores: dict[str, list[str]] = {}
    for nombre in query_params:
        if nombre not in permitidos:
            errores[nombre] = [MENSAJE_NO_ADMITIDO]
            continue
        getlist = getattr(query_params, "getlist", None)
        if getlist is not None and len(getlist(nombre)) > 1:
            errores[nombre] = [MENSAJE_REPETIDO]
    if errores:
        raise ParametroInvalido(errors=errores)


def errores_de_parametros(errors: Mapping[str, Any]) -> ParametroInvalido:
    """Convierte los errores de un serializer de filtros en 400 parametro_invalido."""
    return ParametroInvalido(errors=normalizar_errores(dict(errors)))
