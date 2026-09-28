"""Serializers de salida de la API pública (contracts/openapi.yaml, tags publico-*).

Solo forma y documentación (Skill_Backend Regla 02 y 13): campos explícitos, sin lógica de
negocio ni acceso a datos; los datos llegan ya filtrados (PUBLICADO, medios DISPONIBLES) y
precargados por los selectors. Los nombres de los componentes coinciden con el contrato.
Nunca incluyen ids internos ni datos del staff (THREAT-011, THREAT-019).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalogos.models import PATRON_SLUG, Continente, Escala
from apps.contenido.models import TipoContenido
from apps.core.api.serializers import PaginaMetaSerializer
from apps.medios.models import FormatoDerivado

T = TipoContenido
TIPOS_PUBLICOS = [T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO, T.COLECCION]
TIPOS_BUSCABLES = [T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO]
TIPOS_INDICE = ["DESTINO", "ITINERARIO", "TIPO", "GUIA", "CATEGORIA_GUIA", "COLECCION", "PAGINA"]
SLUGS_PAGINA = [
    "acerca-de",
    "politica-de-tratamiento-de-datos",
    "politica-de-cookies",
    "aviso-legal",
]
SLUGS_MES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
TRAMOS = ["1-3", "4-7", "8-14", "15+"]
TEXTO_ENRIQUECIDO = {
    "type": "string",
    "contentMediaType": "text/html",
    "maxLength": 100000,
    "pattern": "^[^\\u0000]*$",
}
URI = {"type": "string", "format": "uri"}
URI_NULA = {"type": ["string", "null"], "format": "uri"}
URI_REFERENCIA = {"type": "string", "format": "uri-reference"}
Salida = serializers.Serializer[Any]


def lista(
    hijo: type[serializers.Serializer[Any]],
    *,
    source: str | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
) -> serializers.ListField:
    """Array de un componente con minItems/maxItems documentados (drf-spectacular no los emite
    para `many=True`)."""
    extra: dict[str, Any] = {"source": source} if source else {}
    return serializers.ListField(
        child=hijo(), min_length=min_length, max_length=max_length, **extra
    )


class SlugField(serializers.RegexField):
    """components.schemas.Slug."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("min_length", 1)
        kwargs.setdefault("max_length", 120)
        super().__init__(PATRON_SLUG, **kwargs)


@extend_schema_field(TEXTO_ENRIQUECIDO)
class TextoEnriquecidoField(serializers.CharField):
    """HTML de lista blanca ya saneado al guardar (RULE-022, DEC-AUTO-109)."""


@extend_schema_field(URI)
class UriField(serializers.CharField):
    pass


@extend_schema_field(URI_NULA)
class UriNulaField(serializers.CharField):
    pass


