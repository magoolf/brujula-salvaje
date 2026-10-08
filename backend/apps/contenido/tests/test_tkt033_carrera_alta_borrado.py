"""TKT-033 AC_TKT033_02 (F-032-01): carrera alta/DELETE con transacciones REALES.

Reproduce el escenario de la QA de TKT-032: en cada ronda, 3 altas que referencian un borrador y
1 DELETE de ese borrador salen a la vez (barrera) por HTTP, cada una en su hilo con su propia
conexión y su propia transacción con COMMIT (`django_db(transaction=True)`). Antes: IntegrityError
23503 en el COMMIT (FK DEFERRABLE INITIALLY DEFERRED), `ProtectedError` en el DELETE y
`DoesNotExist` al serializar el alta → 500. Ahora las altas bloquean el referenciado con
`FOR KEY SHARE` y el DELETE toma `FOR UPDATE`: quien llega segundo espera y responde un código
documentado (alta 201 o 400 `validacion`; DELETE 204 o 409 `dependencia_bloqueante`).

Requisitos: 0 respuestas 5xx, 0 `excepcion_no_controlada` en el log, ningún hilo colgado
(interbloqueo → 500 `deadlock detected`, o un hilo que no termina en el plazo) y resultados
coherentes con la BD.
"""

from __future__ import annotations

import threading
from collections import Counter
from collections.abc import Callable
from http.cookies import SimpleCookie
from typing import Any

import pytest
from django.db import connections
from django.test import Client

from apps.contenido import services
from apps.contenido.models import Contenido, Destino, Itinerario, TipoAventura, TipoContenido
from apps.cuentas.tests.conftest import crear_staff, entrar

T = TipoContenido
BASE = "/api/v1/panel/contenidos"
RONDAS = 16
PLAZO_S = 60

pytestmark = pytest.mark.django_db(transaction=True)

Peticion = Callable[[Client], Any]


def _post(ruta: str, cuerpo: dict[str, Any]) -> Peticion:
    return lambda c: c.post(f"{BASE}/{ruta}", cuerpo, content_type="application/json")


def _delete(ruta: str, contenido: Contenido) -> Peticion:
    return lambda c: c.delete(f"{BASE}/{ruta}/{contenido.pk}?version={contenido.version}")


