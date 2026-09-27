"""Vistas de la API pública de solo lectura /api/v1/publico/** (MOD-001..008).

Las vistas solo validan parámetros, delegan en los selectors y serializan (Skill_Backend
Regla 01/03). Toda operación está en contracts/openapi.yaml con su operationId.
"""

from __future__ import annotations

from typing import Any, cast

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from apps.busqueda import selectors as busqueda
from apps.catalogos import selectors as catalogos
from apps.catalogos.models import Escala
from apps.contenido import selectors
from apps.contenido.api import serializers as s
from apps.contenido.api.base import (
    CACHE_NO_STORE,
    PARAMETRO_PAGINA,
    VistaPublica,
    respuestas,
)
from apps.contenido.api.filtros import (
    SLUG_SCHEMA,
    FiltroBusquedaSerializer,
    FiltroDestinosSerializer,
    FiltroGuiasSerializer,
    FiltroItinerariosSerializer,
    validar,
)
from apps.contenido.models import Contenido, EstadoEditorial, TipoContenido
from apps.core.exceptions import ErrorApi, NoEncontrado
from apps.core.paginacion import PaginacionNumerada
from apps.inicio import selectors as inicio
from apps.inicio.models import SeccionInicio

T = TipoContenido
PAGINA = ("pagina",)


def _pagina(vista: VistaPublica, request: Request, datos: Any, serializer: type[Any]) -> Response:
    paginador = PaginacionNumerada()
    pagina = paginador.paginate_queryset(datos, request, view=vista)
    contexto = {"marca": getattr(vista, "marca", "")}
    return paginador.get_paginated_response(
        cast("list[Any]", serializer(pagina, many=True, context=contexto).data)
    )


def _contexto() -> dict[str, Any]:
    return {"marca": inicio.nombre_marca()}


def resolver_publicado(tipo: str, slug: str) -> Contenido:
    """404 si no existe o es un borrador; 410 con alternativas si está retirado (DEC-AUTO-113)."""
    contenido = selectors.contenido_por_slug(tipo, slug)
    if contenido is None or contenido.estado_editorial == EstadoEditorial.BORRADOR:
        raise NoEncontrado()
    if contenido.estado_editorial == EstadoEditorial.RETIRADO:
        alternativas = selectors.relacionados(contenido)
        raise ErrorApi(
            codigo="retirado",
            extra={
                "alternativas": s.ContenidoRelacionadoSerializer(alternativas, many=True).data,
                "listado_padre": selectors.LISTADO_PADRE[T(tipo)],
            },
        )
    return contenido


def _slug_path() -> OpenApiParameter:
    return OpenApiParameter("slug", SLUG_SCHEMA, OpenApiParameter.PATH)


# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
class Inicio(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerInicio",
        summary="Datos del inicio (destacados con relleno automático)",
        tags=["publico-general"],
        auth=[],
        responses=respuestas(s.InicioSerializer),
    )
    def get(self, request: Request) -> Response:
        datos = selectors.inicio(
            {
                "destinos": inicio.ids_destacados(SeccionInicio.DESTINOS),
                "itinerarios": inicio.ids_destacados(SeccionInicio.ITINERARIOS),
                "guias": inicio.ids_destacados(SeccionInicio.GUIAS),
            }
        )
        datos["hero"] = inicio.hero()
        return Response(s.InicioSerializer(datos).data)


class Configuracion(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerConfiguracion",
        summary="Marca, lema, descargo y datos del Responsable del tratamiento",
        tags=["publico-general"],
        auth=[],
        responses=respuestas(s.ConfiguracionPublicaSerializer),
    )
    def get(self, request: Request) -> Response:
        config = inicio.config_sitio()
        campos = ("nombre", "identificacion", "domicilio", "canal_atencion")
        responsable = {c: getattr(config, f"responsable_{c}") for c in campos}
        responsable["definido"] = all(responsable[c] for c in campos)
        datos = {
            "nombre_marca": config.nombre_marca,
            "lema": config.lema,
            "texto_descargo": config.texto_descargo,
            "responsable": responsable,
        }
        return Response(s.ConfiguracionPublicaSerializer(datos).data)


