"""AC-TKT003-04: integridad declarativa del contenido (DB_HANDOFF v1.1, ADR-DB-002).

Cada CHECK, UNIQUE, FK compuesta y trigger se prueba con un caso válido y uno inválido.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta

import pytest
from django.db import DataError, IntegrityError, connection, transaction
from django.utils import timezone

from apps.auditoria.models import RevisionContenido
from apps.busqueda.models import BusquedaDocumento
from apps.contenido.models import (
    LONGITUD_MAXIMA_TEXTO,
    ChecklistItem,
    Coleccion,
    Contenido,
    ContenidoMedio,
    ContenidoTermino,
    Destino,
    DestinoTipoAventura,
    DiaItinerario,
    ElementoColeccion,
    Fuente,
    Guia,
    GuiaDestino,
    GuiaTipoAventura,
    Itinerario,
    ItinerarioTipoAventura,
    PaginaInstitucional,
    RelacionContenido,
    TerminoGlosario,
    TipoAventura,
)
from apps.contenido.tests.fabricas import (
    campos_publicado,
    crear_contenido,
    crear_medio,
    forzar_diferidas,
)
from apps.inicio.models import ConfigInicio, ConfigSitio, DestacadoInicio

pytestmark = pytest.mark.django_db


@contextmanager
def _falla(excepcion=IntegrityError):
    """pytest.raises + savepoint: el error no aborta la transacción de la prueba."""
    with pytest.raises(excepcion), transaction.atomic():
        yield


def _destino(titulo: str | None = None, **campos) -> Destino:
    return Destino.objects.create(contenido=crear_contenido("DESTINO", titulo), **campos)


def _tipo(titulo: str | None = None) -> TipoAventura:
    return TipoAventura.objects.create(contenido=crear_contenido("TIPO", titulo))


# ---------------------------------------------------------------------------
# FK compuestas: el subtipo o la relación coincide con el tipo del contenido
# ---------------------------------------------------------------------------
def test_AC_TKT003_04_subtipo_con_tipo_coherente_se_acepta():
    destino = _destino()
    assert destino.tipo_contenido == "DESTINO"
    assert Contenido.objects.get(pk=destino.pk).destino == destino


@pytest.mark.parametrize(
    ("modelo", "tipo_contenido_real"),
    [
        (Destino, "GUIA"),
        (Itinerario, "DESTINO"),
        (Guia, "TIPO"),
        (TipoAventura, "COLECCION"),
        (Coleccion, "TERMINO"),
        (TerminoGlosario, "PAGINA"),
    ],
)
def test_AC_TKT003_04_fk_compuesta_rechaza_subtipo_de_otro_tipo(modelo, tipo_contenido_real):
    contenido = crear_contenido(tipo_contenido_real)
    with _falla():
        modelo.objects.create(contenido=contenido)


def test_AC_TKT003_04_pagina_institucional_fk_compuesta():
    pagina = crear_contenido("PAGINA")
    PaginaInstitucional.objects.create(
        contenido=pagina,
        clave="ACERCA_DE",
        cuerpo="Texto",
        version_documento="1.0",
        vigente_desde=date(2026, 9, 1),
    )
    with _falla():
        PaginaInstitucional.objects.create(
            contenido=crear_contenido("DESTINO"),
            clave="AVISO_LEGAL",
            cuerpo="Texto",
            version_documento="1.0",
            vigente_desde=date(2026, 9, 1),
        )


def test_AC_TKT003_04_elemento_coleccion_solo_destino_o_itinerario():
    coleccion = Coleccion.objects.create(contenido=crear_contenido("COLECCION"))
    destino = _destino()
    ElementoColeccion.objects.create(
        coleccion=coleccion, contenido=destino.contenido, tipo_contenido="DESTINO"
    )
    guia = Guia.objects.create(contenido=crear_contenido("GUIA"))
    # CHECK de tipos admitidos.
    with _falla():
        ElementoColeccion.objects.create(
            coleccion=coleccion, contenido=guia.contenido, tipo_contenido="GUIA"
        )
    # FK compuesta: el tipo declarado no coincide con el real.
    with _falla():
        ElementoColeccion.objects.create(
            coleccion=coleccion, contenido=guia.contenido, tipo_contenido="ITINERARIO"
        )


def test_AC_TKT003_04_relaciones_polimorficas_rechazan_tipo_incoherente():
    destino = _destino()
    guia = Guia.objects.create(contenido=crear_contenido("GUIA"))
    termino = TerminoGlosario.objects.create(contenido=crear_contenido("TERMINO"))
    medio = crear_medio()

    ContenidoTermino.objects.create(
        contenido=destino.contenido, tipo_contenido="DESTINO", termino=termino
    )
    ContenidoMedio.objects.create(contenido=guia.contenido, tipo_contenido="GUIA", medio=medio)
    RelacionContenido.objects.create(
        origen=destino.contenido,
        origen_tipo="DESTINO",
        relacionado=guia.contenido,
        relacionado_tipo="GUIA",
    )
    with _falla():
        ContenidoTermino.objects.create(
            contenido=guia.contenido, tipo_contenido="DESTINO", termino=termino
        )
    with _falla():
        ContenidoMedio.objects.create(
            contenido=destino.contenido, tipo_contenido="ITINERARIO", medio=crear_medio()
        )
    with _falla():
        RelacionContenido.objects.create(
            origen=guia.contenido,
            origen_tipo="GUIA",
            relacionado=destino.contenido,
            relacionado_tipo="GUIA",
        )
    # Autorrelación prohibida.
    with _falla():
        RelacionContenido.objects.create(
            origen=guia.contenido,
            origen_tipo="GUIA",
            relacionado=guia.contenido,
            relacionado_tipo="GUIA",
        )


def test_AC_TKT003_04_destacado_revision_y_busqueda_con_fk_compuesta():
    destino = _destino()
    DestacadoInicio.objects.create(
        seccion="DESTINOS", contenido=destino.contenido, tipo_contenido="DESTINO"
    )
    with _falla():  # CHECK sección-tipo
        DestacadoInicio.objects.create(
            seccion="GUIAS", contenido=destino.contenido, tipo_contenido="DESTINO"
        )
    with _falla():  # FK compuesta
        DestacadoInicio.objects.create(
            seccion="GUIAS", contenido=destino.contenido, tipo_contenido="GUIA"
        )
    RevisionContenido.objects.create(
        contenido=destino.contenido,
        tipo_contenido="DESTINO",
        numero_revision=1,
        motivo="PUBLICACION",
        instantanea={"titulo": "x"},
    )
    with _falla():
        RevisionContenido.objects.create(
            contenido=destino.contenido,
            tipo_contenido="GUIA",
            numero_revision=2,
            motivo="PUBLICACION",
            instantanea={},
        )
    with _falla():
        BusquedaDocumento.objects.create(
            contenido=destino.contenido,
            tipo_contenido="GUIA",
            slug="x",
            titulo="x",
            titulo_norm="x",
            documento="",
        )


def test_AC_TKT003_04_tipo_principal_debe_estar_entre_los_tipos_del_destino():
    destino = _destino()
    tipo_a, tipo_b = _tipo(), _tipo()
    DestinoTipoAventura.objects.create(destino=destino, tipo_aventura=tipo_a)
    destino.tipo_principal = tipo_a
    destino.save()
    forzar_diferidas("fk_destino_tipo_principal_en_tipos")
    with _falla():
        destino.tipo_principal = tipo_b
        destino.save()
        forzar_diferidas("fk_destino_tipo_principal_en_tipos")


def test_AC_TKT003_04_revision_impide_borrar_el_contenido():
    destino = _destino()
    RevisionContenido.objects.create(
        contenido=destino.contenido,
        tipo_contenido="DESTINO",
        numero_revision=1,
        motivo="PUBLICACION",
        instantanea={},
    )
    with _falla(), connection.cursor() as cursor:
        cursor.execute("DELETE FROM app.contenido WHERE id = %s", [destino.pk])


# ---------------------------------------------------------------------------
# Unicidad normalizada (RULE-026, RULE-027, DEC-AUTO-098)
# ---------------------------------------------------------------------------
def test_AC_TKT003_04_titulo_unico_insensible_a_tildes_mayusculas_y_espacios():
    original = crear_contenido("DESTINO", "Montaña  Árbol")
    original.refresh_from_db()
    assert original.titulo_norm == "montana arbol"
    with _falla():
        crear_contenido("DESTINO", "  MONTANA arbol ")
    # Otro tipo sí puede repetir el título.
    crear_contenido("GUIA", "Montaña Árbol")


def test_AC_TKT003_04_slug_unico_por_tipo_y_con_patron():
    crear_contenido("GUIA", slug="ruta-andina")
    crear_contenido("DESTINO", slug="ruta-andina")
    with _falla():
        crear_contenido("GUIA", slug="ruta-andina")
    with _falla():
        crear_contenido("GUIA", slug="Ruta_Andina")


def test_AC_TKT003_04_descripcion_seo_unica_entre_publicados():
    crear_contenido("DESTINO", **campos_publicado("DESTINO", seo_descripcion="Viaje a Los Andes"))
    # Un borrador puede repetirla.
    crear_contenido("GUIA", seo_descripcion="viaje a los ANDES")
    with _falla():
        crear_contenido("GUIA", **campos_publicado("GUIA", seo_descripcion="Viaje a los Andés"))


# ---------------------------------------------------------------------------
# CHECK por estado editorial (STATE-001)
# ---------------------------------------------------------------------------
def test_AC_TKT003_04_publicado_exige_fechas_seo_y_portada():
    crear_contenido("DESTINO", **campos_publicado("DESTINO"))
    crear_contenido("TERMINO", **campos_publicado("TERMINO"))
    crear_contenido("PAGINA", **campos_publicado("PAGINA"))
    with _falla():
        crear_contenido("DESTINO", **campos_publicado("DESTINO", fecha_ultima_revision=None))
    with _falla():
        crear_contenido("DESTINO", **campos_publicado("DESTINO", seo_descripcion=None))
    with _falla():
        crear_contenido("DESTINO", **campos_publicado("DESTINO", portada=None))


def test_AC_TKT003_04_retirado_y_reglas_por_tipo():
    ahora = timezone.now()
    crear_contenido(
        "GUIA",
        estado_editorial="RETIRADO",
        retirado_en=ahora,
        motivo_retiro="Obsoleta",
        primera_publicacion_en=ahora,
    )
    with _falla():  # RETIRADO sin motivo
        crear_contenido("GUIA", estado_editorial="RETIRADO", retirado_en=ahora)
    with _falla():  # AC-033: la página no se retira
        crear_contenido(
            "PAGINA",
            estado_editorial="RETIRADO",
            retirado_en=ahora,
            motivo_retiro="x",
            primera_publicacion_en=ahora,
        )
    with _falla():  # término y página sin portada
        crear_contenido("TERMINO", portada=crear_medio())
    with _falla():  # término sin SEO propio
        crear_contenido("TERMINO", seo_titulo="SEO")
    with _falla():  # orden de fechas de publicación
        crear_contenido(
            "GUIA",
            primera_publicacion_en=ahora,
            publicado_actualizado_en=ahora - timedelta(days=1),
        )
    with _falla():  # tipo fuera del dominio
        crear_contenido("OTRO")
    with _falla():  # versión >= 1
        crear_contenido("GUIA", version=0)


# ---------------------------------------------------------------------------
# Trigger trg_contenido_guardas (RULE-008, AC-101, AC-033, §39.2)
# ---------------------------------------------------------------------------
def test_AC_TKT003_04_guardas_tipo_inmutable_y_slug_tras_publicar():
    borrador = crear_contenido("GUIA")
    borrador.slug = "nuevo-slug"
    borrador.save()  # el slug de un borrador nunca publicado sí cambia
    with _falla():
        Contenido.objects.filter(pk=borrador.pk).update(tipo="DESTINO")

    publicado = crear_contenido("GUIA", **campos_publicado("GUIA"))
    with _falla():
        Contenido.objects.filter(pk=publicado.pk).update(slug="otro-slug")
    with _falla():
        Contenido.objects.filter(pk=publicado.pk).update(primera_publicacion_en=timezone.now())
    # Otros campos de un publicado sí se actualizan.
    Contenido.objects.filter(pk=publicado.pk).update(titulo="Título actualizado")


def test_AC_TKT003_04_guardas_borrado_solo_de_borradores_nunca_publicados():
    borrador = _destino()
    Contenido.objects.filter(pk=borrador.pk).delete()
    assert not Destino.objects.filter(pk=borrador.pk).exists()

    publicado = crear_contenido("GUIA", **campos_publicado("GUIA"))
    with _falla():
        Contenido.objects.filter(pk=publicado.pk).delete()
    pagina = crear_contenido("PAGINA")
    with _falla():
        Contenido.objects.filter(pk=pagina.pk).delete()


def test_AC_TKT003_04_borrado_sql_de_un_borrador_cascada_por_fk_compuesta():
    # La FK compuesta (ON DELETE CASCADE) borra el subtipo aunque el DELETE no pase por el ORM.
    destino = _destino()
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM app.contenido WHERE id = %s", [destino.pk])
        forzar_diferidas("ALL")
    assert not Destino.objects.filter(pk=destino.pk).exists()


# ---------------------------------------------------------------------------
# Destino: meses, rangos, coordenadas y longitud del texto enriquecido
# ---------------------------------------------------------------------------
def test_AC_TKT003_04_meses_mejor_epoca_rango_y_sin_duplicados():
    _destino(meses_mejor_epoca=[1, 6, 12])
    _destino(meses_mejor_epoca=[])
    with _falla():
        _destino(meses_mejor_epoca=[0, 5])
    with _falla():
        _destino(meses_mejor_epoca=[13])
    with _falla():
        _destino(meses_mejor_epoca=[3, 3])


@pytest.mark.parametrize(
    "campos",
    [
        {"dificultad": 6},
        {"nivel_presupuesto": 0},
        {"duracion_min_dias": 10, "duracion_max_dias": 5},
        {"duracion_max_dias": 91},
        {"altitud_max_m": 9001},
        {"latitud": 10},
        {"latitud": 91, "longitud": 0},
        {"latitud": 0, "longitud": -181},
    ],
)
def test_AC_TKT003_04_destino_rechaza_valores_fuera_de_dominio(campos):
    with _falla():
        _destino(**campos)


def test_AC_TKT003_04_tope_de_100000_caracteres_en_texto_enriquecido():
    _destino(descripcion_experta="a" * LONGITUD_MAXIMA_TEXTO)
    with _falla():
        _destino(descripcion_experta="a" * (LONGITUD_MAXIMA_TEXTO + 1))
    with _falla():
        Guia.objects.create(
            contenido=crear_contenido("GUIA"), cuerpo="b" * (LONGITUD_MAXIMA_TEXTO + 1)
        )


# ---------------------------------------------------------------------------
# Itinerario, días, guía, checklist, fuentes
# ---------------------------------------------------------------------------
def test_AC_TKT003_04_dias_unicos_por_itinerario_diferible_para_reordenar():
    itinerario = Itinerario.objects.create(contenido=crear_contenido("ITINERARIO"))
    dia1 = DiaItinerario.objects.create(
        itinerario=itinerario, numero_dia=1, titulo="Llegada", actividades="Traslado"
    )
    dia2 = DiaItinerario.objects.create(
        itinerario=itinerario, numero_dia=2, titulo="Ascenso", actividades="Caminata"
    )
    # Intercambio de números dentro de una transacción (UNIQUE DEFERRABLE).
    with transaction.atomic():
        DiaItinerario.objects.filter(pk=dia1.pk).update(numero_dia=2)
        DiaItinerario.objects.filter(pk=dia2.pk).update(numero_dia=1)
        forzar_diferidas("uq_dia_itinerario_numero")
    with _falla():
        DiaItinerario.objects.create(
            itinerario=itinerario, numero_dia=1, titulo="Repetido", actividades="x"
        )
        forzar_diferidas("uq_dia_itinerario_numero")
    with _falla():
        DiaItinerario.objects.create(
            itinerario=itinerario, numero_dia=61, titulo="Fuera", actividades="x"
        )


def test_AC_TKT003_04_itinerario_guia_checklist_y_fuente():
    tipo = _tipo()
    itinerario = Itinerario.objects.create(
        contenido=crear_contenido("ITINERARIO"), destino=_destino(), duracion_dias=5
    )
    ItinerarioTipoAventura.objects.create(itinerario=itinerario, tipo_aventura=tipo)
    guia = Guia.objects.create(contenido=crear_contenido("GUIA"))
    GuiaDestino.objects.create(guia=guia, destino=itinerario.destino)
    GuiaTipoAventura.objects.create(guia=guia, tipo_aventura=tipo)
    ChecklistItem.objects.create(tipo_aventura=tipo, texto="Botas")
    with _falla():
        ChecklistItem.objects.create(tipo_aventura=tipo, texto="Botas")
    with _falla():
        Itinerario.objects.create(contenido=crear_contenido("ITINERARIO"), duracion_dias=61)
    with _falla():
        Guia.objects.create(contenido=crear_contenido("GUIA"), palabras=-1)
    with _falla():
        Fuente.objects.create(contenido=guia.contenido, titulo="x", url="javascript:alert(1)")
    Fuente.objects.create(contenido=guia.contenido, titulo="x", url="https://ejemplo.org/a")
    with _falla():
        TipoAventura.objects.create(contenido=crear_contenido("TIPO"), nivel_exigencia=0)


# ---------------------------------------------------------------------------
# Medios (RULE-005, DEC-AUTO-044) e inicio/sitio (singletons)
# ---------------------------------------------------------------------------
def test_AC_TKT003_04_medio_disponible_exige_metadatos_y_limites():
    from apps.catalogos.models import Licencia

    licencia = Licencia.objects.get(codigo="CC-BY-4.0")
    crear_medio(
        estado="DISPONIBLE",
        texto_alternativo="Lago al amanecer",
        autor_credito="Autora",
        licencia=licencia,
    )
    with _falla():
        crear_medio(estado="DISPONIBLE", texto_alternativo="x", autor_credito="y")
    with _falla():  # > 40 MP
        crear_medio(ancho_px=8000, alto_px=6000)
    with _falla():  # lado mayor < 1200 px
        crear_medio(ancho_px=1000, alto_px=800)
    with _falla():  # > 10 MB
        crear_medio(peso_bytes=10 * 1024 * 1024 + 1)
    with _falla():  # huella no hexadecimal
        crear_medio(huella_sha256="Z" * 64)
    with _falla():  # huella duplicada
        medio = crear_medio()
        crear_medio(huella_sha256=medio.huella_sha256)


def test_AC_TKT003_04_singletons_de_inicio_y_sitio():
    assert ConfigSitio.objects.get().nombre_marca == "Brújula Salvaje"
    ConfigInicio.objects.create(hero_titular="Explora", hero_subtitulo="x", hero_medio=crear_medio())
    with _falla():
        ConfigInicio.objects.create(
            id=2, hero_titular="Otro", hero_subtitulo="x", hero_medio=crear_medio()
        )
    with _falla():
        ConfigSitio.objects.filter(pk=1).update(texto_descargo="")


def test_AC_TKT003_04_tipo_invalido_en_array_da_error_de_datos():
    with _falla(DataError):
        _destino(meses_mejor_epoca=[40000])
