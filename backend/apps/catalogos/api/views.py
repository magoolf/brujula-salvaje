"""Vistas de taxonomías del panel (contracts/openapi.yaml, tag panel-configuracion). Solo
transporte HTTP (Skill_Backend §4.1): delegan en `apps.catalogos.services`/`selectors`."""

from __future__ import annotations

from typing import Any, cast

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogos import selectors, services
from apps.catalogos.api.serializers import (
    CategoriaGuiaEntradaSerializer,
    CategoriaGuiaPanelSerializer,
    EscalasPanelSerializer,
    LicenciaEntradaSerializer,
    LicenciaSerializer,
    NivelEscalaEntradaSerializer,
    NivelEscalaPanelSerializer,
    PaginaCategoriaGuiaPanelSerializer,
    PaginaLicenciaSerializer,
    PaginaPaisSerializer,
    PaginaRegionSerializer,
    PaisEntradaSerializer,
    PaisSerializer,
    RegionEntradaSerializer,
    RegionSerializer,
)
from apps.catalogos.models import CategoriaGuia, Escala, Licencia, Pais, Region
from apps.core.exceptions import ErrorApi, NoEncontrado, ParametroInvalido
from apps.core.paginacion import PaginacionNumerada
from apps.core.parametros import validar_parametros
from apps.cuentas.permisos import SesionPanel, SoloAdministrador, cuenta_de

ID_MAXIMO = 2**63 - 1

# components.parameters.Pagina (contracts/openapi.yaml): drf-spectacular no auto-documenta los
# query params de `PaginacionNumerada` (TKT-006, ciclo oasdiff: request-parameter-removed).
PARAMETRO_PAGINA = [
    OpenApiParameter(
        "pagina",
        int,
        OpenApiParameter.QUERY,
        required=False,
        description="Número de página (base 1). Fuera de rango → 404 pagina_fuera_de_rango.",
    )
]
PARAMETROS_LISTA_PAISES = [
    OpenApiParameter("region_id", int, OpenApiParameter.QUERY, required=False),
    *PARAMETRO_PAGINA,
]


def _id(id: int) -> int:
    if not 1 <= id <= ID_MAXIMO:
        raise NoEncontrado()
    return id


class _VistaTaxonomia(APIView):
    permission_classes = [SesionPanel]
    throttle_scope = "panel-lectura"


class _VistaTaxonomiaMixta(_VistaTaxonomia):
    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        self.throttle_scope = (
            "panel-lectura" if request.method in SAFE_METHODS else "panel-escritura"
        )
        super().initial(request, *args, **kwargs)


class _VistaSoloAdministrador(_VistaTaxonomiaMixta):
    permission_classes = [SesionPanel, SoloAdministrador]


# ---------------------------------------------------------------------------
# Regiones
# ---------------------------------------------------------------------------
class ListaRegiones(_VistaTaxonomiaMixta):
    tamano_pagina = 100

    @extend_schema(
        operation_id="panelListarRegiones",
        tags=["panel-configuracion"],
        parameters=PARAMETRO_PAGINA,
        responses={200: PaginaRegionSerializer},
    )
    def get(self, request: Request) -> Response:
        validar_parametros(request.query_params, {"pagina"})
        paginador = PaginacionNumerada()
        pagina = paginador.paginate_queryset(
            Region.objects.order_by("orden", "nombre"), request, view=self
        )
        return paginador.get_paginated_response(
            cast("list[Any]", RegionSerializer(pagina, many=True).data)
        )

    @extend_schema(
        operation_id="panelCrearRegion",
        tags=["panel-configuracion"],
        request=RegionEntradaSerializer,
        responses={201: RegionSerializer},
    )
    def post(self, request: Request) -> Response:
        entrada = RegionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        region = services.crear_region(actor.pk, dict(entrada.validated_data))
        return Response(RegionSerializer(region).data, status=201)


class DetalleRegion(_VistaTaxonomiaMixta):
    @extend_schema(
        operation_id="panelObtenerRegion",
        tags=["panel-configuracion"],
        responses={200: RegionSerializer},
    )
    def get(self, request: Request, id: int) -> Response:
        region = Region.objects.filter(pk=_id(id)).first()
        if region is None:
            raise NoEncontrado()
        return Response(RegionSerializer(region).data)

    @extend_schema(
        operation_id="panelActualizarRegion",
        tags=["panel-configuracion"],
        request=RegionEntradaSerializer,
        responses={200: RegionSerializer},
    )
    def put(self, request: Request, id: int) -> Response:
        entrada = RegionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        region = services.actualizar_region(_id(id), actor.pk, dict(entrada.validated_data))
        return Response(RegionSerializer(region).data)


