"""Serializers del panel de medios (contracts/openapi.yaml, tag `panel-medios`). Solo forma y
validación de estructura (Skill_Backend Regla 02): el guardado vive en `apps.medios.services`."""

from __future__ import annotations

import copy
from typing import Any

from django.core.validators import MaxLengthValidator, MinLengthValidator
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.api.serializers import EntradaEstricta, IdSerializerField, PaginaMetaSerializer
from apps.core.esquema import id_contrato, url_http
from apps.medios.models import EstadoMedio, FormatoDerivado, FormatoOrigen


def _con_limite(campo: Any, *, max_length: int | None = None, min_length: int | None = None) -> Any:
    """Ídem `apps.contenido.api.panel_serializers._con_limite` (duplicada a propósito,
    Skill_Backend §5; ver ahí el porqué completo, RONDA 5): reconstruye el `ListSerializer` con
    `validators=` como kwarg del constructor -- mutar `campo.validators` después de construir el
    campo no sobrevive al `copy.deepcopy(self._declared_fields)` que DRF hace en cada
    instanciación del serializer padre, porque `Field.__deepcopy__` reconstruye el campo desde
    `self._args`/`self._kwargs` (los originales) y descarta cualquier mutación posterior."""
    validadores = list(campo._kwargs.get("validators") or [])
    if max_length is not None:
        validadores.append(MaxLengthValidator(max_length))
    if min_length is not None:
        validadores.append(MinLengthValidator(min_length))
    kwargs = dict(campo._kwargs)
    kwargs["child"] = copy.deepcopy(kwargs["child"])
    kwargs["validators"] = validadores
    return campo.__class__(*campo._args, **kwargs)


@extend_schema_field({"type": ["integer", "null"], "format": "int64"})
class _CampoIdNuloInt64(serializers.IntegerField):
    """components.schemas.ActorRef.id: entero int64 nullable ("sistema" cuando es null); ver
    `apps.contenido.api.panel_serializers` (duplicada a propósito, Skill_Backend §5)."""


PATRON_NO_NUL = r"^[^\x00]*$"


@extend_schema_field({"type": "string", "format": "uri-reference"})
class _CampoUriReferencia(serializers.CharField):
    """components.schemas.DerivadoImagen.url: uri-reference (ruta relativa)."""


@extend_schema_field({"type": ["string", "null"], "format": "uri"})
class _CampoUriNulo(serializers.CharField):
    """MedioPanel.fuente_url: uri absoluta nullable."""


def _texto_sin_nul(max_length: int) -> serializers.RegexField:
    """`allow_blank=True` (TKT-006 ciclo oasdiff, `request-property-min-length-set`): el contrato
    no exige longitud mínima en estos campos (string vacío es válido, p.ej. para "borrar" un
    texto alternativo). `allow_blank=False` (elección de una ronda anterior) hacía que
    drf-spectacular inyectara `minLength: 1` automáticamente en el esquema de request
    (`_get_serializer_field_meta`, COMPONENT_SPLIT_REQUEST) -- inofensivo en runtime porque
    `CharField.run_validation` corta en corto para `''` cuando `allow_blank=True` (el patrón
    `PATRON_NO_NUL` nunca llega a evaluarse sobre un string vacío), así que esto solo cambia lo
    que se documenta, no el rango real ya aceptado."""
    return serializers.RegexField(
        PATRON_NO_NUL, max_length=max_length, required=False, allow_null=True, allow_blank=True
    )


@extend_schema_field({"type": ["integer", "null"], "format": "int64"})
class _CampoIdOpcionalInt64(serializers.IntegerField):
    """components.schemas.MedioCatalogacionEntrada.licencia_id (int64, opcional, nullable)."""


class MedioCatalogacionEntradaSerializer(EntradaEstricta):
    titulo_interno = _texto_sin_nul(150)
    texto_alternativo = _texto_sin_nul(250)
    pie_de_foto = _texto_sin_nul(300)
    autor_credito = _texto_sin_nul(150)
    # TKT-032 (INFO de la QA de TKT-012): el patrón del contrato (`^https?://...`) prohíbe la
    # cadena vacía, pero con `allow_blank=True` `CharField.run_validation` cortaba en corto para
    # `''` (el patrón nunca se evaluaba) y la BD la rechazaba (ck_medio_fuente_url) con un 500.
    # Ahora `allow_blank=False` (400 `validacion`); sin URL se envía `null` (el contrato lo
    # admite). El `minLength: 1` que drf-spectacular documentaría por `allow_blank=False` no está
    # en el contrato (el patrón ya excluye la cadena vacía): se quita con `esquema_sin`.
    fuente_url = url_http(
        max_length=500, required=False, allow_null=True, esquema_sin=("minLength",)
    )
    # `id_contrato`: `Id` nullable del contrato (int64, mínimo 1, sin `maximum`) que además
    # rechaza ids fuera de bigint antes del ORM (TKT-032; antes llegaban a la BD → 500).
    licencia_id = id_contrato(required=False, allow_null=True)


