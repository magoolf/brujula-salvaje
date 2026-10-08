"""TKT-035 con transacciones REALES de PostgreSQL (`django_db(transaction=True)`): cada petición o
borrado corre en su hilo, con su conexión y su transacción con COMMIT.

- AC_TKT035_05: un PUT de taxonomía que espera un bloqueo más que `lock_timeout` (55P03) o al que
  PostgreSQL elige como víctima de un interbloqueo (40P01) responde 409 `conflicto_version`
  documentado (traducción global de core), nunca 500, y la reintentona funciona.
- AC_TKT035_06: carrera "borrado de un catálogo (país / categoría de guía) frente a altas de
  contenido que lo referencian y a su retirada (PUT activo=false)". La API no expone DELETE de
  catálogos (retirar es `activo=false`, contrato FEAT-044): el borrado físico solo puede venir de
  fuera de la API (ORM/ops), y aquí se hace así. Antes, un alta cuya FK (DEFERRABLE INITIALLY
  DEFERRED) se comprobaba en el COMMIT tras el borrado del país daba 500 (IntegrityError 23503);
  y un PUT de retirada que leía la fila antes del borrado la RESUCITABA (el UPDATE de 0 filas de
  `save()` pasaba a INSERT). Ahora: 0 respuestas 5xx, 0 `excepcion_no_controlada` y resultados
  coherentes con la BD (el PUT bloquea la fila: Regla 06).
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from collections.abc import Callable
from http.cookies import SimpleCookie
from typing import Any

import pytest
from django.db import DatabaseError, IntegrityError, connection, connections, transaction
from django.db.models import ProtectedError
from django.test import Client

from apps.catalogos.models import CategoriaGuia, Continente, Pais, Region
from apps.contenido.models import Destino, Guia
from apps.cuentas.tests.conftest import crear_staff, entrar

pytestmark = pytest.mark.django_db(transaction=True)

TAX = "/api/v1/panel/taxonomias"
CONT = "/api/v1/panel/contenidos"
RONDAS = 12
RETARDOS_S = (0.0, 0.02, 0.05, 0.08, 0.12, 0.2)
PLAZO_S = 60
LOCK_TIMEOUT_S = 5  # ALTER ROLE app_migrator SET lock_timeout = '5s' (infra/db/init)

Tarea = Callable[[Client], tuple[int | str, Any]]


def _http(respuesta: Any) -> tuple[int, Any]:
    cuerpo = (
        respuesta.json()
        if respuesta.get("Content-Type", "").endswith("json") and respuesta.content
        else None
    )
    return respuesta.status_code, cuerpo


def _a_la_vez(cookies: SimpleCookie, tareas: list[Tarea]) -> list[tuple[int | str, Any]]:
    """Lanza las tareas a la vez (barrera), cada una en su hilo (conexión y transacción propias)."""
    barrera = threading.Barrier(len(tareas))
    resultados: list[tuple[int | str, Any] | None] = [None] * len(tareas)
    fallos: list[BaseException] = []

    def trabajar(indice: int, tarea: Tarea) -> None:
        cliente = Client(raise_request_exception=False)
        cliente.cookies = SimpleCookie(cookies.output(header="", sep=";"))
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


def _sesion(usuario: str) -> SimpleCookie:
    cliente = Client(raise_request_exception=False)
    entrar(cliente, crear_staff(usuario))
    return cliente.cookies


def _cliente(cookies: SimpleCookie) -> Client:
    cliente = Client(raise_request_exception=False)
    cliente.cookies = SimpleCookie(cookies.output(header="", sep=";"))
    return cliente


def _eventos(logs: Callable[[], list[dict[str, Any]]], nombre: str) -> list[dict[str, Any]]:
    return [linea for linea in logs() if linea.get("event") == nombre]


def _region(sufijo: str) -> Region:
    return Region.objects.create(
        nombre=f"Región {sufijo}", slug=f"region-{sufijo}", continente=Continente.ASIA
    )


def _pais(region: Region, sufijo: str, iso: str) -> Pais:
    return Pais.objects.create(
        nombre=f"País {sufijo}", slug=f"pais-{sufijo}", codigo_iso2=iso, region=region
    )


def _entrada_pais(pais: Pais, **cambios: Any) -> dict[str, Any]:
    return {
        "nombre": pais.nombre,
        "slug": pais.slug,
        "codigo_iso2": pais.codigo_iso2,
        "region_id": pais.region_id,
        "activo": pais.activo,
    } | cambios


def _conflicto(estado: int | str, cuerpo: Any) -> None:
    assert estado == 409, cuerpo
    assert cuerpo["code"] == "conflicto_version"
    assert len(cuerpo["trace_id"]) == 32


class _Bloqueador(threading.Thread):
    """Otra transacción (conexión propia) que bloquea filas con FOR UPDATE hasta `soltar`."""

    def __init__(self, sql: list[tuple[str, list[Any]]], antes_de_cada: Callable[[int], None]):
        super().__init__()
        self.sql = sql
        self.antes_de_cada = antes_de_cada
        self.listo = threading.Event()
        self.soltar = threading.Event()
        self.error: BaseException | None = None

    def run(self) -> None:
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                for indice, (sentencia, parametros) in enumerate(self.sql):
                    self.antes_de_cada(indice)
                    cursor.execute(sentencia, parametros)
                    if indice == 0:
                        self.listo.set()
                self.soltar.wait(PLAZO_S)
        except BaseException as exc:  # pragma: no cover - solo si la prueba falla
            self.error = exc
            self.listo.set()
        finally:
            connections.close_all()


def test_AC_TKT035_05_put_de_pais_que_espera_mas_que_lock_timeout_es_409_conflicto_version(
    logs_json: Callable[[], list[dict[str, Any]]],
) -> None:
    cliente = _cliente(_sesion("editora.bloqueo"))
    pais = _pais(_region("bloqueo"), "bloqueo", "QB")
    bloqueador = _Bloqueador(
        [("SELECT id FROM pais WHERE id = %s FOR UPDATE", [pais.pk])], lambda _i: None
    )
    bloqueador.start()
    try:
        assert bloqueador.listo.wait(PLAZO_S)
        inicio = time.monotonic()
        estado, cuerpo = _http(
            cliente.put(
                f"{TAX}/paises/{pais.pk}",
                _entrada_pais(pais, nombre="País renombrado"),
                content_type="application/json",
            )
        )
        esperado = time.monotonic() - inicio
    finally:
        bloqueador.soltar.set()
        bloqueador.join(PLAZO_S)
    assert bloqueador.error is None
    _conflicto(estado, cuerpo)
    assert esperado >= LOCK_TIMEOUT_S - 0.5  # esperó el lock_timeout del rol, no falló antes
    assert [e["sqlstate"] for e in _eventos(logs_json, "conflicto_concurrencia_bd")] == ["55P03"]
    assert _eventos(logs_json, "excepcion_no_controlada") == []
    pais.refresh_from_db()
    assert pais.nombre == "País bloqueo"  # no cambió nada
    # Reintento tras liberarse el bloqueo: se aplica.
    reintento = cliente.put(
        f"{TAX}/paises/{pais.pk}",
        _entrada_pais(pais, nombre="País renombrado"),
        content_type="application/json",
    )
    assert reintento.status_code == 200, reintento.content
    assert reintento.json()["nombre"] == "País renombrado"


def _esperar_a_que_espere_un_bloqueo(pid_excluido: int) -> None:
    """Hasta que OTRA sesión de la BD esté esperando un bloqueo de fila (pg_stat_activity).

    Se consulta dentro de la transacción del bloqueador: `pg_stat_clear_snapshot()` descarta la
    instantánea de estadísticas que PostgreSQL fija por transacción."""
    limite = time.monotonic() + PLAZO_S
    with connection.cursor() as cursor:
        while time.monotonic() < limite:
            cursor.execute("SELECT pg_stat_clear_snapshot()")
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                "AND wait_event_type = 'Lock' AND pid <> %s",
                [pid_excluido],
            )
            if cursor.fetchone()[0]:
                return
            time.sleep(0.05)
    raise AssertionError("ninguna sesión llegó a esperar el bloqueo")  # pragma: no cover


def test_AC_TKT035_05_put_de_pais_victima_de_un_interbloqueo_es_409_conflicto_version(
    logs_json: Callable[[], list[dict[str, Any]]],
) -> None:
    """Interbloqueo real: el PUT que mueve el país a la región R bloquea el país (FOR NO KEY
    UPDATE) y, en el COMMIT, la comprobación de la FK diferida pide FOR KEY SHARE sobre R, que otra
    transacción tiene con FOR UPDATE; esa transacción pide después el país. El PUT empezó a esperar
    antes, así que su `deadlock_timeout` vence primero y PostgreSQL lo aborta (40P01)."""
    cookies = _sesion("editora.interbloqueo")
    origen, destino_r = _region("origen"), _region("destino")
    pais = _pais(origen, "interbloqueo", "QI")
    pid_bloqueador: list[int] = []

    def antes_de_cada(indice: int) -> None:
        if indice == 0:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pid_bloqueador.append(cursor.fetchone()[0])
        else:
            _esperar_a_que_espere_un_bloqueo(pid_bloqueador[0])

    bloqueador = _Bloqueador(
        [
            ("SELECT id FROM region WHERE id = %s FOR UPDATE", [destino_r.pk]),
            ("SELECT id FROM pais WHERE id = %s FOR UPDATE", [pais.pk]),
        ],
        antes_de_cada,
    )
    bloqueador.start()
    try:
        assert bloqueador.listo.wait(PLAZO_S)
        estado, cuerpo = _http(
            _cliente(cookies).put(
                f"{TAX}/paises/{pais.pk}",
                _entrada_pais(pais, region_id=destino_r.pk),
                content_type="application/json",
            )
        )
    finally:
        bloqueador.soltar.set()
        bloqueador.join(PLAZO_S)
    assert bloqueador.error is None, bloqueador.error
    _conflicto(estado, cuerpo)
    assert [e["sqlstate"] for e in _eventos(logs_json, "conflicto_concurrencia_bd")] == ["40P01"]
    assert _eventos(logs_json, "excepcion_no_controlada") == []
    pais.refresh_from_db()
    assert pais.region_id == origen.pk


# ---------------------------------------------------------------------------
# AC_TKT035_06: borrado de catálogo vs altas de contenido que lo referencian y su retirada
# ---------------------------------------------------------------------------
CODIGOS_ALTA = {(201, None), (400, "validacion"), (409, "conflicto_version")}
CODIGOS_RETIRAR = {(200, None), (404, "no_encontrado"), (409, "conflicto_version")}
RESULTADOS_BORRADO = {"borrado", "protegido", "fk_en_commit", "conflicto"}

SQL_BORRAR = {
    "pais": "DELETE FROM pais WHERE id = %s",
    "categoria": "DELETE FROM categoria_guia WHERE id = %s",
}
CASOS = {
    "pais": (Pais, "destinos", "pais_id", Destino),
    "categoria": (CategoriaGuia, "guias", "categoria_id", Guia),
}


def _borrar(modelo: type[Pais] | type[CategoriaGuia], pk: int, retardo_s: float) -> Tarea:
    """Borrado físico fuera de la API (no hay DELETE de catálogos en el contrato). El retardo,
    distinto en cada ronda, hace que el borrado caiga en fases distintas de las altas."""

    def tarea(_cliente: Client) -> tuple[str, None]:
        time.sleep(retardo_s)
        try:
            with transaction.atomic():
                modelo.objects.filter(pk=pk).delete()
        except ProtectedError:
            return "protegido", None  # el alta llegó antes y Django lo vio
        except IntegrityError:
            return "fk_en_commit", None  # 23503 en el COMMIT: el alta confirmó entre medias
        except DatabaseError:
            return "conflicto", None  # 55P03/40P01
        return "borrado", None

    return tarea


def _alta(ruta: str, campo: str, valor: int, titulo: str) -> Tarea:
    return lambda c: _http(
        c.post(f"{CONT}/{ruta}", {"titulo": titulo, campo: valor}, content_type="application/json")
    )


def _retirar_pais(pais: Pais) -> Tarea:
    return lambda c: _http(
        c.put(
            f"{TAX}/paises/{pais.pk}",
            _entrada_pais(pais, activo=False),
            content_type="application/json",
        )
    )


def _retirar_categoria(categoria: CategoriaGuia) -> Tarea:
    entrada = {
        "nombre": categoria.nombre,
        "slug": categoria.slug,
        "descripcion": categoria.descripcion,
        "orden": categoria.orden,
        "activo": False,
    }
    return lambda c: _http(
        c.put(f"{TAX}/categorias-guia/{categoria.pk}", entrada, content_type="application/json")
    )


def _clave(estado: int | str, cuerpo: Any) -> tuple[int | str, str | None]:
    if isinstance(estado, str):
        return estado, None
    assert estado < 500, (estado, cuerpo)
    return estado, cuerpo["code"] if estado >= 400 else None


@pytest.mark.parametrize("caso", sorted(CASOS))
def test_AC_TKT035_06_borrado_de_catalogo_vs_altas_y_retirada_sin_5xx(
    caso: str, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    modelo, ruta, campo, subtipo = CASOS[caso]
    cookies = _sesion(f"editora.carrera.{caso}")
    region = _region(f"carrera-{caso}")
    estados: Counter[Any] = Counter()
    for ronda in range(RONDAS):
        if modelo is Pais:
            catalogo: Pais | CategoriaGuia = _pais(
                region, f"carrera-{ronda}", f"Q{chr(ord('A') + ronda)}"
            )
            retirar = _retirar_pais(catalogo)  # type: ignore[arg-type]
        else:
            catalogo = CategoriaGuia.objects.create(
                nombre=f"Categoría {ronda}", slug=f"categoria-carrera-{ronda}", descripcion="d"
            )
            retirar = _retirar_categoria(catalogo)  # type: ignore[arg-type]
        tareas = [
            _alta(ruta, campo, catalogo.pk, f"Alta A {caso} {ronda}"),
            _alta(ruta, campo, catalogo.pk, f"Alta B {caso} {ronda}"),
            retirar,
            _borrar(modelo, catalogo.pk, RETARDOS_S[ronda % len(RETARDOS_S)]),
        ]
        resultados = [_clave(*r) for r in _a_la_vez(cookies, tareas)]
        alta_a, alta_b, retirada, borrado = resultados
        assert alta_a in CODIGOS_ALTA and alta_b in CODIGOS_ALTA, resultados
        assert retirada in CODIGOS_RETIRAR, resultados
        assert borrado[0] in RESULTADOS_BORRADO, resultados
        for nombre, clave in zip(("alta", "alta", "retirar", "borrar"), resultados, strict=True):
            estados[(nombre, *clave)] += 1
        # Coherencia con la BD: cada 201 es un contenido que lo referencia; si se borró, ninguno.
        existe = modelo.objects.filter(pk=catalogo.pk).exists()
        referencias = subtipo.objects.filter(**{campo: catalogo.pk}).count()
        assert referencias == [alta_a[0], alta_b[0]].count(201), resultados
        assert existe == (borrado[0] != "borrado"), resultados
        if not existe:
            assert referencias == 0
    assert _eventos(logs_json, "excepcion_no_controlada") == []
    print(f"carrera {caso}:", dict(sorted(estados.items(), key=str)))  # noqa: T201 (evidencia -s)


@pytest.mark.parametrize("caso", sorted(CASOS))
def test_AC_TKT035_06_alta_cuyo_catalogo_se_borra_antes_de_su_commit_es_409_conflicto_version(
    caso: str, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """La ventana exacta que antes daba 500: el alta valida la referencia (el borrado aún no ha
    confirmado), inserta y, en el COMMIT, la FK diferida espera al borrado; este confirma y la FK
    falla (23503). Ahora 409 `conflicto_version` y el contenido no se crea."""
    modelo, ruta, campo, subtipo = CASOS[caso]
    cookies = _sesion(f"editora.ventana.{caso}")
    if modelo is Pais:
        catalogo: Pais | CategoriaGuia = _pais(_region("ventana"), "ventana", "QV")
    else:
        catalogo = CategoriaGuia.objects.create(
            nombre="Categoría ventana", slug="categoria-ventana", descripcion="d"
        )
    pid_bloqueador: list[int] = []

    def anotar_pid(_indice: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            pid_bloqueador.append(cursor.fetchone()[0])

    borrado = _Bloqueador([(SQL_BORRAR[caso], [catalogo.pk])], anotar_pid)

    def confirmar_cuando_el_alta_espere() -> None:
        try:
            _esperar_a_que_espere_un_bloqueo(pid_bloqueador[0])
        finally:
            borrado.soltar.set()
            connections.close_all()

    borrado.start()
    assert borrado.listo.wait(PLAZO_S)
    vigia = threading.Thread(target=confirmar_cuando_el_alta_espere)
    vigia.start()
    estado, cuerpo = _alta(ruta, campo, catalogo.pk, f"Alta ventana {caso}")(_cliente(cookies))
    vigia.join(PLAZO_S)
    borrado.join(PLAZO_S)
    assert borrado.error is None, borrado.error
    _conflicto(estado, cuerpo)
    eventos = _eventos(logs_json, "conflicto_concurrencia_bd")
    assert [e["sqlstate"] for e in eventos] == ["23503"]
    assert eventos[0]["restriccion"]  # nombre de la constraint, sin valores
    assert _eventos(logs_json, "excepcion_no_controlada") == []
    assert not modelo.objects.filter(pk=catalogo.pk).exists()
    assert not subtipo.objects.filter(**{campo: catalogo.pk}).exists()
