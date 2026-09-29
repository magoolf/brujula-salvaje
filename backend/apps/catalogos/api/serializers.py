"""Serializers de taxonomías del panel (contracts/openapi.yaml, tag panel-configuracion).
Solo forma y validación (Skill_Backend Regla 02); el guardado vive en `apps.catalogos.services`."""

from __future__ import annotations

import copy
from typing import Any

from django.core.validators import MaxLengthValidator, MinLengthValidator
from rest_framework import serializers

from apps.catalogos.models import Continente, Escala
from apps.core.api.serializers import EntradaEstricta, IdSerializerField, PaginaMetaSerializer

PATRON_SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"
PATRON_NO_NUL = r"^[^\x00]*$"


def _con_limite(campo: Any, *, max_length: int | None = None, min_length: int | None = None) -> Any:
    """Ídem `apps.contenido.api.panel_serializers._con_limite` (duplicada a propósito,
    Skill_Backend §5; ver ahí el porqué completo, RONDA 5): reconstruye el `ListSerializer` con
    `validators=` como kwarg del constructor -- mutar `campo.validators` después de construir el
    campo no sobrevive al `copy.deepcopy(self._declared_fields)` que DRF hace en cada
    instanciación del serializer padre."""
    validadores = list(campo._kwargs.get("validators") or [])
    if max_length is not None:
        validadores.append(MaxLengthValidator(max_length))
    if min_length is not None:
        validadores.append(MinLengthValidator(min_length))
    kwargs = dict(campo._kwargs)
    kwargs["child"] = copy.deepcopy(kwargs["child"])
    kwargs["validators"] = validadores
    return campo.__class__(*campo._args, **kwargs)


class RegionEntradaSerializer(EntradaEstricta):
    nombre = serializers.CharField(min_length=1, max_length=60)
    slug = serializers.RegexField(PATRON_SLUG, min_length=1, max_length=60)
    continente = serializers.ChoiceField(choices=Continente.choices)
    orden = serializers.IntegerField(min_value=0, max_value=1000)
    activo = serializers.BooleanField()


class RegionSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    nombre = serializers.CharField(max_length=60)
    slug = serializers.CharField(max_length=60)
    continente = serializers.ChoiceField(choices=Continente.choices)
    orden = serializers.IntegerField()
    activo = serializers.BooleanField()


class PaginaRegionSerializer(PaginaMetaSerializer):
    resultados = RegionSerializer(many=True)


class PaisEntradaSerializer(EntradaEstricta):
    nombre = serializers.CharField(min_length=1, max_length=80)
    slug = serializers.RegexField(PATRON_SLUG, min_length=1, max_length=80)
    codigo_iso2 = serializers.RegexField(r"^[A-Z]{2}$")
    region_id = IdSerializerField()
    activo = serializers.BooleanField()


class PaisSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    nombre = serializers.CharField(max_length=80)
    slug = serializers.CharField(max_length=80)
    codigo_iso2 = serializers.CharField()
    region_id = IdSerializerField()
    activo = serializers.BooleanField()


class PaginaPaisSerializer(PaginaMetaSerializer):
    resultados = PaisSerializer(many=True)


class CategoriaGuiaEntradaSerializer(EntradaEstricta):
    nombre = serializers.CharField(min_length=1, max_length=80)
    slug = serializers.RegexField(PATRON_SLUG, min_length=1, max_length=80)
    descripcion = serializers.CharField(min_length=1, max_length=400)
    orden = serializers.IntegerField(min_value=0, max_value=1000)
    activo = serializers.BooleanField()


class CategoriaGuiaPanelSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    nombre = serializers.CharField(max_length=80)
    slug = serializers.CharField(max_length=80)
    descripcion = serializers.CharField(max_length=400)
    orden = serializers.IntegerField()
    activo = serializers.BooleanField()


class PaginaCategoriaGuiaPanelSerializer(PaginaMetaSerializer):
    resultados = CategoriaGuiaPanelSerializer(many=True)


class LicenciaEntradaSerializer(EntradaEstricta):
    codigo = serializers.RegexField(r"^[A-Z0-9.-]+$", min_length=1, max_length=40)
    nombre = serializers.CharField(min_length=1, max_length=120)
    url_texto_legal = serializers.CharField(max_length=500, required=False, allow_null=True)
    requiere_atribucion = serializers.BooleanField()
    compatible_publicacion = serializers.BooleanField()
    activo = serializers.BooleanField()


class LicenciaSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    codigo = serializers.CharField(max_length=40)
    nombre = serializers.CharField(max_length=120)
    url_texto_legal = serializers.CharField(allow_null=True)
    requiere_atribucion = serializers.BooleanField()
    compatible_publicacion = serializers.BooleanField()
    activo = serializers.BooleanField()


class PaginaLicenciaSerializer(PaginaMetaSerializer):
    resultados = LicenciaSerializer(many=True)


class NivelEscalaEntradaSerializer(EntradaEstricta):
    etiqueta = serializers.RegexField(PATRON_NO_NUL, min_length=1, max_length=40)
    descripcion = serializers.RegexField(PATRON_NO_NUL, min_length=1, max_length=400)


class NivelEscalaPanelSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    escala = serializers.ChoiceField(choices=Escala.choices)
    nivel = serializers.IntegerField()
    etiqueta = serializers.CharField(max_length=40)
    descripcion = serializers.CharField(max_length=400)


class EscalasPanelSerializer(serializers.Serializer[Any]):
    dificultad = _con_limite(NivelEscalaPanelSerializer(many=True), max_length=5, min_length=5)
    presupuesto = _con_limite(NivelEscalaPanelSerializer(many=True), max_length=4, min_length=4)
