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
- Rotación del identificador (THREAT-002): `abrir_sesion` y `rotar_sesion`. La sesión anterior
  queda invalidada SIEMPRE (TKT-044): `invalidar_clave` borra su fila sin esperar bloqueos o, si
  otra transacción la tiene bloqueada, la revoca con una marca que la carga de sesiones respeta.
  Si la clave nueva no puede darse de alta, la anterior se invalida igualmente y la respuesta es
  401 `sesion_expirada` (el efecto ya está confirmado: nunca 409).
- Guardado de la sesión dentro de DRF (TKT-040, ADR-API-002 §22). Antes lo hacía
  SessionMiddleware.process_response al final de la petición, fuera del EXCEPTION_HANDLER: un
  UPDATE de `sesion_panel` que chocaba con un bloqueo o encontraba la fila borrada respondía 400
  `validacion` (SessionInterrupted) y, en una escritura, con su efecto YA confirmado
  (ATOMIC_REQUESTS=False). Ahora:
  * La renovación de la inactividad se guarda en `authenticate`, ANTES de que la vista haga nada.
    Fila borrada (sesión invalidada en paralelo) → petición anónima con sesión expirada (401
    `sesion_expirada` en las vistas que exigen sesión). Contención (55P03/40P01/40001) → 409
    `conflicto_version` en los métodos no seguros que lo declaran: no hubo efectos y reintentar es
    seguro; en GET/HEAD y en las vistas previas (que no declaran 409) → 401 `sesion_expirada`.
  * Lo que una vista cambia en la sesión DESPUÉS de su efecto (abrir y rotar la sesión) se guarda
    en la propia vista y nunca responde 409 (que invitaría a repetir una operación ya confirmada):
    contención → la respuesta de éxito (la renovación no se aplica, queda en el log); fila ya
    borrada → 401 `sesion_expirada` y la cookie se borra.
  * `cerrar_sesion` borra la fila antes del efecto (la auditoría LOGOUT va después): contención →
    409 `conflicto_version` sin efectos.
  * Red de seguridad para cualquier otro caso: apps.cuentas.middleware.SesionPanelMiddleware.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

import structlog
from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.db import DatabaseError, IntegrityError
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
from apps.cuentas.sesiones import (
    CLAVE_AUTENTICADO_EN,
    CLAVE_CUENTA,
    SessionStore,
    descartar_en_memoria,
    fallo_por_contencion,
    invalidar_clave,
    marcar_guardada,
)

if TYPE_CHECKING:
    from django.contrib.sessions.backends.base import SessionBase
    from rest_framework.request import Request

logger = structlog.get_logger("brujula.cuentas")

CLAVE_ULTIMA_ACTIVIDAD = "panel_ultima_actividad"
CLAVE_MFA_VERIFICADO = "panel_mfa_verificado"
CLAVE_REDIRECCION = "panel_redireccion"
ATRIBUTO_EXPIRADA = "panel_sesion_expirada"
# Ámbitos de tasa (x-limite-tasa del contrato) cuyas operaciones no escriben y no declaran 409: las
# vistas previas del panel. Ante contención al renovar la sesión responden 401 sesion_expirada.
_AMBITOS_SIN_CONFLICTO = frozenset({"panel-vista-previa"})


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


def _guardar_tras_efecto(sesion: SessionBase) -> None:
    """Guarda la sesión cuando el efecto de la vista ya está confirmado (TKT-040, OBS-01 de la QA
    de CHG-API-006). Nunca un 409 (el contrato lo define "sin efectos, reintentable"):
    - contención (55P03/40P01/40001) → la respuesta de éxito de la operación; lo que no pudo
      guardarse (la renovación de la inactividad) simplemente no se aplica y queda en el log;
    - fila de la sesión ya borrada (invalidación concurrente), o alta de una sesión nueva que no
      pudo hacerse → 401 sesion_expirada y la cookie se borra."""
    try:
        sesion.save()
    except UpdateError as exc:
        if fallo_por_contencion(exc):
            logger.warning("sesion_no_guardada", momento="tras_efecto", contencion=True)
            marcar_guardada(sesion)  # el middleware fija la cookie sin volver a intentarlo
            return
        logger.warning("sesion_no_guardada", momento="tras_efecto", contencion=False)
        descartar_en_memoria(sesion)
        raise ErrorApi(codigo="sesion_expirada") from exc
    except DatabaseError as exc:
        # Alta de una sesión nueva (login) que choca con un bloqueo o cuya cuenta ya no existe
        # (FK violada, TKT-044): no hay sesión que entregar y el efecto ya está confirmado →
        # 401 sesion_expirada, no 409.
        if not _alta_imposible(exc):
            raise
        logger.warning("sesion_no_creada", contencion=fallo_por_contencion(exc))
        descartar_en_memoria(sesion)
        raise ErrorApi(codigo="sesion_expirada") from exc


def _alta_imposible(exc: DatabaseError) -> bool:
    """La INSERT de una clave nueva falló por contención (55P03/40P01/40001) o porque la cuenta
    ya no existe (FK violada): sin sesión que entregar → 401. Otro error de la BD es un 500."""
    return fallo_por_contencion(exc) or isinstance(exc, IntegrityError)


def _invalidar_anterior(clave: str | None, *, momento: str) -> None:
    """Invalida la sesión anterior a una apertura o rotación (THREAT-002, TKT-044). Si su fila
    estaba bloqueada por otra transacción queda revocada por marca: nunca sigue siendo válida."""
    if clave and not invalidar_clave(clave):
        logger.warning("sesion_anterior_revocada", momento=momento, contencion=True)


