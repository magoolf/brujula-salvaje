"""TKT-037 con transacciones REALES de PostgreSQL (`django_db(transaction=True)`): cada petición
corre en su hilo, con su conexión y su transacción con COMMIT.

- AC_TKT037_05 (OBS-02 de la QA de TKT-035, RULE-007): la retirada de un país (PUT activo=false,
  `FOR NO KEY UPDATE` de la fila) y las altas, ediciones y publicaciones de contenido que lo
  referencian se serializan. Antes el contenido solo tomaba el `FOR KEY SHARE` de la FK, que no
  choca con la retirada: el alta y la publicación no esperaban, no miraban `activo` y la retirada
  no veía la publicación aún sin confirmar → destinos (también PUBLICADOS) con el país retirado.
  Ahora el contenido lee el país con `FOR SHARE`: quien llega segundo espera y ve lo que hizo el
  primero. Pruebas deterministas (una transacción retenida abierta) y una carrera con barrera.
- AC_TKT037_06 (OBS-1 de la QA de TKT-033): dos PUT concurrentes de contenidos relacionados entre
  sí (A↔B) que cambian su título. Antes: interbloqueo (40P01 → 409 `conflicto_version`, 15/40 en
  la QA). Ahora bloquean en orden ascendente de id y ambos responden 200.

Requisitos comunes: 0 respuestas 5xx, 0 `excepcion_no_controlada` y ningún hilo colgado.
"""

from __future__ import annotations

import threading
from collections import Counter
from collections.abc import Callable
from datetime import date, timedelta
from http.cookies import SimpleCookie
from typing import Any

import pytest
from django.db import connections, transaction
from django.test import Client

from apps.catalogos import services as catalogos
from apps.catalogos.models import Continente, Licencia, Pais, Region
from apps.contenido import reglas, services
from apps.contenido.models import Contenido, Destino, EstadoEditorial, TipoContenido
from apps.contenido.tests import publicos
from apps.cuentas.tests.conftest import crear_staff, entrar

T = TipoContenido
E = EstadoEditorial
BASE = "/api/v1/panel/contenidos"
TAX = "/api/v1/panel/taxonomias"
AYER = date.today() - timedelta(days=1)
RONDAS = 12
RONDAS_RELACIONADOS = 20
PLAZO_S = 60
ESPERA_BLOQUEADA_S = 1.0  # < lock_timeout (5 s app_migrator): el hilo bloqueado sigue esperando

pytestmark = pytest.mark.django_db(transaction=True)

Tarea = Callable[[Client], tuple[int, Any]]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _http(respuesta: Any) -> tuple[int, Any]:
    cuerpo = (
        respuesta.json()
        if respuesta.get("Content-Type", "").endswith("json") and respuesta.content
        else None
    )
    return respuesta.status_code, cuerpo


def _cliente(cookies: SimpleCookie) -> Client:
    cliente = Client(raise_request_exception=False)
    cliente.cookies = SimpleCookie(cookies.output(header="", sep=";"))
    return cliente