# ---------------------------------------------------------------------------
# Países
# ---------------------------------------------------------------------------
class ListaPaises(_VistaTaxonomiaMixta):
    tamano_pagina = 100

    @extend_schema(
        operation_id="panelListarPaises",
        tags=["panel-configuracion"],
        parameters=PARAMETROS_LISTA_PAISES,
        responses={200: PaginaPaisSerializer},
    )
    def get(self, request: Request) -> Response:
        validar_parametros(request.query_params, {"region_id", "pagina"})
        qs = Pais.objects.order_by("nombre")
        region_id = request.query_params.get("region_id")
        if region_id is not None:
            if not region_id.isdigit():
                raise ParametroInvalido(errors={"region_id": ["Debe ser un entero."]})
            qs = qs.filter(region_id=int(region_id))
        paginador = PaginacionNumerada()
        pagina = paginador.paginate_queryset(qs, request, view=self)
        return paginador.get_paginated_response(
            cast("list[Any]", PaisSerializer(pagina, many=True).data)
        )

    @extend_schema(
        operation_id="panelCrearPais",
        tags=["panel-configuracion"],
        request=PaisEntradaSerializer,
        responses={201: PaisSerializer},
    )
    def post(self, request: Request) -> Response:
        entrada = PaisEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        pais = services.crear_pais(actor.pk, dict(entrada.validated_data))
        return Response(PaisSerializer(pais).data, status=201)


class DetallePais(_VistaTaxonomiaMixta):
    @extend_schema(
        operation_id="panelObtenerPais",
        tags=["panel-configuracion"],
        responses={200: PaisSerializer},
    )
    def get(self, request: Request, id: int) -> Response:
        pais = Pais.objects.filter(pk=_id(id)).first()
        if pais is None:
            raise NoEncontrado()
        return Response(PaisSerializer(pais).data)

    @extend_schema(
        operation_id="panelActualizarPais",
        tags=["panel-configuracion"],
        request=PaisEntradaSerializer,
        responses={200: PaisSerializer},
    )
    def put(self, request: Request, id: int) -> Response:
        entrada = PaisEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        pais = services.actualizar_pais(_id(id), actor.pk, dict(entrada.validated_data))
        return Response(PaisSerializer(pais).data)


# ---------------------------------------------------------------------------
# Categorías de guía
# ---------------------------------------------------------------------------
class ListaCategoriasGuia(_VistaTaxonomiaMixta):
    tamano_pagina = 100

    @extend_schema(
        operation_id="panelListarCategoriasGuia",
        tags=["panel-configuracion"],
        parameters=PARAMETRO_PAGINA,
        responses={200: PaginaCategoriaGuiaPanelSerializer},
    )
    def get(self, request: Request) -> Response:
        validar_parametros(request.query_params, {"pagina"})
        paginador = PaginacionNumerada()
        pagina = paginador.paginate_queryset(
            CategoriaGuia.objects.order_by("orden", "nombre"), request, view=self
        )
        return paginador.get_paginated_response(
            cast("list[Any]", CategoriaGuiaPanelSerializer(pagina, many=True).data)
        )

    @extend_schema(
        operation_id="panelCrearCategoriaGuia",
        tags=["panel-configuracion"],
        request=CategoriaGuiaEntradaSerializer,
        responses={201: CategoriaGuiaPanelSerializer},
    )
    def post(self, request: Request) -> Response:
        entrada = CategoriaGuiaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        categoria = services.crear_categoria(actor.pk, dict(entrada.validated_data))
        return Response(CategoriaGuiaPanelSerializer(categoria).data, status=201)


