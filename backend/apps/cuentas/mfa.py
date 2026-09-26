"""Primitivas del segundo factor (FEAT-030, ADR-API-001 §7, DEC-AUTO-037/119).

- TOTP según RFC 6238 (HMAC-SHA1, 6 dígitos, periodo de 30 s) con ventana de ±1 periodo. Sin
  dependencias ni servicios de terceros: el QR lo genera el cliente a partir de `otpauth_uri`.
- El secreto se guarda cifrado con Fernet (AES-128-CBC + HMAC-SHA256) con MFA_FERNET_KEY
  (DB_HANDOFF cuenta_staff.secreto_mfa, CONFIDENTIAL). Nunca se registra ni se devuelve salvo en
  el inicio de la activación.
- Códigos de recuperación: 10 códigos XXXX-XXXX (alfabeto A-Z0-9, ~41 bits cada uno) que se
  muestran una sola vez; se guarda solo su HMAC-SHA256 con una clave derivada de MFA_FERNET_KEY
  (determinista, para localizar el código por su hash con UNIQUE(cuenta_id, hash_codigo)).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

EMISOR = "Brújula Salvaje"
DIGITOS = 6
PERIODO_SEGUNDOS = 30
VENTANA_PERIODOS = 1
BYTES_SECRETO = 20  # 160 bits (RFC 4226 §4) → 32 caracteres base32
NUMERO_CODIGOS_RECUPERACION = 10
_ALFABETO_RECUPERACION = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class SecretoIlegible(Exception):
    """El secreto cifrado no se puede descifrar con la clave actual."""


def _fernet() -> Fernet:
    return Fernet(settings.MFA_FERNET_KEY)


def nuevo_secreto() -> str:
    """Secreto TOTP en base32 sin relleno (patrón del contrato ^[A-Z2-7]{16,64}$)."""
    return base64.b32encode(secrets.token_bytes(BYTES_SECRETO)).decode().rstrip("=")


def cifrar_secreto(secreto: str) -> bytes:
    return _fernet().encrypt(secreto.encode())


def descifrar_secreto(cifrado: bytes | memoryview) -> str:
    try:
        return _fernet().decrypt(bytes(cifrado)).decode()
    except InvalidToken as exc:
        raise SecretoIlegible from exc


def uri_otpauth(secreto: str, usuario: str) -> str:
    etiqueta = quote(f"{EMISOR}:{usuario}", safe="")
    parametros = urlencode(
        {
            "secret": secreto,
            "issuer": EMISOR,
            "algorithm": "SHA1",
            "digits": DIGITOS,
            "period": PERIODO_SEGUNDOS,
        },
        quote_via=quote,
    )
    return f"otpauth://totp/{etiqueta}?{parametros}"


def _clave_base32(secreto: str) -> bytes:
    relleno = "=" * (-len(secreto) % 8)
    return base64.b32decode(secreto + relleno, casefold=True)


def codigo_totp(secreto: str, periodo: int) -> str:
    """Código HOTP (RFC 4226) del contador `periodo`."""
    digest = hmac.new(_clave_base32(secreto), struct.pack(">Q", periodo), hashlib.sha1).digest()
    desplazamiento = digest[-1] & 0x0F
    numero = struct.unpack(">I", digest[desplazamiento : desplazamiento + 4])[0] & 0x7FFFFFFF
    return str(numero % (10**DIGITOS)).zfill(DIGITOS)


def periodo_actual(instante: float | None = None) -> int:
    return int((time.time() if instante is None else instante) // PERIODO_SEGUNDOS)


def verificar_totp(secreto: str, codigo: str, instante: float | None = None) -> int | None:
    """Periodo que coincide con `codigo` dentro de la ventana, o None. Comparación constante."""
    actual = periodo_actual(instante)
    coincidencia: int | None = None
    for periodo in range(actual - VENTANA_PERIODOS, actual + VENTANA_PERIODOS + 1):
        if hmac.compare_digest(codigo_totp(secreto, periodo), codigo) and coincidencia is None:
            coincidencia = periodo
    return coincidencia


def nuevos_codigos_recuperacion() -> list[str]:
    codigos: set[str] = set()
    while len(codigos) < NUMERO_CODIGOS_RECUPERACION:
        cuerpo = "".join(secrets.choice(_ALFABETO_RECUPERACION) for _ in range(8))
        codigos.add(f"{cuerpo[:4]}-{cuerpo[4:]}")
    return sorted(codigos)


def hash_codigo_recuperacion(cuenta_id: int, codigo: str) -> str:
    clave = hashlib.sha256(b"brujula.mfa.recuperacion|" + settings.MFA_FERNET_KEY.encode()).digest()
    mensaje = f"{cuenta_id}|{codigo.strip().upper()}".encode()
    return hmac.new(clave, mensaje, hashlib.sha256).hexdigest()
