"""Consultas de lectura de infraestructura (Skill_Backend §4.3)."""

from __future__ import annotations

from django.db import DEFAULT_DB_ALIAS, connections, transaction

TIMEOUT_READINESS_MS = 1000


def base_datos_disponible(alias: str = DEFAULT_DB_ALIAS) -> bool:
    """`SELECT 1` con statement_timeout de 1 s (ADR-DB-005 §4). Lanza DatabaseError si falla."""
    with transaction.atomic(using=alias), connections[alias].cursor() as cursor:
        cursor.execute(
            "SELECT set_config('statement_timeout', %s, true)", [f"{TIMEOUT_READINESS_MS}ms"]
        )
        cursor.execute("SELECT 1")
        fila = cursor.fetchone()
    return fila is not None and fila[0] == 1
