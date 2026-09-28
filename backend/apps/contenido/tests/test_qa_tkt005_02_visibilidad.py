"""AC-129 / QA-TKT005-02 (DEC-AUTO-912) y OBS-04: nada no publicado en la API pública.

Un contenido PUBLICADO pero incoherente (destino con el tipo principal en BORRADOR, itinerario sin
tipos publicados o cuyo destino no es visible, publicado sin fila de subtipo) se trata como no
publicado en TODA la API pública: 404 en el detalle y fuera de listados, facetas, mapa, meses,
aleatorio, búsqueda, relacionados, colecciones, glosario, créditos, índice y conteos.
"""

from __future__ import annotations

import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.busqueda import services as busqueda
from apps.contenido.api.serializers import DestinoDetalleSerializer
from apps.contenido.models import (
    Contenido,
    DestinoTipoAventura,
    ItinerarioTipoAventura,
)
from apps.contenido.tests import publicos
from apps.contenido.tests.conftest import PUBLICO
from apps.contenido.tests.fabricas import campos_publicado

pytestmark = pytest.mark.django_db


def _slugs(api, ruta: str, **parametros) -> set[str]:
    respuesta = api.get(f"{PUBLICO}{ruta}", parametros)
    assert respuesta.status_code == 200, respuesta.content[:300]
    return {r["slug"] for r in respuesta.json()["resultados"]}


def _texto(api, ruta: str, **parametros) -> str:
    respuesta = api.get(f"{PUBLICO}{ruta}", parametros)
    assert respuesta.status_code == 200, (ruta, respuesta.content[:300])
    return respuesta.content.decode()


@pytest.fixture
def tipo_principal_borrador(mundo):
    """El Cocuy (publicado) pasa a tener como tipo principal un tipo en BORRADOR."""
    cocuy, borrador = mundo["cocuy"], mundo["tipo_borrador"]
    DestinoTipoAventura.objects.create(destino=cocuy, tipo_aventura=borrador)
    type(cocuy).objects.filter(pk=cocuy.pk).update(tipo_principal=borrador)
    publicos.coleccion("Solo Cocuy", [cocuy.contenido])
    return mundo


def test_AC_129_destino_con_tipo_principal_borrador_no_es_publico(api, tipo_principal_borrador):
    m = tipo_principal_borrador
    cocuy = m["cocuy"].contenido.slug
    borrador = m["tipo_borrador"].contenido
    assert api.get(f"{PUBLICO}/destinos/{cocuy}").status_code == 404
    for ruta in ("/destinos", "/destinos/mapa", "/indice", "/busqueda/destinos"):
        parametros = {"q": "cocuy"} if "busqueda" in ruta else {}
        assert cocuy not in _slugs(api, ruta, **parametros), ruta
    for _ in range(15):
        assert api.get(f"{PUBLICO}/destinos/aleatorio").json()["slug"] != cocuy
    assert cocuy not in _texto(api, "/meses")
    assert cocuy not in _texto(api, "/inicio")
    assert cocuy not in _texto(api, "/glosario")
    assert cocuy not in _texto(api, "/busqueda", q="glaciar")
    for ruta in (
        f"/destinos/{m['salento'].contenido.slug}",
        f"/guias/{m['guia_equipo'].contenido.slug}",
        f"/tipos-aventura/{m['tipos'][0].contenido.slug}",
        f"/colecciones/{m['coleccion'].contenido.slug}",
    ):
        cuerpo = _texto(api, ruta)
        assert f'"{cocuy}"' not in cuerpo, ruta
        assert borrador.slug not in cuerpo, ruta
        assert borrador.titulo not in cuerpo, ruta
    # Su itinerario deja de ser público (su destino no lo es).
    ruta = m["ruta_cocuy"].contenido.slug
    assert api.get(f"{PUBLICO}/itinerarios/{ruta}").status_code == 404
    assert ruta not in _slugs(api, "/itinerarios")
    # Conteos y facetas sin él.
    tipos = api.get(f"{PUBLICO}/tipos-aventura").json()["resultados"]
    assert {t["titulo"]: t["numero_destinos"] for t in tipos}["Trekking"] == 3
    facetas = api.get(f"{PUBLICO}/facetas/destinos").json()
    assert borrador.slug not in {t["slug"] for t in facetas["tipos"]}
    assert 4 not in [n["nivel"] for n in facetas["dificultad"]]  # solo El Cocuy tenía 4
    colecciones = api.get(f"{PUBLICO}/colecciones").json()["resultados"]
    assert {c["titulo"]: c["numero_elementos"] for c in colecciones}["Solo Cocuy"] == 0
    # Créditos: su portada no se acredita como usada por él.
    creditos = api.get(f"{PUBLICO}/creditos").json()["resultados"]
    assert all(cocuy not in {u["slug"] for u in c["usado_en"]} for c in creditos)


