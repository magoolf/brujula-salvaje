"""Validación de parámetros de consulta (DEC-AUTO-105, AC-113, THREAT-008).

Un parámetro desconocido, repetido, vacío o fuera de dominio responde 400 `parametro_invalido`
(nunca 500 ni se ignora en silencio). Cada vista declara los parámetros que admite.

- Vacío (QA004-C2-01): `?filtro=` o solo espacios se rechaza siempre. DRF trata la cadena vacía
  de un campo opcional como "ausente" y devolvería el listado sin filtrar; el contrato no declara
  ningún parámetro con `allowEmptyValue` y ningún esquema de consulta admite "" (enums, patrones,
  fechas, enteros, `minLength` >= 1). Si un contrato futuro lo declara, la vista lo indica en
  `admite_vacio`.
- NUL (DEC-AUTO-217, CHG-API-002): un valor con U+0000 se rechaza siempre, antes de parsearlo.
- Repetido: solo los parámetros de tipo array (`style: form, explode: true`) pueden aparecer
  varias veces; la vista los indica en `multiples`.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from apps.core.exceptions import ParametroInvalido, normalizar_errores

MENSAJE_NO_ADMITIDO = "Parámetro no admitido."
MENSAJE_REPETIDO = "El parámetro solo puede aparecer una vez."
MENSAJE_VACIO = "El parámetro no puede estar vacío."
MENSAJE_NUL = "El parámetro contiene caracteres no admitidos."


def _valores(query_params: Mapping[str, Any], nombre: str) -> list[Any]:
    getlist = getattr(query_params, "getlist", None)
    if getlist is not None:
        return list(getlist(nombre))
    return [query_params[nombre]]


def validar_parametros(
    query_params: Mapping[str, Any],
    permitidos: Collection[str],
    *,
    multiples: Collection[str] = (),
    admite_vacio: Collection[str] = (),
) -> None:
    """Rechaza parámetros desconocidos, repetidos (salvo `multiples`) o vacíos."""
    errores: dict[str, list[str]] = {}
    for nombre in query_params:
        if nombre not in permitidos:
            errores[nombre] = [MENSAJE_NO_ADMITIDO]
            continue
        valores = _valores(query_params, nombre)
        if any("\x00" in str(v) for v in valores):
            # DEC-AUTO-217 (CHG-API-002, QA004-C3-01): NUL nunca se admite, antes de cualquier
            # parseo (parse_datetime aceptaría lo que precede al NUL).
            errores[nombre] = [MENSAJE_NUL]
        elif len(valores) > 1 and nombre not in multiples:
            errores[nombre] = [MENSAJE_REPETIDO]
        elif nombre not in admite_vacio and any(not str(v).strip() for v in valores):
            errores[nombre] = [MENSAJE_VACIO]
    if errores:
        raise ParametroInvalido(errors=errores)


def errores_de_parametros(errors: Mapping[str, Any]) -> ParametroInvalido:
    """Convierte los errores de un serializer de filtros en 400 parametro_invalido."""
    return ParametroInvalido(errors=normalizar_errores(dict(errors)))
