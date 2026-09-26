"""Caché de estados de seguridad sin desalojo por volumen (HALLAZGO-QA004-01).

La caché "default" (tabla UNLOGGED cache_limites, ADR-DB-005 §3) guarda estados de seguridad:
contadores de limitación de tasa, fallos y bloqueos de login de usuarios sin cuenta operativa y
la anti-repetición TOTP. El DatabaseCache de Django, al superar MAX_ENTRIES, borra un tercio de
las claves VIGENTES ordenadas por cache_key: un atacante podría generar volumen para desalojar
bloqueos y contadores (oráculo de enumeración y fin de la limitación por origen).

Esta variante nunca borra entradas vigentes: al superar MAX_ENTRIES solo elimina las caducadas.
El tamaño queda acotado por los TTL (límite de tasa ≤ 1 min, TOTP 120 s, login ≤ 2 h) y por el
número real de orígenes activos; la limitación por IP (/24) acota el ritmo de altas nuevas.
"""

from __future__ import annotations

from typing import Any

from django.core.cache.backends.db import DatabaseCache
from django.db import connections


class CacheSinDesalojo(DatabaseCache):
    def _cull(self, db: str, cursor: Any, now: Any, num: int) -> None:
        conexion = connections[db]
        tabla = conexion.ops.quote_name(self._table)  # type: ignore[attr-defined]
        cursor.execute(
            f"DELETE FROM {tabla} WHERE {conexion.ops.quote_name('expires')} < %s",  # noqa: S608
            [conexion.ops.adapt_datetimefield_value(now)],
        )
