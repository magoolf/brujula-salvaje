"""SessionMiddleware del panel con respuesta del contrato si el guardado final falla (TKT-040).

Las vistas del panel guardan la sesión dentro de DRF (apps.cuentas.autenticacion): la renovación
de la inactividad en la autenticación, antes de cualquier efecto, y la apertura y rotación en la
propia vista. El guardado de `SessionMiddleware.process_response` queda así, de ordinario, sin
consultas (SessionStore no repite un UPDATE de datos ya guardados) y solo fija la cookie.

Si aun así fallara (p. ej. un cambio de la sesión fuera de esos caminos), Django lanzaría
`SessionInterrupted`, que fuera de DRF se responde 400 `validacion`: un código no declarado y, en
una escritura, con el efecto ya confirmado (ATOMIC_REQUESTS=False). Esta red de seguridad nunca
responde 409 (que invitaría a repetir una operación que pudo confirmarse): si el fallo es por
contención entrega la respuesta de la vista (la sesión sigue existiendo; solo no se aplica la
renovación, y queda en el log); si la fila ya no existe, 401 `sesion_expirada` (Problem Details,
declarado en todas las operaciones con sesión) y borra la cookie.
"""

from __future__ import annotations

import structlog
from django.conf import settings
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest, HttpResponse
from django.utils.cache import patch_vary_headers

from apps.core.problemas import respuesta_problema
from apps.cuentas.sesiones import descartar_en_memoria, fallo_por_contencion

logger = structlog.get_logger("brujula.cuentas")


class SesionPanelMiddleware(SessionMiddleware):
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        try:
            return super().process_response(request, response)
        except SessionInterrupted as exc:
            causa = exc.__context__
            contencion = causa is not None and fallo_por_contencion(causa)
            logger.warning(
                "sesion_no_guardada",
                momento="middleware",
                contencion=contencion,
                status_original=response.status_code,
            )
            if contencion:
                # La sesión sigue existiendo: la respuesta de la vista se entrega tal cual y solo
                # la renovación de la inactividad no se aplica (OBS-01 QA CHG-API-006).
                return response
            descartar_en_memoria(request.session)
            respuesta = respuesta_problema("sesion_expirada")
            respuesta.delete_cookie(
                settings.SESSION_COOKIE_NAME,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,  # type: ignore[arg-type]
            )
            patch_vary_headers(respuesta, ("Cookie",))
            return respuesta
