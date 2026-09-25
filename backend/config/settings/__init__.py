"""Selección de settings por entorno.

Los contenedores y el CI usan DJANGO_SETTINGS_MODULE=config.settings (DEVOPS_HANDOFF §6.1):
en ese caso se carga el módulo indicado por DJANGO_ENV (prod por defecto; dev o test).
Si DJANGO_SETTINGS_MODULE apunta directamente a un submódulo (p. ej. config.settings.test),
este paquete no carga nada por su cuenta.
"""

from __future__ import annotations

import importlib
import os

from django.core.exceptions import ImproperlyConfigured

_ENTORNOS = frozenset({"prod", "dev", "test"})

if os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings") == "config.settings":
    _entorno = os.environ.get("DJANGO_ENV", "prod").strip().lower() or "prod"
    if _entorno not in _ENTORNOS:
        raise ImproperlyConfigured(f"DJANGO_ENV debe ser uno de {sorted(_ENTORNOS)}")
    _modulo = importlib.import_module(f"config.settings.{_entorno}")
    globals().update({k: v for k, v in vars(_modulo).items() if k.isupper()})
