"""GET /api/v1/panel/auditoria (FEAT-046, FLOW-016, AC-030, THREAT-013).

Solo lectura y solo Administrador. No existe ninguna operación de modificación o borrado:
cualquier otro método responde 405 (THREAT-013).
"""

from __future__ import annotations

from typing import Any, cast

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria import selectors
from apps.auditoria.api.serializers import (
    EventoAuditoriaSerializer,
    FiltroAuditoriaSerializer,
    PaginaEventoAuditoriaSerializer,
)
from apps.auditoria.models import AccionAuditoria, ResultadoAuditoria
from apps.core.api.serializers import ProblemSerializer
from apps.core.paginacion import PaginacionNumerada
from apps.core.parametros import errores_de_parametros, validar_parametros
from apps.core.problemas import MEDIA_TYPE_PROBLEMA
from apps.cuentas.permisos import SesionPanel, SoloAdministrador

PARAMETROS = ("desde", "hasta", "actor_id", "accion", "tipo_entidad", "resultado", "pagina")


def _error(descripcion: str) -> OpenApiResponse:
    return OpenApiResponse(ProblemSerializer, description=descripcion)


class ListaAuditoria(APIView):
    permission_classes = [SesionPanel, SoloAdministrador]
    throttle_scope = "panel-lectura"
    tamano_pagina = 50

    @extend_schema(
        operation_id="panelListarAuditoria",
        summary="Registro de auditoría filtrado (ocurrido_en descendente, 50 por página)",
        tags=["panel-auditoria"],
        parameters=[
            OpenApiParameter("desde", OpenApiTypes.DATETIME),
            OpenApiParameter("hasta", OpenApiTypes.DATETIME),
            OpenApiParameter("actor_id", OpenApiTypes.INT64),
            OpenApiParameter("accion", str, enum=AccionAuditoria.values),
            OpenApiParameter("tipo_entidad", str, pattern=r"^[A-Z_]+$"),
            OpenApiParameter("resultado", str, enum=ResultadoAuditoria.values),
            OpenApiParameter("pagina", int, description="Número de página (base 1)."),
        ],
        responses={
            200: PaginaEventoAuditoriaSerializer,
            (400, MEDIA_TYPE_PROBLEMA): _error("400 validacion / parametro_invalido."),
            (401, MEDIA_TYPE_PROBLEMA): _error("401 no_autenticado / sesion_expirada."),
            (403, MEDIA_TYPE_PROBLEMA): _error("403 permiso_denegado / paso pendiente."),
            (404, MEDIA_TYPE_PROBLEMA): _error("404 pagina_fuera_de_rango."),
            (429, MEDIA_TYPE_PROBLEMA): _error("429 limite_tasa."),
            (500, MEDIA_TYPE_PROBLEMA): _error("500 error_interno."),
        },
    )
    def get(self, request: Request) -> Response:
        validar_parametros(request.query_params, PARAMETROS)
        filtros = FiltroAuditoriaSerializer(data=request.query_params)
        if not filtros.is_valid():
            raise errores_de_parametros(filtros.errors)
        datos = filtros.validated_data
        eventos = selectors.listar_eventos(
            selectors.FiltrosAuditoria(
                desde=datos.get("desde"),
                hasta=datos.get("hasta"),
                actor_id=datos.get("actor_id"),
                accion=datos.get("accion"),
                tipo_entidad=datos.get("tipo_entidad"),
                resultado=datos.get("resultado"),
            )
        )
        paginador = PaginacionNumerada()
        pagina = paginador.paginate_queryset(eventos, request, view=self)
        return paginador.get_paginated_response(
            cast("list[Any]", EventoAuditoriaSerializer(pagina, many=True).data)
        )
