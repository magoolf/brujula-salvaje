"""AC-TKT006: ciclo editorial del panel a nivel de servicio (apps.contenido.services).

Cubre CRUD de borrador, bloqueo optimista, publicar/retirar/reactivar, co-publicación
Destino+Tipo (CHG-BP-001) y retiro en cascada Destino→Itinerarios+Tipos, revisiones y auditoría.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from apps.auditoria.models import (
    AccionAuditoria,
    EventoAuditoria,
    MotivoRevision,
    RevisionContenido,
)
from apps.busqueda.models import BusquedaDocumento
from apps.busqueda.services import reindexar_todo
from apps.contenido import services
from apps.contenido.models import Contenido, EstadoEditorial, TipoContenido
from apps.contenido.tests import publicos
from apps.contenido.tests.fabricas import crear_cuenta

T = TipoContenido
E = EstadoEditorial
AYER = date.today() - timedelta(days=1)

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor() -> int:
    return crear_cuenta("editora.tkt006").pk


def _rellenar_relacionados(cantidad: int = 3) -> None:
    """Destinos publicados y visibles (con tipo principal publicado, RULE-001) para que RULE-006
    (≥3 relacionados) se cumpla por afinidad automática."""
    relleno = publicos.tipo("Tipo de relleno")
    for i in range(cantidad):
        publicos.destino(f"Relleno {i}", tipos=[relleno])


def _datos_tipo_validos(**overrides: object) -> dict[str, object]:
    datos: dict[str, object] = {
        "titulo": "Barranquismo",
        "resumen": "Resumen del tipo",
        "descripcion": "<p>Descripción del tipo</p>",
        "nivel_exigencia": 3,
        "fecha_ultima_revision": AYER,
        "seo_descripcion": "SEO única del tipo",
        "checklist": [],
    }
    datos.update(overrides)
    return datos


def _datos_destino_validos(**overrides: object) -> dict[str, object]:
    datos: dict[str, object] = {
        "titulo": "Cañón Salvaje",
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
        "seo_descripcion": "SEO única del destino",
    }
    datos.update(overrides)
    return datos


# ---------------------------------------------------------------------------
# CRUD de borrador y bloqueo optimista (término: el tipo con menos campos)
# ---------------------------------------------------------------------------
def test_AC_TKT006_02_crear_borrador_termino(actor: int) -> None:
    contenido = services.crear_borrador(
        T.TERMINO, actor, {"titulo": "Vía ferrata", "definicion": "Ruta equipada con cables"}
    )
    assert contenido.estado_editorial == E.BORRADOR
    assert contenido.version == 1
    assert contenido.slug == "via-ferrata"
    assert contenido.termino_glosario.definicion == "Ruta equipada con cables"


def test_AC_TKT006_02_actualizar_borrador_incrementa_version(actor: int) -> None:
    contenido = services.crear_borrador(T.TERMINO, actor, {"titulo": "Crampones"})
    resultado = services.actualizar(
        T.TERMINO, contenido.pk, actor, {"titulo": "Crampones", "definicion": "Nueva"}, version=1
    )
    assert resultado.contenido.version == 2
    assert resultado.contenido.termino_glosario.definicion == "Nueva"


def test_AC_TKT006_02_conflicto_de_version(actor: int) -> None:
    contenido = services.crear_borrador(T.TERMINO, actor, {"titulo": "Piolet"})
    with pytest.raises(services.ConflictoVersion):
        services.actualizar(T.TERMINO, contenido.pk, actor, {"titulo": "Piolet"}, version=99)


def test_AC_TKT006_02_duplicado_de_titulo_termino(actor: int) -> None:
    services.crear_borrador(T.TERMINO, actor, {"titulo": "Repelamiento"})
    with pytest.raises(services.Duplicado):
        services.crear_borrador(T.TERMINO, actor, {"titulo": "REPELAMIENTO"})


def test_AC_TKT006_02_eliminar_borrador_nunca_publicado(actor: int) -> None:
    contenido = services.crear_borrador(T.TERMINO, actor, {"titulo": "Rapel"})
    services.eliminar_borrador(T.TERMINO, contenido.pk, actor, version=1)
    assert not Contenido.objects.filter(pk=contenido.pk).exists()


def test_AC_TKT006_02_no_se_puede_eliminar_lo_ya_publicado(actor: int) -> None:
    _rellenar_relacionados()
    contenido = services.crear_borrador(
        T.TERMINO, actor, {"titulo": "Grieta", "fecha_ultima_revision": AYER}
    )
    destino_usa = publicos.destino("Usa el término", tipos=[])
    from apps.contenido.models import ContenidoTermino

    ContenidoTermino.objects.create(
        contenido=destino_usa.contenido, tipo_contenido=T.DESTINO, termino_id=contenido.pk
    )
    services.publicar(T.TERMINO, contenido.pk, actor, version=1, copublicar_tipos=None)
    services.retirar(
        T.TERMINO,
        contenido.pk,
        actor,
        version=2,
        motivo="obsoleto",
        confirmar_cascada=False,
        cascada_confirmada=None,
    )
    reactivado = services.reactivar(T.TERMINO, contenido.pk, actor, version=3)
    assert reactivado.estado_editorial == E.BORRADOR
    with pytest.raises(services.TransicionInvalida):
        services.eliminar_borrador(T.TERMINO, contenido.pk, actor, version=4)


# ---------------------------------------------------------------------------
# Publicar / retirar / reactivar (término: transición simple de una sola entidad)
# ---------------------------------------------------------------------------
def test_AC_TKT006_02_publicar_termino_requiere_vinculo_publicado(actor: int) -> None:
    contenido = services.crear_borrador(
        T.TERMINO, actor, {"titulo": "Cornisa", "fecha_ultima_revision": AYER}
    )
    with pytest.raises(services.PublicacionInvalida):
        services.publicar(T.TERMINO, contenido.pk, actor, version=1, copublicar_tipos=None)


def test_AC_TKT006_02_publicar_termino_vinculado_crea_revision_y_audita(actor: int) -> None:
    destino_usa = publicos.destino("Destino con glosario", tipos=[])
    contenido = services.crear_borrador(
        T.TERMINO, actor, {"titulo": "Chimenea", "fecha_ultima_revision": AYER}
    )
    from apps.contenido.models import ContenidoTermino

    ContenidoTermino.objects.create(
        contenido=destino_usa.contenido, tipo_contenido=T.DESTINO, termino_id=contenido.pk
    )
    publicado, afectadas = services.publicar(
        T.TERMINO, contenido.pk, actor, version=1, copublicar_tipos=None
    )
    assert publicado.estado_editorial == E.PUBLICADO
    assert publicado.primera_publicacion_en is not None
    assert len(afectadas) == 1
    assert afectadas[0]["origen"] == "PRINCIPAL"
    assert RevisionContenido.objects.filter(
        contenido=publicado, motivo=MotivoRevision.PUBLICACION
    ).exists()
    assert EventoAuditoria.objects.filter(
        accion=AccionAuditoria.PUBLICAR, entidad_id=publicado.pk
    ).exists()


def test_AC_TKT006_02_retirar_y_reactivar_termino(actor: int) -> None:
    destino_usa = publicos.destino("Otro destino con glosario", tipos=[])
    contenido = services.crear_borrador(
        T.TERMINO, actor, {"titulo": "Sendero", "fecha_ultima_revision": AYER}
    )
    from apps.contenido.models import ContenidoTermino

    ContenidoTermino.objects.create(
        contenido=destino_usa.contenido, tipo_contenido=T.DESTINO, termino_id=contenido.pk
    )
    services.publicar(T.TERMINO, contenido.pk, actor, version=1, copublicar_tipos=None)
    contenido.refresh_from_db()
    slug_original = contenido.slug

    retirado, _afectadas = services.retirar(
        T.TERMINO,
        contenido.pk,
        actor,
        version=2,
        motivo="Ya no aplica",
        confirmar_cascada=False,
        cascada_confirmada=None,
    )
    assert retirado.estado_editorial == E.RETIRADO
    assert retirado.motivo_retiro == "Ya no aplica"
    assert RevisionContenido.objects.filter(
        contenido=retirado, motivo=MotivoRevision.RETIRO
    ).exists()

    reactivado = services.reactivar(T.TERMINO, contenido.pk, actor, version=3)
    assert reactivado.estado_editorial == E.BORRADOR
    assert reactivado.slug == slug_original
    assert reactivado.retirado_en is None


def test_AC_TKT006_02_pagina_institucional_nunca_se_retira(actor: int) -> None:
    pagina = publicos.pagina("ACERCA_DE", "Acerca de nosotros")
    with pytest.raises(services.TransicionInvalida):
        services.retirar(
            T.PAGINA,
            pagina.contenido_id,
            actor,
            version=1,
            motivo="x",
            confirmar_cascada=False,
            cascada_confirmada=None,
        )


# ---------------------------------------------------------------------------
# Revisiones
# ---------------------------------------------------------------------------
def test_AC_TKT006_02_listar_y_restaurar_revision(actor: int) -> None:
    destino_usa = publicos.destino("Destino revisiones", tipos=[])
    contenido = services.crear_borrador(
        T.TERMINO, actor, {"titulo": "Vivac", "fecha_ultima_revision": AYER}
    )
    from apps.contenido.models import ContenidoTermino

    ContenidoTermino.objects.create(
        contenido=destino_usa.contenido, tipo_contenido=T.DESTINO, termino_id=contenido.pk
    )
    services.publicar(T.TERMINO, contenido.pk, actor, version=1, copublicar_tipos=None)
    revisiones = list(services.listar_revisiones(T.TERMINO, contenido.pk))
    assert len(revisiones) == 1
    revision = services.obtener_revision(T.TERMINO, contenido.pk, revisiones[0].numero_revision)
    assert revision.instantanea["titulo"] == "Vivac"
    restaurada = services.restaurar_revision(
        T.TERMINO, contenido.pk, revision.numero_revision, actor
    )
    assert restaurada["numero_revision"] == revision.numero_revision
    assert "estado_editorial" not in restaurada["datos"]
    assert EventoAuditoria.objects.filter(accion=AccionAuditoria.RESTAURAR_REVISION).exists()


# ---------------------------------------------------------------------------
# Co-publicación Destino + Tipo (CHG-BP-001, la pieza central del ticket)
# ---------------------------------------------------------------------------
def test_AC_TKT006_02_copublicacion_destino_y_tipo(actor: int) -> None:
    _rellenar_relacionados()
    portada = publicos.medio()
    galeria_medios = [publicos.medio() for _ in range(3)]

    tipo_contenido = services.crear_borrador(
        T.TIPO, actor, {**_datos_tipo_validos(), "portada_id": portada.pk}
    )
    destino_contenido = services.crear_borrador(
        T.DESTINO,
        actor,
        {
            **_datos_destino_validos(),
            "tipos_ids": [tipo_contenido.pk],
            "tipo_principal_id": tipo_contenido.pk,
            "portada_id": portada.pk,
            "galeria_ids": [m.pk for m in galeria_medios],
        },
    )

    publicado, afectadas = services.publicar(
        T.DESTINO,
        destino_contenido.pk,
        actor,
        version=1,
        copublicar_tipos=[{"id": tipo_contenido.pk, "version": 1}],
    )

    assert publicado.estado_editorial == E.PUBLICADO
    assert len(afectadas) == 2
    roles = {a["tipo"]: a["origen"] for a in afectadas}
    assert roles[T.DESTINO] == "PRINCIPAL"
    assert roles[T.TIPO] == "COPUBLICACION"

    tipo_contenido.refresh_from_db()
    assert tipo_contenido.estado_editorial == E.PUBLICADO
    assert RevisionContenido.objects.filter(
        contenido=tipo_contenido, motivo=MotivoRevision.PUBLICACION
    ).exists()
    assert EventoAuditoria.objects.filter(
        accion=AccionAuditoria.PUBLICAR, entidad_id=tipo_contenido.pk
    ).exists()


# ---------------------------------------------------------------------------
# TKT-013 (regresión): el reindexado vivía DENTRO de _confirmar_publicacion_entidad y se disparaba
# por entidad en el momento exacto en que CADA UNA pasaba a PUBLICADO. En una co-publicación
# Destino+Tipo, el destino se confirmaba (y reindexaba) primero, con su tipo_principal todavía en
# BORRADOR; como la visibilidad del destino exige tipo_principal ya PUBLICADO (AC-129) y nada
# volvía a reindexarlo después, quedaba fuera del índice de búsqueda de forma permanente pese a
# estar PUBLICADO en BD. Se verifica el índice REAL (`BusquedaDocumento`, mismo mecanismo que
# apps/busqueda/tests/test_ac_tkt005_03_busqueda.py), sin ningún reindexado externo posterior.
# ---------------------------------------------------------------------------
def test_AC_TKT013_publicar_copublicacion_destino_queda_visible_en_indice_de_inmediato(
    actor: int,
) -> None:
    _rellenar_relacionados()
    portada = publicos.medio()
    galeria_medios = [publicos.medio() for _ in range(3)]

    tipo_contenido = services.crear_borrador(
        T.TIPO, actor, {**_datos_tipo_validos(), "portada_id": portada.pk}
    )
    destino_contenido = services.crear_borrador(
        T.DESTINO,
        actor,
        {
            **_datos_destino_validos(),
            # Requerido para la VISIBILIDAD en el índice (q_visible), aunque reglas.py no lo exige
            # para publicar: sin país, el destino nunca sería indexable y el test no probaría nada.
            "pais_id": publicos.pais().pk,
            "tipos_ids": [tipo_contenido.pk],
            "tipo_principal_id": tipo_contenido.pk,
            "portada_id": portada.pk,
            "galeria_ids": [m.pk for m in galeria_medios],
        },
    )

    services.publicar(
        T.DESTINO,
        destino_contenido.pk,
        actor,
        version=1,
        copublicar_tipos=[{"id": tipo_contenido.pk, "version": 1}],
    )

    # Sin ningún reindexado externo: el propio `publicar()` debe dejar ambas entidades visibles.
    assert BusquedaDocumento.objects.filter(contenido=destino_contenido).exists()
    assert BusquedaDocumento.objects.filter(contenido=tipo_contenido).exists()


def test_AC_TKT013_actualizar_publicacion_copublicacion_destino_queda_visible_en_indice(
    actor: int,
) -> None:
    """Segundo sitio del mismo bug: `_actualizar_publicacion` reindexaba el destino ANTES de
    confirmar los tipos co-publicados en la misma actualización (p. ej. cambiar el tipo_principal
    de un destino ya publicado a un tipo nuevo, co-publicándolo en la misma llamada)."""
    _rellenar_relacionados()
    portada = publicos.medio()
    galeria_medios = [publicos.medio() for _ in range(3)]

    tipo_inicial = services.crear_borrador(
        T.TIPO, actor, {**_datos_tipo_validos(titulo="Tipo inicial"), "portada_id": portada.pk}
    )
    destino_contenido = services.crear_borrador(
        T.DESTINO,
        actor,
        {
            **_datos_destino_validos(),
            # Requerido para la VISIBILIDAD en el índice (q_visible); ver comentario equivalente
            # en el test anterior.
            "pais_id": publicos.pais().pk,
            "tipos_ids": [tipo_inicial.pk],
            "tipo_principal_id": tipo_inicial.pk,
            "portada_id": portada.pk,
            "galeria_ids": [m.pk for m in galeria_medios],
        },
    )
    services.publicar(
        T.DESTINO,
        destino_contenido.pk,
        actor,
        version=1,
        copublicar_tipos=[{"id": tipo_inicial.pk, "version": 1}],
    )
    destino_contenido.refresh_from_db()

    tipo_nuevo = services.crear_borrador(
        T.TIPO,
        actor,
        {
            **_datos_tipo_validos(titulo="Tipo nuevo", seo_descripcion="SEO única del tipo nuevo"),
            "portada_id": portada.pk,
        },
    )

    resultado = services.actualizar(
        T.DESTINO,
        destino_contenido.pk,
        actor,
        {
            **_datos_destino_validos(),
            "tipos_ids": [tipo_inicial.pk, tipo_nuevo.pk],
            "tipo_principal_id": tipo_nuevo.pk,
            "portada_id": portada.pk,
            "galeria_ids": [m.pk for m in galeria_medios],
            "copublicar_tipos": [{"id": tipo_nuevo.pk, "version": 1}],
        },
        version=destino_contenido.version,
    )

    assert resultado.contenido.estado_editorial == E.PUBLICADO
    tipo_nuevo.refresh_from_db()
    assert tipo_nuevo.estado_editorial == E.PUBLICADO

    # Sin ningún reindexado externo: el propio `actualizar()` debe dejar ambas entidades visibles,
    # con el destino apuntando ya a su nuevo tipo_principal co-publicado.
    assert BusquedaDocumento.objects.filter(contenido=resultado.contenido).exists()
    assert BusquedaDocumento.objects.filter(contenido=tipo_nuevo).exists()


def test_AC_TKT006_02_publicar_destino_con_tipo_retirado_falla(actor: int) -> None:
    _rellenar_relacionados()
    portada = publicos.medio()
    galeria_medios = [publicos.medio() for _ in range(3)]
    tipo_retirado = publicos.tipo("Tipo retirado", estado=E.RETIRADO)

    destino_contenido = services.crear_borrador(
        T.DESTINO,
        actor,
        {
            **_datos_destino_validos(),
            "tipos_ids": [tipo_retirado.pk],
            "tipo_principal_id": tipo_retirado.pk,
            "portada_id": portada.pk,
            "galeria_ids": [m.pk for m in galeria_medios],
        },
    )
    with pytest.raises(services.PublicacionInvalida) as exc:
        services.publicar(T.DESTINO, destino_contenido.pk, actor, version=1, copublicar_tipos=None)
    errores = exc.value.extra["errores_por_entidad"]
    codigos = {e["code"] for entidad in errores for e in entidad["errores"]}
    assert "tipo_retirado" in codigos
    destino_contenido.refresh_from_db()
    assert destino_contenido.estado_editorial == E.BORRADOR


def test_AC_TKT006_02_publicar_tipo_solo_sin_destino_publicado_falla(actor: int) -> None:
    _rellenar_relacionados()
    portada = publicos.medio()
    contenido = services.crear_borrador(
        T.TIPO, actor, {**_datos_tipo_validos(), "portada_id": portada.pk}
    )
    with pytest.raises(services.PublicacionInvalida) as exc:
        services.publicar(T.TIPO, contenido.pk, actor, version=1, copublicar_tipos=None)
    errores = exc.value.extra["errores_por_entidad"]
    codigos = {e["code"] for entidad in errores for e in entidad["errores"]}
    assert "tipo_sin_destino_publicado" in codigos


# ---------------------------------------------------------------------------
# Retiro en cascada Destino → Itinerarios + Tipos (RULE-007, RULE-025)
# ---------------------------------------------------------------------------
def test_AC_TKT006_02_retirar_destino_en_cascada(actor: int) -> None:
    tipo_exclusivo = publicos.tipo("Tipo exclusivo")
    destino_ = publicos.destino("Destino en cascada", tipos=[tipo_exclusivo])
    itinerario_ = publicos.itinerario("Ruta de la cascada", destino_, tipos=[tipo_exclusivo])

    contenido, afectadas = services.retirar(
        T.DESTINO,
        destino_.contenido_id,
        actor,
        version=destino_.contenido.version,
        motivo="Cierre de temporada",
        confirmar_cascada=True,
        cascada_confirmada=None,
    )

    assert contenido.estado_editorial == E.RETIRADO
    origenes = {a["tipo"]: a["origen"] for a in afectadas}
    assert origenes[T.DESTINO] == "PRINCIPAL"
    assert origenes[T.ITINERARIO] == "CASCADA"
    assert origenes[T.TIPO] == "CASCADA"

    itinerario_.contenido.refresh_from_db()
    tipo_exclusivo.contenido.refresh_from_db()
    assert itinerario_.contenido.estado_editorial == E.RETIRADO
    assert tipo_exclusivo.contenido.estado_editorial == E.RETIRADO
    assert tipo_exclusivo.contenido.motivo_retiro == "Cascada: sin destinos publicados (RULE-025)"


def test_AC_TKT006_02_retirar_sin_confirmar_cascada_pide_confirmacion(actor: int) -> None:
    tipo_exclusivo = publicos.tipo("Tipo exclusivo 2")
    destino_ = publicos.destino("Destino en cascada 2", tipos=[tipo_exclusivo])

    with pytest.raises(services.CascadaSinConfirmar) as exc:
        services.retirar(
            T.DESTINO,
            destino_.contenido_id,
            actor,
            version=destino_.contenido.version,
            motivo="x",
            confirmar_cascada=False,
            cascada_confirmada=None,
        )
    assert exc.value.extra["impacto_cascada"]["tipos_en_cascada"]
    destino_.contenido.refresh_from_db()
    assert destino_.contenido.estado_editorial == E.PUBLICADO


def test_AC_TKT006_02_cascada_bloqueada_por_itinerario_de_otro_destino(actor: int) -> None:
    tipo_compartido = publicos.tipo("Tipo compartido")
    destino_a_retirar = publicos.destino("Isla sola", tipos=[tipo_compartido])
    otro_destino = publicos.destino("Otro destino", tipos=[])
    publicos.itinerario("Ruta de otro destino", otro_destino, tipos=[tipo_compartido])

    with pytest.raises(services.CascadaBloqueada) as exc:
        services.retirar(
            T.DESTINO,
            destino_a_retirar.contenido_id,
            actor,
            version=destino_a_retirar.contenido.version,
            motivo="x",
            confirmar_cascada=True,
            cascada_confirmada=None,
        )
    assert exc.value.extra["usos"]
    destino_a_retirar.contenido.refresh_from_db()
    assert destino_a_retirar.contenido.estado_editorial == E.PUBLICADO


def test_AC_TKT006_02_impacto_retiro_sin_efectos(actor: int) -> None:
    tipo_exclusivo = publicos.tipo("Tipo exclusivo 3")
    destino_ = publicos.destino("Destino consultado", tipos=[tipo_exclusivo])
    itinerario_ = publicos.itinerario("Ruta consultada", destino_, tipos=[tipo_exclusivo])

    impacto = services.impacto_retiro(T.DESTINO, destino_.contenido_id)
    assert impacto["retirable"] is True
    assert {c["id"] for c in impacto["itinerarios_en_cascada"]} == {itinerario_.contenido_id}
    assert {c["id"] for c in impacto["tipos_en_cascada"]} == {tipo_exclusivo.pk}
    destino_.contenido.refresh_from_db()
    assert destino_.contenido.estado_editorial == E.PUBLICADO


# ---------------------------------------------------------------------------
# TKT-014 (histórico) → TKT-015 (regla correcta): `retirar()` solo tenía una rama de cascada
# explícita para tipo == T.DESTINO (líneas ~1418-1465), que reindexa las entidades que ELLA MISMA
# retira (itinerarios y tipos "sin destinos publicados", RULE-025). Al retirar un T.TIPO
# DIRECTAMENTE (no vía esa cascada) mientras seguía en uso por contenido publicado, TKT-014
# solo evitó el drift de índice (reindexando el Destino/Itinerario dependiente para que dejara de
# ser visible), pero permitió que la operación se completara. Eso violaba RULE-007/FLOW-012 del
# Blueprint ("no se puede retirar un Tipo... en uso por contenido publicado... nunca de forma
# directa") y el propio contrato (`dependencia_bloqueante` ya documentado para este caso exacto en
# contracts/openapi.yaml). TKT-015 añade el bloqueo real con `DependenciaBloqueante` ANTES de
# tocar nada: la operación se rechaza entera y ninguna entidad cambia de estado. Como consecuencia,
# los dos escenarios que antes ejercitaban el reindexado de TKT-014 (un Tipo que SÍ tiene
# dependientes publicados) ahora nunca llegan a `_confirmar_retiro_entidad`/
# `_reindexar_dependientes_de_tipo`: se convierten en pruebas de bloqueo. `_reindexar_dependientes_
# de_tipo` sigue siendo necesaria como defensa en profundidad (p. ej. una publicación concurrente
# que agregue un nuevo dependiente entre la comprobación de `_usos_publicados_de_tipo` y el commit
# de este `retirar()`, ya que solo se bloquea con `select_for_update()` la fila del propio Tipo, no
# las de sus potenciales dependientes) y sigue cubierta por el caso "sin dependientes" más abajo,
# que sí llega al camino feliz.
#
# CORRECCIÓN QA (ciclo_qa 2/3): la primera versión de `_usos_publicados_de_tipo` solo miraba
# `tipo_principal` en el caso de un Destino, no el M2M `tipos_aventura` completo. QA lo reprodujo
# con datos reales: un Destino PUBLICADO con el tipo como SECUNDARIO permitía retirar ese tipo de
# forma directa sin bloqueo, dejando una fila `DestinoTipoAventura` viva apuntando a un Tipo ya
# RETIRADO — un estado que RULE-002/AC-124 declara imposible en cualquier operación normal
# ("ningún Destino PUBLICADO referencia un Tipo no PUBLICADO", sin distinguir principal de
# secundario) y que AC-129 solo contempla como inconsistencia FORZADA en datos de prueba, nunca
# como algo alcanzable por el panel. Además era inconsistente con el propio archivo:
# `_destinos_publicados_de_tipo` y `_tipos_en_cascada` (usadas por la rama T.DESTINO de `retirar()`
# para RULE-025) ya interpretan "un destino tiene este tipo en uso" como pertenencia al M2M
# `tipos_aventura` completo, no solo como `tipo_principal`. `_usos_publicados_de_tipo` (y, por
# consistencia, `_reindexar_dependientes_de_tipo`) se corrigieron para usar el mismo criterio
# amplio; el test que antes documentaba el alcance estrecho como intencional se invirtió más abajo.
# ---------------------------------------------------------------------------
def test_AC_TKT015_retirar_tipo_directo_bloqueado_si_es_tipo_principal_de_destino_publicado(
    actor: int,
) -> None:
    tipo_ = publicos.tipo("Tipo principal en uso TKT-015")
    destino_ = publicos.destino("Destino con tipo principal en uso TKT-015", tipos=[tipo_])
    reindexar_todo()
    assert BusquedaDocumento.objects.filter(contenido=destino_.contenido).exists()

    with pytest.raises(services.DependenciaBloqueante) as exc:
        services.retirar(
            T.TIPO,
            tipo_.pk,
            actor,
            version=tipo_.contenido.version,
            motivo="Ya no se ofrece",
            confirmar_cascada=False,
            cascada_confirmada=None,
        )
    usos = exc.value.extra["usos"]
    assert exc.value.extra["total_usos"] == 1
    assert usos == [
        {
            "tipo_entidad": "DESTINO",
            "id": destino_.contenido_id,
            "titulo": destino_.contenido.titulo,
            "estado_editorial": E.PUBLICADO,
        }
    ]

    # Nada cambia: ni el destino, ni el tipo, ni el índice de búsqueda de ninguno de los dos.
    destino_.contenido.refresh_from_db()
    assert destino_.contenido.estado_editorial == E.PUBLICADO
    tipo_.contenido.refresh_from_db()
    assert tipo_.contenido.estado_editorial == E.PUBLICADO
    assert BusquedaDocumento.objects.filter(contenido=destino_.contenido).exists()
    assert BusquedaDocumento.objects.filter(contenido=tipo_.contenido).exists()
    assert not EventoAuditoria.objects.filter(
        accion=AccionAuditoria.RETIRAR, entidad_id=tipo_.contenido_id
    ).exists()


def test_AC_TKT015_retirar_tipo_directo_bloqueado_si_lo_usa_itinerario_publicado(
    actor: int,
) -> None:
    tipo_del_destino = publicos.tipo("Tipo del destino TKT-015")
    tipo_del_itinerario = publicos.tipo("Tipo exclusivo del itinerario TKT-015")
    destino_ = publicos.destino("Destino con itinerario TKT-015", tipos=[tipo_del_destino])
    itinerario_ = publicos.itinerario(
        "Ruta dependiente TKT-015", destino_, tipos=[tipo_del_itinerario]
    )
    reindexar_todo()
    assert BusquedaDocumento.objects.filter(contenido=itinerario_.contenido).exists()

    with pytest.raises(services.DependenciaBloqueante) as exc:
        services.retirar(
            T.TIPO,
            tipo_del_itinerario.pk,
            actor,
            version=tipo_del_itinerario.contenido.version,
            motivo="Ya no se ofrece",
            confirmar_cascada=False,
            cascada_confirmada=None,
        )
    usos = exc.value.extra["usos"]
    assert exc.value.extra["total_usos"] == 1
    assert usos == [
        {
            "tipo_entidad": "ITINERARIO",
            "id": itinerario_.contenido_id,
            "titulo": itinerario_.contenido.titulo,
            "estado_editorial": E.PUBLICADO,
        }
    ]

    itinerario_.contenido.refresh_from_db()
    assert itinerario_.contenido.estado_editorial == E.PUBLICADO
    tipo_del_itinerario.contenido.refresh_from_db()
    assert tipo_del_itinerario.contenido.estado_editorial == E.PUBLICADO
    assert BusquedaDocumento.objects.filter(contenido=itinerario_.contenido).exists()
    # El destino no depende de este tipo (su tipo_principal es otro): tampoco cambia.
    assert BusquedaDocumento.objects.filter(contenido=destino_.contenido).exists()


def test_AC_TKT015_retirar_tipo_directo_bloqueado_lista_ambos_usos(actor: int) -> None:
    """Un Tipo que es a la vez `tipo_principal` de un Destino publicado Y está en `tipos_aventura`
    de un Itinerario publicado (de OTRO destino) acumula los dos usos en la misma lista."""
    tipo_ = publicos.tipo("Tipo con doble uso TKT-015")
    destino_principal = publicos.destino(
        "Destino que lo tiene como principal TKT-015", tipos=[tipo_]
    )
    otro_tipo = publicos.tipo("Otro tipo TKT-015")
    otro_destino = publicos.destino("Otro destino TKT-015", tipos=[otro_tipo])
    itinerario_ = publicos.itinerario("Itinerario con el tipo TKT-015", otro_destino, tipos=[tipo_])

    with pytest.raises(services.DependenciaBloqueante) as exc:
        services.retirar(
            T.TIPO,
            tipo_.pk,
            actor,
            version=tipo_.contenido.version,
            motivo="Ya no se ofrece",
            confirmar_cascada=False,
            cascada_confirmada=None,
        )
    assert exc.value.extra["total_usos"] == 2
    entidades = {(u["tipo_entidad"], u["id"]) for u in exc.value.extra["usos"]}
    assert entidades == {
        ("DESTINO", destino_principal.contenido_id),
        ("ITINERARIO", itinerario_.contenido_id),
    }


def test_AC_TKT015_retirar_tipo_directo_bloqueado_si_es_solo_secundario_de_destino_publicado(
    actor: int,
) -> None:
    """RULE-002/AC-124: ningún Destino PUBLICADO puede referenciar un Tipo no PUBLICADO, sea
    `tipo_principal` o cualquier otro miembro de `tipos_aventura`. Retirar directamente un Tipo que
    es SOLO secundario (no principal) de un Destino publicado debe bloquear igual que si fuera el
    principal: el destino quedaría con un tipo no publicado en su lista, un estado que AC-129 solo
    contempla como inconsistencia forzada en datos de prueba, nunca alcanzable por el panel."""
    principal = publicos.tipo("Tipo principal TKT-015")
    secundario = publicos.tipo("Tipo secundario TKT-015")
    destino_ = publicos.destino(
        "Destino con tipo secundario TKT-015", tipos=[principal, secundario]
    )

    with pytest.raises(services.DependenciaBloqueante) as exc:
        services.retirar(
            T.TIPO,
            secundario.pk,
            actor,
            version=secundario.contenido.version,
            motivo="Ya no se ofrece",
            confirmar_cascada=False,
            cascada_confirmada=None,
        )
    assert exc.value.extra["total_usos"] == 1
    assert exc.value.extra["usos"] == [
        {
            "tipo_entidad": "DESTINO",
            "id": destino_.contenido_id,
            "titulo": destino_.contenido.titulo,
            "estado_editorial": E.PUBLICADO,
        }
    ]

    destino_.contenido.refresh_from_db()
    assert destino_.contenido.estado_editorial == E.PUBLICADO
    secundario.contenido.refresh_from_db()
    assert secundario.contenido.estado_editorial == E.PUBLICADO
    # El tipo_principal (distinto del retirado) no se ve afectado por este intento bloqueado.
    destino_.refresh_from_db()
    assert destino_.tipo_principal_id == principal.pk


def test_AC_TKT015_retirar_tipo_directo_no_bloqueado_si_los_dependientes_no_estan_publicados(
    actor: int,
) -> None:
    """Un Tipo que es `tipo_principal` de un Destino en BORRADOR o RETIRADO (no PUBLICADO) no
    bloquea: RULE-007 solo protege el contenido publicado."""
    tipo_borrador = publicos.tipo("Tipo de destino en borrador TKT-015")
    publicos.destino("Destino en borrador TKT-015", tipos=[tipo_borrador], estado=E.BORRADOR)

    contenido, _ = services.retirar(
        T.TIPO,
        tipo_borrador.pk,
        actor,
        version=tipo_borrador.contenido.version,
        motivo="Ya no se ofrece",
        confirmar_cascada=False,
        cascada_confirmada=None,
    )
    assert contenido.estado_editorial == E.RETIRADO


def test_AC_TKT014_retirar_tipo_sin_dependientes_no_falla(actor: int) -> None:
    """Caso base: un Tipo sin ningún Destino ni Itinerario dependiente se retira sin error (la
    consulta de dependientes de `_reindexar_dependientes_de_tipo` simplemente no encuentra nada)."""
    tipo_huerfano = publicos.tipo("Tipo sin dependientes TKT-014")
    reindexar_todo()

    contenido, afectadas = services.retirar(
        T.TIPO,
        tipo_huerfano.pk,
        actor,
        version=tipo_huerfano.contenido.version,
        motivo="Sin uso",
        confirmar_cascada=False,
        cascada_confirmada=None,
    )

    assert contenido.estado_editorial == E.RETIRADO
    assert len(afectadas) == 1
    assert afectadas[0]["origen"] == "PRINCIPAL"
