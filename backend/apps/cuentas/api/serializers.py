"""Serializers del panel de acceso y cuentas (contracts/openapi.yaml, tags panel-auth y
panel-cuentas). Solo forma y validación de estructura: sin lógica ni guardado (Regla 02)."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.api.serializers import EntradaEstricta, PaginaMetaSerializer
from apps.cuentas.models import CuentaStaff, EstadoCuenta, RolCuenta
from apps.cuentas.services import Paso

PATRON_CODIGO_MFA = r"^([0-9]{6}|[A-Z0-9]{4}-[A-Z0-9]{4})$"
PATRON_TOTP = r"^[0-9]{6}$"
PATRON_USUARIO_ALTA = r"^[a-z0-9._-]{3,40}$"


# ------------------------------------------------------------------ Entradas (panel-auth)
class LoginEntradaSerializer(EntradaEstricta):
    usuario = serializers.CharField(min_length=1, max_length=40, trim_whitespace=False)
    contrasena = serializers.CharField(
        min_length=1, max_length=128, write_only=True, trim_whitespace=False
    )
    siguiente = serializers.CharField(
        max_length=2000, required=False, allow_null=True, allow_blank=True
    )


class MfaVerificacionEntradaSerializer(EntradaEstricta):
    codigo = serializers.RegexField(PATRON_CODIGO_MFA, write_only=True)


class MfaCodigoEntradaSerializer(EntradaEstricta):
    codigo = serializers.RegexField(PATRON_TOTP, write_only=True)


class MfaDesactivacionEntradaSerializer(EntradaEstricta):
    contrasena = serializers.CharField(
        min_length=1, max_length=128, write_only=True, trim_whitespace=False
    )
    codigo = serializers.RegexField(PATRON_CODIGO_MFA, write_only=True)


class CambioContrasenaEntradaSerializer(EntradaEstricta):
    contrasena_actual = serializers.CharField(
        min_length=1, max_length=128, write_only=True, trim_whitespace=False
    )
    contrasena_nueva = serializers.CharField(
        min_length=12, max_length=128, write_only=True, trim_whitespace=False
    )


class AutorizacionEntradaSerializer(EntradaEstricta):
    decision = serializers.ChoiceField(choices=["AUTORIZO", "NO_AUTORIZO"])
    version_politica = serializers.CharField(max_length=20)


# ------------------------------------------------------------------ Salidas (panel-auth)
class SesionEstadoSerializer(serializers.Serializer[dict[str, Any]]):
    usuario = serializers.CharField(max_length=40)
    nombre_visible = serializers.CharField(max_length=100)
    rol = serializers.ChoiceField(choices=RolCuenta.choices)
    paso_pendiente = serializers.ChoiceField(choices=[p.value for p in Paso])
    mfa_activo = serializers.BooleanField()
    mfa_obligatorio = serializers.BooleanField()
    expira_inactividad_en = serializers.DateTimeField()
    expira_absoluta_en = serializers.DateTimeField()
    redireccion = serializers.RegexField(r"^/panel(/[A-Za-z0-9._~%/-]*)?$")


class MfaActivacionInicioSerializer(serializers.Serializer[dict[str, str]]):
    otpauth_uri = serializers.RegexField(r"^otpauth://totp/", max_length=500)
    clave_secreta = serializers.RegexField(r"^[A-Z2-7]{16,64}$")


class CodigosRecuperacionSerializer(serializers.Serializer[dict[str, list[str]]]):
    codigos = serializers.ListField(
        child=serializers.RegexField(r"^[A-Z0-9]{4}-[A-Z0-9]{4}$"), min_length=10, max_length=10
    )


class AutorizacionVigenteSerializer(serializers.Serializer[dict[str, Any]]):
    version_politica = serializers.CharField(max_length=20)
    vigente_desde = serializers.DateField()
    resumen_finalidad = serializers.CharField(max_length=2000)
    url_politica = serializers.ChoiceField(choices=["/politica-de-tratamiento-de-datos"])
    otorgada_en = serializers.DateTimeField(allow_null=True, required=False)
    version_otorgada = serializers.CharField(max_length=20, allow_null=True, required=False)


# ------------------------------------------------------------------ Cuentas (panel-cuentas)
class CuentaSerializer(serializers.ModelSerializer[CuentaStaff]):
    etiqueta = serializers.SerializerMethodField()
    ultimo_acceso_en = serializers.DateTimeField(source="last_login", allow_null=True)

    class Meta:
        model = CuentaStaff
        fields = [
            "id",
            "usuario",
            "nombre_visible",
            "etiqueta",
            "rol",
            "estado",
            "mfa_activo",
            "debe_cambiar_credencial",
            "ultimo_acceso_en",
            "autorizacion_otorgada_en",
            "autorizacion_version_politica",
            "creado_en",
            "desactivado_en",
            "anonimizado_en",
        ]
        read_only_fields = fields

    def get_etiqueta(self, cuenta: CuentaStaff) -> str:
        return cuenta.usuario or f"Cuenta anonimizada #{cuenta.pk}"


class CuentaCreacionEntradaSerializer(EntradaEstricta):
    usuario = serializers.RegexField(PATRON_USUARIO_ALTA)
    nombre_visible = serializers.CharField(min_length=1, max_length=100)
    rol = serializers.ChoiceField(choices=RolCuenta.choices)


class CuentaActualizacionEntradaSerializer(EntradaEstricta):
    nombre_visible = serializers.CharField(min_length=1, max_length=100, required=False)
    rol = serializers.ChoiceField(choices=RolCuenta.choices, required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs:
            raise serializers.ValidationError("Indica al menos un campo.")
        return attrs


class CuentaConCredencialTemporalSerializer(serializers.Serializer[dict[str, Any]]):
    cuenta = CuentaSerializer()
    contrasena_temporal = serializers.CharField(min_length=16, max_length=64)


class PaginaCuentaSerializer(PaginaMetaSerializer):
    resultados = CuentaSerializer(many=True)


class FiltroCuentasSerializer(serializers.Serializer[dict[str, Any]]):
    estado = serializers.ChoiceField(choices=EstadoCuenta.choices, required=False)
    rol = serializers.ChoiceField(choices=RolCuenta.choices, required=False)
    pagina = serializers.IntegerField(min_value=1, max_value=10000, required=False)
