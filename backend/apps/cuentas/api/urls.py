"""Rutas /api/v1/panel/auth/** y /api/v1/panel/cuentas/** (contracts/openapi.yaml)."""

from django.urls import path

from apps.cuentas.api import views

app_name = "cuentas"

urlpatterns = [
    path("auth/csrf", views.ObtenerCsrf.as_view(), name="csrf"),
    path("auth/login", views.IniciarSesion.as_view(), name="login"),
    path("auth/mfa/verificar", views.VerificarMfa.as_view(), name="mfa-verificar"),
    path("auth/logout", views.CerrarSesion.as_view(), name="logout"),
    path("auth/sesion", views.ObtenerSesion.as_view(), name="sesion"),
    path("auth/sesion/renovar", views.RenovarSesion.as_view(), name="sesion-renovar"),
    path("auth/contrasena", views.CambiarContrasena.as_view(), name="contrasena"),
    path("auth/autorizacion", views.Autorizacion.as_view(), name="autorizacion"),
    path("auth/mfa/activacion", views.IniciarActivacionMfa.as_view(), name="mfa-activacion"),
    path(
        "auth/mfa/activacion/confirmar",
        views.ConfirmarActivacionMfa.as_view(),
        name="mfa-activacion-confirmar",
    ),
    path("auth/mfa/desactivar", views.DesactivarMfa.as_view(), name="mfa-desactivar"),
    path(
        "auth/mfa/codigos-recuperacion",
        views.RegenerarCodigosRecuperacion.as_view(),
        name="mfa-codigos",
    ),
    path("cuentas", views.ListaCuentas.as_view(), name="cuentas"),
    path("cuentas/<int:id>", views.DetalleCuenta.as_view(), name="cuenta"),
    path(
        "cuentas/<int:id>/restablecer-contrasena",
        views.RestablecerContrasenaCuenta.as_view(),
        name="cuenta-restablecer-contrasena",
    ),
    path(
        "cuentas/<int:id>/restablecer-mfa",
        views.RestablecerMfaCuenta.as_view(),
        name="cuenta-restablecer-mfa",
    ),
    path("cuentas/<int:id>/desactivar", views.DesactivarCuenta.as_view(), name="cuenta-desactivar"),
    path("cuentas/<int:id>/reactivar", views.ReactivarCuenta.as_view(), name="cuenta-reactivar"),
    path("cuentas/<int:id>/anonimizar", views.AnonimizarCuenta.as_view(), name="cuenta-anonimizar"),
]
