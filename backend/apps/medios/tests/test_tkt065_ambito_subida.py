"""TKT-065: la subida de medios usa el ámbito `panel-subida` (20/min por cuenta) del contrato.

Antes, `_VistaMediosMixta.initial` fijaba `panel-escritura` (120/min) para todo método no seguro y
`ListaMedios.post` cambiaba `throttle_scope` a `panel-subida` ya dentro del handler, cuando DRF
había ejecutado `check_throttles` en `initial()`: la cuota de subida nunca se aplicaba y una cuenta
podía subir 120 lotes de hasta 10 imágenes por minuto (RESOURCE-EXHAUSTION).

Estas pruebas recorren la pila HTTP real (sesión de panel, CSRF, permisos, limitador sobre
cache_limites en PostgreSQL) y comprueban además, contra `contracts/openapi.yaml`, el ámbito con
el que se limita cada operación de medios en el momento del check.
"""

from __future__ import annotations

import io
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
import yaml
from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.test import Client
from PIL import Image

from apps.core.throttling import LimitePorAmbito
from apps.cuentas.tests.conftest import CONTRASENA, crear_staff, problema

BASE = "/api/v1/panel/medios"
LIMITE_SUBIDA = 20
RAFAGA = 30


def _jpeg() -> io.BytesIO:
    buffer = io.BytesIO()
    Image.new("RGB", (1600, 1200), color=(10, 20, 30)).save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    buffer.name = "foto.jpg"
    return buffer


def _subir_vacio(cliente: Client) -> Any:
    """POST multipart sin archivos: pasa auth/permisos/limitador y la vista responde 400."""
    return cliente.post(BASE, {})


def _es_429_conforme(respuesta: Any) -> None:
    problema(respuesta, 429, "limite_tasa")
    assert 1 <= int(respuesta["Retry-After"]) <= 60


@pytest.mark.django_db
def test_TKT065_01_rafaga_de_subidas_limitada_a_20_por_minuto(cliente_editora: Client) -> None:
    """30 POST seguidos de la misma cuenta: 20 llegan a la vista y 10 reciben 429 limite_tasa.

    En main (ámbito panel-escritura, 120/min) las 30 llegaban a la vista."""
    codigos = []
    bloqueadas = []
    for _ in range(RAFAGA):
        respuesta = _subir_vacio(cliente_editora)
        codigos.append(respuesta.status_code)
        if respuesta.status_code == 429:
            bloqueadas.append(respuesta)
    assert codigos == [400] * LIMITE_SUBIDA + [429] * (RAFAGA - LIMITE_SUBIDA)
    for respuesta in bloqueadas:
        _es_429_conforme(respuesta)


@pytest.mark.django_db
def test_TKT065_02_subidas_reales_consumen_la_cuota_y_la_21a_se_rechaza(
    cliente_editora: Client,
) -> None:
    """Una subida aceptada (200) cuenta igual que las demás; la 21.a no llega a procesarse."""
    aceptada = cliente_editora.post(BASE, {"archivos": _jpeg()})
    assert aceptada.status_code == 200, aceptada.content
    assert aceptada.json()["resultados"][0]["resultado"] == "ACEPTADO"
    for _ in range(LIMITE_SUBIDA - 1):
        assert _subir_vacio(cliente_editora).status_code == 400
    rechazada = cliente_editora.post(BASE, {"archivos": _jpeg()})
    _es_429_conforme(rechazada)
    # Ningún efecto: solo existe el medio de la primera subida.
    listado = cliente_editora.get(BASE)
    assert listado.status_code == 200
    assert listado.json()["total"] == 1


@pytest.mark.django_db
def test_TKT065_03_agotar_subida_no_bloquea_lectura_ni_escritura(cliente_editora: Client) -> None:
    """La cuota de subida es independiente: con panel-subida agotado, las lecturas y las
    escrituras de medios siguen su propio ámbito (y una subida sigue sin pasar)."""
    medio_id = cliente_editora.post(BASE, {"archivos": _jpeg()}).json()["resultados"][0]["medio"][
        "id"
    ]
    for _ in range(LIMITE_SUBIDA - 1):
        _subir_vacio(cliente_editora)
    _es_429_conforme(_subir_vacio(cliente_editora))

    assert cliente_editora.get(BASE).status_code == 200
    assert cliente_editora.get(f"{BASE}/{medio_id}").status_code == 200
    assert cliente_editora.get(f"{BASE}/{medio_id}/usos").status_code == 200
    catalogar = cliente_editora.put(f"{BASE}/{medio_id}", {}, content_type="application/json")
    assert catalogar.status_code == 200, catalogar.content
    assert cliente_editora.post(f"{BASE}/{medio_id}/retirar").status_code == 200
    reactivar = cliente_editora.post(f"{BASE}/{medio_id}/reactivar")
    assert reactivar.status_code == 200, reactivar.content


