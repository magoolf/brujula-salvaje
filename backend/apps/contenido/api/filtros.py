"""Validación de los parámetros de consulta públicos (AC-113, THREAT-008, THREAT-009, DEC-AUTO-047).

Los valores se contrastan con dominios cerrados: patrón de slug, rangos numéricos, enumeraciones y
existencia del slug (tipos/destinos publicados, regiones, países y categorías activos). Cualquier
valor fuera de dominio → 400 parametro_invalido con el parámetro en `errors` (nunca 500).
"""

from __future__ import annotations

from typing import Any, ClassVar

from drf_spectacular.utils import OpenApiParameter
from rest_framework import serializers
from rest_framework.request import Request

from apps.catalogos import selectors as catalogos
from apps.catalogos.models import PATRON_SLUG
from apps.contenido import selectors
from apps.core.parametros import errores_de_parametros

MENSAJE_INEXISTENTE = "No existe."
MENSAJE_REPETIDO = "Los valores no pueden repetirse."
SLUG_SCHEMA: dict[str, Any] = {
    "type": "string",
    "minLength": 1,
    "maxLength": 120,
    "pattern": PATRON_SLUG,
}


def _slug(**kwargs: Any) -> serializers.RegexField:
    return serializers.RegexField(PATRON_SLUG, min_length=1, max_length=120, **kwargs)


def _unicos(nombre: str, valores: list[Any]) -> None:
    if len(set(valores)) != len(valores):
        raise serializers.ValidationError({nombre: [MENSAJE_REPETIDO]})


def _array(items: dict[str, Any], maximo: int) -> dict[str, Any]:
    return {"type": "array", "maxItems": maximo, "uniqueItems": True, "items": items}


def _eleccion(**kwargs: Any) -> serializers.ChoiceField:
    """ChoiceField cuyo error no repite el valor recibido (sin reflejo de la entrada)."""
    return serializers.ChoiceField(
        error_messages={"invalid_choice": "Valor no admitido."}, **kwargs
    )


def rango(maximo: int) -> dict[str, Any]:
    return {"type": "integer", "minimum": 1, "maximum": maximo}


def validar(clase: type[serializers.Serializer[Any]], request: Request) -> Any:
    filtro = clase(data=request.query_params)
    if not filtro.is_valid():
        raise errores_de_parametros(filtro.errors)
    return filtro.validated_data


