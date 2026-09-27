"""Constructores de contenido PUBLICADO coherente para las pruebas de la API pública (TKT-005).

Datos ficticios, sin PII real. Cumplen los CHECK de la BD para PUBLICADO/RETIRADO y los
requisitos de publicación (portada y galería DISPONIBLES, relaciones, fechas).
"""

from __future__ import annotations

import itertools
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.utils import timezone

from apps.catalogos.models import CategoriaGuia, Licencia, Pais, Region
from apps.contenido.models import (
    ChecklistItem,
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
)
from apps.contenido.tests.fabricas import huella
from apps.inicio.models import ConfigInicio, DestacadoInicio
from apps.medios.models import EstadoMedio, Medio, MedioDerivado

_n = itertools.count(1)
BASE = date(2026, 9, 1)


def _sig() -> int:
    return next(_n)


def licencia() -> Licencia:
    return Licencia.objects.filter(compatible_publicacion=True, activo=True).order_by("id").first()


def medio(estado: str = EstadoMedio.DISPONIBLE, **campos: Any) -> Medio:
    n = _sig()
    datos: dict[str, Any] = {
        "archivo_saneado_ruta": f"originales/pub-{n}.jpg",
        "formato_origen": "JPEG",
        "ancho_px": 1600,
        "alto_px": 1200,
        "peso_bytes": 250_000,
        "huella_sha256": huella(f"pub-original-{n}"),
        "sha256_saneado": huella(f"pub-saneado-{n}"),
        "estado": estado,
        "texto_alternativo": f"Vista del paisaje {n}",
        "autor_credito": f"Fotógrafo {n}",
        "licencia": licencia(),
        "pie_de_foto": None,
    }
    datos.update(campos)
    creado = Medio.objects.create(**datos)
    for formato, ancho in (("AVIF", 800), ("WEBP", 800), ("JPEG", 1600)):
        MedioDerivado.objects.create(
            medio=creado,
            formato=formato,
            ancho_px=ancho,
            alto_px=ancho * 3 // 4,
            ruta=f"derivados/{n}-{ancho}.{formato.lower()}",
            peso_bytes=1000,
            sha256=huella(f"der-{n}-{formato}"),
        )
    return creado


def pais(nombre: str = "", region: Region | None = None, iso: str = "") -> Pais:
    n = _sig()
    region = region or Region.objects.order_by("orden", "id").first()
    iso = iso or f"{chr(65 + n % 26)}{chr(65 + (n // 26) % 26)}"
    while Pais.objects.filter(codigo_iso2=iso).exists():
        n = _sig()
        iso = f"{chr(65 + n % 26)}{chr(65 + (n // 26) % 26)}"
    nombre = nombre or f"País {n}"
    return Pais.objects.create(nombre=nombre, slug=f"pais-{n}", codigo_iso2=iso, region=region)


def _contenido(tipo: str, titulo: str, estado: str, revision: date, **campos: Any) -> Contenido:
    n = _sig()
    ahora = timezone.now()
    datos: dict[str, Any] = {
        "tipo": tipo,
        "slug": campos.pop("slug", f"{tipo.lower()}-{n}"),
        "titulo": titulo,
        "estado_editorial": estado,
    }
    if estado != EstadoEditorial.BORRADOR or campos.pop("publicado_antes", False):
        datos.update(
            fecha_ultima_revision=revision,
            primera_publicacion_en=ahora - timedelta(days=30),
            publicado_actualizado_en=ahora - timedelta(days=1),
        )
    if tipo not in ("TERMINO",) and estado == EstadoEditorial.PUBLICADO:
        datos["seo_descripcion"] = f"Descripción SEO única {n} de {titulo}"[:160]
    if tipo not in ("TERMINO", "PAGINA"):
        datos["portada"] = campos.pop("portada", None) or medio()
    if estado == EstadoEditorial.RETIRADO:
        datos.update(retirado_en=ahora, motivo_retiro="Retirado en pruebas")
    datos.update(campos)
    return Contenido.objects.create(**datos)


def galeria(contenido: Contenido, cantidad: int = 3) -> None:
    for orden in range(cantidad):
        ContenidoMedio.objects.create(
            contenido=contenido, tipo_contenido=contenido.tipo, medio=medio(), orden=orden
        )


def tipo(
    titulo: str, estado: str = EstadoEditorial.PUBLICADO, orden: int = 0, **campos: Any
) -> TipoAventura:
    c = _contenido("TIPO", titulo, estado, BASE, **campos)
    t = TipoAventura.objects.create(
        contenido=c,
        resumen=f"Resumen de {titulo}",
        descripcion=f"<p>Descripción de {titulo}</p>",
        nivel_exigencia=3,
        orden=orden,
    )
    for i in range(2):
        ChecklistItem.objects.create(
            tipo_aventura=t, texto=f"Elemento {i} de {titulo}", grupo="Equipo", esencial=i == 0
        )
    galeria(c, 1)
    return t


