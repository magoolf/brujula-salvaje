"""Almacén de sesiones de Django sobre la tabla `sesion_panel` (ADR-DB-005 §2, DEC-AUTO-089).

SESSION_ENGINE = "apps.cuentas.sesiones" (TKT-004). Además del contenido cifrado y firmado de la
sesión, cada fila guarda en columnas propias:
- `cuenta_id`: permite invalidar todas las sesiones de una cuenta (THREAT-002/025, AC-107);
- `autenticado_en`: inicio de la autenticación, para la expiración absoluta de 12 h.
Ambos valores se toman de las claves CLAVE_CUENTA y CLAVE_AUTENTICADO_EN de la sesión.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.contrib.sessions.backends.base import CreateError, UpdateError
from django.contrib.sessions.backends.db import SessionStore as SessionStoreBD
from django.db import DatabaseError, IntegrityError, router, transaction

if TYPE_CHECKING:
    from apps.cuentas.models import SesionPanel

CLAVE_CUENTA = "panel_cuenta_id"
CLAVE_AUTENTICADO_EN = "panel_autenticado_en"

# En una actualización no se reescribe creado_en (tiene db_default y conserva su valor).
_CAMPOS_ACTUALIZABLES = ["session_data", "expire_date", "cuenta", "autenticado_en"]


def _fecha(valor: Any) -> datetime | None:
    if not valor:
        return None
    return datetime.fromisoformat(str(valor))


class SessionStore(SessionStoreBD):
    @classmethod
    def get_model_class(cls) -> type[SesionPanel]:
        from apps.cuentas.models import SesionPanel

        return SesionPanel

    def create_model_instance(self, data: dict[str, Any]) -> SesionPanel:
        instancia: SesionPanel = super().create_model_instance(data)
        instancia.cuenta_id = data.get(CLAVE_CUENTA)
        instancia.autenticado_en = _fecha(data.get(CLAVE_AUTENTICADO_EN))
        return instancia

    def save(self, must_create: bool = False) -> None:
        if self.session_key is None:
            self.create()
            return
        datos = self._get_session(no_load=must_create)
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
