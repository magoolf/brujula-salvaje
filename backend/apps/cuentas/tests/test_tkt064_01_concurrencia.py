"""TKT-064 (THREAT fuerza bruta, THREAT replay TOTP): contador de fallos de login en caché y anti
repetición TOTP bajo concurrencia REAL de PostgreSQL (`django_db(transaction=True)`): cada intento
corre en su hilo, con su conexión y su transacción, y todos arrancan a la vez (barrera).

- AC_TKT064_01: la suma de un fallo al contador en caché (lectura, hash de referencia y escritura,
  `_fallo_sin_cuenta`) es atómica por sí misma: MAXIMO_FALLOS fallos simultáneos sobre el mismo
  usuario bloquean exactamente una vez aunque quien llama no tenga el bloqueo del login. En main
  se perdían actualizaciones (todos leían 0 y escribían 1: sin bloqueo).
- AC_TKT064_02: la anti repetición TOTP (`_totp_valido`) es atómica por sí misma: el mismo código
  en paralelo se acepta una sola vez aunque quien llama no tenga la fila de la cuenta bloqueada.
  En main se aceptaba en todas las transacciones que leían antes del primer COMMIT.
- AC_TKT064_03: ambas operaciones exigen una transacción (en autocommit el bloqueo consultivo se
  liberaría al terminar la sentencia).
- AC_TKT064_04/05/06 (regresión de los flujos públicos, que ya serializaban por usuario y por
  fila de cuenta): login simultáneo de un usuario inexistente y de una cuenta operativa →
  bloqueo exacto al quinto fallo y la misma secuencia de respuestas (anti enumeración, THREAT-018);
  el mismo TOTP en paralelo por servicio y por HTTP → un solo éxito.
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from collections.abc import Callable
from typing import Any

import pytest
from django.core.cache import cache
from django.db import connections, transaction
from django.test import Client
from django.utils import timezone

from apps.cuentas import services
from apps.cuentas.models import CuentaStaff, EstadoCuenta, RolCuenta
from apps.cuentas.tests.conftest import BASE, IP, crear_staff

pytestmark = pytest.mark.django_db(transaction=True)

PLAZO_S = 60
INCORRECTA = "contrasena-incorrecta-2026"
# Cada transacción del AC_TKT064_02 sigue abierta este tiempo tras validar el código: sin
# atomicidad propia, todas leen la anti repetición antes del primer COMMIT.
RETENCION_S = 0.3


@pytest.fixture(autouse=True)
def _limites_limpios() -> None:
    """cache_limites no la vacía el flush de las pruebas transaccionales."""
    cache.clear()


def _en_paralelo(n: int, accion: Callable[[int], Any]) -> list[Any]:
    """accion(i) en n hilos que arrancan a la vez; resultado o excepción de cada uno."""
    barrera = threading.Barrier(n)
    resultados: list[Any] = [None] * n

    def correr(i: int) -> None:
        try:
            barrera.wait(PLAZO_S)
            resultados[i] = accion(i)
        except BaseException as exc:
            resultados[i] = exc
        finally:
            connections.close_all()

    hilos = [threading.Thread(target=correr, args=(i,)) for i in range(n)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(PLAZO_S)
    assert not any(hilo.is_alive() for hilo in hilos), "algún hilo no terminó"
    return resultados


def _nombres(resultados: list[Any]) -> Counter[str]:
    return Counter(type(resultado).__name__ for resultado in resultados)


# ---------------------------------------------------------------------------
# Atomicidad propia de las operaciones (fallaban en main)
# ---------------------------------------------------------------------------
def test_AC_TKT064_01_fallos_simultaneos_en_cache_bloquean_exactamente() -> None:
    usuario = "nadie.simultaneo"

    def fallo(_i: int) -> Any:
        with transaction.atomic():
            return services._fallo_sin_cuenta(usuario, INCORRECTA, timezone.now(), IP, None)

    resultados = _en_paralelo(services.MAXIMO_FALLOS, fallo)

    errores = [r for r in resultados if isinstance(r, BaseException)]
    assert errores == []
    bloqueos = [r for r in resultados if r is not None]
    assert len(bloqueos) == 1, resultados  # main: 0 (todos leían 0 y escribían 1)
    fallos = services._leer_fallos(usuario)
    assert fallos["intentos"] == 0
    assert fallos["bloqueos"] == 1
    assert services._bloqueo_de(fallos, timezone.now()) is not None


def test_AC_TKT064_01_un_fallo_mas_del_maximo_ya_encuentra_el_bloqueo() -> None:
    usuario = "nadie.simultaneo.mas"

    def fallo(_i: int) -> Any:
        with transaction.atomic():
            return services._fallo_sin_cuenta(usuario, INCORRECTA, timezone.now(), IP, None)

    resultados = _en_paralelo(services.MAXIMO_FALLOS + 1, fallo)

    assert [r for r in resultados if isinstance(r, BaseException)] == []
    finales = [r for r in resultados if r is not None]
    # El quinto bloquea y el sexto (sea cual sea su orden) devuelve ese mismo bloqueo vigente.
    assert len(finales) == 2, resultados
    assert finales[0] == finales[1]
    assert services._leer_fallos(usuario)["bloqueos"] == 1


def test_AC_TKT064_02_mismo_totp_en_paralelo_sin_bloqueo_de_fila_se_acepta_una_vez() -> None:
    staff = crear_staff("admin.totp.simultaneo", rol=RolCuenta.ADMINISTRADOR)
    codigo = staff.codigo()

    def validar(_i: int) -> bool:
        with transaction.atomic():
            cuenta = CuentaStaff.objects.get(pk=staff.cuenta.pk)  # sin FOR UPDATE
            valido = services._totp_valido(cuenta, codigo)
            time.sleep(RETENCION_S)
            return valido

    resultados = _en_paralelo(6, validar)

    assert [r for r in resultados if isinstance(r, BaseException)] == []
    assert resultados.count(True) == 1, resultados  # main: 6


def test_AC_TKT064_02_tras_el_paralelo_se_rechaza_el_mismo_periodo_y_los_anteriores() -> None:
    staff = crear_staff("admin.totp.ventana", rol=RolCuenta.ADMINISTRADOR)

    def validar(_i: int) -> bool:
        with transaction.atomic():
            cuenta = CuentaStaff.objects.get(pk=staff.cuenta.pk)
            return services._totp_valido(cuenta, staff.codigo())

    assert _en_paralelo(4, validar).count(True) == 1
    with transaction.atomic():
        cuenta = CuentaStaff.objects.get(pk=staff.cuenta.pk)
        assert services._totp_valido(cuenta, staff.codigo()) is False
        assert services._totp_valido(cuenta, staff.codigo(-1)) is False
        assert services._totp_valido(cuenta, staff.codigo(1)) is True  # periodo posterior


def test_AC_TKT064_03_las_operaciones_atomicas_exigen_transaccion() -> None:
    staff = crear_staff("admin.totp.autocommit", rol=RolCuenta.ADMINISTRADOR)
    with pytest.raises(RuntimeError, match="transacción"):
        services._totp_valido(staff.cuenta, staff.codigo())
    with pytest.raises(RuntimeError, match="transacción"):
        services._fallo_sin_cuenta("nadie.autocommit", INCORRECTA, timezone.now(), IP, None)
    assert services._leer_fallos("nadie.autocommit")["intentos"] == 0


# ---------------------------------------------------------------------------
# Regresión de los flujos públicos (serializados por usuario y por fila de cuenta)
# ---------------------------------------------------------------------------
def _login_fallido(usuario: str) -> Callable[[int], Any]:
    return lambda _i: services.iniciar_sesion(usuario, INCORRECTA, IP)


def test_AC_TKT064_04_logins_fallidos_simultaneos_de_inexistente_bloquean_al_quinto() -> None:
    resultados = _en_paralelo(services.MAXIMO_FALLOS, _login_fallido("nadie.carrera"))

    assert _nombres(resultados) == Counter(
        {"CredencialesInvalidas": services.MAXIMO_FALLOS - 1, "AccesoBloqueado": 1}
    )
    with pytest.raises(services.AccesoBloqueado):
        services.iniciar_sesion("nadie.carrera", INCORRECTA, IP)


def test_AC_TKT064_04_logins_fallidos_simultaneos_de_cuenta_bloquean_al_quinto() -> None:
    staff = crear_staff("editora.carrera")
    resultados = _en_paralelo(services.MAXIMO_FALLOS, _login_fallido("editora.carrera"))

    # Misma secuencia de respuestas que el usuario inexistente (anti enumeración, THREAT-018).
    assert _nombres(resultados) == Counter(
        {"CredencialesInvalidas": services.MAXIMO_FALLOS - 1, "AccesoBloqueado": 1}
    )
    cuenta = CuentaStaff.objects.get(pk=staff.cuenta.pk)
    assert cuenta.estado == EstadoCuenta.BLOQUEADA_TEMPORAL
    assert cuenta.bloqueos_consecutivos == 1
    assert cuenta.intentos_fallidos == 0
    with pytest.raises(services.AccesoBloqueado):
        services.iniciar_sesion("editora.carrera", staff.contrasena, IP)


def test_AC_TKT064_05_mismo_totp_en_paralelo_por_servicio_un_solo_exito() -> None:
    staff = crear_staff("admin.mfa.carrera", rol=RolCuenta.ADMINISTRADOR)
    codigo = staff.codigo()
    resultados = _en_paralelo(4, lambda _i: services.verificar_mfa(staff.cuenta.pk, codigo, IP))

    assert _nombres(resultados) == Counter({"CuentaStaff": 1, "MfaInvalido": 3})


def test_AC_TKT064_06_mismo_totp_en_paralelo_por_http_un_solo_exito() -> None:
    staff = crear_staff("admin.http.carrera", rol=RolCuenta.ADMINISTRADOR)
    clientes = [Client(raise_request_exception=False) for _ in range(4)]
    for cliente in clientes:
        respuesta = cliente.post(
            f"{BASE}/auth/login",
            {"usuario": staff.cuenta.usuario, "contrasena": staff.contrasena},
            content_type="application/json",
            REMOTE_ADDR=IP,
        )
        assert respuesta.status_code == 200, respuesta.content
        assert respuesta.json()["paso_pendiente"] == "MFA"
    codigo = staff.codigo()

    def verificar(i: int) -> int:
        return (
            clientes[i]
            .post(
                f"{BASE}/auth/mfa/verificar",
                {"codigo": codigo},
                content_type="application/json",
                REMOTE_ADDR=IP,
            )
            .status_code
        )

    estados = _en_paralelo(len(clientes), verificar)

    assert sorted(estados) == [200, 401, 401, 401], estados