def destino(
    titulo: str,
    *,
    tipos: list[TipoAventura],
    pais_: Pais | None = None,
    estado: str = EstadoEditorial.PUBLICADO,
    dificultad: int = 3,
    meses: list[int] | None = None,
    duracion: tuple[int, int] = (4, 7),
    presupuesto: int = 2,
    revision: date = BASE,
    coordenadas: tuple[str, str] | None = ("4.5", "-74.1"),
    cuerpo: str = "",
    **campos: Any,
) -> Destino:
    c = _contenido("DESTINO", titulo, estado, revision, **campos)
    lat, lon = coordenadas if coordenadas else (None, None)
    d = Destino.objects.create(
        contenido=c,
        pais=pais_ or pais(),
        resumen=f"Resumen de {titulo}",
        descripcion_experta=cuerpo or f"<p>Descripción experta de {titulo}</p>",
        tipo_principal=tipos[0] if tipos else None,
        dificultad=dificultad,
        meses_mejor_epoca=meses or [1, 2],
        duracion_min_dias=duracion[0],
        duracion_max_dias=duracion[1],
        nivel_presupuesto=presupuesto,
        clima="Templado",
        altitud_max_m=2600,
        como_llegar="<p>En autobús</p>",
        seguridad_riesgos="<p>Riesgos moderados</p>",
        sostenibilidad="<p>No dejes rastro</p>",
        latitud=Decimal(lat) if lat else None,
        longitud=Decimal(lon) if lon else None,
    )
    for t in tipos:
        DestinoTipoAventura.objects.create(destino=d, tipo_aventura=t)
    galeria(c, 3)
    Fuente.objects.create(contenido=c, titulo=f"Fuente de {titulo}", url="https://example.org")
    return d


def itinerario(
    titulo: str,
    destino_: Destino,
    *,
    dias: int = 3,
    estado: str = EstadoEditorial.PUBLICADO,
    tipos: list[TipoAventura] | None = None,
    **campos: Any,
) -> Itinerario:
    c = _contenido("ITINERARIO", titulo, estado, BASE, **campos)
    i = Itinerario.objects.create(
        contenido=c,
        destino=destino_,
        resumen=f"Resumen de {titulo}",
        duracion_dias=dias,
        dificultad=2,
        riesgos_seguridad="<p>Lleva agua</p>",
        distancia_total_km=Decimal("42.5"),
        desnivel_acumulado_m=1200,
    )
    for numero in range(1, dias + 1):
        DiaItinerario.objects.create(
            itinerario=i, numero_dia=numero, titulo=f"Día {numero}", actividades="<p>Caminar</p>"
        )
    for t in tipos or []:
        ItinerarioTipoAventura.objects.create(itinerario=i, tipo_aventura=t)
    return i


def categoria() -> CategoriaGuia:
    return CategoriaGuia.objects.filter(activo=True).order_by("orden", "id").first()


def guia(
    titulo: str,
    *,
    categoria_: CategoriaGuia | None = None,
    estado: str = EstadoEditorial.PUBLICADO,
    destinos: list[Destino] | None = None,
    tipos: list[TipoAventura] | None = None,
    revision: date = BASE,
    palabras: int = 450,
    **campos: Any,
) -> Guia:
    c = _contenido("GUIA", titulo, estado, revision, **campos)
    g = Guia.objects.create(
        contenido=c,
        categoria=categoria_ or categoria(),
        resumen=f"Resumen de {titulo}",
        cuerpo=f"<p>Cuerpo de {titulo}</p>",
        palabras=palabras,
        remite_a_metodologia=True,
    )
    for d in destinos or []:
        GuiaDestino.objects.create(guia=g, destino=d)
    for t in tipos or []:
        GuiaTipoAventura.objects.create(guia=g, tipo_aventura=t)
    return g


def coleccion(titulo: str, elementos: list[Contenido], **campos: Any) -> Coleccion:
    c = _contenido("COLECCION", titulo, campos.pop("estado", EstadoEditorial.PUBLICADO), BASE)
    col = Coleccion.objects.create(
        contenido=c, resumen=f"Resumen de {titulo}", descripcion="<p>Colección</p>"
    )
    for orden, elemento in enumerate(elementos):
        ElementoColeccion.objects.create(
            coleccion=col,
            contenido=elemento,
            tipo_contenido=elemento.tipo,
            orden=orden,
            nota_editorial=f"Nota {orden}",
        )
    return col


def termino(titulo: str, usado_en: list[Contenido], **campos: Any) -> TerminoGlosario:
    estado = campos.pop("estado", EstadoEditorial.PUBLICADO)
    c = _contenido("TERMINO", titulo, estado, BASE)
    t = TerminoGlosario.objects.create(contenido=c, definicion=f"Definición de {titulo}")
    for contenido in usado_en:
        ContenidoTermino.objects.create(
            contenido=contenido, tipo_contenido=contenido.tipo, termino=t
        )
    return t


