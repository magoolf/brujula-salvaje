"""Serializers de taxonomías del panel (contracts/openapi.yaml, tag panel-configuracion).
Solo forma y validación (Skill_Backend Regla 02); el guardado vive en `apps.catalogos.services`."""

from __future__ import annotations

import copy
from typing import Any

from django.core.validators import MaxLengthValidator, MinLengthValidator
from rest_framework import serializers

from apps.catalogos.models import Continente, Escala
from apps.core.api.serializers import EntradaEstricta, IdSerializerField, PaginaMetaSerializer
from apps.core.esquema import id_contrato, texto_sin_nul, url_http

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


class _IdMixin(serializers.Serializer[Any]):
    """Rama `{id}` de las salidas `allOf: [{id}, {X}Campos]` del contrato."""

    id = IdSerializerField()


# Cada recurso declara UNA vez sus campos ({X}Campos del contrato) en un Mixin que comparten la
# entrada y la salida (mismo patrón que apps/contenido/api/panel_serializers.py, TKT-012): así el
# componente {X}Campos que `apps.core.esquema` reparte en `allOf` lleva las mismas restricciones
# (patrón, longitudes, rangos) en petición y respuesta, como en el contrato. En la salida los
# validadores no se ejecutan (solo `to_representation`).
class RegionCamposMixin(serializers.Serializer[Any]):
    nombre = texto_sin_nul(min_length=1, max_length=60)
    slug = serializers.RegexField(PATRON_SLUG, min_length=1, max_length=60)
    continente = serializers.ChoiceField(choices=Continente.choices)
    orden = serializers.IntegerField(min_value=0, max_value=1000)
    activo = serializers.BooleanField()


class RegionEntradaSerializer(EntradaEstricta, RegionCamposMixin):
    pass


class RegionSerializer(_IdMixin, RegionCamposMixin):
    pass


class PaginaRegionSerializer(PaginaMetaSerializer):
    resultados = RegionSerializer(many=True)


class PaisCamposMixin(serializers.Serializer[Any]):
    nombre = texto_sin_nul(min_length=1, max_length=80)
    slug = serializers.RegexField(PATRON_SLUG, min_length=1, max_length=80)
    codigo_iso2 = serializers.RegexField(r"^[A-Z]{2}$")
    region_id = id_contrato()
    activo = serializers.BooleanField()


class PaisEntradaSerializer(EntradaEstricta, PaisCamposMixin):
    pass


class PaisSerializer(_IdMixin, PaisCamposMixin):
    pass


class PaginaPaisSerializer(PaginaMetaSerializer):
    resultados = PaisSerializer(many=True)


class CategoriaGuiaCamposMixin(serializers.Serializer[Any]):
    nombre = texto_sin_nul(min_length=1, max_length=80)
    slug = serializers.RegexField(PATRON_SLUG, min_length=1, max_length=80)
    descripcion = texto_sin_nul(min_length=1, max_length=400)
    orden = serializers.IntegerField(min_value=0, max_value=1000)
    activo = serializers.BooleanField()


class CategoriaGuiaEntradaSerializer(EntradaEstricta, CategoriaGuiaCamposMixin):
    pass


class CategoriaGuiaPanelSerializer(_IdMixin, CategoriaGuiaCamposMixin):
    pass


class PaginaCategoriaGuiaPanelSerializer(PaginaMetaSerializer):
    resultados = CategoriaGuiaPanelSerializer(many=True)


class LicenciaCamposMixin(serializers.Serializer[Any]):
    codigo = serializers.RegexField(r"^[A-Z0-9.-]+$", min_length=1, max_length=40)
    nombre = texto_sin_nul(min_length=1, max_length=120)
    # El contrato exige URL absoluta http(s) (`format: uri`, `pattern: '^https?://...'`): se
    # valida de verdad, no solo se documenta (TKT-012).
    url_texto_legal = url_http(max_length=500, required=False, allow_null=True)
    requiere_atribucion = serializers.BooleanField()
    compatible_publicacion = serializers.BooleanField()
    activo = serializers.BooleanField()


class LicenciaEntradaSerializer(EntradaEstricta, LicenciaCamposMixin):
    pass


class LicenciaSerializer(_IdMixin, LicenciaCamposMixin):
    pass


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
