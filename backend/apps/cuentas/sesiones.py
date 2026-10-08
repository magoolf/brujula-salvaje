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
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from django.contrib.sessions.backends.base import CreateError, UpdateError
from django.contrib.sessions.backends.db import SessionStore as SessionStoreBD
from django.db import DatabaseError, IntegrityError, router, transaction

from apps.core.exceptions import SQLSTATE_CONCURRENCIA, sqlstate_de

if TYPE_CHECKING:
    from django.contrib.sessions.backends.base import SessionBase

    from apps.cuentas.models import SesionPanel

CLAVE_CUENTA = "panel_cuenta_id"
CLAVE_AUTENTICADO_EN = "panel_autenticado_en"

# En una actualización no se reescribe creado_en (tiene db_default y conserva su valor).
_CAMPOS_ACTUALIZABLES = ["session_data", "expire_date", "cuenta", "autenticado_en"]


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
