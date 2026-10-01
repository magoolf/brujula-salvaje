"""Serializers de inicio, configuración del sitio y tablero (contracts/openapi.yaml, tags
panel-configuracion y panel-tablero). Solo forma y validación (Skill_Backend Regla 02)."""

from __future__ import annotations

import copy
from typing import Any

from django.core.validators import MaxLengthValidator
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.contenido.models import TipoContenido
from apps.core.api.serializers import EntradaEstricta, IdSerializerField
from apps.core.esquema import id_contrato, lista_ids, texto_sin_nul


def _con_limite(campo: Any, *, max_length: int | None = None) -> Any:
    """Ídem `apps.contenido.api.panel_serializers._con_limite` (duplicada a propósito,
    Skill_Backend §5; ver ahí el porqué completo, RONDA 5): reconstruye el `ListSerializer` con
    `validators=` como kwarg del constructor -- mutar `campo.validators` después de construir el
    campo no sobrevive al `copy.deepcopy(self._declared_fields)` que DRF hace en cada
    instanciación del serializer padre. Solo `max_length` aquí: ninguno de los campos de este
    archivo necesitó `minItems`."""
    if max_length is None:
        return campo
    validadores = [*(campo._kwargs.get("validators") or []), MaxLengthValidator(max_length)]
    kwargs = dict(campo._kwargs)
    kwargs["child"] = copy.deepcopy(kwargs["child"])
    kwargs["validators"] = validadores
    return campo.__class__(*campo._args, **kwargs)


@extend_schema_field({"type": "string", "enum": list(TipoContenido.values)})
class _CampoTipoEntidadConEnum(serializers.ChoiceField):
    """`ChoiceField` de `tipo` (TipoEntidadContenido) con el enum inline (TKT-006, ciclo oasdiff:
    enum removed in revision); ver la misma clase en `apps.contenido.api.panel_serializers`
    (duplicada a propósito, Skill_Backend §5)."""


def _tipo_entidad_field() -> serializers.ChoiceField:
    return _CampoTipoEntidadConEnum(choices=TipoContenido.choices)


@extend_schema_field({"type": "string", "enum": ["BORRADOR", "PUBLICADO", "RETIRADO"]})
class _CampoEstadoEditorial(serializers.ChoiceField):
    """`ChoiceField` de `estado_editorial` (EstadoEditorial) con el enum inline."""


def _campo_estado_editorial(**kwargs: Any) -> serializers.ChoiceField:
    return _CampoEstadoEditorial(choices=["BORRADOR", "PUBLICADO", "RETIRADO"], **kwargs)


def _id_lista(minimo: int, maximo: int) -> serializers.ListField:
    """`ConfigInicioCampos.*_ids` del contrato: `minItems`/`maxItems`, `uniqueItems: true`
    (validado: una lista con ids repetidos es un 400) e ítems `Id` sin `maximum` (TKT-012)."""
    return lista_ids(maximo, min_length=minimo, required=True)


class ConfigInicioCamposMixin(serializers.Serializer[Any]):
    """components.schemas.ConfigInicioCampos: lo comparten entrada y salida (TKT-012), para que
    el componente que `apps.core.esquema` reparte en `allOf` lleve las mismas restricciones."""

    hero_titular = texto_sin_nul(min_length=1, max_length=80)
    hero_subtitulo = texto_sin_nul(min_length=1, max_length=160)
    hero_medio_id = id_contrato()
    destinos_ids = _id_lista(6, 12)
    itinerarios_ids = _id_lista(3, 6)
    guias_ids = _id_lista(3, 6)


class ConfigInicioEntradaSerializer(EntradaEstricta, ConfigInicioCamposMixin):
    pass


@extend_schema_field({"type": ["integer", "null"], "format": "int64"})
class _CampoIdNuloInt64(serializers.IntegerField):
    """components.schemas.ActorRef.id: entero int64 nullable ("sistema" cuando es null); ver
    `apps.contenido.api.panel_serializers` (duplicada a propósito, Skill_Backend §5)."""


class ActorRefSerializer(serializers.Serializer[Any]):
    """components.schemas.ActorRef con `ref_name` propio (evita colisión entre dominios,
    Skill_Backend §5: cada capa API define sus propios serializers de salida)."""

    id = _CampoIdNuloInt64(allow_null=True)
    etiqueta = serializers.CharField(max_length=60)

    class Meta:
        ref_name = "ActorRefInicio"


