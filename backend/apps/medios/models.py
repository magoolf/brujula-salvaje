"""Medios (DB_HANDOFF v1.1: medio, medio_derivado; BLUEPRINT DATA-016, STATE-002).

Los archivos viven en el sistema de archivos (fuera de la BD); aquí solo la clave de
almacenamiento generada por el sistema, las dimensiones, las huellas y los metadatos.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Cast, Greatest, Now

from apps.catalogos.models import PATRON_URL, Licencia
from apps.medios.campos import PATRON_SHA256, CampoSha256

PESO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB (DEC-AUTO-044)
PIXELES_MAXIMOS = 40_000_000  # 40 MP (DEC-AUTO-044)
LADO_MAYOR_MINIMO_PX = 1200


class FormatoOrigen(models.TextChoices):
    JPEG = "JPEG", "JPEG"
    PNG = "PNG", "PNG"
    WEBP = "WEBP", "WebP"


class FormatoDerivado(models.TextChoices):
    AVIF = "AVIF", "AVIF"
    WEBP = "WEBP", "WebP"
    JPEG = "JPEG", "JPEG"


class EstadoMedio(models.TextChoices):
    PENDIENTE_METADATOS = "PENDIENTE_METADATOS", "Pendiente de metadatos"
    DISPONIBLE = "DISPONIBLE", "Disponible"
    RETIRADO = "RETIRADO", "Retirado"


class Medio(models.Model):
    """DATA-016. RECHAZADO nunca se persiste (STATE-002)."""

    archivo_saneado_ruta = models.CharField(max_length=255, unique=True)
    formato_origen = models.CharField(max_length=4, choices=FormatoOrigen.choices)
    ancho_px = models.IntegerField()
    alto_px = models.IntegerField()
    peso_bytes = models.IntegerField()
    huella_sha256 = CampoSha256(unique=True)
    sha256_saneado = CampoSha256()
    titulo_interno = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001
    texto_alternativo = models.CharField(max_length=250, null=True, blank=True)  # noqa: DJ001
    pie_de_foto = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001
    autor_credito = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001
    fuente_url = models.CharField(max_length=500, null=True, blank=True)  # noqa: DJ001
    licencia = models.ForeignKey(
        Licencia, on_delete=models.PROTECT, null=True, blank=True, related_name="medios"
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoMedio.choices,
        default=EstadoMedio.PENDIENTE_METADATOS,
        db_default=EstadoMedio.PENDIENTE_METADATOS,
    )
    # NULL = carga semilla (DEC-AUTO-095).
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    subido_en = models.DateTimeField(db_default=Now())
    actualizado_en = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "medio"
        indexes = [
            # Listado paginado del panel por estado (AP-22).
            models.Index(F("estado"), F("subido_en").desc(), name="ix_medio_estado_subido"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(formato_origen__in=FormatoOrigen.values),
                name="ck_medio_formato_origen",
            ),
            models.CheckConstraint(condition=Q(ancho_px__gt=0), name="ck_medio_ancho"),
            models.CheckConstraint(condition=Q(alto_px__gt=0), name="ck_medio_alto"),
            models.CheckConstraint(
                condition=Q(peso_bytes__gte=1, peso_bytes__lte=PESO_MAXIMO_BYTES),
                name="ck_medio_peso",
            ),
            models.CheckConstraint(
                condition=Q(huella_sha256__regex=PATRON_SHA256), name="ck_medio_huella"
            ),
            models.CheckConstraint(
                condition=Q(sha256_saneado__regex=PATRON_SHA256), name="ck_medio_sha256_saneado"
            ),
            models.CheckConstraint(
                condition=Q(fuente_url__isnull=True) | Q(fuente_url__regex=PATRON_URL),
                name="ck_medio_fuente_url",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=EstadoMedio.values), name="ck_medio_estado"
            ),
            models.CheckConstraint(
                condition=models.lookups.LessThanOrEqual(
                    Cast("ancho_px", models.BigIntegerField()) * F("alto_px"), PIXELES_MAXIMOS
                ),
                name="ck_medio_megapixeles",
            ),
            models.CheckConstraint(
                condition=models.lookups.GreaterThanOrEqual(
                    Greatest("ancho_px", "alto_px"), LADO_MAYOR_MINIMO_PX
                ),
                name="ck_medio_lado_mayor",
            ),
            # RULE-005: un medio DISPONIBLE tiene alt, crédito y licencia.
            models.CheckConstraint(
                condition=~Q(estado=EstadoMedio.DISPONIBLE)
                | Q(
                    texto_alternativo__isnull=False,
                    autor_credito__isnull=False,
                    licencia__isnull=False,
                ),
                name="ck_medio_disponible",
            ),
        ]

    def __str__(self) -> str:
        return f"Medio #{self.pk}"


class MedioDerivado(models.Model):
    """Derivados servidos al público (srcset); DEC-AUTO-084."""

    medio = models.ForeignKey(Medio, on_delete=models.CASCADE, related_name="derivados")
    formato = models.CharField(max_length=4, choices=FormatoDerivado.choices)
    ancho_px = models.IntegerField()
    alto_px = models.IntegerField()
    ruta = models.CharField(max_length=255, unique=True)
    peso_bytes = models.IntegerField()
    sha256 = CampoSha256()

    class Meta:
        db_table = "medio_derivado"
        constraints = [
            models.UniqueConstraint(
                fields=["medio", "formato", "ancho_px"], name="uq_medio_derivado"
            ),
            models.CheckConstraint(
                condition=Q(formato__in=FormatoDerivado.values), name="ck_medio_derivado_formato"
            ),
            models.CheckConstraint(condition=Q(ancho_px__gt=0), name="ck_medio_derivado_ancho"),
            models.CheckConstraint(condition=Q(alto_px__gt=0), name="ck_medio_derivado_alto"),
            models.CheckConstraint(condition=Q(peso_bytes__gt=0), name="ck_medio_derivado_peso"),
            models.CheckConstraint(
                condition=Q(sha256__regex=PATRON_SHA256), name="ck_medio_derivado_sha256"
            ),
        ]

    def __str__(self) -> str:
        return f"Derivado {self.formato} {self.ancho_px}px del medio #{self.medio_id}"
