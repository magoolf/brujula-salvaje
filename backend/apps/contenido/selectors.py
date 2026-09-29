"""Consultas de lectura del sitio público (MOD-001..008; AP-01..AP-14; Skill_Backend §4.3).

Reglas transversales:
- RULE-001 / THREAT-011: toda consulta filtra estado_editorial = PUBLICADO en el servidor; los
  elementos relacionados (tipos, términos, guías, itinerarios, elementos de colección) también.
  Los medios solo si están DISPONIBLES (RULE-005).
- THREAT-019: nunca se leen ni exponen creado_por/actualizado_por ni datos de cuentas.
- Sin N+1: cada selector devuelve un QuerySet o lista con select_related/prefetch_related; las
  pruebas cuentan las consultas (Skill_Backend §8).
- Solo lectura: ningún selector escribe.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from django.db.models import Count, Exists, Max, OuterRef, Prefetch, Q, QuerySet

from apps.catalogos.models import CategoriaGuia, NivelEscala
from apps.contenido.models import (
    ChecklistItem,
    ClavePagina,
    Coleccion,
    Contenido,
    ContenidoMedio,
    ContenidoTermino,
    Destino,
    DestinoTipoAventura,
    DiaItinerario,
    ElementoColeccion,
    EstadoEditorial,
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
    TipoContenido,
)
from apps.medios.models import Medio
from apps.medios.selectors import medios_publicos, prefetch_imagen

PUB = EstadoEditorial.PUBLICADO
T = TipoContenido

# Tipos que aparecen como tarjetas o referencias públicas (TipoContenidoPublico del contrato).
TIPOS_PUBLICOS = (T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO, T.COLECCION)
TIPOS_CON_TERMINOS = (T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO)

MAX_RELACIONADOS = 6
MAX_ITINERARIOS_DESTINO = 12
MAX_AFINES = 6
MAX_GUIAS_RELACIONADAS = 6
MAX_DESTINOS_TIPO = 12
MAX_DESTINOS_GUIA = 20
MAX_TIPOS_GUIA = 12
MAX_USADO_EN = 20
GUIAS_RECIENTES_POR_CATEGORIA = 4
PALABRAS_POR_MINUTO = 200

# RULE-019 / DEC-AUTO-047: tramos de duración (un destino coincide si su rango se solapa).
TRAMOS_DURACION: dict[str, tuple[int, int | None, str]] = {
    "1-3": (1, 3, "1 a 3 días"),
    "4-7": (4, 7, "4 a 7 días"),
    "8-14": (8, 14, "8 a 14 días"),
    "15+": (15, None, "15 días o más"),
}
ORDENES_DESTINOS = {
    "nombre": ("contenido__titulo", "contenido__slug"),
    "dificultad_asc": ("dificultad", "contenido__titulo", "contenido__slug"),
    "dificultad_desc": ("-dificultad", "contenido__titulo", "contenido__slug"),
}
ORDENES_ITINERARIOS = {
    "titulo": ("contenido__titulo", "contenido__slug"),
    "duracion_asc": ("duracion_dias", "contenido__titulo", "contenido__slug"),
    "duracion_desc": ("-duracion_dias", "contenido__titulo", "contenido__slug"),
}
# Rutas públicas (BLUEPRINT §10) de las páginas institucionales y de los listados padre.
SLUG_PAGINA = {
    ClavePagina.ACERCA_DE: "acerca-de",
    ClavePagina.POLITICA_DATOS: "politica-de-tratamiento-de-datos",
    ClavePagina.POLITICA_COOKIES: "politica-de-cookies",
    ClavePagina.AVISO_LEGAL: "aviso-legal",
}
CLAVE_PAGINA = {slug: clave for clave, slug in SLUG_PAGINA.items()}
LISTADO_PADRE = {
    T.DESTINO: "/destinos",
    T.ITINERARIO: "/itinerarios",
    T.TIPO: "/tipos-de-aventura",
    T.GUIA: "/guias",
    T.COLECCION: "/colecciones",
}
NOMBRES_MES = (
    ("enero", "Enero"),
    ("febrero", "Febrero"),
    ("marzo", "Marzo"),
    ("abril", "Abril"),
    ("mayo", "Mayo"),
    ("junio", "Junio"),
    ("julio", "Julio"),
    ("agosto", "Agosto"),
    ("septiembre", "Septiembre"),
    ("octubre", "Octubre"),
    ("noviembre", "Noviembre"),
    ("diciembre", "Diciembre"),
)
RECIENTES = ("-fecha_ultima_revision", "titulo", "id")


def _publicado(prefijo: str = "contenido__") -> Q:
    return Q(**{f"{prefijo}estado_editorial": PUB})


def _publicado_por_id(referencia: str) -> Exists:
    """Existe un contenido PUBLICADO con id = `referencia` (subconsulta correlacionada por PK:
    plan estable aunque las estadísticas estén desactualizadas)."""
    return Exists(Contenido.objects.filter(pk=OuterRef(referencia), estado_editorial=PUB))


def _tipo_itinerario_publicado(referencia: str = "pk") -> Exists:
    return Exists(
        ItinerarioTipoAventura.objects.filter(
            itinerario_id=OuterRef(referencia), tipo_aventura__contenido__estado_editorial=PUB
        )
    )


def _q_por_tipo(tipo: str) -> Q:
    """Condición de coherencia de un tipo (solo lo que ese tipo necesita)."""
    if tipo == T.DESTINO:
        return Q(destino__pais__isnull=False) & Q(_publicado_por_id("destino__tipo_principal_id"))
    if tipo == T.ITINERARIO:
        destino_visible = destinos_publicados().filter(pk=OuterRef("itinerario__destino_id"))
        return Q(Exists(destino_visible)) & Q(_tipo_itinerario_publicado())
    subtipo = {
        T.GUIA: "guia__categoria",
        T.TIPO: "tipo_aventura",
        T.COLECCION: "coleccion",
        T.TERMINO: "termino_glosario",
        T.PAGINA: "pagina",
    }[TipoContenido(tipo)]
    return Q(**{f"{subtipo}__isnull": False})


def q_visible(tipo: str | None = None) -> Q:
    """Contenido visible en la API pública (AC-129, QA-TKT005-02, DEC-AUTO-912).

    PUBLICADO y coherente: con su fila de subtipo y con las relaciones que el contrato exige
    publicadas. Un destino con el tipo principal no publicado, o un itinerario cuyo destino no es
    visible o sin ningún tipo publicado, se trata como no publicado en TODA la API pública (404 en
    el detalle y fuera de listados, facetas, mapa, búsqueda, relacionados, colecciones, glosario,
    créditos e índice). La invariante que impide ese estado es del servicio de publicación.
    """
    if tipo is not None:
        return Q(estado_editorial=PUB, tipo=tipo) & _q_por_tipo(tipo)
    por_tipo = Q()
    for valor in TipoContenido.values:
        por_tipo |= Q(tipo=valor) & _q_por_tipo(valor)
    return Q(estado_editorial=PUB) & por_tipo


def contenidos_visibles(tipo: str | None = None) -> QuerySet[Contenido]:
    return Contenido.objects.filter(q_visible(tipo))


def _ids_visibles(tipo: str | None = None) -> QuerySet[Contenido, Any]:
    return contenidos_visibles(tipo).values("pk")


def es_visible(contenido_id: int) -> bool:
    return contenidos_visibles().filter(pk=contenido_id).exists()


# ---------------------------------------------------------------------------
# Prefetch reutilizables
# ---------------------------------------------------------------------------
def _tipos_publicos() -> QuerySet[TipoAventura]:
    return (
        TipoAventura.objects.filter(_publicado())
        .select_related("contenido")
        .order_by("orden", "contenido__titulo", "contenido__slug")
    )


def _prefetch_tipos(ruta: str = "tipos_aventura") -> Prefetch[str, QuerySet[Any], str]:
    return Prefetch(ruta, queryset=_tipos_publicos(), to_attr="tipos_publicos")


def _prefetch_galeria() -> Prefetch[str, QuerySet[Any], str]:
    galeria = (
        ContenidoMedio.objects.filter(medio__in=medios_publicos())
        .select_related("medio__licencia")
        .prefetch_related("medio__derivados")
        .order_by("orden", "id")
    )
    return Prefetch("contenido__galeria", queryset=galeria, to_attr="galeria_publica")


def _prefetch_fuentes() -> Prefetch[str, QuerySet[Any], str]:
    return Prefetch(
        "contenido__fuentes", queryset=Fuente.objects.order_by("orden", "id"), to_attr="fuentes_ord"
    )


def _prefetch_terminos() -> Prefetch[str, QuerySet[Any], str]:
    terminos = (
        ContenidoTermino.objects.filter(termino__contenido__estado_editorial=PUB)
        .select_related("termino__contenido")
        .order_by("termino__contenido__titulo", "id")
    )
    return Prefetch("contenido__terminos", queryset=terminos, to_attr="terminos_publicos")


def _detalle_comun() -> list[Prefetch[str, QuerySet[Any], str]]:
    return [
        prefetch_imagen("contenido__portada"),
        _prefetch_galeria(),
        _prefetch_fuentes(),
        _prefetch_terminos(),
    ]


# ---------------------------------------------------------------------------
# Tarjetas (listados, inicio, relacionados de detalle)
# ---------------------------------------------------------------------------
def con_tarjeta_destino(qs: QuerySet[Destino]) -> QuerySet[Destino]:
    return qs.select_related("contenido", "pais__region").prefetch_related(
        prefetch_imagen("contenido__portada"), _prefetch_tipos()
    )


def con_tarjeta_itinerario(qs: QuerySet[Itinerario]) -> QuerySet[Itinerario]:
    return qs.select_related("contenido", "destino__contenido").prefetch_related(
        prefetch_imagen("contenido__portada")
    )


def con_tarjeta_guia(qs: QuerySet[Guia]) -> QuerySet[Guia]:
    return qs.select_related("contenido", "categoria").prefetch_related(
        prefetch_imagen("contenido__portada")
    )


def con_tarjeta_tipo(qs: QuerySet[TipoAventura]) -> QuerySet[TipoAventura]:
    visibles = Count("destinos", filter=Q(destinos__in=destinos_publicados()), distinct=True)
    return (
        qs.select_related("contenido")
        .annotate(numero_destinos=visibles)
        .prefetch_related(prefetch_imagen("contenido__portada"))
    )


def con_tarjeta_coleccion(qs: QuerySet[Coleccion]) -> QuerySet[Coleccion]:
    elementos_publicados = Count(
        "elementos", filter=Q(elementos__contenido_id__in=_ids_visibles()), distinct=True
    )
    return (
        qs.select_related("contenido")
        .annotate(numero_elementos=elementos_publicados)
        .prefetch_related(prefetch_imagen("contenido__portada"))
    )


# Misma regla de visibilidad que q_visible(), expresada con uniones por clave desde cada subtipo
# (planes estables aunque las estadísticas estén desactualizadas).
def destinos_publicados() -> QuerySet[Destino]:
    return Destino.objects.filter(
        _publicado(), _publicado_por_id("tipo_principal_id"), pais__isnull=False
    )


def itinerarios_publicados() -> QuerySet[Itinerario]:
    # RULE-003 / AC-129: el destino debe ser visible y el itinerario tener un tipo publicado.
    destino_visible = destinos_publicados().filter(pk=OuterRef("destino_id"))
    return Itinerario.objects.filter(
        _publicado(), Exists(destino_visible), _tipo_itinerario_publicado()
    )


def guias_publicadas() -> QuerySet[Guia]:
    return Guia.objects.filter(_publicado(), categoria__isnull=False)


def tipos_publicados() -> QuerySet[TipoAventura]:
    return TipoAventura.objects.filter(_publicado())


def colecciones_publicadas() -> QuerySet[Coleccion]:
    return Coleccion.objects.filter(_publicado())


# ---------------------------------------------------------------------------
# Destinos: filtros y facetas (AP-02, RULE-019, DEC-AUTO-047)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FiltrosDestinos:
    tipos: tuple[str, ...] = ()
    region: str | None = None
    pais: str | None = None
    dificultad_min: int | None = None
    dificultad_max: int | None = None
    mes: int | None = None
    duraciones: tuple[str, ...] = ()
    presupuestos: tuple[int, ...] = ()
    orden: str = "nombre"


def slugs_de_tipos_publicados(slugs: Iterable[str]) -> set[str]:
    return set(
        Contenido.objects.filter(tipo=T.TIPO, estado_editorial=PUB, slug__in=list(slugs))
        .values_list("slug", flat=True)
    )  # fmt: skip


def existe_destino_publicado(slug: str) -> bool:
    return destinos_publicados().filter(contenido__slug=slug).exists()


def listar_destinos(filtros: FiltrosDestinos) -> QuerySet[Destino]:
    """OR dentro de una faceta, AND entre facetas; dificultad en rango; tramos por solape."""
    qs = destinos_publicados()
    if filtros.tipos:
        con_tipo = DestinoTipoAventura.objects.filter(
            destino_id=OuterRef("pk"),
            tipo_aventura__contenido__slug__in=filtros.tipos,
            tipo_aventura__contenido__estado_editorial=PUB,
        )
        qs = qs.filter(Exists(con_tipo))
    if filtros.region:
        qs = qs.filter(pais__region__slug=filtros.region)
    if filtros.pais:
        qs = qs.filter(pais__slug=filtros.pais)
    if filtros.dificultad_min is not None:
        qs = qs.filter(dificultad__gte=filtros.dificultad_min)
    if filtros.dificultad_max is not None:
        qs = qs.filter(dificultad__lte=filtros.dificultad_max)
    if filtros.mes is not None:
        qs = qs.filter(meses_mejor_epoca__contains=[filtros.mes])
    if filtros.duraciones:
        solapa = Q()
        for codigo in filtros.duraciones:
            minimo, maximo, _etiqueta = TRAMOS_DURACION[codigo]
            tramo = Q(duracion_max_dias__gte=minimo)
            if maximo is not None:
                tramo &= Q(duracion_min_dias__lte=maximo)
            solapa |= tramo
        qs = qs.filter(solapa)
    if filtros.presupuestos:
        qs = qs.filter(nivel_presupuesto__in=filtros.presupuestos)
    return con_tarjeta_destino(qs.order_by(*ORDENES_DESTINOS[filtros.orden]))


@dataclass
class Facetas:
    tipos: list[Contenido]
    regiones: list[object]
    dificultad: list[NivelEscala]
    presupuesto: list[NivelEscala]
    tramos_duracion: list[dict[str, object]]


def _tramo_con_destinos(filas: Sequence[tuple[int | None, int | None]], codigo: str) -> bool:
    minimo, maximo, _etiqueta = TRAMOS_DURACION[codigo]
    for dur_min, dur_max in filas:
        if dur_min is None or dur_max is None:
            continue
        if dur_max >= minimo and (maximo is None or dur_min <= maximo):
            return True
    return False


def facetas_destinos(regiones_con_paises: object, niveles: Sequence[NivelEscala]) -> Facetas:
    """Solo valores con destinos publicados (FEAT-004). `regiones_con_paises` es el selector de
    catálogos que devuelve regiones con sus países (inyectado para no acoplar dominios)."""
    destinos = list(
        destinos_publicados().values_list(
            "pais_id",
            "pais__region_id",
            "dificultad",
            "nivel_presupuesto",
            "duracion_min_dias",
            "duracion_max_dias",
        )
    )
    tipos = list(
        Contenido.objects.filter(
            tipo=T.TIPO,
            estado_editorial=PUB,
            tipo_aventura__destinos__in=destinos_publicados(),
        )
        .distinct()
        .order_by("tipo_aventura__orden", "titulo", "slug")
    )
    paises = {fila[0] for fila in destinos if fila[0] is not None}
    regiones = {fila[1] for fila in destinos if fila[1] is not None}
    dificultades = {fila[2] for fila in destinos}
    presupuestos = {fila[3] for fila in destinos}
    duraciones = [(fila[4], fila[5]) for fila in destinos]
    return Facetas(
        tipos=tipos,
        regiones=regiones_con_paises(regiones, paises),  # type: ignore[operator]
        dificultad=[n for n in niveles if n.escala == "DIFICULTAD" and n.nivel in dificultades],
        presupuesto=[n for n in niveles if n.escala == "PRESUPUESTO" and n.nivel in presupuestos],
        tramos_duracion=[
            {"codigo": codigo, "etiqueta": etiqueta, "min_dias": minimo, "max_dias": maximo}
            for codigo, (minimo, maximo, etiqueta) in TRAMOS_DURACION.items()
            if _tramo_con_destinos(duraciones, codigo)
        ],
    )


def destinos_mapa() -> QuerySet[Destino]:
    """AP-04: todos los destinos publicados con coordenadas (≤500, una página)."""
    return (
        destinos_publicados()
        .filter(latitud__isnull=False, longitud__isnull=False)
        .select_related("contenido", "pais__region")
        .order_by("contenido__titulo", "contenido__slug")
    )


def slug_destino_aleatorio() -> str | None:
    """AP-14 (EXP-003): un destino publicado al azar. No es criptográfico (no es un secreto)."""
    slugs = list(destinos_publicados().values_list("contenido__slug", flat=True))
    return random.choice(slugs) if slugs else None  # noqa: S311  # nosec B311


# ---------------------------------------------------------------------------
# Meses (AP-09, RULE-011)
# ---------------------------------------------------------------------------
@dataclass
class Mes:
    mes: int
    slug: str
    nombre: str
    numero_destinos: int
    destacado: Destino | None


def meses() -> list[Mes]:
    filas = list(
        destinos_publicados()
        .order_by("-contenido__fecha_ultima_revision", "contenido__titulo", "pk")
        .values_list("pk", "meses_mejor_epoca")
    )
    conteo = dict.fromkeys(range(1, 13), 0)
    destacado_id: dict[int, int] = {}
    for pk, meses_destino in filas:
        for mes in meses_destino or []:
            conteo[mes] += 1
            destacado_id.setdefault(mes, pk)
    tarjetas = {
        d.pk: d for d in con_tarjeta_destino(Destino.objects.filter(pk__in=destacado_id.values()))
    }
    return [
        Mes(
            mes=numero,
            slug=slug,
            nombre=nombre,
            numero_destinos=conteo[numero],
            destacado=tarjetas.get(destacado_id.get(numero, 0)),
        )
        for numero, (slug, nombre) in enumerate(NOMBRES_MES, start=1)
    ]


# ---------------------------------------------------------------------------
# Resolución de detalles por slug (404 / 410, DEC-AUTO-040/113)
# ---------------------------------------------------------------------------
def contenido_por_slug(tipo: str, slug: str) -> Contenido | None:
    """Fila del supertipo en cualquier estado (la vista decide 404/410/200)."""
    return (
        Contenido.objects.filter(tipo=tipo, slug=slug)
        .only("id", "tipo", "slug", "titulo", "estado_editorial", "primera_publicacion_en")
        .first()
    )


def detalle_destino(pk: int) -> Destino:
    return (
        Destino.objects.select_related("contenido", "pais__region", "tipo_principal__contenido")
        .prefetch_related(*_detalle_comun(), _prefetch_tipos())
        .get(pk=pk)
    )


def detalle_itinerario(pk: int) -> Itinerario:
    return (
        Itinerario.objects.select_related("contenido")
        .prefetch_related(
            *_detalle_comun(),
            _prefetch_tipos(),
            Prefetch("dias", queryset=DiaItinerario.objects.order_by("numero_dia", "id")),
        )
        .get(pk=pk)
    )


def detalle_tipo(pk: int) -> TipoAventura:
    return (
        TipoAventura.objects.select_related("contenido")
        .prefetch_related(
            *_detalle_comun(),
            Prefetch(
                "checklist",
                queryset=ChecklistItem.objects.order_by("orden", "grupo", "texto", "id"),
            ),
        )
        .get(pk=pk)
    )


def detalle_guia(pk: int) -> Guia:
    return (
        Guia.objects.select_related("contenido", "categoria")
        .prefetch_related(
            *_detalle_comun(),
            Prefetch(
                "tipos_aventura", queryset=_tipos_publicos(), to_attr="tipos_relacionados_pub"
            ),
        )
        .get(pk=pk)
    )


def detalle_coleccion(pk: int) -> Coleccion:
    return (
        Coleccion.objects.select_related("contenido")
        .prefetch_related(prefetch_imagen("contenido__portada"))
        .get(pk=pk)
    )


def minutos_lectura(palabras: int) -> int | None:
    """EXP-004 / FEAT-052: ceil(palabras / 200); None si no hay recuento."""
    return math.ceil(palabras / PALABRAS_POR_MINUTO) if palabras > 0 else None


def itinerarios_de_destino(destino_id: int) -> tuple[list[Itinerario], int]:
    qs = itinerarios_publicados().filter(destino_id=destino_id)
    total = qs.count()
    if not total:
        return [], 0
    tarjetas = con_tarjeta_itinerario(qs.order_by("contenido__titulo", "contenido__slug"))
    return list(tarjetas[:MAX_ITINERARIOS_DESTINO]), total


def itinerarios_afines(destino: Destino) -> list[Itinerario]:
    """SCR-004: si el destino no tiene itinerarios, itinerarios de sus tipos o de su región."""
    afinidad = Q(tipos_aventura__in=[t.pk for t in getattr(destino, "tipos_publicos", [])])
    if destino.pais is not None:
        afinidad |= Q(destino__pais__region_id=destino.pais.region_id)
    ids = list(
        itinerarios_publicados()
        .filter(afinidad)
        .exclude(destino_id=destino.pk)
        .order_by("-contenido__fecha_ultima_revision", "contenido__titulo")
        .values_list("pk", flat=True)
        .distinct()[: MAX_AFINES * 4]
    )
    unicos = list(dict.fromkeys(ids))[:MAX_AFINES]
    return _en_orden(con_tarjeta_itinerario(Itinerario.objects.filter(pk__in=unicos)), unicos)


def guias_de_destino(destino_id: int) -> list[Guia]:
    ids = GuiaDestino.objects.filter(destino_id=destino_id).values("guia_id")
    qs = guias_publicadas().filter(pk__in=ids).order_by(*_recientes("contenido__"))
    return list(con_tarjeta_guia(qs)[:MAX_GUIAS_RELACIONADAS])


def guias_de_tipo(tipo_id: int) -> list[Guia]:
    ids = GuiaTipoAventura.objects.filter(tipo_aventura_id=tipo_id).values("guia_id")
    qs = guias_publicadas().filter(pk__in=ids).order_by(*_recientes("contenido__"))
    return list(con_tarjeta_guia(qs)[:MAX_GUIAS_RELACIONADAS])


def destinos_de_tipo(tipo_id: int) -> tuple[list[Destino], int]:
    qs = destinos_publicados().filter(tipos_aventura=tipo_id)
    total = qs.count()
    tarjetas = con_tarjeta_destino(qs.order_by("contenido__titulo", "contenido__slug"))
    return list(tarjetas[:MAX_DESTINOS_TIPO]), total


def destinos_de_guia(guia_id: int) -> list[Destino]:
    ids = GuiaDestino.objects.filter(guia_id=guia_id).values("destino_id")
    qs = destinos_publicados().filter(pk__in=ids).order_by("contenido__titulo")
    return list(con_tarjeta_destino(qs)[:MAX_DESTINOS_GUIA])


@dataclass
class ElementoPublico:
    tipo: str
    orden: int
    nota_editorial: str | None
    destino: Destino | None = None
    itinerario: Itinerario | None = None


def elementos_de_coleccion(coleccion_id: int) -> list[ElementoPublico]:
    """RULE-024: solo los elementos publicados, en su orden."""
    elementos = list(
        ElementoColeccion.objects.filter(
            coleccion_id=coleccion_id, contenido_id__in=_ids_visibles()
        )
        .order_by("orden", "id")
        .values_list("contenido_id", "tipo_contenido", "orden", "nota_editorial")
    )
    ids_destinos = [e[0] for e in elementos if e[1] == T.DESTINO]
    ids_itinerarios = [e[0] for e in elementos if e[1] == T.ITINERARIO]
    destinos = {
        d.pk: d for d in con_tarjeta_destino(destinos_publicados().filter(pk__in=ids_destinos))
    }
    itinerarios = {
        i.pk: i
        for i in con_tarjeta_itinerario(itinerarios_publicados().filter(pk__in=ids_itinerarios))
    }
    resultado: list[ElementoPublico] = []
    for contenido_id, tipo, orden, nota in elementos:
        elemento = ElementoPublico(tipo=tipo, orden=orden, nota_editorial=nota)
        if tipo == T.DESTINO and contenido_id in destinos:
            elemento.destino = destinos[contenido_id]
        elif tipo == T.ITINERARIO and contenido_id in itinerarios:
            elemento.itinerario = itinerarios[contenido_id]
        else:
            continue
        resultado.append(elemento)
    return resultado


# ---------------------------------------------------------------------------
# "Sigue explorando" y alternativas del 410 (RULE-006, DEC-AUTO-042, DEC-AUTO-113)
# ---------------------------------------------------------------------------
@dataclass
class Relacionado:
    contenido: Contenido
    origen: str


def _recientes(prefijo: str = "") -> tuple[str, ...]:
    return tuple(f"-{prefijo}{c[1:]}" if c.startswith("-") else f"{prefijo}{c}" for c in RECIENTES)


def _publicos() -> QuerySet[Contenido]:
    return contenidos_visibles().filter(tipo__in=TIPOS_PUBLICOS)


def _criterios_afinidad(contenido: Contenido) -> list[Q]:
    """Afinidad por tipo principal, región, destino padre o categoría (DEC-AUTO-042).

    Se omiten los criterios cuyo valor de referencia es nulo (no hay afinidad que buscar).
    """
    mismo_tipo = Q(tipo=contenido.tipo)
    criterios: list[Q] = []
    if contenido.tipo == T.DESTINO:
        fila = (
            Destino.objects.filter(pk=contenido.pk)
            .values_list("tipo_principal_id", "pais__region_id")
            .first()
        )
        tipo_principal, region = fila if fila is not None else (None, None)
        if tipo_principal is not None:
            criterios.append(mismo_tipo & Q(destino__tipo_principal_id=tipo_principal))
        if region is not None:
            criterios.append(mismo_tipo & Q(destino__pais__region_id=region))
    elif contenido.tipo == T.ITINERARIO:
        destino_id = (
            Itinerario.objects.filter(pk=contenido.pk).values_list("destino_id", flat=True).first()
        )
        if destino_id is not None:
            criterios += [mismo_tipo & Q(itinerario__destino_id=destino_id), Q(pk=destino_id)]
    elif contenido.tipo == T.GUIA:
        categoria_id = (
            Guia.objects.filter(pk=contenido.pk).values_list("categoria_id", flat=True).first()
        )
        if categoria_id is not None:
            criterios.append(mismo_tipo & Q(guia__categoria_id=categoria_id))
        criterios.append(Q(tipo=T.DESTINO, destino__guias=contenido.pk))
    elif contenido.tipo == T.TIPO:
        criterios.append(Q(tipo=T.DESTINO, destino__tipo_principal_id=contenido.pk))
    return criterios


def _ids_afines(contenido: Contenido, excluidos: set[int], limite: int) -> list[int]:
    criterios = [*_criterios_afinidad(contenido), Q(tipo=contenido.tipo), Q()]
    elegidos: list[int] = []
    for criterio in criterios:
        faltan = limite - len(elegidos)
        if faltan <= 0:
            break
        ids = (
            _publicos()
            .filter(criterio)
            .exclude(pk__in=excluidos | set(elegidos))
            .order_by(*RECIENTES)
            .values_list("pk", flat=True)[:faltan]
        )
        elegidos.extend(ids)
    return elegidos


def _cargar_relacionados(ids: Sequence[int]) -> dict[int, Contenido]:
    filas = (
        Contenido.objects.filter(pk__in=ids)
        .select_related("destino", "itinerario", "guia", "tipo_aventura", "coleccion")
        .prefetch_related(prefetch_imagen("portada"))
    )
    return {c.pk: c for c in filas}


def relacionados(contenido: Contenido, limite: int = MAX_RELACIONADOS) -> list[Relacionado]:
    """Curados (en su orden) + complemento automático por afinidad, solo publicados."""
    curados = list(
        RelacionContenido.objects.filter(
            origen_id=contenido.pk,
            relacionado_id__in=_ids_visibles(),
            relacionado__tipo__in=TIPOS_PUBLICOS,
        )
        .order_by("orden", "id")
        .values_list("relacionado_id", flat=True)[:limite]
    )
    automaticos = _ids_afines(contenido, {contenido.pk, *curados}, limite - len(curados))
    cargados = _cargar_relacionados([*curados, *automaticos])
    return [
        Relacionado(cargados[pk], origen)
        for ids, origen in ((curados, "CURADO"), (automaticos, "AUTOMATICO"))
        for pk in ids
        if pk in cargados
    ]


def _en_orden[M: object](qs: Iterable[M], ids: Sequence[int]) -> list[M]:
    por_id = {getattr(obj, "pk"): obj for obj in qs}  # noqa: B009
    return [por_id[pk] for pk in ids if pk in por_id]


# ---------------------------------------------------------------------------
# Glosario, páginas, colecciones, categorías e índice
# ---------------------------------------------------------------------------
def _refs_publicas() -> QuerySet[ContenidoTermino]:
    return (
        ContenidoTermino.objects.filter(
            contenido_id__in=_ids_visibles(), contenido__tipo__in=TIPOS_CON_TERMINOS
        )
        .select_related("contenido")
        .order_by("contenido__titulo", "id")
    )


def glosario() -> QuerySet[TerminoGlosario]:
    """AP-13: términos publicados en orden alfabético español (collation es-x-icu)."""
    return (
        TerminoGlosario.objects.filter(_publicado())
        .select_related("contenido")
        .prefetch_related(Prefetch("usos", queryset=_refs_publicas(), to_attr="usos_publicos"))
        .order_by("contenido__titulo", "contenido__slug")
    )


def pagina_institucional(clave: str) -> PaginaInstitucional | None:
    return (
        PaginaInstitucional.objects.filter(clave=clave, contenido__estado_editorial=PUB)
        .select_related("contenido")
        .first()
    )


def categorias_con_guias() -> QuerySet[CategoriaGuia]:
    """Categorías activas con ≥1 guía publicada y sus guías más recientes (AP-07)."""
    recientes = con_tarjeta_guia(guias_publicadas().order_by(*_recientes("contenido__")))
    return (
        CategoriaGuia.objects.filter(activo=True)
        .annotate(numero_guias=Count("guias", filter=Q(guias__contenido__estado_editorial=PUB)))
        .filter(numero_guias__gt=0)
        .prefetch_related(Prefetch("guias", queryset=recientes, to_attr="guias_publicas"))
        .order_by("orden", "nombre")
    )


def categoria_con_guias(slug: str) -> CategoriaGuia | None:
    return (
        CategoriaGuia.objects.filter(slug=slug, activo=True, guias__contenido__estado_editorial=PUB)
        .distinct()
        .first()
    )


def listar_guias(categoria: str | None) -> QuerySet[Guia]:
    qs = guias_publicadas()
    if categoria:
        qs = qs.filter(categoria__slug=categoria)
    return con_tarjeta_guia(qs.order_by(*_recientes("contenido__")))


def listar_itinerarios(destino: str | None, orden: str) -> QuerySet[Itinerario]:
    qs = itinerarios_publicados()
    if destino:
        qs = qs.filter(destino__contenido__slug=destino)
    return con_tarjeta_itinerario(qs.order_by(*ORDENES_ITINERARIOS[orden]))


def listar_tipos() -> QuerySet[TipoAventura]:
    return con_tarjeta_tipo(tipos_publicados().order_by("orden", "contenido__titulo"))


def listar_colecciones() -> QuerySet[Coleccion]:
    return con_tarjeta_coleccion(colecciones_publicadas().order_by("contenido__titulo"))


@dataclass
class EntradaIndice:
    tipo: str
    slug: str
    titulo: str
    publicado_actualizado_en: datetime | None
    agrupacion: dict[str, str] | None = field(default=None)


def indice() -> list[EntradaIndice]:
    """AP-12: todo lo publicado (mapa del sitio y sitemap.xml), agrupado por sección."""
    contenidos = (
        contenidos_visibles()
        .exclude(tipo=T.TERMINO)
        .select_related("destino__pais__region", "guia__categoria", "pagina")
        .order_by("tipo", "titulo", "slug")
    )
    entradas: list[EntradaIndice] = []
    for c in contenidos:
        agrupacion = None
        slug = c.slug
        if c.tipo == T.DESTINO and c.destino.pais is not None:
            region = c.destino.pais.region
            agrupacion = {"slug": region.slug, "nombre": region.nombre}
        elif c.tipo == T.GUIA and c.guia.categoria is not None:
            categoria = c.guia.categoria
            agrupacion = {"slug": categoria.slug, "nombre": categoria.nombre}
        elif c.tipo == T.PAGINA:
            slug = SLUG_PAGINA[ClavePagina(c.pagina.clave)]
        entradas.append(
            EntradaIndice(c.tipo, slug, c.titulo, c.publicado_actualizado_en, agrupacion)
        )
    categorias = (
        CategoriaGuia.objects.filter(activo=True, guias__contenido__estado_editorial=PUB)
        .annotate(actualizado=Max("guias__contenido__publicado_actualizado_en"))
        .order_by("orden", "nombre")
    )
    entradas.extend(
        EntradaIndice("CATEGORIA_GUIA", cat.slug, cat.nombre, cat.actualizado) for cat in categorias
    )
    return entradas


# ---------------------------------------------------------------------------
# Inicio (AP-01, RULE-016): mínimos 6/3/3 con relleno por revisión más reciente
# ---------------------------------------------------------------------------
MINIMOS_INICIO = {"destinos": (6, 12), "itinerarios": (3, 6), "guias": (3, 6)}
MAX_TIPOS_INICIO = 30


def _completar(
    base: QuerySet[Any], destacados: Sequence[int], minimo: int, maximo: int
) -> list[int]:
    """Destacados publicados en su orden; si no llegan al mínimo, relleno por revisión reciente."""
    publicados = set(base.filter(pk__in=destacados).values_list("pk", flat=True))
    elegidos = [pk for pk in dict.fromkeys(destacados) if pk in publicados][:maximo]
    if len(elegidos) < minimo:
        relleno = (
            base.exclude(pk__in=elegidos)
            .order_by(*_recientes("contenido__"))
            .values_list("pk", flat=True)[: minimo - len(elegidos)]
        )
        elegidos.extend(relleno)
    return elegidos


def inicio(destacados: dict[str, Sequence[int]]) -> dict[str, Any]:
    """Bloques del inicio; `destacados` son los ids configurados por sección (DATA-022)."""
    fuentes: dict[str, tuple[QuerySet[Any], Any]] = {
        "destinos": (destinos_publicados(), con_tarjeta_destino),
        "itinerarios": (itinerarios_publicados(), con_tarjeta_itinerario),
        "guias": (guias_publicadas(), con_tarjeta_guia),
    }
    datos: dict[str, Any] = {}
    for seccion, (base, tarjeta) in fuentes.items():
        minimo, maximo = MINIMOS_INICIO[seccion]
        ids = _completar(base, destacados.get(seccion, ()), minimo, maximo)
        datos[seccion] = _en_orden(tarjeta(base.model.objects.filter(pk__in=ids)), ids)
    datos["tipos"] = list(listar_tipos()[:MAX_TIPOS_INICIO])
    return datos


# ---------------------------------------------------------------------------
# Fichas completas (detalle + bloques relacionados)
# ---------------------------------------------------------------------------
def ficha_destino(contenido: Contenido) -> Destino:
    destino = detalle_destino(contenido.pk)
    itinerarios, total = itinerarios_de_destino(destino.pk)
    vars(destino).update(
        itinerarios_publicos=itinerarios,
        itinerarios_total=total,
        itinerarios_afines=[] if total else itinerarios_afines(destino),
        guias_relacionadas=guias_de_destino(destino.pk),
        relacionados=relacionados(destino.contenido),
    )
    return destino


def ficha_itinerario(contenido: Contenido) -> Itinerario | None:
    itinerario = detalle_itinerario(contenido.pk)
    tarjeta = con_tarjeta_destino(destinos_publicados().filter(pk=itinerario.destino_id)).first()
    if tarjeta is None:
        # RULE-003: sin destino publicado el itinerario no es público (la cascada lo retira).
        return None
    vars(itinerario).update(
        destino_tarjeta=tarjeta, relacionados=relacionados(itinerario.contenido)
    )
    return itinerario


def ficha_tipo(contenido: Contenido) -> TipoAventura:
    tipo = detalle_tipo(contenido.pk)
    destinos, total = destinos_de_tipo(tipo.pk)
    vars(tipo).update(
        destinos_tarjeta=destinos,
        destinos_total=total,
        guias_relacionadas=guias_de_tipo(tipo.pk),
        relacionados=relacionados(tipo.contenido),
    )
    return tipo


def ficha_guia(contenido: Contenido) -> Guia:
    guia = detalle_guia(contenido.pk)
    vars(guia).update(
        minutos_lectura=minutos_lectura(guia.palabras),
        destinos_relacionados=destinos_de_guia(guia.pk),
        relacionados=relacionados(guia.contenido),
    )
    return guia


def ficha_coleccion(contenido: Contenido) -> Coleccion:
    coleccion = detalle_coleccion(contenido.pk)
    vars(coleccion).update(elementos_publicos=elementos_de_coleccion(coleccion.pk))
    return coleccion


# ---------------------------------------------------------------------------
# Créditos de imágenes (AP-11, FEAT-024)
# ---------------------------------------------------------------------------
def ids_medios_en_uso(hero_medio_id: int | None) -> QuerySet[Medio]:
    """Medios DISPONIBLES usados como portada o galería de contenido publicado, o como hero."""
    portada = _publicos().filter(portada_id=OuterRef("pk"))
    galeria = ContenidoMedio.objects.filter(
        medio_id=OuterRef("pk"),
        contenido_id__in=_ids_visibles(),
        contenido__tipo__in=TIPOS_PUBLICOS,
    )
    en_uso = Q(Exists(portada)) | Q(Exists(galeria))
    if hero_medio_id is not None:
        en_uso |= Q(pk=hero_medio_id)
    return medios_publicos().filter(en_uso).order_by("autor_credito", "id")


def usos_de_medios(medio_ids: Sequence[int]) -> dict[int, list[Contenido]]:
    """Contenido publicado que usa cada medio (portada y galería), sin repetir y ordenado."""
    usos: dict[int, dict[int, Contenido]] = {pk: {} for pk in medio_ids}
    portadas = _publicos().filter(portada_id__in=medio_ids).order_by("titulo", "id")
    for contenido in portadas:
        usos[contenido.portada_id][contenido.pk] = contenido  # type: ignore[index]
    galerias = (
        ContenidoMedio.objects.filter(
            medio_id__in=medio_ids,
            contenido_id__in=_ids_visibles(),
            contenido__tipo__in=TIPOS_PUBLICOS,
        )
        .select_related("contenido")
        .order_by("contenido__titulo", "id")
    )
    for uso in galerias:
        usos[uso.medio_id].setdefault(uso.contenido_id, uso.contenido)
    return {pk: list(por_contenido.values())[:MAX_USADO_EN] for pk, por_contenido in usos.items()}


@dataclass
class Credito:
    medio: Any
    usado_en: list[dict[str, str]]


def creditos(medios: Sequence[Any]) -> list[Credito]:
    usos = usos_de_medios([m.pk for m in medios])
    return [
        Credito(
            medio=m,
            usado_en=[{"tipo": c.tipo, "slug": c.slug, "titulo": c.titulo} for c in usos[m.pk]],
        )
        for m in medios
    ]
