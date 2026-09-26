"""Campos de modelo con tipo físico propio del DB_HANDOFF."""

from __future__ import annotations

from typing import Any

from django.db import models

PATRON_SHA256 = r"^[0-9a-f]{64}$"


class CampoSha256(models.CharField):  # type: ignore[type-arg]
    """Huella sha256 en hexadecimal: `char(64)` (DB_HANDOFF), con CHECK de patrón en el modelo."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["max_length"] = 64
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> Any:
        nombre, ruta, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        return nombre, ruta, args, kwargs

    def db_type(self, connection: Any) -> str:
        return "char(64)"
