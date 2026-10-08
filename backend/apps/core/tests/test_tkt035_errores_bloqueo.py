"""TKT-035: traducción GLOBAL (manejador de DRF de core) de los errores de BD de concurrencia.

- AC_TKT035_01: `OperationalError` con SQLSTATE 55P03 (lock_not_available), 40P01
  (deadlock_detected) o 40001 (serialization_failure) → 409 `conflicto_version` RFC 9457 con
  `trace_id`, sin Retry-After (el contrato solo lo documenta para idempotencia_en_curso).
- AC_TKT035_02: `IntegrityError` 23503 (FK violada en el COMMIT por un borrado concurrente del
  referenciado) → 409 `conflicto_version`.
- AC_TKT035_03: `ProtectedError`/`RestrictedError` que ningún servicio tradujo → 409
  `dependencia_bloqueante` con `usos` (ReferenciaUso, máx. 100) y `total_usos`, sin `__str__`.
- AC_TKT035_04: cualquier otro error de BD sigue siendo 500 `error_interno` controlado y se
  registra como `excepcion_no_controlada` (no se ocultan errores que no son de concurrencia).

Las pruebas con transacciones reales (55P03 y 40P01 de PostgreSQL, carrera borrado/alta) están en
apps/catalogos/tests/test_tkt035_concurrencia.py.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import psycopg.errors
import pytest
from django.db import DatabaseError, IntegrityError, OperationalError
from django.db.models import ProtectedError, RestrictedError

from apps.catalogos.models import Region
from apps.core.exceptions import MAX_USOS, manejador_excepciones, sqlstate_de
from apps.core.problemas import MEDIA_TYPE_PROBLEMA

TRACE_ID = re.compile(r"^[0-9a-f]{32}$")


def _error_bd(clase: type[DatabaseError], sqlstate: str | None) -> DatabaseError:
    """Error de Django como lo levanta su envoltorio de psycopg (`raise ... from origen`)."""
    origen = psycopg.errors.lookup(sqlstate)("mensaje con valores 'secretos'") if sqlstate else None
    try:
        raise clase("mensaje con valores 'secretos'") from origen
    except DatabaseError as exc:
        return exc


def _eventos(logs: Callable[[], list[dict[str, Any]]], nombre: str) -> list[dict[str, Any]]:
    return [linea for linea in logs() if linea.get("event") == nombre]


def _problema(respuesta: Any, estado: int, codigo: str) -> dict[str, Any]:
    assert respuesta.status_code == estado
    assert respuesta.content_type == MEDIA_TYPE_PROBLEMA  # Response de DRF sin renderizar
    cuerpo: dict[str, Any] = respuesta.data
    assert cuerpo["code"] == codigo
    assert cuerpo["status"] == estado
    assert cuerpo["type"].endswith(f"/errors/{codigo}")
    assert TRACE_ID.match(cuerpo["trace_id"])
    assert "secretos" not in str(cuerpo)
    return cuerpo


@pytest.mark.parametrize(
    ("clase", "sqlstate"),
    [
        (OperationalError, "55P03"),
        (OperationalError, "40P01"),
        (OperationalError, "40001"),
        (DatabaseError, "55P03"),  # p. ej. NOWAIT envuelto como DatabaseError genérico
    ],
)
def test_AC_TKT035_01_bloqueo_interbloqueo_y_serializacion_son_409_conflicto_version(
    clase: type[DatabaseError], sqlstate: str, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    respuesta = manejador_excepciones(_error_bd(clase, sqlstate), {})
    cuerpo = _problema(respuesta, 409, "conflicto_version")
    assert cuerpo["errors"] == {}
    assert "Recarga y vuelve a intentarlo" in cuerpo["detail"]
    assert "Retry-After" not in respuesta
    eventos = _eventos(logs_json, "conflicto_concurrencia_bd")
    assert [e["sqlstate"] for e in eventos] == [sqlstate]
    assert _eventos(logs_json, "excepcion_no_controlada") == []


def test_AC_TKT035_02_fk_violada_en_el_commit_es_409_conflicto_version(
    logs_json: Callable[[], list[dict[str, Any]]],
) -> None:
    respuesta = manejador_excepciones(_error_bd(IntegrityError, "23503"), {})
    _problema(respuesta, 409, "conflicto_version")
    assert [e["sqlstate"] for e in _eventos(logs_json, "conflicto_concurrencia_bd")] == ["23503"]
    assert _eventos(logs_json, "excepcion_no_controlada") == []


def _objeto(db_table: str, pk: int, **campos: Any) -> Any:
    return SimpleNamespace(_meta=SimpleNamespace(db_table=db_table), pk=pk, **campos)


def test_AC_TKT035_03_protected_error_es_409_dependencia_bloqueante_con_usos() -> None:
    objetos = [
        _objeto("destino", 9, titulo="Torres del Paine", estado_editorial="PUBLICADO"),
        _objeto("itinerario", 3, titulo="x" * 300, estado_editorial=None),
        Region(pk=4, nombre="Patagonia"),
    ]
    respuesta = manejador_excepciones(ProtectedError("protegido", objetos), {})
    cuerpo = _problema(respuesta, 409, "dependencia_bloqueante")
    assert cuerpo["total_usos"] == 3
    assert cuerpo["usos"] == [
        {
            "tipo_entidad": "DESTINO",
            "id": 9,
            "titulo": "Torres del Paine",
            "estado_editorial": "PUBLICADO",
        },
        # Sin `titulo` en el modelo no se usa `__str__` (podría llevar datos personales).
        {"tipo_entidad": "ITINERARIO", "id": 3, "titulo": "x" * 150, "estado_editorial": None},
        {"tipo_entidad": "REGION", "id": 4, "titulo": "REGION #4", "estado_editorial": None},
    ]


def test_AC_TKT035_03_restricted_error_limita_usos_al_maximo_del_contrato() -> None:
    objetos = [_objeto("medio", pk) for pk in range(150, 0, -1)]
    respuesta = manejador_excepciones(RestrictedError("restringido", objetos), {})
    cuerpo = _problema(respuesta, 409, "dependencia_bloqueante")
    assert cuerpo["total_usos"] == 150
    assert len(cuerpo["usos"]) == MAX_USOS
    assert [u["id"] for u in cuerpo["usos"]] == list(range(1, MAX_USOS + 1))
    assert cuerpo["usos"][0] == {
        "tipo_entidad": "MEDIO",
        "id": 1,
        "titulo": "MEDIO #1",
        "estado_editorial": None,
    }


@pytest.mark.parametrize(
    ("clase", "sqlstate"),
    [
        (OperationalError, "57014"),  # query_canceled (statement_timeout): no es de concurrencia
        (OperationalError, "08006"),  # connection_failure
        (OperationalError, None),  # sin causa de psycopg
        (IntegrityError, "23505"),  # unique_violation no traducida por un servicio: es un fallo
        (IntegrityError, "23514"),  # check_violation
        (DatabaseError, None),
    ],
)
def test_AC_TKT035_04_otros_errores_de_bd_siguen_siendo_500_controlado(
    clase: type[DatabaseError],
    sqlstate: str | None,
    logs_json: Callable[[], list[dict[str, Any]]],
) -> None:
    respuesta = manejador_excepciones(_error_bd(clase, sqlstate), {"view": object()})
    cuerpo = _problema(respuesta, 500, "error_interno")
    assert cuerpo["errors"] == {}
    assert len(_eventos(logs_json, "excepcion_no_controlada")) == 1
    assert _eventos(logs_json, "conflicto_concurrencia_bd") == []


def test_AC_TKT035_04_sqlstate_solo_de_la_causa_de_psycopg() -> None:
    assert sqlstate_de(_error_bd(OperationalError, "40P01")) == "40P01"
    assert sqlstate_de(_error_bd(OperationalError, None)) is None

    class _CausaRaraError(Exception):
        sqlstate = 55

    falso = OperationalError("x")
    falso.__cause__ = _CausaRaraError()
    assert sqlstate_de(falso) is None
    assert sqlstate_de(ValueError("x")) is None
