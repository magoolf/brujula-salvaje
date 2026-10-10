"""Vistas del ciclo editorial del panel (contracts/openapi.yaml, `panel-contenidos` y
`panel-ciclo-editorial`). Solo transporte HTTP (Skill_Backend §4.1, Reglas 01-03): validan la
estructura, delegan en `apps.contenido.services` y serializan la respuesta.
"""

from __future__ import annotations

from typing import Any, ClassVar

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contenido import services
from apps.contenido.api import panel_selectors
from apps.contenido.api.panel_serializers import (
    ACTUALIZACION_SERIALIZER,
    ENTRADA_SERIALIZER,
    PANEL_SERIALIZER,
    VISTA_PREVIA_SERIALIZER,
    AnalisisPublicacionEntradaSerializer,
    AnalisisPublicacionSerializer,
    DestinoGuardadoSerializer,
    ImpactoRetiroSerializer,
    PaginaContenidoResumenSerializer,
    PaginaRevisionResumenSerializer,
    PublicacionEntradaSerializer,
    RestauracionRevisionSerializer,
    ResultadoTransicionSerializer,
    RetiroEntradaSerializer,
    RevisionDetalleSerializer,
    TransicionEntradaSerializer,
)
from apps.contenido.models import ClavePagina, TipoContenido
from apps.core import idempotencia
from apps.core.exceptions import ErrorApi, NoEncontrado
from apps.core.paginacion import PaginacionNumerada
from apps.core.parametros import errores_de_parametros, validar_parametros
from apps.core.throttling import ip_cliente
from apps.cuentas.permisos import SesionPanel, cuenta_de

T = TipoContenido
ID_MAXIMO = 2**63 - 1
# components.parameters.Pagina (contracts/openapi.yaml): ver panel_urls.PARAMETROS_LISTADO.
PARAMETRO_PAGINA = [
    OpenApiParameter(
        "pagina",
        int,
        OpenApiParameter.QUERY,
        required=False,
        description="Número de página (base 1). Fuera de rango → 404 pagina_fuera_de_rango.",
    )
]
# components.parameters.IdempotencyKey (contracts/openapi.yaml): ver panel_urls.py.
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
TIPOS_CON_CREACION = (T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO, T.COLECCION, T.TERMINO)
OPERACION_CREAR: dict[str, str] = {
    T.DESTINO: "panelCrearDestino",
    T.ITINERARIO: "panelCrearItinerario",
    T.GUIA: "panelCrearGuia",
    T.TIPO: "panelCrearTipoAventura",
    T.COLECCION: "panelCrearColeccion",
    T.TERMINO: "panelCrearTerminoGlosario",
}
OPERACION_LISTAR: dict[str, str] = {
    T.DESTINO: "panelListarDestinos",
    T.ITINERARIO: "panelListarItinerarios",
    T.GUIA: "panelListarGuias",
    T.TIPO: "panelListarTiposAventura",
    T.COLECCION: "panelListarColecciones",
    T.TERMINO: "panelListarTerminosGlosario",
}
OPERACION_OBTENER: dict[str, str] = {
    T.DESTINO: "panelObtenerDestino",
    T.ITINERARIO: "panelObtenerItinerario",
    T.GUIA: "panelObtenerGuia",
    T.TIPO: "panelObtenerTipoAventura",
    T.COLECCION: "panelObtenerColeccion",
    T.TERMINO: "panelObtenerTerminoGlosario",
}
OPERACION_ACTUALIZAR: dict[str, str] = {
    T.DESTINO: "panelActualizarDestino",
    T.ITINERARIO: "panelActualizarItinerario",
    T.GUIA: "panelActualizarGuia",
    T.TIPO: "panelActualizarTipoAventura",
    T.COLECCION: "panelActualizarColeccion",
    T.TERMINO: "panelActualizarTerminoGlosario",
}
OPERACION_ELIMINAR: dict[str, str] = {
    T.DESTINO: "panelEliminarDestino",
    T.ITINERARIO: "panelEliminarItinerario",
    T.GUIA: "panelEliminarGuia",
    T.TIPO: "panelEliminarTipoAventura",
    T.COLECCION: "panelEliminarColeccion",
    T.TERMINO: "panelEliminarTerminoGlosario",
}
OPERACION_VISTA_PREVIA: dict[str, str] = {
    T.DESTINO: "panelVistaPreviaDestino",
    T.ITINERARIO: "panelVistaPreviaItinerario",
    T.GUIA: "panelVistaPreviaGuia",
    T.TIPO: "panelVistaPreviaTipoAventura",
    T.COLECCION: "panelVistaPreviaColeccion",
    T.PAGINA: "panelVistaPreviaPaginaInstitucional",
}


