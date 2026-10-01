"""Autenticación propia del panel: sesión en `sesion_panel` + CSRF (ADR-API-001, OBS-QA003-06).

No se usa django.contrib.auth (ni ModelBackend ni AuthenticationMiddleware): sus tablas auth_*
no existen (DB_HANDOFF). La cuenta de la sesión se lee de la clave CLAVE_CUENTA.

- CSRF (THREAT-003): toda petición con método no seguro que pase por esta clase se valida con el
  mismo mecanismo que CsrfViewMiddleware (las vistas de DRF están exentas del middleware), también
  el login, que aún no tiene sesión. Fallo → 403 `csrf_invalido`.
- Expiración (DEC-AUTO-049, AC-109): 30 min de inactividad y 12 h absolutas. Una sesión vencida
  se borra y la petición queda anónima; los permisos responden 401 `sesion_expirada`.
- Actividad: cada petición autenticada renueva la inactividad salvo las vistas con
  `renueva_inactividad = False` (GET /auth/sesion, para que el aviso de expiración sea fiable).
- Rotación del identificador (THREAT-002): `abrir_sesion` y `rotar_sesion`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.middleware.csrf import CsrfViewMiddleware
from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import SAFE_METHODS

from apps.core.exceptions import ErrorApi
from apps.cuentas import selectors
from apps.cuentas.models import CuentaStaff
from apps.cuentas.services import redireccion_segura
from apps.cuentas.sesiones import CLAVE_AUTENTICADO_EN, CLAVE_CUENTA

if TYPE_CHECKING:
    from django.contrib.sessions.backends.base import SessionBase
    from rest_framework.request import Request

CLAVE_ULTIMA_ACTIVIDAD = "panel_ultima_actividad"
CLAVE_MFA_VERIFICADO = "panel_mfa_verificado"
CLAVE_REDIRECCION = "panel_redireccion"
ATRIBUTO_EXPIRADA = "panel_sesion_expirada"


class _ComprobacionCsrf(CsrfViewMiddleware):
    def _reject(self, request: HttpRequest, reason: str) -> Any:
        return reason


def _sin_respuesta(_peticion: HttpRequest) -> HttpResponseBase:  # pragma: no cover
    return HttpResponse(status=204)


def exigir_csrf(request: HttpRequest) -> None:
    comprobacion = _ComprobacionCsrf(_sin_respuesta)
    comprobacion.process_request(request)
    motivo = comprobacion.process_view(request, _sin_respuesta, (), {})
    if motivo:
        raise ErrorApi(codigo="csrf_invalido")


def _fecha(valor: Any) -> datetime | None:
    return datetime.fromisoformat(valor) if isinstance(valor, str) and valor else None


@dataclass(frozen=True)
class DatosSesion:
    cuenta_id: int
    autenticado_en: datetime
    ultima_actividad: datetime
    mfa_verificado: bool
    redireccion: str

    @property
    def expira_inactividad_en(self) -> datetime:
        return self.ultima_actividad + timedelta(seconds=settings.PANEL_INACTIVIDAD_SEGUNDOS)

    @property
    def expira_absoluta_en(self) -> datetime:
        return self.autenticado_en + timedelta(seconds=settings.PANEL_SESION_MAXIMA_SEGUNDOS)

    @property
    def expira_en(self) -> datetime:
        return min(self.expira_inactividad_en, self.expira_absoluta_en)


def leer_sesion(sesion: SessionBase) -> DatosSesion | None:
    cuenta_id = sesion.get(CLAVE_CUENTA)
    autenticado_en = _fecha(sesion.get(CLAVE_AUTENTICADO_EN))
    ultima = _fecha(sesion.get(CLAVE_ULTIMA_ACTIVIDAD))
    if not isinstance(cuenta_id, int) or autenticado_en is None or ultima is None:
        return None
    return DatosSesion(
        cuenta_id=cuenta_id,
        autenticado_en=autenticado_en,
        ultima_actividad=ultima,
        mfa_verificado=bool(sesion.get(CLAVE_MFA_VERIFICADO, False)),
        redireccion=_redireccion_guardada(sesion),
    )


def _redireccion_guardada(sesion: SessionBase) -> str:
    """TKT-031 OBS-05: el destino guardado se revalida al leerlo (sesiones abiertas con reglas
    anteriores a un despliegue, o valores no textuales); si no es válido, /panel."""
    valor = sesion.get(CLAVE_REDIRECCION)
    return redireccion_segura(valor if isinstance(valor, str) else None)


def _fijar_caducidad(sesion: SessionBase) -> None:
    datos = leer_sesion(sesion)
    if datos is not None:
        sesion.set_expiry(datos.expira_en)


def marcar_actividad(sesion: SessionBase, ahora: datetime | None = None) -> None:
    sesion[CLAVE_ULTIMA_ACTIVIDAD] = (ahora or timezone.now()).isoformat()
    _fijar_caducidad(sesion)


def abrir_sesion(
    sesion: SessionBase, cuenta: CuentaStaff, *, mfa_verificado: bool, redireccion: str
) -> None:
    """Nueva sesión (identificador nuevo; la anterior se borra) tras validar la contraseña."""
    sesion.flush()
    ahora = timezone.now().isoformat()
    sesion[CLAVE_CUENTA] = cuenta.pk
    sesion[CLAVE_AUTENTICADO_EN] = ahora
    sesion[CLAVE_ULTIMA_ACTIVIDAD] = ahora
    sesion[CLAVE_MFA_VERIFICADO] = mfa_verificado
    sesion[CLAVE_REDIRECCION] = redireccion
    _fijar_caducidad(sesion)


def rotar_sesion(sesion: SessionBase, *, mfa_verificado: bool | None = None) -> None:
    """Cambia el identificador conservando los datos (MFA, contraseña, privilegios)."""
    if mfa_verificado is not None:
        sesion[CLAVE_MFA_VERIFICADO] = mfa_verificado
    sesion.cycle_key()
    _fijar_caducidad(sesion)


def cerrar_sesion(sesion: SessionBase) -> None:
    sesion.flush()


class AutenticacionSesionPanel(BaseAuthentication):
    """DEFAULT_AUTHENTICATION_CLASSES de DRF. Devuelve (cuenta, None) o None (anónima)."""

    def authenticate(self, request: Request) -> tuple[CuentaStaff, None] | None:
        peticion: HttpRequest = request._request
        if request.method not in SAFE_METHODS:
            exigir_csrf(peticion)
        sesion: SessionBase | None = getattr(peticion, "session", None)
        if sesion is None:
            return None
        datos = leer_sesion(sesion)
        if datos is None:
            return None
        ahora = timezone.now()
        if ahora >= datos.expira_en:
            cerrar_sesion(sesion)
            setattr(peticion, ATRIBUTO_EXPIRADA, True)
            return None
        cuenta = selectors.cuenta_con_sesion(datos.cuenta_id)
        if cuenta is None:
            cerrar_sesion(sesion)
            return None
        vista = (request.parser_context or {}).get("view")
        if getattr(vista, "renueva_inactividad", True):
            marcar_actividad(sesion, ahora)
        return (cuenta, None)


class EsquemaSesionPanel(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    """securitySchemes del contrato: cookie `sessionid` (+ cabecera X-CSRFToken si no es GET)."""

    target_class = "apps.cuentas.autenticacion.AutenticacionSesionPanel"
    name = ["sesionPanel", "csrfToken"]

    def get_security_requirement(self, auto_schema: Any) -> dict[str, list[Any]]:
        if auto_schema.method in SAFE_METHODS:
            return {"sesionPanel": []}
        return {"sesionPanel": [], "csrfToken": []}

    def get_security_definition(self, auto_schema: Any) -> list[dict[str, str]]:
        return [
            {"type": "apiKey", "in": "cookie", "name": settings.SESSION_COOKIE_NAME},
            {"type": "apiKey", "in": "header", "name": "X-CSRFToken"},
        ]
