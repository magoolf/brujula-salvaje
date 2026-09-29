"""TKT-007 — comando `cargar_semilla`: AC-031, AC-032, AC-033, AC-042, AC-043, AC-044 y la
idempotencia exigida por el ticket.

La fixture `semilla` carga el dataset UNA sola vez por módulo (17 pruebas leen el mismo estado
ya sembrado; el comando genera ~130 medios reales con Pillow y publica ~90 contenidos, y
repetirlo en cada prueba resulta impracticable: una primera versión con alcance por prueba tardó
más de media hora solo para este archivo). Para lograrlo sin filtrar datos reales a OTRAS pruebas
del resto de la suite (lo que sí ocurrió con una versión anterior que usaba
`django_db_blocker.unblock()` a secas: dejaba filas confirmadas fuera de cualquier transacción,
rotas por pruebas de otros módulos que asumen una base de datos vacía — `ConfigInicio` duplicado,
conteos de medios, etc., detectado ejecutando la suite completa), la fixture abre explícitamente
su propia transacción (`transaction.atomic()`) alrededor de TODO el módulo y la revierte con
`transaction.set_rollback(True)` al terminar: mismo patrón que usan `TestCase.setUpTestData` /
`django_db_blocker` de pytest-django para compartir estado costoso sin dejar rastro.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

import pytest
from django.core.management import call_command
from django.db import transaction
from django.db.models import Count

from apps.contenido import reglas
from apps.contenido.models import (
    Coleccion,
    Contenido,
    Destino,
    EstadoEditorial,
    Guia,
    Itinerario,
    PaginaInstitucional,
    TipoAventura,
    TipoContenido,
)
from apps.medios.models import Medio

T = TipoContenido
E = EstadoEditorial

CATEGORIAS_GUIA_ESPERADAS = {
    "preparacion-fisica",
    "equipo-y-mochila",
    "seguridad-y-gestion-de-riesgos",
    "salud-en-altitud-y-en-viaje",
    "viaje-sostenible-y-no-dejar-rastro",
    "presupuesto-y-planificacion",
    "fotografia-de-aventura",
    "primera-aventura",
}


@pytest.fixture(scope="module")
def semilla(django_db_setup: None, django_db_blocker: Any) -> Iterator[None]:
    with django_db_blocker.unblock(), transaction.atomic():
        call_command("cargar_semilla")
        yield
        transaction.set_rollback(True)


@pytest.fixture
def destinos_publicados(semilla: None, db: None) -> list[Destino]:
    return list(
        Destino.objects.select_related("contenido", "pais")
        .filter(contenido__estado_editorial=E.PUBLICADO)
        .order_by("contenido__slug")
    )


# ---------------------------------------------------------------------------
# AC-042: >=20 destinos publicados, nombres únicos
# ---------------------------------------------------------------------------
def test_AC_042_destinos_publicados_minimo_20(destinos_publicados: list[Destino]) -> None:
    assert len(destinos_publicados) >= 20
    titulos = [d.contenido.titulo for d in destinos_publicados]
    assert len(titulos) == len(set(titulos)), "hay títulos de destino duplicados"
    slugs = [d.contenido.slug for d in destinos_publicados]
    assert len(slugs) == len(set(slugs)), "hay slugs de destino duplicados"
    # Ticket: exactamente 24 (requirements.yaml contenido_semilla.destinos_propuestos)
    assert len(destinos_publicados) == 24


# ---------------------------------------------------------------------------
# AC-043: conteos mínimos del dataset semilla (REQ-040/041, ticket TKT-007)
# ---------------------------------------------------------------------------
def test_AC_043_conteos_minimos(semilla: None, db: None) -> None:
    conteo = lambda tipo: Contenido.objects.filter(  # noqa: E731
        tipo=tipo, estado_editorial=E.PUBLICADO
    ).count()

    assert conteo(T.DESTINO) >= 20
    assert conteo(T.TIPO) >= 10
    assert conteo(T.ITINERARIO) >= 10
    assert conteo(T.GUIA) >= 10
    assert conteo(T.COLECCION) >= 3
    assert conteo(T.TERMINO) >= 10
    assert conteo(T.PAGINA) == 4

    # Los 12 tipos de aventura literales de requirements.yaml (DEC-AUTO-006), ni uno más ni
    # menos: la lista está fijada, no se inventan tipos adicionales.
    assert conteo(T.TIPO) == 12

    # Guías repartidas en las 8 categorías semilla (REQ-041), ninguna vacía de las que se usan.
    categorias_usadas = set(
        Guia.objects.filter(contenido__estado_editorial=E.PUBLICADO)
        .select_related("categoria")
        .values_list("categoria__slug", flat=True)
    )
    assert categorias_usadas <= CATEGORIAS_GUIA_ESPERADAS
    assert len(categorias_usadas) >= 6  # >=6 de las 8 categorías representadas


# ---------------------------------------------------------------------------
# AC-044: 0 destinos publicados con campos obligatorios vacíos; una entidad incompleta se
# rechaza con mensaje (se ejerce `reglas.validar_destino`, la función real que usa el servicio
# de publicación, sin necesidad de reconstruir todo un ciclo HTTP).
# ---------------------------------------------------------------------------
def test_AC_044_cero_destinos_con_campos_obligatorios_vacios(
    destinos_publicados: list[Destino],
) -> None:
    campos_obligatorios = (
        "resumen",
        "descripcion_experta",
        "dificultad",
        "nivel_presupuesto",
        "clima",
        "como_llegar",
        "seguridad_riesgos",
        "sostenibilidad",
        "latitud",
        "longitud",
        "duracion_min_dias",
        "duracion_max_dias",
        "tipo_principal_id",
        "pais_id",
    )
    incompletos = []
    for destino in destinos_publicados:
        for campo in campos_obligatorios:
            if getattr(destino, campo) in (None, ""):
                incompletos.append((destino.contenido.slug, campo))
        if not destino.meses_mejor_epoca:
            incompletos.append((destino.contenido.slug, "meses_mejor_epoca"))
        if destino.contenido.portada_id is None:
            incompletos.append((destino.contenido.slug, "portada_id"))
        if destino.contenido.fecha_ultima_revision is None:
            incompletos.append((destino.contenido.slug, "fecha_ultima_revision"))
        if destino.contenido.seo_descripcion is None:
            incompletos.append((destino.contenido.slug, "seo_descripcion"))
    assert incompletos == []


def test_AC_044_publicar_destino_incompleto_es_rechazado() -> None:
    """La misma función `reglas.validar_destino` que usa `services.publicar()` (RULE-002/006/
    023/027): un destino sin `seguridad_riesgos` ni `sostenibilidad` se rechaza con mensaje,
    no se acepta en silencio. No depende de la BD ni de la semilla."""
    datos = reglas.DatosDestino(
        resumen="Resumen válido",
        descripcion_experta="<p>" + ("palabra " * 700) + "</p>",
        tipos_ids=(1,),
        tipo_principal_id=1,
        dificultad=2,
        meses_mejor_epoca=(1, 2),
        duracion_min_dias=2,
        duracion_max_dias=4,
        nivel_presupuesto=2,
        clima=None,  # incompleto a propósito
        como_llegar="Texto",
        seguridad_riesgos=None,  # incompleto a propósito
        sostenibilidad=None,  # incompleto a propósito
        latitud=1.0,
        longitud=1.0,
        portada_id=1,
        galeria_ids=(1, 2, 3),
        fecha_ultima_revision=None,  # incompleto a propósito
        seo_descripcion="desc",
        medios_disponibles_en_galeria=3,
        relacionados_publicados=3,
    )
    errores = reglas.validar_destino(datos)
    campos_con_error = {e["campo"] for e in errores}
    assert {"clima", "seguridad_riesgos", "sostenibilidad", "fecha_ultima_revision"} <= (
        campos_con_error
    )


# ---------------------------------------------------------------------------
# AC-031: 100% de contenidos publicados muestran autoría y fecha de última revisión
# ---------------------------------------------------------------------------
def test_AC_031_autoria_y_fecha_de_revision(semilla: None, db: None) -> None:
    publicados = Contenido.objects.filter(
        estado_editorial=E.PUBLICADO,
        tipo__in=[T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO, T.COLECCION, T.TERMINO],
    )
    assert publicados.exists()
    sin_fecha = publicados.filter(fecha_ultima_revision__isnull=True).count()
    assert sin_fecha == 0
    # REQ-023/DEC-AUTO-039: autoría de equipo editorial, nunca un nombre de persona real. La
    # semilla usa `creado_por=None` (DEC-AUTO-095, "NULL = carga semilla"), que el panel ya
    # renderiza como autoría de equipo, no como ausencia de autoría.
    con_persona_real = publicados.exclude(creado_por__isnull=True).count()
    assert con_persona_real == 0

    paginas = Contenido.objects.filter(tipo=T.PAGINA, estado_editorial=E.PUBLICADO)
    assert paginas.count() == 4
    assert paginas.filter(fecha_ultima_revision__isnull=True).count() == 0


# ---------------------------------------------------------------------------
# AC-032: 100% de fichas e itinerarios muestran dificultad, riesgos/seguridad y descargo
# ---------------------------------------------------------------------------
def test_AC_032_dificultad_riesgos_y_descargo_en_destinos(
    destinos_publicados: list[Destino],
) -> None:
    assert destinos_publicados
    for destino in destinos_publicados:
        assert destino.dificultad is not None, destino.contenido.slug
        assert 1 <= destino.dificultad <= 5
        assert destino.seguridad_riesgos, destino.contenido.slug
        assert "orientativa" in destino.seguridad_riesgos.lower(), (
            f"{destino.contenido.slug}: falta el descargo de orientatividad en seguridad_riesgos"
        )


def test_AC_032_dificultad_riesgos_y_descargo_en_itinerarios(semilla: None, db: None) -> None:
    itinerarios = list(
        Itinerario.objects.select_related("contenido").filter(
            contenido__estado_editorial=E.PUBLICADO
        )
    )
    assert len(itinerarios) >= 10
    for itinerario in itinerarios:
        assert itinerario.dificultad is not None, itinerario.contenido.slug
        assert 1 <= itinerario.dificultad <= 5
        assert itinerario.riesgos_seguridad, itinerario.contenido.slug
        assert "orientativo" in itinerario.riesgos_seguridad.lower(), itinerario.contenido.slug


# ---------------------------------------------------------------------------
# AC-033 (páginas institucionales, no se retiran/eliminan; siempre existen)
# ---------------------------------------------------------------------------
def test_AC_033_paginas_institucionales_publicadas_y_no_retirables(semilla: None, db: None) -> None:
    paginas = list(PaginaInstitucional.objects.select_related("contenido").all())
    assert len(paginas) == 4
    claves = {p.clave for p in paginas}
    assert claves == {"ACERCA_DE", "POLITICA_DATOS", "POLITICA_COOKIES", "AVISO_LEGAL"}
    for pagina in paginas:
        assert pagina.contenido.estado_editorial == E.PUBLICADO
        assert pagina.contenido.primera_publicacion_en is not None
        assert pagina.version_documento
        assert pagina.vigente_desde is not None
        assert pagina.cuerpo


# ---------------------------------------------------------------------------
# REQ-043: 100% de los medios con licencia, autor/crédito y alt real
# ---------------------------------------------------------------------------
def test_REQ_043_medios_100_por_ciento_con_licencia_autor_y_alt(semilla: None, db: None) -> None:
    medios = list(Medio.objects.all())
    assert len(medios) >= 100
    sin_alt = [m.pk for m in medios if not m.texto_alternativo]
    sin_autor = [m.pk for m in medios if not m.autor_credito]
    sin_licencia = [m.pk for m in medios if m.licencia_id is None]
    assert sin_alt == []
    assert sin_autor == []
    assert sin_licencia == []
    # DEC-AUTO-014: ilustraciones propias, licencia "PROPIA" (obra propia del equipo editorial),
    # nunca hotlink a bancos de imágenes de terceros.
    licencias_usadas = {m.licencia.codigo for m in medios if m.licencia_id is not None}
    assert licencias_usadas == {"PROPIA"}
    # Alt real y descriptivo: ninguno debería ser el genérico "imagen de destino" citado en el
    # ticket como ejemplo de lo que NO se quiere.
    genericos = [m.pk for m in medios if m.texto_alternativo.strip().lower() == "imagen de destino"]
    assert genericos == []


# ---------------------------------------------------------------------------
# PRB-BP-002: Surf y Ciclismo de montaña como tipo secundario verídico, no principal
# ---------------------------------------------------------------------------
def test_PRB_BP_002_surf_y_ciclismo_como_tipo_secundario(semilla: None, db: None) -> None:
    for slug in ("surf", "ciclismo-de-montana"):
        tipo = TipoAventura.objects.select_related("contenido").get(contenido__slug=slug)
        assert tipo.contenido.estado_editorial == E.PUBLICADO
        # RULE-025: al menos un destino publicado lo usa (como principal o secundario).
        assert tipo.destinos.filter(contenido__estado_editorial=E.PUBLICADO).exists()
        # Pero nunca como tipo PRINCIPAL de ningún destino (la semilla PRD no lo respalda como
        # actividad principal de ninguno de los 24 destinos, ver requirements.yaml PRB-BP-002).
        assert not tipo.destinos_principales.filter(
            contenido__estado_editorial=E.PUBLICADO
        ).exists()


# ---------------------------------------------------------------------------
# RULE-025: cada tipo de aventura publicado tiene >=1 destino publicado
# ---------------------------------------------------------------------------
def test_RULE_025_todo_tipo_publicado_tiene_destino_publicado(semilla: None, db: None) -> None:
    tipos = TipoAventura.objects.select_related("contenido").filter(
        contenido__estado_editorial=E.PUBLICADO
    )
    assert tipos.count() == 12
    sin_destino = [
        t.contenido.slug
        for t in tipos
        if not t.destinos.filter(contenido__estado_editorial=E.PUBLICADO).exists()
    ]
    assert sin_destino == []


# ---------------------------------------------------------------------------
# RULE-006: todo Destino/Itinerario/Guía/Tipo publicado muestra >=3 relacionados publicados
# ---------------------------------------------------------------------------
def test_RULE_006_relacionados_minimos(semilla: None, db: None) -> None:
    from apps.contenido import selectors as contenido_selectors

    revisados = 0
    for contenido in Contenido.objects.filter(
        estado_editorial=E.PUBLICADO, tipo__in=[T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO]
    ):
        relacionados = contenido_selectors.relacionados(contenido, limite=3)
        assert len(relacionados) >= 3, contenido.slug
        revisados += 1
    assert revisados >= 24 + 10 + 10 + 12  # destinos + itinerarios + guías + tipos


# ---------------------------------------------------------------------------
# Colecciones (REQ-027, mínimo 3 exigido por el ticket, con margen real de 4)
# ---------------------------------------------------------------------------
def test_colecciones_minimo_3_con_4_elementos_publicados(semilla: None, db: None) -> None:
    colecciones = list(
        Coleccion.objects.select_related("contenido").filter(
            contenido__estado_editorial=E.PUBLICADO
        )
    )
    assert len(colecciones) >= 3
    for coleccion in colecciones:
        publicados = coleccion.elementos.filter(contenido__estado_editorial=E.PUBLICADO).count()
        assert publicados >= 4, coleccion.contenido.slug


# ---------------------------------------------------------------------------
# Configuración de inicio (usa apps.inicio.services, RULE-016)
# ---------------------------------------------------------------------------
def test_configuracion_de_inicio_completa(semilla: None, db: None) -> None:
    from apps.inicio.models import ConfigInicio, DestacadoInicio, SeccionInicio

    config = ConfigInicio.objects.first()
    assert config is not None
    assert config.hero_titular
    assert config.hero_subtitulo
    assert config.hero_medio_id is not None
    assert DestacadoInicio.objects.filter(seccion=SeccionInicio.DESTINOS).count() >= 6
    assert DestacadoInicio.objects.filter(seccion=SeccionInicio.ITINERARIOS).count() >= 3
    assert DestacadoInicio.objects.filter(seccion=SeccionInicio.GUIAS).count() >= 3


# ---------------------------------------------------------------------------
# Idempotencia (instrucción explícita del ticket: "ejecutar dos veces, mismo resultado")
# ---------------------------------------------------------------------------
def test_idempotencia_ejecutar_dos_veces_no_duplica_ni_falla(semilla: None, db: None) -> None:
    antes = {
        "contenido": Contenido.objects.count(),
        "medio": Medio.objects.count(),
        "destino_publicado": Contenido.objects.filter(
            tipo=T.DESTINO, estado_editorial=E.PUBLICADO
        ).count(),
    }
    # Dentro de la transacción por prueba de pytest-django (fixture `db`): el comando vuelve a
    # ejecutarse sobre los datos ya sembrados por el fixture `semilla` (module-scoped, ya
    # confirmados fuera de esta transacción) y no debe crear ni publicar nada nuevo.
    call_command("cargar_semilla")
    despues = {
        "contenido": Contenido.objects.count(),
        "medio": Medio.objects.count(),
        "destino_publicado": Contenido.objects.filter(
            tipo=T.DESTINO, estado_editorial=E.PUBLICADO
        ).count(),
    }
    assert antes == despues, "la segunda ejecución no debe crear ni duplicar contenido"


def test_idempotencia_slugs_estables_get_or_create_semantico(semilla: None, db: None) -> None:
    """Confirma el mecanismo real de idempotencia (búsqueda por slug antes de crear), no solo
    su efecto observable: no debe haber dos filas `Contenido` con el mismo (tipo, slug)."""
    duplicados = Contenido.objects.values("tipo", "slug").annotate(n=Count("id")).filter(n__gt=1)
    assert list(duplicados) == []


# ---------------------------------------------------------------------------
# Precisión factual mínima: coordenadas dentro de rango real, sin cifras volátiles evidentes
# ---------------------------------------------------------------------------
def test_destinos_coordenadas_validas_y_sin_precios_en_seguridad(
    destinos_publicados: list[Destino],
) -> None:
    patron_precio = re.compile(r"[$€]\s?\d|\bUSD\b|\bCOP\b|\d+\s?(?:USD|COP|EUR)\b")
    for destino in destinos_publicados:
        assert -90 <= float(destino.latitud) <= 90, destino.contenido.slug
        assert -180 <= float(destino.longitud) <= 180, destino.contenido.slug
        # DEC-AUTO-033: sin precios ni cifras volátiles en el texto editorial.
        assert not patron_precio.search(destino.seguridad_riesgos), destino.contenido.slug
        assert not patron_precio.search(destino.descripcion_experta), destino.contenido.slug