@pytest.mark.django_db
def test_TKT065_04_la_cuota_de_subida_es_por_cuenta(cliente_editora: Client) -> None:
    """Otra cuenta conserva su cuota de subida aunque la primera la haya agotado."""
    for _ in range(LIMITE_SUBIDA):
        _subir_vacio(cliente_editora)
    _es_429_conforme(_subir_vacio(cliente_editora))

    otra = crear_staff("editora.dos")
    cliente = Client(raise_request_exception=False)
    respuesta = cliente.post(
        "/api/v1/panel/auth/login",
        {"usuario": otra.cuenta.usuario, "contrasena": CONTRASENA},
        content_type="application/json",
        REMOTE_ADDR="198.51.100.9",
    )
    assert respuesta.status_code == 200, respuesta.content
    assert _subir_vacio(cliente).status_code == 400


def _ambitos_del_contrato() -> dict[tuple[str, str], str]:
    ruta = Path(settings.BASE_DIR).parent / "contracts" / "openapi.yaml"
    documento = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    ambitos: dict[tuple[str, str], str] = {}
    for camino, operaciones in documento["paths"].items():
        if not camino.startswith(BASE):
            continue
        for metodo, operacion in operaciones.items():
            if isinstance(operacion, dict) and "x-limite-tasa" in operacion:
                ambitos[(metodo.upper(), camino.replace("{id}", "1"))] = operacion["x-limite-tasa"]
    return ambitos


@pytest.fixture
def ambitos_en_el_check(monkeypatch: pytest.MonkeyPatch) -> list[str | None]:
    """Registra el `throttle_scope` de la vista en el momento en que DRF consulta el limitador."""
    vistos: list[str | None] = []
    original = LimitePorAmbito.allow_request

    def espia(self: LimitePorAmbito, request: Any, view: Any) -> bool:
        vistos.append(getattr(view, "throttle_scope", None))
        return original(self, request, view)

    monkeypatch.setattr(LimitePorAmbito, "allow_request", espia)
    return vistos


@pytest.mark.django_db
def test_TKT065_05_cada_operacion_de_medios_se_limita_con_su_ambito_del_contrato(
    cliente_editora: Client, ambitos_en_el_check: list[str | None]
) -> None:
    """Para cada operación de /panel/medios del contrato, el ámbito activo cuando se ejecuta
    `check_throttles` es su `x-limite-tasa` (antes POST /panel/medios daba panel-escritura)."""
    esperados = _ambitos_del_contrato()
    assert ("POST", BASE) in esperados
    assert len(esperados) == 8
    for (metodo, camino), ambito in sorted(esperados.items()):
        ambitos_en_el_check.clear()
        # El cuerpo no importa: el limitador se consulta en initial(), antes de parsearlo.
        cliente_editora.generic(metodo, camino, "{}", content_type="application/json")
        assert ambitos_en_el_check == [ambito], (metodo, camino)


@pytest.mark.django_db
@pytest.mark.parametrize("metodo", ["HEAD", "OPTIONS"])
def test_TKT065_06_metodos_seguros_sin_operacion_usan_panel_lectura(
    cliente_editora: Client, ambitos_en_el_check: list[str | None], metodo: str
) -> None:
    cliente_editora.generic(metodo, BASE)
    assert ambitos_en_el_check == ["panel-lectura"]


# ---------------------------------------------------------------------------
# Ráfaga concurrente (limitador atómico de TKT-043): sesiones propias de la misma cuenta.
# ---------------------------------------------------------------------------
def _a_la_vez[T](n: int, funcion: Callable[[int], T]) -> list[T]:
    barrera = threading.Barrier(n)

    def tarea(i: int) -> T:
        try:
            barrera.wait(timeout=60)
            return funcion(i)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=n) as grupo:
        return list(grupo.map(tarea, range(n)))


@pytest.fixture
def _cache_vacia() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("_cache_vacia")
def test_TKT065_07_rafaga_concurrente_de_subidas_exacta() -> None:
    """30 subidas simultáneas de la misma cuenta (una sesión por hilo): 20 pasan y 10 x 429."""
    staff = crear_staff("editora.rafaga")
    clientes = []
    for i in range(RAFAGA):
        cliente = Client(raise_request_exception=False)
        respuesta = cliente.post(
            "/api/v1/panel/auth/login",
            {"usuario": staff.cuenta.usuario, "contrasena": CONTRASENA},
            content_type="application/json",
            REMOTE_ADDR=f"198.51.{i}.10",  # una red /24 por login: sin cuota panel-login común
        )
        assert respuesta.status_code == 200, respuesta.content
        clientes.append(cliente)

    respuestas = _a_la_vez(RAFAGA, lambda i: _subir_vacio(clientes[i]))
    codigos = sorted(r.status_code for r in respuestas)
    assert codigos == [400] * LIMITE_SUBIDA + [429] * (RAFAGA - LIMITE_SUBIDA)
    for respuesta in respuestas:
        if respuesta.status_code == 429:
            _es_429_conforme(respuesta)
