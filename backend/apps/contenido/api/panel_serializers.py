"""Serializers del panel editorial (contracts/openapi.yaml, tag `panel-contenidos` y
`panel-ciclo-editorial`). Solo forma y validación de estructura (Skill_Backend Regla 02): la
lógica de negocio y el guardado viven en `apps.contenido.services`.

Los campos de entrada usan `EntradaEstricta` (additionalProperties/unevaluatedProperties: false
del contrato → 400 `campo_no_permitido`, DEC-AUTO-108, THREAT-024). Las salidas son serializers
explícitos (Regla 13): nunca `__all__`.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.contenido.models import ClavePagina, TipoContenido
from apps.core.api.serializers import EntradaEstricta, IdSerializerField, PaginaMetaSerializer

T = TipoContenido


@extend_schema_field({"type": "string"})
class _CampoTipo(serializers.ChoiceField):
    """`ChoiceField` con validación real pero esquema en línea sin clave `enum` nombrada.

    `extend_schema_field` solo sobrevive al `Field.__deepcopy__` de DRF (que reconstruye la
    instancia vía `self.__class__(*args, **kwargs)` al enlazar el serializer, perdiendo cualquier
    atributo puesto sobre la instancia) si se aplica sobre la CLASE, nunca sobre la instancia: de
    ahí esta subclase en vez de decorar cada `ChoiceField(...)` suelto. Evita que drf-spectacular
    registre y reconcilie un componente de enum compartido entre los varios subconjuntos de
    `tipo`/`tipo_contenido` del contrato (W001). `ENUM_NAME_OVERRIDES` (la vía recomendada) vive en
    `config/settings/base.py`, fuera de los `archivos_permitidos` de TKT-006.
    """


def _tipo_field(choices: Any) -> serializers.ChoiceField:
    return _CampoTipo(choices=choices)


def _tipo_entidad_field() -> serializers.ChoiceField:
    return _CampoTipo(choices=TipoContenido.choices)


PATRON_SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"
PATRON_NO_NUL = r"^[^\x00]*$"


def _texto(max_length: int, *, requerido: bool = False, nulo: bool = True) -> serializers.CharField:
    return serializers.CharField(
        max_length=max_length,
        required=requerido,
        allow_null=nulo and not requerido,
        allow_blank=False,
        trim_whitespace=False,
    )


def _html(max_length: int = 100_000) -> serializers.CharField:
    return serializers.CharField(
        max_length=max_length,
        required=False,
        allow_null=True,
        allow_blank=False,
        trim_whitespace=False,
    )


def _id_lista(maximo: int) -> serializers.ListField:
    return serializers.ListField(
        child=IdSerializerField(), max_length=maximo, required=False, default=list
    )


# ---------------------------------------------------------------------------
# Comunes (ContenidoComunCampos / entrada)
# ---------------------------------------------------------------------------
class RelacionEntradaSerializer(EntradaEstricta):
    tipo = _tipo_field([T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO, T.COLECCION])
    id = IdSerializerField()


class FuenteEntradaSerializer(EntradaEstricta):
    titulo = serializers.CharField(min_length=1, max_length=200)
    entidad_editora = _texto(150)
    url = serializers.CharField(max_length=500, required=False, allow_null=True)
    fecha_consulta = serializers.DateField(required=False, allow_null=True)


class ComunesMixin(serializers.Serializer[Any]):
    titulo = serializers.CharField(min_length=1, max_length=150)
    slug = serializers.RegexField(PATRON_SLUG, max_length=120, required=False, allow_null=True)
    fecha_ultima_revision = serializers.DateField(required=False, allow_null=True)
    seo_titulo = _texto(70)
    seo_descripcion = _texto(160)
    relaciones = RelacionEntradaSerializer(  # type: ignore[call-arg]
        many=True, required=False, max_length=12, default=list
    )
    terminos_ids = _id_lista(50)
    fuentes = FuenteEntradaSerializer(  # type: ignore[call-arg]
        many=True, required=False, max_length=30, default=list
    )

    def validate_relaciones(self, valor: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ids = [r["id"] for r in valor]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("No puede haber relaciones repetidas.")
        return valor


class VersionMixin(serializers.Serializer[Any]):
    version = serializers.IntegerField(min_value=1)


class IdOpcionalMixin(serializers.Serializer[Any]):
    id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Destino
# ---------------------------------------------------------------------------
class DestinoCamposMixin(serializers.Serializer[Any]):
    pais_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    resumen = _texto(300)
    descripcion_experta = _html()
    tipos_ids = _id_lista(12)
    tipo_principal_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    dificultad = serializers.IntegerField(min_value=1, max_value=5, required=False, allow_null=True)
    meses_mejor_epoca = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=12),
        max_length=12,
        required=False,
        default=list,
    )
    duracion_min_dias = serializers.IntegerField(
        min_value=1, max_value=90, required=False, allow_null=True
    )
    duracion_max_dias = serializers.IntegerField(
        min_value=1, max_value=90, required=False, allow_null=True
    )
    nivel_presupuesto = serializers.IntegerField(
        min_value=1, max_value=4, required=False, allow_null=True
    )
    clima = _html(5000)
    altitud_max_m = serializers.IntegerField(
        min_value=-500, max_value=9000, required=False, allow_null=True
    )
    como_llegar = _html()
    seguridad_riesgos = _html()
    sostenibilidad = _html()
    latitud = serializers.FloatField(min_value=-90, max_value=90, required=False, allow_null=True)
    longitud = serializers.FloatField(
        min_value=-180, max_value=180, required=False, allow_null=True
    )
    portada_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    galeria_ids = _id_lista(30)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        tipos = attrs.get("tipos_ids") or []
        if len(tipos) != len(set(tipos)):
            raise serializers.ValidationError({"tipos_ids": ["No puede haber tipos repetidos."]})
        principal = attrs.get("tipo_principal_id")
        if principal is not None and tipos and principal not in tipos:
            raise serializers.ValidationError(
                {"tipo_principal_id": ["Debe pertenecer a tipos_ids."]}
            )
        return attrs


class TipoVersionadoEntradaSerializer(EntradaEstricta):
    """TipoVersionado de entrada: id + version (bloqueo optimista, ALT-016). Se define una sola
    vez a nivel de módulo y se reutiliza (nunca anidada) para que drf-spectacular no registre dos
    componentes distintos con el mismo nombre inferido (W001)."""

    id = IdSerializerField()
    version = serializers.IntegerField(min_value=1)


class EntidadRefEntradaSerializer(EntradaEstricta):
    """EntidadRef de entrada: tipo + id (CHG-API-005). Ídem: definida una sola vez."""

    tipo = _tipo_entidad_field()
    id = IdSerializerField()


class OperacionPublicadaMixin(serializers.Serializer[Any]):
    """Solo el destino usa estos campos de control (CamposOperacionPublicada, CHG-API-005)."""

    copublicar_tipos = TipoVersionadoEntradaSerializer(  # type: ignore[call-arg]
        many=True, required=False, max_length=12, default=list
    )
    confirmar_cascada = serializers.BooleanField(required=False, default=False)
    cascada_confirmada = EntidadRefEntradaSerializer(  # type: ignore[call-arg]
        many=True, required=False, max_length=12
    )


class DestinoEntradaSerializer(EntradaEstricta, ComunesMixin, DestinoCamposMixin):
    pass


class DestinoActualizacionSerializer(
    EntradaEstricta, ComunesMixin, DestinoCamposMixin, OperacionPublicadaMixin, VersionMixin
):
    pass


class DestinoVistaPreviaSerializer(
    EntradaEstricta, ComunesMixin, DestinoCamposMixin, IdOpcionalMixin
):
    pass


# ---------------------------------------------------------------------------
# Itinerario
# ---------------------------------------------------------------------------
class DiaEntradaSerializer(EntradaEstricta):
    numero_dia = serializers.IntegerField(min_value=1, max_value=60)
    titulo = serializers.CharField(min_length=1, max_length=150)
    actividades = serializers.CharField(max_length=50_000, trim_whitespace=False)
    distancia_km = serializers.FloatField(
        min_value=0, max_value=99_999.9, required=False, allow_null=True
    )
    desnivel_positivo_m = serializers.IntegerField(
        min_value=0, max_value=20_000, required=False, allow_null=True
    )
    desnivel_negativo_m = serializers.IntegerField(
        min_value=0, max_value=20_000, required=False, allow_null=True
    )
    alojamiento_orientativo = _texto(300)
    consejos = serializers.CharField(
        max_length=50_000, required=False, allow_null=True, trim_whitespace=False
    )

    def validate_actividades(self, valor: str) -> str:
        from apps.contenido.saneado import sanear_html

        return sanear_html(valor) or ""

    def validate_consejos(self, valor: str | None) -> str | None:
        from apps.contenido.saneado import sanear_html

        return sanear_html(valor)


class ItinerarioCamposMixin(serializers.Serializer[Any]):
    destino_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    resumen = _texto(300)
    duracion_dias = serializers.IntegerField(
        min_value=1, max_value=60, required=False, allow_null=True
    )
    dificultad = serializers.IntegerField(min_value=1, max_value=5, required=False, allow_null=True)
    tipos_ids = _id_lista(12)
    distancia_total_km = serializers.FloatField(
        min_value=0, max_value=99_999.9, required=False, allow_null=True
    )
    desnivel_acumulado_m = serializers.IntegerField(
        min_value=0, max_value=1_000_000, required=False, allow_null=True
    )
    riesgos_seguridad = _html()
    portada_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    galeria_ids = _id_lista(30)
    dias = DiaEntradaSerializer(  # type: ignore[call-arg]
        many=True, required=False, max_length=60, default=list
    )

    def validate_dias(self, valor: list[dict[str, Any]]) -> list[dict[str, Any]]:
        numeros = [d["numero_dia"] for d in valor]
        if len(numeros) != len(set(numeros)):
            raise serializers.ValidationError("El número de día no puede repetirse.")
        return valor


class ItinerarioEntradaSerializer(EntradaEstricta, ComunesMixin, ItinerarioCamposMixin):
    pass


class ItinerarioActualizacionSerializer(
    EntradaEstricta, ComunesMixin, ItinerarioCamposMixin, VersionMixin
):
    pass


class ItinerarioVistaPreviaSerializer(
    EntradaEstricta, ComunesMixin, ItinerarioCamposMixin, IdOpcionalMixin
):
    pass


# ---------------------------------------------------------------------------
# Guía
# ---------------------------------------------------------------------------
class GuiaCamposMixin(serializers.Serializer[Any]):
    categoria_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    resumen = _texto(300)
    cuerpo = _html()
    destinos_ids = _id_lista(20)
    tipos_ids = _id_lista(12)
    remite_a_metodologia = serializers.BooleanField(required=False, default=False)
    portada_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class GuiaEntradaSerializer(EntradaEstricta, ComunesMixin, GuiaCamposMixin):
    pass


class GuiaActualizacionSerializer(EntradaEstricta, ComunesMixin, GuiaCamposMixin, VersionMixin):
    pass


class GuiaVistaPreviaSerializer(EntradaEstricta, ComunesMixin, GuiaCamposMixin, IdOpcionalMixin):
    pass


# ---------------------------------------------------------------------------
# Tipo de aventura
# ---------------------------------------------------------------------------
class ChecklistEntradaSerializer(EntradaEstricta):
    texto = serializers.CharField(min_length=1, max_length=200)
    grupo = _texto(60)
    esencial = serializers.BooleanField()
    orden = serializers.IntegerField(min_value=0, max_value=1000)


class TipoAventuraCamposMixin(serializers.Serializer[Any]):
    resumen = _texto(300)
    descripcion = _html()
    nivel_exigencia = serializers.IntegerField(
        min_value=1, max_value=5, required=False, allow_null=True
    )
    portada_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    orden = serializers.IntegerField(min_value=0, max_value=1000, required=False, default=0)
    checklist = ChecklistEntradaSerializer(  # type: ignore[call-arg]
        many=True, required=False, max_length=100, default=list
    )

    def validate_checklist(self, valor: list[dict[str, Any]]) -> list[dict[str, Any]]:
        textos = [c["texto"] for c in valor]
        if len(textos) != len(set(textos)):
            raise serializers.ValidationError(
                "El texto de la lista de comprobación no puede repetirse."
            )
        return valor


class TipoAventuraEntradaSerializer(EntradaEstricta, ComunesMixin, TipoAventuraCamposMixin):
    pass


class TipoAventuraActualizacionSerializer(
    EntradaEstricta, ComunesMixin, TipoAventuraCamposMixin, VersionMixin
):
    pass


class TipoAventuraVistaPreviaSerializer(
    EntradaEstricta, ComunesMixin, TipoAventuraCamposMixin, IdOpcionalMixin
):
    pass


# ---------------------------------------------------------------------------
# Colección
# ---------------------------------------------------------------------------
class ElementoColeccionEntradaSerializer(EntradaEstricta):
    tipo_contenido = _tipo_field([T.DESTINO, T.ITINERARIO])
    contenido_id = IdSerializerField()
    orden = serializers.IntegerField(min_value=0, max_value=1000)
    nota_editorial = _texto(300)


class ColeccionCamposMixin(serializers.Serializer[Any]):
    resumen = _texto(300)
    descripcion = _html()
    portada_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    elementos = ElementoColeccionEntradaSerializer(  # type: ignore[call-arg]
        many=True, required=False, max_length=100, default=list
    )

    def validate_elementos(self, valor: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pares = [(e["tipo_contenido"], e["contenido_id"]) for e in valor]
        if len(pares) != len(set(pares)):
            raise serializers.ValidationError("Un elemento no puede repetirse en la colección.")
        return valor


class ColeccionEntradaSerializer(EntradaEstricta, ComunesMixin, ColeccionCamposMixin):
    pass


class ColeccionActualizacionSerializer(
    EntradaEstricta, ComunesMixin, ColeccionCamposMixin, VersionMixin
):
    pass


class ColeccionVistaPreviaSerializer(
    EntradaEstricta, ComunesMixin, ColeccionCamposMixin, IdOpcionalMixin
):
    pass


# ---------------------------------------------------------------------------
# Término de glosario
# ---------------------------------------------------------------------------
class TerminoGlosarioCamposMixin(serializers.Serializer[Any]):
    titulo = serializers.CharField(min_length=1, max_length=150)
    slug = serializers.RegexField(PATRON_SLUG, max_length=120, required=False, allow_null=True)
    definicion = _texto(600)
    fecha_ultima_revision = serializers.DateField(required=False, allow_null=True)


class TerminoGlosarioEntradaSerializer(EntradaEstricta, TerminoGlosarioCamposMixin):
    pass


class TerminoGlosarioActualizacionSerializer(
    EntradaEstricta, TerminoGlosarioCamposMixin, VersionMixin
):
    pass


# ---------------------------------------------------------------------------
# Página institucional
# ---------------------------------------------------------------------------
class PaginaInstitucionalCamposMixin(serializers.Serializer[Any]):
    titulo = serializers.CharField(min_length=1, max_length=150)
    cuerpo = serializers.CharField(max_length=100_000, trim_whitespace=False)
    version_documento = serializers.CharField(min_length=1, max_length=20)
    vigente_desde = serializers.DateField()
    fecha_ultima_revision = serializers.DateField(required=False, allow_null=True)
    seo_titulo = _texto(70)
    seo_descripcion = _texto(160)


class PaginaInstitucionalActualizacionSerializer(
    EntradaEstricta, PaginaInstitucionalCamposMixin, VersionMixin
):
    pass


class PaginaInstitucionalVistaPreviaSerializer(
    EntradaEstricta, PaginaInstitucionalCamposMixin, IdOpcionalMixin
):
    titulo = serializers.CharField(min_length=1, max_length=150, required=False)
    cuerpo = serializers.CharField(max_length=100_000, required=False, trim_whitespace=False)
    version_documento = serializers.CharField(min_length=1, max_length=20, required=False)
    vigente_desde = serializers.DateField(required=False)


# ---------------------------------------------------------------------------
# Ciclo editorial (común a todos los tipos)
# ---------------------------------------------------------------------------
class TransicionEntradaSerializer(EntradaEstricta):
    version = serializers.IntegerField(min_value=1)


class PublicacionEntradaSerializer(EntradaEstricta):
    version = serializers.IntegerField(min_value=1)
    copublicar_tipos = TipoVersionadoEntradaSerializer(  # type: ignore[call-arg]
        many=True, required=False, max_length=12, default=list
    )


class RetiroEntradaSerializer(EntradaEstricta):
    version = serializers.IntegerField(min_value=1)
    motivo = serializers.CharField(min_length=1, max_length=300, trim_whitespace=False)
    confirmar_cascada = serializers.BooleanField(required=False, default=False)
    cascada_confirmada = EntidadRefEntradaSerializer(  # type: ignore[call-arg]
        many=True, required=False, max_length=212
    )


class AnalisisPublicacionEntradaSerializer(EntradaEstricta):
    version = serializers.IntegerField(min_value=1)
    tipos_ids = _id_lista(12)
    tipo_principal_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Salidas (referencias y metadatos comunes)
# ---------------------------------------------------------------------------
class ActorRefSerializer(serializers.Serializer[Any]):
    """components.schemas.ActorRef. `ref_name` propio: evita colisionar en el esquema generado
    con los `ActorRefSerializer` de otros dominios (apps.auditoria, apps.medios, apps.inicio),
    cada uno definido en su propia capa API por Skill_Backend §5 (sin importar entre dominios)."""

    id = serializers.IntegerField(allow_null=True)
    etiqueta = serializers.CharField(max_length=60)

    class Meta:
        ref_name = "ActorRefContenido"


class ContenidoRefPanelSerializer(serializers.Serializer[Any]):
    tipo = serializers.CharField()
    id = IdSerializerField()
    titulo = serializers.CharField(max_length=150)
    slug = serializers.CharField(max_length=120, allow_null=True, required=False)
    estado_editorial = serializers.CharField()


class ErrorReglaSerializer(serializers.Serializer[Any]):
    campo = serializers.CharField(max_length=100)
    code = serializers.RegexField(r"^[a-z][a-z0-9_]{2,63}$")
    mensaje = serializers.CharField(max_length=300)
    referencias = ContenidoRefPanelSerializer(many=True, required=False)


class RequisitosPublicacionSerializer(serializers.Serializer[Any]):
    cumple = serializers.BooleanField()
    pendientes = ErrorReglaSerializer(many=True)


class EntidadTransitadaSerializer(ContenidoRefPanelSerializer):
    version = serializers.IntegerField(min_value=1)
    numero_revision = serializers.IntegerField(min_value=1, allow_null=True)
    url_publica = serializers.CharField(allow_null=True, required=False)
    origen = serializers.ChoiceField(choices=["PRINCIPAL", "COPUBLICACION", "CASCADA"])


class ResultadoTransicionSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    tipo = serializers.CharField()
    estado_editorial = serializers.CharField()
    version = serializers.IntegerField(min_value=1)
    numero_revision = serializers.IntegerField(min_value=1, allow_null=True)
    url_publica = serializers.CharField(allow_null=True, required=False)
    afectados = ContenidoRefPanelSerializer(many=True)
    entidades = EntidadTransitadaSerializer(many=True)


class BloqueoCascadaSerializer(serializers.Serializer[Any]):
    tipo_aventura = ContenidoRefPanelSerializer()
    itinerarios = ContenidoRefPanelSerializer(many=True)
    total_itinerarios = serializers.IntegerField(min_value=1)


class ImpactoRetiroSerializer(serializers.Serializer[Any]):
    retirable = serializers.BooleanField()
    itinerarios_en_cascada = ContenidoRefPanelSerializer(many=True)
    tipos_en_cascada = ContenidoRefPanelSerializer(many=True)
    bloqueos_cascada = BloqueoCascadaSerializer(many=True)
    colecciones = ContenidoRefPanelSerializer(many=True)
    destacados = serializers.ListField(child=serializers.CharField())
    enlaces_entrantes = serializers.IntegerField(min_value=0)
    bloqueos = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class ValidacionEntidadSerializer(serializers.Serializer[Any]):
    tipo = serializers.CharField()
    id = IdSerializerField()
    titulo = serializers.CharField(max_length=150)
    slug = serializers.CharField(max_length=120, allow_null=True, required=False)
    estado_editorial = serializers.CharField()
    version = serializers.IntegerField(min_value=1)
    rol = serializers.ChoiceField(choices=["PRINCIPAL", "COPUBLICACION", "CASCADA"])
    cumple = serializers.BooleanField()
    pendientes = ErrorReglaSerializer(many=True)


class TipoVersionadoSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    version = serializers.IntegerField(min_value=1)


class AnalisisPublicacionSerializer(serializers.Serializer[Any]):
    operacion = serializers.ChoiceField(choices=["PUBLICAR", "ACTUALIZAR_PUBLICACION"])
    confirmable = serializers.BooleanField()
    entidad = ValidacionEntidadSerializer()
    copublicacion = ValidacionEntidadSerializer(many=True)
    copublicar_tipos = TipoVersionadoSerializer(many=True)
    tipos_en_cascada = ContenidoRefPanelSerializer(many=True)
    bloqueos_cascada = BloqueoCascadaSerializer(many=True)


class RevisionResumenSerializer(serializers.Serializer[Any]):
    numero_revision = serializers.IntegerField(min_value=1)
    motivo = serializers.CharField()
    creado_en = serializers.DateTimeField()
    creado_por = ActorRefSerializer()


class RevisionDetalleSerializer(RevisionResumenSerializer):
    instantanea = serializers.DictField()


class RestauracionRevisionSerializer(serializers.Serializer[Any]):
    numero_revision = serializers.IntegerField(min_value=1)
    version_actual = serializers.IntegerField(min_value=1)
    datos = serializers.DictField()


class PaginaRevisionResumenSerializer(PaginaMetaSerializer):
    resultados = RevisionResumenSerializer(many=True)


# ---------------------------------------------------------------------------
# Salidas Panel por tipo (ContenidoPanelMeta + ContenidoComunCampos + {Tipo}Campos)
# ---------------------------------------------------------------------------
class ReferenciasPanelSerializer(serializers.Serializer[Any]):
    medios = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    contenidos = ContenidoRefPanelSerializer(many=True, required=False)
    terminos = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    taxonomias = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class ContenidoPanelMetaSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    tipo = serializers.CharField()
    estado_editorial = serializers.CharField()
    version = serializers.IntegerField(min_value=1)
    slug_bloqueado = serializers.BooleanField()
    primera_publicacion_en = serializers.DateTimeField(allow_null=True)
    publicado_actualizado_en = serializers.DateTimeField(allow_null=True)
    retirado_en = serializers.DateTimeField(allow_null=True)
    motivo_retiro = serializers.CharField(allow_null=True, max_length=300)
    creado_en = serializers.DateTimeField()
    actualizado_en = serializers.DateTimeField()
    creado_por = ActorRefSerializer()
    actualizado_por = ActorRefSerializer()
    url_publica = serializers.CharField(allow_null=True, required=False)
    requisitos_publicacion = RequisitosPublicacionSerializer()
    referencias = ReferenciasPanelSerializer()

    def to_representation(self, instance: Any) -> dict[str, Any]:
        from apps.contenido import services

        contenido = instance
        return {
            "id": contenido.pk,
            "tipo": contenido.tipo,
            "estado_editorial": contenido.estado_editorial,
            "version": contenido.version,
            "slug_bloqueado": contenido.primera_publicacion_en is not None,
            "primera_publicacion_en": contenido.primera_publicacion_en,
            "publicado_actualizado_en": contenido.publicado_actualizado_en,
            "retirado_en": contenido.retirado_en,
            "motivo_retiro": contenido.motivo_retiro,
            "creado_en": contenido.creado_en,
            "actualizado_en": contenido.actualizado_en,
            "creado_por": {
                "id": contenido.creado_por_id,
                "etiqueta": f"#{contenido.creado_por_id}" if contenido.creado_por_id else "sistema",
            },
            "actualizado_por": {
                "id": contenido.actualizado_por_id,
                "etiqueta": f"#{contenido.actualizado_por_id}"
                if contenido.actualizado_por_id
                else "sistema",
            },
            "url_publica": services._url_publica(contenido),
            "requisitos_publicacion": _requisitos_publicacion(contenido),
            "referencias": {"medios": [], "contenidos": [], "terminos": [], "taxonomias": []},
        }


def _requisitos_publicacion(contenido: Any) -> dict[str, Any]:
    from apps.contenido import services

    if contenido.tipo == T.PAGINA or contenido.estado_editorial == "RETIRADO":
        return {"cumple": True, "pendientes": []}
    subtipo = services.subtipo_de(contenido)
    errores = services._validar_entidad_para_publicar(
        contenido.tipo,
        contenido,
        subtipo,
        exigir_destino_publicado=(contenido.estado_editorial == "PUBLICADO"),
    )
    return {"cumple": not errores, "pendientes": errores}


def _comunes_representacion(contenido: Any) -> dict[str, Any]:
    return {
        "titulo": contenido.titulo,
        "slug": contenido.slug,
        "fecha_ultima_revision": contenido.fecha_ultima_revision,
        "seo_titulo": contenido.seo_titulo,
        "seo_descripcion": contenido.seo_descripcion,
        "relaciones": [
            {"tipo": r.relacionado_tipo, "id": r.relacionado_id}
            for r in contenido.relacionados.order_by("orden", "id")
        ],
        "terminos_ids": list(contenido.terminos.values_list("termino_id", flat=True)),
        "fuentes": [
            {
                "titulo": f.titulo,
                "entidad_editora": f.entidad_editora,
                "url": f.url,
                "fecha_consulta": f.fecha_consulta,
            }
            for f in contenido.fuentes.order_by("orden", "id")
        ],
    }


class DestinoPanelSerializer(ContenidoPanelMetaSerializer):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        destino = instance.destino
        base.update(_comunes_representacion(instance))
        base.update(
            {
                "pais_id": destino.pais_id,
                "resumen": destino.resumen,
                "descripcion_experta": destino.descripcion_experta,
                "tipos_ids": list(destino.tipos_aventura.values_list("id", flat=True)),
                "tipo_principal_id": destino.tipo_principal_id,
                "dificultad": destino.dificultad,
                "meses_mejor_epoca": list(destino.meses_mejor_epoca or []),
                "duracion_min_dias": destino.duracion_min_dias,
                "duracion_max_dias": destino.duracion_max_dias,
                "nivel_presupuesto": destino.nivel_presupuesto,
                "clima": destino.clima,
                "altitud_max_m": destino.altitud_max_m,
                "como_llegar": destino.como_llegar,
                "seguridad_riesgos": destino.seguridad_riesgos,
                "sostenibilidad": destino.sostenibilidad,
                "latitud": float(destino.latitud) if destino.latitud is not None else None,
                "longitud": float(destino.longitud) if destino.longitud is not None else None,
                "portada_id": instance.portada_id,
                "galeria_ids": list(
                    instance.galeria.order_by("orden").values_list("medio_id", flat=True)
                ),
            }
        )
        return base


class DestinoGuardadoSerializer(DestinoPanelSerializer):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        contenido, entidades_afectadas = instance
        base = super().to_representation(contenido)
        base["entidades_afectadas"] = entidades_afectadas
        return base


class ItinerarioPanelSerializer(ContenidoPanelMetaSerializer):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        itinerario = instance.itinerario
        base.update(_comunes_representacion(instance))
        base.update(
            {
                "destino_id": itinerario.destino_id,
                "resumen": itinerario.resumen,
                "duracion_dias": itinerario.duracion_dias,
                "dificultad": itinerario.dificultad,
                "tipos_ids": list(itinerario.tipos_aventura.values_list("id", flat=True)),
                "distancia_total_km": float(itinerario.distancia_total_km)
                if itinerario.distancia_total_km is not None
                else None,
                "desnivel_acumulado_m": itinerario.desnivel_acumulado_m,
                "riesgos_seguridad": itinerario.riesgos_seguridad,
                "portada_id": instance.portada_id,
                "galeria_ids": list(
                    instance.galeria.order_by("orden").values_list("medio_id", flat=True)
                ),
                "dias": [
                    {
                        "numero_dia": d.numero_dia,
                        "titulo": d.titulo,
                        "actividades": d.actividades,
                        "distancia_km": float(d.distancia_km)
                        if d.distancia_km is not None
                        else None,
                        "desnivel_positivo_m": d.desnivel_positivo_m,
                        "desnivel_negativo_m": d.desnivel_negativo_m,
                        "alojamiento_orientativo": d.alojamiento_orientativo,
                        "consejos": d.consejos,
                    }
                    for d in itinerario.dias.order_by("numero_dia")
                ],
            }
        )
        return base


class GuiaPanelSerializer(ContenidoPanelMetaSerializer):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        guia = instance.guia
        base.update(_comunes_representacion(instance))
        base.update(
            {
                "categoria_id": guia.categoria_id,
                "resumen": guia.resumen,
                "cuerpo": guia.cuerpo,
                "destinos_ids": list(guia.destinos.values_list("contenido_id", flat=True)),
                "tipos_ids": list(guia.tipos_aventura.values_list("id", flat=True)),
                "remite_a_metodologia": guia.remite_a_metodologia,
                "portada_id": instance.portada_id,
                "palabras": guia.palabras,
            }
        )
        return base


class TipoAventuraPanelSerializer(ContenidoPanelMetaSerializer):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        tipo = instance.tipo_aventura
        base.update(_comunes_representacion(instance))
        base.update(
            {
                "resumen": tipo.resumen,
                "descripcion": tipo.descripcion,
                "nivel_exigencia": tipo.nivel_exigencia,
                "portada_id": instance.portada_id,
                "orden": tipo.orden,
                "checklist": [
                    {"texto": c.texto, "grupo": c.grupo, "esencial": c.esencial, "orden": c.orden}
                    for c in tipo.checklist.order_by("orden", "id")
                ],
            }
        )
        return base


class ColeccionPanelSerializer(ContenidoPanelMetaSerializer):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        coleccion = instance.coleccion
        base.update(_comunes_representacion(instance))
        base.update(
            {
                "resumen": coleccion.resumen,
                "descripcion": coleccion.descripcion,
                "portada_id": instance.portada_id,
                "elementos": [
                    {
                        "tipo_contenido": e.tipo_contenido,
                        "contenido_id": e.contenido_id,
                        "orden": e.orden,
                        "nota_editorial": e.nota_editorial,
                    }
                    for e in coleccion.elementos.order_by("orden", "id")
                ],
            }
        )
        return base


class TerminoGlosarioPanelSerializer(ContenidoPanelMetaSerializer):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        termino = instance.termino_glosario
        base.update(
            {
                "titulo": instance.titulo,
                "slug": instance.slug,
                "definicion": termino.definicion,
                "fecha_ultima_revision": instance.fecha_ultima_revision,
                "vinculado_en": [
                    {
                        "tipo": u.contenido.tipo,
                        "id": u.contenido_id,
                        "titulo": u.contenido.titulo,
                        "estado_editorial": u.contenido.estado_editorial,
                    }
                    for u in termino.usos.select_related("contenido")
                ],
            }
        )
        return base


class PaginaInstitucionalPanelSerializer(ContenidoPanelMetaSerializer):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        pagina = instance.pagina
        base.update(
            {
                "titulo": instance.titulo,
                "cuerpo": pagina.cuerpo,
                "version_documento": pagina.version_documento,
                "vigente_desde": pagina.vigente_desde,
                "fecha_ultima_revision": instance.fecha_ultima_revision,
                "seo_titulo": instance.seo_titulo,
                "seo_descripcion": instance.seo_descripcion,
                "clave": pagina.clave,
                "solo_administrador": pagina.clave != ClavePagina.ACERCA_DE,
            }
        )
        return base


class ContenidoResumenPanelSerializer(serializers.Serializer[Any]):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        from apps.contenido import services

        contenido = instance
        return {
            "id": contenido.pk,
            "tipo": contenido.tipo,
            "titulo": contenido.titulo,
            "slug": contenido.slug,
            "estado_editorial": contenido.estado_editorial,
            "version": contenido.version,
            "fecha_ultima_revision": contenido.fecha_ultima_revision,
            "actualizado_en": contenido.actualizado_en,
            "actualizado_por": {
                "id": contenido.actualizado_por_id,
                "etiqueta": f"#{contenido.actualizado_por_id}"
                if contenido.actualizado_por_id
                else "sistema",
            },
            "publicado": contenido.estado_editorial == "PUBLICADO",
            "url_publica": services._url_publica(contenido),
        }


class PaginaContenidoResumenSerializer(PaginaMetaSerializer):
    resultados = ContenidoResumenPanelSerializer(many=True)


PANEL_SERIALIZER: dict[str, type[serializers.Serializer[Any]]] = {
    T.DESTINO: DestinoPanelSerializer,
    T.ITINERARIO: ItinerarioPanelSerializer,
    T.GUIA: GuiaPanelSerializer,
    T.TIPO: TipoAventuraPanelSerializer,
    T.COLECCION: ColeccionPanelSerializer,
    T.TERMINO: TerminoGlosarioPanelSerializer,
    T.PAGINA: PaginaInstitucionalPanelSerializer,
}
ENTRADA_SERIALIZER: dict[str, type[serializers.Serializer[Any]]] = {
    T.DESTINO: DestinoEntradaSerializer,
    T.ITINERARIO: ItinerarioEntradaSerializer,
    T.GUIA: GuiaEntradaSerializer,
    T.TIPO: TipoAventuraEntradaSerializer,
    T.COLECCION: ColeccionEntradaSerializer,
    T.TERMINO: TerminoGlosarioEntradaSerializer,
}
ACTUALIZACION_SERIALIZER: dict[str, type[serializers.Serializer[Any]]] = {
    T.DESTINO: DestinoActualizacionSerializer,
    T.ITINERARIO: ItinerarioActualizacionSerializer,
    T.GUIA: GuiaActualizacionSerializer,
    T.TIPO: TipoAventuraActualizacionSerializer,
    T.COLECCION: ColeccionActualizacionSerializer,
    T.TERMINO: TerminoGlosarioActualizacionSerializer,
    T.PAGINA: PaginaInstitucionalActualizacionSerializer,
}
VISTA_PREVIA_SERIALIZER: dict[str, type[serializers.Serializer[Any]]] = {
    T.DESTINO: DestinoVistaPreviaSerializer,
    T.ITINERARIO: ItinerarioVistaPreviaSerializer,
    T.GUIA: GuiaVistaPreviaSerializer,
    T.TIPO: TipoAventuraVistaPreviaSerializer,
    T.COLECCION: ColeccionVistaPreviaSerializer,
    T.PAGINA: PaginaInstitucionalVistaPreviaSerializer,
}
