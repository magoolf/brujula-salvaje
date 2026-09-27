"""Settings de pruebas (pytest usa --ds=config.settings.test).

PostgreSQL real (compose.ci.yaml): DB_HOST/DB_PORT/DB_USER/DB_PASSWORD del entorno; la BD de
pruebas es test_brujula. Los secretos tienen valores de prueba solo si el entorno no los define.
"""

from __future__ import annotations

import base64
import os

os.environ.setdefault("DJANGO_SECRET_KEY", "clave-solo-para-pruebas-" + "x" * 40)
os.environ.setdefault("THROTTLE_HMAC_KEY", "hmac-solo-para-pruebas-" + "y" * 40)
# Clave Fernet bien formada (32 bytes en base64 urlsafe) solo para pruebas.
os.environ.setdefault(
    "MFA_FERNET_KEY", base64.urlsafe_b64encode(b"fernet-solo-para-pruebas-" + b"z" * 7).decode()
)
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_USER", "app_migrator")

from config.settings.base import *  # noqa: F403
from config.settings.base import DATABASES

# PostgreSQL estándar + vaciado compatible con el trigger anti-TRUNCATE de evento_auditoria en
# las pruebas transaccionales (apps/ops/bd_pruebas/base.py, TKT-003).
DATABASES["default"]["ENGINE"] = "apps.ops.bd_pruebas"

DEBUG = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
OTEL_SDK_DISABLED = True