class Escalas(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerEscalas",
        summary="Escalas de dificultad (1-5) y presupuesto (1-4)",
        tags=["publico-general"],
        auth=[],
        responses=respuestas(s.EscalasSerializer),
    )
    def get(self, request: Request) -> Response:
        datos = {
            "dificultad": catalogos.niveles(Escala.DIFICULTAD),
            "presupuesto": catalogos.niveles(Escala.PRESUPUESTO),
        }
        return Response(s.EscalasSerializer(datos).data)


class Meses(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerMeses",
        summary="Doce meses con número de destinos y un destacado por mes",
        tags=["publico-general"],
        auth=[],
        responses=respuestas(s.MesesSerializer),
    )
    def get(self, request: Request) -> Response:
        return Response(s.MesesSerializer({"meses": selectors.meses()}).data)


class Indice(VistaPublica):
    parametros = PAGINA
    tamano_pagina = 1000

    @extend_schema(
        operation_id="publicoListarIndice",
        summary="Todas las páginas publicadas (mapa del sitio HTML y sitemap.xml)",
        tags=["publico-general"],
        auth=[],
        parameters=[PARAMETRO_PAGINA],
        responses=respuestas(s.PaginaEntradaIndiceSerializer, con_404=True),
    )
    def get(self, request: Request) -> Response:
        return _pagina(self, request, selectors.indice(), s.EntradaIndiceSerializer)


class PaginaInstitucional(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerPaginaInstitucional",
        summary="Página institucional (Acerca de / Metodología y páginas legales)",
        tags=["publico-general"],
        auth=[],
        parameters=[OpenApiParameter("slug", str, OpenApiParameter.PATH, enum=s.SLUGS_PAGINA)],
        responses=respuestas(s.PaginaInstitucionalPublicaSerializer, con_404=True),
    )
    def get(self, request: Request, slug: str) -> Response:
        clave = selectors.CLAVE_PAGINA.get(slug)
        pagina = selectors.pagina_institucional(clave) if clave is not None else None
        if pagina is None:
            raise NoEncontrado()
        vars(pagina)["slug_publico"] = slug
        return Response(s.PaginaInstitucionalPublicaSerializer(pagina, context=_contexto()).data)


# ---------------------------------------------------------------------------
# Destinos
# ---------------------------------------------------------------------------
class FacetasDestinos(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerFacetasDestinos",
        summary="Opciones de los filtros de destinos (solo valores con contenido publicado)",
        tags=["publico-destinos"],
        auth=[],
        responses=respuestas(s.FacetasDestinosSerializer),
    )
    def get(self, request: Request) -> Response:
        facetas = selectors.facetas_destinos(
            catalogos.regiones_con_paises, catalogos.todos_los_niveles()
        )
        return Response(s.FacetasDestinosSerializer(facetas).data)


class ListaDestinos(VistaPublica):
    parametros = (*FiltroDestinosSerializer.PARAMETROS, "pagina")
    multiples = FiltroDestinosSerializer.MULTIPLES
    tamano_pagina = 24

    @extend_schema(
        operation_id="publicoListarDestinos",
        summary="Listar y filtrar destinos publicados (24 por página)",
        tags=["publico-destinos"],
        auth=[],
        parameters=[*FiltroDestinosSerializer.documentacion(), PARAMETRO_PAGINA],
        responses=respuestas(s.PaginaDestinoTarjetaSerializer, con_404=True),
    )
    def get(self, request: Request) -> Response:
        filtros = validar(FiltroDestinosSerializer, request)
        return _pagina(
            self, request, selectors.listar_destinos(filtros), s.DestinoTarjetaSerializer
        )


