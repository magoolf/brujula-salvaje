"""TKT-007 — comando `cargar_semilla`: AC-031, AC-032, AC-033, AC-042, AC-043, AC-044 y la
idempotencia exigida por el ticket.

La fixture `semilla` carga el dataset UNA sola vez por módulo (17 pruebas leen el mismo estado
ya sembrado; el comando sube ~130 fotografías por el pipeline de medios y publica ~90 contenidos, y
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
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.db import transaction
from django.db.models import Count
from django.test import Client

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
from apps.medios.models import EstadoMedio, Medio
from seed import fotografias as seed_fotos

T = TipoContenido
E = EstadoEditorial
COMMONS = "https://commons.wikimedia.org/wiki/File:"

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
def semilla(django_db_setup: None, django_db_blocker: Any) -> Iterator[str]:
    """Devuelve la salida (stdout) de la primera ejecución, para comparar contadores."""
    with django_db_blocker.unblock(), transaction.atomic():
        salida = StringIO()
        call_command("cargar_semilla", stdout=salida)
        yield salida.getvalue()
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
# REQ-043/REQ-071 (TKT-041): 100% de los medios son fotografías del manifiesto con licencia
# compatible, autor, fuente y alt; la página de Créditos los lista todos con su atribución.
# ---------------------------------------------------------------------------
def test_REQ_043_medios_100_por_ciento_con_licencia_autor_y_alt(semilla: None, db: None) -> None:
    medios = list(Medio.objects.select_related("licencia"))
    manifiesto = {f.sha256: f for f in seed_fotos.fotos()}
    # Todas las fotos del manifiesto se usan y no hay ningún medio ajeno a él.
    assert len(medios) == len(manifiesto) >= 100
    assert {m.huella_sha256 for m in medios} == set(manifiesto)
    sin_alt = [m.pk for m in medios if not (m.texto_alternativo or "").strip()]
    sin_autor = [m.pk for m in medios if not (m.autor_credito or "").strip()]
    sin_fuente = [m.pk for m in medios if not (m.fuente_url or "").startswith(COMMONS)]
    sin_licencia = [m.pk for m in medios if m.licencia_id is None]
    assert sin_alt == []
    assert sin_autor == []
    assert sin_fuente == []
    assert sin_licencia == []
    assert {m.estado for m in medios} == {EstadoMedio.DISPONIBLE}
    for m in medios:
        foto = manifiesto[m.huella_sha256]
        assert m.licencia is not None
        # Solo CC0, dominio público, CC BY y CC BY-SA (nada NC/ND), del catálogo y compatibles.
        assert m.licencia.codigo == foto.licencia
        assert m.licencia.codigo in seed_fotos.LICENCIAS_ADMITIDAS
        assert m.licencia.compatible_publicacion is True
        assert m.licencia.url_texto_legal == foto.url_licencia
        assert m.texto_alternativo == foto.alt
        assert m.autor_credito == foto.autor
        assert m.fuente_url == foto.pagina
    # TKT-041 sustituye a DEC-AUTO-014: ya no quedan ilustraciones "PROPIA".
    assert not any(m.licencia and m.licencia.codigo == "PROPIA" for m in medios)
    # Alt real y descriptivo, nunca genérico ni de ilustración.
    genericos = [
        m.pk
        for m in medios
        if (m.texto_alternativo or "").strip().lower() == "imagen de destino"
        or "ilustración" in (m.texto_alternativo or "").lower()
    ]
    assert genericos == []


def test_REQ_043_creditos_listan_todos_los_medios_con_atribucion(semilla: None, db: None) -> None:
    api = Client(raise_request_exception=False)
    creditos: list[dict[str, Any]] = []
    url: str | None = "/api/v1/publico/creditos"
    while url:
        respuesta = api.get(url)
        assert respuesta.status_code == 200
        pagina = respuesta.json()
        creditos.extend(pagina["resultados"])
        url = pagina["siguiente"]  # enlace relativo o None en la última página
    # Todos los medios están en uso (portada, galería o portada de inicio) y aparecen en Créditos.
    assert len(creditos) == Medio.objects.count()
    for credito in creditos:
        imagen = credito["imagen"]
        assert imagen["autor_credito"]
        assert imagen["fuente_url"].startswith(COMMONS)
        assert imagen["licencia"]["codigo"] in seed_fotos.LICENCIAS_ADMITIDAS
        assert imagen["licencia"]["url_texto_legal"].startswith("https://creativecommons.org/")
        assert imagen["texto_alternativo"]


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


_CONTADORES = re.compile(
    r"Creados: (\d+), reutilizados: (\d+), publicados en esta ejecución: (\d+)"
)


def _contadores(salida: str) -> tuple[int, int, int]:
    encontrado = _CONTADORES.search(salida)
    assert encontrado is not None, salida
    creados, reutilizados, publicados = (int(g) for g in encontrado.groups())
    return creados, reutilizados, publicados


def _estado_inicio() -> dict[str, Any]:
    from apps.auditoria.models import AccionAuditoria, EventoAuditoria
    from apps.inicio.models import ConfigInicio, DestacadoInicio

    return {
        "config": list(
            ConfigInicio.objects.values(
                "id", "hero_titular", "hero_subtitulo", "hero_medio_id", "actualizado_en"
            )
        ),
        "destacados": list(
            DestacadoInicio.objects.order_by("id").values(
                "id", "seccion", "contenido_id", "tipo_contenido", "orden"
            )
        ),
        "auditoria_config_inicio": EventoAuditoria.objects.filter(
            accion=AccionAuditoria.CONFIG_INICIO
        ).count(),
    }


def test_AC_TKT012_03_configurar_inicio_cuenta_reutilizado_y_es_idempotente(
    semilla: str, db: None
) -> None:
    """TKT-012 (hallazgo de QA de TKT-007): en la 2.ª+ ejecución `_configurar_inicio` no
    incrementaba el contador informativo (y además reejecutaba el servicio, con su auditoría y
    el borrado/recreado de destacados). Ahora cuenta como reutilizada y no repite efectos: la
    segunda ejecución reporta 0 creados y reutiliza EXACTAMENTE todo lo que la primera tocó, y la
    configuración de inicio queda idéntica en BD (mismos ids, mismo `actualizado_en`, ningún
    evento de auditoría nuevo)."""
    creados_1, reutilizados_1, _ = _contadores(semilla)
    assert creados_1 > 0
    antes = _estado_inicio()

    salida = StringIO()
    call_command("cargar_semilla", stdout=salida)
    creados_2, reutilizados_2, publicados_2 = _contadores(salida.getvalue())

    assert (creados_2, publicados_2) == (0, 0)
    assert reutilizados_2 == creados_1 + reutilizados_1
    assert _estado_inicio() == antes


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
