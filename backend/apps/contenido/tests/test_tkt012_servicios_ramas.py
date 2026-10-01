"""TKT-012 (deuda de cobertura, Skill_Backend §8: services > 90 %): ramas de
`apps.contenido.services` sin ninguna prueba (hallazgo de QA en TKT-006: services.py 56-87 %).

Cada prueba fija una regla de negocio concreta del ciclo editorial (no solo ejecuta líneas):
errores de transición y de versión, slug inmutable/en uso, co-publicación inválida, cascada de
"actualizar publicación" (sin confirmar, impacto modificado, bloqueada y confirmada), análisis de
publicación, vista previa por tipo, páginas institucionales y guardado de todos los campos por
tipo (por HTTP, para recorrer también los serializers del panel).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from django.test import Client

from apps.contenido import services
from apps.contenido.models import (
    ChecklistItem,
    Contenido,
    DiaItinerario,
    ElementoColeccion,
    EstadoEditorial,
    TipoContenido,
)
from apps.contenido.tests import publicos
from apps.contenido.tests.fabricas import crear_cuenta
from apps.contenido.tests.test_ac_tkt006_02_servicios_ciclo import (
    _datos_destino_validos,
    _datos_tipo_validos,
    _rellenar_relacionados,
)

T = TipoContenido
E = EstadoEditorial
AYER = date.today() - timedelta(days=1)
BASE = "/api/v1/panel/contenidos"

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor() -> int:
    return crear_cuenta("editora.tkt012.servicios").pk


def _json(cliente: Client, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
    return getattr(cliente, metodo)(ruta, cuerpo, content_type="application/json")


def _destino_publicado_valido(actor: int, *tipos_extra: int) -> tuple[Contenido, int, list[int]]:
    """Destino PUBLICADO que cumple todos los requisitos (con un tipo principal co-publicado).
    Devuelve (contenido, id del tipo principal, ids de la galería)."""
    _rellenar_relacionados()
    portada = publicos.medio()
    galeria = [publicos.medio().pk for _ in range(3)]
    tipo = services.crear_borrador(
        T.TIPO, actor, {**_datos_tipo_validos(titulo="Tipo principal"), "portada_id": portada.pk}
    )
    destino = services.crear_borrador(
        T.DESTINO,
        actor,
        {
            **_datos_destino_validos(),
            "pais_id": publicos.pais().pk,
            "tipos_ids": [tipo.pk, *tipos_extra],
            "tipo_principal_id": tipo.pk,
            "portada_id": portada.pk,
            "galeria_ids": galeria,
        },
    )
    services.publicar(
        T.DESTINO, destino.pk, actor, version=1, copublicar_tipos=[{"id": tipo.pk, "version": 1}]
    )
    destino.refresh_from_db()
    return destino, tipo.pk, galeria


def _datos_actualizacion(destino: Contenido, tipos_ids: list[int], galeria: list[int]) -> dict:
    return {
        **_datos_destino_validos(),
        "tipos_ids": tipos_ids,
        "tipo_principal_id": tipos_ids[0],
        "portada_id": destino.portada_id,
        "galeria_ids": galeria,
    }


# ---------------------------------------------------------------------------
# Guardado de todos los campos por tipo (HTTP: services._aplicar_* + panel serializers)
# ---------------------------------------------------------------------------
def test_TKT012_itinerario_guarda_y_reemplaza_todos_sus_campos(cliente_editora: Client) -> None:
    destino = publicos.destino("Destino del itinerario", tipos=[])
    tipo = publicos.tipo("Senderismo de prueba")
    medio = publicos.medio()
    cuerpo = {
        "titulo": "Travesía completa",
        "destino_id": destino.contenido_id,
        "resumen": "Resumen",
        "duracion_dias": 2,
        "dificultad": 3,
        "tipos_ids": [tipo.pk],
        "distancia_total_km": 25.5,
        "desnivel_acumulado_m": 900,
        "riesgos_seguridad": "<p>Riesgos <script>x</script></p>",
        "portada_id": medio.pk,
        "galeria_ids": [medio.pk],
        "dias": [
            {"numero_dia": 1, "titulo": "Día uno", "actividades": "<p>Subir</p>"},
            {
                "numero_dia": 2,
                "titulo": "Día dos",
                "actividades": "<p>Bajar</p>",
                "distancia_km": 12.5,
                "consejos": "<p>Agua</p>",
            },
        ],
    }
    creado = _json(cliente_editora, "post", f"{BASE}/itinerarios", cuerpo)
    assert creado.status_code == 201, creado.content
    datos = creado.json()
    assert datos["destino_id"] == destino.contenido_id
    assert [d["numero_dia"] for d in datos["dias"]] == [1, 2]
    assert "script" not in datos["riesgos_seguridad"]
    assert datos["galeria_ids"] == [medio.pk]

    cuerpo["dias"] = [{"numero_dia": 1, "titulo": "Único día", "actividades": "<p>Todo</p>"}]
    actualizado = _json(
        cliente_editora,
        "put",
        f"{BASE}/itinerarios/{datos['id']}",
        cuerpo | {"version": datos["version"]},
    )
    assert actualizado.status_code == 200, actualizado.content
    assert DiaItinerario.objects.filter(itinerario_id=datos["id"]).count() == 1


def test_TKT012_guia_coleccion_y_tipo_guardan_sus_campos(cliente_editora: Client) -> None:
    destino = publicos.destino("Destino de la guía", tipos=[])
    tipo = publicos.tipo("Tipo de la guía")
    medio = publicos.medio()

    guia = _json(
        cliente_editora,
        "post",
        f"{BASE}/guias",
        {
            "titulo": "Guía completa",
            "categoria_id": publicos.categoria().pk,
            "resumen": "Resumen",
            "cuerpo": "<p>uno dos tres</p>",
            "destinos_ids": [destino.contenido_id],
            "tipos_ids": [tipo.pk],
            "remite_a_metodologia": True,
            "portada_id": medio.pk,
        },
    )
    assert guia.status_code == 201, guia.content
    assert guia.json()["palabras"] == 3
    assert guia.json()["destinos_ids"] == [destino.contenido_id]

    coleccion = _json(
        cliente_editora,
        "post",
        f"{BASE}/colecciones",
        {
            "titulo": "Colección completa",
            "resumen": "Resumen",
            "descripcion": "<p>Desc</p>",
            "portada_id": medio.pk,
            "elementos": [
                {"tipo_contenido": "DESTINO", "contenido_id": destino.contenido_id, "orden": 0}
            ],
        },
    )
    assert coleccion.status_code == 201, coleccion.content
    assert ElementoColeccion.objects.filter(coleccion_id=coleccion.json()["id"]).count() == 1

    tipo_nuevo = _json(
        cliente_editora,
        "post",
        f"{BASE}/tipos-aventura",
        {
            "titulo": "Tipo completo",
            "resumen": "Resumen",
            "descripcion": "<p>Desc</p>",
            "nivel_exigencia": 2,
            "orden": 5,
            "portada_id": medio.pk,
            "checklist": [
                {"texto": "Casco", "grupo": "Equipo", "esencial": True, "orden": 0},
                {"texto": "Agua", "esencial": False, "orden": 1},
            ],
        },
    )
    assert tipo_nuevo.status_code == 201, tipo_nuevo.content
    assert ChecklistItem.objects.filter(tipo_aventura_id=tipo_nuevo.json()["id"]).count() == 2
    assert tipo_nuevo.json()["orden"] == 5


# ---------------------------------------------------------------------------
# Slug: en uso, inmutable tras publicar, propuesto si llega vacío
# ---------------------------------------------------------------------------
def test_TKT012_slug_en_uso_y_slug_vacio_se_propone(actor: int) -> None:
    services.crear_borrador(T.DESTINO, actor, {"titulo": "Uno", "slug": "ocupado"})
    otro = services.crear_borrador(T.DESTINO, actor, {"titulo": "Dos"})
    with pytest.raises(services.SlugEnUso):
        services.actualizar(T.DESTINO, otro.pk, actor, {"slug": "ocupado"}, version=1)
    resultado = services.actualizar(
        T.DESTINO, otro.pk, actor, {"titulo": "Dos renombrado", "slug": None}, version=1
    )
    assert resultado.contenido.slug == "dos-renombrado"


def test_TKT012_slug_de_termino_en_borrador_y_tras_publicar(actor: int) -> None:
    destino = publicos.destino("Destino del término", tipos=[])
    termino = services.crear_borrador(
        T.TERMINO, actor, {"titulo": "Cordada", "fecha_ultima_revision": AYER}
    )
    resultado = services.actualizar(
        T.TERMINO, termino.pk, actor, {"slug": "cordada-alpina"}, version=1
    )
    assert resultado.contenido.slug == "cordada-alpina"

    from apps.contenido.models import ContenidoTermino

    ContenidoTermino.objects.create(
        contenido=destino.contenido, tipo_contenido=T.DESTINO, termino_id=termino.pk
    )
    services.publicar(T.TERMINO, termino.pk, actor, version=2, copublicar_tipos=None)
    with pytest.raises(services.SlugInmutable):
        services.actualizar(T.TERMINO, termino.pk, actor, {"slug": "otro"}, version=3)


def test_TKT012_termino_duplicado_al_renombrar(actor: int) -> None:
    services.crear_borrador(T.TERMINO, actor, {"titulo": "Glaciar"})
    otro = services.crear_borrador(T.TERMINO, actor, {"titulo": "Morrena"})
    with pytest.raises(services.Duplicado):
        services.actualizar(T.TERMINO, otro.pk, actor, {"titulo": "GLACIAR"}, version=1)


# ---------------------------------------------------------------------------
# actualizar(): transiciones y campos de operación no permitidos
# ---------------------------------------------------------------------------
def test_TKT012_actualizar_retirado_exige_reactivar(actor: int) -> None:
    termino = publicos.termino("Retirado", [], estado=E.RETIRADO)
    with pytest.raises(services.TransicionInvalida):
        services.actualizar(T.TERMINO, termino.contenido_id, actor, {"titulo": "X"}, version=1)


@pytest.mark.parametrize(
    ("tipo", "operacion"),
    [
        (T.TERMINO, {"copublicar_tipos": [{"id": 1, "version": 1}]}),
        (T.DESTINO, {"copublicar_tipos": [{"id": 1, "version": 1}]}),
        (T.DESTINO, {"confirmar_cascada": True}),
    ],
)
def test_TKT012_operacion_de_publicacion_no_permitida_en_borrador(
    actor: int, tipo: str, operacion: dict[str, Any]
) -> None:
    contenido = services.crear_borrador(tipo, actor, {"titulo": f"Borrador {tipo}"})
    with pytest.raises(services.ErrorApi) as error:
        services.actualizar(tipo, contenido.pk, actor, {"titulo": "Y", **operacion}, version=1)
    assert error.value.codigo == "campo_no_permitido"


def test_TKT012_actualizar_publicacion_valida_requisitos_y_slug(actor: int) -> None:
    destino = publicos.destino("Publicado", tipos=[])
    termino = publicos.termino("Vinculado", [destino.contenido])
    with pytest.raises(services.SlugInmutable):
        services.actualizar(
            T.TERMINO,
            termino.contenido_id,
            actor,
            {"slug": "otro-slug"},
            version=termino.contenido.version,
        )
    with pytest.raises(services.PublicacionInvalida):
        services.actualizar(
            T.TERMINO,
            termino.contenido_id,
            actor,
            {"fecha_ultima_revision": None},
            version=termino.contenido.version,
        )


def test_TKT012_actualizar_termino_publicado_por_http_no_es_500(cliente_editora: Client) -> None:
    """Regresión encontrada al cubrir `_actualizar_publicacion`: el término no está en
    `APLICAR_CAMPOS` y editar uno PUBLICADO respondía 500 (KeyError 'TERMINO')."""
    destino = publicos.destino("Destino del glosario publicado", tipos=[])
    termino = publicos.termino("Collado", [destino.contenido])
    publicos.termino("Portillo", [destino.contenido])
    ruta = f"{BASE}/glosario/{termino.contenido_id}"
    version = cliente_editora.get(ruta).json()["version"]
    base = {"titulo": "Collado", "fecha_ultima_revision": AYER.isoformat()}

    respuesta = _json(
        cliente_editora,
        "put",
        ruta,
        base | {"definicion": "Paso entre montañas", "version": version},
    )
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["definicion"] == "Paso entre montañas"
    assert respuesta.json()["estado_editorial"] == "PUBLICADO"

    duplicado = _json(
        cliente_editora, "put", ruta, base | {"titulo": "PORTILLO", "version": version + 1}
    )
    assert duplicado.status_code == 409, duplicado.content


# ---------------------------------------------------------------------------
# Cascada de "actualizar publicación" (quitar tipos de un destino publicado)
# ---------------------------------------------------------------------------
def test_TKT012_quitar_tipo_exclusivo_pide_confirmar_y_valida_impacto(actor: int) -> None:
    exclusivo = publicos.tipo("Tipo exclusivo a quitar")
    destino, principal, galeria = _destino_publicado_valido(actor, exclusivo.pk)
    datos = _datos_actualizacion(destino, [principal], galeria)

    with pytest.raises(services.CascadaSinConfirmar) as sin_confirmar:
        services.actualizar(T.DESTINO, destino.pk, actor, dict(datos), version=destino.version)
    impacto = sin_confirmar.value.extra["impacto_cascada"]
    assert [t["id"] for t in impacto["tipos_en_cascada"]] == [exclusivo.pk]

    with pytest.raises(services.ImpactoModificado):
        services.actualizar(
            T.DESTINO,
            destino.pk,
            actor,
            {**datos, "cascada_confirmada": [{"tipo": T.TIPO, "id": principal}]},
            version=destino.version,
        )

    resultado = services.actualizar(
        T.DESTINO,
        destino.pk,
        actor,
        {**datos, "cascada_confirmada": [{"tipo": T.TIPO, "id": exclusivo.pk}]},
        version=destino.version,
    )
    assert [e["origen"] for e in resultado.entidades_afectadas] == ["CASCADA"]
    exclusivo.contenido.refresh_from_db()
    assert exclusivo.contenido.estado_editorial == E.RETIRADO


def test_TKT012_quitar_tipo_usado_por_itinerario_publicado_queda_bloqueado(actor: int) -> None:
    compartido = publicos.tipo("Tipo con itinerario")
    destino, principal, galeria = _destino_publicado_valido(actor, compartido.pk)
    otro = publicos.destino("Otro destino del itinerario", tipos=[])
    publicos.itinerario("Ruta que usa el tipo", otro, tipos=[compartido])
    datos = _datos_actualizacion(destino, [principal], galeria)
    with pytest.raises(services.CascadaBloqueada) as error:
        services.actualizar(
            T.DESTINO, destino.pk, actor, {**datos, "confirmar_cascada": True}, version=2
        )
    assert error.value.extra["total_usos"] == 1


def test_TKT012_quitar_tipo_con_otro_destino_publicado_no_cascada(actor: int) -> None:
    compartido = publicos.tipo("Tipo compartido sin cascada")
    destino, principal, galeria = _destino_publicado_valido(actor, compartido.pk)
    publicos.destino("Otro destino que lo conserva", tipos=[compartido])
    datos = _datos_actualizacion(destino, [principal], galeria)
    resultado = services.actualizar(T.DESTINO, destino.pk, actor, datos, version=2)
    assert resultado.entidades_afectadas == []


# ---------------------------------------------------------------------------
# Co-publicación y publicar(): ramas de error
# ---------------------------------------------------------------------------
def _destino_borrador_con_tipo(actor: int, *, tipo_en_borrador: bool = True) -> tuple[int, int]:
    _rellenar_relacionados()
    portada = publicos.medio()
    tipo = services.crear_borrador(
        T.TIPO, actor, {**_datos_tipo_validos(titulo="Tipo a copublicar"), "portada_id": portada.pk}
    )
    destino = services.crear_borrador(
        T.DESTINO,
        actor,
        {
            **_datos_destino_validos(),
            "tipos_ids": [tipo.pk],
            "tipo_principal_id": tipo.pk,
            "portada_id": portada.pk,
            "galeria_ids": [publicos.medio().pk for _ in range(3)],
        },
    )
    return destino.pk, tipo.pk


def test_TKT012_copublicar_tipo_no_asociado_o_sin_pedir(actor: int) -> None:
    destino_id, _tipo_id = _destino_borrador_con_tipo(actor)
    ajeno = publicos.tipo("Tipo ajeno al destino")
    with pytest.raises(services.PublicacionInvalida) as error:
        services.publicar(
            T.DESTINO,
            destino_id,
            actor,
            version=1,
            copublicar_tipos=[{"id": ajeno.pk, "version": 1}],
        )
    codigos = {
        e["code"]
        for entidad in error.value.extra["errores_por_entidad"]
        for e in entidad["errores"]
    }
    assert {"copublicacion_tipo_no_asociado", "tipo_no_publicado"} <= codigos


def test_TKT012_copublicar_con_version_desactualizada_es_conflicto(actor: int) -> None:
    destino_id, tipo_id = _destino_borrador_con_tipo(actor)
    with pytest.raises(services.ConflictoVersion) as error:
        services.publicar(
            T.DESTINO,
            destino_id,
            actor,
            version=1,
            copublicar_tipos=[{"id": tipo_id, "version": 7}],
        )
    assert error.value.extra["entidades_en_conflicto"][0]["id"] == tipo_id


def test_TKT012_copublicar_tipo_incompleto_reporta_sus_errores(actor: int) -> None:
    destino_id, tipo_id = _destino_borrador_con_tipo(actor)
    Contenido.objects.filter(pk=tipo_id).update(seo_descripcion=None)
    with pytest.raises(services.PublicacionInvalida) as error:
        services.publicar(
            T.DESTINO,
            destino_id,
            actor,
            version=1,
            copublicar_tipos=[{"id": tipo_id, "version": 1}],
        )
    roles = {e["rol"] for e in error.value.extra["errores_por_entidad"]}
    assert "COPUBLICACION" in roles
    assert any(clave.startswith("copublicar_tipos.") for clave in error.value.errors)


def test_TKT012_publicar_ramas_de_error(actor: int) -> None:
    termino = services.crear_borrador(T.TERMINO, actor, {"titulo": "Arista"})
    with pytest.raises(services.ErrorApi) as error:
        services.publicar(
            T.TERMINO, termino.pk, actor, version=1, copublicar_tipos=[{"id": 1, "version": 1}]
        )
    assert error.value.codigo == "campo_no_permitido"
    with pytest.raises(services.ConflictoVersion):
        services.publicar(T.TERMINO, termino.pk, actor, version=9, copublicar_tipos=None)
    publicado = publicos.termino("Ya publicado", [])
    with pytest.raises(services.TransicionInvalida):
        services.publicar(
            T.TERMINO, publicado.contenido_id, actor, version=1, copublicar_tipos=None
        )


# ---------------------------------------------------------------------------
# retirar() / reactivar(): ramas de error y cascada confirmada explícitamente
# ---------------------------------------------------------------------------
def test_TKT012_retirar_ramas_de_error(actor: int) -> None:
    borrador = services.crear_borrador(T.TERMINO, actor, {"titulo": "Sin publicar"})
    with pytest.raises(services.TransicionInvalida):
        services.retirar(T.TERMINO, borrador.pk, actor, 1, "x", False, None)
    publicado = publicos.termino("Publicado para retirar", [])
    with pytest.raises(services.ConflictoVersion):
        services.retirar(T.TERMINO, publicado.contenido_id, actor, 99, "x", False, None)


def test_TKT012_retirar_destino_con_cascada_confirmada_explicita(actor: int) -> None:
    exclusivo = publicos.tipo("Tipo exclusivo confirmado")
    destino = publicos.destino("Destino confirmado", tipos=[exclusivo])
    with pytest.raises(services.ImpactoModificado):
        services.retirar(
            T.DESTINO, destino.contenido_id, actor, 1, "Cierre", False, [{"tipo": "TIPO", "id": 1}]
        )
    contenido, afectadas = services.retirar(
        T.DESTINO,
        destino.contenido_id,
        actor,
        1,
        "Cierre",
        False,
        [{"tipo": "TIPO", "id": exclusivo.pk}],
    )
    assert contenido.estado_editorial == E.RETIRADO
    assert [a["origen"] for a in afectadas] == ["PRINCIPAL", "CASCADA"]


def test_TKT012_retirar_destino_que_supera_el_limite_de_cascada(
    actor: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    exclusivo = publicos.tipo("Tipo del límite")
    destino = publicos.destino("Destino del límite", tipos=[exclusivo])
    monkeypatch.setattr(services, "LIMITE_CASCADA", 0)
    with pytest.raises(services.ReglaNegocio):
        services.retirar(T.DESTINO, destino.contenido_id, actor, 1, "x", True, None)


def test_TKT012_reactivar_ramas_de_error(actor: int) -> None:
    with pytest.raises(services.TransicionInvalida):
        services.reactivar(T.PAGINA, 1, actor, 1)
    publicado = publicos.termino("No retirado", [])
    with pytest.raises(services.TransicionInvalida):
        services.reactivar(T.TERMINO, publicado.contenido_id, actor, 1)
    retirado = publicos.termino("Retirado de verdad", [], estado=E.RETIRADO)
    with pytest.raises(services.ConflictoVersion):
        services.reactivar(T.TERMINO, retirado.contenido_id, actor, 42)


# ---------------------------------------------------------------------------
# analizar_publicacion()
# ---------------------------------------------------------------------------
def test_TKT012_analizar_borrador_de_destino_incluye_copublicacion(actor: int) -> None:
    destino_id, tipo_id = _destino_borrador_con_tipo(actor)
    analisis = services.analizar_publicacion(T.DESTINO, destino_id, 1)
    assert analisis["operacion"] == "PUBLICAR"
    assert analisis["copublicar_tipos"] == [{"id": tipo_id, "version": 1}]
    assert analisis["copublicacion"][0]["rol"] == "COPUBLICACION"
    assert analisis["confirmable"] is True


def test_TKT012_analizar_actualizacion_de_destino_con_tipos_propuestos(actor: int) -> None:
    exclusivo = publicos.tipo("Tipo exclusivo analizado")
    destino, principal, _galeria = _destino_publicado_valido(actor, exclusivo.pk)
    portada = publicos.medio()
    nuevo = services.crear_borrador(
        T.TIPO,
        actor,
        {
            **_datos_tipo_validos(titulo="Tipo nuevo analizado", seo_descripcion="SEO nueva"),
            "portada_id": portada.pk,
        },
    )
    usado = publicos.destino("Destino con itinerario del exclusivo", tipos=[])
    publicos.itinerario("Itinerario que bloquea", usado, tipos=[exclusivo])

    analisis = services.analizar_publicacion(
        T.DESTINO, destino.pk, destino.version, [principal, nuevo.pk, 987654], principal
    )
    assert analisis["operacion"] == "ACTUALIZAR_PUBLICACION"
    assert [c["id"] for c in analisis["copublicacion"]] == [nuevo.pk]
    assert [t["id"] for t in analisis["tipos_en_cascada"]] == [exclusivo.pk]
    assert analisis["bloqueos_cascada"][0]["total_itinerarios"] == 1
    assert analisis["confirmable"] is False


def test_TKT012_analizar_ramas_de_error_y_publicado_no_destino(actor: int) -> None:
    publicado = publicos.termino("Analizado publicado", [])
    with pytest.raises(services.ConflictoVersion):
        services.analizar_publicacion(T.TERMINO, publicado.contenido_id, 99)
    with pytest.raises(services.ErrorApi) as error:
        services.analizar_publicacion(T.TERMINO, publicado.contenido_id, 1, [1], None)
    assert error.value.codigo == "campo_no_permitido"
    analisis = services.analizar_publicacion(T.TERMINO, publicado.contenido_id, 1)
    assert analisis["operacion"] == "ACTUALIZAR_PUBLICACION"
    retirado = publicos.termino("Analizado retirado", [], estado=E.RETIRADO)
    with pytest.raises(services.TransicionInvalida):
        services.analizar_publicacion(T.TERMINO, retirado.contenido_id, 1)


# ---------------------------------------------------------------------------
# Revisiones y páginas institucionales
# ---------------------------------------------------------------------------
def test_TKT012_restaurar_revision_inexistente_es_404(actor: int) -> None:
    termino = publicos.termino("Sin revisiones", [])
    with pytest.raises(services.NoEncontrado):
        services.restaurar_revision(T.TERMINO, termino.contenido_id, 5, actor)


def test_TKT012_actualizar_pagina_incompleta_es_publicacion_invalida(actor: int) -> None:
    pagina = publicos.pagina("AVISO_LEGAL", "Aviso legal")
    with pytest.raises(services.PublicacionInvalida):
        services.actualizar(
            T.PAGINA,
            pagina.contenido_id,
            actor,
            {"cuerpo": "", "version_documento": "2.0"},
            version=1,
        )
    resultado = services.actualizar(
        T.PAGINA,
        pagina.contenido_id,
        actor,
        {
            "titulo": "Aviso legal v2",
            "seo_titulo": "Aviso",
            "seo_descripcion": "Aviso legal del sitio",
            "fecha_ultima_revision": AYER,
            "cuerpo": "<p>Texto legal vigente</p>",
            "version_documento": "2.0",
            "vigente_desde": AYER,
        },
        version=1,
    )
    assert resultado.contenido.version == 2
    assert resultado.contenido.pagina.version_documento == "2.0"


# ---------------------------------------------------------------------------
# Vista previa por tipo (sin persistir, AC-111)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("ruta", "forma"),
    [
        ("destinos", "DestinoDetalle"),
        ("itinerarios", "ItinerarioDetalle"),
        ("guias", "GuiaDetalle"),
        ("tipos-aventura", "TipoAventuraDetalle"),
        ("colecciones", "ColeccionDetalle"),
    ],
)
def test_TKT012_vista_previa_por_tipo_no_persiste(
    cliente_editora: Client, ruta: str, forma: str
) -> None:
    destino = publicos.destino("Destino previsto", tipos=[])
    tipo = publicos.tipo("Tipo previsto")
    medio = publicos.medio()
    comunes = {
        "titulo": f"Vista previa {ruta}",
        "seo_descripcion": "SEO de la vista previa",
        "relaciones": [{"tipo": "DESTINO", "id": destino.contenido_id}],
    }
    especificos: dict[str, dict[str, Any]] = {
        "destinos": {
            "tipos_ids": [tipo.pk],
            "tipo_principal_id": tipo.pk,
            "galeria_ids": [medio.pk],
            "meses_mejor_epoca": [1],
        },
        "itinerarios": {
            "destino_id": destino.contenido_id,
            "tipos_ids": [tipo.pk],
            "dias": [{"numero_dia": 1, "titulo": "Día", "actividades": "<p>a</p>"}],
        },
        "guias": {"fuentes": [{"titulo": "Fuente", "url": "https://example.org"}]},
        "tipos-aventura": {
            "id": tipo.pk,
            "checklist": [{"texto": "Casco", "esencial": True, "orden": 0}],
        },
        "colecciones": {
            "elementos": [
                {"tipo_contenido": "DESTINO", "contenido_id": destino.contenido_id, "orden": 0}
            ]
        },
    }
    antes = Contenido.objects.count()
    respuesta = _json(
        cliente_editora, "post", f"{BASE}/{ruta}/vista-previa", comunes | especificos[ruta]
    )
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["forma"] == forma
    assert respuesta.json()["requisitos_publicacion"]["cumple"] is False
    assert Contenido.objects.count() == antes