class MapaDestinos(VistaPublica):
    parametros = PAGINA
    tamano_pagina = 500

    @extend_schema(
        operation_id="publicoListarDestinosMapa",
        summary="Lista ligera de destinos con coordenadas (mapa y lista alternativa)",
        tags=["publico-destinos"],
        auth=[],
        parameters=[PARAMETRO_PAGINA],
        responses=respuestas(s.PaginaDestinoMapaSerializer, con_404=True),
    )
    def get(self, request: Request) -> Response:
        return _pagina(self, request, selectors.destinos_mapa(), s.DestinoMapaItemSerializer)


class DestinoAleatorio(VistaPublica):
    throttle_scope = "publico-aleatorio"
    cache_control = CACHE_NO_STORE

    @extend_schema(
        operation_id="publicoObtenerDestinoAleatorio",
        summary="Sorpréndeme (un destino publicado al azar)",
        tags=["publico-destinos"],
        auth=[],
        responses=respuestas(s.DestinoAleatorioSerializer, con_404=True),
    )
    def get(self, request: Request) -> Response:
        slug = selectors.slug_destino_aleatorio()
        if slug is None:
            raise NoEncontrado()
        return Response(s.DestinoAleatorioSerializer({"slug": slug}).data)


class DetalleDestino(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerDestino",
        summary="Ficha de destino por slug",
        tags=["publico-destinos"],
        auth=[],
        parameters=[_slug_path()],
        responses=respuestas(s.DestinoDetalleSerializer, con_404=True, con_410=True),
    )
    def get(self, request: Request, slug: str) -> Response:
        contenido = resolver_publicado(T.DESTINO, slug)
        destino = selectors.ficha_destino(contenido)
        return Response(s.DestinoDetalleSerializer(destino, context=_contexto()).data)


# ---------------------------------------------------------------------------
# Itinerarios, tipos, guías y colecciones
# ---------------------------------------------------------------------------
class ListaItinerarios(VistaPublica):
    parametros = (*FiltroItinerariosSerializer.PARAMETROS, "pagina")
    tamano_pagina = 24

    @extend_schema(
        operation_id="publicoListarItinerarios",
        summary="Listar itinerarios publicados (24 por página)",
        tags=["publico-itinerarios"],
        auth=[],
        parameters=[*FiltroItinerariosSerializer.documentacion(), PARAMETRO_PAGINA],
        responses=respuestas(s.PaginaItinerarioTarjetaSerializer, con_404=True),
    )
    def get(self, request: Request) -> Response:
        filtros = validar(FiltroItinerariosSerializer, request)
        itinerarios = selectors.listar_itinerarios(filtros.get("destino"), filtros["orden"])
        return _pagina(self, request, itinerarios, s.ItinerarioTarjetaSerializer)


class DetalleItinerario(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerItinerario",
        summary="Detalle de itinerario día a día",
        tags=["publico-itinerarios"],
        auth=[],
        parameters=[_slug_path()],
        responses=respuestas(s.ItinerarioDetalleSerializer, con_404=True, con_410=True),
    )
    def get(self, request: Request, slug: str) -> Response:
        contenido = resolver_publicado(T.ITINERARIO, slug)
        itinerario = selectors.ficha_itinerario(contenido)
        if itinerario is None:
            raise NoEncontrado()
        return Response(s.ItinerarioDetalleSerializer(itinerario, context=_contexto()).data)


class ListaTipos(VistaPublica):
    parametros = PAGINA
    tamano_pagina = 100

    @extend_schema(
        operation_id="publicoListarTiposAventura",
        summary="Índice de tipos de aventura publicados",
        tags=["publico-tipos"],
        auth=[],
        parameters=[PARAMETRO_PAGINA],
        responses=respuestas(s.PaginaTipoAventuraTarjetaSerializer, con_404=True),
    )
    def get(self, request: Request) -> Response:
        return _pagina(self, request, selectors.listar_tipos(), s.TipoAventuraTarjetaSerializer)