def test_AC_129_itinerario_con_destino_no_publicado_no_se_expone(api, mundo, logs_json):
    ruta, colca = mundo["ruta_colca"], mundo["colca"]
    Contenido.objects.filter(pk=colca.pk).update(
        estado_editorial="RETIRADO", retirado_en=timezone.now(), motivo_retiro="Prueba"
    )
    slug = ruta.contenido.slug
    assert api.get(f"{PUBLICO}/itinerarios/{slug}").status_code == 404
    assert slug not in _slugs(api, "/itinerarios")
    assert slug not in _texto(api, "/inicio")
    assert slug not in _texto(api, f"/tipos-aventura/{mundo['tipos'][1].contenido.slug}")
    # Error de integridad registrado sin PII (solo id y tipo).
    errores = [e for e in logs_json() if e.get("event") == "integridad_contenido_publicado"]
    assert errores == [
        {**errores[0], "contenido_id": ruta.pk, "tipo": "ITINERARIO", "level": "error"}
    ]
    assert ruta.contenido.titulo not in logs_json.texto()


def test_AC_129_itinerario_sin_tipos_publicados_no_es_publico(api, mundo):
    ruta = mundo["ruta_colca"]
    ItinerarioTipoAventura.objects.filter(itinerario=ruta).delete()
    ItinerarioTipoAventura.objects.create(itinerario=ruta, tipo_aventura=mundo["tipo_borrador"])
    assert api.get(f"{PUBLICO}/itinerarios/{ruta.contenido.slug}").status_code == 404
    assert ruta.contenido.slug not in _slugs(api, "/itinerarios")


def test_AC_129_relacion_curada_a_un_borrador_no_se_expone(api, mundo):
    publicos.relacionar(mundo["salento"].contenido, mundo["borrador"].contenido)
    cuerpo = _texto(api, f"/destinos/{mundo['salento'].contenido.slug}")
    assert mundo["borrador"].contenido.slug not in cuerpo


def test_AC_129_serializer_no_expone_tipo_principal_no_publicado(tipo_principal_borrador):
    cocuy = tipo_principal_borrador["cocuy"]
    cocuy.refresh_from_db()
    assert DestinoDetalleSerializer().get_tipo_principal(cocuy) is None


# ---------------------------------------------------------------------------
# OBS-04: registro publicado sin subtipo → omitido en índice y búsqueda; nada responde 500
# ---------------------------------------------------------------------------
def test_OBS_04_publicado_sin_subtipo_se_omite_y_el_comando_falla_al_final(api, mundo):
    huerfana = Contenido.objects.create(
        tipo="GUIA",
        slug="guia-sin-subtipo",
        titulo="Guía sin subtipo",
        **campos_publicado("GUIA"),
    )
    resultado = busqueda.reindexar_todo()
    assert resultado.omitidos == 1
    assert resultado.documentos == 11
    assert api.get(f"{PUBLICO}/indice").status_code == 200
    assert huerfana.slug not in _slugs(api, "/indice")
    assert api.get(f"{PUBLICO}/guias/{huerfana.slug}").status_code == 404
    with pytest.raises(CommandError, match="omitidos=1"):
        call_command("reindexar_busqueda", stdout=io.StringIO())
    # El resto del índice se reconstruyó igualmente.
    assert _slugs(api, "/busqueda/destinos", q="cocuy") == {mundo["cocuy"].contenido.slug}
