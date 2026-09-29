"""Vistas del panel de medios (contracts/openapi.yaml, tag `panel-medios`). Solo transporte HTTP
(Skill_Backend §4.1): delegan en `apps.medios.services`/`selectors_panel`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from django.conf import settings
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import idempotencia
from apps.core.exceptions import NoEncontrado, ParametroInvalido
from apps.core.paginacion import PaginacionNumerada
from apps.core.parametros import validar_parametros
from apps.core.throttling import ip_cliente
from apps.cuentas.permisos import SesionPanel, cuenta_de
from apps.medios import selectors_panel, services
from apps.medios.api.serializers import (
    MedioCatalogacionEntradaSerializer,
    MedioPanelSerializer,
    ResultadoSubidaSerializer,
    UsoMedioSerializer,
)
from apps.medios.models import EstadoMedio, FormatoDerivado, MedioDerivado

ID_MAXIMO = 2**63 - 1
CONTENT_TYPE_POR_FORMATO = {"AVIF": "image/avif", "WEBP": "image/webp", "JPEG": "image/jpeg"}
MAXIMO_ARCHIVOS = 10


def _id(id: int) -> int:
    if not 1 <= id <= ID_MAXIMO:
        raise NoEncontrado()
    return id


def _ip(request: Request) -> str | None:
    return ip_cliente(request.META)


class _VistaMedios(APIView):
    permission_classes = [SesionPanel]
    throttle_scope = "panel-lectura"


class _VistaMediosMixta(_VistaMedios):
    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        self.throttle_scope = (
            "panel-lectura" if request.method in SAFE_METHODS else "panel-escritura"
        )
        super().initial(request, *args, **kwargs)


class ListaMedios(_VistaMediosMixta):
    tamano_pagina = 48
    throttle_scope_subida = "panel-subida"

    @extend_schema(
        operation_id="panelListarMedios",
        tags=["panel-medios"],
        responses={200: OpenApiResponse(description="Página de medios.")},
    )
    def get(self, request: Request) -> Response:
        validar_parametros(request.query_params, {"estado", "licencia", "en_uso", "q", "pagina"})
        estado = request.query_params.get("estado")
        if estado and estado not in EstadoMedio.values:
            raise ParametroInvalido(errors={"estado": ["Valor no admitido."]})
        en_uso_raw = request.query_params.get("en_uso")
        en_uso = {"true": True, "false": False}.get(en_uso_raw) if en_uso_raw is not None else None
        if en_uso_raw is not None and en_uso is None:
            raise ParametroInvalido(errors={"en_uso": ["Debe ser true o false."]})
        qs = selectors_panel.listar_panel(
            estado=estado,
            licencia=request.query_params.get("licencia"),
            en_uso=en_uso,
            texto=request.query_params.get("q"),
        )
        paginador = PaginacionNumerada()
        pagina = paginador.paginate_queryset(qs, request, view=self)
        return paginador.get_paginated_response(
            cast("list[Any]", MedioPanelSerializer(pagina, many=True).data)
        )

    @extend_schema(
        operation_id="panelSubirMedios",
        tags=["panel-medios"],
        request={"multipart/form-data": OpenApiTypes.BINARY},
        responses={200: ResultadoSubidaSerializer},
    )
    def post(self, request: Request) -> Response:
        self.throttle_scope = self.throttle_scope_subida
        archivos = request.FILES.getlist("archivos")
        if not archivos or len(archivos) > MAXIMO_ARCHIVOS:
            raise ParametroInvalido(errors={"archivos": ["Sube entre 1 y 10 archivos."]})
        actor = cuenta_de(request)

        def efecto() -> idempotencia.Resultado:
            resultados = services.subir_medios(actor.pk, archivos)
            cuerpo = ResultadoSubidaSerializer({"resultados": resultados}).data
            return idempotencia.Resultado(codigo_http=status.HTTP_200_OK, cuerpo=cuerpo)

        resultado = idempotencia.ejecutar(
            cuenta_id=actor.pk,
            clave=idempotencia.leer_clave(request.headers.get(idempotencia.CABECERA)),
            operacion="panelSubirMedios",
            huella=idempotencia.huella_peticion(
                "panelSubirMedios", {}, sorted(f.name or "" for f in archivos)
            ),
            efecto=efecto,
        )
        return Response(resultado.cuerpo, status=resultado.codigo_http)


class DetalleMedio(_VistaMediosMixta):
    @extend_schema(
        operation_id="panelObtenerMedio",
        tags=["panel-medios"],
        responses={200: MedioPanelSerializer},
    )
    def get(self, request: Request, id: int) -> Response:
        medio = services.obtener(_id(id))
        return Response(MedioPanelSerializer(medio).data)

    @extend_schema(
        operation_id="panelCatalogarMedio",
        tags=["panel-medios"],
        request=MedioCatalogacionEntradaSerializer,
        responses={200: MedioPanelSerializer},
    )
    def put(self, request: Request, id: int) -> Response:
        entrada = MedioCatalogacionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        medio = services.catalogar(_id(id), actor.pk, dict(entrada.validated_data))
        return Response(MedioPanelSerializer(medio).data)


class ArchivoMedio(_VistaMedios):
    @extend_schema(
        operation_id="panelObtenerArchivoMedio",
        tags=["panel-medios"],
        responses={200: OpenApiTypes.BINARY},
    )
    def get(self, request: Request, id: int) -> HttpResponse:
        validar_parametros(request.query_params, {"ancho", "formato"})
        ancho = request.query_params.get("ancho")
        formato = request.query_params.get("formato")
        if not ancho or not ancho.isdigit() or formato not in FormatoDerivado.values:
            raise ParametroInvalido(errors={"ancho": ["Parámetros inválidos."]})
        derivado = MedioDerivado.objects.filter(
            medio_id=_id(id), ancho_px=int(ancho), formato=formato
        ).first()
        if derivado is None:
            raise NoEncontrado()
        ruta = Path(settings.MEDIA_ROOT) / derivado.ruta
        contenido = ruta.read_bytes()
        respuesta = HttpResponse(contenido, content_type=CONTENT_TYPE_POR_FORMATO[formato])
        respuesta["X-Content-Type-Options"] = "nosniff"
        respuesta["Cache-Control"] = "no-store"
        return respuesta


class UsosMedio(_VistaMedios):
    tamano_pagina = 50

    @extend_schema(
        operation_id="panelListarUsosMedio",
        tags=["panel-medios"],
        responses={200: OpenApiResponse(description="Página de usos.")},
    )
    def get(self, request: Request, id: int) -> Response:
        validar_parametros(request.query_params, {"pagina"})
        services.obtener(_id(id))
        filas = services.usos(_id(id))
        paginador = PaginacionNumerada()
        pagina = paginador.paginate_queryset(filas, request, view=self)
        return paginador.get_paginated_response(
            cast("list[Any]", UsoMedioSerializer(pagina, many=True).data)
        )


class RetirarMedio(_VistaMedios):
    throttle_scope = "panel-escritura"

    @extend_schema(
        operation_id="panelRetirarMedio",
        tags=["panel-medios"],
        request=None,
        responses={200: MedioPanelSerializer},
    )
    def post(self, request: Request, id: int) -> Response:
        actor = cuenta_de(request)
        medio = services.retirar(_id(id), actor.pk)
        return Response(MedioPanelSerializer(medio).data)


class ReactivarMedio(_VistaMedios):
    throttle_scope = "panel-escritura"

    @extend_schema(
        operation_id="panelReactivarMedio",
        tags=["panel-medios"],
        request=None,
        responses={200: MedioPanelSerializer},
    )
    def post(self, request: Request, id: int) -> Response:
        actor = cuenta_de(request)
        medio = services.reactivar(_id(id), actor.pk)
        return Response(MedioPanelSerializer(medio).data)
