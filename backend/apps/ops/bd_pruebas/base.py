"""Backend PostgreSQL para pruebas: permite el vaciado (flush) de las pruebas transaccionales.

Las pruebas `django_db(transaction=True)` vacían la BD al terminar con `TRUNCATE` de todas las
tablas. `evento_auditoria` rechaza TRUNCATE siempre (trigger trg_auditoria_inmutable_truncate,
ADR-DB-004 §1), así que el vaciado fallaría. Este backend envuelve el SQL de vaciado para que,
en la MISMA transacción, el propietario (app_migrator) desactive ese trigger, vacíe y lo vuelva
a activar. Solo lo usa config.settings.test: en producción el motor es el estándar de Django y
el rol de la aplicación (app_rw) no tiene privilegio TRUNCATE ni puede alterar tablas.
"""

from __future__ import annotations

from typing import Any

from django.db.backends.postgresql import base
from django.db.backends.postgresql.operations import DatabaseOperations as OperacionesPostgres

TABLA_AUDITORIA = "evento_auditoria"
TRIGGER_TRUNCATE = "trg_auditoria_inmutable_truncate"


class DatabaseOperations(OperacionesPostgres):
    def sql_flush(
        self,
        style: Any,
        tables: Any,
        *,
        reset_sequences: bool = False,
        allow_cascade: bool = False,
    ) -> list[str]:
        sentencias: list[str] = super().sql_flush(
            style, tables, reset_sequences=reset_sequences, allow_cascade=allow_cascade
        )
        if not sentencias or TABLA_AUDITORIA not in tables:
            return sentencias
        tabla = self.quote_name(TABLA_AUDITORIA)
        return [
            f"ALTER TABLE {tabla} DISABLE TRIGGER {TRIGGER_TRUNCATE}",
            *sentencias,
            f"ALTER TABLE {tabla} ENABLE TRIGGER {TRIGGER_TRUNCATE}",
        ]


class DatabaseWrapper(base.DatabaseWrapper):
    ops_class = DatabaseOperations
