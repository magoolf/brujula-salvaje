"""Operación (DB_HANDOFF v1.1: ops_ejecucion_tarea, idempotencia_peticion, cache_limites,
vista v_medio_uso; ADR-DB-005).

- `cache_limites` (UNLOGGED) no tiene modelo: la usa la caché DatabaseCache de Django y la crea
  la migración 0001_inicial con RunSQL (esquema de createcachetable).
- `idempotencia_peticion` lleva además el constraint trigger diferido trg_idempotencia_completa
  (RunSQL): al confirmar, la fila debe tener la respuesta 2xx (DEC-AUTO-124).
- `MedioUso` es un modelo no gestionado sobre la vista v_medio_uso (RunSQL).
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Cast, Now

from apps.contenido.models import TipoContenido
from apps.medios.campos import PATRON_SHA256, CampoSha256

VENTANA_IDEMPOTENCIA = timedelta(hours=24)
TAMANO_MAXIMO_RESPUESTA = 65_536  # 64 KB (DEC-AUTO-128)


class TareaProgramada(models.TextChoices):
    PURGA_AUDITORIA = "PURGA_AUDITORIA"
    ANONIMIZACION_CUENTAS = "ANONIMIZACION_CUENTAS"
    PURGA_SESIONES = "PURGA_SESIONES"
    PURGA_OPS = "PURGA_OPS"
    REINDEX_BUSQUEDA = "REINDEX_BUSQUEDA"
    VERIFICACION_BUSQUEDA = "VERIFICACION_BUSQUEDA"
    REAPLICAR_ANONIMIZACIONES = "REAPLICAR_ANONIMIZACIONES"
    VIGILAR_CACHE_LIMITES = "VIGILAR_CACHE_LIMITES"


class ResultadoTarea(models.TextChoices):
    EN_CURSO = "EN_CURSO"
    EXITO = "EXITO"
    FALLO = "FALLO"


class OperacionIdempotente(models.TextChoices):
    """Las 11 operationId del contrato que admiten Idempotency-Key (ADR-API-002 §5)."""

    CREAR_DESTINO = "panelCrearDestino"
    CREAR_ITINERARIO = "panelCrearItinerario"
    CREAR_GUIA = "panelCrearGuia"
    CREAR_TIPO_AVENTURA = "panelCrearTipoAventura"
    CREAR_COLECCION = "panelCrearColeccion"
    CREAR_TERMINO_GLOSARIO = "panelCrearTerminoGlosario"
    PUBLICAR_CONTENIDO = "panelPublicarContenido"
    RETIRAR_CONTENIDO = "panelRetirarContenido"
    REACTIVAR_CONTENIDO = "panelReactivarContenido"
    SUBIR_MEDIOS = "panelSubirMedios"
    CREAR_CUENTA = "panelCrearCuenta"


class RolMedioUso(models.TextChoices):
    PORTADA = "PORTADA"
    GALERIA = "GALERIA"
    HERO = "HERO"


class OpsEjecucionTarea(models.Model):
    """Registro de las tareas programadas (sin PII); retención <= 30 días (purgar_ops)."""

    tarea = models.CharField(max_length=40, choices=TareaProgramada.choices)
    iniciado_en = models.DateTimeField(db_default=Now())
    finalizado_en = models.DateTimeField(null=True, blank=True)
    resultado = models.CharField(
        max_length=8,
        choices=ResultadoTarea.choices,
        default=ResultadoTarea.EN_CURSO,
        db_default=ResultadoTarea.EN_CURSO,
    )
    filas_afectadas = models.IntegerField(null=True, blank=True)
    detalle = models.CharField(max_length=500, null=True, blank=True)  # noqa: DJ001

    class Meta:
        db_table = "ops_ejecucion_tarea"
        indexes = [
            models.Index(F("tarea"), F("iniciado_en").desc(), name="ix_ops_tarea_iniciado"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(tarea__in=TareaProgramada.values), name="ck_ops_ejecucion_tarea"
            ),
            models.CheckConstraint(
                condition=Q(resultado__in=ResultadoTarea.values),
                name="ck_ops_ejecucion_resultado",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tarea} #{self.pk}"


class IdempotenciaPeticion(models.Model):
    """Claves Idempotency-Key del panel (CHG-DB-001; DEC-AUTO-123..128).

    El protocolo (misma transacción que el efecto) está en DB_HANDOFF idempotencia_peticion.notas
    y lo implementa el servicio común de las 11 operaciones (TKT-004/005/006).
    """

    cuenta = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="claves_idempotencia",
        # Lo cubre el UNIQUE (cuenta_id, clave).
        db_index=False,
    )
    clave = models.UUIDField()
    operacion = models.CharField(max_length=40, choices=OperacionIdempotente.choices)
    huella_peticion = CampoSha256()
    codigo_http = models.SmallIntegerField(null=True, blank=True)
    recurso_id = models.BigIntegerField(null=True, blank=True)
    cuerpo_respuesta = models.JSONField(null=True, blank=True)
    cuerpo_omitido = models.BooleanField(default=False, db_default=False)
    creado_en = models.DateTimeField(db_default=Now())
    expira_en = models.DateTimeField(db_default=Now() + VENTANA_IDEMPOTENCIA)

    class Meta:
        db_table = "idempotencia_peticion"
        constraints = [
            models.UniqueConstraint(
                fields=["cuenta", "clave"], name="uq_idempotencia_cuenta_clave"
            ),
            models.CheckConstraint(
                condition=Q(operacion__in=OperacionIdempotente.values),
                name="ck_idempotencia_operacion",
            ),
            models.CheckConstraint(
                condition=Q(huella_peticion__regex=PATRON_SHA256), name="ck_idempotencia_huella"
            ),
            models.CheckConstraint(
                condition=Q(codigo_http__isnull=True)
                | Q(codigo_http__gte=200, codigo_http__lte=299),
                name="ck_idempotencia_codigo_http",
            ),
            models.CheckConstraint(
                condition=Q(cuerpo_respuesta__isnull=True)
                | Q(
                    models.lookups.LessThanOrEqual(
                        models.Func(
                            Cast("cuerpo_respuesta", models.TextField()),
                            function="octet_length",
                            output_field=models.IntegerField(),
                        ),
                        TAMANO_MAXIMO_RESPUESTA,
                    )
                ),
                name="ck_idempotencia_tamano_respuesta",
            ),
            models.CheckConstraint(
                condition=Q(expira_en__gt=F("creado_en"))
                & Q(expira_en__lte=F("creado_en") + VENTANA_IDEMPOTENCIA),
                name="ck_idempotencia_expiracion",
            ),
            models.CheckConstraint(
                condition=~Q(cuerpo_omitido=True, cuerpo_respuesta__isnull=False),
                name="ck_idempotencia_omitido",
            ),
            # AC-106, DEC-AUTO-125: la contraseña temporal nunca se persiste.
            models.CheckConstraint(
                condition=~Q(operacion=OperacionIdempotente.CREAR_CUENTA)
                | Q(cuerpo_respuesta__isnull=True, cuerpo_omitido=True),
                name="ck_idempotencia_crear_cuenta",
            ),
        ]

    def __str__(self) -> str:
        return f"Idempotencia {self.operacion} #{self.pk}"


class MedioUso(models.Model):
    """Vista v_medio_uso: usos de un medio como PORTADA, GALERIA o HERO (AP-11, AP-22, AC-117).

    `id` es una clave sintética de la vista ("<ROL>:<id de origen>") porque Django exige PK.
    """

    id = models.CharField(max_length=40, primary_key=True)
    medio = models.ForeignKey(
        "medios.Medio", on_delete=models.DO_NOTHING, db_constraint=False, related_name="usos"
    )
    contenido = models.ForeignKey(
        "contenido.Contenido",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        null=True,
        related_name="+",
    )
    tipo_contenido = models.CharField(max_length=10, choices=TipoContenido.choices, null=True)  # noqa: DJ001
    titulo = models.CharField(max_length=150, null=True)  # noqa: DJ001
    estado_editorial = models.CharField(max_length=10, null=True)  # noqa: DJ001
    rol = models.CharField(max_length=7, choices=RolMedioUso.choices)

    class Meta:
        managed = False
        db_table = "v_medio_uso"

    def __str__(self) -> str:
        return f"{self.rol} del medio #{self.medio_id}"
