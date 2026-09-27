"""Rutas raíz. Superficies (DEC-AUTO-100): /health/*, /api/v1/publico/**, /api/v1/panel/**.

Panel de TKT-004: /api/v1/panel/auth/**, /api/v1/panel/cuentas/** y /api/v1/panel/auditoria.
El resto de rutas /api/v1/** se añade en TKT-005/006. Los errores fuera de DRF también responden
application/problem+json (Skill_Backend §12.1).
"""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.api.urls")),
    path("api/v1/panel/", include("apps.cuentas.api.urls")),
    path("api/v1/panel/", include("apps.auditoria.api.urls")),
]

handler400 = "apps.core.api.views.solicitud_invalida"
handler403 = "apps.core.api.views.permiso_denegado"
handler404 = "apps.core.api.views.no_encontrado"
handler500 = "apps.core.api.views.error_servidor"
