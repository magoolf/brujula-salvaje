"""Auditoría inmutable y revisiones (DB_HANDOFF v1.1: evento_auditoria, revision_contenido).

Inmutabilidad (ADR-DB-004 §1, DEC-AUTO-091), creada en la migración 0002_inmutabilidad:
- `app_rw` solo tiene SELECT e INSERT en ambas tablas;
- trigger `trg_auditoria_inmutable` en evento_auditoria (UPDATE solo para seudonimizar, DELETE
  solo de eventos con más de 365 días, TRUNCATE nunca);
- funciones SECURITY DEFINER `app.fn_auditoria_purgar()` y `app.fn_auditoria_seudonimizar(id)`.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F, Func, Q
from django.db.models.functions import Now

from apps.auditoria.campos import CampoCidr
from apps.contenido.models import TipoContenido


class AccionAuditoria(models.TextChoices):
    """Las 28 acciones de BLUEPRINT §18.4 DATA-025."""

    LOGIN_OK = "LOGIN_OK"
    LOGIN_FALLIDO = "LOGIN_FALLIDO"
    BLOQUEO = "BLOQUEO"
    LOGOUT = "LOGOUT"
    AUTORIZACION_ACEPTADA = "AUTORIZACION_ACEPTADA"
    CAMBIO_CREDENCIAL = "CAMBIO_CREDENCIAL"
    MFA_ACTIVAR = "MFA_ACTIVAR"
    MFA_DESACTIVAR = "MFA_DESACTIVAR"
    CREAR = "CREAR"
    EDITAR = "EDITAR"
    PUBLICAR = "PUBLICAR"
    ACTUALIZAR_PUBLICACION = "ACTUALIZAR_PUBLICACION"
    RETIRAR = "RETIRAR"
    REACTIVAR = "REACTIVAR"
    ELIMINAR_BORRADOR = "ELIMINAR_BORRADOR"
    RESTAURAR_REVISION = "RESTAURAR_REVISION"
    SUBIR_MEDIO = "SUBIR_MEDIO"
    EDITAR_MEDIO = "EDITAR_MEDIO"
    RETIRAR_MEDIO = "RETIRAR_MEDIO"
    CONFIG_INICIO = "CONFIG_INICIO"
    CONFIG_SITIO = "CONFIG_SITIO"
    TAXONOMIA = "TAXONOMIA"
    CUENTA_CREAR = "CUENTA_CREAR"
    CUENTA_ROL = "CUENTA_ROL"
    CUENTA_RESTABLECER = "CUENTA_RESTABLECER"
    CUENTA_DESACTIVAR = "CUENTA_DESACTIVAR"
    CUENTA_REACTIVAR = "CUENTA_REACTIVAR"
    CUENTA_ANONIMIZAR = "CUENTA_ANONIMIZAR"


# Solo los eventos de autenticación pueden llevar la IP truncada (REQ-057).
ACCIONES_CON_IP = [
    AccionAuditoria.LOGIN_OK,
    AccionAuditoria.LOGIN_FALLIDO,
    AccionAuditoria.BLOQUEO,
    AccionAuditoria.LOGOUT,
]


class ResultadoAuditoria(models.TextChoices):
    EXITO = "EXITO", "Éxito"
    FALLO = "FALLO", "Fallo"


class MotivoRevision(models.TextChoices):
    PUBLICACION = "PUBLICACION", "Publicación"
    ACTUALIZACION = "ACTUALIZACION", "Actualización"
    RETIRO = "RETIRO", "Retiro"
    RESTAURACION = "RESTAURACION", "Restauración"


def _familia(campo: str) -> Func:
    return Func(F(campo), function="family", output_field=models.IntegerField())


def _mascara(campo: str) -> Func:
    return Func(F(campo), function="masklen", output_field=models.IntegerField())


class EventoAuditoria(models.Model):
    """DATA-025 (solo inserción). `entidad_id` sin FK: la auditoría sobrevive al borrador."""

    ocurrido_en = models.DateTimeField(db_default=Now())
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        # Lo cubre el índice (actor_id, ocurrido_en DESC).
        db_index=False,
    )
    # 'desconocido' si el usuario no existe; 'sistema' en tareas y semilla (ADR-DB-004 §1.5).
    actor_etiqueta = models.CharField(max_length=60)
    accion = models.CharField(max_length=30, choices=AccionAuditoria.choices)
    resultado = models.CharField(max_length=5, choices=ResultadoAuditoria.choices)
    tipo_entidad = models.CharField(max_length=20, null=True, blank=True)  # noqa: DJ001
    entidad_id = models.BigIntegerField(null=True, blank=True)
    entidad_titulo = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001
    # Solo nombres de campos, nunca valores.
    campos_cambiados = ArrayField(models.CharField(max_length=60), null=True, blank=True)
    ip_truncada = CampoCidr(null=True, blank=True)

    class Meta:
        db_table = "evento_auditoria"
        indexes = [
            models.Index(F("ocurrido_en").desc(), name="ix_evento_auditoria_ocurrido"),
            models.Index(F("actor"), F("ocurrido_en").desc(), name="ix_evento_auditoria_actor"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(accion__in=AccionAuditoria.values), name="ck_evento_auditoria_accion"
            ),
            models.CheckConstraint(
                condition=Q(resultado__in=ResultadoAuditoria.values),
                name="ck_evento_auditoria_resultado",
            ),
            # DEC-AUTO-092: solo redes /24 (IPv4) o /48 (IPv6).
            models.CheckConstraint(
                condition=Q(ip_truncada__isnull=True)
                | Q(
                    models.lookups.Exact(_familia("ip_truncada"), 4),
                    models.lookups.Exact(_mascara("ip_truncada"), 24),
                )
                | Q(
                    models.lookups.Exact(_familia("ip_truncada"), 6),
                    models.lookups.Exact(_mascara("ip_truncada"), 48),
                ),
                name="ck_evento_auditoria_ip_mascara",
            ),
            models.CheckConstraint(
                condition=Q(ip_truncada__isnull=True) | Q(accion__in=ACCIONES_CON_IP),
                name="ck_evento_auditoria_ip_accion",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.accion} #{self.pk}"


class RevisionContenido(models.Model):
    """DATA-026 (inmutable). ON DELETE RESTRICT: lo publicado alguna vez no se borra."""

    contenido = models.ForeignKey(
        "contenido.Contenido", on_delete=models.PROTECT, related_name="revisiones"
    )
    tipo_contenido = models.CharField(max_length=10, choices=TipoContenido.choices)
    numero_revision = models.IntegerField()
    motivo = models.CharField(max_length=14, choices=MotivoRevision.choices)
    # Todos los campos y relaciones del contenido; ids de medios/cuentas, nunca PII del staff.
    instantanea = models.JSONField()
    # NULL = semilla (DEC-AUTO-095).
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    creado_en = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "revision_contenido"
        constraints = [
            models.UniqueConstraint(
                fields=["contenido", "numero_revision"], name="uq_revision_contenido_numero"
            ),
            models.CheckConstraint(
                condition=Q(numero_revision__gte=1), name="ck_revision_contenido_numero"
            ),
            models.CheckConstraint(
                condition=Q(motivo__in=MotivoRevision.values), name="ck_revision_contenido_motivo"
            ),
        ]

    def __str__(self) -> str:
        return f"Revisión {self.numero_revision} del contenido #{self.contenido_id}"
