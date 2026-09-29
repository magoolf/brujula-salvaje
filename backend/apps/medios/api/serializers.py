"""Serializers del panel de medios (contracts/openapi.yaml, tag `panel-medios`). Solo forma y
validación de estructura (Skill_Backend Regla 02): el guardado vive en `apps.medios.services`."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.api.serializers import EntradaEstricta, IdSerializerField, PaginaMetaSerializer
from apps.medios.models import EstadoMedio, FormatoDerivado, FormatoOrigen


class MedioCatalogacionEntradaSerializer(EntradaEstricta):
    titulo_interno = serializers.CharField(
        max_length=150, required=False, allow_null=True, allow_blank=False
    )
    texto_alternativo = serializers.CharField(
        max_length=250, required=False, allow_null=True, allow_blank=False
    )
    pie_de_foto = serializers.CharField(
        max_length=300, required=False, allow_null=True, allow_blank=False
    )
    autor_credito = serializers.CharField(
        max_length=150, required=False, allow_null=True, allow_blank=False
    )
    fuente_url = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=False
    )
    licencia_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class LicenciaRefSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    codigo = serializers.CharField(max_length=40)
    nombre = serializers.CharField(max_length=120)
    compatible_publicacion = serializers.BooleanField()


class DerivadoImagenSerializer(serializers.Serializer[Any]):
    """components.schemas.DerivadoImagen con `ref_name` propio: `apps.contenido.api.serializers`
    ya define un `DerivadoImagenSerializer` público con otro `Meta` (sin licencia ni credenciales
    del panel); mismo nombre de clase en dominios distintos por Skill_Backend §5."""

    formato = serializers.ChoiceField(choices=FormatoDerivado.choices)
    ancho_px = serializers.IntegerField(min_value=1)
    alto_px = serializers.IntegerField(min_value=1)
    url = serializers.CharField()

    class Meta:
        ref_name = "DerivadoImagenPanel"


class ActorRefSerializer(serializers.Serializer[Any]):
    """components.schemas.ActorRef con `ref_name` propio (evita colisión entre dominios,
    Skill_Backend §5: cada capa API define sus propios serializers de salida)."""

    id = serializers.IntegerField(allow_null=True)
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
    fuente_url = serializers.CharField(allow_null=True)
    licencia = LicenciaRefSerializer(allow_null=True)
    formato_origen = serializers.ChoiceField(choices=FormatoOrigen.choices)
    ancho_px = serializers.IntegerField(min_value=1)
    alto_px = serializers.IntegerField(min_value=1)
    peso_bytes = serializers.IntegerField(min_value=1)
    derivados = DerivadoImagenSerializer(many=True)
    numero_usos = serializers.IntegerField(min_value=0)
    en_uso_publicado = serializers.BooleanField()
    subido_por = ActorRefSerializer()
    subido_en = serializers.DateTimeField()
    actualizado_en = serializers.DateTimeField()
    pendientes_catalogacion = serializers.ListField(child=serializers.CharField())

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
                    "ancho_px": d.ancho_px,
                    "alto_px": d.alto_px,
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


class ResultadoArchivoSerializer(serializers.Serializer[Any]):
    nombre_archivo = serializers.CharField(max_length=255)
    resultado = serializers.ChoiceField(choices=["ACEPTADO", "RECHAZADO", "DUPLICADO"])
    medio = MedioPanelSerializer(allow_null=True, required=False)
    medio_existente_id = serializers.IntegerField(min_value=1, allow_null=True, required=False)
    motivo = serializers.DictField(required=False, allow_null=True)


class ResultadoSubidaSerializer(serializers.Serializer[Any]):
    resultados = ResultadoArchivoSerializer(many=True)


class UsoMedioSerializer(serializers.Serializer[Any]):
    tipo_contenido = serializers.CharField()
    contenido_id = IdSerializerField()
    titulo = serializers.CharField(max_length=150)
    estado_editorial = serializers.CharField(allow_null=True)
    rol = serializers.ChoiceField(choices=["PORTADA", "GALERIA", "HERO"])


class PaginaUsoMedioSerializer(PaginaMetaSerializer):
    resultados = UsoMedioSerializer(many=True)
