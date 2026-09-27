"""Vistas del acceso al panel y de las cuentas del staff (contracts/openapi.yaml).

Solo transporte HTTP (Skill_Backend §4.1, Reglas 01-03): validan la estructura, delegan en
apps.cuentas.services y serializan. La sesión HTTP se gestiona con apps.cuentas.autenticacion.
"""

from __future__ import annotations

from typing import Any, cast

from django.middleware.csrf import get_token
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import SAFE_METHODS, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import idempotencia
from apps.core.api.serializers import (
    ProblemaConUsosSerializer,
    ProblemaValidacionSerializer,
    ProblemSerializer,
)
from apps.core.exceptions import NoEncontrado
from apps.core.paginacion import PaginacionNumerada
from apps.core.parametros import errores_de_parametros, validar_parametros
from apps.core.problemas import MEDIA_TYPE_PROBLEMA
from apps.core.throttling import ip_cliente
from apps.cuentas import selectors, services
from apps.cuentas.api import serializers as s
from apps.cuentas.autenticacion import (
    abrir_sesion,
    cerrar_sesion,
    leer_sesion,
    redireccion_segura,
    rotar_sesion,
)
from apps.cuentas.models import CuentaStaff, EstadoCuenta, RolCuenta
from apps.cuentas.permisos import (
    TODOS_LOS_PASOS,
    SesionPanel,
    SoloAdministrador,
    cuenta_de,
    olvidar_paso,
    paso_de,
)
from apps.cuentas.services import Paso

ID_MAXIMO = 2**63 - 1
TRAS_MFA = frozenset(TODOS_LOS_PASOS - {Paso.MFA})


# ---------------------------------------------------------------------------
# Documentación de errores (components.responses del contrato)
# ---------------------------------------------------------------------------
def _problema(descripcion: str, codigo: int) -> OpenApiResponse:
    """Esquema de error del contrato: ProblemaValidacion (400/422), ProblemaConUsos (409)."""
    esquema: type[ProblemSerializer] = ProblemSerializer
    if codigo in (400, 422):
        esquema = ProblemaValidacionSerializer
    elif codigo == 409:
        esquema = ProblemaConUsosSerializer
    return OpenApiResponse(esquema, description=descripcion)


def _errores(*codigos: int) -> dict[Any, OpenApiResponse]:
    descripciones = {
        400: "400 validacion / parametro_invalido / campo_no_permitido.",
        401: "401 no_autenticado / sesion_expirada / credenciales_invalidas / mfa_*.",
        403: "403 permiso_denegado / csrf_invalido / paso pendiente.",
        404: "404 no_encontrado / pagina_fuera_de_rango.",
        409: "409 conflicto (transicion_invalida, duplicado, ultimo_administrador...).",
        422: "422 regla_negocio / idempotencia_conflicto.",
        429: "429 limite_tasa / acceso_bloqueado_temporalmente (Retry-After).",
        500: "500 error_interno.",
    }
    return {
        (codigo, MEDIA_TYPE_PROBLEMA): _problema(descripciones[codigo], codigo)
        for codigo in codigos
    }


def _ip(request: Request) -> str | None:
    return ip_cliente(request.META)


def _estado_sesion(request: Request, cuenta: CuentaStaff, paso: Paso) -> Response:
    datos = leer_sesion(request.session)
    if datos is None:  # pragma: no cover - la vista solo se llega con sesión
        raise NoEncontrado()
    cuerpo = s.SesionEstadoSerializer(
        {
            "usuario": cuenta.usuario,
            "nombre_visible": cuenta.nombre_visible,
            "rol": cuenta.rol,
            "paso_pendiente": paso.value,
            "mfa_activo": cuenta.mfa_activo,
            "mfa_obligatorio": cuenta.es_administrador,
            "expira_inactividad_en": datos.expira_inactividad_en,
            "expira_absoluta_en": datos.expira_absoluta_en,
            "redireccion": datos.redireccion,
        }
    ).data
    return Response(cuerpo)