class DetalleTipo(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerTipoAventura",
        summary="Detalle de tipo de aventura con checklist",
        tags=["publico-tipos"],
        auth=[],
        parameters=[_slug_path()],
        responses=respuestas(s.TipoAventuraDetalleSerializer, con_404=True, con_410=True),
    )
    def get(self, request: Request, slug: str) -> Response:
        contenido = resolver_publicado(T.TIPO, slug)
        tipo = selectors.ficha_tipo(contenido)
        return Response(s.TipoAventuraDetalleSerializer(tipo, context=_contexto()).data)


class ListaCategoriasGuia(VistaPublica):
    parametros = PAGINA
    tamano_pagina = 100

    @extend_schema(
        operation_id="publicoListarCategoriasGuia",
        summary="Categorías con al menos una guía publicada y sus guías más recientes (hasta 4)",
        tags=["publico-guias"],
        auth=[],
        parameters=[PARAMETRO_PAGINA],
        responses=respuestas(s.PaginaCategoriaGuiaIndiceSerializer, con_404=True),
    )
    def get(self, request: Request) -> Response:
        categorias = selectors.categorias_con_guias()
        return _pagina(self, request, categorias, s.CategoriaGuiaIndiceSerializer)


class DetalleCategoriaGuia(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerCategoriaGuia",
        summary="Datos de una categoría (sus guías con GET /guias?categoria=)",
        tags=["publico-guias"],
        auth=[],
        parameters=[_slug_path()],
        responses=respuestas(s.CategoriaGuiaPublicaSerializer, con_404=True),
    )
    def get(self, request: Request, slug: str) -> Response:
        categoria = selectors.categoria_con_guias(slug)
        if categoria is None:
            raise NoEncontrado()
        return Response(s.CategoriaGuiaPublicaSerializer(categoria).data)


class ListaGuias(VistaPublica):
    parametros = (*FiltroGuiasSerializer.PARAMETROS, "pagina")
    tamano_pagina = 24

    @extend_schema(
        operation_id="publicoListarGuias",
        summary="Guías publicadas por fecha de revisión descendente (24 por página)",
        tags=["publico-guias"],
        auth=[],
        parameters=[*FiltroGuiasSerializer.documentacion(), PARAMETRO_PAGINA],
        responses=respuestas(s.PaginaGuiaTarjetaSerializer, con_404=True),
    )
    def get(self, request: Request) -> Response:
        filtros = validar(FiltroGuiasSerializer, request)
        guias = selectors.listar_guias(filtros.get("categoria"))
        return _pagina(self, request, guias, s.GuiaTarjetaSerializer)


class DetalleGuia(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerGuia",
        summary="Detalle de guía",
        tags=["publico-guias"],
        auth=[],
        parameters=[_slug_path()],
        responses=respuestas(s.GuiaDetalleSerializer, con_404=True, con_410=True),
    )
    def get(self, request: Request, slug: str) -> Response:
        contenido = resolver_publicado(T.GUIA, slug)
        guia = selectors.ficha_guia(contenido)
        return Response(s.GuiaDetalleSerializer(guia, context=_contexto()).data)


class ListaColecciones(VistaPublica):
    parametros = PAGINA
    tamano_pagina = 100

    @extend_schema(
        operation_id="publicoListarColecciones",
        summary="Índice de colecciones publicadas",
        tags=["publico-colecciones"],
        auth=[],
        parameters=[PARAMETRO_PAGINA],
        responses=respuestas(s.PaginaColeccionTarjetaSerializer, con_404=True),
    )
    def get(self, request: Request) -> Response:
        colecciones = selectors.listar_colecciones()
        return _pagina(self, request, colecciones, s.ColeccionTarjetaSerializer)


class DetalleColeccion(VistaPublica):
    @extend_schema(
        operation_id="publicoObtenerColeccion",
        summary="Detalle de colección (solo elementos publicados, RULE-024)",
        tags=["publico-colecciones"],
        auth=[],
        parameters=[_slug_path()],
        responses=respuestas(s.ColeccionDetalleSerializer, con_404=True, con_410=True),
    )
    def get(self, request: Request, slug: str) -> Response:
        contenido = resolver_publicado(T.COLECCION, slug)
        coleccion = selectors.ficha_coleccion(contenido)
        return Response(s.ColeccionDetalleSerializer(coleccion, context=_contexto()).data)


