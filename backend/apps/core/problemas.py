"""Problem Details RFC 9457 (Skill_Backend §12.1, ADR-API-002 §2, DEC-AUTO-103/118).

Catálogo cerrado de `code` de contracts/openapi.yaml (components.schemas.Problem).
`title` y `detail` en español y sin datos técnicos.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import JsonResponse

from apps.core.trazas import trace_id_actual

MEDIA_TYPE_PROBLEMA = "application/problem+json"

# code -> (status, title, detail por defecto)
CATALOGO: dict[str, tuple[int, str, str]] = {
    "validacion": (400, "Datos inválidos", "Revisa los campos marcados."),
    "parametro_invalido": (
        400,
        "Parámetro inválido",
        "Algún parámetro de la petición no es válido.",
    ),
    "campo_no_permitido": (400, "Campo no permitido", "La petición incluye campos no permitidos."),
    "no_autenticado": (401, "No autenticado", "Debes iniciar sesión."),
    "sesion_expirada": (401, "Sesión expirada", "Tu sesión ha expirado. Vuelve a iniciar sesión."),
    "credenciales_invalidas": (401, "Credenciales inválidas", "Usuario o contraseña incorrectos."),
    "mfa_requerido": (401, "Verificación requerida", "Introduce el código de verificación."),
    "mfa_invalido": (401, "Código inválido", "El código de verificación no es válido."),
    "permiso_denegado": (403, "Permiso denegado", "No tienes permiso para realizar esta acción."),
    "csrf_invalido": (403, "Token CSRF inválido", "Recarga la página e inténtalo de nuevo."),
    "cambio_credencial_requerido": (
        403,
        "Cambio de contraseña requerido",
        "Debes cambiar tu contraseña antes de continuar.",
    ),
    "autorizacion_requerida": (
        403,
        "Autorización requerida",
        "Debes aceptar la autorización de tratamiento de datos.",
    ),
    "configuracion_mfa_requerida": (
        403,
        "Configuración de verificación requerida",
        "Debes configurar la verificación en dos pasos.",
    ),
    "no_encontrado": (404, "No encontrado", "El recurso solicitado no existe."),
    "pagina_fuera_de_rango": (404, "Página fuera de rango", "La página solicitada no existe."),
    "metodo_no_permitido": (
        405,
        "Método no permitido",
        "El método no está permitido en este recurso.",
    ),
    "conflicto_version": (
        409,
        "Conflicto de versión",
        "El recurso cambió. Recarga y vuelve a intentarlo.",
    ),
    "transicion_invalida": (
        409,
        "Transición inválida",
        "La acción no es válida en el estado actual.",
    ),
    "slug_inmutable": (409, "Slug inmutable", "El slug no puede cambiar tras publicar."),
    "slug_en_uso": (409, "Slug en uso", "El slug ya está en uso."),
    "duplicado": (409, "Duplicado", "Ya existe un recurso igual."),
    "dependencia_bloqueante": (
        409,
        "Dependencia bloqueante",
        "Hay elementos que dependen de este recurso.",
    ),
    "medio_en_uso": (409, "Medio en uso", "El medio se usa en contenido publicado."),
    "ultimo_administrador": (
        409,
        "Último administrador",
        "Debe quedar al menos un administrador activo.",
    ),
    "operacion_sobre_si_mismo": (
        409,
        "Operación no permitida",
        "No puedes realizar esta acción sobre tu cuenta.",
    ),
    "mfa_obligatorio": (
        409,
        "Verificación obligatoria",
        "La verificación en dos pasos es obligatoria.",
    ),
    "idempotencia_en_curso": (
        409,
        "Petición en curso",
        "Otra petición con la misma clave de idempotencia aún se está procesando.",
    ),
    "idempotencia_respuesta_no_reproducible": (
        409,
        "Respuesta no reproducible",
        "La operación ya se realizó y su respuesta no puede repetirse.",
    ),
    "retirado": (410, "Contenido retirado", "Este contenido ya no está disponible."),
    "carga_demasiado_grande": (
        413,
        "Carga demasiado grande",
        "La petición supera el tamaño permitido.",
    ),
    "tipo_medio_no_soportado": (
        415,
        "Tipo no soportado",
        "El tipo de contenido de la petición no se admite.",
    ),
    "publicacion_invalida": (422, "No se puede publicar", "Faltan requisitos de publicación."),
    "regla_negocio": (422, "Regla de negocio", "La operación no cumple las reglas del sistema."),
    "idempotencia_conflicto": (
        422,
        "Conflicto de idempotencia",
        "La clave de idempotencia ya se usó con otra petición.",
    ),
    "limite_tasa": (
        429,
        "Demasiadas peticiones",
        "Has superado el límite de peticiones. Inténtalo más tarde.",
    ),
    "acceso_bloqueado_temporalmente": (
        429,
        "Acceso bloqueado temporalmente",
        "Demasiados intentos. Inténtalo más tarde.",
    ),
    "error_interno": (500, "Error interno", "Se produjo un error inesperado. Inténtalo más tarde."),
    "servicio_no_disponible": (
        503,
        "Servicio no disponible",
        "El servicio no está disponible en este momento.",
    ),
}


def cuerpo_problema(
    codigo: str,
    *,
    detalle: str | None = None,
    errors: dict[str, list[str]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cuerpo problem+json; `trace_id` es el de la petición en curso."""
    estado, titulo, detalle_defecto = CATALOGO[codigo]
    base = str(settings.PROBLEM_TYPE_BASE_URL).rstrip("/")
    cuerpo: dict[str, Any] = {
        "type": f"{base}/errors/{codigo}",
        "title": titulo,
        "status": estado,
        "detail": detalle or detalle_defecto,
        "code": codigo,
        "errors": errors or {},
        "trace_id": trace_id_actual(),
    }
    if extra:
        cuerpo.update({k: v for k, v in extra.items() if k not in cuerpo})
    return cuerpo


def respuesta_problema(codigo: str, **kwargs: Any) -> JsonResponse:
    """Respuesta Django (fuera de DRF): handlers 400/403/404/500 y fallo CSRF."""
    cuerpo = cuerpo_problema(codigo, **kwargs)
    return JsonResponse(
        cuerpo,
        status=cuerpo["status"],
        content_type=MEDIA_TYPE_PROBLEMA,
        json_dumps_params={"ensure_ascii": False},
    )
