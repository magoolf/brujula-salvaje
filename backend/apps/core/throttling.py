"""Limitación de tasa base e IP del cliente (DEC-AUTO-111, ADR-API-002 §9, ADR-DB-005 §3).

- Solo actúa en vistas que declaran `throttle_scope` (perfiles `x-limite-tasa` del contrato).
- Clave de origen: HMAC-SHA256 (THROTTLE_HMAC_KEY) de la IP truncada (/24 IPv4, /48 IPv6) o de
  la cuenta autenticada. Nunca se guarda la IP en claro (REQ-057, THREAT-020).
- IP del cliente (RSK-OPS-012): `X-Forwarded-For` solo se tiene en cuenta si REMOTE_ADDR es un
  proxy de confianza (DJANGO_TRUSTED_PROXIES, lista de redes). Sin esa lista se conserva el
  comportamiento de DRF con NUM_PROXIES.
- Almacenamiento: caché "default" = DatabaseCache sobre cache_limites (tabla de TKT-003).
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
from collections.abc import Mapping
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from django.conf import settings
from rest_framework.throttling import ScopedRateThrottle

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

_PREFIJO_V4 = 24
_PREFIJO_V6 = 48

Red = ipaddress.IPv4Network | ipaddress.IPv6Network


def truncar_ip(ip: str | None) -> str:
    """Red /24 (IPv4) o /48 (IPv6) de la IP; "desconocida" si no es una IP válida."""
    try:
        direccion = ipaddress.ip_address((ip or "").strip())
    except ValueError:
        return "desconocida"
    prefijo = _PREFIJO_V4 if direccion.version == 4 else _PREFIJO_V6
    return str(ipaddress.ip_network(f"{direccion}/{prefijo}", strict=False))


def red_truncada(ip: str | None) -> str | None:
    """Como truncar_ip, pero None si la IP no es válida (para columnas cidr)."""
    red = truncar_ip(ip)
    return None if red == "desconocida" else red


def huella_hmac(texto: str) -> str:
    clave = settings.THROTTLE_HMAC_KEY.encode()
    return hmac.new(clave, texto.encode(), hashlib.sha256).hexdigest()


@lru_cache(maxsize=8)
def _redes(proxies: tuple[str, ...]) -> tuple[Red, ...]:
    return tuple(ipaddress.ip_network(red, strict=False) for red in proxies)


def _es_proxy_de_confianza(remota: str | None, proxies: tuple[str, ...]) -> bool:
    try:
        direccion = ipaddress.ip_address((remota or "").strip())
    except ValueError:
        return False
    return any(direccion in red for red in _redes(proxies))


def ip_cliente(meta: Mapping[str, Any]) -> str | None:
    """IP del cliente según la cadena de proxies de confianza (misma regla que DRF get_ident)."""
    remota = meta.get("REMOTE_ADDR")
    reenviada = str(meta.get("HTTP_X_FORWARDED_FOR") or "")
    num_proxies = int(settings.NUM_PROXIES or 0)
    proxies = tuple(settings.PROXIES_CONFIANZA)
    if not reenviada or num_proxies <= 0:
        return remota
    if proxies and not _es_proxy_de_confianza(remota, proxies):
        return remota
    direcciones = [parte.strip() for parte in reenviada.split(",") if parte.strip()]
    if not direcciones:
        return remota
    return direcciones[-min(num_proxies, len(direcciones))]


class LimitePorAmbito(ScopedRateThrottle):
    """ScopedRateThrottle con clave seudonimizada (cuenta o IP truncada)."""

    def get_ident(self, request: Request) -> str:
        return ip_cliente(request.META) or ""

    def get_cache_key(self, request: Request, view: APIView) -> str:
        usuario = getattr(request, "user", None)
        if usuario is not None and getattr(usuario, "is_authenticated", False):
            origen = f"cuenta:{usuario.pk}"
        else:
            origen = f"ip:{truncar_ip(self.get_ident(request))}"
        return f"limite:{self.scope}:{huella_hmac(f'{self.scope}|{origen}')}"