def _ip(request: Request) -> str | None:
    return ip_cliente(request.META)


def _id(id: int) -> int:
    if not 1 <= id <= ID_MAXIMO:
        raise NoEncontrado()
    return id


class _VistaPanelContenido(APIView):
    permission_classes = [SesionPanel]
    throttle_scope = "panel-lectura"


class _VistaPanelMixta(_VistaPanelContenido):
    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        self.throttle_scope = (
            "panel-lectura" if request.method in SAFE_METHODS else "panel-escritura"
        )
        super().initial(request, *args, **kwargs)


def _autorizar_pagina(request: Request, clave: str) -> None:
    if clave != ClavePagina.ACERCA_DE and not cuenta_de(request).es_administrador:
        raise ErrorApi(codigo="permiso_denegado")


def _autorizar_ciclo(request: Request, tipo: str, id: int) -> str:
    """Tipo interno de la ruta `{tipo}` de las operaciones de ciclo y de revisiones, tras aplicar a
    las páginas institucionales la misma autorización que su PUT: las páginas legales (todas salvo
    ACERCA_DE) solo las consulta, publica, retira, reactiva y restaura un Administrador → 403
    `permiso_denegado` (TKT-050 revisiones, TKT-052 ciclo; AC-033). El 404 del contenido inexistente
    se mantiene antes que el 403 (igual que el PUT) y el 403 precede a cualquier búsqueda
    secundaria, a la idempotencia y a cualquier efecto o auditoría."""
    tipo_interno = services.RUTA_A_TIPO[tipo]
    if tipo_interno == T.PAGINA:
        contenido = services.obtener_para_editar(T.PAGINA, _id(id))
        _autorizar_pagina(request, contenido.pagina.clave)
    return tipo_interno


# ---------------------------------------------------------------------------
# Listado + creación por tipo: /panel/contenidos/{ruta}
# ---------------------------------------------------------------------------
class ListaContenidoPorTipo(_VistaPanelMixta):
    tipo: ClassVar[str]
    tamano_pagina = 50

    def get(self, request: Request) -> Response:
        validar_parametros(request.query_params, {"estado", "q", "pagina"})
        estado = request.query_params.get("estado")
        if estado and estado not in {"BORRADOR", "PUBLICADO", "RETIRADO"}:
            raise errores_de_parametros({"estado": ["Valor no admitido."]})
        texto = request.query_params.get("q")
        qs = panel_selectors.listar_por_tipo(self.tipo, estado=estado, texto=texto)
        paginador = PaginacionNumerada()
        pagina = paginador.paginate_queryset(qs, request, view=self)
        return paginador.get_paginated_response(_serializar_lista(pagina))

    def post(self, request: Request) -> Response:
        entrada = ENTRADA_SERIALIZER[self.tipo](data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)

        def efecto() -> idempotencia.Resultado:
            contenido = services.crear_borrador(
                self.tipo, actor.pk, dict(entrada.validated_data), _ip(request)
            )
            cuerpo = PANEL_SERIALIZER[self.tipo](contenido).data
            return idempotencia.Resultado(
                codigo_http=status.HTTP_201_CREATED, cuerpo=cuerpo, recurso_id=contenido.pk
            )

        resultado = idempotencia.ejecutar(
            cuenta_id=actor.pk,
            clave=idempotencia.leer_clave(request.headers.get(idempotencia.CABECERA)),
            operacion=OPERACION_CREAR[self.tipo],
            huella=idempotencia.huella_peticion(OPERACION_CREAR[self.tipo], {}, request.data),
            efecto=efecto,
            ubicacion=lambda cid: (
                f"/api/v1/panel/contenidos/{services.TIPO_A_RUTA[self.tipo]}/{cid}"
            ),
        )
        return Response(resultado.cuerpo, status=resultado.codigo_http)


def _serializar_lista(pagina: Any) -> list[dict[str, Any]]:
    from apps.contenido.api.panel_serializers import ContenidoResumenPanelSerializer

    return list(ContenidoResumenPanelSerializer(pagina, many=True).data)


class ListaPaginasInstitucionales(_VistaPanelContenido):
    tamano_pagina = 50

    @extend_schema(
        operation_id="panelListarPaginasInstitucionales",
        tags=["panel-contenidos"],
        parameters=PARAMETRO_PAGINA,
        responses={200: PaginaContenidoResumenSerializer},
    )
    def get(self, request: Request) -> Response:
        validar_parametros(request.query_params, {"pagina"})
        qs = panel_selectors.listar_por_tipo(T.PAGINA)
        paginador = PaginacionNumerada()
        pagina = paginador.paginate_queryset(qs, request, view=self)
        return paginador.get_paginated_response(_serializar_lista(pagina))


