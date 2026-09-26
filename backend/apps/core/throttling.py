"""Limitación de tasa base (DEC-AUTO-111, ADR-API-002 §9, ADR-DB-005 §3).

- Solo actúa en vistas que declaran `throttle_scope` (perfiles `x-limite-tasa` del contrato).
- Clave de origen: HMAC-SHA256 (THROTTLE_HMAC_KEY) de la IP truncada (/24 IPv4, /48 IPv6) o de
  la cuenta autenticada. Nunca se guarda la IP en claro (REQ-057, THREAT-020).
- La IP del cliente sale de X-Forwarded-For según NUM_PROXIES (proxy de confianza).
- Almacenamiento: caché "default" = DatabaseCache sobre cache_limites (tabla de TKT-003).
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
from typing import TYPE_CHECKING

from django.conf import settings
from rest_framework.throttling import ScopedRateThrottle

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

_PREFIJO_V4 = 24
_PREFIJO_V6 = 48


def truncar_ip(ip: str | None) -> str:
    """Red /24 (IPv4) o /48 (IPv6) de la IP; "desconocida" si no es una IP válida."""
    try:
        direccion = ipaddress.ip_address((ip or "").strip())
    except ValueError:
        return "desconocida"
    prefijo = _PREFIJO_V4 if direccion.version == 4 else _PREFIJO_V6
    return str(ipaddress.ip_network(f"{direccion}/{prefijo}", strict=False))


def huella_hmac(texto: str) -> str:
    clave = settings.THROTTLE_HMAC_KEY.encode()
    return hmac.new(clave, texto.encode(), hashlib.sha256).hexdigest()


class LimitePorAmbito(ScopedRateThrottle):
    """ScopedRateThrottle con clave seudonimizada (cuenta o IP truncada)."""

    def get_cache_key(self, request: Request, view: APIView) -> str:
        usuario = getattr(request, "user", None)
        if usuario is not None and getattr(usuario, "is_authenticated", False):
            origen = f"cuenta:{usuario.pk}"
        else:
            origen = f"ip:{truncar_ip(self.get_ident(request))}"
        return f"limite:{self.scope}:{huella_hmac(f'{self.scope}|{origen}')}"
