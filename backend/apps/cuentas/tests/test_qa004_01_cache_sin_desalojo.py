"""Regresión de HALLAZGO-QA004-01: los estados de seguridad de la caché no se desalojan por volumen.

Con el DatabaseCache estándar (MAX_ENTRIES=300) superar el límite borraba un tercio de las claves
vigentes: los bloqueos de usuarios inexistentes volvían a 401 (oráculo de enumeración frente a
las cuentas existentes, cuyo bloqueo vive en la BD) y los contadores de limitación de tasa se
perdían. Se llena la tabla por encima de 300 y de 5000 entradas y se comprueba que persisten el
bloqueo de un inexistente, la limitación por IP y la anti-repetición TOTP, y que la respuesta a
un inexistente bloqueado y a una cuenta existente bloqueada es idéntica.
"""

from __future__ import annotations

import pytest
from django.core.cache import cache
from django.db import connection
from django.test import Client

from apps.cuentas.models import RolCuenta
from apps.cuentas.tests.conftest import CONTRASENA, crear_staff, post, problema

pytestmark = pytest.mark.django_db


def _login(cliente: Client, usuario: str, contrasena: str, ip: str):
    return post(
        cliente, "/auth/login", {"usuario": usuario, "contrasena": contrasena}, REMOTE_ADDR=ip
    )


def _rellenar(vigentes: int, caducadas: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO app.cache_limites (cache_key, value, expires) "
            "SELECT ':1:relleno:' || g, 'x', now() + interval '1 hour' "
            "FROM generate_series(1, %s) g",
            [vigentes],
        )
        cursor.execute(
            "INSERT INTO app.cache_limites (cache_key, value, expires) "
            "SELECT ':1:caducada:' || g, 'x', now() - interval '1 minute' "
            "FROM generate_series(1, %s) g",
            [caducadas],
        )


def _contar(prefijo: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM app.cache_limites WHERE cache_key LIKE %s", [f"{prefijo}%"]
        )
        return int(cursor.fetchone()[0])


@pytest.mark.parametrize("volumen", [350, 6000])
def test_QA004_01_estados_de_seguridad_sobreviven_al_volumen(volumen):
    cliente = Client(raise_request_exception=False)
    crear_staff("editora.uno")
    admin = crear_staff("admin.cache", rol=RolCuenta.ADMINISTRADOR)

    # Bloqueo de un inexistente (caché) y de una cuenta existente (BD), desde IP distintas.
    for _ in range(5):
        _login(cliente, "fantasma", "mal", "198.51.100.1")
        _login(cliente, "editora.uno", "mal", "198.51.101.1")
    # IP que agota su límite de 10/min en panel-login.
    for indice in range(10):
        _login(cliente, f"relleno{indice}", "mal", "198.51.102.1")
    # Anti-repetición TOTP: el código usado queda registrado.
    sesion_admin = Client(raise_request_exception=False)
    _login(sesion_admin, "admin.cache", CONTRASENA, "198.51.103.1")
    codigo = admin.codigo()
    assert post(sesion_admin, "/auth/mfa/verificar", {"codigo": codigo}).status_code == 200

    seguridad_antes = _contar(":1:limite:") + _contar(":1:login:") + _contar(":1:totp:")
    _rellenar(volumen, 50)
    cache.set("fuerza-poda", 1)  # un set() con la tabla por encima de MAX_ENTRIES poda

    # Por encima de MAX_ENTRIES (5000) se purgan las caducadas; nunca se desaloja una vigente.
    assert _contar(":1:caducada:") == (0 if volumen > 5000 else 50)
    assert _contar(":1:relleno:") == volumen
    assert _contar(":1:limite:") + _contar(":1:login:") + _contar(":1:totp:") >= seguridad_antes

    inexistente = _login(cliente, "fantasma", "mal", "198.51.104.1")
    existente = _login(cliente, "editora.uno", "mal", "198.51.104.1")
    cuerpo_inexistente = problema(inexistente, 429, "acceso_bloqueado_temporalmente")
    cuerpo_existente = problema(existente, 429, "acceso_bloqueado_temporalmente")
    cuerpo_inexistente.pop("trace_id")
    cuerpo_existente.pop("trace_id")
    assert cuerpo_inexistente == cuerpo_existente
    assert abs(int(inexistente["Retry-After"]) - int(existente["Retry-After"])) <= 5

    problema(_login(cliente, "otro", "mal", "198.51.102.1"), 429, "limite_tasa")

    otro = Client(raise_request_exception=False)
    _login(otro, "admin.cache", CONTRASENA, "198.51.105.1")
    problema(post(otro, "/auth/mfa/verificar", {"codigo": codigo}), 401, "mfa_invalido")


def test_QA004_01_cache_por_defecto_sin_desalojo(settings):
    assert settings.CACHES["default"]["BACKEND"] == "apps.core.cache.CacheSinDesalojo"
    _rellenar(10, 5)
    cache.set("clave", "valor")
    assert _contar(":1:caducada:") == 5  # por debajo de MAX_ENTRIES no se poda
    assert cache.get("clave") == "valor"
