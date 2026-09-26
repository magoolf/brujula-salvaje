from django.urls import path

from apps.core.api.views import SaludLive, SaludReady

app_name = "core"

urlpatterns = [
    path("health/live", SaludLive.as_view(), name="salud-live"),
    path("health/ready", SaludReady.as_view(), name="salud-ready"),
]
