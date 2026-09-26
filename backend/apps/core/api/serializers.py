"""Serializers de core (solo documentación/forma y validación de entrada; sin lógica, Regla 02)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rest_framework import serializers

from apps.core.exceptions import ErrorApi


class EstadoSaludSerializer(serializers.Serializer[dict[str, str]]):
    """components.schemas.EstadoSalud: solo {status: ok} (THREAT-028)."""

    status = serializers.ChoiceField(choices=["ok"])


class ProblemSerializer(serializers.Serializer[dict[str, object]]):
    """components.schemas.Problem (RFC 9457)."""

    type = serializers.URLField()
    title = serializers.CharField(max_length=200)
    status = serializers.IntegerField(min_value=400, max_value=599)
    detail = serializers.CharField(max_length=1000, required=False)
    code = serializers.RegexField(r"^[a-z][a-z0-9_]{2,63}$")
    errors = serializers.DictField(  # type: ignore[assignment]
        child=serializers.ListField(child=serializers.CharField(max_length=500)), required=False
    )
    trace_id = serializers.RegexField(r"^[0-9a-f]{32}$")


class PaginaMetaSerializer(serializers.Serializer[dict[str, Any]]):
    """components.schemas.PaginaMeta (DEC-AUTO-104); cada página añade `resultados`."""

    total = serializers.IntegerField(min_value=0)
    pagina = serializers.IntegerField(min_value=1)
    tamano_pagina = serializers.IntegerField(min_value=1)
    total_paginas = serializers.IntegerField(min_value=0)
    siguiente = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class EntradaEstricta(serializers.Serializer[Any]):
    """Base de las entradas con additionalProperties: false (DEC-AUTO-108, THREAT-024).

    Un campo desconocido o no editable → 400 `campo_no_permitido` con el campo en `errors`.
    """

    def to_internal_value(self, data: Any) -> Any:
        if isinstance(data, Mapping):
            sobrantes = sorted(str(clave) for clave in data if clave not in self.fields)
            if sobrantes:
                raise ErrorApi(
                    codigo="campo_no_permitido",
                    errors={clave: ["Campo no permitido."] for clave in sobrantes},
                )
        return super().to_internal_value(data)
