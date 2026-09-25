"""Settings de pruebas (pytest usa --ds=config.settings.test).

PostgreSQL real (compose.ci.yaml): DB_HOST/DB_PORT/DB_USER/DB_PASSWORD del entorno; la BD de
pruebas es test_brujula. Los secretos tienen valores de prueba solo si el entorno no los define.
"""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "clave-solo-para-pruebas-" + "x" * 40)
os.environ.setdefault("THROTTLE_HMAC_KEY", "hmac-solo-para-pruebas-" + "y" * 40)
os.environ.setdefault("MFA_FERNET_KEY", "fernet-solo-para-pruebas")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_USER", "app_migrator")

from config.settings.base import *  # noqa: F403

DEBUG = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
OTEL_SDK_DISABLED = True
