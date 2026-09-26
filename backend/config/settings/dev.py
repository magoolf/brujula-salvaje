"""Settings de desarrollo local fuera de contenedores (DJANGO_ENV=dev)."""

from __future__ import annotations

from config.settings.base import *  # noqa: F403

DEBUG = True
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