class DificultadField(serializers.IntegerField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(min_value=1, max_value=5, **kwargs)


class PresupuestoField(serializers.IntegerField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(min_value=1, max_value=4, **kwargs)


class MesField(serializers.IntegerField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(min_value=1, max_value=12, **kwargs)


@extend_schema_field(
    {
        "type": "array",
        "minItems": 1,
        "maxItems": 12,
        "uniqueItems": True,
        "items": {"type": "integer", "minimum": 1, "maximum": 12},
    }
)
class MesesMejorEpocaField(serializers.ListField):
    """RULE-011: meses 1..12 sin repetir (el CHECK de la BD lo garantiza)."""


def ref(componente: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{componente}"}


def arreglo(
    componente: str, *, min_length: int | None = None, max_length: int | None = None
) -> dict[str, Any]:
    """Esquema de un array de componentes para campos calculados (con minItems/maxItems)."""
    esquema: dict[str, Any] = {"type": "array", "items": ref(componente)}
    if min_length is not None:
        esquema["minItems"] = min_length
    if max_length is not None:
        esquema["maxItems"] = max_length
    return esquema


# ---------------------------------------------------------------------------
# Primitivas compuestas
# ---------------------------------------------------------------------------
class LicenciaPublicaSerializer(Salida):
    codigo = serializers.CharField(max_length=40)
    nombre = serializers.CharField(max_length=120)
    url_texto_legal = UriNulaField(allow_null=True)
    requiere_atribucion = serializers.BooleanField()


class DerivadoImagenSerializer(Salida):
    ancho = serializers.IntegerField(source="ancho_px", min_value=1)
    alto = serializers.IntegerField(source="alto_px", min_value=1)
    formato = serializers.ChoiceField(choices=FormatoDerivado.choices)
    url = serializers.SerializerMethodField()

    @extend_schema_field(URI_REFERENCIA)
    def get_url(self, derivado: Any) -> str:
        # Ruta estática pública con nombre generado por el sistema (DEC-AUTO-110).
        return f"{str(settings.MEDIA_PUBLIC_URL).rstrip('/')}/{derivado.ruta.lstrip('/')}"


class ImagenPublicaSerializer(Salida):
    """Solo medios DISPONIBLES (RULE-005); sin datos del staff (THREAT-019)."""

    texto_alternativo = serializers.CharField(max_length=250)
    pie_de_foto = serializers.CharField(max_length=300, allow_null=True)
    autor_credito = serializers.CharField(max_length=150)
    fuente_url = UriNulaField(allow_null=True)
    licencia = LicenciaPublicaSerializer()
    ancho = serializers.IntegerField(source="ancho_px", min_value=1)
    alto = serializers.IntegerField(source="alto_px", min_value=1)
    derivados = lista(DerivadoImagenSerializer, source="derivados.all", min_length=1, max_length=24)


class RefTaxonomiaSerializer(Salida):
    slug = SlugField()
    nombre = serializers.CharField(max_length=150)


class RegionPublicaSerializer(Salida):
    slug = SlugField()
    nombre = serializers.CharField(max_length=60)
    continente = serializers.ChoiceField(choices=Continente.choices)


class PaisPublicoSerializer(Salida):
    slug = SlugField()
    nombre = serializers.CharField(max_length=80)
    codigo_iso2 = serializers.RegexField(r"^[A-Z]{2}$")
    region = RegionPublicaSerializer()


class NivelEscalaSerializer(Salida):
    escala = serializers.ChoiceField(choices=Escala.choices)
    nivel = serializers.IntegerField(min_value=1, max_value=5)
    etiqueta = serializers.CharField(max_length=40)
    descripcion = serializers.CharField(max_length=400)


class MetadatosEditorialesSerializer(Salida):
    """Firma de equipo (DEC-AUTO-039): nunca creado_por ni nombres del staff."""

    autoria = serializers.SerializerMethodField()
    fecha_ultima_revision = serializers.DateField()
    primera_publicacion_en = serializers.DateTimeField(allow_null=True)
    publicado_actualizado_en = serializers.DateTimeField()
    seo_titulo = serializers.SerializerMethodField()
    seo_descripcion = serializers.CharField(max_length=160)

    @extend_schema_field({"type": "string", "maxLength": 120})
    def get_autoria(self, contenido: Any) -> str:
        return f"Equipo editorial {self.context.get('marca', '')}".strip()

    @extend_schema_field({"type": "string", "maxLength": 70})
    def get_seo_titulo(self, contenido: Any) -> str:
        # Sin título SEO propio se usa el título del contenido, acotado a 70 (RULE-027).
        return str(contenido.seo_titulo or contenido.titulo)[:70]


class FuentePublicaSerializer(Salida):
    titulo = serializers.CharField(max_length=200)
    entidad_editora = serializers.CharField(max_length=150, allow_null=True)
    url = UriNulaField(allow_null=True)
    fecha_consulta = serializers.DateField(allow_null=True)


class TerminoRefSerializer(Salida):
    slug = SlugField(source="termino.contenido.slug")
    termino = serializers.CharField(source="termino.contenido.titulo", max_length=150)


def _refs_tipos(objeto: Any) -> list[dict[str, str]]:
    """Tipos de aventura publicados precargados (to_attr tipos_publicos), como RefTaxonomia."""
    return [
        {"slug": t.contenido.slug, "nombre": t.contenido.titulo}
        for t in getattr(objeto, "tipos_publicos", [])[:12]
    ]


def _resumen_de(contenido: Any) -> str | None:
    for relacion in ("destino", "itinerario", "guia", "tipo_aventura", "coleccion"):
        subtipo = getattr(contenido, relacion, None) if hasattr(contenido, relacion) else None
        if subtipo is not None:
            return getattr(subtipo, "resumen", None)
    return None


class ContenidoRelacionadoSerializer(Salida):
    tipo = serializers.ChoiceField(source="contenido.tipo", choices=TIPOS_PUBLICOS)
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    resumen = serializers.SerializerMethodField()
    portada = ImagenPublicaSerializer(source="contenido.portada", allow_null=True)
    origen = serializers.ChoiceField(choices=["CURADO", "AUTOMATICO"])

    @extend_schema_field({"type": ["string", "null"], "maxLength": 300})
    def get_resumen(self, relacionado: Any) -> str | None:
        return _resumen_de(relacionado.contenido)


class ContenidoRefPublicoSerializer(Salida):
    tipo = serializers.ChoiceField(choices=TIPOS_PUBLICOS)
    slug = SlugField()
    titulo = serializers.CharField(max_length=150)


# ---------------------------------------------------------------------------
# Tarjetas
# ---------------------------------------------------------------------------
class DestinoTarjetaSerializer(Salida):
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    pais = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    tipos = serializers.SerializerMethodField()
    dificultad = DificultadField()
    portada = ImagenPublicaSerializer(source="contenido.portada", allow_null=True)

    @extend_schema_field(RefTaxonomiaSerializer)
    def get_pais(self, destino: Any) -> dict[str, str] | None:
        pais = destino.pais
        return {"slug": pais.slug, "nombre": pais.nombre} if pais is not None else None

    @extend_schema_field(RefTaxonomiaSerializer)
    def get_region(self, destino: Any) -> dict[str, str] | None:
        pais = destino.pais
        if pais is None:
            return None
        return {"slug": pais.region.slug, "nombre": pais.region.nombre}

    @extend_schema_field(arreglo("RefTaxonomia", max_length=12))
    def get_tipos(self, destino: Any) -> list[dict[str, str]]:
        return _refs_tipos(destino)


class ItinerarioTarjetaSerializer(Salida):
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    destino = serializers.SerializerMethodField()
    duracion_dias = serializers.IntegerField(min_value=1, max_value=60)
    dificultad = DificultadField()
    portada = ImagenPublicaSerializer(source="contenido.portada", allow_null=True)

    @extend_schema_field(RefTaxonomiaSerializer)
    def get_destino(self, itinerario: Any) -> dict[str, str] | None:
        destino = itinerario.destino
        if destino is None:
            return None
        return {"slug": destino.contenido.slug, "nombre": destino.contenido.titulo}


class GuiaTarjetaSerializer(Salida):
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    resumen = serializers.CharField(max_length=300)
    categoria = serializers.SerializerMethodField()
    fecha_ultima_revision = serializers.DateField(source="contenido.fecha_ultima_revision")
    minutos_lectura = serializers.IntegerField(min_value=1, allow_null=True)
    portada = ImagenPublicaSerializer(source="contenido.portada", allow_null=True)

    @extend_schema_field(RefTaxonomiaSerializer)
    def get_categoria(self, guia: Any) -> dict[str, str] | None:
        categoria = guia.categoria
        return {"slug": categoria.slug, "nombre": categoria.nombre} if categoria else None


class TipoAventuraTarjetaSerializer(Salida):
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    resumen = serializers.CharField(max_length=300)
    nivel_exigencia = DificultadField()
    numero_destinos = serializers.IntegerField(min_value=0)
    portada = ImagenPublicaSerializer(source="contenido.portada", allow_null=True)


class ColeccionTarjetaSerializer(Salida):
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    resumen = serializers.CharField(max_length=300)
    numero_elementos = serializers.IntegerField(min_value=0)
    portada = ImagenPublicaSerializer(source="contenido.portada", allow_null=True)


class DestinoMapaItemSerializer(Salida):
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    pais = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    latitud = serializers.FloatField(min_value=-90, max_value=90)
    longitud = serializers.FloatField(min_value=-180, max_value=180)
    dificultad = DificultadField()

    get_pais = DestinoTarjetaSerializer.get_pais
    get_region = DestinoTarjetaSerializer.get_region


class DestinoAleatorioSerializer(Salida):
    slug = SlugField()


# ---------------------------------------------------------------------------
# Detalles
# ---------------------------------------------------------------------------
class _DetalleComun(Salida):
    """Campos comunes de los detalles (galería, fuentes, términos, relacionados, metadatos)."""

    fuentes = lista(FuentePublicaSerializer, source="contenido.fuentes_ord", max_length=30)
    terminos = lista(TerminoRefSerializer, source="contenido.terminos_publicos", max_length=50)
    relacionados = lista(ContenidoRelacionadoSerializer, min_length=3, max_length=6)
    metadatos = MetadatosEditorialesSerializer(source="contenido")


def _galeria(objeto: Any) -> list[Any]:
    return [uso.medio for uso in getattr(objeto.contenido, "galeria_publica", [])]


class DestinoDetalleSerializer(_DetalleComun):
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    pais = PaisPublicoSerializer()
    resumen = serializers.CharField(max_length=300)
    descripcion_experta = TextoEnriquecidoField()
    tipos = serializers.SerializerMethodField()
    tipo_principal = serializers.SerializerMethodField()
    dificultad = DificultadField()
    meses_mejor_epoca = MesesMejorEpocaField(child=MesField(), min_length=1, max_length=12)
    duracion_min_dias = serializers.IntegerField(min_value=1, max_value=90)
    duracion_max_dias = serializers.IntegerField(min_value=1, max_value=90)
    nivel_presupuesto = PresupuestoField()
    clima = serializers.CharField(max_length=5000)
    altitud_max_m = serializers.IntegerField(min_value=-500, max_value=9000, allow_null=True)
    como_llegar = TextoEnriquecidoField()
    seguridad_riesgos = TextoEnriquecidoField()
    sostenibilidad = TextoEnriquecidoField()
    latitud = serializers.FloatField(min_value=-90, max_value=90)
    longitud = serializers.FloatField(min_value=-180, max_value=180)
    portada = ImagenPublicaSerializer(source="contenido.portada")
    galeria = serializers.SerializerMethodField()
    itinerarios = lista(ItinerarioTarjetaSerializer, source="itinerarios_publicos", max_length=12)
    itinerarios_total = serializers.IntegerField(min_value=0)
    itinerarios_afines = lista(ItinerarioTarjetaSerializer, max_length=6)
    guias_relacionadas = lista(GuiaTarjetaSerializer, max_length=6)

    @extend_schema_field(arreglo("RefTaxonomia", min_length=1, max_length=12))
    def get_tipos(self, objeto: Any) -> list[dict[str, str]]:
        return _refs_tipos(objeto)

    @extend_schema_field(RefTaxonomiaSerializer)
    def get_tipo_principal(self, destino: Any) -> dict[str, str] | None:
        tipo = destino.tipo_principal
        if tipo is None:
            return None
        return {"slug": tipo.contenido.slug, "nombre": tipo.contenido.titulo}

    @extend_schema_field(arreglo("ImagenPublica", min_length=3, max_length=30))
    def get_galeria(self, destino: Any) -> list[dict[str, Any]]:
        return list(ImagenPublicaSerializer(_galeria(destino), many=True).data)


class DiaItinerarioSerializer(Salida):
    numero_dia = serializers.IntegerField(min_value=1, max_value=60)
    titulo = serializers.CharField(max_length=150)
    actividades = TextoEnriquecidoField()
    distancia_km = serializers.FloatField(min_value=0, allow_null=True)
    desnivel_positivo_m = serializers.IntegerField(min_value=0, allow_null=True)
    desnivel_negativo_m = serializers.IntegerField(min_value=0, allow_null=True)
    alojamiento_orientativo = serializers.CharField(max_length=300, allow_null=True)
    consejos = serializers.SerializerMethodField()

    @extend_schema_field({"type": ["string", "null"], "contentMediaType": "text/html"})
    def get_consejos(self, dia: Any) -> str | None:
        return dia.consejos  # type: ignore[no-any-return]


class ItinerarioDetalleSerializer(_DetalleComun):
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    destino = DestinoTarjetaSerializer(source="destino_tarjeta")
    duracion_dias = serializers.IntegerField(min_value=1, max_value=60)
    dificultad = DificultadField()
    tipos = serializers.SerializerMethodField()
    resumen = serializers.CharField(max_length=300)
    distancia_total_km = serializers.FloatField(min_value=0, allow_null=True)
    desnivel_acumulado_m = serializers.IntegerField(min_value=0, allow_null=True)
    dias = lista(DiaItinerarioSerializer, source="dias.all", min_length=1, max_length=60)
    riesgos_seguridad = TextoEnriquecidoField()
    portada = ImagenPublicaSerializer(source="contenido.portada")
    galeria = serializers.SerializerMethodField()

    @extend_schema_field(arreglo("RefTaxonomia", min_length=1, max_length=12))
    def get_tipos(self, objeto: Any) -> list[dict[str, str]]:
        return _refs_tipos(objeto)

    @extend_schema_field(arreglo("ImagenPublica", max_length=30))
    def get_galeria(self, itinerario: Any) -> list[dict[str, Any]]:
        return list(ImagenPublicaSerializer(_galeria(itinerario), many=True).data)


class ChecklistItemSerializer(Salida):
    texto = serializers.CharField(max_length=200)
    grupo = serializers.CharField(max_length=60, allow_null=True)
    esencial = serializers.BooleanField()
    orden = serializers.IntegerField(min_value=0)


class TipoAventuraDetalleSerializer(_DetalleComun):
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    resumen = serializers.CharField(max_length=300)
    descripcion = TextoEnriquecidoField()
    nivel_exigencia = DificultadField()
    portada = ImagenPublicaSerializer(source="contenido.portada")
    destinos = lista(DestinoTarjetaSerializer, source="destinos_tarjeta", max_length=12)
    destinos_total = serializers.IntegerField(min_value=0)
    checklist = lista(ChecklistItemSerializer, source="checklist.all", max_length=100)
    guias_relacionadas = lista(GuiaTarjetaSerializer, max_length=6)


class CategoriaGuiaPublicaSerializer(Salida):
    slug = SlugField()
    nombre = serializers.CharField(max_length=80)
    descripcion = serializers.CharField(max_length=400)


class CategoriaGuiaIndiceSerializer(CategoriaGuiaPublicaSerializer):
    numero_guias = serializers.IntegerField(min_value=1)
    guias_recientes = serializers.SerializerMethodField()

    @extend_schema_field(arreglo("GuiaTarjeta", max_length=4))
    def get_guias_recientes(self, categoria: Any) -> list[dict[str, Any]]:
        guias = getattr(categoria, "guias_publicas", [])[: self.context.get("recientes", 4)]
        return list(GuiaTarjetaSerializer(guias, many=True).data)


class GuiaDetalleSerializer(_DetalleComun):
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    categoria = CategoriaGuiaPublicaSerializer()
    resumen = serializers.CharField(max_length=300)
    cuerpo = TextoEnriquecidoField()
    minutos_lectura = serializers.IntegerField(min_value=1, allow_null=True)
    portada = ImagenPublicaSerializer(source="contenido.portada")
    destinos_relacionados = lista(DestinoTarjetaSerializer, max_length=20)
    tipos_relacionados = serializers.SerializerMethodField()
    remite_a_metodologia = serializers.BooleanField()

    @extend_schema_field(arreglo("RefTaxonomia", max_length=12))
    def get_tipos_relacionados(self, guia: Any) -> list[dict[str, str]]:
        return [
            {"slug": t.contenido.slug, "nombre": t.contenido.titulo}
            for t in getattr(guia, "tipos_relacionados_pub", [])[:12]
        ]


class ElementoColeccionSerializer(Salida):
    tipo = serializers.ChoiceField(choices=[T.DESTINO, T.ITINERARIO])
    orden = serializers.IntegerField(min_value=0)
    nota_editorial = serializers.CharField(max_length=300, allow_null=True)
    destino = DestinoTarjetaSerializer(allow_null=True)
    itinerario = ItinerarioTarjetaSerializer(allow_null=True)


class ColeccionDetalleSerializer(Salida):
    slug = SlugField(source="contenido.slug")
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    resumen = serializers.CharField(max_length=300)
    descripcion = TextoEnriquecidoField()
    portada = ImagenPublicaSerializer(source="contenido.portada")
    elementos = lista(ElementoColeccionSerializer, source="elementos_publicos", max_length=100)
    metadatos = MetadatosEditorialesSerializer(source="contenido")


class PaginaInstitucionalPublicaSerializer(Salida):
    slug = serializers.ChoiceField(source="slug_publico", choices=SLUGS_PAGINA)
    titulo = serializers.CharField(source="contenido.titulo", max_length=150)
    cuerpo = TextoEnriquecidoField()
    version_documento = serializers.CharField(max_length=20)
    vigente_desde = serializers.DateField()
    metadatos = MetadatosEditorialesSerializer(source="contenido")


# ---------------------------------------------------------------------------
# Agregados
# ---------------------------------------------------------------------------
class HeroSerializer(Salida):
    titular = serializers.CharField(source="hero_titular", max_length=80)
    subtitulo = serializers.CharField(source="hero_subtitulo", max_length=160)
    imagen = ImagenPublicaSerializer(source="hero_medio")


HERO_SCHEMA: dict[str, Any] = {
    "type": ["object", "null"],
    "required": ["titular", "subtitulo", "imagen"],
    "properties": {
        "titular": {"type": "string", "maxLength": 80},
        "subtitulo": {"type": "string", "maxLength": 160},
        "imagen": ref("ImagenPublica"),
    },
}


class InicioSerializer(Salida):
    hero = serializers.SerializerMethodField()
    destinos = lista(DestinoTarjetaSerializer, max_length=12)
    itinerarios = lista(ItinerarioTarjetaSerializer, max_length=6)
    guias = lista(GuiaTarjetaSerializer, max_length=6)
    tipos = lista(TipoAventuraTarjetaSerializer, max_length=30)

    @extend_schema_field(HERO_SCHEMA)
    def get_hero(self, datos: Any) -> dict[str, Any] | None:
        hero = datos.get("hero")
        return dict(HeroSerializer(hero).data) if hero is not None else None


class ResponsableSerializer(Salida):
    """Si `definido` es false, el Frontend muestra [RESPONSABLE POR DEFINIR] (GAP-004)."""

    definido = serializers.BooleanField()
    nombre = serializers.CharField(max_length=150, allow_null=True)
    identificacion = serializers.CharField(max_length=40, allow_null=True)
    domicilio = serializers.CharField(max_length=200, allow_null=True)
    canal_atencion = serializers.CharField(max_length=200, allow_null=True)


class ConfiguracionPublicaSerializer(Salida):
    nombre_marca = serializers.CharField(max_length=60)
    lema = serializers.CharField(max_length=120, allow_null=True)
    texto_descargo = serializers.CharField(max_length=5000)
    responsable = ResponsableSerializer()


class EscalasSerializer(Salida):
    dificultad = lista(NivelEscalaSerializer, min_length=5, max_length=5)
    presupuesto = lista(NivelEscalaSerializer, min_length=4, max_length=4)


class MesSerializer(Salida):
    mes = MesField()
    nombre = serializers.CharField(max_length=12)
    slug = serializers.ChoiceField(choices=SLUGS_MES)
    numero_destinos = serializers.IntegerField(min_value=0)
    destacado = DestinoTarjetaSerializer(allow_null=True)


class MesesSerializer(Salida):
    meses = lista(MesSerializer, min_length=12, max_length=12)


class RegionFacetaSerializer(Salida):
    slug = SlugField()
    nombre = serializers.CharField(max_length=60)
    continente = serializers.ChoiceField(choices=Continente.choices)
    paises = serializers.SerializerMethodField()

    @extend_schema_field(arreglo("RefTaxonomia", max_length=250))
    def get_paises(self, region: Any) -> list[dict[str, str]]:
        return [{"slug": p.slug, "nombre": p.nombre} for p in region.paises_publicos]


class TramoDuracionSerializer(Salida):
    codigo = serializers.ChoiceField(choices=TRAMOS)
    etiqueta = serializers.CharField(max_length=40)
    min_dias = serializers.IntegerField(min_value=1)
    max_dias = serializers.IntegerField(min_value=1, allow_null=True)


class FacetasDestinosSerializer(Salida):
    tipos = serializers.SerializerMethodField()
    regiones = lista(RegionFacetaSerializer, max_length=20)
    dificultad = lista(NivelEscalaSerializer, max_length=5)
    presupuesto = lista(NivelEscalaSerializer, max_length=4)
    tramos_duracion = lista(TramoDuracionSerializer, max_length=4)

    @extend_schema_field(arreglo("RefTaxonomia", max_length=30))
    def get_tipos(self, facetas: Any) -> list[dict[str, str]]:
        return [{"slug": c.slug, "nombre": c.titulo} for c in facetas.tipos]


class TerminoGlosarioPublicoSerializer(Salida):
    slug = SlugField(source="contenido.slug")
    termino = serializers.CharField(source="contenido.titulo", max_length=150)
    definicion = serializers.CharField(max_length=600)
    usado_en = serializers.SerializerMethodField()

    @extend_schema_field(arreglo("ContenidoRefPublico", max_length=20))
    def get_usado_en(self, termino: Any) -> list[dict[str, str]]:
        return [
            {"tipo": uso.contenido.tipo, "slug": uso.contenido.slug, "titulo": uso.contenido.titulo}
            for uso in getattr(termino, "usos_publicos", [])[:20]
        ]


class CreditoMedioSerializer(Salida):
    imagen = ImagenPublicaSerializer(source="medio")
    usado_en = lista(ContenidoRefPublicoSerializer, max_length=20)


class EntradaIndiceSerializer(Salida):
    tipo = serializers.ChoiceField(choices=TIPOS_INDICE)
    slug = SlugField()
    titulo = serializers.CharField(max_length=150)
    agrupacion = RefTaxonomiaSerializer(allow_null=True)
    publicado_actualizado_en = serializers.DateTimeField()


class ResultadoBusquedaSerializer(Salida):
    tipo = serializers.ChoiceField(choices=TIPOS_BUSCABLES)
    slug = SlugField()
    titulo = serializers.CharField(max_length=150)
    resumen = serializers.CharField(max_length=300, allow_null=True)
    pais = serializers.CharField(max_length=80, allow_null=True)
    portada = ImagenPublicaSerializer(allow_null=True)


class GrupoBusquedaSerializer(Salida):
    total = serializers.IntegerField(min_value=0)
    resultados = lista(ResultadoBusquedaSerializer, max_length=10)


class GruposBusquedaSerializer(Salida):
    destinos = GrupoBusquedaSerializer()
    itinerarios = GrupoBusquedaSerializer()
    guias = GrupoBusquedaSerializer()
    tipos = GrupoBusquedaSerializer()


class BusquedaAgrupadaSerializer(Salida):
    """No incluye `q` (THREAT-010)."""

    total = serializers.IntegerField(min_value=0)
    grupos = GruposBusquedaSerializer()


PROBLEMA_RETIRADO: dict[str, Any] = {
    "allOf": [
        ref("Problem"),
        {
            "type": "object",
            "required": ["alternativas"],
            "properties": {
                "alternativas": {
                    "type": "array",
                    "maxItems": 6,
                    "items": ref("ContenidoRelacionado"),
                },
                "listado_padre": {
                    "type": "string",
                    "description": "Ruta pública del listado padre (p. ej. /destinos).",
                    "pattern": "^/[a-z0-9/-]*$",
                },
            },
        },
    ]
}
"""components.schemas.ProblemaRetirado (410, DEC-AUTO-113): Problem + alternativas publicadas."""


# ---------------------------------------------------------------------------
# Páginas (PaginaMeta + resultados, DEC-AUTO-104)
# ---------------------------------------------------------------------------
class PaginaDestinoTarjetaSerializer(PaginaMetaSerializer):
    resultados = DestinoTarjetaSerializer(many=True)


class PaginaDestinoMapaSerializer(PaginaMetaSerializer):
    resultados = DestinoMapaItemSerializer(many=True)


class PaginaItinerarioTarjetaSerializer(PaginaMetaSerializer):
    resultados = ItinerarioTarjetaSerializer(many=True)


class PaginaTipoAventuraTarjetaSerializer(PaginaMetaSerializer):
    resultados = TipoAventuraTarjetaSerializer(many=True)


@extend_schema_field(
    {
        "type": "array",
        "items": {
            "allOf": [
                ref("CategoriaGuiaPublica"),
                {
                    "type": "object",
                    "required": ["numero_guias", "guias_recientes"],
                    "properties": {
                        "numero_guias": {"type": "integer", "minimum": 1},
                        "guias_recientes": {
                            "type": "array",
                            "maxItems": 4,
                            "items": ref("GuiaTarjeta"),
                        },
                    },
                },
            ]
        },
    }
)
class _ListaCategoriaGuiaIndice(serializers.ListField):
    """components.schemas.CategoriaGuiaIndice = allOf(CategoriaGuiaPublica, ...)."""


class PaginaCategoriaGuiaIndiceSerializer(PaginaMetaSerializer):
    resultados = _ListaCategoriaGuiaIndice(child=CategoriaGuiaIndiceSerializer())


class PaginaGuiaTarjetaSerializer(PaginaMetaSerializer):
    resultados = GuiaTarjetaSerializer(many=True)


class PaginaColeccionTarjetaSerializer(PaginaMetaSerializer):
    resultados = ColeccionTarjetaSerializer(many=True)


class PaginaResultadoBusquedaSerializer(PaginaMetaSerializer):
    resultados = ResultadoBusquedaSerializer(many=True)


class PaginaTerminoGlosarioPublicoSerializer(PaginaMetaSerializer):
    resultados = TerminoGlosarioPublicoSerializer(many=True)


class PaginaCreditoMedioSerializer(PaginaMetaSerializer):
    resultados = CreditoMedioSerializer(many=True)


class PaginaEntradaIndiceSerializer(PaginaMetaSerializer):
    resultados = EntradaIndiceSerializer(many=True)