class DetalleCategoriaGuia(_VistaTaxonomiaMixta):
    @extend_schema(
        operation_id="panelObtenerCategoriaGuia",
        tags=["panel-configuracion"],
        responses={200: CategoriaGuiaPanelSerializer},
    )
    def get(self, request: Request, id: int) -> Response:
        categoria = CategoriaGuia.objects.filter(pk=_id(id)).first()
        if categoria is None:
            raise NoEncontrado()
        return Response(CategoriaGuiaPanelSerializer(categoria).data)

    @extend_schema(
        operation_id="panelActualizarCategoriaGuia",
        tags=["panel-configuracion"],
        request=CategoriaGuiaEntradaSerializer,
        responses={200: CategoriaGuiaPanelSerializer},
    )
    def put(self, request: Request, id: int) -> Response:
        entrada = CategoriaGuiaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        categoria = services.actualizar_categoria(_id(id), actor.pk, dict(entrada.validated_data))
        return Response(CategoriaGuiaPanelSerializer(categoria).data)


# ---------------------------------------------------------------------------
# Licencias (alta/edición solo Administrador; lectura para EDITOR y ADMINISTRADOR)
# ---------------------------------------------------------------------------
class ListaLicencias(_VistaTaxonomiaMixta):
    tamano_pagina = 100

    @extend_schema(
        operation_id="panelListarLicencias",
        tags=["panel-configuracion"],
        parameters=PARAMETRO_PAGINA,
        responses={200: PaginaLicenciaSerializer},
    )
    def get(self, request: Request) -> Response:
        validar_parametros(request.query_params, {"pagina"})
        paginador = PaginacionNumerada()
        pagina = paginador.paginate_queryset(
            Licencia.objects.order_by("nombre"), request, view=self
        )
        return paginador.get_paginated_response(
            cast("list[Any]", LicenciaSerializer(pagina, many=True).data)
        )

    @extend_schema(
        operation_id="panelCrearLicencia",
        tags=["panel-configuracion"],
        request=LicenciaEntradaSerializer,
        responses={201: LicenciaSerializer},
    )
    def post(self, request: Request) -> Response:
        if not cuenta_de(request).es_administrador:
            raise ErrorApi(codigo="permiso_denegado")
        entrada = LicenciaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        licencia = services.crear_licencia(actor.pk, dict(entrada.validated_data))
        return Response(LicenciaSerializer(licencia).data, status=201)


class DetalleLicencia(_VistaTaxonomiaMixta):
    @extend_schema(
        operation_id="panelObtenerLicencia",
        tags=["panel-configuracion"],
        responses={200: LicenciaSerializer},
    )
    def get(self, request: Request, id: int) -> Response:
        licencia = Licencia.objects.filter(pk=_id(id)).first()
        if licencia is None:
            raise NoEncontrado()
        return Response(LicenciaSerializer(licencia).data)

    @extend_schema(
        operation_id="panelActualizarLicencia",
        tags=["panel-configuracion"],
        request=LicenciaEntradaSerializer,
        responses={200: LicenciaSerializer},
    )
    def put(self, request: Request, id: int) -> Response:
        if not cuenta_de(request).es_administrador:
            raise ErrorApi(codigo="permiso_denegado")
        entrada = LicenciaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        licencia = services.actualizar_licencia(_id(id), actor.pk, dict(entrada.validated_data))
        return Response(LicenciaSerializer(licencia).data)


# ---------------------------------------------------------------------------
# Escalas (lectura para EDITOR y ADMINISTRADOR; edición solo Administrador)
# ---------------------------------------------------------------------------
class Escalas(_VistaTaxonomia):
    @extend_schema(
        operation_id="panelObtenerEscalas",
        tags=["panel-configuracion"],
        responses={200: EscalasPanelSerializer},
    )
    def get(self, request: Request) -> Response:
        niveles = selectors.todos_los_niveles()
        cuerpo = {
            "dificultad": [n for n in niveles if n.escala == Escala.DIFICULTAD],
            "presupuesto": [n for n in niveles if n.escala == Escala.PRESUPUESTO],
        }
        return Response(EscalasPanelSerializer(cuerpo).data)


class ActualizarNivelEscala(_VistaSoloAdministrador):
    @extend_schema(
        operation_id="panelActualizarNivelEscala",
        tags=["panel-configuracion"],
        request=NivelEscalaEntradaSerializer,
        responses={200: NivelEscalaPanelSerializer},
    )
    def put(self, request: Request, id: int) -> Response:
        entrada = NivelEscalaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        nivel = services.actualizar_nivel_escala(_id(id), actor.pk, dict(entrada.validated_data))
        return Response(NivelEscalaPanelSerializer(nivel).data)
