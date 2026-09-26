"""Lectura tipada de variables de entorno (DEVOPS_HANDOFF §7, .env.example).

Sin dependencias externas. Una variable obligatoria ausente o vacía falla al arrancar
(fail-closed) con ImproperlyConfigured, nunca con un valor inventado.
"""

from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

_VERDADEROS = frozenset({"1", "true", "yes", "on"})
_FALSOS = frozenset({"0", "false", "no", "off"})


def texto(nombre: str, defecto: str | None = None) -> str:
    """Devuelve la variable como texto; sin defecto, es obligatoria."""
    valor = os.environ.get(nombre, "").strip()
    if valor:
        return valor
    if defecto is None:
        raise ImproperlyConfigured(f"Falta la variable de entorno obligatoria {nombre}")
    return defecto


def booleano(nombre: str, defecto: bool) -> bool:
    valor = os.environ.get(nombre, "").strip().lower()
    if not valor:
        return defecto
    if valor in _VERDADEROS:
        return True
    if valor in _FALSOS:
        return False
    raise ImproperlyConfigured(f"{nombre} debe ser booleano (true/false)")


def entero(nombre: str, defecto: int) -> int:
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        return defecto
    try:
        return int(valor)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{nombre} debe ser un entero") from exc


def lista(nombre: str, defecto: str = "") -> list[str]:
    """Lista separada por comas, sin elementos vacíos."""
    valor = os.environ.get(nombre, "").strip() or defecto
    return [parte.strip() for parte in valor.split(",") if parte.strip()]
