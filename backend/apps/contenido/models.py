"""Contenido editorial: supertipo, subtipos 1:1 y relaciones polimórficas (ADR-DB-002).

Fuente: DB_HANDOFF v1.1 (tablas contenido .. relacion_contenido), BLUEPRINT §18.3/§18.4.

- Supertipo `contenido` (ATR-COMUN) + subtipos con PK = contenido_id (OneToOneField explícito,
  sin herencia multi-tabla implícita). Cada subtipo y cada relación polimórfica guarda
  `tipo_contenido` y la FK compuesta (contenido_id, tipo_contenido) → contenido(id, tipo), que
  Django no modela: la crea la migración 0002_integridad_sql (RunSQL), junto con la FK compuesta
  DEFERRABLE de tipo_principal y el trigger trg_contenido_guardas.
- Los atributos obligatorios para publicar son NULL en la BD; los garantiza el servicio de
  publicación (TKT-005) y la BD refuerza con CHECK por estado los de la fila de contenido.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F, Func, Q
from django.db.models.functions import Length, Now

from apps.catalogos.models import PATRON_SLUG, PATRON_URL

LONGITUD_MAXIMA_TEXTO = 100_000  # DEC-AUTO-097 (THREAT-009)
MESES = list(range(1, 13))


class TipoContenido(models.TextChoices):
    DESTINO = "DESTINO", "Destino"
    ITINERARIO = "ITINERARIO", "Itinerario"
    GUIA = "GUIA", "Guía"
    TIPO = "TIPO", "Tipo de aventura"
    COLECCION = "COLECCION", "Colección"
    TERMINO = "TERMINO", "Término de glosario"
    PAGINA = "PAGINA", "Página institucional"


class EstadoEditorial(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    PUBLICADO = "PUBLICADO", "Publicado"
    RETIRADO = "RETIRADO", "Retirado"


class ClavePagina(models.TextChoices):
    ACERCA_DE = "ACERCA_DE", "Acerca de"
    POLITICA_DATOS = "POLITICA_DATOS", "Política de datos"
    POLITICA_COOKIES = "POLITICA_COOKIES", "Política de cookies"
    AVISO_LEGAL = "AVISO_LEGAL", "Aviso legal"


T = TipoContenido
# Tipos admitidos por cada relación polimórfica (ADR-DB-002 §3).
TIPOS_ELEMENTO_COLECCION = [T.DESTINO, T.ITINERARIO]
TIPOS_CON_TERMINOS = [T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO]
TIPOS_CON_GALERIA = [T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO, T.COLECCION]
TIPOS_RELACIONABLES = TIPOS_CON_GALERIA
TIPOS_SIN_PORTADA = [T.TERMINO, T.PAGINA]


def normalizar(expresion: str | F) -> Func:
    """app.f_normalizar(x): minúsculas, sin tildes y espacios colapsados (ADR-DB-003)."""
    return Func(
        expresion, function="app.f_normalizar", output_field=models.CharField(max_length=150)
    )


def ck_longitud(campo: str, tabla: str) -> models.CheckConstraint:
    """CHECK char_length(campo) <= 100000 para texto enriquecido (NULL permitido)."""
    return models.CheckConstraint(
        condition=Q(**{f"{campo}__isnull": True})
        | Q(models.lookups.LessThanOrEqual(Length(campo), LONGITUD_MAXIMA_TEXTO)),
        name=f"ck_{tabla}_{campo}_longitud",
    )


def ck_tipo_constante(tabla: str, tipo: str) -> models.CheckConstraint:
    return models.CheckConstraint(
        condition=Q(tipo_contenido=tipo), name=f"ck_{tabla}_tipo_contenido"
    )


def ck_tipos(
    tabla: str, tipos: list[TipoContenido], campo: str = "tipo_contenido"
) -> models.CheckConstraint:
    return models.CheckConstraint(
        condition=Q(**{f"{campo}__in": [str(t) for t in tipos]}), name=f"ck_{tabla}_{campo}"
    )


def ck_rango(tabla: str, campo: str, minimo: int, maximo: int) -> models.CheckConstraint:
    return models.CheckConstraint(
        condition=Q(**{f"{campo}__isnull": True})
        | Q(**{f"{campo}__gte": minimo, f"{campo}__lte": maximo}),
        name=f"ck_{tabla}_{campo}",
    )


def ck_no_negativo(tabla: str, campo: str) -> models.CheckConstraint:
    return models.CheckConstraint(
        condition=Q(**{f"{campo}__isnull": True}) | Q(**{f"{campo}__gte": 0}),
        name=f"ck_{tabla}_{campo}",
    )


def campo_tipo_constante(tipo: str) -> models.CharField:  # type: ignore[type-arg]
    return models.CharField(max_length=10, default=tipo, db_default=tipo, editable=False)


# ---------------------------------------------------------------------------
# Supertipo
# ---------------------------------------------------------------------------
class Contenido(models.Model):
    """ATR-COMUN (§18.3). Bloqueo optimista con `version` (AC-110)."""

    tipo = models.CharField(max_length=10, choices=TipoContenido.choices)
    slug = models.CharField(max_length=120)
    titulo = models.CharField(max_length=150, db_collation="es-x-icu")
    titulo_norm = models.GeneratedField(
        expression=normalizar("titulo"),
        output_field=models.CharField(max_length=150),
        db_persist=True,
    )
    estado_editorial = models.CharField(
        max_length=10,
        choices=EstadoEditorial.choices,
        default=EstadoEditorial.BORRADOR,
        db_default=EstadoEditorial.BORRADOR,
    )
    fecha_ultima_revision = models.DateField(null=True, blank=True)
    seo_titulo = models.CharField(max_length=70, null=True, blank=True)  # noqa: DJ001
    seo_descripcion = models.CharField(max_length=160, null=True, blank=True)  # noqa: DJ001
    primera_publicacion_en = models.DateTimeField(null=True, blank=True)
    publicado_actualizado_en = models.DateTimeField(null=True, blank=True)
    retirado_en = models.DateTimeField(null=True, blank=True)
    motivo_retiro = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001
    portada = models.ForeignKey(
        "medios.Medio", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # NULL = carga semilla (DEC-AUTO-095).
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    creado_en = models.DateTimeField(db_default=Now())
    actualizado_en = models.DateTimeField(db_default=Now())
    version = models.IntegerField(default=1, db_default=1)

    class Meta:
        db_table = "contenido"
        indexes = [
            # Listados A-Z paginados (AP-02, AP-05, AP-13) con collation es-x-icu.
            models.Index(
                fields=["tipo", "titulo"],
                condition=Q(estado_editorial=EstadoEditorial.PUBLICADO),
                name="ix_contenido_pub_titulo",
            ),
            # Relleno del inicio (AP-01, RULE-016) y guías recientes (AP-07).
            models.Index(
                F("tipo"),
                F("fecha_ultima_revision").desc(),
                condition=Q(estado_editorial=EstadoEditorial.PUBLICADO),
                name="ix_contenido_pub_revision",
            ),
        ]
        constraints = [
            ck_tipos("contenido", list(TipoContenido), campo="tipo"),
            models.CheckConstraint(condition=Q(slug__regex=PATRON_SLUG), name="ck_contenido_slug"),
            models.CheckConstraint(
                condition=Q(estado_editorial__in=EstadoEditorial.values),
                name="ck_contenido_estado_editorial",
            ),
            models.CheckConstraint(condition=Q(version__gte=1), name="ck_contenido_version"),
            # RULE-008 (los slugs de los retirados quedan reservados: la fila no se borra).
            models.UniqueConstraint(fields=["tipo", "slug"], name="uq_contenido_tipo_slug"),
            # RULE-026, DEC-AUTO-098: unicidad insensible a mayúsculas, tildes y espacios.
            models.UniqueConstraint(
                fields=["tipo", "titulo_norm"], name="uq_contenido_tipo_titulo_norm"
            ),
            # Destino de las FK compuestas (ADR-DB-002).
            models.UniqueConstraint(fields=["id", "tipo"], name="uq_contenido_id_tipo"),
            # RULE-027: descripción SEO única (normalizada) entre los publicados.
            models.UniqueConstraint(
                normalizar("seo_descripcion"),
                condition=Q(
                    estado_editorial=EstadoEditorial.PUBLICADO, seo_descripcion__isnull=False
                ),
                name="uq_contenido_seo_publicado",
            ),
            models.CheckConstraint(
                condition=~Q(estado_editorial=EstadoEditorial.PUBLICADO)
                | Q(
                    fecha_ultima_revision__isnull=False,
                    primera_publicacion_en__isnull=False,
                    publicado_actualizado_en__isnull=False,
                ),
                name="ck_contenido_publicado_fechas",
            ),
            models.CheckConstraint(
                condition=~Q(estado_editorial=EstadoEditorial.PUBLICADO)
                | Q(tipo=T.TERMINO)
                | Q(seo_descripcion__isnull=False),
                name="ck_contenido_publicado_seo",
            ),
            models.CheckConstraint(
                condition=~Q(estado_editorial=EstadoEditorial.PUBLICADO)
                | Q(tipo__in=TIPOS_SIN_PORTADA)
                | Q(portada__isnull=False),
                name="ck_contenido_publicado_portada",
            ),
            models.CheckConstraint(
                condition=~Q(estado_editorial=EstadoEditorial.RETIRADO)
                | Q(
                    retirado_en__isnull=False,
                    motivo_retiro__isnull=False,
                    primera_publicacion_en__isnull=False,
                ),
                name="ck_contenido_retirado",
            ),
            # AC-033: las páginas institucionales no se retiran.
            models.CheckConstraint(
                condition=~Q(tipo=T.PAGINA) | ~Q(estado_editorial=EstadoEditorial.RETIRADO),
                name="ck_contenido_pagina_no_retirable",
            ),
            models.CheckConstraint(
                condition=~Q(tipo__in=TIPOS_SIN_PORTADA) | Q(portada__isnull=True),
                name="ck_contenido_sin_portada",
            ),
            models.CheckConstraint(
                condition=~Q(tipo=T.TERMINO)
                | Q(seo_titulo__isnull=True, seo_descripcion__isnull=True),
                name="ck_contenido_termino_sin_seo",
            ),
            models.CheckConstraint(
                condition=Q(publicado_actualizado_en__isnull=True)
                | Q(primera_publicacion_en__lte=F("publicado_actualizado_en")),
                name="ck_contenido_orden_publicacion",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tipo} {self.slug}"


# ---------------------------------------------------------------------------
# Subtipos
# ---------------------------------------------------------------------------
class TipoAventura(models.Model):
    """DATA-003."""

    contenido = models.OneToOneField(
        Contenido, on_delete=models.CASCADE, primary_key=True, related_name="tipo_aventura"
    )
    tipo_contenido = campo_tipo_constante(T.TIPO)
    descripcion = models.TextField(null=True, blank=True)  # noqa: DJ001
    resumen = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001
    nivel_exigencia = models.SmallIntegerField(null=True, blank=True)
    orden = models.SmallIntegerField(default=0, db_default=0)

    class Meta:
        db_table = "tipo_aventura"
        constraints = [
            ck_tipo_constante("tipo_aventura", T.TIPO),
            ck_longitud("descripcion", "tipo_aventura"),
            ck_rango("tipo_aventura", "nivel_exigencia", 1, 5),
        ]

    def __str__(self) -> str:
        return f"Tipo de aventura #{self.pk}"


class ChecklistItem(models.Model):
    """DATA-004."""

    tipo_aventura = models.ForeignKey(
        TipoAventura, on_delete=models.CASCADE, related_name="checklist"
    )
    texto = models.CharField(max_length=200)
    grupo = models.CharField(max_length=60, null=True, blank=True)  # noqa: DJ001
    esencial = models.BooleanField(default=False, db_default=False)
    orden = models.SmallIntegerField(default=0, db_default=0)

    class Meta:
        db_table = "checklist_item"
        constraints = [
            models.UniqueConstraint(fields=["tipo_aventura", "texto"], name="uq_checklist_item"),
        ]

    def __str__(self) -> str:
        return self.texto


class Destino(models.Model):
    """DATA-005."""

    contenido = models.OneToOneField(
        Contenido, on_delete=models.CASCADE, primary_key=True, related_name="destino"
    )
    tipo_contenido = campo_tipo_constante(T.DESTINO)
    pais = models.ForeignKey(
        "catalogos.Pais", on_delete=models.PROTECT, null=True, blank=True, related_name="destinos"
    )
    resumen = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001
    descripcion_experta = models.TextField(null=True, blank=True)  # noqa: DJ001
    tipos_aventura: models.ManyToManyField[TipoAventura, models.Model] = models.ManyToManyField(
        TipoAventura, through="DestinoTipoAventura", related_name="destinos"
    )
    tipo_principal = models.ForeignKey(
        TipoAventura,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="destinos_principales",
    )
    dificultad = models.SmallIntegerField(null=True, blank=True)
    meses_mejor_epoca = ArrayField(models.SmallIntegerField(), default=list, db_default=[])
    duracion_min_dias = models.SmallIntegerField(null=True, blank=True)
    duracion_max_dias = models.SmallIntegerField(null=True, blank=True)
    nivel_presupuesto = models.SmallIntegerField(null=True, blank=True)
    clima = models.TextField(null=True, blank=True)  # noqa: DJ001
    altitud_max_m = models.IntegerField(null=True, blank=True)
    como_llegar = models.TextField(null=True, blank=True)  # noqa: DJ001
    seguridad_riesgos = models.TextField(null=True, blank=True)  # noqa: DJ001
    sostenibilidad = models.TextField(null=True, blank=True)  # noqa: DJ001
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        db_table = "destino"
        constraints = [
            ck_tipo_constante("destino", T.DESTINO),
            ck_longitud("descripcion_experta", "destino"),
            ck_longitud("clima", "destino"),
            ck_longitud("como_llegar", "destino"),
            ck_longitud("seguridad_riesgos", "destino"),
            ck_longitud("sostenibilidad", "destino"),
            ck_rango("destino", "dificultad", 1, 5),
            ck_rango("destino", "duracion_min_dias", 1, 90),
            ck_rango("destino", "duracion_max_dias", 1, 90),
            ck_rango("destino", "nivel_presupuesto", 1, 4),
            ck_rango("destino", "altitud_max_m", -500, 9000),
            ck_rango("destino", "latitud", -90, 90),
            ck_rango("destino", "longitud", -180, 180),
            # RULE-011: meses 1..12 sin repetir.
            models.CheckConstraint(
                condition=Q(meses_mejor_epoca__contained_by=MESES)
                & Q(
                    Func(
                        F("meses_mejor_epoca"),
                        function="app.f_sin_duplicados",
                        output_field=models.BooleanField(),
                    )
                ),
                name="ck_destino_meses_mejor_epoca",
            ),
            models.CheckConstraint(
                condition=Q(duracion_min_dias__isnull=True)
                | Q(duracion_max_dias__isnull=True)
                | Q(duracion_min_dias__lte=F("duracion_max_dias")),
                name="ck_destino_duracion",
            ),
            # RULE-023: coordenadas completas o ninguna.
            models.CheckConstraint(
                condition=Q(latitud__isnull=True, longitud__isnull=True)
                | Q(latitud__isnull=False, longitud__isnull=False),
                name="ck_destino_coordenadas",
            ),
        ]

    def __str__(self) -> str:
        return f"Destino #{self.pk}"


class DestinoTipoAventura(models.Model):
    """DATA-005.tipos_aventura (N:M). Destino de la FK compuesta de tipo_principal."""

    destino = models.ForeignKey(Destino, on_delete=models.CASCADE, related_name="+")
    tipo_aventura = models.ForeignKey(TipoAventura, on_delete=models.PROTECT, related_name="+")

    class Meta:
        db_table = "destino_tipo_aventura"
        constraints = [
            models.UniqueConstraint(
                fields=["destino", "tipo_aventura"], name="uq_destino_tipo_aventura"
            ),
        ]

    def __str__(self) -> str:
        return f"Destino #{self.destino_id} - tipo #{self.tipo_aventura_id}"


class Itinerario(models.Model):
    """DATA-006."""

    contenido = models.OneToOneField(
        Contenido, on_delete=models.CASCADE, primary_key=True, related_name="itinerario"
    )
    tipo_contenido = campo_tipo_constante(T.ITINERARIO)
    destino = models.ForeignKey(
        Destino, on_delete=models.PROTECT, null=True, blank=True, related_name="itinerarios"
    )
    resumen = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001
    duracion_dias = models.SmallIntegerField(null=True, blank=True)
    dificultad = models.SmallIntegerField(null=True, blank=True)
    tipos_aventura: models.ManyToManyField[TipoAventura, models.Model] = models.ManyToManyField(
        TipoAventura, through="ItinerarioTipoAventura", related_name="itinerarios"
    )
    distancia_total_km = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    desnivel_acumulado_m = models.IntegerField(null=True, blank=True)
    riesgos_seguridad = models.TextField(null=True, blank=True)  # noqa: DJ001

    class Meta:
        db_table = "itinerario"
        constraints = [
            ck_tipo_constante("itinerario", T.ITINERARIO),
            ck_rango("itinerario", "duracion_dias", 1, 60),
            ck_rango("itinerario", "dificultad", 1, 5),
            ck_no_negativo("itinerario", "distancia_total_km"),
            ck_no_negativo("itinerario", "desnivel_acumulado_m"),
            ck_longitud("riesgos_seguridad", "itinerario"),
        ]

    def __str__(self) -> str:
        return f"Itinerario #{self.pk}"


class ItinerarioTipoAventura(models.Model):
    """DATA-006.tipos_aventura (N:M)."""

    itinerario = models.ForeignKey(Itinerario, on_delete=models.CASCADE, related_name="+")
    tipo_aventura = models.ForeignKey(TipoAventura, on_delete=models.PROTECT, related_name="+")

    class Meta:
        db_table = "itinerario_tipo_aventura"
        constraints = [
            models.UniqueConstraint(
                fields=["itinerario", "tipo_aventura"], name="uq_itinerario_tipo_aventura"
            ),
        ]

    def __str__(self) -> str:
        return f"Itinerario #{self.itinerario_id} - tipo #{self.tipo_aventura_id}"


class DiaItinerario(models.Model):
    """DATA-007."""

    itinerario = models.ForeignKey(Itinerario, on_delete=models.CASCADE, related_name="dias")
    numero_dia = models.SmallIntegerField()
    titulo = models.CharField(max_length=150)
    actividades = models.TextField()
    distancia_km = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    desnivel_positivo_m = models.IntegerField(null=True, blank=True)
    desnivel_negativo_m = models.IntegerField(null=True, blank=True)
    alojamiento_orientativo = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001
    consejos = models.TextField(null=True, blank=True)  # noqa: DJ001

    class Meta:
        db_table = "dia_itinerario"
        constraints = [
            # DEFERRABLE: permite reordenar los días en una transacción.
            models.UniqueConstraint(
                fields=["itinerario", "numero_dia"],
                name="uq_dia_itinerario_numero",
                deferrable=models.Deferrable.DEFERRED,
            ),
            ck_rango("dia_itinerario", "numero_dia", 1, 60),
            ck_longitud("actividades", "dia_itinerario"),
            ck_longitud("consejos", "dia_itinerario"),
            ck_no_negativo("dia_itinerario", "distancia_km"),
            ck_no_negativo("dia_itinerario", "desnivel_positivo_m"),
            ck_no_negativo("dia_itinerario", "desnivel_negativo_m"),
        ]

    def __str__(self) -> str:
        return f"Día {self.numero_dia} del itinerario #{self.itinerario_id}"


class Guia(models.Model):
    """DATA-009."""

    contenido = models.OneToOneField(
        Contenido, on_delete=models.CASCADE, primary_key=True, related_name="guia"
    )
    tipo_contenido = campo_tipo_constante(T.GUIA)
    categoria = models.ForeignKey(
        "catalogos.CategoriaGuia",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="guias",
    )
    resumen = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001
    cuerpo = models.TextField(null=True, blank=True)  # noqa: DJ001
    remite_a_metodologia = models.BooleanField(default=False, db_default=False)
    palabras = models.IntegerField(default=0, db_default=0)
    destinos: models.ManyToManyField[Destino, models.Model] = models.ManyToManyField(
        Destino, through="GuiaDestino", related_name="guias"
    )
    tipos_aventura: models.ManyToManyField[TipoAventura, models.Model] = models.ManyToManyField(
        TipoAventura, through="GuiaTipoAventura", related_name="guias"
    )

    class Meta:
        db_table = "guia"
        constraints = [
            ck_tipo_constante("guia", T.GUIA),
            ck_longitud("cuerpo", "guia"),
            models.CheckConstraint(condition=Q(palabras__gte=0), name="ck_guia_palabras"),
        ]

    def __str__(self) -> str:
        return f"Guía #{self.pk}"


class GuiaDestino(models.Model):
    """DATA-009.destinos_relacionados (N:M)."""

    guia = models.ForeignKey(Guia, on_delete=models.CASCADE, related_name="+")
    destino = models.ForeignKey(Destino, on_delete=models.CASCADE, related_name="+")

    class Meta:
        db_table = "guia_destino"
        constraints = [
            models.UniqueConstraint(fields=["guia", "destino"], name="uq_guia_destino"),
        ]

    def __str__(self) -> str:
        return f"Guía #{self.guia_id} - destino #{self.destino_id}"


class GuiaTipoAventura(models.Model):
    """DATA-009.tipos_relacionados (N:M)."""

    guia = models.ForeignKey(Guia, on_delete=models.CASCADE, related_name="+")
    tipo_aventura = models.ForeignKey(TipoAventura, on_delete=models.CASCADE, related_name="+")

    class Meta:
        db_table = "guia_tipo_aventura"
        constraints = [
            models.UniqueConstraint(fields=["guia", "tipo_aventura"], name="uq_guia_tipo_aventura"),
        ]

    def __str__(self) -> str:
        return f"Guía #{self.guia_id} - tipo #{self.tipo_aventura_id}"


class Coleccion(models.Model):
    """DATA-010."""

    contenido = models.OneToOneField(
        Contenido, on_delete=models.CASCADE, primary_key=True, related_name="coleccion"
    )
    tipo_contenido = campo_tipo_constante(T.COLECCION)
    resumen = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001
    descripcion = models.TextField(null=True, blank=True)  # noqa: DJ001

    class Meta:
        db_table = "coleccion"
        constraints = [
            ck_tipo_constante("coleccion", T.COLECCION),
            ck_longitud("descripcion", "coleccion"),
        ]

    def __str__(self) -> str:
        return f"Colección #{self.pk}"


class ElementoColeccion(models.Model):
    """DATA-011: solo destinos o itinerarios (FK compuesta)."""

    coleccion = models.ForeignKey(Coleccion, on_delete=models.CASCADE, related_name="elementos")
    contenido = models.ForeignKey(
        Contenido, on_delete=models.CASCADE, related_name="elementos_de_coleccion"
    )
    tipo_contenido = models.CharField(max_length=10, choices=TipoContenido.choices)
    orden = models.SmallIntegerField(default=0, db_default=0)
    nota_editorial = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001

    class Meta:
        db_table = "elemento_coleccion"
        constraints = [
            models.UniqueConstraint(
                fields=["coleccion", "contenido"], name="uq_elemento_coleccion"
            ),
            ck_tipos("elemento_coleccion", TIPOS_ELEMENTO_COLECCION),
        ]

    def __str__(self) -> str:
        return f"Elemento #{self.pk} de la colección #{self.coleccion_id}"


class TerminoGlosario(models.Model):
    """DATA-012. El término es contenido.titulo (único vía UNIQUE(tipo, titulo_norm))."""

    contenido = models.OneToOneField(
        Contenido, on_delete=models.CASCADE, primary_key=True, related_name="termino_glosario"
    )
    tipo_contenido = campo_tipo_constante(T.TERMINO)
    definicion = models.CharField(max_length=600, null=True, blank=True)  # noqa: DJ001

    class Meta:
        db_table = "termino_glosario"
        constraints = [ck_tipo_constante("termino_glosario", T.TERMINO)]

    def __str__(self) -> str:
        return f"Término #{self.pk}"


class ContenidoTermino(models.Model):
    """DATA-013."""

    contenido = models.ForeignKey(Contenido, on_delete=models.CASCADE, related_name="terminos")
    tipo_contenido = models.CharField(max_length=10, choices=TipoContenido.choices)
    termino = models.ForeignKey(TerminoGlosario, on_delete=models.CASCADE, related_name="usos")

    class Meta:
        db_table = "contenido_termino"
        constraints = [
            models.UniqueConstraint(fields=["contenido", "termino"], name="uq_contenido_termino"),
            ck_tipos("contenido_termino", TIPOS_CON_TERMINOS),
        ]

    def __str__(self) -> str:
        return f"Contenido #{self.contenido_id} - término #{self.termino_id}"


class PaginaInstitucional(models.Model):
    """DATA-014: no se retiran ni se borran (CHECK de contenido + trigger de guardas)."""

    contenido = models.OneToOneField(
        Contenido, on_delete=models.CASCADE, primary_key=True, related_name="pagina"
    )
    tipo_contenido = campo_tipo_constante(T.PAGINA)
    clave = models.CharField(max_length=20, unique=True, choices=ClavePagina.choices)
    cuerpo = models.TextField()
    version_documento = models.CharField(max_length=20)
    vigente_desde = models.DateField()

    class Meta:
        db_table = "pagina_institucional"
        constraints = [
            ck_tipo_constante("pagina_institucional", T.PAGINA),
            models.CheckConstraint(
                condition=Q(clave__in=ClavePagina.values), name="ck_pagina_institucional_clave"
            ),
            ck_longitud("cuerpo", "pagina_institucional"),
        ]

    def __str__(self) -> str:
        return str(self.clave)


# ---------------------------------------------------------------------------
# Relaciones polimórficas
# ---------------------------------------------------------------------------
class ContenidoMedio(models.Model):
    """DATA-017, solo rol GALERIA (PORTADA = contenido.portada; hero = config_inicio)."""

    contenido = models.ForeignKey(Contenido, on_delete=models.CASCADE, related_name="galeria")
    tipo_contenido = models.CharField(max_length=10, choices=TipoContenido.choices)
    medio = models.ForeignKey("medios.Medio", on_delete=models.PROTECT, related_name="+")
    orden = models.SmallIntegerField(default=0, db_default=0)

    class Meta:
        db_table = "contenido_medio"
        constraints = [
            models.UniqueConstraint(fields=["contenido", "medio"], name="uq_contenido_medio"),
            ck_tipos("contenido_medio", TIPOS_CON_GALERIA),
        ]

    def __str__(self) -> str:
        return f"Medio #{self.medio_id} en el contenido #{self.contenido_id}"


class Fuente(models.Model):
    """DATA-018. La URL es texto: nunca se consulta (THREAT-022)."""

    contenido = models.ForeignKey(Contenido, on_delete=models.CASCADE, related_name="fuentes")
    titulo = models.CharField(max_length=200)
    entidad_editora = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001
    url = models.CharField(max_length=500, null=True, blank=True)  # noqa: DJ001
    fecha_consulta = models.DateField(null=True, blank=True)
    orden = models.SmallIntegerField(default=0, db_default=0)

    class Meta:
        db_table = "fuente"
        constraints = [
            models.CheckConstraint(
                condition=Q(url__isnull=True) | Q(url__regex=PATRON_URL), name="ck_fuente_url"
            ),
        ]

    def __str__(self) -> str:
        return self.titulo


class RelacionContenido(models.Model):
    """DATA-019: relación curada unidireccional (el complemento automático no se persiste)."""

    origen = models.ForeignKey(Contenido, on_delete=models.CASCADE, related_name="relacionados")
    origen_tipo = models.CharField(max_length=10, choices=TipoContenido.choices)
    relacionado = models.ForeignKey(
        Contenido, on_delete=models.CASCADE, related_name="relacionado_desde"
    )
    relacionado_tipo = models.CharField(max_length=10, choices=TipoContenido.choices)
    orden = models.SmallIntegerField(default=0, db_default=0)

    class Meta:
        db_table = "relacion_contenido"
        constraints = [
            models.UniqueConstraint(fields=["origen", "relacionado"], name="uq_relacion_contenido"),
            models.CheckConstraint(
                condition=~Q(origen=F("relacionado")), name="ck_relacion_contenido_distintos"
            ),
            ck_tipos("relacion_contenido", TIPOS_RELACIONABLES, campo="origen_tipo"),
            ck_tipos("relacion_contenido", TIPOS_RELACIONABLES, campo="relacionado_tipo"),
        ]

    def __str__(self) -> str:
        return f"Relación #{self.origen_id} -> #{self.relacionado_id}"
