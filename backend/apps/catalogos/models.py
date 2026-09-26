"""Catálogos (DB_HANDOFF v1.1: region, pais, categoria_guia, licencia, nivel_escala).

Las FK entrantes usan PROTECT. La semilla (7 regiones, 8 categorías, 5 licencias y 9 niveles)
está en la migración de datos 0002_semilla; los países llegan con la carga semilla de contenido.
"""

from __future__ import annotations

from django.db import models
from django.db.models import Q

PATRON_SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"
PATRON_URL = r"^(https?://|/)"


class Continente(models.TextChoices):
    AMERICA = "AMERICA", "América"
    EUROPA = "EUROPA", "Europa"
    AFRICA = "AFRICA", "África"
    ASIA = "ASIA", "Asia"
    OCEANIA = "OCEANIA", "Oceanía"
    ANTARTIDA = "ANTARTIDA", "Antártida"


class Escala(models.TextChoices):
    DIFICULTAD = "DIFICULTAD", "Dificultad"
    PRESUPUESTO = "PRESUPUESTO", "Presupuesto"


class Region(models.Model):
    """DATA-001."""

    nombre = models.CharField(max_length=60, unique=True)
    slug = models.CharField(max_length=60, unique=True)
    continente = models.CharField(max_length=10, choices=Continente.choices)
    orden = models.SmallIntegerField(default=0, db_default=0)
    activo = models.BooleanField(default=True, db_default=True)

    class Meta:
        db_table = "region"
        constraints = [
            models.CheckConstraint(condition=Q(slug__regex=PATRON_SLUG), name="ck_region_slug"),
            models.CheckConstraint(
                condition=Q(continente__in=Continente.values), name="ck_region_continente"
            ),
        ]

    def __str__(self) -> str:
        return self.nombre


class Pais(models.Model):
    """DATA-002."""

    nombre = models.CharField(max_length=80, unique=True)
    slug = models.CharField(max_length=80, unique=True)
    codigo_iso2 = models.CharField(max_length=2, unique=True)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="paises")
    activo = models.BooleanField(default=True, db_default=True)

    class Meta:
        db_table = "pais"
        verbose_name_plural = "países"
        constraints = [
            models.CheckConstraint(condition=Q(slug__regex=PATRON_SLUG), name="ck_pais_slug"),
            models.CheckConstraint(
                condition=Q(codigo_iso2__regex=r"^[A-Z]{2}$"), name="ck_pais_codigo_iso2"
            ),
        ]

    def __str__(self) -> str:
        return self.nombre


class CategoriaGuia(models.Model):
    """DATA-008."""

    nombre = models.CharField(max_length=80, unique=True)
    slug = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField(max_length=400)
    orden = models.SmallIntegerField(default=0, db_default=0)
    activo = models.BooleanField(default=True, db_default=True)

    class Meta:
        db_table = "categoria_guia"
        constraints = [
            models.CheckConstraint(
                condition=Q(slug__regex=PATRON_SLUG), name="ck_categoria_guia_slug"
            ),
        ]

    def __str__(self) -> str:
        return self.nombre


class Licencia(models.Model):
    """DATA-015."""

    codigo = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=120)
    url_texto_legal = models.CharField(max_length=500, null=True, blank=True)  # noqa: DJ001
    requiere_atribucion = models.BooleanField()
    compatible_publicacion = models.BooleanField()
    activo = models.BooleanField(default=True, db_default=True)

    class Meta:
        db_table = "licencia"
        constraints = [
            models.CheckConstraint(
                condition=Q(codigo__regex=r"^[A-Z0-9.-]+$"), name="ck_licencia_codigo"
            ),
            models.CheckConstraint(
                condition=Q(url_texto_legal__isnull=True) | Q(url_texto_legal__regex=PATRON_URL),
                name="ck_licencia_url",
            ),
        ]

    def __str__(self) -> str:
        return self.codigo


class NivelEscala(models.Model):
    """DATA-020 (RULE-012): 5 niveles de dificultad y 4 de presupuesto."""

    escala = models.CharField(max_length=12, choices=Escala.choices)
    nivel = models.SmallIntegerField()
    etiqueta = models.CharField(max_length=40)
    descripcion = models.CharField(max_length=400)

    class Meta:
        db_table = "nivel_escala"
        constraints = [
            models.UniqueConstraint(fields=["escala", "nivel"], name="uq_nivel_escala"),
            models.CheckConstraint(
                condition=Q(escala__in=Escala.values), name="ck_nivel_escala_escala"
            ),
            models.CheckConstraint(
                condition=Q(escala=Escala.DIFICULTAD, nivel__gte=1, nivel__lte=5)
                | Q(escala=Escala.PRESUPUESTO, nivel__gte=1, nivel__lte=4),
                name="ck_nivel_escala_rango",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.escala} {self.nivel}"
