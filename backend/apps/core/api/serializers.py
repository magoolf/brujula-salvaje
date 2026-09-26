"""Serializers de salida de core (solo documentación/forma; sin lógica, Regla 02)."""

from __future__ import annotations

from rest_framework import serializers


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