@extend_schema_field(
    {
        # Sin 'null' aquí: `allow_null=True` en el uso (`LicenciaRefSerializer(allow_null=True)`)
        # hace que `append_meta` (drf-spectacular) lo añada una sola vez a `type`; declararlo
        # también aquí duplicaba la entrada (`['object', 'null', 'null']`).
        "type": "object",
        "required": ["id", "codigo", "nombre", "compatible_publicacion"],
        "properties": {
            # Inline, no `$ref`: drf-spectacular no registra un componente `Id` propio
            # (`IdSerializerField` usa `extend_schema_field` inline, apps.core, fuera de
            # archivos_permitidos); mismo literal que `components.schemas.Id` del contrato.
            "id": {"type": "integer", "format": "int64", "minimum": 1},
            "codigo": {"type": "string", "maxLength": 40},
            "nombre": {"type": "string", "maxLength": 120},
            "compatible_publicacion": {"type": "boolean"},
        },
    }
)
class LicenciaRefSerializer(serializers.Serializer[Any]):
    """`MedioPanel.licencia` (TKT-006 ciclo oasdiff, `response-property-one-of-added`): el
    contrato lo declara como objeto EN LÍNEA nullable (`type: ['object', 'null']`, sin `$ref` a
    un componente propio). Usar este serializer como `LicenciaRefSerializer(allow_null=True)`
    genera en cambio un `$ref` a un componente nombrado que `append_meta` (OAS 3.1) envuelve en
    `oneOf: [{$ref}, {type: 'null'}]` -- forma válida pero distinta a la del contrato.
    `extend_schema_field` con el literal exacto evita el `$ref`/`oneOf` y coincide byte a byte
    con `MedioPanel.licencia`. `MedioPanelSerializer.to_representation` ya construye este campo
    a mano (dict literal), así que el override no cambia ningún comportamiento en runtime."""

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
    derivados = _con_limite(DerivadoImagenSerializer(many=True), max_length=24)
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


@extend_schema_field(
    {
        # Sin 'null' aquí: ídem `LicenciaRefSerializer`, `allow_null=True` en el uso
        # (`MotivoRechazoMedioSerializer(..., allow_null=True)`) lo añade una sola vez.
        "type": "object",
        "required": ["code", "detalle"],
        "properties": {
            "code": {
                "type": "string",
                "enum": [
                    "formato_no_permitido",
                    "tamano_excedido",
                    "dimensiones_insuficientes",
                    "megapixeles_excedidos",
                    "archivo_corrupto",
                ],
            },
            "detalle": {"type": "string", "maxLength": 300},
        },
    }
)
class MotivoRechazoMedioSerializer(serializers.Serializer[Any]):
    """`ResultadoSubida.resultados[].motivo` (esquema en línea del contrato: {code, detalle}).
    `extend_schema_field` (TKT-006 ciclo oasdiff, `response-property-one-of-added`): mismo caso
    que `LicenciaRefSerializer` -- el contrato lo declara inline nullable, no como `$ref`
    envuelto en `oneOf`. `ResultadoArchivoSerializer.motivo` no tiene `to_representation` propio,
    pero DRF serializa un `dict` de entrada (`{"code":..., "detalle":...}` o `None`) igual con o
    sin este override: el override solo cambia el esquema, no la introspección de atributos."""

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
    resultados = _con_limite(ResultadoArchivoSerializer(many=True), max_length=10, min_length=1)


@extend_schema_field({"$ref": "#/components/schemas/EstadoEditorial"})
class _CampoEstadoEditorialRef(serializers.ChoiceField):
    """`UsoMedio.estado_editorial` del contrato: `oneOf: [$ref EstadoEditorial, null]` (TKT-012,
    response-property-one-of-added). Sin el override drf-spectacular nombra el enum
    `EstadoEditorialEnum` y oasdiff lo ve como otra rama del `oneOf`. Con `allow_null=True`,
    `append_meta` envuelve el `$ref` en `oneOf: [{$ref}, {type: 'null'}]`, la forma exacta del
    contrato; el componente `EstadoEditorial` lo garantiza `apps.core.esquema`."""


class UsoMedioSerializer(serializers.Serializer[Any]):
    tipo_contenido = serializers.ChoiceField(
        choices=["DESTINO", "ITINERARIO", "GUIA", "TIPO", "COLECCION", "CONFIG_INICIO"]
    )
    contenido_id = IdSerializerField()
    titulo = serializers.CharField(max_length=150)
    estado_editorial = _CampoEstadoEditorialRef(
        choices=["BORRADOR", "PUBLICADO", "RETIRADO"], allow_null=True, required=False
    )
    rol = serializers.ChoiceField(choices=["PORTADA", "GALERIA", "HERO"])


class PaginaUsoMedioSerializer(PaginaMetaSerializer):
    resultados = UsoMedioSerializer(many=True)


class SubidaMediosEntradaSerializer(serializers.Serializer[Any]):
    """components.schemas.SubidaMediosEntrada: SOLO documenta el cuerpo multipart de
    `panelSubirMedios` (TKT-012: request-property-removed `archivos` y el request-body-type-changed
    que DEC-AUTO-920 tenía que ignorar). La vista lee `request.FILES.getlist("archivos")` y aplica
    ella misma el 1..10 (400 con el mismo `errors.archivos`); el contenido de cada archivo lo
    valida `apps.medios.services` (tipo real, tamaño, megapíxeles)."""

    archivos = serializers.ListField(child=serializers.FileField(), min_length=1, max_length=10)
