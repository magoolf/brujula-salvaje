"""AC-TKT005-03: búsqueda insensible a tildes y mayúsculas, por prefijo y agrupada; p95 medido.

Trazabilidad: FEAT-016, AP-10, RULE-018, ADR-DB-003, DEC-AUTO-048, AC-019, AC-020, AC-116,
REQ-051 (búsqueda p95 ≤ 500 ms), REQ-053 (lecturas p95 ≤ 300 ms), THREAT-008/009/010/020.
"""

from __future__ import annotations

import statistics
import time
from datetime import date, timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.busqueda import selectors, services
from apps.busqueda.models import BusquedaDocumento
from apps.contenido.models import Contenido, Destino, EstadoEditorial
from apps.contenido.tests import publicos
from apps.contenido.tests.conftest import PUBLICO, api, mundo  # noqa: F401 (fixtures)
from apps.core.throttling import LimitePorAmbito

pytestmark = pytest.mark.django_db


def _buscar(api, q, **extra):
    return api.get(f"{PUBLICO}/busqueda", {"q": q, **extra})


def _grupo(respuesta, grupo: str) -> list[str]:
    assert respuesta.status_code == 200, respuesta.content[:300]
    return [r["slug"] for r in respuesta.json()["grupos"][grupo]["resultados"]]


# ---------------------------------------------------------------------------
# AC-019: insensible a tildes/mayúsculas, prefijos, ámbito y agrupación
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("q", ["cañón", "CANON", "Cañon del", "canon colca", "  colca  "])
def test_AC_TKT005_03_AC_019_insensible_a_tildes_y_mayusculas(api, mundo, q):
    assert _grupo(_buscar(api, q), "destinos") == [mundo["colca"].contenido.slug]


def test_AC_TKT005_03_prefijo_y_ambito_titulo_resumen_cuerpo_pais_y_tipo(api, mundo):
    assert _grupo(_buscar(api, "annap"), "destinos") == [mundo["annapurna"].contenido.slug]
    # Cuerpo (peso D), con stemming español: "lagunas" → "laguna".
    assert _grupo(_buscar(api, "laguna"), "destinos") == [mundo["cocuy"].contenido.slug]
    # País (peso C).
    assert _grupo(_buscar(api, "nepal"), "destinos") == [mundo["annapurna"].contenido.slug]
    # Nombre de tipo (peso C) y el propio tipo en su grupo.
    trekking = _buscar(api, "trekking").json()
    assert trekking["grupos"]["destinos"]["total"] == 4
    assert [r["slug"] for r in trekking["grupos"]["tipos"]["resultados"]] == [
        mundo["tipos"][0].contenido.slug
    ]
    assert trekking["grupos"]["itinerarios"]["total"] == 2


def test_AC_TKT005_03_agrupada_con_totales_y_maximo_10_por_grupo(api, mundo):
    trek = mundo["tipos"][0]
    for i in range(12):
        publicos.destino(f"Selva profunda {i:02d}", tipos=[trek])
    services.reindexar_todo()
    cuerpo = _buscar(api, "selva").json()
    assert cuerpo["grupos"]["destinos"]["total"] == 12
    assert len(cuerpo["grupos"]["destinos"]["resultados"]) == 10
    assert cuerpo["total"] == 12
    assert set(cuerpo["grupos"]) == {"destinos", "itinerarios", "guias", "tipos"}
    assert "q" not in cuerpo  # THREAT-010
    resultado = cuerpo["grupos"]["destinos"]["resultados"][0]
    assert resultado["tipo"] == "DESTINO"
    assert resultado["portada"]["derivados"]
    # "Ver todos": el grupo completo paginado (24).
    grupo = api.get(f"{PUBLICO}/busqueda/destinos", {"q": "selva"}).json()
    assert (grupo["total"], len(grupo["resultados"]), grupo["tamano_pagina"]) == (12, 12, 24)
    assert api.get(f"{PUBLICO}/busqueda/destinos", {"q": "selva", "pagina": 2}).status_code == 404


