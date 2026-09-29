"""Rutas raíz. Superficies (DEC-AUTO-100): /health/*, /api/v1/publico/**, /api/v1/panel/**.

Público de TKT-005: /api/v1/publico/** (solo lectura, anónimo). Panel de TKT-004:
/api/v1/panel/auth/**, /api/v1/panel/cuentas/** y /api/v1/panel/auditoria. Panel de TKT-006:
contenidos, medios, taxonomías, inicio, configuración y tablero. Los errores fuera de DRF
también responden application/problem+json (Skill_Backend §12.1).
"""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.api.urls")),
    path("api/v1/publico/", include("apps.contenido.api.urls")),
    path("api/v1/panel/", include("apps.cuentas.api.urls")),
    path("api/v1/panel/", include("apps.auditoria.api.urls")),
    path("api/v1/panel/", include("apps.contenido.api.panel_urls")),
    path("api/v1/panel/", include("apps.medios.api.urls")),
    path("api/v1/panel/", include("apps.catalogos.api.urls")),
    path("api/v1/panel/", include("apps.inicio.api.urls")),
]

handler400 = "apps.core.api.views.solicitud_invalida"
handler403 = "apps.core.api.views.permiso_denegado"
handler404 = "apps.core.api.views.no_encontrado"
handler500 = "apps.core.api.views.error_servidor"