@extend_schema_field({"type": "string", "format": "uri-reference"})
class _CampoUriReferencia(serializers.CharField):
    """components.schemas.MedioMiniatura.url_miniatura: uri-reference (ruta relativa); ver la
    misma clase en `apps.contenido.api.panel_serializers` (duplicada a propósito, §5)."""


class MedioMiniaturaSerializer(serializers.Serializer[Any]):
    """components.schemas.MedioMiniatura (`ConfigInicioPanel.referencias.medios[]`)."""

    id = IdSerializerField()
    estado = serializers.CharField()
    texto_alternativo = serializers.CharField(max_length=250, allow_null=True)
    licencia_codigo = serializers.CharField(max_length=40, allow_null=True)
    url_miniatura = _CampoUriReferencia()


class ContenidoRefPanelSerializer(serializers.Serializer[Any]):
    """components.schemas.ContenidoRefPanel. `ref_name` propio (Skill_Backend §5): cada capa API
    define sus propios serializers de referencia sin importar entre dominios."""

    tipo = _tipo_entidad_field()
    id = IdSerializerField()
    titulo = serializers.CharField(max_length=150)
    slug = serializers.CharField(max_length=120, allow_null=True, required=False)
    estado_editorial = _campo_estado_editorial()

    class Meta:
        ref_name = "ContenidoRefPanelInicio"


class ReferenciasConfigInicioSerializer(serializers.Serializer[Any]):
    """`ConfigInicioPanel.referencias` (esquema en línea del contrato)."""

    medios = _con_limite(MedioMiniaturaSerializer(many=True, required=False), max_length=1)
    contenidos = _con_limite(ContenidoRefPanelSerializer(many=True, required=False), max_length=24)


class ConfigInicioPanelSerializer(ConfigInicioCamposMixin):
    """components.schemas.ConfigInicioPanel. Declara los campos (Skill_Backend Regla 13,
    TKT-006 ciclo oasdiff): un `to_representation` propio sin campos declarados no genera
    ninguna propiedad en el esquema drf-spectacular."""

    actualizado_en = serializers.DateTimeField()
    actualizado_por = ActorRefSerializer()
    referencias = ReferenciasConfigInicioSerializer()

    def to_representation(self, instance: Any) -> dict[str, Any]:
        from apps.inicio import selectors

        config = instance
        return {
            "hero_titular": config.hero_titular,
            "hero_subtitulo": config.hero_subtitulo,
            "hero_medio_id": config.hero_medio_id,
            "destinos_ids": selectors.ids_destacados("DESTINOS"),
            "itinerarios_ids": selectors.ids_destacados("ITINERARIOS"),
            "guias_ids": selectors.ids_destacados("GUIAS"),
            "actualizado_en": config.actualizado_en,
            "actualizado_por": {
                "id": config.actualizado_por_id,
                "etiqueta": f"#{config.actualizado_por_id}"
                if config.actualizado_por_id
                else "sistema",
            },
            "referencias": {"medios": [], "contenidos": []},
        }


def _texto_opcional(max_length: int) -> serializers.RegexField:
    return texto_sin_nul(max_length=max_length, required=False, allow_null=True)


class ConfiguracionSitioCamposMixin(serializers.Serializer[Any]):
    """components.schemas.ConfiguracionSitioCampos (compartido por entrada y salida, TKT-012)."""

    nombre_marca = texto_sin_nul(min_length=1, max_length=60)
    lema = _texto_opcional(120)
    texto_descargo = texto_sin_nul(min_length=1, max_length=5000, trim_whitespace=False)
    responsable_nombre = _texto_opcional(150)
    responsable_identificacion = _texto_opcional(40)
    responsable_domicilio = _texto_opcional(200)
    responsable_canal_atencion = _texto_opcional(200)


class ConfiguracionSitioEntradaSerializer(EntradaEstricta, ConfiguracionSitioCamposMixin):
    pass


class ConfiguracionSitioSerializer(ConfiguracionSitioCamposMixin):
    actualizado_en = serializers.DateTimeField()


class ContenidoResumenTableroSerializer(serializers.Serializer[Any]):
    """components.schemas.ContenidoResumenPanel (`Tablero.recientes`). Declara los campos
    (Skill_Backend Regla 13, TKT-006 ciclo oasdiff): un `to_representation` propio sin campos
    declarados no genera ninguna propiedad en el esquema drf-spectacular (el componente vacío se
    descarta y `recientes` desaparece del esquema, gate: property present in base, missing in
    revision)."""

    id = IdSerializerField()
    tipo = _tipo_entidad_field()
    titulo = serializers.CharField(max_length=150)
    slug = serializers.CharField(max_length=120, allow_null=True, required=False)
    estado_editorial = _campo_estado_editorial()
    version = serializers.IntegerField(min_value=1)
    fecha_ultima_revision = serializers.DateField(allow_null=True, required=False)
    actualizado_en = serializers.DateTimeField()
    actualizado_por = ActorRefSerializer()
    publicado = serializers.BooleanField()
    url_publica = serializers.RegexField(r"^/[a-z0-9/-]*$", allow_null=True, required=False)

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


