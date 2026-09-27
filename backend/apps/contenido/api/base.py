"""Base de las vistas de la API pública /api/v1/publico/** (DEC-AUTO-100, ADR-API-002).

- Anónima: sin autenticación (la sesión del panel es la autenticación global de DRF) y permiso
  explícito AllowAny; nunca toca la sesión ni fija cookies (RULE-029, AC-060).
- Solo GET/HEAD: cualquier otro método → 405 metodo_no_permitido (problem+json).
- Limitación de tasa por perfil x-limite-tasa (throttle_scope), clave HMAC de la IP truncada.
- Parámetros de consulta cerrados (AC-113, THREAT-008): desconocidos, repetidos, vacíos o con
  NUL → 400 parametro_invalido; los arrays del contrato (style form, explode) en `multiples`.
- Caché HTTP (DEC-AUTO-112): 200 y 410 con `public, max-age=60, stale-while-revalidate=300`
  (o `no-store` en búsqueda y aleatorio); el resto de errores, `no-store`.
"""

from __future__ import annotations

from typing import Any, ClassVar

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contenido.api.serializers import PROBLEMA_RETIRADO
from apps.core.api.serializers import ProblemaValidacionSerializer, ProblemSerializer
from apps.core.parametros import validar_parametros
from apps.core.problemas import MEDIA_TYPE_PROBLEMA

CACHE_PUBLICO = "public, max-age=60, stale-while-revalidate=300"
CACHE_NO_STORE = "no-store"
ESTADOS_CACHEABLES = frozenset({200, 410})

PARAMETRO_PAGINA = OpenApiParameter(
    "pagina",
    int,
    description="Número de página (base 1). Fuera de rango → 404 pagina_fuera_de_rango.",
)


def _problema(descripcion: str) -> OpenApiResponse:
    return OpenApiResponse(ProblemSerializer, description=descripcion)


def respuestas(ok: Any, *, con_404: bool = False, con_410: bool = False) -> dict[Any, Any]:
    """Respuestas documentadas de una operación pública (contracts/openapi.yaml)."""
    resultado: dict[Any, Any] = {
        200: ok,
        (400, MEDIA_TYPE_PROBLEMA): OpenApiResponse(
            ProblemaValidacionSerializer,
            description="400 validacion / parametro_invalido / campo_no_permitido.",
        ),
    }
    if con_404:
        resultado[(404, MEDIA_TYPE_PROBLEMA)] = _problema(
            "404 no_encontrado / pagina_fuera_de_rango."
        )
    if con_410:
        resultado[(410, MEDIA_TYPE_PROBLEMA)] = OpenApiResponse(
            PROBLEMA_RETIRADO,
            description="410 retirado. Sin el cuerpo del contenido; incluye alternativas.",
        )
    resultado[(429, MEDIA_TYPE_PROBLEMA)] = _problema(
        "429 limite_tasa / acceso_bloqueado_temporalmente."
    )
    resultado[(500, MEDIA_TYPE_PROBLEMA)] = _problema("500 error_interno.")
    return resultado


class VistaPublica(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    http_method_names = ["get", "head"]
    throttle_scope = "publico-lectura"
    cache_control = CACHE_PUBLICO
    parametros: ClassVar[tuple[str, ...]] = ()
    multiples: ClassVar[tuple[str, ...]] = ()

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        # Después del throttling: los parámetros inválidos también consumen cuota (THREAT-009).
        validar_parametros(request.query_params, self.parametros, multiples=self.multiples)

    def finalize_response(
        self, request: Request, response: Response, *args: Any, **kwargs: Any
    ) -> Response:
        respuesta = super().finalize_response(request, response, *args, **kwargs)
        cacheable = respuesta.status_code in ESTADOS_CACHEABLES
        respuesta["Cache-Control"] = self.cache_control if cacheable else CACHE_NO_STORE
        return respuesta