def test_AC_TKT005_03_orden_por_relevancia_titulo_primero(api, mundo):
    # "cocuy" está en el título de El Cocuy (A) y en el de su itinerario; el destino gana en su
    # grupo y el itinerario aparece en el suyo.
    cuerpo = _buscar(api, "cocuy").json()
    assert cuerpo["grupos"]["destinos"]["resultados"][0]["slug"] == mundo["cocuy"].contenido.slug
    assert _grupo(_buscar(api, "cocuy"), "itinerarios") == [mundo["ruta_cocuy"].contenido.slug]


def test_AC_TKT005_03_respaldo_difuso_por_trigramas(api, mundo):
    # "anapurna" (con una n) no casa por prefijo; el respaldo por similitud del título sí.
    assert _grupo(_buscar(api, "anapurna"), "destinos") == [mundo["annapurna"].contenido.slug]
    assert _buscar(api, "zzzzqqq").json()["total"] == 0


def test_AC_TKT005_03_solo_contenido_publicado(api, mundo):
    assert _buscar(api, "retirado").json()["grupos"]["destinos"]["total"] == 0
    assert _buscar(api, "borrador").json()["grupos"]["destinos"]["total"] == 0
    assert _buscar(api, "tipo borrador").json()["grupos"]["tipos"]["total"] == 0


@pytest.mark.parametrize("q", ["a", " b ", "x" * 101])
def test_AC_TKT005_03_AC_020_longitud_fuera_de_rango_400_sin_buscar(api, mundo, q):
    respuesta = _buscar(api, q)
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "parametro_invalido"
    assert "q" in respuesta.json()["errors"]


def test_AC_TKT005_03_q_obligatorio_y_grupo_inexistente(api, mundo):
    assert api.get(f"{PUBLICO}/busqueda").status_code == 400
    assert api.get(f"{PUBLICO}/busqueda/destinos").status_code == 400
    assert api.get(f"{PUBLICO}/busqueda/playas", {"q": "sol"}).status_code == 404
    assert _buscar(api, "cocuy", extra="1").status_code == 400
    assert api.get(f"{PUBLICO}/busqueda", {"q": ["uno", "dos"]}).status_code == 400


# ---------------------------------------------------------------------------
# Servicio de índice (ADR-DB-003 §2): upsert/delete y reconstrucción idempotente
# ---------------------------------------------------------------------------
def test_AC_TKT005_03_indexar_y_desindexar(mundo):
    colca = mundo["colca"].contenido
    assert services.indexar(colca.pk) is True
    fila = BusquedaDocumento.objects.get(contenido=colca)
    assert (fila.titulo_norm, fila.pais_nombre) == ("canon del colca", "Perú")
    Contenido.objects.filter(pk=colca.pk).update(
        estado_editorial=EstadoEditorial.RETIRADO, retirado_en=timezone.now(), motivo_retiro="x"
    )
    assert services.indexar(colca.pk) is False
    assert not BusquedaDocumento.objects.filter(contenido=colca).exists()
    borrador = mundo["borrador"].contenido
    assert services.indexar(borrador.pk) is False


def test_AC_TKT005_03_reindexar_idempotente_y_estado_coherente(mundo):
    total = services.reindexar_todo()
    assert total == BusquedaDocumento.objects.count() == services.reindexar_todo()
    # 4 destinos + 2 itinerarios + 2 guías + 3 tipos publicados.
    assert total == 11
    assert selectors.estado_indice().coherente
    BusquedaDocumento.objects.filter(contenido=mundo["cocuy"].contenido).delete()
    estado = selectors.estado_indice()
    assert (estado.publicados, estado.indexados, estado.faltan, estado.sobran) == (11, 10, 1, 0)
    assert not estado.coherente


def test_AC_TKT005_03_texto_plano_sin_html():
    assert services.texto_plano("<p>Hola &amp; <strong>adiós</strong></p>", None) == "Hola & adiós"


