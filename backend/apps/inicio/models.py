"""Inicio y sitio (DB_HANDOFF v1.1: config_inicio, destacado_inicio, config_sitio).

config_inicio y config_sitio son singletons (id = 1). config_sitio se siembra en la migración
0001 con un descargo provisional y el Responsable vacío (GAP-004 → marcador en la UI);
config_inicio llega con la carga semilla de contenido (necesita un medio).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Length, Now

from apps.contenido.models import LONGITUD_MAXIMA_TEXTO, TipoContenido

ID_SINGLETON = 1


class SeccionInicio(models.TextChoices):
    DESTINOS = "DESTINOS", "Destinos"
    ITINERARIOS = "ITINERARIOS", "Itinerarios"
    GUIAS = "GUIAS", "Guías"


class ConfigInicio(models.Model):
    """DATA-021 (singleton)."""

    id = models.SmallIntegerField(primary_key=True, default=ID_SINGLETON)
    hero_titular = models.CharField(max_length=80)
    hero_subtitulo = models.CharField(max_length=160)
    hero_medio = models.ForeignKey("medios.Medio", on_delete=models.PROTECT, related_name="+")
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    actualizado_en = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "config_inicio"
        constraints = [
            models.CheckConstraint(condition=Q(id=ID_SINGLETON), name="ck_config_inicio_singleton"),
        ]

    def __str__(self) -> str:
        return "Configuración de inicio"


class DestacadoInicio(models.Model):
    """DATA-022: el tipo del contenido debe corresponder a la sección (CHECK + FK compuesta)."""

    seccion = models.CharField(max_length=12, choices=SeccionInicio.choices)
    contenido = models.ForeignKey(
        "contenido.Contenido", on_delete=models.CASCADE, related_name="destacados"
    )
    tipo_contenido = models.CharField(max_length=10, choices=TipoContenido.choices)
    orden = models.SmallIntegerField(default=0, db_default=0)

    class Meta:
        db_table = "destacado_inicio"
        constraints = [
            models.UniqueConstraint(fields=["seccion", "contenido"], name="uq_destacado_inicio"),
            models.CheckConstraint(
                condition=Q(seccion=SeccionInicio.DESTINOS, tipo_contenido=TipoContenido.DESTINO)
                | Q(seccion=SeccionInicio.ITINERARIOS, tipo_contenido=TipoContenido.ITINERARIO)
                | Q(seccion=SeccionInicio.GUIAS, tipo_contenido=TipoContenido.GUIA),
                name="ck_destacado_inicio_seccion_tipo",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.seccion}: contenido #{self.contenido_id}"


class ConfigSitio(models.Model):
    """DATA-023 (singleton). Los datos del Responsable se publican por obligación legal."""

    id = models.SmallIntegerField(primary_key=True, default=ID_SINGLETON)
    nombre_marca = models.CharField(
        max_length=60, default="Brújula Salvaje", db_default="Brújula Salvaje"
    )
    lema = models.CharField(max_length=120, null=True, blank=True)  # noqa: DJ001
    texto_descargo = models.TextField()
    responsable_nombre = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001
    responsable_identificacion = models.CharField(max_length=40, null=True, blank=True)  # noqa: DJ001
    responsable_domicilio = models.CharField(max_length=200, null=True, blank=True)  # noqa: DJ001
    responsable_canal_atencion = models.CharField(max_length=200, null=True, blank=True)  # noqa: DJ001
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    actualizado_en = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "config_sitio"
        constraints = [
            models.CheckConstraint(condition=Q(id=ID_SINGLETON), name="ck_config_sitio_singleton"),
            models.CheckConstraint(
                condition=Q(
                    models.lookups.GreaterThanOrEqual(Length("texto_descargo"), 1),
                    models.lookups.LessThanOrEqual(Length("texto_descargo"), LONGITUD_MAXIMA_TEXTO),
                ),
                name="ck_config_sitio_texto_descargo",
            ),
        ]

    def __str__(self) -> str:
        return "Configuración del sitio"