class FiltroDestinosSerializer(serializers.Serializer[Any]):
    PARAMETROS: ClassVar[tuple[str, ...]] = (
        "tipo",
        "region",
        "pais",
        "dificultad_min",
        "dificultad_max",
        "mes",
        "duracion",
        "presupuesto",
        "orden",
    )
    MULTIPLES: ClassVar[tuple[str, ...]] = ("tipo", "duracion", "presupuesto")

    tipo = serializers.ListField(child=_slug(), max_length=12, required=False)
    region = _slug(required=False)
    pais = _slug(required=False)
    dificultad_min = serializers.IntegerField(min_value=1, max_value=5, required=False)
    dificultad_max = serializers.IntegerField(min_value=1, max_value=5, required=False)
    mes = serializers.IntegerField(min_value=1, max_value=12, required=False)
    duracion = serializers.ListField(
        child=_eleccion(choices=list(selectors.TRAMOS_DURACION)),
        max_length=4,
        required=False,
    )
    presupuesto = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=4), max_length=4, required=False
    )
    orden = _eleccion(choices=list(selectors.ORDENES_DESTINOS), required=False, default="nombre")

    @staticmethod
    def documentacion() -> list[OpenApiParameter]:
        return [
            OpenApiParameter(
                "tipo", _array(SLUG_SCHEMA, 12), style="form", explode=True,
                description="Slugs de tipos de aventura (OR). Repetible `?tipo=a&tipo=b`.",
            ),
            OpenApiParameter("region", SLUG_SCHEMA),
            OpenApiParameter("pais", SLUG_SCHEMA),
            OpenApiParameter("dificultad_min", rango(5)),
            OpenApiParameter("dificultad_max", rango(5)),
            OpenApiParameter("mes", rango(12)),
            OpenApiParameter(
                "duracion",
                _array({"type": "string", "enum": list(selectors.TRAMOS_DURACION)}, 4),
                style="form", explode=True, description="Tramos de duración (OR).",
            ),
            OpenApiParameter(
                "presupuesto", _array(rango(4), 4), style="form", explode=True,
                description="Niveles de presupuesto (OR).",
            ),
            OpenApiParameter(
                "orden",
                {"type": "string", "enum": list(selectors.ORDENES_DESTINOS), "default": "nombre"},
            ),
        ]  # fmt: skip

    def validate(self, attrs: dict[str, Any]) -> selectors.FiltrosDestinos:
        for nombre in self.MULTIPLES:
            _unicos(nombre, attrs.get(nombre, []))
        minimo, maximo = attrs.get("dificultad_min"), attrs.get("dificultad_max")
        if minimo is not None and maximo is not None and minimo > maximo:
            raise serializers.ValidationError(
                {"dificultad_min": ["No puede ser mayor que dificultad_max."]}
            )
        tipos = attrs.get("tipo", [])
        if tipos and selectors.slugs_de_tipos_publicados(tipos) != set(tipos):
            raise serializers.ValidationError({"tipo": [MENSAJE_INEXISTENTE]})
        if attrs.get("region") and not catalogos.existe_region(attrs["region"]):
            raise serializers.ValidationError({"region": [MENSAJE_INEXISTENTE]})
        if attrs.get("pais") and not catalogos.existe_pais(attrs["pais"]):
            raise serializers.ValidationError({"pais": [MENSAJE_INEXISTENTE]})
        return selectors.FiltrosDestinos(
            tipos=tuple(tipos),
            region=attrs.get("region"),
            pais=attrs.get("pais"),
            dificultad_min=minimo,
            dificultad_max=maximo,
            mes=attrs.get("mes"),
            duraciones=tuple(attrs.get("duracion", [])),
            presupuestos=tuple(attrs.get("presupuesto", [])),
            orden=attrs["orden"],
        )


class FiltroItinerariosSerializer(serializers.Serializer[Any]):
    PARAMETROS: ClassVar[tuple[str, ...]] = ("destino", "orden")

    destino = _slug(required=False)
    orden = _eleccion(choices=list(selectors.ORDENES_ITINERARIOS), required=False, default="titulo")

    @staticmethod
    def documentacion() -> list[OpenApiParameter]:
        return [
            OpenApiParameter(
                "destino", SLUG_SCHEMA, description="Slug del destino (itinerarios de un destino)."
            ),
            OpenApiParameter(
                "orden",
                {
                    "type": "string",
                    "enum": list(selectors.ORDENES_ITINERARIOS),
                    "default": "titulo",
                },
            ),
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        destino = attrs.get("destino")
        if destino and not selectors.existe_destino_publicado(destino):
            raise serializers.ValidationError({"destino": [MENSAJE_INEXISTENTE]})
        return attrs


class FiltroGuiasSerializer(serializers.Serializer[Any]):
    PARAMETROS: ClassVar[tuple[str, ...]] = ("categoria",)

    categoria = _slug(required=False)

    @staticmethod
    def documentacion() -> list[OpenApiParameter]:
        return [OpenApiParameter("categoria", SLUG_SCHEMA)]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        categoria = attrs.get("categoria")
        if categoria and not catalogos.existe_categoria(categoria):
            raise serializers.ValidationError({"categoria": [MENSAJE_INEXISTENTE]})
        return attrs


class FiltroBusquedaSerializer(serializers.Serializer[Any]):
    """RULE-018: 2..100 caracteres tras recortar; fuera de rango → 400 sin buscar (AC-020)."""

    q = serializers.CharField(min_length=2, max_length=100, trim_whitespace=True)

    @staticmethod
    def documentacion_q() -> OpenApiParameter:
        return OpenApiParameter(
            "q",
            {"type": "string", "minLength": 2, "maxLength": 100, "pattern": "^[^\\u0000]*$"},
            required=True,
            description="Texto de búsqueda (2..100 caracteres tras recortar espacios).",
        )
