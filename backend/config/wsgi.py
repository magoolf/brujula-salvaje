"""WSGI de Brújula Salvaje (gunicorn config.wsgi:application).

OpenTelemetry se instrumenta antes de cargar la aplicación (su middleware debe registrarse
antes de construir la cadena) y solo si OTEL_SDK_DISABLED=false.
"""

import os

import django
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup(set_prefix=False)

from apps.core.observabilidad import configurar_otel  # noqa: E402

configurar_otel()

application = get_wsgi_application()