def _estado_actual(request: Request) -> Response:
    olvidar_paso(request)
    return _estado_sesion(request, cuenta_de(request), paso_de(request))


class _VistaPanel(APIView):
    """Base: sesión del panel obligatoria; por defecto solo sin pasos pendientes."""

    permission_classes = [SesionPanel]
    pasos_permitidos: frozenset[Paso] = frozenset({Paso.NINGUNO})
    renueva_inactividad = True
    throttle_scope = "panel-escritura"


class _VistaPanelMixta(_VistaPanel):
    """GET cuenta como lectura y el resto como escritura (x-limite-tasa del contrato)."""

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        lectura = request.method in SAFE_METHODS
        self.throttle_scope = "panel-lectura" if lectura else "panel-escritura"
        super().initial(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# panel-auth
# ---------------------------------------------------------------------------
class ObtenerCsrf(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "panel-login"

    @extend_schema(
        operation_id="panelObtenerCsrf",
        summary="Emite la cookie csrftoken antes del login",
        tags=["panel-auth"],
        auth=[],
        responses={
            204: OpenApiResponse(description="Cookie csrftoken emitida."),
            **_errores(429, 500),
        },
    )
    def get(self, request: Request) -> Response:
        get_token(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class IniciarSesion(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "panel-login"

    @extend_schema(
        operation_id="panelIniciarSesion",
        summary="Iniciar sesión (usuario y contraseña)",
        tags=["panel-auth"],
        auth=[{"csrfToken": []}],  # type: ignore[list-item]
        request=s.LoginEntradaSerializer,
        responses={200: s.SesionEstadoSerializer, **_errores(400, 401, 403, 429, 500)},
    )
    def post(self, request: Request) -> Response:
        entrada = s.LoginEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        resultado = services.iniciar_sesion(datos["usuario"], datos["contrasena"], _ip(request))
        abrir_sesion(
            request.session,
            resultado.cuenta,
            mfa_verificado=not resultado.requiere_mfa,
            redireccion=redireccion_segura(datos.get("siguiente")),
        )
        paso = services.paso_pendiente(
            resultado.cuenta,
            mfa_verificado=not resultado.requiere_mfa,
            version_vigente=selectors.politica_vigente().version,
        )
        return _estado_sesion(request, resultado.cuenta, paso)


class VerificarMfa(_VistaPanel):
    pasos_permitidos = frozenset({Paso.MFA})
    throttle_scope = "panel-mfa"

    @extend_schema(
        operation_id="panelVerificarMfa",
        summary="Segundo factor (TOTP o código de recuperación)",
        tags=["panel-auth"],
        request=s.MfaVerificacionEntradaSerializer,
        responses={200: s.SesionEstadoSerializer, **_errores(400, 401, 403, 429, 500)},
    )
    def post(self, request: Request) -> Response:
        entrada = s.MfaVerificacionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        cuenta = cuenta_de(request)
        try:
            services.verificar_mfa(cuenta.pk, entrada.validated_data["codigo"], _ip(request))
        except services.AccesoBloqueado:
            cerrar_sesion(request.session)
            raise
        rotar_sesion(request.session, mfa_verificado=True)
        return _estado_actual(request)


class CerrarSesion(_VistaPanel):
    pasos_permitidos = TODOS_LOS_PASOS

    @extend_schema(
        operation_id="panelCerrarSesion",
        summary="Cerrar sesión (invalida en el servidor)",
        tags=["panel-auth"],
        request=None,
        responses={
            204: OpenApiResponse(description="Sesión invalidada."),
            **_errores(401, 403, 429, 500),
        },
    )
    def post(self, request: Request) -> Response:
        services.cerrar_sesion(cuenta_de(request), _ip(request))
        cerrar_sesion(request.session)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ObtenerSesion(_VistaPanel):
    pasos_permitidos = TODOS_LOS_PASOS
    renueva_inactividad = False  # consultarla no renueva la inactividad (AC-109)
    throttle_scope = "panel-lectura"

    @extend_schema(
        operation_id="panelObtenerSesion",
        summary="Estado de la sesión actual",
        tags=["panel-auth"],
        responses={200: s.SesionEstadoSerializer, **_errores(401, 429, 500)},
    )
    def get(self, request: Request) -> Response:
        return _estado_actual(request)


class RenovarSesion(_VistaPanel):
    pasos_permitidos = TODOS_LOS_PASOS

    @extend_schema(
        operation_id="panelRenovarSesion",
        summary="Seguir conectado (renueva la inactividad; nunca supera el máximo de 12 h)",
        tags=["panel-auth"],
        request=None,
        responses={200: s.SesionEstadoSerializer, **_errores(401, 403, 429, 500)},
    )
    def post(self, request: Request) -> Response:
        # La autenticación ya renovó la inactividad (acotada por la expiración absoluta).
        return _estado_actual(request)


class CambiarContrasena(_VistaPanel):
    pasos_permitidos = TRAS_MFA

    @extend_schema(
        operation_id="panelCambiarContrasena",
        summary="Cambiar la contraseña propia (obligatorio tras alta o restablecimiento)",
        tags=["panel-auth"],
        request=s.CambioContrasenaEntradaSerializer,
        responses={200: s.SesionEstadoSerializer, **_errores(400, 401, 403, 429, 500)},
    )
    def post(self, request: Request) -> Response:
        entrada = s.CambioContrasenaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        services.cambiar_contrasena(
            cuenta_de(request).pk,
            datos["contrasena_actual"],
            datos["contrasena_nueva"],
            sesion_actual=request.session.session_key,
        )
        rotar_sesion(request.session)
        cuenta_de(request).refresh_from_db()
        return _estado_actual(request)


class Autorizacion(_VistaPanelMixta):
    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        # GET se puede consultar tras el MFA; POST solo sin pasos previos pendientes.
        lectura = request.method in SAFE_METHODS
        self.pasos_permitidos = (
            TRAS_MFA if lectura else frozenset({Paso.NINGUNO, Paso.AUTORIZACION})
        )
        super().initial(request, *args, **kwargs)

    @extend_schema(
        operation_id="panelObtenerAutorizacion",
        summary="Política de tratamiento vigente y autorización otorgada",
        tags=["panel-auth"],
        responses={200: s.AutorizacionVigenteSerializer, **_errores(401, 429, 500)},
    )
    def get(self, request: Request) -> Response:
        cuenta = cuenta_de(request)
        vigente = selectors.politica_vigente()
        return Response(
            s.AutorizacionVigenteSerializer(
                {
                    "version_politica": vigente.version,
                    "vigente_desde": vigente.vigente_desde,
                    "resumen_finalidad": vigente.resumen_finalidad,
                    "url_politica": vigente.url,
                    "otorgada_en": cuenta.autorizacion_otorgada_en,
                    "version_otorgada": cuenta.autorizacion_version_politica,
                }
            ).data
        )

    @extend_schema(
        operation_id="panelRegistrarAutorizacion",
        summary="Autorizar o no autorizar el tratamiento de datos",
        tags=["panel-auth"],
        request=s.AutorizacionEntradaSerializer,
        responses={
            200: s.SesionEstadoSerializer,
            204: OpenApiResponse(description="No autorizó; sesión cerrada."),
            **_errores(400, 401, 403, 409, 429, 500),
        },
    )
    def post(self, request: Request) -> Response:
        entrada = s.AutorizacionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        cuenta = cuenta_de(request)
        if datos["decision"] == "NO_AUTORIZO":
            services.cerrar_sesion(cuenta, _ip(request))
            cerrar_sesion(request.session)
            return Response(status=status.HTTP_204_NO_CONTENT)
        services.registrar_autorizacion(cuenta.pk, datos["version_politica"])
        cuenta.refresh_from_db()
        return _estado_actual(request)


class IniciarActivacionMfa(_VistaPanel):
    pasos_permitidos = frozenset({Paso.NINGUNO, Paso.CONFIGURAR_MFA})

    @extend_schema(
        operation_id="panelIniciarActivacionMfa",
        summary="Iniciar activación TOTP con reautenticación (URI otpauth; QR en el cliente)",
        tags=["panel-auth"],
        request=s.MfaActivacionInicioEntradaSerializer,
        responses={
            200: s.MfaActivacionInicioSerializer,
            **_errores(400, 401, 403, 409, 429, 500),
        },
    )
    def post(self, request: Request) -> Response:
        entrada = s.MfaActivacionInicioEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        activacion = services.iniciar_activacion_mfa(
            cuenta_de(request).pk, entrada.validated_data["contrasena"], _ip(request)
        )
        return Response(
            s.MfaActivacionInicioSerializer(
                {"otpauth_uri": activacion.uri, "clave_secreta": activacion.secreto}
            ).data
        )


class ConfirmarActivacionMfa(_VistaPanel):
    pasos_permitidos = frozenset({Paso.NINGUNO, Paso.CONFIGURAR_MFA})
    throttle_scope = "panel-mfa"

    @extend_schema(
        operation_id="panelConfirmarActivacionMfa",
        summary="Confirmar activación TOTP; devuelve los códigos de recuperación una sola vez",
        tags=["panel-auth"],
        request=s.MfaCodigoEntradaSerializer,
        responses={200: s.CodigosRecuperacionSerializer, **_errores(400, 401, 403, 409, 429, 500)},
    )
    def post(self, request: Request) -> Response:
        entrada = s.MfaCodigoEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        codigos = services.confirmar_activacion_mfa(
            cuenta_de(request).pk, entrada.validated_data["codigo"]
        )
        rotar_sesion(request.session, mfa_verificado=True)
        return Response(s.CodigosRecuperacionSerializer({"codigos": codigos}).data)


class DesactivarMfa(_VistaPanel):
    throttle_scope = "panel-mfa"

    @extend_schema(
        operation_id="panelDesactivarMfa",
        summary="Desactivar MFA propio (rechazado para Administrador, 409 mfa_obligatorio)",
        tags=["panel-auth"],
        request=s.MfaDesactivacionEntradaSerializer,
        responses={
            204: OpenApiResponse(description="MFA desactivado."),
            **_errores(400, 401, 403, 409, 429, 500),
        },
    )
    def post(self, request: Request) -> Response:
        entrada = s.MfaDesactivacionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        services.desactivar_mfa(cuenta_de(request).pk, datos["contrasena"], datos["codigo"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegenerarCodigosRecuperacion(_VistaPanel):
    throttle_scope = "panel-mfa"

    @extend_schema(
        operation_id="panelRegenerarCodigosRecuperacion",
        summary="Regenerar códigos de recuperación (invalida los anteriores)",
        tags=["panel-auth"],
        request=s.MfaCodigoEntradaSerializer,
        responses={200: s.CodigosRecuperacionSerializer, **_errores(400, 401, 403, 409, 429, 500)},
    )
    def post(self, request: Request) -> Response:
        entrada = s.MfaCodigoEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        codigos = services.regenerar_codigos_recuperacion(
            cuenta_de(request).pk, entrada.validated_data["codigo"]
        )
        return Response(s.CodigosRecuperacionSerializer({"codigos": codigos}).data)


# ---------------------------------------------------------------------------
# panel-cuentas (solo Administrador)
# ---------------------------------------------------------------------------
def _id_cuenta(id: int) -> int:
    if not 1 <= id <= ID_MAXIMO:
        raise NoEncontrado()
    return id


def _ubicacion_cuenta(cuenta_id: int) -> str:
    return f"/api/v1/panel/cuentas/{cuenta_id}"


def _con_temporal(resultado: services.CuentaConTemporal) -> dict[str, Any]:
    return s.CuentaConCredencialTemporalSerializer(
        {"cuenta": resultado.cuenta, "contrasena_temporal": resultado.contrasena_temporal}
    ).data


class _VistaCuentas(_VistaPanelMixta):
    permission_classes = [SesionPanel, SoloAdministrador]


class _AccionCuenta(_VistaCuentas):
    throttle_scope = "panel-escritura"


IDEMPOTENCY_KEY = OpenApiParameter(
    name=idempotencia.CABECERA,
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.HEADER,
    required=False,
    description="UUID opcional (DEC-AUTO-107). Ver components.parameters.IdempotencyKey.",
)


class ListaCuentas(_VistaCuentas):
    tamano_pagina = 50

    @extend_schema(
        operation_id="panelListarCuentas",
        summary="Cuentas del equipo",
        tags=["panel-cuentas"],
        parameters=[
            OpenApiParameter("estado", str, enum=EstadoCuenta.values),
            OpenApiParameter("rol", str, enum=RolCuenta.values),
            OpenApiParameter("pagina", int, description="Número de página (base 1)."),
        ],
        responses={200: s.PaginaCuentaSerializer, **_errores(400, 401, 403, 404, 429, 500)},
    )
    def get(self, request: Request) -> Response:
        validar_parametros(request.query_params, {"estado", "rol", "pagina"})
        filtros = s.FiltroCuentasSerializer(data=request.query_params)
        if not filtros.is_valid():
            raise errores_de_parametros(filtros.errors)
        cuentas = selectors.listar_cuentas(
            estado=filtros.validated_data.get("estado"), rol=filtros.validated_data.get("rol")
        )
        paginador = PaginacionNumerada()
        pagina = paginador.paginate_queryset(cuentas, request, view=self)
        return paginador.get_paginated_response(
            cast("list[Any]", s.CuentaSerializer(pagina, many=True).data)
        )

    @extend_schema(
        operation_id="panelCrearCuenta",
        summary="Alta de cuenta con contraseña temporal (se devuelve una sola vez)",
        tags=["panel-cuentas"],
        parameters=[IDEMPOTENCY_KEY],
        request=s.CuentaCreacionEntradaSerializer,
        responses={
            201: s.CuentaConCredencialTemporalSerializer,
            **_errores(400, 401, 403, 409, 422, 429, 500),
        },
    )
    def post(self, request: Request) -> Response:
        entrada = s.CuentaCreacionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        datos = entrada.validated_data

        def efecto() -> idempotencia.Resultado:
            resultado = services.crear_cuenta(actor, **datos)
            return idempotencia.Resultado(
                codigo_http=status.HTTP_201_CREATED,
                cuerpo=_con_temporal(resultado),
                recurso_id=resultado.cuenta.pk,
            )

        resultado = idempotencia.ejecutar(
            cuenta_id=actor.pk,
            clave=idempotencia.leer_clave(request.headers.get(idempotencia.CABECERA)),
            operacion="panelCrearCuenta",
            huella=idempotencia.huella_peticion("panelCrearCuenta", {}, request.data),
            efecto=efecto,
            reproducible=False,  # la contraseña temporal nunca se persiste (AC-106)
            ubicacion=_ubicacion_cuenta,
        )
        return Response(resultado.cuerpo, status=resultado.codigo_http)


class DetalleCuenta(_VistaCuentas):
    @extend_schema(
        operation_id="panelObtenerCuenta",
        summary="Obtener cuenta",
        tags=["panel-cuentas"],
        responses={200: s.CuentaSerializer, **_errores(401, 403, 404, 429, 500)},
    )
    def get(self, request: Request, id: int) -> Response:
        return Response(s.CuentaSerializer(selectors.obtener_cuenta(_id_cuenta(id))).data)

    @extend_schema(
        operation_id="panelActualizarCuenta",
        summary="Cambiar nombre visible o rol",
        tags=["panel-cuentas"],
        request=s.CuentaActualizacionEntradaSerializer,
        responses={200: s.CuentaSerializer, **_errores(400, 401, 403, 404, 409, 429, 500)},
    )
    def patch(self, request: Request, id: int) -> Response:
        entrada = s.CuentaActualizacionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        cuenta = services.actualizar_cuenta(
            cuenta_de(request),
            _id_cuenta(id),
            nombre_visible=datos.get("nombre_visible"),
            rol=datos.get("rol"),
        )
        return Response(s.CuentaSerializer(cuenta).data)


class RestablecerContrasenaCuenta(_AccionCuenta):
    @extend_schema(
        operation_id="panelRestablecerContrasenaCuenta",
        summary="Nueva contraseña temporal; invalida sesiones; PENDIENTE_ACTIVACION",
        tags=["panel-cuentas"],
        request=None,
        responses={
            200: s.CuentaConCredencialTemporalSerializer,
            **_errores(401, 403, 404, 409, 429, 500),
        },
    )
    def post(self, request: Request, id: int) -> Response:
        return Response(
            _con_temporal(services.restablecer_contrasena(cuenta_de(request), _id_cuenta(id)))
        )


class RestablecerMfaCuenta(_AccionCuenta):
    @extend_schema(
        operation_id="panelRestablecerMfaCuenta",
        summary="Elimina el MFA y emite contraseña temporal; invalida sesiones",
        tags=["panel-cuentas"],
        request=None,
        responses={
            200: s.CuentaConCredencialTemporalSerializer,
            **_errores(401, 403, 404, 409, 429, 500),
        },
    )
    def post(self, request: Request, id: int) -> Response:
        resultado = services.restablecer_contrasena(
            cuenta_de(request), _id_cuenta(id), borrar_mfa=True
        )
        return Response(_con_temporal(resultado))


class DesactivarCuenta(_AccionCuenta):
    @extend_schema(
        operation_id="panelDesactivarCuenta",
        summary="Desactivar (invalida sesiones y credenciales de inmediato)",
        tags=["panel-cuentas"],
        request=None,
        responses={200: s.CuentaSerializer, **_errores(401, 403, 404, 409, 429, 500)},
    )
    def post(self, request: Request, id: int) -> Response:
        cuenta = services.desactivar_cuenta(cuenta_de(request), _id_cuenta(id))
        return Response(s.CuentaSerializer(cuenta).data)


class ReactivarCuenta(_AccionCuenta):
    @extend_schema(
        operation_id="panelReactivarCuenta",
        summary="DESACTIVADA → PENDIENTE_ACTIVACION con contraseña temporal",
        tags=["panel-cuentas"],
        request=None,
        responses={
            200: s.CuentaConCredencialTemporalSerializer,
            **_errores(401, 403, 404, 409, 429, 500),
        },
    )
    def post(self, request: Request, id: int) -> Response:
        return Response(
            _con_temporal(services.reactivar_cuenta(cuenta_de(request), _id_cuenta(id)))
        )


class AnonimizarCuenta(_AccionCuenta):
    @extend_schema(
        operation_id="panelAnonimizarCuenta",
        summary="Anonimizar ahora (solo DESACTIVADA; irreversible)",
        tags=["panel-cuentas"],
        request=None,
        responses={200: s.CuentaSerializer, **_errores(401, 403, 404, 409, 429, 500)},
    )
    def post(self, request: Request, id: int) -> Response:
        cuenta = services.anonimizar_cuenta(cuenta_de(request), _id_cuenta(id))
        return Response(s.CuentaSerializer(cuenta).data)
