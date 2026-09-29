"""Serializers del panel de medios (contracts/openapi.yaml, tag `panel-medios`). Solo forma y
validación de estructura (Skill_Backend Regla 02): el guardado vive en `apps.medios.services`."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.api.serializers import EntradaEstricta, IdSerializerField, PaginaMetaSerializer
from apps.medios.models import EstadoMedio, FormatoDerivado, FormatoOrigen


@extend_schema_field({"type": ["integer", "null"], "format": "int64"})
class _CampoIdNuloInt64(serializers.IntegerField):
    """components.schemas.ActorRef.id: entero int64 nullable ("sistema" cuando es null); ver
    `apps.contenido.api.panel_serializers` (duplicada a propósito, Skill_Backend §5)."""


PATRON_NO_NUL = r"^[^\x00]*$"
PATRON_URL_HTTP = r"^https?://[^\x00]*$"


@extend_schema_field({"type": "string", "format": "uri-reference"})
class _CampoUriReferencia(serializers.CharField):
    """components.schemas.DerivadoImagen.url: uri-reference (ruta relativa)."""


@extend_schema_field({"type": ["string", "null"], "format": "uri"})
class _CampoUriNulo(serializers.CharField):
    """MedioPanel.fuente_url: uri absoluta nullable."""


def _texto_sin_nul(max_length: int) -> serializers.RegexField:
    return serializers.RegexField(
        PATRON_NO_NUL, max_length=max_length, required=False, allow_null=True, allow_blank=False
    )


@extend_schema_field({"type": ["integer", "null"], "format": "int64"})
class _CampoIdOpcionalInt64(serializers.IntegerField):
    """components.schemas.MedioCatalogacionEntrada.licencia_id (int64, opcional, nullable)."""


class MedioCatalogacionEntradaSerializer(EntradaEstricta):
    titulo_interno = _texto_sin_nul(150)
    texto_alternativo = _texto_sin_nul(250)
    pie_de_foto = _texto_sin_nul(300)
    autor_credito = _texto_sin_nul(150)
    fuente_url = serializers.RegexField(
        PATRON_URL_HTTP, max_length=500, required=False, allow_null=True, allow_blank=False
    )
    licencia_id = _CampoIdOpcionalInt64(min_value=1, required=False, allow_null=True)


class LicenciaRefSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    codigo = serializers.CharField(max_length=40)
    nombre = serializers.CharField(max_length=120)
    compatible_publicacion = serializers.BooleanField()


class DerivadoImagenSerializer(serializers.Serializer[Any]):
    """components.schemas.DerivadoImagen con `ref_name` propio: `apps.contenido.api.serializers`
    ya define un `DerivadoImagenSerializer` público con otro `Meta` (sin licencia ni credenciales
    del panel); mismo nombre de clase en dominios distintos por Skill_Backend §5.

    Campos `ancho`/`alto` (no `ancho_px`/`alto_px`, TKT-006 ciclo de corrección del gate CI):
    el contrato nombra así `DerivadoImagen.ancho`/`.alto` (requerido/opcional respectivamente)."""

    formato = serializers.ChoiceField(choices=FormatoDerivado.choices)
    ancho = serializers.IntegerField(min_value=1)
    alto = serializers.IntegerField(min_value=1)
    url = _CampoUriReferencia()

    class Meta:
        ref_name = "DerivadoImagenPanel"


class ActorRefSerializer(serializers.Serializer[Any]):
    """components.schemas.ActorRef con `ref_name` propio (evita colisión entre dominios,
    Skill_Backend §5: cada capa API define sus propios serializers de salida)."""

    id = _CampoIdNuloInt64(allow_null=True)
    etiqueta = serializers.CharField(max_length=60)

    class Meta:
        ref_name = "ActorRefMedio"


class MedioPanelSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    estado = serializers.ChoiceField(choices=EstadoMedio.choices)
    titulo_interno = serializers.CharField(max_length=150, allow_null=True)
    texto_alternativo = serializers.CharField(max_length=250, allow_null=True)
    pie_de_foto = serializers.CharField(max_length=300, allow_null=True)
    autor_credito = serializers.CharField(max_length=150, allow_null=True)
    fuente_url = _CampoUriNulo(allow_null=True)
    licencia = LicenciaRefSerializer(allow_null=True)
    formato_origen = serializers.ChoiceField(choices=FormatoOrigen.choices)
    ancho_px = serializers.IntegerField(min_value=1)
    alto_px = serializers.IntegerField(min_value=1)
    peso_bytes = serializers.IntegerField(min_value=1)
    derivados = DerivadoImagenSerializer(many=True, max_length=24)  # type: ignore[call-arg]
    numero_usos = serializers.IntegerField(min_value=0)
    en_uso_publicado = serializers.BooleanField()
    subido_por = ActorRefSerializer()
    subido_en = serializers.DateTimeField()
    actualizado_en = serializers.DateTimeField()
    pendientes_catalogacion = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[
                "texto_alternativo",
                "autor_credito",
                "licencia",
                "licencia_incompatible",
            ]
        ),
        max_length=5,
    )

    def to_representation(self, instance: Any) -> dict[str, Any]:
        from apps.medios import services

        medio = instance
        return {
            "id": medio.pk,
            "estado": medio.estado,
            "titulo_interno": medio.titulo_interno,
            "texto_alternativo": medio.texto_alternativo,
            "pie_de_foto": medio.pie_de_foto,
            "autor_credito": medio.autor_credito,
            "fuente_url": medio.fuente_url,
            "licencia": (
                {
                    "id": medio.licencia_id,
                    "codigo": medio.licencia.codigo,
                    "nombre": medio.licencia.nombre,
                    "compatible_publicacion": medio.licencia.compatible_publicacion,
                }
                if medio.licencia_id
                else None
            ),
            "formato_origen": medio.formato_origen,
            "ancho_px": medio.ancho_px,
            "alto_px": medio.alto_px,
            "peso_bytes": medio.peso_bytes,
            "derivados": [
                {
                    "formato": d.formato,
                    "ancho": d.ancho_px,
                    "alto": d.alto_px,
                    "url": (
                        f"/api/v1/panel/medios/{medio.pk}/archivo"
                        f"?ancho={d.ancho_px}&formato={d.formato}"
                    ),
                }
                for d in medio.derivados.all()
            ],
            "numero_usos": len(services.usos(medio.pk)),
            "en_uso_publicado": services._en_uso_publicado(medio.pk),
            "subido_por": {
                "id": medio.subido_por_id,
                "etiqueta": f"#{medio.subido_por_id}" if medio.subido_por_id else "sistema",
            },
            "subido_en": medio.subido_en,
            "actualizado_en": medio.actualizado_en,
            "pendientes_catalogacion": services._pendientes_catalogacion(
                medio,
                licencia_compatible=(
                    medio.licencia.compatible_publicacion if medio.licencia_id else None
                ),
            ),
        }


class PaginaMedioPanelSerializer(PaginaMetaSerializer):
    resultados = MedioPanelSerializer(many=True)


class MotivoRechazoMedioSerializer(serializers.Serializer[Any]):
    """`ResultadoSubida.resultados[].motivo` (esquema en línea del contrato: {code, detalle})."""

    code = serializers.ChoiceField(
        choices=[
            "formato_no_permitido",
            "tamano_excedido",
            "dimensiones_insuficientes",
            "megapixeles_excedidos",
            "archivo_corrupto",
        ]
    )
    detalle = serializers.CharField(max_length=300)


class ResultadoArchivoSerializer(serializers.Serializer[Any]):
    nombre_archivo = serializers.CharField(max_length=255)
    resultado = serializers.ChoiceField(choices=["ACEPTADO", "RECHAZADO", "DUPLICADO"])
    medio = MedioPanelSerializer(allow_null=True, required=False)
    medio_existente_id = _CampoIdOpcionalInt64(min_value=1, allow_null=True, required=False)
    motivo = MotivoRechazoMedioSerializer(required=False, allow_null=True)


class ResultadoSubidaSerializer(serializers.Serializer[Any]):
    resultados = ResultadoArchivoSerializer(many=True)


class UsoMedioSerializer(serializers.Serializer[Any]):
    tipo_contenido = serializers.ChoiceField(
        choices=["DESTINO", "ITINERARIO", "GUIA", "TIPO", "COLECCION", "CONFIG_INICIO"]
    )
    contenido_id = IdSerializerField()
    titulo = serializers.CharField(max_length=150)
    estado_editorial = serializers.ChoiceField(
        choices=["BORRADOR", "PUBLICADO", "RETIRADO"], allow_null=True, required=False
    )
    rol = serializers.ChoiceField(choices=["PORTADA", "GALERIA", "HERO"])


class PaginaUsoMedioSerializer(PaginaMetaSerializer):
    resultados = UsoMedioSerializer(many=True)
