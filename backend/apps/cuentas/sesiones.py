"""Almacén de sesiones de Django sobre la tabla `sesion_panel` (ADR-DB-005 §2, DEC-AUTO-089).

Solo enlaza el backend de sesiones en base de datos con el modelo `SesionPanel`. La asociación
de la sesión con la cuenta, la expiración absoluta de 12 h y la activación como SESSION_ENGINE
son parte del flujo de autenticación del panel (TKT-004).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.sessions.backends.db import SessionStore as SessionStoreBD

if TYPE_CHECKING:
    from apps.cuentas.models import SesionPanel


class SessionStore(SessionStoreBD):
    @classmethod
    def get_model_class(cls) -> type[SesionPanel]:
        from apps.cuentas.models import SesionPanel

        return SesionPanel
