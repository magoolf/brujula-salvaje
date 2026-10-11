"""TKT-062: ActorRef y referencias reales en las respuestas del panel editorial.

- `creado_por`/`actualizado_por` (ContenidoPanelMeta, ContenidoResumenPanel) y `creado_por` de las
  revisiones (RevisionResumen) llevan la etiqueta de `components.schemas.ActorRef` ("Usuario o
  seudónimo si la cuenta está anonimizada; 'sistema' para procesos"); antes era `#<id>`.
- `ContenidoPanelMeta.referencias` trae los datos de visualización de los ids referenciados
  (medios, contenidos, términos, taxonomías); antes venía siempre vacío.
- Sin N+1: número de consultas fijo, independiente de cuántas referencias o autores haya.
Todo se valida contra los esquemas de contracts/openapi.yaml (JSON Schema 2020-12).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.auditoria.models import RevisionContenido
from apps.contenido import services
from apps.contenido.api import panel_selectors
from apps.contenido.api.panel_serializers import PANEL_SERIALIZER
from apps.contenido.models import Contenido, RelacionContenido
from apps.contenido.tests import publicos
from apps.contenido.tests.conftest import validar_contra
from apps.contenido.tests.fabricas import crear_cuenta
from apps.core.actores import precargar_actores
from apps.cuentas.models import CuentaStaff, EstadoCuenta
from apps.medios.models import Medio, MedioDerivado

pytestmark = pytest.mark.django_db

PANEL = "/api/v1/panel/contenidos"


def _anonimizar(cuenta: CuentaStaff) -> None:
    """Deja la cuenta ANONIMIZADA cumpliendo ck_cuenta_staff_anonimizada."""
    ahora = timezone.now()
    CuentaStaff.objects.filter(pk=cuenta.pk).update(
        usuario=None,
        nombre_visible=None,
        estado=EstadoCuenta.ANONIMIZADA,
        password="!inutilizable",  # nosec B106 (hash inutilizable, no es un secreto)
        desactivado_en=ahora,
        anonimizado_en=ahora,
    )


def _miniatura(medio: Medio) -> dict[str, Any]:
    # `publicos.medio()` crea AVIF 800, WEBP 800 y JPEG 1600: el más estrecho, WebP a igual ancho.
    return {
        "id": medio.pk,
        "estado": medio.estado,
        "texto_alternativo": medio.texto_alternativo,
        "licencia_codigo": medio.licencia.codigo if medio.licencia else None,
        "url_miniatura": f"/api/v1/panel/medios/{medio.pk}/archivo?ancho=800&formato=WEBP",
    }


def _ref(c: Contenido) -> dict[str, Any]:
    return {
        "tipo": c.tipo,
        "id": c.pk,
        "titulo": c.titulo,
        "slug": c.slug,
        "estado_editorial": c.estado_editorial,
    }


def _destino_con_referencias(
    relacionados: int = 2, terminos: int = 1, estado: str = "PUBLICADO"
) -> dict[str, Any]:
    autora = crear_cuenta("autora.062")
    editor = crear_cuenta("editor.062")
    t1 = publicos.tipo("Senderismo 062")
    t2 = publicos.tipo("Escalada 062")
    pais = publicos.pais("Colombia 062")
    destino = publicos.destino(
        "Destino 062",
        tipos=[t1, t2],
        pais_=pais,
        estado=estado,
        creado_por=autora,
        actualizado_por=editor,
    )
    c = destino.contenido
    otros = [
        publicos.guia(f"Guía relacionada {i}", estado="BORRADOR").contenido
        for i in range(relacionados)
    ]
    publicos.relacionar(c, *otros)
    vocablos = [publicos.termino(f"Vivac {i}", usado_en=[c]).contenido for i in range(terminos)]
    galeria = [
        Medio.objects.get(pk=pk)
        for pk in c.galeria.order_by("orden", "id").values_list("medio_id", flat=True)
    ]
    return {
        "contenido": c,
        "autora": autora,
        "editor": editor,
        "tipos": [t1.contenido, t2.contenido],
        "pais": pais,
        "relacionados": otros,
        "terminos": vocablos,
        "medios": [c.portada, *galeria],
    }


def test_TKT062_detalle_destino_trae_referencias_reales_y_actores(cliente_editora: Client) -> None:
    mundo = _destino_con_referencias()
    c = mundo["contenido"]
    respuesta = cliente_editora.get(f"{PANEL}/destinos/{c.pk}")
    assert respuesta.status_code == 200, respuesta.content
    datos = respuesta.json()

    assert validar_contra("DestinoPanel", datos) == []
    assert datos["creado_por"] == {"id": mundo["autora"].pk, "etiqueta": "autora.062"}
    assert datos["actualizado_por"] == {"id": mundo["editor"].pk, "etiqueta": "editor.062"}
    assert datos["referencias"] == {
        "medios": [_miniatura(m) for m in mundo["medios"]],
        "contenidos": [_ref(r) for r in mundo["relacionados"]],
        "terminos": [{"id": t.pk, "termino": t.titulo} for t in mundo["terminos"]],
        "taxonomias": [
            {"clase": "PAIS", "id": mundo["pais"].pk, "nombre": "Colombia 062"},
            *({"clase": "TIPO", "id": t.pk, "nombre": t.titulo} for t in mundo["tipos"]),
        ],
    }
    # Cada id referenciado por los campos tiene su dato de visualización.
    ids_medios = {m["id"] for m in datos["referencias"]["medios"]}
    assert {datos["portada_id"], *datos["galeria_ids"]} == ids_medios
    assert {r["id"] for r in datos["relaciones"]} == {
        r["id"] for r in datos["referencias"]["contenidos"]
    }
    assert set(datos["terminos_ids"]) == {t["id"] for t in datos["referencias"]["terminos"]}


def test_TKT062_put_devuelve_las_mismas_referencias(cliente_editora: Client, editora: Any) -> None:
    mundo = _destino_con_referencias(estado="BORRADOR")
    c = mundo["contenido"]
    detalle = cliente_editora.get(f"{PANEL}/destinos/{c.pk}").json()
    cuerpo = {k: detalle[k] for k in services.CAMPOS_EDITABLES["DESTINO"]}
    cuerpo["version"] = detalle["version"]
    respuesta = cliente_editora.put(
        f"{PANEL}/destinos/{c.pk}", cuerpo, content_type="application/json"
    )
    assert respuesta.status_code == 200, respuesta.content
    datos = respuesta.json()
    assert validar_contra("DestinoPanel", datos) == []
    assert datos["referencias"] == detalle["referencias"]
    assert datos["actualizado_por"] == {"id": editora.cuenta.pk, "etiqueta": "editora.uno"}
    assert datos["creado_por"] == {"id": mundo["autora"].pk, "etiqueta": "autora.062"}


def test_TKT062_referencias_de_itinerario_guia_y_coleccion(cliente_editora: Client) -> None:
    tipo = publicos.tipo("Trekking 062")
    base = publicos.destino("Base 062", tipos=[tipo])
    otro = publicos.destino("Otro 062", tipos=[tipo], estado="RETIRADO")
    itinerario = publicos.itinerario("Itinerario 062", base, tipos=[tipo])
    categoria = publicos.categoria()
    guia = publicos.guia("Guía 062", destinos=[base, otro], tipos=[tipo], categoria_=categoria)
    coleccion = publicos.coleccion("Colección 062", [base.contenido, itinerario.contenido])

    casos: list[tuple[str, Contenido, str, dict[str, Any]]] = [
        (
            "itinerarios",
            itinerario.contenido,
            "ItinerarioPanel",
            {
                "contenidos": [_ref(base.contenido)],
                "taxonomias": [{"clase": "TIPO", "id": tipo.pk, "nombre": "Trekking 062"}],
            },
        ),
        (
            "guias",
            guia.contenido,
            "GuiaPanel",
            {
                "contenidos": [_ref(base.contenido), _ref(otro.contenido)],
                "taxonomias": [
                    {"clase": "CATEGORIA", "id": categoria.pk, "nombre": categoria.nombre},
                    {"clase": "TIPO", "id": tipo.pk, "nombre": "Trekking 062"},
                ],
            },
        ),
        (
            "colecciones",
            coleccion.contenido,
            "ColeccionPanel",
            {
                "contenidos": [_ref(base.contenido), _ref(itinerario.contenido)],
                "taxonomias": [],
            },
        ),
    ]
    for ruta, contenido, componente, esperado in casos:
        datos = cliente_editora.get(f"{PANEL}/{ruta}/{contenido.pk}").json()
        assert validar_contra(componente, datos) == [], ruta
        assert datos["referencias"]["contenidos"] == esperado["contenidos"], ruta
        assert datos["referencias"]["taxonomias"] == esperado["taxonomias"], ruta
        assert datos["referencias"]["medios"][0]["id"] == contenido.portada_id, ruta
        assert datos["actualizado_por"] == {"id": None, "etiqueta": "sistema"}, ruta


def test_TKT062_medio_sin_derivados_se_omite_de_referencias(cliente_editora: Client) -> None:
    """DEC-AUTO-1081 (mismo criterio que inicio): sin derivado no hay `url_miniatura`."""
    mundo = _destino_con_referencias()
    c = mundo["contenido"]
    MedioDerivado.objects.filter(medio_id=c.portada_id).delete()
    datos = cliente_editora.get(f"{PANEL}/destinos/{c.pk}").json()
    assert validar_contra("DestinoPanel", datos) == []
    assert c.portada_id not in {m["id"] for m in datos["referencias"]["medios"]}
    assert len(datos["referencias"]["medios"]) == len(mundo["medios"]) - 1


def test_TKT062_actor_anonimizado_y_sin_actor(cliente_editora: Client) -> None:
    mundo = _destino_con_referencias()
    c = mundo["contenido"]
    _anonimizar(mundo["editor"])
    Contenido.objects.filter(pk=c.pk).update(creado_por=None)
    datos = cliente_editora.get(f"{PANEL}/destinos/{c.pk}").json()
    assert datos["creado_por"] == {"id": None, "etiqueta": "sistema"}
    assert datos["actualizado_por"] == {
        "id": mundo["editor"].pk,
        "etiqueta": f"Cuenta anonimizada #{mundo['editor'].pk}",
    }
    assert "editor.062" not in str(datos)


def test_TKT062_listado_lleva_la_etiqueta_del_usuario(cliente_editora: Client) -> None:
    mundo = _destino_con_referencias()
    datos = cliente_editora.get(f"{PANEL}/destinos").json()
    assert validar_contra("PaginaContenidoResumen", datos) == []
    fila = next(r for r in datos["resultados"] if r["id"] == mundo["contenido"].pk)
    assert fila["actualizado_por"] == {"id": mundo["editor"].pk, "etiqueta": "editor.062"}
    assert not any(r["actualizado_por"]["etiqueta"].startswith("#") for r in datos["resultados"])


def test_TKT062_revisiones_llevan_la_etiqueta_del_usuario(cliente_editora: Client) -> None:
    mundo = _destino_con_referencias()
    c = mundo["contenido"]
    for numero, autor in ((1, mundo["autora"]), (2, mundo["editor"]), (3, None)):
        RevisionContenido.objects.create(
            contenido=c,
            tipo_contenido=c.tipo,
            numero_revision=numero,
            motivo="PUBLICACION" if numero == 1 else "ACTUALIZACION",
            instantanea={"estado_editorial": "PUBLICADO"},
            creado_por=autor,
        )
    _anonimizar(mundo["editor"])

    lista = cliente_editora.get(f"{PANEL}/destinos/{c.pk}/revisiones").json()
    assert validar_contra("PaginaRevisionResumen", lista) == []
    assert [r["creado_por"] for r in lista["resultados"]] == [
        {"id": None, "etiqueta": "sistema"},
        {"id": mundo["editor"].pk, "etiqueta": f"Cuenta anonimizada #{mundo['editor'].pk}"},
        {"id": mundo["autora"].pk, "etiqueta": "autora.062"},
    ]
    detalle = cliente_editora.get(f"{PANEL}/destinos/{c.pk}/revisiones/1").json()
    assert validar_contra("RevisionDetalle", detalle) == []
    assert detalle["creado_por"] == {"id": mundo["autora"].pk, "etiqueta": "autora.062"}


def _consultas_serializar(contenido: Contenido) -> int:
    fresco = Contenido.objects.get(pk=contenido.pk)
    with CaptureQueriesContext(connection) as consultas:
        PANEL_SERIALIZER[fresco.tipo](fresco).data  # noqa: B018 (serializa)
    return len(consultas.captured_queries)


def test_TKT062_referencias_sin_n_mas_1(django_assert_num_queries: Any) -> None:
    """`referencias_panel` cuesta 4 consultas fijas (contenidos; medios + derivados; país) con 1
    o con 9 relacionados, 10 términos y 10 medios, y el detalle completo no crece con ellas."""
    pocos = _destino_con_referencias(relacionados=1, terminos=1)["contenido"]
    campos = services.campos_editables(pocos)
    with django_assert_num_queries(4):
        panel_selectors.referencias_panel(campos)
    base = _consultas_serializar(pocos)

    RelacionContenido.objects.filter(origen=pocos).delete()
    publicos.relacionar(
        pocos, *(publicos.guia(f"Guía extra {i}", estado="BORRADOR").contenido for i in range(9))
    )
    for i in range(9):
        publicos.termino(f"Término extra {i}", usado_en=[pocos])
    publicos.galeria(pocos, 6)
    campos = services.campos_editables(pocos)
    with django_assert_num_queries(4):
        referencias = panel_selectors.referencias_panel(campos)
    assert len(referencias["contenidos"]) == 9
    assert len(referencias["terminos"]) == 10
    assert len(referencias["medios"]) == 1 + 3 + 6
    assert _consultas_serializar(pocos) == base


def test_TKT062_actores_del_detalle_en_una_sola_consulta() -> None:
    """creado_por y actualizado_por (cuentas distintas) se cargan juntas: 1 consulta, no 2."""
    c = _destino_con_referencias()["contenido"]
    fresco = Contenido.objects.get(pk=c.pk)
    with CaptureQueriesContext(connection) as consultas:
        precargar_actores([fresco], "creado_por", "actualizado_por")
        assert fresco.creado_por.usuario == "autora.062"
        assert fresco.actualizado_por.usuario == "editor.062"
    assert len(consultas.captured_queries) == 1


def test_TKT062_listado_sin_n_mas_1_por_autor(cliente_editora: Client) -> None:
    """El listado hace las mismas consultas con 1 autor que con 6 autores distintos."""
    tipo = publicos.tipo("Tipo listado 062")
    autora = crear_cuenta("autora.lista")
    for i in range(6):
        publicos.destino(f"Listado A {i}", tipos=[tipo], actualizado_por=autora)
    with CaptureQueriesContext(connection) as uno:
        r = cliente_editora.get(f"{PANEL}/destinos")
    assert r.status_code == 200

    for i, c in enumerate(Contenido.objects.filter(tipo="DESTINO").order_by("id")):
        Contenido.objects.filter(pk=c.pk).update(actualizado_por=crear_cuenta(f"autora.lista{i}"))
    with CaptureQueriesContext(connection) as varios:
        r = cliente_editora.get(f"{PANEL}/destinos")
    etiquetas = {f["actualizado_por"]["etiqueta"] for f in r.json()["resultados"]}
    assert len(etiquetas) == 6
    assert len(varios.captured_queries) == len(uno.captured_queries)