def pagina(clave: str, titulo: str, estado: str = EstadoEditorial.PUBLICADO) -> PaginaInstitucional:
    c = _contenido("PAGINA", titulo, estado, BASE)
    return PaginaInstitucional.objects.create(
        contenido=c,
        clave=clave,
        cuerpo=f"<p>{titulo}</p>",
        version_documento="1.0",
        vigente_desde=BASE,
    )


def relacionar(origen: Contenido, *relacionados: Contenido) -> None:
    for orden, rel in enumerate(relacionados):
        RelacionContenido.objects.create(
            origen=origen,
            origen_tipo=origen.tipo,
            relacionado=rel,
            relacionado_tipo=rel.tipo,
            orden=orden,
        )


def config_inicio(hero: Medio | None = None) -> ConfigInicio:
    return ConfigInicio.objects.create(
        hero_titular="Explora lo salvaje",
        hero_subtitulo="Destinos de aventura",
        hero_medio=hero or medio(),
    )


def destacar(seccion: str, *contenidos: Contenido) -> None:
    for orden, c in enumerate(contenidos):
        DestacadoInicio.objects.create(
            seccion=seccion, contenido=c, tipo_contenido=c.tipo, orden=orden
        )


def mundo() -> dict[str, Any]:
    """Conjunto coherente: 3 tipos, 6 destinos (1 retirado, 1 borrador), itinerarios, guías, etc."""
    regiones = list(Region.objects.order_by("orden", "id")[:2])
    co = pais("Colombia", regiones[0], "CO")
    pe = pais("Perú", regiones[0], "PE")
    np_ = pais("Nepal", regiones[1], "NP")
    trek = tipo("Trekking", orden=1)
    kayak = tipo("Kayak", orden=2)
    escalada = tipo("Escalada en roca", orden=3)
    tipo_borrador = tipo("Tipo borrador", estado=EstadoEditorial.BORRADOR)
    cocuy = destino(
        "El Cocuy", tipos=[trek, escalada], pais_=co, dificultad=4, meses=[1, 2, 12],
        duracion=(5, 8), presupuesto=2, cuerpo="<p>Glaciares y lagunas de alta montaña</p>",
    )  # fmt: skip
    salento = destino(
        "Salento", tipos=[trek], pais_=co, dificultad=1, meses=[6, 7], duracion=(1, 3),
        presupuesto=1, revision=BASE + timedelta(days=5),
    )  # fmt: skip
    colca = destino(
        "Cañón del Colca", tipos=[trek, kayak], pais_=pe, dificultad=3, meses=[5, 6],
        duracion=(3, 5), presupuesto=3,
    )  # fmt: skip
    annapurna = destino(
        "Annapurna", tipos=[trek], pais_=np_, dificultad=5, meses=[10, 11], duracion=(12, 20),
        presupuesto=4, coordenadas=("28.596", "83.820"),
    )  # fmt: skip
    retirado = destino("Destino retirado", tipos=[trek], pais_=co, estado=EstadoEditorial.RETIRADO)
    borrador = destino("Destino borrador", tipos=[trek], pais_=co, estado=EstadoEditorial.BORRADOR)
    ruta_cocuy = itinerario("Travesía del Cocuy", cocuy, dias=5, tipos=[trek])
    ruta_colca = itinerario("Colca en tres días", colca, dias=3, tipos=[trek, kayak])
    guia_equipo = guia("Cómo elegir botas", destinos=[cocuy, salento], tipos=[trek])
    guia_altura = guia("Mal de altura", destinos=[annapurna], revision=BASE + timedelta(days=10))
    col = coleccion(
        "Andes esenciales", [cocuy.contenido, colca.contenido, ruta_cocuy.contenido,
                             retirado.contenido],
    )  # fmt: skip
    glaciar = termino("Glaciar", [cocuy.contenido])
    relacionar(cocuy.contenido, salento.contenido, ruta_cocuy.contenido, guia_equipo.contenido)
    acerca = pagina("ACERCA_DE", "Acerca de")
    return {
        "paises": (co, pe, np_),
        "tipos": (trek, kayak, escalada),
        "tipo_borrador": tipo_borrador,
        "cocuy": cocuy,
        "salento": salento,
        "colca": colca,
        "annapurna": annapurna,
        "retirado": retirado,
        "borrador": borrador,
        "ruta_cocuy": ruta_cocuy,
        "ruta_colca": ruta_colca,
        "guia_equipo": guia_equipo,
        "guia_altura": guia_altura,
        "coleccion": col,
        "termino": glaciar,
        "acerca": acerca,
    }
