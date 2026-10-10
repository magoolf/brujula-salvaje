"""Limitación de tasa base e IP del cliente (DEC-AUTO-111, ADR-API-002 §9, ADR-DB-005 §3).

- Solo actúa en vistas que declaran `throttle_scope` (perfiles `x-limite-tasa` del contrato).
- Clave de origen: HMAC-SHA256 (THROTTLE_HMAC_KEY) de la IP truncada (/24 IPv4, /48 IPv6) o de
  la cuenta autenticada. Nunca se guarda la IP en claro (REQ-057, THREAT-020).
- IP del cliente (RSK-OPS-012): `X-Forwarded-For` solo se tiene en cuenta si REMOTE_ADDR es un
  proxy de confianza (DJANGO_TRUSTED_PROXIES, lista de redes). Sin esa lista se conserva el
  comportamiento de DRF con NUM_PROXIES.
- Almacenamiento: tabla de la caché "default" (cache_limites, UNLOGGED, TKT-003), con conteo
  ATÓMICO (TKT-043): el SimpleRateThrottle de DRF hacía get + set del historial a través de la
  caché (lectura-modificación-escritura) y las peticiones simultáneas perdían actualizaciones;
  una ráfaga concurrente de la misma cuenta no recibía ningún 429. Ahora cada petición ejecuta
  una única sentencia INSERT ... ON CONFLICT DO UPDATE ... WHERE ... RETURNING que, bajo el
  bloqueo de fila de PostgreSQL, descarta las marcas fuera de la ventana, comprueba la cuota y
  añade la suya. La semántica es la de DRF (ventana deslizante exacta y la misma `wait()` para
  Retry-After); solo cambia el formato del valor (`float8[]` en texto, en vez de pickle) y la
  clave, que no lleva el prefijo ":<versión>:" de la caché de Django, así que nunca colisiona
  con las entradas de `cache.get/set`. `cache.clear()` y la purga de caducadas las siguen
  borrando (columna `expires` = última marca + ventana).
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
from collections.abc import Mapping
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.cache import caches
from django.db import connections, router
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


# Purga de caducadas dentro de la misma sentencia (sin consultas extra, así que el número de
# consultas por petición es fijo): en ~1 de cada N sentencias se borran hasta LOTE_PURGA filas
# caducadas (nunca vigentes, como CacheSinDesalojo._cull), saltando las bloqueadas por otra
# petición. Sustituye a la purga que antes disparaba `cache.set` al superar MAX_ENTRIES; la
# purga diaria PURGA_OPS sigue existiendo.
FRECUENCIA_PURGA = 200
LOTE_PURGA = 500

# Una sola sentencia y una sola fila por (ámbito, origen): el ON CONFLICT DO UPDATE toma el
# bloqueo de la fila y evalúa el WHERE sobre su versión más reciente, así que las peticiones
# simultáneas se serializan en la fila y ninguna pierde la marca de otra. Si la cuota está
# agotada el WHERE es falso: no se modifica nada y el CTE no devuelve filas (denegada); en ese
# caso, y solo en ese, la misma sentencia lee el historial vigente (instantánea del inicio de la
# sentencia), que solo sirve para calcular Retry-After. Un único viaje a la BD en ambos casos.
# El CTE `purga` se ejecuta siempre hasta el final aunque no se referencie (PostgreSQL) y excluye
# la clave de la petición, para no tocar dos veces la misma fila en una sentencia.
# Identificador de tabla citado con quote_name (configuración LOCATION); valores parametrizados.
_SQL_REGISTRAR = """
WITH purga AS (
  DELETE FROM {tabla} WHERE cache_key IN (
    SELECT p.cache_key FROM {tabla} AS p
    WHERE (SELECT random()) < %(probabilidad_purga)s
      AND p.expires < now() AND p.cache_key <> %(clave)s
    LIMIT %(lote_purga)s FOR UPDATE SKIP LOCKED
  )
), registro AS (
  INSERT INTO {tabla} AS c (cache_key, value, expires)
  VALUES (%(clave)s, ARRAY[%(ahora)s::float8]::text, to_timestamp(%(ahora)s + %(ventana)s))
  ON CONFLICT (cache_key) DO UPDATE SET
    value = array_append(
      ARRAY(SELECT m FROM unnest(c.value::float8[]) AS m WHERE m > %(desde)s ORDER BY m),
      %(ahora)s::float8
    )::text,
    expires = EXCLUDED.expires
  WHERE (SELECT count(*) FROM unnest(c.value::float8[]) AS m WHERE m > %(desde)s) < %(maximo)s
  RETURNING value
)
SELECT r.value, CASE WHEN r.value IS NULL THEN (
  SELECT ARRAY(SELECT m FROM unnest(h.value::float8[]) AS m WHERE m > %(desde)s ORDER BY m)::text
  FROM {tabla} AS h WHERE h.cache_key = %(clave)s
) END
FROM (SELECT (SELECT value FROM registro) AS value) AS r
"""


def _marcas(texto: str | None) -> list[float]:
    """'{1.5,2.5}' -> [2.5, 1.5] (más reciente primero, el orden de DRF para `wait()`)."""
    contenido = (texto or "").strip("{}")
    return sorted((float(parte) for parte in contenido.split(",") if parte), reverse=True)


def registrar_peticion(
    clave: str, ahora: float, maximo: int, ventana: int
) -> tuple[bool, list[float]]:
    """Registra la petición si queda cuota en la ventana deslizante, de forma atómica.

    Devuelve (permitida, historial vigente con la marca nueva si se permitió).
    """
    if maximo < 1:  # cuota 0: siempre denegada, como DRF (len([]) >= 0)
        return False, []
    cache = caches["default"]
    tabla_cache = cache._table  # type: ignore[attr-defined]
    alias = router.db_for_write(cache.cache_model_class)  # type: ignore[attr-defined]
    conexion = connections[alias]
    tabla = conexion.ops.quote_name(tabla_cache)
    parametros: dict[str, str | int | float] = {
        "clave": clave,
        "ahora": ahora,
        "ventana": ventana,
        "desde": ahora - ventana,
        "maximo": maximo,
        "probabilidad_purga": 1.0 / FRECUENCIA_PURGA,
        "lote_purga": LOTE_PURGA,
    }
    with conexion.cursor() as cursor:
        cursor.execute(_SQL_REGISTRAR.format(tabla=tabla), parametros)
        registrada, vigente = cursor.fetchone()
    if registrada is None:
        return False, _marcas(vigente)
    return True, _marcas(registrada)


class LimitePorAmbito(ScopedRateThrottle):
    """ScopedRateThrottle con clave seudonimizada (cuenta o IP truncada) y conteo atómico."""

    def allow_request(self, request: Request, view: APIView) -> bool:
        # Mismo preámbulo que ScopedRateThrottle.allow_request + SimpleRateThrottle.allow_request;
        # solo el registro del historial pasa a ser atómico (registrar_peticion).
        self.scope = getattr(view, self.scope_attr, None)
        if not self.scope:
            return True
        self.rate = self.get_rate()
        self.num_requests, self.duration = maximo, ventana = self.parse_rate(self.rate)
        if maximo is None or ventana is None:
            return True
        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True
        self.now = self.timer()
        permitida, self.history = registrar_peticion(self.key, self.now, maximo, ventana)
        return permitida

    def wait(self) -> float | None:
        # Con peticiones simultáneas la marca más antigua puede ser posterior a self.now (otra
        # petición leyó el reloj después y registró antes): se acota a la ventana.
        espera = super().wait()
        if espera is None:
            return None
        return min(max(espera, 0.0), float(self.duration or 0))

    def get_ident(self, request: Request) -> str:
        return ip_cliente(request.META) or ""

    def get_cache_key(self, request: Request, view: APIView) -> str:
        usuario = getattr(request, "user", None)
        if usuario is not None and getattr(usuario, "is_authenticated", False):
            origen = f"cuenta:{usuario.pk}"
        else:
            origen = f"ip:{truncar_ip(self.get_ident(request))}"
        return f"limite:{self.scope}:{huella_hmac(f'{self.scope}|{origen}')}"