# ---------------------------------------------------------------------------
# REQ-051 / REQ-053: p95 medido con datos de prueba (throttling desactivado solo aquí)
# ---------------------------------------------------------------------------
def _datos_volumen(cantidad: int) -> None:
    portada = publicos.medio()
    pais = publicos.pais("Tierra de pruebas")
    ahora = timezone.now()
    palabras = ["volcán", "laguna", "páramo", "selva", "desierto", "cañón", "glaciar", "costa"]
    for i in range(cantidad):
        palabra = palabras[i % len(palabras)]
        contenido = Contenido.objects.create(
            tipo="DESTINO",
            slug=f"volumen-{i}",
            titulo=f"{palabra.capitalize()} número {i}",
            estado_editorial=EstadoEditorial.PUBLICADO,
            fecha_ultima_revision=date(2026, 1, 1) + timedelta(days=i % 200),
            primera_publicacion_en=ahora,
            publicado_actualizado_en=ahora,
            seo_descripcion=f"SEO volumen {i}",
            portada=portada,
        )
        Destino.objects.create(
            contenido=contenido,
            pais=pais,
            resumen=f"Resumen con {palabra} y aventura {i}",
            descripcion_experta=f"<p>{' '.join(palabras)} {palabra} número {i}</p>" * 20,
            dificultad=1 + i % 5,
            meses_mejor_epoca=[1 + i % 12],
            duracion_min_dias=2,
            duracion_max_dias=6,
            nivel_presupuesto=1 + i % 4,
        )
    services.reindexar_todo()


def _p95(muestras: list[float]) -> float:
    return statistics.quantiles(muestras, n=20)[18]


def test_AC_TKT005_03_p95_busqueda_y_lecturas_con_datos_de_prueba(api, mundo, monkeypatch):
    monkeypatch.setattr(LimitePorAmbito, "allow_request", lambda self, request, view: True)
    _datos_volumen(600)
    consultas = ["volcán", "laguna páramo", "selv", "CAÑON", "glaciar costa", "numero 12"]
    consultas += ["aventura", "desiert", "volcan numero", "costa 5", "anapurna", "zzz"]
    tiempos_busqueda: list[float] = []
    for ronda in range(5):
        for q in consultas:
            inicio = time.perf_counter()
            respuesta = _buscar(api, q)
            tiempos_busqueda.append((time.perf_counter() - inicio) * 1000)
            assert respuesta.status_code == 200, (ronda, q)
    tiempos_lectura: list[float] = []
    rutas = ["/destinos", "/destinos?mes=3", f"/destinos/{mundo['cocuy'].contenido.slug}"]
    rutas += ["/inicio", "/destinos/mapa", "/facetas/destinos"]
    for _ in range(10):
        for ruta in rutas:
            inicio = time.perf_counter()
            assert api.get(f"{PUBLICO}{ruta}").status_code == 200
            tiempos_lectura.append((time.perf_counter() - inicio) * 1000)
    p95_busqueda, p95_lectura = _p95(tiempos_busqueda), _p95(tiempos_lectura)
    print(f"EVIDENCIA p95 busqueda={p95_busqueda:.1f} ms lecturas={p95_lectura:.1f} ms")  # noqa: T201
    assert p95_busqueda <= 500
    assert p95_lectura <= 300


def test_AC_TKT005_03_statement_timeout_de_la_busqueda(mundo, django_assert_max_num_queries):
    # THREAT-009: la transacción de búsqueda fija statement_timeout = 2 s (SET LOCAL).
    with connection.cursor() as cursor:
        cursor.execute("SHOW statement_timeout")
        previo = cursor.fetchone()[0]
    with django_assert_max_num_queries(8):
        selectors.buscar_agrupado("cocuy")
    with connection.cursor() as cursor:
        cursor.execute("SHOW statement_timeout")
        assert cursor.fetchone()[0] == previo
    assert selectors.TIMEOUT_BUSQUEDA == "2s"