def abrir_sesion(
    sesion: SessionBase, cuenta: CuentaStaff, *, mfa_verificado: bool, redireccion: str
) -> None:
    """Nueva sesión (identificador nuevo; la anterior se invalida) tras validar la contraseña.

    Se guarda ya, dentro de DRF (TKT-040): el login ya está confirmado (_guardar_tras_efecto)."""
    _invalidar_anterior(sesion.session_key, momento="apertura")
    descartar_en_memoria(sesion)
    ahora = timezone.now().isoformat()
    sesion[CLAVE_CUENTA] = cuenta.pk
    sesion[CLAVE_AUTENTICADO_EN] = ahora
    sesion[CLAVE_ULTIMA_ACTIVIDAD] = ahora
    sesion[CLAVE_MFA_VERIFICADO] = mfa_verificado
    sesion[CLAVE_REDIRECCION] = redireccion
    _fijar_caducidad(sesion)
    _guardar_tras_efecto(sesion)


def rotar_sesion(sesion: SessionBase, *, mfa_verificado: bool | None = None) -> None:
    """Cambia el identificador conservando los datos (MFA, contraseña, privilegios).

    La vista la llama tras su efecto (TKT-040): nunca 409. TKT-044:
    - alta (INSERT) de la clave nueva con los datos; si falla de verdad (bloqueo de la cuenta por
      la FK, cuenta borrada, otro error...), la clave anterior se invalida igualmente y se descarta
      la sesión: 401 `sesion_expirada` (_alta_imposible); otro error de la BD se propaga (500);
    - la clave anterior se invalida aunque su fila esté bloqueada (marca de revocación)."""
    tienda = cast(SessionStore, sesion)
    if mfa_verificado is not None:
        tienda[CLAVE_MFA_VERIFICADO] = mfa_verificado
    _fijar_caducidad(tienda)
    try:
        anterior = tienda.crear_con_clave_nueva()
    except DatabaseError as exc:
        # Primero la seguridad (THREAT-002): invalidar la anterior antes de cualquier otro
        # cálculo, incluido el del log (QA TKT-044 F-A).
        _invalidar_anterior(tienda.session_key, momento="rotacion_fallida")
        descartar_en_memoria(tienda)
        logger.warning("sesion_no_rotada", contencion=fallo_por_contencion(exc))
        if not _alta_imposible(exc):
            raise
        raise ErrorApi(codigo="sesion_expirada") from exc
    _invalidar_anterior(anterior, momento="rotacion")
    _guardar_tras_efecto(tienda)  # sin consultas si nada cambió desde el alta


def cerrar_sesion(sesion: SessionBase) -> None:
    """Borra la sesión en la BD. Las vistas la llaman ANTES de auditar el cierre (TKT-040): si el
    borrado choca con un bloqueo (p. ej. una invalidación concurrente de las sesiones de la
    cuenta), 409 conflicto_version sin efectos (traducción global de core) y la sesión sigue
    intacta para reintentar: se borra la fila ANTES de vaciar la sesión en memoria (`flush()`
    la vacía primero y, si el borrado fallara, el middleware guardaría una sesión vacía)."""
    sesion.delete()
    descartar_en_memoria(sesion)


def descartar_sesion(sesion: SessionBase) -> None:
    """Invalida la sesión tras un efecto ya confirmado o al detectar que expiró, sin esperar
    bloqueos: si su fila está bloqueada queda revocada por marca (TKT-044). La sesión se descarta
    en esta respuesta (cookie borrada)."""
    _invalidar_anterior(sesion.session_key, momento="descarte")
    descartar_en_memoria(sesion)


def _codigo_contencion(request: Request, vista: Any) -> str:
    """Código ante contención al renovar la inactividad, antes de que la vista actúe: 409 en los
    métodos no seguros que lo declaran (sin efectos, reintentable); 401 sesion_expirada en las
    lecturas y en las vistas previas, que no declaran 409 (contrato, ADR-API-002 §22)."""
    if request.method in SAFE_METHODS:
        return "sesion_expirada"
    if getattr(vista, "throttle_scope", None) in _AMBITOS_SIN_CONFLICTO:
        return "sesion_expirada"
    return "conflicto_version"


def _renovar(request: Request, sesion: SessionBase, vista: Any, ahora: datetime) -> bool:
    """Renueva la inactividad y la guarda ya, dentro de DRF (TKT-040). False si la fila de la
    sesión ya no existe (se invalidó en paralelo): la petición queda anónima y expirada."""
    marcar_actividad(sesion, ahora)
    try:
        sesion.save()
    except UpdateError as exc:
        if not fallo_por_contencion(exc):
            logger.info("sesion_invalidada_en_curso")
            descartar_en_memoria(sesion)
            return False
        codigo = _codigo_contencion(request, vista)
        logger.warning("sesion_no_guardada", momento="renovacion", codigo=codigo)
        # La sesión sigue siendo válida: no se vuelve a intentar guardar al final de la petición.
        sesion.modified = False
        raise ErrorApi(codigo=codigo) from exc
    return True


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
            descartar_sesion(sesion)
            setattr(peticion, ATRIBUTO_EXPIRADA, True)
            return None
        cuenta = selectors.cuenta_con_sesion(datos.cuenta_id)
        if cuenta is None:
            descartar_sesion(sesion)
            return None
        vista = (request.parser_context or {}).get("view")
        if getattr(vista, "renueva_inactividad", True) and not _renovar(
            request, sesion, vista, ahora
        ):
            setattr(peticion, ATRIBUTO_EXPIRADA, True)
            return None
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