# ---------------------------------------------------------------------------
# Búsqueda (FEAT-016, AP-10, DEC-AUTO-048): el texto buscado nunca se registra (THREAT-020)
# ---------------------------------------------------------------------------
class Busqueda(VistaPublica):
    throttle_scope = "publico-busqueda"
    cache_control = CACHE_NO_STORE
    parametros = ("q",)

    @extend_schema(
        operation_id="publicoBuscar",
        summary="Búsqueda agrupada por tipo (hasta 10 por grupo)",
        tags=["publico-busqueda"],
        auth=[],
        parameters=[FiltroBusquedaSerializer.documentacion_q()],
        responses=respuestas(s.BusquedaAgrupadaSerializer),
    )
    def get(self, request: Request) -> Response:
        texto = validar(FiltroBusquedaSerializer, request)["q"]
        resultado = busqueda.buscar_agrupado(texto)
        return Response(s.BusquedaAgrupadaSerializer(resultado).data)


class BusquedaPorGrupo(VistaPublica):
    throttle_scope = "publico-busqueda"
    cache_control = CACHE_NO_STORE
    parametros = ("q", "pagina")
    tamano_pagina = 24

    @extend_schema(
        operation_id="publicoBuscarPorGrupo",
        summary='Todos los resultados de un grupo ("Ver todos", 24 por página)',
        tags=["publico-busqueda"],
        auth=[],
        parameters=[
            OpenApiParameter("grupo", str, OpenApiParameter.PATH, enum=list(busqueda.GRUPOS)),
            FiltroBusquedaSerializer.documentacion_q(),
            PARAMETRO_PAGINA,
        ],
        responses=respuestas(s.PaginaResultadoBusquedaSerializer, con_404=True),
    )
    def get(self, request: Request, grupo: str) -> Response:
        if grupo not in busqueda.GRUPOS:
            raise NoEncontrado()
        texto = validar(FiltroBusquedaSerializer, request)["q"]
        paginador = PaginacionNumerada()
        ids = busqueda.buscar_ids_grupo(texto, busqueda.GRUPOS[grupo])
        pagina = paginador.paginate_queryset(ids, request, view=self)
        resultados = busqueda.resultados_por_ids(pagina)
        return paginador.get_paginated_response(
            cast("list[Any]", s.ResultadoBusquedaSerializer(resultados, many=True).data)
        )


# ---------------------------------------------------------------------------
# Glosario y créditos
# ---------------------------------------------------------------------------
class Glosario(VistaPublica):
    parametros = PAGINA
    tamano_pagina = 100

    @extend_schema(
        operation_id="publicoListarGlosario",
        summary="Términos publicados en orden alfabético español",
        tags=["publico-glosario-creditos"],
        auth=[],
        parameters=[PARAMETRO_PAGINA],
        responses=respuestas(s.PaginaTerminoGlosarioPublicoSerializer, con_404=True),
    )
    def get(self, request: Request) -> Response:
        return _pagina(self, request, selectors.glosario(), s.TerminoGlosarioPublicoSerializer)


class Creditos(VistaPublica):
    parametros = PAGINA
    tamano_pagina = 24

    @extend_schema(
        operation_id="publicoListarCreditos",
        summary="Créditos de los medios usados en contenido publicado",
        tags=["publico-glosario-creditos"],
        auth=[],
        parameters=[PARAMETRO_PAGINA],
        responses=respuestas(s.PaginaCreditoMedioSerializer, con_404=True),
    )
    def get(self, request: Request) -> Response:
        hero_id = inicio.hero_medio_id()
        paginador = PaginacionNumerada()
        medios = paginador.paginate_queryset(
            selectors.ids_medios_en_uso(hero_id), request, view=self
        )
        creditos = selectors.creditos(medios)
        return paginador.get_paginated_response(
            cast("list[Any]", s.CreditoMedioSerializer(creditos, many=True).data)
        )
