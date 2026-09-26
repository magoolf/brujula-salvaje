"""Settings de producción y de los contenedores (compose): DEBUG siempre desactivado.

`manage.py check --deploy` debe pasar sin avisos con valores de producción
(DJANGO_SECURE_SSL_REDIRECT=true, DJANGO_SECURE_HSTS_SECONDS>=31536000).
"""

from __future__ import annotations

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403
from config.settings.base import MFA_FERNET_KEY, SECRET_KEY, THROTTLE_HMAC_KEY

DEBUG = False

_PLACEHOLDER = "CHANGE_ME"
for _nombre, _valor in (
    ("DJANGO_SECRET_KEY", SECRET_KEY),
    ("THROTTLE_HMAC_KEY", THROTTLE_HMAC_KEY),
):
    if _valor.startswith(_PLACEHOLDER) or len(_valor) < 32:
        raise ImproperlyConfigured(
            f"{_nombre} no es válida: usa un valor aleatorio de >= 32 caracteres "
            "(scripts/ops/init-env.sh)"
        )

# El secreto TOTP del staff se cifra con esta clave (DB_HANDOFF cuenta_staff.secreto_mfa):
# debe ser una clave Fernet (32 bytes en base64 urlsafe), nunca el marcador de .env.example.
try:
    Fernet(MFA_FERNET_KEY)
except ValueError as _error:
    raise ImproperlyConfigured(
        "MFA_FERNET_KEY no es una clave Fernet válida (scripts/ops/init-env.sh)"
    ) from _error