class ConteoTipoSerializer(serializers.Serializer[Any]):
    tipo = _tipo_entidad_field()
    borrador = serializers.IntegerField(min_value=0)
    publicado = serializers.IntegerField(min_value=0)
    retirado = serializers.IntegerField(min_value=0)


class AlertaTableroSerializer(serializers.Serializer[Any]):
    code = serializers.ChoiceField(
        choices=["responsable_sin_definir", "destacado_retirado", "coleccion_bajo_minimo"]
    )
    mensaje = serializers.CharField(max_length=300)
    enlace = serializers.RegexField(r"^/panel(/[a-z0-9/-]*)?$", allow_null=True, required=False)


@extend_schema_field(
    {
        # Sin 'null' aquí: `allow_null=True` en el uso (`SaludEditorialSerializer(allow_null=True,
        # ...)` en `TableroSerializer`) hace que `append_meta` lo añada una sola vez a `type`;
        # declararlo también aquí duplicaba la entrada (ver mismo caso en `apps.medios.api`).
        "type": "object",
        "properties": {
            "revisiones_antiguas": {
                "type": "array",
                "maxItems": 50,
                "items": {"$ref": "#/components/schemas/ContenidoRefPanelInicio"},
            },
            "medios_pendientes_metadatos": {"type": "integer", "minimum": 0},
            "medios_sin_uso": {"type": "integer", "minimum": 0},
            "colecciones_bajo_minimo": {
                "type": "array",
                "maxItems": 50,
                "items": {"$ref": "#/components/schemas/ContenidoRefPanelInicio"},
            },
            "destacados_bajo_minimo": {
                "type": "array",
                "maxItems": 3,
                "items": {"type": "string", "enum": ["DESTINOS", "ITINERARIOS", "GUIAS"]},
            },
            "contenidos_con_pocos_relacionados": {
                "type": "array",
                "maxItems": 50,
                "items": {"$ref": "#/components/schemas/ContenidoRefPanelInicio"},
            },
        },
    }
)
class SaludEditorialSerializer(serializers.Serializer[Any]):
    """`Tablero.salud_editorial` (EXP-001, COULD): null mientras no esté implementado.

    `extend_schema_field` con el literal completo del contrato (TKT-006 ciclo oasdiff,
    `response-property-one-of-added`): el contrato declara `salud_editorial` como objeto en
    línea nullable (`type: ['object', 'null']`, sin `oneOf`), pero al usar este serializer como
    campo anidado con `allow_null=True`, `append_meta` (drf-spectacular, OAS 3.1) envuelve
    cualquier `$ref` nullable en `oneOf: [{$ref}, {type: 'null'}]` -- forma válida pero distinta
    a la que el contrato documenta. El override también fija los `maxItems` de sus 4 arrays
    (50/50/3/50, contrato) que de otro modo drf-spectacular no puede derivar de un
    `ListSerializer` (ver `_con_limite`) y que aquí, al escribir el literal a mano, cuestan lo
    mismo declarar bien."""

    revisiones_antiguas = ContenidoRefPanelSerializer(many=True, required=False)
    medios_pendientes_metadatos = serializers.IntegerField(min_value=0, required=False)
    medios_sin_uso = serializers.IntegerField(min_value=0, required=False)
    colecciones_bajo_minimo = ContenidoRefPanelSerializer(many=True, required=False)
    destacados_bajo_minimo = serializers.ListField(
        child=serializers.ChoiceField(choices=["DESTINOS", "ITINERARIOS", "GUIAS"]),
        required=False,
    )
    contenidos_con_pocos_relacionados = ContenidoRefPanelSerializer(many=True, required=False)


class TableroSerializer(serializers.Serializer[Any]):
    conteos = _con_limite(ConteoTipoSerializer(many=True), max_length=7)
    recientes = _con_limite(ContenidoResumenTableroSerializer(many=True), max_length=10)
    alertas = _con_limite(AlertaTableroSerializer(many=True), max_length=20)
    salud_editorial = SaludEditorialSerializer(allow_null=True, required=False)