def _a_la_vez(cookies: SimpleCookie, peticiones: list[Peticion]) -> list[tuple[int, Any]]:
    """Lanza las peticiones a la vez, cada una en su hilo (conexión y transacción propias)."""
    barrera = threading.Barrier(len(peticiones))
    resultados: list[tuple[int, Any] | None] = [None] * len(peticiones)
    fallos: list[BaseException] = []

    def trabajar(indice: int, peticion: Peticion) -> None:
        cliente = Client(raise_request_exception=False)
        cliente.cookies = SimpleCookie(cookies.output(header="", sep=";"))
        try:
            barrera.wait(PLAZO_S)
            respuesta = peticion(cliente)
            cuerpo = (
                respuesta.json()
                if respuesta.get("Content-Type", "").endswith("json") and respuesta.content
                else None
            )
            resultados[indice] = (respuesta.status_code, cuerpo)
        except BaseException as exc:  # pragma: no cover - solo si la prueba falla
            fallos.append(exc)
        finally:
            connections.close_all()

    hilos = [threading.Thread(target=trabajar, args=(i, p)) for i, p in enumerate(peticiones)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(PLAZO_S)
    assert not any(h.is_alive() for h in hilos), "hilo colgado: posible interbloqueo"
    assert not fallos, fallos
    assert all(r is not None for r in resultados)
    return [r for r in resultados if r is not None]


@pytest.fixture
def sesion(logs_json: Callable[[], list[dict[str, Any]]]) -> tuple[int, SimpleCookie]:
    staff = crear_staff("editora.carrera")
    cliente = Client(raise_request_exception=False)
    entrar(cliente, staff)
    return staff.cuenta.pk, cliente.cookies


def _sin_excepciones(logs: Callable[[], list[dict[str, Any]]]) -> None:
    eventos = [linea for linea in logs() if linea.get("event") == "excepcion_no_controlada"]
    assert eventos == [], eventos[:3]


# Códigos documentados que puede dar cada petición de la carrera. 409 `conflicto_version` solo
# si una espera de bloqueo supera `lock_timeout` (p. ej. el host se detiene unos segundos): es
# reintentable y no ha cambiado nada (manejador global de `core.exceptions`, TKT-035).
CODIGOS_ALTA = {(201, None), (400, "validacion"), (409, "conflicto_version")}
CODIGOS_BORRADO = {(204, None), (409, "dependencia_bloqueante"), (409, "conflicto_version")}


def _clasificar(
    resultados: list[tuple[int, Any]], nombres: tuple[str, ...], estados: Counter[Any], ronda: int
) -> list[tuple[int, str | None]]:
    clasificados = []
    for (codigo, cuerpo), nombre in zip(resultados, nombres, strict=True):
        assert codigo < 500, (ronda, nombre, codigo, cuerpo)
        clave = (codigo, cuerpo["code"] if codigo >= 400 else None)
        permitidos = CODIGOS_BORRADO if nombre == "delete" else CODIGOS_ALTA
        assert clave in permitidos, (ronda, nombre, clave, cuerpo)
        estados[(nombre, *clave)] += 1
        clasificados.append(clave)
    return clasificados


def test_AC_TKT033_02_carrera_altas_que_referencian_un_destino_y_su_delete(
    sesion: tuple[int, SimpleCookie], logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    actor_id, cookies = sesion
    estados: Counter[Any] = Counter()
    for ronda in range(RONDAS):
        destino = services.crear_borrador(T.DESTINO, actor_id, {"titulo": f"Destino {ronda}"})
        peticiones = [
            _post("itinerarios", {"titulo": f"Itinerario A {ronda}", "destino_id": destino.pk}),
            _post("itinerarios", {"titulo": f"Itinerario B {ronda}", "destino_id": destino.pk}),
            _post("guias", {"titulo": f"Guía {ronda}", "destinos_ids": [destino.pk]}),
            _delete("destinos", destino),
        ]
        resultados = _a_la_vez(cookies, peticiones)
        it_a, it_b, _guia, borrado = _clasificar(
            resultados, ("itinerario", "itinerario", "guia", "delete"), estados, ronda
        )
        existe = Destino.objects.filter(pk=destino.pk).exists()
        referencias = Itinerario.objects.filter(destino_id=destino.pk).count()
        # Coherencia con la BD: cada 201 de itinerario es un itinerario que lo referencia; si se
        # borró, ninguno pudo quedar (los que llegaron después respondieron 400).
        assert referencias == [it_a[0], it_b[0]].count(201)
        assert existe == (borrado[0] != 204)
        if borrado == (204, None):
            assert referencias == 0
        if borrado == (409, "dependencia_bloqueante"):
            assert referencias >= 1
    _sin_excepciones(logs_json)
    print("carrera destino:", dict(sorted(estados.items())))  # noqa: T201 (evidencia en -s)


def test_AC_TKT033_02_carrera_altas_que_referencian_un_tipo_y_su_delete(
    sesion: tuple[int, SimpleCookie], logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    actor_id, cookies = sesion
    estados: Counter[Any] = Counter()
    for ronda in range(RONDAS):
        tipo = services.crear_borrador(T.TIPO, actor_id, {"titulo": f"Tipo {ronda}"})
        peticiones = [
            _post(
                "destinos",
                {
                    "titulo": f"Destino {ronda}",
                    "tipos_ids": [tipo.pk],
                    "tipo_principal_id": tipo.pk,
                },
            ),
            _post("itinerarios", {"titulo": f"Itinerario {ronda}", "tipos_ids": [tipo.pk]}),
            _post("guias", {"titulo": f"Guía {ronda}", "tipos_ids": [tipo.pk]}),
            _delete("tipos-aventura", tipo),
        ]
        resultados = _a_la_vez(cookies, peticiones)
        destino, itinerario, _guia, borrado = _clasificar(
            resultados, ("destino", "itinerario", "guia", "delete"), estados, ronda
        )
        existe = TipoAventura.objects.filter(pk=tipo.pk).exists()
        assert existe == (borrado[0] != 204)
        if borrado == (204, None):
            assert destino[0] != 201 and itinerario[0] != 201
        if borrado == (409, "dependencia_bloqueante"):
            assert 201 in {destino[0], itinerario[0]}
    _sin_excepciones(logs_json)
    print("carrera tipo:", dict(sorted(estados.items())))  # noqa: T201 (evidencia en -s)
