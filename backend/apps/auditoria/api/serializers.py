"""Serializers de la consulta de auditoría (contracts/openapi.yaml, tag panel-auditoria)."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.auditoria.models import AccionAuditoria, EventoAuditoria, ResultadoAuditoria
from apps.core.api.serializers import IdSerializerField, PaginaMetaSerializer


class ActorRefSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField(allow_null=True, max_value=2**63 - 1)
    etiqueta = serializers.CharField(max_length=60)


class EventoAuditoriaSerializer(serializers.ModelSerializer[EventoAuditoria]):
    id = IdSerializerField(read_only=True)
    actor = serializers.SerializerMethodField()
    tipo_entidad = serializers.CharField(max_length=40, allow_null=True, read_only=True)
    entidad_id = serializers.IntegerField(allow_null=True, max_value=2**63 - 1, read_only=True)
    entidad_titulo = serializers.CharField(max_length=150, allow_null=True, read_only=True)
    campos_cambiados = serializers.ListField(
        child=serializers.CharField(max_length=100), max_length=100, read_only=True
    )
    ip_truncada = serializers.CharField(max_length=45, allow_null=True, read_only=True)

    class Meta:
        model = EventoAuditoria
        fields = [
            "id",
            "ocurrido_en",
            "actor",
            "accion",
            "resultado",
            "tipo_entidad",
            "entidad_id",
            "entidad_titulo",
            "campos_cambiados",
            "ip_truncada",
        ]
        read_only_fields = fields

    @extend_schema_field(ActorRefSerializer)
    def get_actor(self, evento: EventoAuditoria) -> dict[str, Any]:
        return {"id": evento.actor_id, "etiqueta": evento.actor_etiqueta}

    def to_representation(self, instance: EventoAuditoria) -> dict[str, Any]:
        if instance.campos_cambiados is None:
            instance.campos_cambiados = []
        datos: dict[str, Any] = super().to_representation(instance)
        return datos


class PaginaEventoAuditoriaSerializer(PaginaMetaSerializer):
    resultados = EventoAuditoriaSerializer(many=True)


class FiltroAuditoriaSerializer(serializers.Serializer[dict[str, Any]]):
    desde = serializers.DateTimeField(required=False)
    hasta = serializers.DateTimeField(required=False)
    actor_id = serializers.IntegerField(min_value=1, max_value=2**63 - 1, required=False)
    accion = serializers.ChoiceField(choices=AccionAuditoria.choices, required=False)
    tipo_entidad = serializers.RegexField(r"^[A-Z_]+$", max_length=40, required=False)
    resultado = serializers.ChoiceField(choices=ResultadoAuditoria.choices, required=False)
    pagina = serializers.IntegerField(min_value=1, max_value=10000, required=False)
