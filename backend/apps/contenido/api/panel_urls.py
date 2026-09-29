"""Rutas /api/v1/panel/contenidos/** (contracts/openapi.yaml, tags panel-contenidos y
panel-ciclo-editorial). Se incluyen desde `config.urls` (TKT-006)."""

from __future__ import annotations

from typing import Any

from django.urls import path, register_converter
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema

from apps.contenido.api import panel_serializers as s
from apps.contenido.api import panel_views as v
from apps.contenido.models import TipoContenido

T = TipoContenido

# components.parameters.{EstadoEditorialFiltro,TextoFiltro,Pagina} (contracts/openapi.yaml):
# duplicados aquí como OpenApiParameter porque drf-spectacular no auto-documenta los query
# params de `PaginacionNumerada` (no implementa `get_schema_operation_parameters`) ni los que
# `validar_parametros()` valida en runtime (TKT-006, ciclo oasdiff: request-parameter-removed).
PARAMETROS_LISTADO = [
    OpenApiParameter(
        "estado",
        str,
        OpenApiParameter.QUERY,
        required=False,
        enum=["BORRADOR", "PUBLICADO", "RETIRADO"],
    ),
    OpenApiParameter(
        "q",
        str,
        OpenApiParameter.QUERY,
        required=False,
        description="Filtro de texto del panel (título, alt, crédito según el recurso).",
    ),
    OpenApiParameter(
        "pagina",
        int,
        OpenApiParameter.QUERY,
        required=False,
        description="Número de página (base 1). Fuera de rango → 404 pagina_fuera_de_rango.",
    ),
]
PARAMETRO_PAGINA = [PARAMETROS_LISTADO[2]]
# components.parameters.IdempotencyKey / VersionQuery (contracts/openapi.yaml).
PARAMETRO_IDEMPOTENCY_KEY = [
    OpenApiParameter(
        "Idempotency-Key",
        str,
        OpenApiParameter.HEADER,
        required=False,
        description=(
            "UUID opcional (DEC-AUTO-107, CHG-API-001): repetir la misma clave devuelve la "
            "misma respuesta 2xx confirmada (24 h)."
        ),
    )
]
PARAMETRO_VERSION_QUERY = [
    OpenApiParameter(
        "version",
        int,
        OpenApiParameter.QUERY,
        required=True,
        description="Versión conocida por el cliente (bloqueo optimista, DEC-AUTO-050).",
    )
]


class TipoContenidoRuta:
    """components.schemas.TipoContenidoRuta: solo los 7 segmentos válidos."""

    regex = "destinos|itinerarios|guias|tipos-aventura|colecciones|glosario|paginas"

    def to_python(self, valor: str) -> str:
        return valor

    def to_url(self, valor: str) -> str:
        return valor


register_converter(TipoContenidoRuta, "tiporuta")

app_name = "panel_contenido"


def _lista(tipo: str, nombre: str) -> type[v.ListaContenidoPorTipo]:
    # `extend_schema` etiqueta la función in situ (no crea una copia): heredar el método del
    # padre sin envolverlo en una función propia haría que todas las subclases compartan el
    # mismo objeto función y la última llamada sobrescribiría el operation_id de las demás.
    def get(self: v.ListaContenidoPorTipo, request: Any) -> Any:
        return v.ListaContenidoPorTipo.get(self, request)

    def post(self: v.ListaContenidoPorTipo, request: Any) -> Any:
        return v.ListaContenidoPorTipo.post(self, request)

    get = extend_schema(
        operation_id=v.OPERACION_LISTAR[tipo],
        tags=["panel-contenidos"],
        parameters=PARAMETROS_LISTADO,
        responses={200: s.PaginaContenidoResumenSerializer},
    )(get)
    post = extend_schema(
        operation_id=v.OPERACION_CREAR[tipo],
        tags=["panel-contenidos"],
        parameters=PARAMETRO_IDEMPOTENCY_KEY,
        request=s.ENTRADA_SERIALIZER[tipo],
        responses={201: s.PANEL_SERIALIZER[tipo]},
    )(post)
    return type(nombre, (v.ListaContenidoPorTipo,), {"tipo": tipo, "get": get, "post": post})


