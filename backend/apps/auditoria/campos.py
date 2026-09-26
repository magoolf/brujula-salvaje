"""Campo `cidr` de PostgreSQL (Django no trae CidrField; DB_HANDOFF evento_auditoria)."""

from __future__ import annotations

from typing import Any

from django.db import models


class CampoCidr(models.Field):  # type: ignore[type-arg]
    """Red IP como `cidr`: la BD rechaza bits de host, así que no puede guardar una IP completa.

    Se lee y se escribe como texto (p. ej. "203.0.113.0/24"); DEC-AUTO-092.
    """

    description = "Red IP (cidr de PostgreSQL)"

    def db_type(self, connection: Any) -> str:
        return "cidr"

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> str | None:
        return None if value is None else str(value)

    def to_python(self, value: Any) -> str | None:
        return None if value is None else str(value)

    def get_prep_value(self, value: Any) -> str | None:
        return None if value is None else str(value)
