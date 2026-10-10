"""TKT-043: el limitador por ámbito cuenta de forma atómica bajo concurrencia.

Con el SimpleRateThrottle de DRF sobre DatabaseCache el conteo era get + set del historial
(lectura-modificación-escritura): N peticiones simultáneas leían el mismo historial y cada una
escribía el suyo + 1, de modo que se perdían actualizaciones y una ráfaga concurrente no recibía
ningún 429 (QA TKT-022 OBS-C2-04, DEC-AUTO-969). Estas pruebas usan hilos reales, cada uno con su
propia conexión a PostgreSQL (transaction=True), y una barrera para que las peticiones lleguen a
la vez.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any

import pytest
from django.core.cache import cache
from django.db import connection, connections
from django.test import Client
from django.test.utils import CaptureQueriesContext

from apps.core import throttling
from apps.core.throttling import LimitePorAmbito

pytestmark = pytest.mark.django_db(transaction=True)

CONCURRENTES = 12


class _Limite(LimitePorAmbito):
    THROTTLE_RATES = {"panel-login": "10/min", "panel-lectura": "600/min", "prueba-5": "5/min"}


@pytest.fixture(autouse=True)
def _cache_vacia() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


def _a_la_vez[T](n: int, funcion: Callable[[int], T]) -> list[T]:
    """Ejecuta `funcion(i)` en n hilos que arrancan juntos; cada hilo cierra su conexión."""
    barrera = threading.Barrier(n)

    def tarea(i: int) -> T:
        try:
            barrera.wait(timeout=30)
            return funcion(i)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=n) as grupo:
        return list(grupo.map(tarea, range(n)))


def _peticion(cuenta: int) -> Any:
    usuario = SimpleNamespace(pk=cuenta, is_authenticated=True)
    return SimpleNamespace(user=usuario, META={"REMOTE_ADDR": "198.51.100.7"})


def _permitir(scope: str, cuenta: int) -> bool:
    limite = _Limite()
    return limite.allow_request(_peticion(cuenta), SimpleNamespace(throttle_scope=scope))


@pytest.mark.parametrize("ronda", range(3))
def test_TKT043_01_rafaga_concurrente_respeta_el_limite_exacto(ronda: int) -> None:
    """24 peticiones simultáneas de la misma cuenta con 10/min: exactamente 10 pasan."""
    resultados = _a_la_vez(24, lambda _i: _permitir("panel-login", 1000 + ronda))
    assert resultados.count(True) == 10
    assert resultados.count(False) == 14


def test_TKT043_02_lotes_concurrentes_alcanzan_el_429_de_panel_lectura() -> None:
    """Escenario de la sonda de QA: lotes de 12 concurrentes de la misma cuenta, 600/min."""
    permitidas = 0
    denegadas = 0
    for _lote in range(55):  # 660 peticiones en lotes de 12
        resultados = _a_la_vez(CONCURRENTES, lambda _i: _permitir("panel-lectura", 42))
        permitidas += resultados.count(True)
        denegadas += resultados.count(False)
    assert permitidas == 600
    assert denegadas == 60


@pytest.mark.urls("apps.core.tests.urls_prueba")
def test_TKT043_03_http_concurrente_429_problem_details_con_retry_after() -> None:
    """Por HTTP (vista de prueba 5/min, misma red /24): 12 a la vez -> 5 x 200 y 7 x 429."""

    def pedir(i: int) -> Any:
        return Client(raise_request_exception=False).get(
            "/prueba/limitada-5", REMOTE_ADDR=f"203.0.113.{i + 1}"
        )

    respuestas = _a_la_vez(CONCURRENTES, pedir)
    codigos = sorted(r.status_code for r in respuestas)
    assert codigos == [200] * 5 + [429] * 7
    for respuesta in respuestas:
        if respuesta.status_code == 429:
            assert respuesta["Content-Type"] == "application/problem+json"
            assert respuesta.json()["code"] == "limite_tasa"
            assert 1 <= int(respuesta["Retry-After"]) <= 60


def test_TKT043_04_ambitos_y_cuentas_no_comparten_cuota() -> None:
    """Cada (ámbito, origen) tiene su propio contador también bajo concurrencia."""

    def mezcla(i: int) -> tuple[int, bool]:
        grupo = i % 3  # 0: prueba-5 cuenta 7; 1: prueba-5 cuenta 8; 2: panel-login cuenta 7
        return grupo, _permitir("panel-login" if grupo == 2 else "prueba-5", 8 if grupo == 1 else 7)

    resultados = _a_la_vez(24, mezcla)
    for grupo, maximo in ((0, 5), (1, 5), (2, 8)):
        permitidas = [ok for g, ok in resultados if g == grupo]
        assert len(permitidas) == 8
        assert permitidas.count(True) == maximo


def test_TKT043_05_secuencial_sigue_exacto_y_ventana_deslizante(monkeypatch) -> None:
    """panel-login en secuencia: 10 pasan, la 11.a no; al salir de la ventana vuelve a pasar."""
    # Reloj real como base: `expires` (última marca + ventana) debe quedar en el futuro para que la
    # purga de caducadas no borre la fila.
    base = float(int(time.time()))
    ahora = [base]
    monkeypatch.setattr(_Limite, "timer", lambda self: ahora[0])
    for i in range(10):
        ahora[0] += 1
        assert _permitir("panel-login", 5), i
    ahora[0] += 1
    limite = _Limite()
    assert not limite.allow_request(_peticion(5), SimpleNamespace(throttle_scope="panel-login"))
    # La más antigua (t+1) sale de la ventana a t+61: espera 60 - (11 - 1) = 50 s.
    assert limite.wait() == pytest.approx(50.0)
    ahora[0] = base + 61.5  # sale de la ventana la primera petición
    assert _permitir("panel-login", 5)
    assert not _permitir("panel-login", 5)
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM app.cache_limites WHERE cache_key LIKE '%limite:%'")
        assert cursor.fetchone()[0] == 1


def test_TKT043_06_purga_ocasional_solo_borra_caducadas(monkeypatch) -> None:
    """La purga que sustituye al _cull de cache.set nunca borra estados vigentes."""
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO app.cache_limites (cache_key, value, expires) VALUES "
            "('limite:viejo', '{1.0}', now() - interval '1 minute'), "
            "(':1:vigente', 'x', now() + interval '1 hour')"
        )
    monkeypatch.setattr(throttling, "FRECUENCIA_PURGA", 1)
    assert _permitir("panel-login", 77)
    with connection.cursor() as cursor:
        cursor.execute("SELECT cache_key FROM app.cache_limites ORDER BY cache_key")
        claves = [fila[0] for fila in cursor.fetchall()]
    assert "limite:viejo" not in claves
    assert ":1:vigente" in claves
    assert len(claves) == 2


def test_TKT043_07_casos_limite_del_limitador() -> None:
    limite = _Limite()
    # Sin ámbito o con ámbito sin tasa configurada: no limita (comportamiento de DRF).
    assert limite.allow_request(_peticion(1), SimpleNamespace())

    class _SinClave(_Limite):
        def get_cache_key(self, request: Any, view: Any) -> None:  # type: ignore[override]
            return None

    assert _SinClave().allow_request(_peticion(1), SimpleNamespace(throttle_scope="panel-login"))

    class _SinTasa(_Limite):
        THROTTLE_RATES = {"sin-tasa": None}

    assert _SinTasa().allow_request(_peticion(1), SimpleNamespace(throttle_scope="sin-tasa"))

    # Cuota 0: se deniega siempre; sin historial la espera es la ventana completa.
    class _Cero(_Limite):
        THROTTLE_RATES = {"cero": "0/min"}

    cero = _Cero()
    assert not cero.allow_request(_peticion(1), SimpleNamespace(throttle_scope="cero"))
    assert cero.history == []
    assert cero.wait() == 60.0

    # Espera acotada a [0, ventana] aunque la marca más antigua sea posterior a `now`.
    limite.duration, limite.num_requests, limite.now = 60, 1, 100.0
    limite.history = [130.0]
    assert limite.wait() == 60.0
    limite.history = [10.0]
    assert limite.wait() == 0.0
    limite.history = [1.0, 2.0]
    assert limite.wait() is None


def test_TKT043_08_formato_del_historial() -> None:
    assert throttling._marcas("{1.5,3,2.25}") == [3.0, 2.25, 1.5]
    assert throttling._marcas("{}") == []
    assert throttling._marcas(None) == []


@pytest.mark.parametrize("frecuencia", [1, 200])
def test_TKT043_09_una_consulta_por_peticion_con_o_sin_purga(monkeypatch, frecuencia: int) -> None:
    """Número de consultas fijo (1) permitida o denegada, toque o no la purga (tests N+1)."""
    monkeypatch.setattr(throttling, "FRECUENCIA_PURGA", frecuencia)
    for _ in range(12):  # 10 permitidas + 2 denegadas
        with CaptureQueriesContext(connection) as consultas:
            _permitir("panel-login", 99)
        assert len(consultas) == 1
