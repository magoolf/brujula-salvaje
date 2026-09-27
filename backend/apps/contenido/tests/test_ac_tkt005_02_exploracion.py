"""AC-TKT005-02: filtros y facetas combinables, mes, aleatorio, mapa, 404/410 y paginación.

Trazabilidad: FEAT-001..028/051/052, RULE-001, RULE-006, RULE-011, RULE-016, RULE-019, RULE-024,
DEC-AUTO-040/042/047/113, AC-010, AC-011, AC-012, AC-014, AC-015, AC-017, AC-018, AC-023,
AC-035, AC-036, AC-100, AC-113, AC-122, AC-123. Sin N+1 (Skill_Backend §8).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.catalogos.models import Region
from apps.contenido.models import EstadoEditorial
from apps.contenido.tests import publicos
from apps.contenido.tests.conftest import PUBLICO
from apps.inicio.models import SeccionInicio

pytestmark = pytest.mark.django_db


def _slugs(respuesta) -> list[str]:
    assert respuesta.status_code == 200, respuesta.content[:400]
    return [r["slug"] for r in respuesta.json()["resultados"]]


def _destinos(api, **parametros):
    return api.get(f"{PUBLICO}/destinos", parametros)


def _s(mundo, *claves) -> list[str]:
    return [mundo[c].contenido.slug for c in claves]


# ---------------------------------------------------------------------------
# Listado y filtros de destinos (AC-012, AC-017, AC-018, RULE-019, DEC-AUTO-047)
# ---------------------------------------------------------------------------
def test_AC_TKT005_02_AC_012_solo_publicados_orden_alfabetico_espanol(api, mundo):
    respuesta = _destinos(api)
    assert _slugs(respuesta) == _s(mundo, "annapurna", "colca", "cocuy", "salento")
    cuerpo = respuesta.json()
    assert (cuerpo["total"], cuerpo["pagina"], cuerpo["tamano_pagina"]) == (4, 1, 24)
    assert cuerpo["total_paginas"] == 1
    assert cuerpo["siguiente"] is None
    assert cuerpo["anterior"] is None
    tarjeta = cuerpo["resultados"][2]
    assert tarjeta["pais"] == {"slug": mundo["paises"][0].slug, "nombre": "Colombia"}
    assert [t["nombre"] for t in tarjeta["tipos"]] == ["Trekking", "Escalada en roca"]


def test_AC_TKT005_02_or_dentro_de_faceta_and_entre_facetas(api, mundo):
    trek, kayak, escalada = (t.contenido.slug for t in mundo["tipos"])
    assert _slugs(_destinos(api, tipo=kayak)) == _s(mundo, "colca")
    assert _slugs(_destinos(api, tipo=[kayak, escalada])) == _s(mundo, "colca", "cocuy")
    assert _slugs(_destinos(api, tipo=trek, pais=mundo["paises"][1].slug)) == _s(mundo, "colca")
    region2 = mundo["annapurna"].pais.region.slug
    assert _slugs(_destinos(api, region=region2)) == _s(mundo, "annapurna")
    assert _slugs(_destinos(api, tipo=trek, region=region2, presupuesto=[1, 2])) == []


def test_AC_TKT005_02_AC_017_dificultad_como_rango(api, mundo):
    assert _slugs(_destinos(api, dificultad_min=3, dificultad_max=4)) == _s(mundo, "colca", "cocuy")
    assert _slugs(_destinos(api, dificultad_max=3)) == _s(mundo, "colca", "salento")


def test_AC_TKT005_02_mes_duracion_por_solapamiento_y_presupuesto(api, mundo):
    assert _slugs(_destinos(api, mes=6)) == _s(mundo, "colca", "salento")
    assert _slugs(_destinos(api, mes=3)) == []
    # Tramos por solapamiento: Colca (3-5) coincide con 1-3 y con 4-7.
    assert _slugs(_destinos(api, duracion="1-3")) == _s(mundo, "colca", "salento")
    assert _slugs(_destinos(api, duracion="15+")) == _s(mundo, "annapurna")
    assert _slugs(_destinos(api, duracion=["1-3", "15+"])) == _s(
        mundo, "annapurna", "colca", "salento"
    )
    assert _slugs(_destinos(api, presupuesto=[1, 4])) == _s(mundo, "annapurna", "salento")


def test_AC_TKT005_02_orden_por_dificultad(api, mundo):
    esperado = _s(mundo, "annapurna", "cocuy", "colca", "salento")
    assert _slugs(_destinos(api, orden="dificultad_desc")) == esperado
    assert _slugs(_destinos(api, orden="dificultad_asc")) == list(reversed(esperado))


@pytest.mark.parametrize(
    ("parametros", "campo"),
    [
        ({"tipo": "no-existe"}, "tipo"),
        ({"region": "no-existe"}, "region"),
        ({"pais": "no-existe"}, "pais"),
        ({"dificultad_min": "4", "dificultad_max": "2"}, "dificultad_min"),
        ({"dificultad_min": "0"}, "dificultad_min"),
        ({"mes": "13"}, "mes"),
        ({"duracion": "2-5"}, "duracion"),
        ({"presupuesto": "5"}, "presupuesto"),
        ({"orden": "precio"}, "orden"),
        ({"desconocido": "1"}, "desconocido"),
        ({"region": ""}, "region"),
        ({"region": "Con-Mayusculas"}, "region"),
        ({"pagina": "0"}, "pagina"),
    ],
)
def test_AC_TKT005_02_AC_113_valores_fuera_de_dominio_400(api, mundo, parametros, campo):
    respuesta = _destinos(api, **parametros)
    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["code"] == "parametro_invalido"
    assert any(clave.split(".")[0] == campo for clave in cuerpo["errors"])


def test_AC_TKT005_02_arrays_sin_repetidos_y_acotados(api, mundo):
    trek = mundo["tipos"][0].contenido.slug
    assert _destinos(api, tipo=[trek, trek]).status_code == 400
    assert _destinos(api, tipo=[f"t-{i}" for i in range(13)]).status_code == 400
    assert _destinos(api, region=["a", "b"]).json()["errors"]["region"]
    borrador = mundo["tipo_borrador"].contenido.slug
    assert _destinos(api, tipo=borrador).json()["errors"]["tipo"]


def test_AC_TKT005_02_paginacion_24_y_pagina_fuera_de_rango(api, mundo):
    trek = mundo["tipos"][0]
    for i in range(22):
        publicos.destino(f"Zona {i:02d}", tipos=[trek])
    primera = _destinos(api).json()
    assert (primera["total"], primera["total_paginas"], len(primera["resultados"])) == (26, 2, 24)
    assert primera["siguiente"] == f"{PUBLICO}/destinos?pagina=2"
    segunda = _destinos(api, pagina=2).json()
    assert len(segunda["resultados"]) == 2
    assert segunda["anterior"] == f"{PUBLICO}/destinos?pagina=1"
    fuera = _destinos(api, pagina=3)
    assert fuera.status_code == 404
    assert fuera.json()["code"] == "pagina_fuera_de_rango"


def test_AC_TKT005_02_facetas_solo_valores_con_contenido_publicado(api, mundo):
    facetas = api.get(f"{PUBLICO}/facetas/destinos").json()
    assert [t["nombre"] for t in facetas["tipos"]] == ["Trekking", "Kayak", "Escalada en roca"]
    regiones = {r["slug"]: [p["nombre"] for p in r["paises"]] for r in facetas["regiones"]}
    assert regiones == {
        mundo["cocuy"].pais.region.slug: ["Colombia", "Perú"],
        mundo["annapurna"].pais.region.slug: ["Nepal"],
    }
    assert [n["nivel"] for n in facetas["dificultad"]] == [1, 3, 4, 5]
    assert [n["nivel"] for n in facetas["presupuesto"]] == [1, 2, 3, 4]
    assert [t["codigo"] for t in facetas["tramos_duracion"]] == ["1-3", "4-7", "8-14", "15+"]
    assert facetas["tramos_duracion"][3]["max_dias"] is None


# ---------------------------------------------------------------------------
# Mapa, meses y aleatorio (AC-023, AC-036, AC-122)
# ---------------------------------------------------------------------------
def test_AC_TKT005_02_AC_023_mapa_solo_publicados_con_coordenadas(api, mundo):
    publicos.destino("Sin coordenadas", tipos=[mundo["tipos"][0]], coordenadas=None)
    respuesta = api.get(f"{PUBLICO}/destinos/mapa").json()
    assert respuesta["tamano_pagina"] == 500
    assert [r["slug"] for r in respuesta["resultados"]] == _s(
        mundo, "annapurna", "colca", "cocuy", "salento"
    )
    annapurna = respuesta["resultados"][0]
    assert (annapurna["latitud"], annapurna["longitud"]) == (28.596, 83.82)
    assert annapurna["region"]["slug"] == mundo["annapurna"].pais.region.slug


def test_AC_TKT005_02_AC_036_meses_con_conteo_y_destacado(api, mundo):
    meses = api.get(f"{PUBLICO}/meses").json()["meses"]
    assert [m["slug"] for m in meses][:3] == ["enero", "febrero", "marzo"]
    por_mes = {m["mes"]: m for m in meses}
    assert por_mes[6]["numero_destinos"] == 2
    # Destacado: el de revisión más reciente (Salento).
    assert por_mes[6]["destacado"]["slug"] == mundo["salento"].contenido.slug
    assert por_mes[3] == {
        "mes": 3,
        "nombre": "Marzo",
        "slug": "marzo",
        "numero_destinos": 0,
        "destacado": None,
    }


def test_AC_TKT005_02_AC_122_aleatorio_solo_publicados_y_404_sin_destinos(api, mundo):
    publicados = set(_s(mundo, "annapurna", "colca", "cocuy", "salento"))
    vistos = {api.get(f"{PUBLICO}/destinos/aleatorio").json()["slug"] for _ in range(20)}
    assert vistos <= publicados
    assert len(vistos) > 1


def test_AC_TKT005_02_aleatorio_sin_destinos_404(api, db):
    respuesta = api.get(f"{PUBLICO}/destinos/aleatorio")
    assert respuesta.status_code == 404
    assert respuesta["Cache-Control"] == "no-store"


# ---------------------------------------------------------------------------
# Detalles: 200 / 404 / 410 (AC-014, AC-015, AC-100, DEC-AUTO-040/113)
# ---------------------------------------------------------------------------
def test_AC_TKT005_02_AC_014_ficha_de_destino_completa(api, mundo):
    ficha = api.get(f"{PUBLICO}/destinos/{mundo['cocuy'].contenido.slug}").json()
    assert ficha["pais"]["region"]["slug"] == mundo["cocuy"].pais.region.slug
    assert ficha["tipo_principal"]["nombre"] == "Trekking"
    assert ficha["meses_mejor_epoca"] == [1, 2, 12]
    assert len(ficha["galeria"]) == 3
    assert [i["slug"] for i in ficha["itinerarios"]] == _s(mundo, "ruta_cocuy")
    assert (ficha["itinerarios_total"], ficha["itinerarios_afines"]) == (1, [])
    assert [g["slug"] for g in ficha["guias_relacionadas"]] == _s(mundo, "guia_equipo")
    assert [t["termino"] for t in ficha["terminos"]] == ["Glaciar"]
    assert ficha["fuentes"][0]["url"] == "https://example.org"
    assert ficha["metadatos"]["autoria"] == "Equipo editorial Brújula Salvaje"
    assert ficha["metadatos"]["seo_titulo"] == "El Cocuy"


def test_AC_TKT005_02_RULE_006_relacionados_curados_primero_y_complemento(api, mundo):
    ficha = api.get(f"{PUBLICO}/destinos/{mundo['cocuy'].contenido.slug}").json()
    relacionados = ficha["relacionados"]
    assert [(r["slug"], r["origen"]) for r in relacionados[:3]] == [
        (mundo["salento"].contenido.slug, "CURADO"),
        (mundo["ruta_cocuy"].contenido.slug, "CURADO"),
        (mundo["guia_equipo"].contenido.slug, "CURADO"),
    ]
    automaticos = relacionados[3:]
    assert 3 <= len(relacionados) <= 6
    assert all(r["origen"] == "AUTOMATICO" for r in automaticos)
    # Afinidad: primero los destinos con el mismo tipo principal.
    assert automaticos[0]["tipo"] == "DESTINO"
    slugs = {r["slug"] for r in relacionados}
    no_publicos = _s(mundo, "cocuy", "retirado", "borrador")
    assert slugs.isdisjoint(no_publicos)


def test_AC_TKT005_02_itinerarios_afines_si_el_destino_no_tiene(api, mundo):
    ficha = api.get(f"{PUBLICO}/destinos/{mundo['salento'].contenido.slug}").json()
    assert ficha["itinerarios"] == []
    assert ficha["itinerarios_total"] == 0
    assert {i["slug"] for i in ficha["itinerarios_afines"]} == set(
        _s(mundo, "ruta_cocuy", "ruta_colca")
    )


@pytest.mark.parametrize(
    "ruta", ["destinos", "itinerarios", "tipos-aventura", "guias", "colecciones"]
)
def test_AC_TKT005_02_inexistente_404(api, mundo, ruta):
    respuesta = api.get(f"{PUBLICO}/{ruta}/no-existe-nada")
    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "no_encontrado"


def test_AC_TKT005_02_AC_100_retirado_410_con_alternativas_sin_cuerpo(api, mundo):
    respuesta = api.get(f"{PUBLICO}/destinos/{mundo['retirado'].contenido.slug}")
    assert respuesta.status_code == 410
    cuerpo = respuesta.json()
    assert cuerpo["code"] == "retirado"
    assert cuerpo["listado_padre"] == "/destinos"
    assert 3 <= len(cuerpo["alternativas"]) <= 6
    publicados = set(_s(mundo, "annapurna", "colca", "cocuy", "salento", "ruta_cocuy"))
    publicados |= set(_s(mundo, "ruta_colca", "guia_equipo", "guia_altura", "coleccion"))
    publicados |= {t.contenido.slug for t in mundo["tipos"]}
    assert {a["slug"] for a in cuerpo["alternativas"]} <= publicados
    for campo in ("descripcion_experta", "resumen", "galeria", "pais", "titulo"):
        assert campo not in cuerpo


@pytest.mark.parametrize(
    ("ruta", "tipo", "padre"),
    [
        ("itinerarios", "ITINERARIO", "/itinerarios"),
        ("guias", "GUIA", "/guias"),
        ("tipos-aventura", "TIPO", "/tipos-de-aventura"),
        ("colecciones", "COLECCION", "/colecciones"),
    ],
)
def test_AC_TKT005_02_retirado_410_en_cada_tipo(api, mundo, ruta, tipo, padre):
    if tipo == "ITINERARIO":
        objeto = publicos.itinerario("Retirado", mundo["cocuy"], estado=EstadoEditorial.RETIRADO)
    elif tipo == "GUIA":
        objeto = publicos.guia("Guía retirada", estado=EstadoEditorial.RETIRADO)
    elif tipo == "TIPO":
        objeto = publicos.tipo("Tipo retirado", estado=EstadoEditorial.RETIRADO)
    else:
        objeto = publicos.coleccion("Retirada", [], estado=EstadoEditorial.RETIRADO)
    respuesta = api.get(f"{PUBLICO}/{ruta}/{objeto.contenido.slug}")
    assert respuesta.status_code == 410
    assert respuesta.json()["listado_padre"] == padre
    assert len(respuesta.json()["alternativas"]) >= 3


def test_AC_TKT005_02_detalles_de_itinerario_tipo_guia_y_coleccion(api, mundo):
    itinerario = api.get(f"{PUBLICO}/itinerarios/{mundo['ruta_cocuy'].contenido.slug}").json()
    assert itinerario["destino"]["slug"] == mundo["cocuy"].contenido.slug
    assert [d["numero_dia"] for d in itinerario["dias"]] == [1, 2, 3, 4, 5]
    assert itinerario["distancia_total_km"] == 42.5

    tipo = api.get(f"{PUBLICO}/tipos-aventura/{mundo['tipos'][0].contenido.slug}").json()
    assert tipo["destinos_total"] == 4
    assert len(tipo["checklist"]) == 2
    assert tipo["checklist"][0]["esencial"] is True

    guia = api.get(f"{PUBLICO}/guias/{mundo['guia_equipo'].contenido.slug}").json()
    assert guia["minutos_lectura"] == 3  # ceil(450 / 200)
    assert [d["slug"] for d in guia["destinos_relacionados"]] == _s(mundo, "cocuy", "salento")
    assert [t["nombre"] for t in guia["tipos_relacionados"]] == ["Trekking"]

    # RULE-024: el elemento retirado no aparece.
    coleccion = api.get(f"{PUBLICO}/colecciones/{mundo['coleccion'].contenido.slug}").json()
    tipos = [(e["tipo"], (e["destino"] or e["itinerario"])["slug"]) for e in coleccion["elementos"]]
    assert tipos == [
        ("DESTINO", mundo["cocuy"].contenido.slug),
        ("DESTINO", mundo["colca"].contenido.slug),
        ("ITINERARIO", mundo["ruta_cocuy"].contenido.slug),
    ]


def test_AC_TKT005_02_itinerario_con_destino_no_publico_404(api, mundo):
    oculto = publicos.itinerario("Huérfano", mundo["borrador"])
    assert api.get(f"{PUBLICO}/itinerarios/{oculto.contenido.slug}").status_code == 404
    assert oculto.contenido.slug not in _slugs(api.get(f"{PUBLICO}/itinerarios"))


# ---------------------------------------------------------------------------
# Otros listados
# ---------------------------------------------------------------------------
def test_AC_TKT005_02_itinerarios_por_destino_y_orden(api, mundo):
    cocuy = mundo["cocuy"].contenido.slug
    assert _slugs(api.get(f"{PUBLICO}/itinerarios", {"destino": cocuy})) == _s(mundo, "ruta_cocuy")
    orden = _slugs(api.get(f"{PUBLICO}/itinerarios", {"orden": "duracion_desc"}))
    assert orden == _s(mundo, "ruta_cocuy", "ruta_colca")
    borrador = mundo["borrador"].contenido.slug
    assert api.get(f"{PUBLICO}/itinerarios", {"destino": borrador}).status_code == 400


def test_AC_TKT005_02_tipos_con_numero_de_destinos_publicados(api, mundo):
    tipos = api.get(f"{PUBLICO}/tipos-aventura").json()["resultados"]
    assert [(t["titulo"], t["numero_destinos"]) for t in tipos] == [
        ("Trekking", 4),
        ("Kayak", 1),
        ("Escalada en roca", 1),
    ]


def test_AC_TKT005_02_categorias_y_guias(api, mundo):
    categorias = api.get(f"{PUBLICO}/categorias-guia").json()["resultados"]
    assert len(categorias) == 1
    assert categorias[0]["numero_guias"] == 2
    recientes = [g["slug"] for g in categorias[0]["guias_recientes"]]
    assert recientes == _s(mundo, "guia_altura", "guia_equipo")
    slug = categorias[0]["slug"]
    assert _slugs(api.get(f"{PUBLICO}/guias", {"categoria": slug})) == recientes
    assert api.get(f"{PUBLICO}/guias", {"categoria": "no-existe"}).status_code == 400
    otra = publicos.categoria().__class__.objects.exclude(slug=slug).first()
    assert api.get(f"{PUBLICO}/categorias-guia/{otra.slug}").status_code == 404


def test_AC_TKT005_02_glosario_creditos_e_indice(api, mundo):
    glosario = api.get(f"{PUBLICO}/glosario").json()["resultados"]
    assert glosario[0]["termino"] == "Glaciar"
    assert glosario[0]["usado_en"] == [
        {"tipo": "DESTINO", "slug": mundo["cocuy"].contenido.slug, "titulo": "El Cocuy"}
    ]
    creditos = api.get(f"{PUBLICO}/creditos").json()
    autores = {c["imagen"]["autor_credito"] for c in creditos["resultados"]}
    assert mundo["borrador"].contenido.portada.autor_credito not in autores
    assert mundo["retirado"].contenido.portada.autor_credito not in autores
    assert mundo["cocuy"].contenido.portada.autor_credito in autores

    indice = api.get(f"{PUBLICO}/indice").json()["resultados"]
    por_slug = {(e["tipo"], e["slug"]): e for e in indice}
    assert ("PAGINA", "acerca-de") in por_slug
    assert ("DESTINO", mundo["cocuy"].contenido.slug) in por_slug
    assert por_slug[("DESTINO", mundo["cocuy"].contenido.slug)]["agrupacion"]["slug"] == (
        mundo["cocuy"].pais.region.slug
    )
    assert any(e["tipo"] == "CATEGORIA_GUIA" for e in indice)
    ocultos = set(_s(mundo, "retirado", "borrador")) | {mundo["termino"].contenido.slug}
    assert ocultos.isdisjoint(e["slug"] for e in indice)


def test_AC_TKT005_02_paginas_institucionales(api, mundo):
    pagina = api.get(f"{PUBLICO}/paginas/acerca-de").json()
    assert (pagina["slug"], pagina["titulo"], pagina["version_documento"]) == (
        "acerca-de",
        "Acerca de",
        "1.0",
    )
    assert api.get(f"{PUBLICO}/paginas/aviso-legal").status_code == 404
    assert api.get(f"{PUBLICO}/paginas/otra-cosa").status_code == 404


# ---------------------------------------------------------------------------
# Inicio, configuración y escalas (AC-010, AC-011, RULE-016)
# ---------------------------------------------------------------------------
def test_AC_TKT005_02_AC_011_inicio_destacados_en_orden_y_relleno(api, mundo):
    publicos.destacar(
        SeccionInicio.DESTINOS, mundo["annapurna"].contenido, mundo["retirado"].contenido
    )
    publicos.config_inicio()
    inicio = api.get(f"{PUBLICO}/inicio").json()
    destinos = [d["slug"] for d in inicio["destinos"]]
    # El destacado primero; el retirado se ignora y se rellena por revisión más reciente.
    assert destinos[0] == mundo["annapurna"].contenido.slug
    assert set(destinos) == set(_s(mundo, "annapurna", "colca", "cocuy", "salento"))
    assert destinos[1] == mundo["salento"].contenido.slug
    assert len(inicio["itinerarios"]) == 2
    assert [g["slug"] for g in inicio["guias"]] == _s(mundo, "guia_altura", "guia_equipo")
    assert [t["titulo"] for t in inicio["tipos"]] == ["Trekking", "Kayak", "Escalada en roca"]
    assert inicio["hero"]["titular"] == "Explora lo salvaje"


def test_AC_TKT005_02_inicio_sin_hero_disponible(api, mundo):
    assert api.get(f"{PUBLICO}/inicio").json()["hero"] is None
    publicos.config_inicio(hero=publicos.medio(estado="PENDIENTE_METADATOS"))
    assert api.get(f"{PUBLICO}/inicio").json()["hero"] is None


def test_AC_TKT005_02_configuracion_y_escalas(api, db):
    config = api.get(f"{PUBLICO}/configuracion").json()
    assert config["nombre_marca"] == "Brújula Salvaje"
    assert config["responsable"]["definido"] is False
    escalas = api.get(f"{PUBLICO}/escalas").json()
    assert [n["nivel"] for n in escalas["dificultad"]] == [1, 2, 3, 4, 5]
    assert [n["nivel"] for n in escalas["presupuesto"]] == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Sin N+1 (Skill_Backend §8): el número de consultas no crece con los datos
# ---------------------------------------------------------------------------
def _consultas(api, ruta: str, **parametros) -> int:
    with CaptureQueriesContext(connection) as capturadas:
        assert api.get(f"{PUBLICO}{ruta}", parametros).status_code == 200
    return len(capturadas)


RUTAS_N_MAS_1 = [
    "/destinos",
    "/destinos/mapa",
    "/itinerarios",
    "/tipos-aventura",
    "/guias",
    "/categorias-guia",
    "/colecciones",
    "/glosario",
    "/creditos",
    "/indice",
    "/inicio",
    "/meses",
    "/facetas/destinos",
]


def test_AC_TKT005_02_sin_n_mas_1_en_listados(api, mundo):
    antes = {ruta: _consultas(api, ruta) for ruta in RUTAS_N_MAS_1}
    trek, kayak, _ = mundo["tipos"]
    region = Region.objects.order_by("-orden").first()
    for i in range(6):
        d = publicos.destino(
            f"Nuevo {i}", tipos=[trek, kayak], pais_=publicos.pais(region=region), meses=[3, 4]
        )
        publicos.itinerario(f"Ruta nueva {i}", d)
        g = publicos.guia(f"Guía nueva {i}", destinos=[d], revision=publicos.BASE + timedelta(i))
        publicos.termino(f"Término {i}", [d.contenido, g.contenido])
        publicos.coleccion(f"Colección {i}", [d.contenido])
    despues = {ruta: _consultas(api, ruta) for ruta in RUTAS_N_MAS_1}
    assert despues == antes


def test_AC_TKT005_02_sin_n_mas_1_en_detalles(api, mundo):
    ruta = f"/destinos/{mundo['cocuy'].contenido.slug}"
    antes = _consultas(api, ruta)
    trek = mundo["tipos"][0]
    for i in range(4):
        publicos.itinerario(f"Otra ruta {i}", mundo["cocuy"])
        publicos.guia(f"Otra guía {i}", destinos=[mundo["cocuy"]])
        publicos.galeria(mundo["cocuy"].contenido, 1)
        publicos.destino(f"Vecino {i}", tipos=[trek], pais_=mundo["cocuy"].pais)
    # Acotado: no crece con itinerarios, guías, galería ni vecinos (la afinidad usa ≤4 pasos).
    assert _consultas(api, ruta) <= antes <= 35
