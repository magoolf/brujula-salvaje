"""Servicio común de idempotencia del panel (ADR-API-002 §5, DEC-AUTO-107/123..129).

Implementa el protocolo de DB_HANDOFF `idempotencia_peticion.notas` para las 11 operaciones que
admiten `Idempotency-Key`, TODO dentro de la MISMA transacción que el efecto de negocio:

1. Se borra la fila vencida de (cuenta, clave), si la hay: la clave se reutiliza como nueva.
2. INSERT ... ON CONFLICT (cuenta_id, clave) DO NOTHING RETURNING id. Un duplicado concurrente sin
   confirmar hace esperar a esta sentencia; si la espera supera lock_timeout (3 s) → 409
   `idempotencia_en_curso` con Retry-After (reintentable con la misma clave).
3. Si ya existía: otra operación u otra huella → 422 `idempotencia_conflicto`; misma operación y
   huella → se devuelve la respuesta original sin repetir el efecto. Si la respuesta no se guardó
   (secretos, p. ej. la contraseña temporal de panelCrearCuenta) → 409
   `idempotencia_respuesta_no_reproducible` con Location del recurso (DEC-AUTO-125/129).
4. Si se insertó: se ejecuta el efecto y, antes del commit, se guarda la respuesta 2xx. Cualquier
   error hace ROLLBACK del efecto y de la fila: solo se guardan respuestas 2xx confirmadas (el
   constraint trigger diferido trg_idempotencia_completa lo garantiza en la BD).

Es infraestructura (Skill_Backend Regla 10): trabaja con SQL sobre la tabla y no importa la app
`ops`, dueña del modelo. Los servicios de dominio lo usan a través de `ejecutar`.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import OperationalError, connection, transaction

from apps.core.exceptions import ErrorApi, ParametroInvalido

CABECERA = "Idempotency-Key"
META_CABECERA = "HTTP_IDEMPOTENCY_KEY"

# Las 11 operationId del contrato que admiten Idempotency-Key (CHECK ck_idempotencia_operacion).
OPERACIONES = frozenset(
    {
        "panelCrearDestino",
        "panelCrearItinerario",
        "panelCrearGuia",
        "panelCrearTipoAventura",
        "panelCrearColeccion",
        "panelCrearTerminoGlosario",
        "panelPublicarContenido",
        "panelRetirarContenido",
        "panelReactivarContenido",
        "panelSubirMedios",
        "panelCrearCuenta",
    }
)

TAMANO_MAXIMO_RESPUESTA = 65_536  # 64 KB (DEC-AUTO-128, CHECK ck_idempotencia_tamano_respuesta)
SQLSTATE_LOCK_NO_DISPONIBLE = "55P03"
_UUID_CANONICO = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")


@dataclass(frozen=True)
class Resultado:
    """Respuesta 2xx de una operación (la que se guarda y se reproduce)."""

    codigo_http: int
    cuerpo: Any
    recurso_id: int | None = None
    repetida: bool = False
    cabeceras: Mapping[str, str] = field(default_factory=dict)


class IdempotenciaEnCurso(ErrorApi):
    codigo = "idempotencia_en_curso"


class IdempotenciaConflicto(ErrorApi):
    codigo = "idempotencia_conflicto"


class RespuestaNoReproducible(ErrorApi):
    codigo = "idempotencia_respuesta_no_reproducible"


def leer_clave(valor: str | None) -> uuid.UUID | None:
    """Valor de la cabecera Idempotency-Key: UUID canónico u omitida."""
    if valor is None:
        return None
    texto = valor.strip()
    if not _UUID_CANONICO.fullmatch(texto):
        raise ParametroInvalido(errors={CABECERA: ["Debe ser un UUID."]})
    return uuid.UUID(texto)


def huella_peticion(operacion: str, parametros_ruta: Mapping[str, Any], cuerpo: Any) -> str:
    """sha256 de la operación, los parámetros de ruta y el cuerpo canónico (claves ordenadas)."""
    canonico = json.dumps(
        {"operacion": operacion, "ruta": dict(parametros_ruta), "cuerpo": cuerpo},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        cls=DjangoJSONEncoder,
    )
    return hashlib.sha256(canonico.encode()).hexdigest()


def _segundos_espera() -> int:
    return max(1, math.ceil(int(settings.IDEMPOTENCIA_LOCK_TIMEOUT_MS) / 1000))


def _cuerpo_guardable(cuerpo: Any) -> str | None:
    """JSON del cuerpo si cabe en 64 KB; None si no puede guardarse."""
    texto = json.dumps(cuerpo, cls=DjangoJSONEncoder, ensure_ascii=False)
    return texto if len(texto.encode()) <= TAMANO_MAXIMO_RESPUESTA else None


def _decodificar(valor: Any) -> Any:
    # Django registra jsonb como texto en psycopg 3 (lo decodifica JSONField, no el cursor).
    return json.loads(valor) if isinstance(valor, str | bytes) else valor


def _reservar(cursor: Any, cuenta_id: int, clave: uuid.UUID, operacion: str, huella: str) -> bool:
    """Pasos 1 y 2 del protocolo. True si la clave queda reservada para esta transacción."""
    cursor.execute(
        "SELECT set_config('lock_timeout', %s, true)",
        [f"{int(settings.IDEMPOTENCIA_LOCK_TIMEOUT_MS)}ms"],
    )
    try:
        cursor.execute(
            "DELETE FROM idempotencia_peticion "
            "WHERE cuenta_id = %s AND clave = %s AND expira_en <= now()",
            [cuenta_id, clave],
        )
        cursor.execute(
            "INSERT INTO idempotencia_peticion (cuenta_id, clave, operacion, huella_peticion) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (cuenta_id, clave) DO NOTHING RETURNING id",
            [cuenta_id, clave, operacion, huella],
        )
    except OperationalError as exc:
        if getattr(exc.__cause__, "sqlstate", None) == SQLSTATE_LOCK_NO_DISPONIBLE:
            espera = _segundos_espera()
            raise IdempotenciaEnCurso(
                "Otra petición con la misma clave de idempotencia aún se está procesando. "
                "Reintenta en unos segundos.",
                cabeceras={"Retry-After": str(espera)},
            ) from exc
        raise
    return cursor.fetchone() is not None


def _reproducir(
    cursor: Any,
    cuenta_id: int,
    clave: uuid.UUID,
    operacion: str,
    huella: str,
    ubicacion: Callable[[int], str] | None,
) -> Resultado:
    """Paso 3 del protocolo: la clave ya estaba completada."""
    cursor.execute(
        "SELECT operacion, huella_peticion, codigo_http, recurso_id, cuerpo_respuesta, "
        "cuerpo_omitido FROM idempotencia_peticion WHERE cuenta_id = %s AND clave = %s",
        [cuenta_id, clave],
    )
    fila = cursor.fetchone()
    if fila is None:  # pragma: no cover - la fila existía al hacer el INSERT
        raise IdempotenciaEnCurso(cabeceras={"Retry-After": str(_segundos_espera())})
    operacion_guardada, huella_guardada, codigo_http, recurso_id, cuerpo, omitido = fila
    if operacion_guardada != operacion or huella_guardada != huella:
        raise IdempotenciaConflicto(
            errors={CABECERA: ["La clave ya se usó con otra operación u otros datos."]}
        )
    if omitido:
        cabeceras = {}
        if ubicacion is not None and recurso_id is not None:
            cabeceras["Location"] = ubicacion(int(recurso_id))
        raise RespuestaNoReproducible(cabeceras=cabeceras)
    return Resultado(
        codigo_http=int(codigo_http),
        cuerpo=_decodificar(cuerpo),
        recurso_id=recurso_id,
        repetida=True,
    )


def ejecutar(
    *,
    cuenta_id: int,
    clave: uuid.UUID | None,
    operacion: str,
    huella: str,
    efecto: Callable[[], Resultado],
    reproducible: bool = True,
    ubicacion: Callable[[int], str] | None = None,
) -> Resultado:
    """Ejecuta `efecto` una sola vez por (cuenta, clave) en una única transacción.

    `reproducible=False` (panelCrearCuenta) no guarda el cuerpo: la repetición responde 409
    `idempotencia_respuesta_no_reproducible` con `Location` = ubicacion(recurso_id).
    Sin clave, el efecto se ejecuta igualmente dentro de una transacción.
    """
    if operacion not in OPERACIONES:
        raise ValueError(f"Operación sin idempotencia en el contrato: {operacion}")
    with transaction.atomic():
        if clave is None:
            return efecto()
        with connection.cursor() as cursor:
            if not _reservar(cursor, cuenta_id, clave, operacion, huella):
                return _reproducir(cursor, cuenta_id, clave, operacion, huella, ubicacion)
        resultado = efecto()
        if not 200 <= resultado.codigo_http <= 299:
            raise ValueError("Solo se guardan respuestas 2xx")
        cuerpo = _cuerpo_guardable(resultado.cuerpo) if reproducible else None
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE idempotencia_peticion SET codigo_http = %s, recurso_id = %s, "
                "cuerpo_respuesta = %s::jsonb, cuerpo_omitido = %s "
                "WHERE cuenta_id = %s AND clave = %s",
                [
                    resultado.codigo_http,
                    resultado.recurso_id,
                    cuerpo,
                    cuerpo is None,
                    cuenta_id,
                    clave,
                ],
            )
        return resultado


def borrar_claves_de_cuenta(cuenta_id: int) -> int:
    """Borra las claves de una cuenta (anonimización, DEC-AUTO-127). Devuelve cuántas."""
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM idempotencia_peticion WHERE cuenta_id = %s", [cuenta_id])
        return int(cursor.rowcount)
