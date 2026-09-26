"""Documento de búsqueda derivado (DB_HANDOFF v1.1: busqueda_documento; ADR-DB-003).

Solo contiene contenido PUBLICADO de tipo DESTINO, ITINERARIO, GUIA o TIPO: el servicio de
publicación hace upsert o delete en la misma transacción (TKT-005). `documento` usa la
configuración de texto `app.es_unaccent` creada en la migración 0001_extensiones_funciones.
"""

from __future__ import annotations

from django.contrib.postgres.indexes import GinIndex, OpClass
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

from apps.contenido.models import TipoContenido

T = TipoContenido
TIPOS_BUSCABLES = [T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO]
CONFIGURACION_TEXTO = "app.es_unaccent"


class BusquedaDocumento(models.Model):
    """Fila derivada por contenido publicado: pesos A título, B resumen, C país/tipos, D cuerpo."""

    contenido = models.OneToOneField(
        "contenido.Contenido", on_delete=models.CASCADE, related_name="documento_busqueda"
    )
    tipo_contenido = models.CharField(max_length=10, choices=TipoContenido.choices)
    slug = models.CharField(max_length=120)
    titulo = models.CharField(max_length=150)
    titulo_norm = models.CharField(max_length=150)
    resumen = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001
    pais_nombre = models.CharField(max_length=80, null=True, blank=True)  # noqa: DJ001
    documento = SearchVectorField()
    actualizado_en = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "busqueda_documento"
        indexes = [
            GinIndex(fields=["documento"], name="ix_busqueda_documento_fts"),
            # Respaldo difuso por similitud (pg_trgm en el esquema ext).
            GinIndex(
                OpClass(F("titulo_norm"), name="gin_trgm_ops"), name="ix_busqueda_titulo_trgm"
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(tipo_contenido__in=[str(t) for t in TIPOS_BUSCABLES]),
                name="ck_busqueda_documento_tipo_contenido",
            ),
        ]

    def __str__(self) -> str:
        return f"Documento de búsqueda del contenido #{self.contenido_id}"
