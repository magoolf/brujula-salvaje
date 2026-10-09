"""Vistas de inicio, configuración del sitio y tablero (contracts/openapi.yaml, tags
panel-configuracion y panel-tablero). Solo transporte HTTP (Skill_Backend §4.1)."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.serializers import respuesta_conflicto_bd
from apps.cuentas.permisos import SesionPanel, SoloAdministrador, cuenta_de
from apps.inicio import services
from apps.inicio.api.serializers import (
    ConfigInicioEntradaSerializer,
    ConfigInicioPanelSerializer,
    ConfiguracionSitioEntradaSerializer,
    ConfiguracionSitioSerializer,
    TableroSerializer,
)


class Tablero(APIView):
    permission_classes = [SesionPanel]
    throttle_scope = "panel-lectura"

    @extend_schema(
        operation_id="panelObtenerTablero",
        tags=["panel-tablero"],
        responses={200: TableroSerializer},
    )
    def get(self, request: Request) -> Response:
        actor = cuenta_de(request)
        resultado = services.tablero(es_administrador=actor.es_administrador)
        return Response(TableroSerializer(resultado).data)


class _VistaInicioMixta(APIView):
    permission_classes = [SesionPanel]

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        self.throttle_scope = (
            "panel-lectura" if request.method in SAFE_METHODS else "panel-escritura"
        )
        super().initial(request, *args, **kwargs)


class ConfigInicioView(_VistaInicioMixta):
    @extend_schema(
        operation_id="panelObtenerConfigInicio",
        tags=["panel-configuracion"],
        responses={200: ConfigInicioPanelSerializer},
    )
    def get(self, request: Request) -> Response:
        config = services.obtener_config_inicio()
        return Response(ConfigInicioPanelSerializer(config).data)

    @extend_schema(
        operation_id="panelActualizarConfigInicio",
        tags=["panel-configuracion"],
        request=ConfigInicioEntradaSerializer,
        responses={200: ConfigInicioPanelSerializer, **respuesta_conflicto_bd()},
    )
    def put(self, request: Request) -> Response:
        entrada = ConfigInicioEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        config = services.actualizar_config_inicio(actor.pk, dict(entrada.validated_data))
        return Response(ConfigInicioPanelSerializer(config).data)


class ConfiguracionSitioView(_VistaInicioMixta):
    permission_classes = [SesionPanel, SoloAdministrador]

    @extend_schema(
        operation_id="panelObtenerConfiguracionSitio",
        tags=["panel-configuracion"],
        responses={200: ConfiguracionSitioSerializer},
    )
    def get(self, request: Request) -> Response:
        config = services.obtener_config_sitio()
        return Response(ConfiguracionSitioSerializer(config).data)

    @extend_schema(
        operation_id="panelActualizarConfiguracionSitio",
        tags=["panel-configuracion"],
        request=ConfiguracionSitioEntradaSerializer,
        responses={200: ConfiguracionSitioSerializer, **respuesta_conflicto_bd()},
    )
    def put(self, request: Request) -> Response:
        entrada = ConfiguracionSitioEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actor = cuenta_de(request)
        config = services.actualizar_config_sitio(actor.pk, dict(entrada.validated_data))
        return Response(ConfiguracionSitioSerializer(config).data)