# ---------------------------------------------------------------------------
# Detalle: /panel/contenidos/{ruta}/{id}
# ---------------------------------------------------------------------------
class DetalleContenidoPorTipo(_VistaPanelMixta):
    tipo: ClassVar[str]

    def get(self, request: Request, id: int) -> Response:
        contenido = services.obtener_para_editar(self.tipo, _id(id))
        return Response(PANEL_SERIALIZER[self.tipo](contenido).data)

    def put(self, request: Request, id: int) -> Response:
        entrada = ACTUALIZACION_SERIALIZER[self.tipo](data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        datos = dict(entrada.validated_data)
        version = datos.pop("version")
        resultado = services.actualizar(self.tipo, _id(id), actor.pk, datos, version, _ip(request))
        if resultado.entidades_afectadas or self.tipo == T.DESTINO:
            return Response(
                DestinoGuardadoSerializer((resultado.contenido, resultado.entidades_afectadas)).data
            )
        return Response(PANEL_SERIALIZER[self.tipo](resultado.contenido).data)

    def delete(self, request: Request, id: int) -> Response:
        validar_parametros(request.query_params, {"version"})
        version = request.query_params.get("version")
        if version is None or not version.isdigit():
            raise errores_de_parametros({"version": ["Debes indicar la versión."]})
        actor = cuenta_de(request)
        services.eliminar_borrador(self.tipo, _id(id), actor.pk, int(version), _ip(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


class DetallePaginaInstitucional(_VistaPanelMixta):
    @extend_schema(
        operation_id="panelObtenerPaginaInstitucional",
        tags=["panel-contenidos"],
        responses={200: PANEL_SERIALIZER[T.PAGINA]},
    )
    def get(self, request: Request, id: int) -> Response:
        contenido = services.obtener_para_editar(T.PAGINA, _id(id))
        return Response(PANEL_SERIALIZER[T.PAGINA](contenido).data)

    @extend_schema(
        operation_id="panelActualizarPaginaInstitucional",
        tags=["panel-contenidos"],
        request=ACTUALIZACION_SERIALIZER[T.PAGINA],
        responses={200: PANEL_SERIALIZER[T.PAGINA]},
    )
    def put(self, request: Request, id: int) -> Response:
        entrada = ACTUALIZACION_SERIALIZER[T.PAGINA](data=request.data)
        entrada.is_valid(raise_exception=True)
        contenido_previo = services.obtener_para_editar(T.PAGINA, _id(id))
        _autorizar_pagina(request, contenido_previo.pagina.clave)
        actor = cuenta_de(request)
        datos = dict(entrada.validated_data)
        version = datos.pop("version")
        resultado = services.actualizar(T.PAGINA, _id(id), actor.pk, datos, version, _ip(request))
        return Response(PANEL_SERIALIZER[T.PAGINA](resultado.contenido).data)


# ---------------------------------------------------------------------------
# Vista previa: /panel/contenidos/{ruta}/vista-previa
# ---------------------------------------------------------------------------
class VistaPreviaContenido(_VistaPanelContenido):
    tipo: ClassVar[str]
    throttle_scope = "panel-vista-previa"

    def post(self, request: Request) -> Response:
        entrada = VISTA_PREVIA_SERIALIZER[self.tipo](data=request.data)
        entrada.is_valid(raise_exception=True)
        resultado = services.vista_previa(self.tipo, dict(entrada.validated_data))
        formas: dict[str, str] = {
            T.DESTINO: "DestinoDetalle",
            T.ITINERARIO: "ItinerarioDetalle",
            T.GUIA: "GuiaDetalle",
            T.TIPO: "TipoAventuraDetalle",
            T.COLECCION: "ColeccionDetalle",
            T.PAGINA: "PaginaInstitucionalPublica",
        }
        return Response(
            {
                "marca": "VISTA PREVIA – NO PUBLICADO",
                "forma": formas[self.tipo],
                "datos": resultado["datos"],
                "requisitos_publicacion": resultado["requisitos_publicacion"],
            }
        )


# ---------------------------------------------------------------------------
# Ciclo editorial: /panel/contenidos/{tipo}/{id}/...
# ---------------------------------------------------------------------------
class PublicarContenido(_VistaPanelContenido):
    throttle_scope = "panel-escritura"

    @extend_schema(
        operation_id="panelPublicarContenido",
        tags=["panel-ciclo-editorial"],
        parameters=PARAMETRO_IDEMPOTENCY_KEY,
        request=PublicacionEntradaSerializer,
        responses={200: ResultadoTransicionSerializer},
    )
    def post(self, request: Request, tipo: str, id: int) -> Response:
        entrada = PublicacionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        datos = entrada.validated_data
        tipo_real = _autorizar_ciclo(request, tipo, id)

        def efecto() -> idempotencia.Resultado:
            contenido, afectadas = services.publicar(
                tipo_real,
                _id(id),
                actor.pk,
                datos["version"],
                list(datos.get("copublicar_tipos") or []),
                _ip(request),
            )
            cuerpo = _resultado_transicion(contenido, afectadas)
            return idempotencia.Resultado(
                codigo_http=status.HTTP_200_OK, cuerpo=cuerpo, recurso_id=contenido.pk
            )

        resultado = idempotencia.ejecutar(
            cuenta_id=actor.pk,
            clave=idempotencia.leer_clave(request.headers.get(idempotencia.CABECERA)),
            operacion="panelPublicarContenido",
            huella=idempotencia.huella_peticion(
                "panelPublicarContenido", {"tipo": tipo, "id": id}, request.data
            ),
            efecto=efecto,
        )
        return Response(resultado.cuerpo, status=resultado.codigo_http)


def _resultado_transicion(contenido: Any, afectadas: list[dict[str, Any]]) -> dict[str, Any]:
    ultima_revision = afectadas[0].get("numero_revision") if afectadas else None
    return {
        "id": contenido.pk,
        "tipo": contenido.tipo,
        "estado_editorial": contenido.estado_editorial,
        "version": contenido.version,
        "numero_revision": ultima_revision,
        "url_publica": services._url_publica(contenido),
        "afectados": [
            {
                "tipo": e["tipo"],
                "id": e["id"],
                "titulo": e["titulo"],
                "slug": e.get("slug"),
                "estado_editorial": e["estado_editorial"],
            }
            for e in afectadas[1:]
        ],
        "entidades": afectadas,
    }


class AnalizarPublicacion(_VistaPanelContenido):
    throttle_scope = "panel-vista-previa"

    @extend_schema(
        operation_id="panelAnalizarPublicacion",
        tags=["panel-ciclo-editorial"],
        request=AnalisisPublicacionEntradaSerializer,
        responses={200: AnalisisPublicacionSerializer},
    )
    def post(self, request: Request, tipo: str, id: int) -> Response:
        entrada = AnalisisPublicacionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        resultado = services.analizar_publicacion(
            _autorizar_ciclo(request, tipo, id),
            _id(id),
            datos["version"],
            list(datos.get("tipos_ids") or []) or None,
            datos.get("tipo_principal_id"),
        )
        return Response(AnalisisPublicacionSerializer(resultado).data)


class ImpactoRetiro(_VistaPanelContenido):
    @extend_schema(
        operation_id="panelObtenerImpactoRetiro",
        tags=["panel-ciclo-editorial"],
        responses={200: ImpactoRetiroSerializer},
    )
    def get(self, request: Request, tipo: str, id: int) -> Response:
        resultado = services.impacto_retiro(_autorizar_ciclo(request, tipo, id), _id(id))
        return Response(ImpactoRetiroSerializer(resultado).data)


class RetirarContenido(_VistaPanelContenido):
    throttle_scope = "panel-escritura"

    @extend_schema(
        operation_id="panelRetirarContenido",
        tags=["panel-ciclo-editorial"],
        parameters=PARAMETRO_IDEMPOTENCY_KEY,
        request=RetiroEntradaSerializer,
        responses={200: ResultadoTransicionSerializer},
    )
    def post(self, request: Request, tipo: str, id: int) -> Response:
        entrada = RetiroEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        datos = entrada.validated_data
        tipo_real = _autorizar_ciclo(request, tipo, id)

        def efecto() -> idempotencia.Resultado:
            contenido, afectadas = services.retirar(
                tipo_real,
                _id(id),
                actor.pk,
                datos["version"],
                datos["motivo"],
                datos.get("confirmar_cascada", False),
                list(datos.get("cascada_confirmada") or []) or None,
                _ip(request),
            )
            cuerpo = _resultado_transicion(contenido, afectadas)
            return idempotencia.Resultado(
                codigo_http=status.HTTP_200_OK, cuerpo=cuerpo, recurso_id=contenido.pk
            )

        resultado = idempotencia.ejecutar(
            cuenta_id=actor.pk,
            clave=idempotencia.leer_clave(request.headers.get(idempotencia.CABECERA)),
            operacion="panelRetirarContenido",
            huella=idempotencia.huella_peticion(
                "panelRetirarContenido", {"tipo": tipo, "id": id}, request.data
            ),
            efecto=efecto,
        )
        return Response(resultado.cuerpo, status=resultado.codigo_http)


class ReactivarContenido(_VistaPanelContenido):
    throttle_scope = "panel-escritura"

    @extend_schema(
        operation_id="panelReactivarContenido",
        tags=["panel-ciclo-editorial"],
        parameters=PARAMETRO_IDEMPOTENCY_KEY,
        request=TransicionEntradaSerializer,
        responses={200: ResultadoTransicionSerializer},
    )
    def post(self, request: Request, tipo: str, id: int) -> Response:
        entrada = TransicionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        tipo_real = _autorizar_ciclo(request, tipo, id)

        def efecto() -> idempotencia.Resultado:
            contenido = services.reactivar(
                tipo_real, _id(id), actor.pk, entrada.validated_data["version"], _ip(request)
            )
            cuerpo = _resultado_transicion(
                contenido, [services._entidad_transitada(contenido, origen="PRINCIPAL")]
            )
            return idempotencia.Resultado(
                codigo_http=status.HTTP_200_OK, cuerpo=cuerpo, recurso_id=contenido.pk
            )

        resultado = idempotencia.ejecutar(
            cuenta_id=actor.pk,
            clave=idempotencia.leer_clave(request.headers.get(idempotencia.CABECERA)),
            operacion="panelReactivarContenido",
            huella=idempotencia.huella_peticion(
                "panelReactivarContenido", {"tipo": tipo, "id": id}, request.data
            ),
            efecto=efecto,
        )
        return Response(resultado.cuerpo, status=resultado.codigo_http)


class ListaRevisiones(_VistaPanelContenido):
    tamano_pagina = 50

    @extend_schema(
        operation_id="panelListarRevisiones",
        tags=["panel-ciclo-editorial"],
        parameters=PARAMETRO_PAGINA,
        responses={200: PaginaRevisionResumenSerializer},
    )
    def get(self, request: Request, tipo: str, id: int) -> Response:
        validar_parametros(request.query_params, {"pagina"})
        qs = services.listar_revisiones(_autorizar_ciclo(request, tipo, id), _id(id))
        paginador = PaginacionNumerada()
        pagina = paginador.paginate_queryset(qs, request, view=self)
        return paginador.get_paginated_response(_serializar_revisiones(pagina))


def _serializar_revisiones(pagina: Any) -> list[dict[str, Any]]:
    from apps.contenido.api.panel_serializers import RevisionResumenSerializer

    datos = []
    for r in pagina:
        datos.append(
            {
                "numero_revision": r.numero_revision,
                "motivo": r.motivo,
                "creado_en": r.creado_en,
                "creado_por": {
                    "id": r.creado_por_id,
                    "etiqueta": f"#{r.creado_por_id}" if r.creado_por_id else "sistema",
                },
            }
        )
    return list(RevisionResumenSerializer(datos, many=True).data)


class DetalleRevision(_VistaPanelContenido):
    @extend_schema(
        operation_id="panelObtenerRevision",
        tags=["panel-ciclo-editorial"],
        responses={200: RevisionDetalleSerializer},
    )
    def get(self, request: Request, tipo: str, id: int, numero: int) -> Response:
        r = services.obtener_revision(_autorizar_ciclo(request, tipo, id), _id(id), numero)
        datos = {
            "numero_revision": r.numero_revision,
            "motivo": r.motivo,
            "creado_en": r.creado_en,
            "creado_por": {
                "id": r.creado_por_id,
                "etiqueta": f"#{r.creado_por_id}" if r.creado_por_id else "sistema",
            },
            "instantanea": r.instantanea,
        }
        return Response(RevisionDetalleSerializer(datos).data)


class RestaurarRevision(_VistaPanelContenido):
    throttle_scope = "panel-escritura"

    @extend_schema(
        operation_id="panelRestaurarRevision",
        tags=["panel-ciclo-editorial"],
        request=None,
        responses={200: RestauracionRevisionSerializer},
    )
    def post(self, request: Request, tipo: str, id: int, numero: int) -> Response:
        tipo_interno = _autorizar_ciclo(request, tipo, id)
        actor = cuenta_de(request)
        resultado = services.restaurar_revision(
            tipo_interno, _id(id), numero, actor.pk, _ip(request)
        )
        return Response(RestauracionRevisionSerializer(resultado).data)
