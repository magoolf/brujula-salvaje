"""Permisos del panel (Blueprint §12 deny-by-default, STATE-004, THREAT-004, AC-105).

- `SesionPanel`: exige una sesión vigente y que el paso pendiente de la sesión esté entre los
  `pasos_permitidos` de la vista (por defecto solo NINGUNO). Si no, el código del contrato:
  401 mfa_requerido · 403 cambio_credencial_requerido / configuracion_mfa_requerida /
  autorizacion_requerida (y 403 permiso_denegado si la vista es solo de un paso intermedio).
- `SoloAdministrador`: el rol se lee de la cuenta en la BD, nunca de la petición (THREAT-004).
Otras apps del panel (TKT-005/006) importan estas clases (no son parte de la capa api).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import BasePermission

from apps.core.exceptions import ErrorApi
from apps.cuentas import selectors
from apps.cuentas.autenticacion import ATRIBUTO_EXPIRADA, leer_sesion
from apps.cuentas.models import CuentaStaff
from apps.cuentas.services import Paso, paso_pendiente

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

TODOS_LOS_PASOS = frozenset(Paso)
CODIGO_POR_PASO = {
    Paso.NINGUNO: "permiso_denegado",
    Paso.MFA: "mfa_requerido",
    Paso.CAMBIO_CREDENCIAL: "cambio_credencial_requerido",
    Paso.CONFIGURAR_MFA: "configuracion_mfa_requerida",
    Paso.AUTORIZACION: "autorizacion_requerida",
}
_ATRIBUTO_PASO = "panel_paso_pendiente"


def cuenta_de(request: Request) -> CuentaStaff:
    cuenta = request.user
    if not isinstance(cuenta, CuentaStaff):
        expirada = getattr(request._request, ATRIBUTO_EXPIRADA, False)
        raise ErrorApi(codigo="sesion_expirada" if expirada else "no_autenticado")
    return cuenta


def paso_de(request: Request) -> Paso:
    """Paso pendiente de la sesión actual (se calcula una vez por petición)."""
    paso = getattr(request._request, _ATRIBUTO_PASO, None)
    if isinstance(paso, Paso):
        return paso
    cuenta = cuenta_de(request)
    datos = leer_sesion(request._request.session)
    paso = paso_pendiente(
        cuenta,
        mfa_verificado=bool(datos and datos.mfa_verificado),
        version_vigente=selectors.politica_vigente().version,
    )
    setattr(request._request, _ATRIBUTO_PASO, paso)
    return paso


def olvidar_paso(request: Request) -> None:
    """Tras cambiar el estado de la cuenta en la vista, el paso se vuelve a calcular."""
    if hasattr(request._request, _ATRIBUTO_PASO):
        delattr(request._request, _ATRIBUTO_PASO)


class SesionPanel(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        paso = paso_de(request)
        permitidos = getattr(view, "pasos_permitidos", frozenset({Paso.NINGUNO}))
        if paso not in permitidos:
            raise ErrorApi(codigo=CODIGO_POR_PASO[paso])
        return True


class SoloAdministrador(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not cuenta_de(request).es_administrador:
            raise ErrorApi(codigo="permiso_denegado")
        return True
