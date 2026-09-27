"""AC-TKT005-01: cada operación /api/v1/publico/** del contrato está implementada completa.

- El esquema generado contiene las 25 operaciones públicas, todas en el contrato con el mismo
  operationId, sin rutas parciales (gate por operación; oasdiff y schemathesis van en CI).
- Cada operación responde conforme a su esquema del contrato (JSON Schema 2020-12) con datos
  reales: 200, 400, 404 y 410 (response_schema_conformance en pytest).
- Solo GET/HEAD; sin cookies; cabeceras de caché del contrato.
"""

from __future__ import annotations

import re

import pytest

from apps.contenido.tests.conftest import PUBLICO, contrato
from apps.core.esquema import GeneradorContrato

pytestmark = pytest.mark.django_db

METODOS = {"get", "put", "post", "delete", "patch"}
OPERACIONES_PUBLICAS = {
    "publicoObtenerInicio",
    "publicoObtenerConfiguracion",
    "publicoObtenerEscalas",
    "publicoObtenerMeses",
    "publicoListarIndice",
    "publicoObtenerPaginaInstitucional",
    "publicoObtenerFacetasDestinos",
    "publicoListarDestinos",
    "publicoListarDestinosMapa",
    "publicoObtenerDestinoAleatorio",
    "publicoObtenerDestino",
    "publicoListarItinerarios",
    "publicoObtenerItinerario",
    "publicoListarTiposAventura",
    "publicoObtenerTipoAventura",
    "publicoListarCategoriasGuia",
    "publicoObtenerCategoriaGuia",
    "publicoListarGuias",
    "publicoObtenerGuia",
    "publicoListarColecciones",
    "publicoObtenerColeccion",
    "publicoBuscar",
    "publicoBuscarPorGrupo",
    "publicoListarGlosario",
    "publicoListarCreditos",
}


def _operaciones(doc: dict) -> dict[tuple[str, str], str]:
    return {
        (re.sub(r"\{[^}]+\}", "{}", ruta), metodo): op["operationId"]
        for ruta, item in doc["paths"].items()
        for metodo, op in item.items()
        if metodo in METODOS
    }


def test_AC_TKT005_01_operaciones_publicas_generadas_documentadas_y_completas():
    c = _operaciones(contrato())
    g = _operaciones(GeneradorContrato().get_schema(request=None, public=True))
    publicas_contrato = {op for (ruta, _m), op in c.items() if ruta.startswith(PUBLICO)}
    assert publicas_contrato == OPERACIONES_PUBLICAS
    assert OPERACIONES_PUBLICAS <= set(g.values())
    assert set(g) <= set(c), sorted(set(g) - set(c))
    for clave, operation_id in g.items():
        assert c[clave] == operation_id
    rutas_g = {ruta for ruta, _ in g}
    assert sorted(k for k in set(c) - set(g) if k[0] in rutas_g) == []


def _ok(api, ruta, conforme, componente, **parametros):
    respuesta = api.get(f"{PUBLICO}{ruta}", parametros)
    assert respuesta.status_code == 200, (ruta, respuesta.content[:500])
    assert respuesta["Content-Type"] == "application/json"
    assert "Set-Cookie" not in respuesta.headers
    assert not respuesta.cookies
    conforme(componente, respuesta.json())
    return respuesta


