"""Rutas raíz. Superficies (DEC-AUTO-100): /health/*, /api/v1/publico/**, /api/v1/panel/**.

Las rutas /api/v1/** se añaden en TKT-004..006. Los errores fuera de DRF también responden
application/problem+json (Skill_Backend §12.1).
"""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.api.urls")),
]

handler400 = "apps.core.api.views.solicitud_invalida"
handler403 = "apps.core.api.views.permiso_denegado"
handler404 = "apps.core.api.views.no_encontrado"
handler500 = "apps.core.api.views.error_servidor"
