"""Serializers de inicio, configuración del sitio y tablero (contracts/openapi.yaml, tags
panel-configuracion y panel-tablero). Solo forma y validación (Skill_Backend Regla 02)."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.contenido.models import TipoContenido
from apps.core.api.serializers import EntradaEstricta, IdSerializerField


@extend_schema_field({"type": "string"})
class _CampoTipo(serializers.ChoiceField):
    """`ChoiceField` con esquema en línea sin clave `enum` nombrada. `extend_schema_field` debe
    aplicarse sobre la CLASE (no sobre la instancia): `Field.__deepcopy__` de DRF reconstruye la
    instancia vía `self.__class__(*args, **kwargs)` al enlazar el serializer y descarta cualquier
    atributo puesto solo sobre la instancia. Evita que drf-spectacular reconcilie un componente de
    enum compartido entre dominios (W001); ver la misma clase en
    `apps.contenido.api.panel_serializers` (duplicada a propósito, Skill_Backend §5)."""


def _tipo_entidad_field() -> serializers.ChoiceField:
    return _CampoTipo(choices=TipoContenido.choices)


def _id_lista(minimo: int, maximo: int) -> serializers.ListField:
    return serializers.ListField(child=IdSerializerField(), min_length=minimo, max_length=maximo)


class ConfigInicioEntradaSerializer(EntradaEstricta):
    hero_titular = serializers.CharField(min_length=1, max_length=80)
    hero_subtitulo = serializers.CharField(min_length=1, max_length=160)
    hero_medio_id = IdSerializerField()
    destinos_ids = _id_lista(6, 12)
    itinerarios_ids = _id_lista(3, 6)
    guias_ids = _id_lista(3, 6)

    def _validar_unicos(self, nombre: str, valor: list[int]) -> list[int]:
        if len(set(valor)) != len(valor):
            raise serializers.ValidationError(f"{nombre}: no puede haber ids repetidos.")
        return valor

    def validate_destinos_ids(self, valor: list[int]) -> list[int]:
        return self._validar_unicos("destinos_ids", valor)

    def validate_itinerarios_ids(self, valor: list[int]) -> list[int]:
        return self._validar_unicos("itinerarios_ids", valor)

    def validate_guias_ids(self, valor: list[int]) -> list[int]:
        return self._validar_unicos("guias_ids", valor)


class ActorRefSerializer(serializers.Serializer[Any]):
    """components.schemas.ActorRef con `ref_name` propio (evita colisión entre dominios,
    Skill_Backend §5: cada capa API define sus propios serializers de salida)."""

    id = serializers.IntegerField(allow_null=True)
    etiqueta = serializers.CharField(max_length=60)

    class Meta:
        ref_name = "ActorRefInicio"


class MedioMiniaturaSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    estado = serializers.CharField()
    texto_alternativo = serializers.CharField(allow_null=True)
    licencia_codigo = serializers.CharField(allow_null=True)
    url_miniatura = serializers.CharField()


class ConfigInicioPanelSerializer(serializers.Serializer[Any]):
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


class ConfiguracionSitioEntradaSerializer(EntradaEstricta):
    nombre_marca = serializers.CharField(min_length=1, max_length=60)
    lema = serializers.CharField(max_length=120, required=False, allow_null=True)
    texto_descargo = serializers.CharField(min_length=1, max_length=5000, trim_whitespace=False)
    responsable_nombre = serializers.CharField(max_length=150, required=False, allow_null=True)
    responsable_identificacion = serializers.CharField(
        max_length=40, required=False, allow_null=True
    )
    responsable_domicilio = serializers.CharField(max_length=200, required=False, allow_null=True)
    responsable_canal_atencion = serializers.CharField(
        max_length=200, required=False, allow_null=True
    )


class ConfiguracionSitioSerializer(serializers.Serializer[Any]):
    nombre_marca = serializers.CharField(max_length=60)
    lema = serializers.CharField(allow_null=True)
    texto_descargo = serializers.CharField()
    responsable_nombre = serializers.CharField(allow_null=True)
    responsable_identificacion = serializers.CharField(allow_null=True)
    responsable_domicilio = serializers.CharField(allow_null=True)
    responsable_canal_atencion = serializers.CharField(allow_null=True)
    actualizado_en = serializers.DateTimeField()


class ContenidoResumenTableroSerializer(serializers.Serializer[Any]):
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
    enlace = serializers.CharField(allow_null=True, required=False)


class ContenidoRefPanelSerializer(serializers.Serializer[Any]):
    """components.schemas.ContenidoRefPanel. `ref_name` propio (Skill_Backend §5): cada capa API
    define sus propios serializers de referencia sin importar entre dominios."""

    tipo = serializers.CharField()
    id = IdSerializerField()
    titulo = serializers.CharField(max_length=150)
    slug = serializers.CharField(max_length=120, allow_null=True, required=False)
    estado_editorial = serializers.CharField()

    class Meta:
        ref_name = "ContenidoRefPanelInicio"


class SaludEditorialSerializer(serializers.Serializer[Any]):
    """`Tablero.salud_editorial` (EXP-001, COULD): null mientras no esté implementado."""

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
    conteos = ConteoTipoSerializer(many=True)
    recientes = ContenidoResumenTableroSerializer(many=True)
    alertas = AlertaTableroSerializer(many=True)
    salud_editorial = SaludEditorialSerializer(allow_null=True, required=False)
