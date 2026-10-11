"""TKT-068 (MEDIUM, rendimiento; trazabilidad TKT-062): `MedioPanel.numero_usos` y
`MedioPanel.en_uso_publicado` se calculan por LOTE (`selectors_panel.resumen_usos`, 3 consultas
agregadas) en lugar de `services.usos` + `services._en_uso_publicado` por medio (6 consultas por
medio: el listado de 48 medios del panel hacía cerca de 300 consultas).

- AC-1: el listado del panel hace el MISMO número de consultas con 1 medio que con 48 (página
  completa), con usos y autoras distintas en cada medio (ActorRef `subido_por` también por lote).
- AC-2: los valores son idénticos a la implementación anterior (`services.usos`/
  `services._en_uso_publicado`, que siguen siendo el oráculo y los usa `retirar`): sin uso, usado
  en borrador, usado en publicado, usado en varios contenidos, hero de inicio y medio retirado.
- AC-3: el detalle de un medio no empeora (los usos pasan de 6 consultas a 3).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from apps.contenido.models import Contenido, ContenidoMedio, EstadoEditorial
from apps.contenido.tests import publicos
from apps.contenido.tests.conftest import validar_contra
from apps.contenido.tests.fabricas import crear_cuenta
from apps.inicio.models import ID_SINGLETON, ConfigInicio
from apps.medios import selectors_panel, services
from apps.medios.models import EstadoMedio, Medio

pytestmark = pytest.mark.django_db

RUTA = "/api/v1/panel/medios"
TABLAS_DE_USO = ('"contenido"', '"contenido_medio"', '"config_inicio"')


def _en_galeria(medio: Medio, contenido: Contenido, orden: int = 10) -> None:
    ContenidoMedio.objects.create(
        contenido=contenido, tipo_contenido=contenido.tipo, medio=medio, orden=orden
    )


def _oraculo(medio_id: int) -> tuple[int, bool]:
    """Implementación anterior de `MedioPanelSerializer` (antes de TKT-068)."""
    return len(services.usos(medio_id)), services._en_uso_publicado(medio_id)


def _escenarios() -> dict[str, Medio]:
    """Un medio por caso del ticket (y algunos combinados)."""
    medios: dict[str, Medio] = {}
    medios["sin_uso"] = publicos.medio()

    medios["portada_borrador"] = publicos.medio()
    publicos.destino(
        "Borrador con portada",
        tipos=[],
        estado=EstadoEditorial.BORRADOR,
        portada=medios["portada_borrador"],
    )

    medios["galeria_borrador"] = publicos.medio()
    borrador = publicos.destino("Borrador con galería", tipos=[], estado=EstadoEditorial.BORRADOR)
    _en_galeria(medios["galeria_borrador"], borrador.contenido)

    medios["portada_publicado"] = publicos.medio()
    publicos.destino("Publicado con portada", tipos=[], portada=medios["portada_publicado"])

    medios["galeria_publicado"] = publicos.medio()
    publicado = publicos.destino("Publicado con galería", tipos=[])
    _en_galeria(medios["galeria_publicado"], publicado.contenido)

    # Varios contenidos: portada de un publicado y de un borrador + galería de un retirado y de
    # otro borrador (4 usos, publicado).
    medios["varios"] = publicos.medio()
    publicos.destino("Varios 1", tipos=[], portada=medios["varios"])
    publicos.destino(
        "Varios 2", tipos=[], estado=EstadoEditorial.BORRADOR, portada=medios["varios"]
    )
    retirado = publicos.destino("Varios 3", tipos=[], estado=EstadoEditorial.RETIRADO)
    _en_galeria(medios["varios"], retirado.contenido)
    _en_galeria(medios["varios"], borrador.contenido, orden=11)

    # Varios contenidos, ninguno publicado (portada y galería del MISMO borrador + un retirado).
    medios["varios_sin_publicar"] = publicos.medio()
    otro_borrador = publicos.destino(
        "Varios sin publicar",
        tipos=[],
        estado=EstadoEditorial.BORRADOR,
        portada=medios["varios_sin_publicar"],
    )
    _en_galeria(medios["varios_sin_publicar"], otro_borrador.contenido)
    _en_galeria(medios["varios_sin_publicar"], retirado.contenido, orden=11)

    medios["hero"] = publicos.medio()
    publicos.config_inicio(hero=medios["hero"])

    # Medio retirado: sin uso y usado solo por un borrador (retirar exige que no haya publicado).
    medios["retirado_sin_uso"] = publicos.medio(estado=EstadoMedio.RETIRADO)
    medios["retirado_en_borrador"] = publicos.medio(estado=EstadoMedio.RETIRADO)
    _en_galeria(medios["retirado_en_borrador"], otro_borrador.contenido, orden=12)
    return medios


ESPERADO = {
    "sin_uso": (0, False),
    "portada_borrador": (1, False),
    "galeria_borrador": (1, False),
    "portada_publicado": (1, True),
    "galeria_publicado": (1, True),
    "varios": (4, True),
    "varios_sin_publicar": (3, False),
    "hero": (1, True),
    "retirado_sin_uso": (0, False),
    "retirado_en_borrador": (1, False),
}


def test_AC_TKT068_02_resumen_por_lote_identico_a_la_implementacion_anterior() -> None:
    medios = _escenarios()
    resumen = selectors_panel.resumen_usos(m.pk for m in medios.values())
    for caso, medio in medios.items():
        obtenido = resumen.get(medio.pk, selectors_panel.SIN_USOS)
        assert (obtenido.numero_usos, obtenido.en_uso_publicado) == _oraculo(medio.pk), caso
        assert _oraculo(medio.pk) == ESPERADO[caso], caso
    # Un id sin usos no aparece (el llamante usa SIN_USOS); un lote vacío no consulta.
    assert medios["sin_uso"].pk not in resumen
    with CaptureQueriesContext(connection) as consultas:
        assert selectors_panel.resumen_usos([]) == {}
    assert len(consultas) == 0


def test_AC_TKT068_02_listado_y_detalle_identicos_a_la_implementacion_anterior(
    cliente_editora: Client,
) -> None:
    medios = _escenarios()
    pagina = cliente_editora.get(RUTA).json()
    assert validar_contra("PaginaMedioPanel", pagina) == []
    por_id = {fila["id"]: fila for fila in pagina["resultados"]}
    for caso, medio in medios.items():
        esperado = _oraculo(medio.pk)
        fila = por_id[medio.pk]
        assert (fila["numero_usos"], fila["en_uso_publicado"]) == esperado, caso
        detalle = cliente_editora.get(f"{RUTA}/{medio.pk}").json()
        assert validar_contra("MedioPanel", detalle) == []
        assert (detalle["numero_usos"], detalle["en_uso_publicado"]) == esperado, caso
        assert detalle == fila, caso


def test_AC_TKT068_02_filtro_en_uso_coherente_con_numero_usos(cliente_editora: Client) -> None:
    """El filtro `en_uso` (anterior a TKT-068, sin cambios) solo mira portada y galería: el hero
    de inicio cuenta en `numero_usos` pero no en el filtro, así que queda fuera de esta prueba."""
    medios = _escenarios()
    ids = {m.pk for caso, m in medios.items() if caso != "hero"}
    for en_uso in ("true", "false"):
        filas = cliente_editora.get(RUTA, {"en_uso": en_uso}).json()["resultados"]
        propias = [f for f in filas if f["id"] in ids]
        assert propias
        assert all((f["numero_usos"] > 0) == (en_uso == "true") for f in propias)


def marca(cantidad: int) -> str:
    """Texto que solo llevan los medios de `_poblar(cantidad)` (filtro `q` del listado): los
    destinos crean además medios de galería que, sin filtro, también entrarían en la página."""
    return f"lote{cantidad}tkt068"


def _poblar(cantidad: int) -> list[Medio]:
    """`cantidad` medios con autora propia y usos variados (portada publicada, galería en
    borrador y, el primero, hero): el peor caso para un N+1 en usos y en ActorRef."""
    medios = []
    for i in range(cantidad):
        medio = publicos.medio(
            subido_por=crear_cuenta(f"fotografa.068.{cantidad}.{i}"),
            texto_alternativo=f"{marca(cantidad)} {i}",
        )
        if i % 2 == 0:
            publicos.destino(f"Publicado {cantidad}-{i}", tipos=[], portada=medio)
        else:
            borrador = publicos.destino(
                f"Borrador {cantidad}-{i}", tipos=[], estado=EstadoEditorial.BORRADOR
            )
            _en_galeria(medio, borrador.contenido)
        medios.append(medio)
    ConfigInicio.objects.update_or_create(
        pk=ID_SINGLETON,
        defaults={"hero_titular": "Hero", "hero_subtitulo": "Sub", "hero_medio": medios[0]},
    )
    return medios


def test_AC_TKT068_01_listado_mismas_consultas_con_1_y_con_48_medios(
    cliente_editora: Client, django_assert_num_queries: Any
) -> None:
    (unico,) = _poblar(1)
    con_uno = cliente_editora.get(RUTA, {"q": marca(1)}).json()
    assert [f["id"] for f in con_uno["resultados"]] == [unico.pk]
    with CaptureQueriesContext(connection) as uno:
        assert cliente_editora.get(RUTA, {"q": marca(1)}).status_code == 200

    _poblar(48)
    with django_assert_num_queries(len(uno)):
        respuesta = cliente_editora.get(RUTA, {"q": marca(48)})
    datos = respuesta.json()
    assert validar_contra("PaginaMedioPanel", datos) == []
    assert len(datos["resultados"]) == 48  # página completa (tamano_pagina del listado)
    etiquetas = {f["subido_por"]["etiqueta"] for f in datos["resultados"]}
    assert len(etiquetas) == 48  # 48 autoras distintas, sin N+1 en ActorRef
    for fila in datos["resultados"]:
        assert (fila["numero_usos"], fila["en_uso_publicado"]) == _oraculo(fila["id"])


def test_AC_TKT068_01_usos_del_listado_en_tres_consultas(cliente_editora: Client) -> None:
    _poblar(10)
    with CaptureQueriesContext(connection) as consultas:
        assert cliente_editora.get(RUTA).status_code == 200
    de_uso = [
        q["sql"]
        for q in consultas.captured_queries
        if any(t in q["sql"].split(" WHERE ")[0] for t in TABLAS_DE_USO)
        and '"medio"' not in q["sql"].split(" WHERE ")[0]
    ]
    assert len(de_uso) == 3, de_uso


def test_AC_TKT068_03_detalle_no_empeora(cliente_editora: Client) -> None:
    """El detalle serializa un medio sin precarga: sus usos cuestan 3 consultas (antes 6: 3 de
    `services.usos` + 3 de `services._en_uso_publicado`), y precargado, ninguna."""
    from apps.medios.api.serializers import MedioPanelSerializer, precargar_panel

    (medio,) = _poblar(1)
    fresco = Medio.objects.select_related("licencia").prefetch_related("derivados").get(pk=medio.pk)
    with CaptureQueriesContext(connection) as sin_precarga:
        datos: Any = MedioPanelSerializer(fresco).data
    assert (datos["numero_usos"], datos["en_uso_publicado"]) == _oraculo(medio.pk) == (2, True)
    # 3 de usos + 1 de la cuenta de `subido_por`.
    assert len(sin_precarga) == 4

    fresco = Medio.objects.select_related("licencia").prefetch_related("derivados").get(pk=medio.pk)
    precargar_panel([fresco])
    with CaptureQueriesContext(connection) as precargado:
        assert MedioPanelSerializer(fresco).data == datos
    assert len(precargado) == 0
    detalle = cliente_editora.get(f"{RUTA}/{medio.pk}").json()
    assert (detalle["numero_usos"], detalle["en_uso_publicado"]) == (2, True)