CASOS_200 = [
    ("/inicio", "Inicio", {}),
    ("/configuracion", "ConfiguracionPublica", {}),
    ("/escalas", "Escalas", {}),
    ("/meses", "Meses", {}),
    ("/indice", "PaginaEntradaIndice", {}),
    ("/paginas/acerca-de", "PaginaInstitucionalPublica", {}),
    ("/facetas/destinos", "FacetasDestinos", {}),
    ("/destinos", "PaginaDestinoTarjeta", {}),
    ("/destinos/mapa", "PaginaDestinoMapa", {}),
    ("/itinerarios", "PaginaItinerarioTarjeta", {}),
    ("/tipos-aventura", "PaginaTipoAventuraTarjeta", {}),
    ("/categorias-guia", "PaginaCategoriaGuiaIndice", {}),
    ("/guias", "PaginaGuiaTarjeta", {}),
    ("/colecciones", "PaginaColeccionTarjeta", {}),
    ("/glosario", "PaginaTerminoGlosarioPublico", {}),
    ("/creditos", "PaginaCreditoMedio", {}),
    ("/busqueda", "BusquedaAgrupada", {"q": "cocuy"}),
    ("/busqueda/destinos", "PaginaResultadoBusqueda", {"q": "trek"}),
]


@pytest.mark.parametrize(("ruta", "componente", "parametros"), CASOS_200)
def test_AC_TKT005_01_listados_y_agregados_conformes(
    api, mundo, conforme, ruta, componente, parametros
):
    _ok(api, ruta, conforme, componente, **parametros)


def test_AC_TKT005_01_detalles_conformes(api, mundo, conforme):
    d = mundo
    casos = [
        (f"/destinos/{d['cocuy'].contenido.slug}", "DestinoDetalle"),
        (f"/itinerarios/{d['ruta_cocuy'].contenido.slug}", "ItinerarioDetalle"),
        (f"/tipos-aventura/{d['tipos'][0].contenido.slug}", "TipoAventuraDetalle"),
        (f"/guias/{d['guia_equipo'].contenido.slug}", "GuiaDetalle"),
        (f"/colecciones/{d['coleccion'].contenido.slug}", "ColeccionDetalle"),
        (f"/categorias-guia/{d['guia_equipo'].categoria.slug}", "CategoriaGuiaPublica"),
        ("/destinos/aleatorio", "DestinoAleatorio"),
    ]
    for ruta, componente in casos:
        _ok(api, ruta, conforme, componente)


def test_AC_TKT005_01_errores_conformes(api, mundo, conforme):
    retirado = api.get(f"{PUBLICO}/destinos/{mundo['retirado'].contenido.slug}")
    assert retirado.status_code == 410
    assert retirado["Content-Type"] == "application/problem+json"
    conforme("ProblemaRetirado", retirado.json())
    invalido = api.get(f"{PUBLICO}/destinos", {"dificultad_min": "9"})
    assert invalido.status_code == 400
    conforme("ProblemaValidacion", invalido.json())
    inexistente = api.get(f"{PUBLICO}/guias/no-existe")
    assert inexistente.status_code == 404
    conforme("Problem", inexistente.json())
    fuera = api.get(f"{PUBLICO}/destinos", {"pagina": "50"})
    assert fuera.status_code == 404
    assert fuera.json()["code"] == "pagina_fuera_de_rango"


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete", "options"])
def test_AC_TKT005_01_solo_get_y_head(api, mundo, metodo):
    respuesta = getattr(api, metodo)(f"{PUBLICO}/destinos")
    assert respuesta.status_code == 405
    assert respuesta.json()["code"] == "metodo_no_permitido"
    assert api.head(f"{PUBLICO}/destinos").status_code == 200


def test_AC_TKT005_01_cabeceras_de_cache_del_contrato(api, mundo):
    publico = "public, max-age=60, stale-while-revalidate=300"
    assert api.get(f"{PUBLICO}/destinos")["Cache-Control"] == publico
    assert (
        api.get(f"{PUBLICO}/destinos/{mundo['retirado'].contenido.slug}")["Cache-Control"]
        == publico
    )
    assert api.get(f"{PUBLICO}/busqueda", {"q": "cocuy"})["Cache-Control"] == "no-store"
    assert api.get(f"{PUBLICO}/destinos/aleatorio")["Cache-Control"] == "no-store"
    assert api.get(f"{PUBLICO}/guias/no-existe")["Cache-Control"] == "no-store"