def _a_la_vez(cookies: SimpleCookie, tareas: list[Tarea]) -> list[tuple[int, Any]]:
    """Lanza las tareas a la vez (barrera), cada una en su hilo (conexión y transacción propias)."""
    barrera = threading.Barrier(len(tareas))
    resultados: list[tuple[int, Any] | None] = [None] * len(tareas)
    fallos: list[BaseException] = []

    def trabajar(indice: int, tarea: Tarea) -> None:
        cliente = _cliente(cookies)
        try:
            barrera.wait(PLAZO_S)
            resultados[indice] = tarea(cliente)
        except BaseException as exc:  # pragma: no cover - solo si la prueba falla
            fallos.append(exc)
        finally:
            connections.close_all()

    hilos = [threading.Thread(target=trabajar, args=(i, t)) for i, t in enumerate(tareas)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(PLAZO_S)
    assert not any(h.is_alive() for h in hilos), "hilo colgado: posible interbloqueo"
    assert not fallos, fallos
    assert all(r is not None for r in resultados)
    return [r for r in resultados if r is not None]


class _Retenida:
    """Ejecuta `operacion` en una transacción de otro hilo y la deja ABIERTA (con sus bloqueos)
    hasta `confirmar()`."""

    def __init__(self, operacion: Callable[[], Any]) -> None:
        self._hecha = threading.Event()
        self._confirmar = threading.Event()
        self._fallos: list[BaseException] = []

        def trabajar() -> None:
            try:
                with transaction.atomic():
                    operacion()
                    self._hecha.set()
                    self._confirmar.wait(PLAZO_S)
            except BaseException as exc:  # pragma: no cover - solo si la prueba falla
                self._fallos.append(exc)
                self._hecha.set()
            finally:
                connections.close_all()

        self._hilo = threading.Thread(target=trabajar)

    def __enter__(self) -> _Retenida:
        self._hilo.start()
        assert self._hecha.wait(PLAZO_S)
        assert not self._fallos, self._fallos
        return self

    def confirmar(self) -> None:
        self._confirmar.set()
        self._hilo.join(PLAZO_S)
        assert not self._hilo.is_alive()
        assert not self._fallos, self._fallos

    def __exit__(self, *_exc: object) -> None:
        self._confirmar.set()
        self._hilo.join(PLAZO_S)


class _EnSegundoPlano:
    """Una petición HTTP en otro hilo, para comprobar que espera un bloqueo."""

    def __init__(self, cookies: SimpleCookie, tarea: Tarea) -> None:
        self.resultado: tuple[int, Any] | None = None

        def trabajar() -> None:
            try:
                self.resultado = tarea(_cliente(cookies))
            finally:
                connections.close_all()

        self._hilo = threading.Thread(target=trabajar)
        self._hilo.start()

    def sigue_esperando(self) -> bool:
        self._hilo.join(ESPERA_BLOQUEADA_S)
        return self._hilo.is_alive()

    def esperar(self) -> tuple[int, Any]:
        self._hilo.join(PLAZO_S)
        assert not self._hilo.is_alive(), "hilo colgado"
        assert self.resultado is not None
        return self.resultado


@pytest.fixture
def sesion(logs_json: Callable[[], list[dict[str, Any]]]) -> tuple[int, SimpleCookie]:
    staff = crear_staff("editora.tkt037")
    cliente = Client(raise_request_exception=False)
    entrar(cliente, staff)
    return staff.cuenta.pk, cliente.cookies


def _sin_excepciones(logs: Callable[[], list[dict[str, Any]]]) -> None:
    eventos = [linea for linea in logs() if linea.get("event") == "excepcion_no_controlada"]
    assert eventos == [], eventos[:3]


def _region() -> Region:
    return Region.objects.create(
        nombre="Región carrera", slug="region-carrera", continente=Continente.ASIA
    )


def _pais(region: Region, n: int) -> Pais:
    iso = f"{chr(65 + n // 26 % 26)}{chr(65 + n % 26)}"
    return Pais.objects.create(
        nombre=f"País carrera {n}", slug=f"pais-carrera-{n}", codigo_iso2=iso, region=region
    )


def _entrada_pais(pais: Pais, activo: bool) -> dict[str, Any]:
    return {
        "nombre": pais.nombre,
        "slug": pais.slug,
        "codigo_iso2": pais.codigo_iso2,
        "region_id": pais.region_id,
        "activo": activo,
    }


def _put_pais(pais: Pais, activo: bool) -> Tarea:
    return lambda c: _http(
        c.put(
            f"{TAX}/paises/{pais.pk}", _entrada_pais(pais, activo), content_type="application/json"
        )
    )


def _publicar(contenido: Contenido) -> Tarea:
    return lambda c: _http(
        c.post(
            f"{BASE}/destinos/{contenido.pk}/publicar",
            {"version": contenido.version},
            content_type="application/json",
        )
    )


def _alta(titulo: str, pais: Pais) -> Tarea:
    return lambda c: _http(
        c.post(
            f"{BASE}/destinos",
            {"titulo": titulo, "pais_id": pais.pk},
            content_type="application/json",
        )
    )


def _put_destino(contenido: Contenido, cuerpo: dict[str, Any]) -> Tarea:
    return lambda c: _http(
        c.put(
            f"{BASE}/destinos/{contenido.pk}",
            {"version": contenido.version, **cuerpo},
            content_type="application/json",
        )
    )


def _clave(resultado: tuple[int, Any]) -> tuple[int, str | None]:
    codigo, cuerpo = resultado
    return codigo, (cuerpo or {}).get("code") if codigo >= 400 else None


def _mundo_publicable() -> tuple[Region, Any]:
    """Región, y un tipo publicado con 3 destinos publicados (RULE-002/RULE-006 por afinidad)."""
    # Las pruebas transaccionales vacían la BD al terminar: los medios necesitan una licencia.
    Licencia.objects.get_or_create(
        codigo="CC-BY-4.0",
        defaults={
            "nombre": "CC BY 4.0",
            "requiere_atribucion": True,
            "compatible_publicacion": True,
        },
    )
    region = _region()
    relleno = _pais(region, 600)
    # Atómico: el tipo principal del destino se inserta antes que su M2M (FK DEFERRABLE).
    with transaction.atomic():
        tipo = publicos.tipo("Tipo carrera")
        for i in range(3):
            publicos.destino(f"Relleno carrera {i}", tipos=[tipo], pais_=relleno)
    return region, tipo


def _borrador_publicable(actor_id: int, tipo: Any, pais: Pais, sufijo: str) -> Contenido:
    datos = {
        "titulo": f"Destino carrera {sufijo}",
        "pais_id": pais.pk,
        "tipos_ids": [tipo.pk],
        "tipo_principal_id": tipo.pk,
        "resumen": "Resumen corto",
        "descripcion_experta": "palabra " * 600,
        "dificultad": 3,
        "meses_mejor_epoca": [1, 2],
        "duracion_min_dias": 2,
        "duracion_max_dias": 5,
        "nivel_presupuesto": 2,
        "clima": "Templado",
        "como_llegar": "En bus",
        "seguridad_riesgos": "Ninguno relevante",
        "sostenibilidad": "Lleva tu basura",
        "latitud": 6.5,
        "longitud": -72.3,
        "fecha_ultima_revision": AYER,
        "seo_descripcion": f"SEO única del destino carrera {sufijo}",
        "portada_id": publicos.medio().pk,
        "galeria_ids": [publicos.medio().pk for _ in range(3)],
    }
    return services.crear_borrador(T.DESTINO, actor_id, datos)


def _publicados_con_catalogo_retirado() -> int:
    return (
        Destino.objects.filter(contenido__estado_editorial=E.PUBLICADO, pais__activo=False).count()
        + Destino.objects.filter(
            contenido__estado_editorial=E.PUBLICADO, pais__region__activo=False
        ).count()
    )


# ---------------------------------------------------------------------------
# AC_TKT037_05 — retirada del país frente a altas, ediciones y publicaciones
# ---------------------------------------------------------------------------
def test_AC_TKT037_05_alta_espera_a_la_retirada_en_curso_y_la_rechaza(
    sesion: tuple[int, SimpleCookie], logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    actor_id, cookies = sesion
    pais = _pais(_region(), 1)
    with _Retenida(lambda: catalogos.actualizar_pais(pais.pk, actor_id, {"activo": False})) as r:
        alta = _EnSegundoPlano(cookies, _alta("Alta en carrera", pais))
        assert alta.sigue_esperando(), "el alta no esperó a la retirada en curso (FOR SHARE)"
        r.confirmar()
        codigo, cuerpo = alta.esperar()
    assert (codigo, cuerpo["code"]) == (400, "validacion"), cuerpo
    assert cuerpo["errors"] == {"pais_id": [reglas.MENSAJE_PAIS_RETIRADO]}
    assert not Destino.objects.filter(pais=pais).exists()
    _sin_excepciones(logs_json)


def test_AC_TKT037_05_edicion_que_asigna_el_pais_espera_a_la_retirada_y_la_rechaza(
    sesion: tuple[int, SimpleCookie],
) -> None:
    actor_id, cookies = sesion
    region = _region()
    pais, otro = _pais(region, 1), _pais(region, 2)
    borrador = services.crear_borrador(T.DESTINO, actor_id, {"titulo": "B", "pais_id": otro.pk})
    with _Retenida(lambda: catalogos.actualizar_pais(pais.pk, actor_id, {"activo": False})) as r:
        put = _EnSegundoPlano(cookies, _put_destino(borrador, {"titulo": "B", "pais_id": pais.pk}))
        assert put.sigue_esperando(), "la edición no esperó a la retirada en curso"
        r.confirmar()
        assert _clave(put.esperar()) == (400, "validacion")
    assert Destino.objects.get(pk=borrador.pk).pais_id == otro.pk


def test_AC_TKT037_05_publicacion_espera_a_la_retirada_en_curso_y_la_rechaza(
    sesion: tuple[int, SimpleCookie],
) -> None:
    actor_id, cookies = sesion
    region, tipo = _mundo_publicable()
    pais = _pais(region, 1)
    borrador = _borrador_publicable(actor_id, tipo, pais, "retenida")
    with _Retenida(lambda: catalogos.actualizar_pais(pais.pk, actor_id, {"activo": False})) as r:
        publicacion = _EnSegundoPlano(cookies, _publicar(borrador))
        assert publicacion.sigue_esperando(), "la publicación no esperó a la retirada en curso"
        r.confirmar()
        codigo, cuerpo = publicacion.esperar()
    assert (codigo, cuerpo["code"]) == (422, "publicacion_invalida"), cuerpo
    assert cuerpo["errors"]["pais_id"] == [reglas.MENSAJE_PAIS_RETIRADO]
    assert Contenido.objects.get(pk=borrador.pk).estado_editorial == E.BORRADOR


def test_AC_TKT037_05_retirada_espera_a_la_publicacion_en_curso_y_la_bloquea(
    sesion: tuple[int, SimpleCookie],
) -> None:
    actor_id, cookies = sesion
    region, tipo = _mundo_publicable()
    pais = _pais(region, 1)
    borrador = _borrador_publicable(actor_id, tipo, pais, "publicada")
    with _Retenida(
        lambda: services.publicar(T.DESTINO, borrador.pk, actor_id, borrador.version, None)
    ) as p:
        retirada = _EnSegundoPlano(cookies, _put_pais(pais, activo=False))
        assert retirada.sigue_esperando(), "la retirada no esperó a la publicación en curso"
        p.confirmar()
        codigo, cuerpo = retirada.esperar()
    assert (codigo, cuerpo["code"]) == (409, "dependencia_bloqueante"), cuerpo
    assert [u["id"] for u in cuerpo["usos"]] == [borrador.pk]
    assert Pais.objects.get(pk=pais.pk).activo
    assert _publicados_con_catalogo_retirado() == 0


RETIRO = {(200, None), (409, "dependencia_bloqueante"), (409, "conflicto_version")}
PUBLICACION = {(200, None), (422, "publicacion_invalida"), (409, "conflicto_version")}
ALTA = {(201, None), (400, "validacion"), (409, "conflicto_version")}
EDICION = {(200, None), (400, "validacion"), (409, "conflicto_version")}


def test_AC_TKT037_05_carrera_retirada_del_pais_frente_a_altas_ediciones_y_publicacion(
    sesion: tuple[int, SimpleCookie], logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    actor_id, cookies = sesion
    region, tipo = _mundo_publicable()
    estados: Counter[Any] = Counter()
    for ronda in range(RONDAS):
        pais = _pais(region, 10 + ronda)
        otro = _pais(region, 100 + ronda)
        publicable = _borrador_publicable(actor_id, tipo, pais, f"r{ronda}")
        editable = services.crear_borrador(
            T.DESTINO, actor_id, {"titulo": f"Editable {ronda}", "pais_id": otro.pk}
        )
        tareas = [
            _put_pais(pais, activo=False),
            _publicar(publicable),
            _alta(f"Alta A {ronda}", pais),
            _alta(f"Alta B {ronda}", pais),
            _put_destino(editable, {"titulo": f"Editable {ronda}", "pais_id": pais.pk}),
        ]
        nombres = ("retiro", "publicacion", "alta", "alta", "edicion")
        permitidos = (RETIRO, PUBLICACION, ALTA, ALTA, EDICION)
        resultados = _a_la_vez(cookies, tareas)
        claves = []
        for resultado, nombre, validos in zip(resultados, nombres, permitidos, strict=True):
            assert resultado[0] < 500, (ronda, nombre, resultado)
            clave = _clave(resultado)
            assert clave in validos, (ronda, nombre, resultado)
            estados[(nombre, *clave)] += 1
            claves.append(clave)
        retiro, publicacion = claves[0], claves[1]
        pais.refresh_from_db()
        publicado = Contenido.objects.get(pk=publicable.pk).estado_editorial == E.PUBLICADO
        # RULE-007: nunca ambos. La retirada ve la publicación confirmada antes (409) y la
        # publicación ve la retirada confirmada antes (422).
        assert not (retiro == (200, None) and publicacion == (200, None)), (ronda, claves)
        assert pais.activo == (retiro != (200, None))
        assert publicado == (publicacion == (200, None))
        if publicado:
            assert retiro[0] == 409, (ronda, claves)
        assert _publicados_con_catalogo_retirado() == 0, ronda
    _sin_excepciones(logs_json)
    print("carrera RULE-007:", dict(sorted(estados.items())))  # noqa: T201 (evidencia en -s)


# ---------------------------------------------------------------------------
# AC_TKT037_06 — ediciones concurrentes de contenidos relacionados entre sí (OBS-1)
# ---------------------------------------------------------------------------
def test_AC_TKT037_06_ediciones_cruzadas_a_b_no_se_interbloquean(
    sesion: tuple[int, SimpleCookie], logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    actor_id, cookies = sesion
    estados: Counter[Any] = Counter()
    for ronda in range(RONDAS_RELACIONADOS):
        a = services.crear_borrador(T.DESTINO, actor_id, {"titulo": f"A {ronda}"})
        b = services.crear_borrador(T.DESTINO, actor_id, {"titulo": f"B {ronda}"})
        tareas = [
            _put_destino(
                a, {"titulo": f"A {ronda} nuevo", "relaciones": [{"tipo": "DESTINO", "id": b.pk}]}
            ),
            _put_destino(
                b, {"titulo": f"B {ronda} nuevo", "relaciones": [{"tipo": "DESTINO", "id": a.pk}]}
            ),
        ]
        for resultado in _a_la_vez(cookies, tareas):
            assert resultado[0] < 500, (ronda, resultado)
            estados[_clave(resultado)] += 1
    interbloqueos = [
        linea
        for linea in logs_json()
        if linea.get("event") == "conflicto_concurrencia_bd" and linea.get("sqlstate") == "40P01"
    ]
    print("ediciones A<->B:", dict(estados), "40P01:", len(interbloqueos))  # noqa: T201
    assert interbloqueos == []
    assert estados == Counter({(200, None): 2 * RONDAS_RELACIONADOS})
    _sin_excepciones(logs_json)