def _detalle(tipo: str, nombre: str) -> type[v.DetalleContenidoPorTipo]:
    def get(self: v.DetalleContenidoPorTipo, request: Any, id: int) -> Any:
        return v.DetalleContenidoPorTipo.get(self, request, id)

    def put(self: v.DetalleContenidoPorTipo, request: Any, id: int) -> Any:
        return v.DetalleContenidoPorTipo.put(self, request, id)

    def delete(self: v.DetalleContenidoPorTipo, request: Any, id: int) -> Any:
        return v.DetalleContenidoPorTipo.delete(self, request, id)

    get = extend_schema(
        operation_id=v.OPERACION_OBTENER[tipo],
        tags=["panel-contenidos"],
        responses={200: s.PANEL_SERIALIZER[tipo]},
    )(get)
    put = extend_schema(
        operation_id=v.OPERACION_ACTUALIZAR[tipo],
        tags=["panel-contenidos"],
        request=s.ACTUALIZACION_SERIALIZER[tipo],
        responses={200: s.PANEL_SERIALIZER[tipo]},
    )(put)
    delete = extend_schema(
        operation_id=v.OPERACION_ELIMINAR[tipo],
        tags=["panel-contenidos"],
        parameters=PARAMETRO_VERSION_QUERY,
        request=None,
        responses={204: OpenApiResponse(description="Borrador eliminado.")},
    )(delete)
    return type(
        nombre,
        (v.DetalleContenidoPorTipo,),
        {"tipo": tipo, "get": get, "put": put, "delete": delete},
    )


def _vista_previa(tipo: str, nombre: str) -> type[v.VistaPreviaContenido]:
    def post(self: v.VistaPreviaContenido, request: Any) -> Any:
        return v.VistaPreviaContenido.post(self, request)

    post = extend_schema(
        operation_id=v.OPERACION_VISTA_PREVIA[tipo],
        tags=["panel-contenidos"],
        request=s.VISTA_PREVIA_SERIALIZER[tipo],
        responses={200: s.VistaPreviaSerializer},
    )(post)
    return type(nombre, (v.VistaPreviaContenido,), {"tipo": tipo, "post": post})


_RUTAS = (
    ("destinos", T.DESTINO),
    ("itinerarios", T.ITINERARIO),
    ("guias", T.GUIA),
    ("tipos-aventura", T.TIPO),
    ("colecciones", T.COLECCION),
    ("glosario", T.TERMINO),
)
# El glosario no tiene vista previa en el contrato (TerminoGlosarioVistaPrevia no existe:
# TerminoGlosarioCampos no usa ContenidoComunCampos ni requiere revisión visual previa).
_RUTAS_CON_VISTA_PREVIA = tuple((ruta, tipo) for ruta, tipo in _RUTAS if tipo != T.TERMINO)

urlpatterns = (
    [
        path(f"contenidos/{ruta}", _lista(tipo, f"Lista{tipo.title()}").as_view(), name=f"{ruta}")
        for ruta, tipo in _RUTAS
    ]
    + [
        path(
            f"contenidos/{ruta}/vista-previa",
            _vista_previa(tipo, f"VistaPrevia{tipo.title()}").as_view(),
            name=f"{ruta}-vista-previa",
        )
        for ruta, tipo in _RUTAS_CON_VISTA_PREVIA
    ]
    + [
        path(
            f"contenidos/{ruta}/<int:id>",
            _detalle(tipo, f"Detalle{tipo.title()}").as_view(),
            name=f"{ruta}-detalle",
        )
        for ruta, tipo in _RUTAS
    ]
    + [
        path("contenidos/paginas", v.ListaPaginasInstitucionales.as_view(), name="paginas"),
        path(
            "contenidos/paginas/<int:id>",
            v.DetallePaginaInstitucional.as_view(),
            name="paginas-detalle",
        ),
        path(
            "contenidos/paginas/vista-previa",
            _vista_previa(T.PAGINA, "VistaPreviaPagina").as_view(),
            name="paginas-vista-previa",
        ),
        path(
            "contenidos/<tiporuta:tipo>/<int:id>/publicar",
            v.PublicarContenido.as_view(),
            name="publicar",
        ),
        path(
            "contenidos/<tiporuta:tipo>/<int:id>/analisis-publicacion",
            v.AnalizarPublicacion.as_view(),
            name="analisis-publicacion",
        ),
        path(
            "contenidos/<tiporuta:tipo>/<int:id>/impacto-retiro",
            v.ImpactoRetiro.as_view(),
            name="impacto-retiro",
        ),
        path(
            "contenidos/<tiporuta:tipo>/<int:id>/retirar",
            v.RetirarContenido.as_view(),
            name="retirar",
        ),
        path(
            "contenidos/<tiporuta:tipo>/<int:id>/reactivar",
            v.ReactivarContenido.as_view(),
            name="reactivar",
        ),
        path(
            "contenidos/<tiporuta:tipo>/<int:id>/revisiones",
            v.ListaRevisiones.as_view(),
            name="revisiones",
        ),
        path(
            "contenidos/<tiporuta:tipo>/<int:id>/revisiones/<int:numero>",
            v.DetalleRevision.as_view(),
            name="revision-detalle",
        ),
        path(
            "contenidos/<tiporuta:tipo>/<int:id>/revisiones/<int:numero>/restaurar",
            v.RestaurarRevision.as_view(),
            name="revision-restaurar",
        ),
    ]
)
