"""Almacén de sesiones de Django sobre la tabla `sesion_panel` (ADR-DB-005 §2, DEC-AUTO-089).

SESSION_ENGINE = "apps.cuentas.sesiones" (TKT-004). Además del contenido cifrado y firmado de la
sesión, cada fila guarda en columnas propias:
- `cuenta_id`: permite invalidar todas las sesiones de una cuenta (THREAT-002/025, AC-107);
- `autenticado_en`: inicio de la autenticación, para la expiración absoluta de 12 h.
Ambos valores se toman de las claves CLAVE_CUENTA y CLAVE_AUTENTICADO_EN de la sesión.

TKT-040: la sesión se guarda DENTRO de DRF (autenticación y vistas, apps.cuentas.autenticacion),
para que un fallo del guardado tenga la respuesta del contrato y no el 400 `validacion` de
`SessionInterrupted`. Por eso `save()` no repite un UPDATE si los datos ya se guardaron tal cual en
esta petición (el guardado final de SessionMiddleware queda sin consultas y solo fija la cookie), y
`fallo_por_contencion` distingue un fallo por bloqueo (55P03/40P01/40001) de una fila ya borrada.

TKT-044 (THREAT-002): invalidar una sesión no puede depender de poder borrar su fila. Si otra
transacción la tiene bloqueada, `invalidar_clave` no espera: inserta una marca de revocación (una
fila de esta misma tabla con clave `~<sha256>`, sin cuenta y con la caducidad máxima de una sesión)
y `SessionStore` nunca carga una clave que tenga marca (misma consulta, NOT EXISTS por la PK). Las
marcas caducan y las retira la purga horaria de caducadas (`clear_expired`). Sin cambio de esquema.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from django.conf import settings
from django.contrib.sessions.backends.base import CreateError, UpdateError
from django.contrib.sessions.backends.db import SessionStore as SessionStoreBD
from django.core.exceptions import SuspiciousOperation
from django.db import DatabaseError, IntegrityError, connections, router, transaction
from django.db.models import Exists
from django.utils import timezone

from apps.core.exceptions import SQLSTATE_CONCURRENCIA, sqlstate_de

if TYPE_CHECKING:
    from django.contrib.sessions.backends.base import SessionBase

    from apps.cuentas.models import SesionPanel

CLAVE_CUENTA = "panel_cuenta_id"
CLAVE_AUTENTICADO_EN = "panel_autenticado_en"

# En una actualización no se reescribe creado_en (tiene db_default y conserva su valor).
_CAMPOS_ACTUALIZABLES = ["session_data", "expire_date", "cuenta", "autenticado_en"]
# Prefijo de las marcas de revocación: no está en VALID_KEY_CHARS de Django ([a-z0-9]), así que
# ninguna clave de sesión real empieza por él y una marca nunca se carga como sesión (TKT-044).
_PREFIJO_REVOCACION = "~"
# Intentos de alta de una clave nueva que choca con una existente (23505) antes de rendirse.
_INTENTOS_CLAVE_NUEVA = 10
_SQLSTATE_CLAVE_REPETIDA = "23505"  # unique_violation


def _fecha(valor: Any) -> datetime | None:
    if not valor:
        return None
    return datetime.fromisoformat(str(valor))


def fallo_por_contencion(exc: BaseException) -> bool:
    """True si el fallo (o su causa encadenada) es un error de BD por otra transacción en curso:
    espera de bloqueo agotada, interbloqueo o fallo de serialización. False si la fila de la sesión
    ya no existía (UPDATE de 0 filas: logout, desactivación, cambio de contraseña en otra sesión)
    o si es otro error."""
    actual: BaseException | None = exc
    while actual is not None:
        if isinstance(actual, DatabaseError) and sqlstate_de(actual) in SQLSTATE_CONCURRENCIA:
            return True
        actual = actual.__cause__
    return False


def descartar_en_memoria(sesion: SessionBase) -> None:
    """Vacía la sesión sin tocar la BD: SessionMiddleware no la guarda y borra la cookie."""
    sesion.clear()
    sesion._session_key = None


def marcar_guardada(sesion: SessionBase) -> None:
    """Da por guardados los datos actuales: el guardado final de SessionMiddleware no repite un
    UPDATE que acaba de fallar por contención (la cookie se sigue fijando)."""
    if isinstance(sesion, SessionStore) and sesion.session_key is not None:
        sesion._guardado = (sesion.session_key, dict(sesion._get_session()))  # type: ignore[attr-defined]


def clave_revocacion(clave: str) -> str:
    """Clave (40 caracteres, la longitud de la columna) de la marca de revocación de `clave`."""
    return _PREFIJO_REVOCACION + hashlib.sha256(clave.encode()).hexdigest()[:39]


def invalidar_clave(clave: str) -> bool:
    """Garantiza que la sesión `clave` deja de valer, sin esperar bloqueos (TKT-044, THREAT-002).

    Borra su fila con NOWAIT. Si otra transacción la tiene bloqueada (una renovación en curso, una
    invalidación de las sesiones de la cuenta que aún puede deshacerse...), inserta su marca de
    revocación: la marca no referencia la cuenta ni toca la fila bloqueada, así que no espera a
    nadie, y `SessionStore` ya no carga esa clave aunque la fila sobreviva. Devuelve True si la
    fila se borró (o no existía) y False si quedó revocada por la marca. Otros errores de la BD se
    propagan (no se oculta que la sesión pudo quedar viva)."""
    modelo = SessionStore.get_model_class()
    using = router.db_for_write(modelo)
    tabla = connections[using].ops.quote_name(modelo._meta.db_table)
    # Identificador de la tabla citado por quote_name; el valor va parametrizado.
    sentencia = (
        f"DELETE FROM {tabla} WHERE session_key IN "  # noqa: S608  # nosec B608
        f"(SELECT session_key FROM {tabla} WHERE session_key = %s FOR UPDATE NOWAIT)"
    )
    try:
        with transaction.atomic(using=using), connections[using].cursor() as cursor:
            cursor.execute(sentencia, [clave])
    except DatabaseError as exc:
        if not fallo_por_contencion(exc):
            raise
    else:
        return True
    caducidad = timezone.now() + timedelta(
        seconds=max(settings.PANEL_SESION_MAXIMA_SEGUNDOS, settings.SESSION_COOKIE_AGE)
    )
    modelo.objects.using(using).bulk_create(
        [modelo(session_key=clave_revocacion(clave), session_data="", expire_date=caducidad)],
        ignore_conflicts=True,  # otra invalidación ya la marcó
    )
    return False


class SessionStore(SessionStoreBD):
    def __init__(self, session_key: str | None = None) -> None:
        super().__init__(session_key)
        # (clave, datos) de lo último que esta instancia guardó en la BD (TKT-040).
        self._guardado: tuple[str, dict[str, Any]] | None = None

    @classmethod
    def get_model_class(cls) -> type[SesionPanel]:
        from apps.cuentas.models import SesionPanel

        return SesionPanel

    def create_model_instance(self, data: dict[str, Any]) -> SesionPanel:
        instancia = cast("SesionPanel", super().create_model_instance(data))
        cuenta_id = data.get(CLAVE_CUENTA)
        instancia.cuenta_id = cuenta_id if isinstance(cuenta_id, int) else None
        instancia.autenticado_en = _fecha(data.get(CLAVE_AUTENTICADO_EN))
        return instancia

    def _validate_session_key(self, key: str | None) -> bool:
        """Una clave de marca de revocación nunca es una clave de sesión válida (TKT-044)."""
        valida = super()._validate_session_key(key)  # type: ignore[misc]
        return bool(valida) and not str(key).startswith(_PREFIJO_REVOCACION)

    def _get_session_from_db(self) -> SesionPanel | None:
        """Como el de Django, pero una clave revocada (con marca) no carga (TKT-044): la misma
        consulta por la PK comprueba que no exista su marca de revocación."""
        clave = str(self.session_key)
        modelo = self.model
        try:
            return cast(
                "SesionPanel",
                modelo.objects.filter(
                    ~Exists(modelo.objects.filter(session_key=clave_revocacion(clave)))
                ).get(session_key=clave, expire_date__gt=timezone.now()),
            )
        except (modelo.DoesNotExist, SuspiciousOperation) as exc:
            if isinstance(exc, SuspiciousOperation):
                logging.getLogger(f"django.security.{exc.__class__.__name__}").warning(str(exc))
            self._session_key = None
            return None

    def crear_con_clave_nueva(self) -> str | None:
        """Da de alta (INSERT) una clave nueva con los datos actuales y devuelve la anterior, que
        NO se borra: la invalida quien llama con `invalidar_clave` (TKT-044).

        A diferencia de `cycle_key` de Django (que asigna la clave nueva ANTES de guardarla), si la
        INSERT falla la sesión conserva la clave anterior y el error se propaga: quien llama sabe
        de verdad que no hubo clave nueva (F-02 de la QA de TKT-040)."""
        datos = self._session  # type: ignore[attr-defined]
        anterior = self.session_key
        self._alta_con_clave_nueva(anterior)
        self._session_cache = datos
        self.modified = True
        return anterior

    def create(self) -> None:
        """Alta de una sesión nueva (login). Como la de Django, pero acotada: Django reintenta
        para siempre ante cualquier CreateError, y una FK de la cuenta violada (cuenta borrada
        mientras tanto: las FK son DEFERRABLE y fallan en el COMMIT) no es una clave repetida y
        nunca dejaría de fallar (TKT-044). Ese error de la BD se propaga a quien llama."""
        self._alta_con_clave_nueva(None)
        self.modified = True

    def _alta_con_clave_nueva(self, anterior: str | None) -> None:
        """INSERT de los datos actuales con una clave nueva. Solo una clave repetida (23505) se
        reintenta con otra; cualquier otro fallo restaura `anterior` y propaga el error de la BD."""
        for intento in range(1, _INTENTOS_CLAVE_NUEVA + 1):
            self._session_key = self._get_new_session_key()  # type: ignore[attr-defined]
            try:
                self.save(must_create=True)
            except CreateError as exc:
                causa = exc.__cause__
                repetida = causa is not None and sqlstate_de(causa) == _SQLSTATE_CLAVE_REPETIDA
                if repetida and intento < _INTENTOS_CLAVE_NUEVA:
                    continue
                self._session_key = anterior
                if isinstance(causa, DatabaseError):
                    raise causa from exc
                raise
            except BaseException:
                self._session_key = anterior
                raise
            return

    def save(self, must_create: bool = False) -> None:
        if self.session_key is None:
            self.create()
            return
        datos = self._get_session(no_load=must_create)  # type: ignore[attr-defined]
        if not must_create and self._guardado == (self.session_key, datos):
            return  # ya guardada tal cual en esta petición (guardado temprano, TKT-040)
        instancia = self.create_model_instance(datos)
        using = router.db_for_write(self.model, instance=instancia)
        try:
            with transaction.atomic(using=using):
                instancia.save(
                    force_insert=must_create,
                    force_update=not must_create,
                    update_fields=None if must_create else _CAMPOS_ACTUALIZABLES,
                    using=using,
                )
        except IntegrityError as exc:
            if must_create:
                raise CreateError from exc
            raise
        except DatabaseError as exc:
            # La sesión se invalidó mientras tanto (logout, desactivación, restablecimiento).
            if not must_create:
                raise UpdateError from exc
            raise
        self._guardado = (self.session_key, dict(datos))
