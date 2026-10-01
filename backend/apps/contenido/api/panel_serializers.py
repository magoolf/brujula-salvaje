"""Serializers del panel editorial (contracts/openapi.yaml, tag `panel-contenidos` y
`panel-ciclo-editorial`). Solo forma y validación de estructura (Skill_Backend Regla 02): la
lógica de negocio y el guardado viven en `apps.contenido.services`.

Los campos de entrada usan `EntradaEstricta` (additionalProperties/unevaluatedProperties: false
del contrato → 400 `campo_no_permitido`, DEC-AUTO-108, THREAT-024). Las salidas son serializers
explícitos (Regla 13): nunca `__all__`.
"""

from __future__ import annotations

import copy
from typing import Any

from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.utils.deconstruct import deconstructible
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.contenido.models import ClavePagina, TipoContenido
from apps.core.api.serializers import (
    EntradaEstricta,
    IdSerializerField,
    PaginaMetaSerializer,
    ReferenciaUsoSerializer,
)
from apps.core.esquema import (
    id_contrato,
    lista_ids,
    lista_unica,
    numero,
    texto_html,
    texto_sin_nul,
    url_http,
)
from apps.medios.models import EstadoMedio

T = TipoContenido


def _con_limite(campo: Any, *, max_length: int | None = None, min_length: int | None = None) -> Any:
    """Añade `MaxLengthValidator`/`MinLengthValidator` a un campo `many=True` (ListSerializer
    generado por `SomeSerializer(many=True, ...)`, TKT-006 ciclo oasdiff) para que
    drf-spectacular genere `maxItems`/`minItems` (`_insert_field_validators`, que solo lee
    `field.validators`; `ListSerializer.max_length`/`.min_length` los aplica a mano en
    `to_internal_value` sin pasar por `.validators`).

    RONDA 5 -- la primera versión de este helper (`campo.validators.append(...)`, mutación
    posterior a la construcción) NO SOBREVIVE: cada vez que el serializer padre se instancia,
    `BaseSerializer.get_fields()` hace `copy.deepcopy(self._declared_fields)`, y
    `Field.__deepcopy__` (rest_framework/fields.py) NO copia el estado del objeto -- reconstruye
    el campo desde cero llamando a `self.__class__(*self._args, **self._kwargs)` con los
    argumentos ORIGINALES de construcción (`_args`/`_kwargs`, guardados por `Field.__new__`).
    Cualquier atributo mutado después de construir el campo (como `.validators.append(...)`) se
    pierde en cada copia; por eso el hallazgo `*-items-unset` seguía apareciendo en el esquema
    pese al `append`. La solución es reconstruir el `ListSerializer` con `validators=` como
    kwarg del constructor (DRF trata `validators`, junto con `regex`, como inmutable y lo
    reutiliza tal cual en cada `__deepcopy__`, en vez de copiarlo -- ver `Field.__deepcopy__`),
    usando `campo._kwargs`/`campo._args` (los mismos que `many_init` ya calculó: `child` y
    cualquier otro kwarg de `LIST_SERIALIZER_KWARGS` como `required`/`default`/`allow_null`) para
    no tener que repetirlos en cada sitio de uso. `child` se deep-copia porque el `child` ya
    guardado en `_kwargs` está `bind()`eado al `ListSerializer` original: reutilizarlo tal cual
    en un `ListSerializer` nuevo dispara `AssertionError: redundant source=''` al volver a hacer
    `bind()`."""
    validadores = list(campo._kwargs.get("validators") or [])
    if max_length is not None:
        validadores.append(MaxLengthValidator(max_length))
    if min_length is not None:
        validadores.append(MinLengthValidator(min_length))
    kwargs = dict(campo._kwargs)
    kwargs["child"] = copy.deepcopy(kwargs["child"])
    kwargs["validators"] = validadores
    return campo.__class__(*campo._args, **kwargs)


@extend_schema_field({"type": "string"})
class _CampoTipo(serializers.ChoiceField):
    """`ChoiceField` con validación real pero esquema en línea sin clave `enum` nombrada.

    `extend_schema_field` solo sobrevive al `Field.__deepcopy__` de DRF (que reconstruye la
    instancia vía `self.__class__(*args, **kwargs)` al enlazar el serializer, perdiendo cualquier
    atributo puesto sobre la instancia) si se aplica sobre la CLASE, nunca sobre la instancia: de
    ahí esta subclase en vez de decorar cada `ChoiceField(...)` suelto. Evita que drf-spectacular
    registre y reconcilie un componente de enum compartido entre los varios subconjuntos de
    `tipo`/`tipo_contenido` del contrato (W001). `ENUM_NAME_OVERRIDES` (la vía recomendada) vive en
    `config/settings/base.py`, fuera de los `archivos_permitidos` de TKT-006.
    """


def _tipo_field(choices: Any) -> serializers.ChoiceField:
    return _CampoTipo(choices=choices)


@extend_schema_field({"type": "object"})
class _ObjetoOpacoField(serializers.DictField):
    """Documento estructurado de forma libre (`instantanea` de una revisión, `datos` de una
    restauración): el contrato lo declara `{type: object}` SIN `additionalProperties` (objeto
    CERRADO sin propiedades fijas, gate_contrato.py N13). `DictField` por sí solo genera
    `additionalProperties: {}` (objeto ABIERTO), que el gate rechaza cuando el contrato lo cierra;
    `extend_schema_field` sobre la clase fuerza el esquema exacto del contrato sin tocar la
    validación/serialización real de `DictField` (TKT-006, ciclo de corrección del gate CI)."""


@extend_schema_field({"type": "string", "enum": list(TipoContenido.values)})
class _CampoTipoEntidadConEnum(serializers.ChoiceField):
    """`ChoiceField` de `tipo` (TipoEntidadContenido, 7 valores) con el enum inline en vez de un
    componente nombrado: evita la colisión W001 de `_CampoTipo` (esquema fijo sin `enum`) SIN
    perder los valores válidos que el contrato sí documenta (gate oasdiff: enum removed in
    revision). Al ser un esquema literal por `extend_schema_field` (no un `$ref` reconciliado),
    reusarlo en múltiples campos `tipo` no reintroduce la colisión de nombre."""


def _tipo_entidad_field() -> serializers.ChoiceField:
    return _CampoTipoEntidadConEnum(choices=TipoContenido.choices)


@extend_schema_field({"type": "string", "enum": ["BORRADOR", "PUBLICADO", "RETIRADO"]})
class _CampoEstadoEditorial(serializers.ChoiceField):
    """`ChoiceField` de `estado_editorial` (EstadoEditorial) con el enum inline; mismo motivo que
    `_CampoTipoEntidadConEnum`."""


def _campo_estado_editorial(**kwargs: Any) -> serializers.ChoiceField:
    return _CampoEstadoEditorial(choices=["BORRADOR", "PUBLICADO", "RETIRADO"], **kwargs)


@extend_schema_field({"type": ["integer", "null"], "format": "int64"})
class _CampoIdNuloInt64(serializers.IntegerField):
    """components.schemas.ActorRef.id: entero int64 nullable ("sistema" cuando es null); un
    `IntegerField` sin anotar no declara `format: int64` (TKT-006, ciclo oasdiff:
    response-property-type-changed, formato int64 -> none)."""


@extend_schema_field({"type": "string", "format": "uri-reference"})
class _CampoUriReferencia(serializers.CharField):
    """components.schemas.MedioMiniatura.url_miniatura: uri-reference (ruta relativa)."""


@deconstructible
class _SinClavesRepetidas:
    """Lista de objetos sin dos elementos con la misma clave (`claves`): aplica de verdad el
    `uniqueItems` del contrato en listas de referencias (TKT-032). 400 `validacion`."""

    def __init__(self, claves: tuple[str, ...], mensaje: str) -> None:
        self.claves = claves
        self.mensaje = mensaje

    def __call__(self, valor: list[dict[str, Any]]) -> None:
        vistas = [tuple(elemento.get(c) for c in self.claves) for elemento in valor]
        if len(vistas) != len(set(vistas)):
            raise serializers.ValidationError(self.mensaje, code="elementos_repetidos")

    def __eq__(self, otro: object) -> bool:
        return (
            isinstance(otro, _SinClavesRepetidas)
            and otro.claves == self.claves
            and otro.mensaje == self.mensaje
        )

    def __hash__(self) -> int:
        return hash((self.claves, self.mensaje))


@extend_schema_field({"type": "string", "enum": ["PRINCIPAL", "COPUBLICACION", "CASCADA"]})
class _CampoRolEntidadOperacion(serializers.ChoiceField):
    """components.schemas.RolEntidadOperacion con el enum inline (`origen`/`rol` de las
    entidades multi-entidad, CHG-API-005); mismo motivo que `_CampoTipoEntidadConEnum`."""


def _campo_rol_entidad_operacion() -> serializers.ChoiceField:
    return _CampoRolEntidadOperacion(choices=["PRINCIPAL", "COPUBLICACION", "CASCADA"])


PATRON_SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"
PATRON_NO_NUL = r"^[^\x00]*$"


def _texto(max_length: int, *, requerido: bool = False, nulo: bool = True) -> serializers.CharField:
    """Texto plano del contrato (`pattern: '^[^\\u0000]*$'`, TKT-012)."""
    return texto_sin_nul(
        max_length=max_length,
        required=requerido,
        allow_null=nulo and not requerido,
        allow_blank=False,
        trim_whitespace=False,
    )


def _html(max_length: int = 100_000) -> serializers.CharField:
    """Texto HTML del contrato (`contentMediaType: text/html` + patrón sin NUL, TKT-012)."""
    return texto_html(
        max_length=max_length,
        required=False,
        allow_null=True,
        allow_blank=False,
        trim_whitespace=False,
    )


def _id_lista(maximo: int) -> serializers.ListField:
    """Lista de `Id` del contrato: `uniqueItems: true` (validado), `maxItems`, ítems sin
    `maximum` (TKT-012: request-property-max-set / response-property-unique-items-unset)."""
    return lista_ids(maximo)


def _id_opcional() -> serializers.IntegerField:
    """`{type: [integer, null], format: int64, minimum: 1}` del contrato (TKT-012)."""
    return id_contrato(required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Comunes (ContenidoComunCampos / entrada)
# ---------------------------------------------------------------------------
@extend_schema_field(
    {"type": "string", "enum": ["DESTINO", "ITINERARIO", "GUIA", "TIPO", "COLECCION"]}
)
class _CampoTipoRelacionable(serializers.ChoiceField):
    """`RelacionEntrada.tipo`: subconjunto de TipoEntidadContenido (sin TERMINO ni PAGINA, que no
    son relacionables) con el enum inline (TKT-006, ciclo oasdiff: enum removed en `_CampoTipo`)."""


class RelacionEntradaSerializer(EntradaEstricta):
    tipo = _CampoTipoRelacionable(choices=[T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO, T.COLECCION])
    id = id_contrato()


class FuenteEntradaSerializer(EntradaEstricta):
    titulo = texto_sin_nul(min_length=1, max_length=200)
    entidad_editora = _texto(150)
    # El contrato exige URL absoluta http(s) (`pattern: '^https?://...'`, `format: uri`): se
    # valida de verdad, no solo se documenta (TKT-012).
    url = url_http(max_length=500, required=False, allow_null=True)
    fecha_consulta = serializers.DateField(required=False, allow_null=True)


class ComunesMixin(serializers.Serializer[Any]):
    titulo = texto_sin_nul(min_length=1, max_length=150)
    slug = serializers.RegexField(PATRON_SLUG, max_length=120, required=False, allow_null=True)
    fecha_ultima_revision = serializers.DateField(required=False, allow_null=True)
    seo_titulo = _texto(70)
    seo_descripcion = _texto(160)
    relaciones = _con_limite(
        RelacionEntradaSerializer(  # type: ignore[call-arg]
            many=True, required=False, max_length=12, default=list
        ),
        max_length=12,
    )
    terminos_ids = _id_lista(50)
    fuentes = _con_limite(
        FuenteEntradaSerializer(  # type: ignore[call-arg]
            many=True, required=False, max_length=30, default=list
        ),
        max_length=30,
    )

    def validate_relaciones(self, valor: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ids = [r["id"] for r in valor]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("No puede haber relaciones repetidas.")
        return valor


class VersionMixin(serializers.Serializer[Any]):
    version = serializers.IntegerField(min_value=1)


class IdOpcionalMixin(serializers.Serializer[Any]):
    id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Destino
# ---------------------------------------------------------------------------
class DestinoCamposMixin(serializers.Serializer[Any]):
    pais_id = _id_opcional()
    resumen = _texto(300)
    descripcion_experta = _html()
    tipos_ids = _id_lista(12)
    tipo_principal_id = _id_opcional()
    dificultad = serializers.IntegerField(min_value=1, max_value=5, required=False, allow_null=True)
    meses_mejor_epoca = lista_unica(
        serializers.IntegerField(min_value=1, max_value=12),
        max_length=12,
        required=False,
        default=list,
    )
    duracion_min_dias = serializers.IntegerField(
        min_value=1, max_value=90, required=False, allow_null=True
    )
    duracion_max_dias = serializers.IntegerField(
        min_value=1, max_value=90, required=False, allow_null=True
    )
    nivel_presupuesto = serializers.IntegerField(
        min_value=1, max_value=4, required=False, allow_null=True
    )
    clima = _texto(5000)  # texto plano en el contrato (sin contentMediaType)
    altitud_max_m = serializers.IntegerField(
        min_value=-500, max_value=9000, required=False, allow_null=True
    )
    como_llegar = _html()
    seguridad_riesgos = _html()
    sostenibilidad = _html()
    latitud = numero(min_value=-90, max_value=90, required=False, allow_null=True)
    longitud = numero(min_value=-180, max_value=180, required=False, allow_null=True)
    portada_id = _id_opcional()
    galeria_ids = _id_lista(30)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        tipos = attrs.get("tipos_ids") or []
        if len(tipos) != len(set(tipos)):
            raise serializers.ValidationError({"tipos_ids": ["No puede haber tipos repetidos."]})
        principal = attrs.get("tipo_principal_id")
        if principal is not None and tipos and principal not in tipos:
            raise serializers.ValidationError(
                {"tipo_principal_id": ["Debe pertenecer a tipos_ids."]}
            )
        return attrs


class TipoVersionadoEntradaSerializer(EntradaEstricta):
    """TipoVersionado de entrada: id + version (bloqueo optimista, ALT-016). Se define una sola
    vez a nivel de módulo y se reutiliza (nunca anidada) para que drf-spectacular no registre dos
    componentes distintos con el mismo nombre inferido (W001)."""

    # `id_contrato`: `Id` del contrato (int64, mínimo 1, sin `maximum`) y además rechaza ids
    # fuera de bigint antes del ORM (TKT-032; antes `_CampoIdSinMaximo`, sin ese control).
    id = id_contrato()
    version = serializers.IntegerField(min_value=1)


class EntidadRefEntradaSerializer(EntradaEstricta):
    """EntidadRef de entrada: tipo + id (CHG-API-005). Ídem: definida una sola vez."""

    tipo = _tipo_entidad_field()
    # `id_contrato`: `Id` del contrato (int64, mínimo 1, sin `maximum`) y además rechaza ids
    # fuera de bigint antes del ORM (TKT-032; antes `_CampoIdSinMaximo`, sin ese control).
    id = id_contrato()


def _copublicar_tipos() -> serializers.ListField:
    """`copublicar_tipos` del contrato (PublicacionEntrada y CamposOperacionPublicada): `maxItems:
    12`, `uniqueItems: true` y "sin ids repetidos (400 validacion)" (TKT-032). `lista_unica`
    (ListField con hijo serializer) documenta y aplica `uniqueItems`; un `Serializer(many=True)`
    no lo admite. La unicidad se exige por `id` (más estricta que la igualdad de objeto que
    implica `uniqueItems`, y es lo que el contrato describe)."""
    return lista_unica(
        TipoVersionadoEntradaSerializer(),
        max_length=12,
        required=False,
        default=list,
        esquema_extra={"default": []},
        validators=[_SinClavesRepetidas(("id",), "No puede haber tipos repetidos.")],
    )


def _cascada_confirmada(maximo: int) -> serializers.ListField:
    """`cascada_confirmada` del contrato (`maxItems`, `uniqueItems: true`, TKT-032): una entidad
    (tipo, id) no se confirma dos veces."""
    return lista_unica(
        EntidadRefEntradaSerializer(),
        max_length=maximo,
        required=False,
        validators=[_SinClavesRepetidas(("tipo", "id"), "No puede haber entidades repetidas.")],
    )


class OperacionPublicadaMixin(serializers.Serializer[Any]):
    """Solo el destino usa estos campos de control (CamposOperacionPublicada, CHG-API-005)."""

    copublicar_tipos = _copublicar_tipos()
    confirmar_cascada = serializers.BooleanField(required=False, default=False)
    cascada_confirmada = _cascada_confirmada(12)


class DestinoEntradaSerializer(EntradaEstricta, ComunesMixin, DestinoCamposMixin):
    pass


class DestinoActualizacionSerializer(
    EntradaEstricta, ComunesMixin, DestinoCamposMixin, OperacionPublicadaMixin, VersionMixin
):
    pass


class DestinoVistaPreviaSerializer(
    EntradaEstricta, ComunesMixin, DestinoCamposMixin, IdOpcionalMixin
):
    pass


# ---------------------------------------------------------------------------
# Itinerario
# ---------------------------------------------------------------------------
class DiaEntradaSerializer(EntradaEstricta):
    numero_dia = serializers.IntegerField(min_value=1, max_value=60)
    titulo = texto_sin_nul(min_length=1, max_length=150)
    actividades = texto_html(max_length=50_000, trim_whitespace=False)
    distancia_km = numero(min_value=0, max_value=99_999.9, required=False, allow_null=True)
    desnivel_positivo_m = serializers.IntegerField(
        min_value=0, max_value=20_000, required=False, allow_null=True
    )
    desnivel_negativo_m = serializers.IntegerField(
        min_value=0, max_value=20_000, required=False, allow_null=True
    )
    alojamiento_orientativo = _texto(300)
    consejos = texto_html(max_length=50_000, required=False, allow_null=True, trim_whitespace=False)

    def validate_actividades(self, valor: str) -> str:
        from apps.contenido.saneado import sanear_html

        return sanear_html(valor) or ""

    def validate_consejos(self, valor: str | None) -> str | None:
        from apps.contenido.saneado import sanear_html

        return sanear_html(valor)


class ItinerarioCamposMixin(serializers.Serializer[Any]):
    destino_id = _id_opcional()
    resumen = _texto(300)
    duracion_dias = serializers.IntegerField(
        min_value=1, max_value=60, required=False, allow_null=True
    )
    dificultad = serializers.IntegerField(min_value=1, max_value=5, required=False, allow_null=True)
    tipos_ids = _id_lista(12)
    distancia_total_km = numero(min_value=0, max_value=99_999.9, required=False, allow_null=True)
    desnivel_acumulado_m = serializers.IntegerField(
        min_value=0, max_value=1_000_000, required=False, allow_null=True
    )
    riesgos_seguridad = _html()
    portada_id = _id_opcional()
    galeria_ids = _id_lista(30)
    dias = _con_limite(
        DiaEntradaSerializer(  # type: ignore[call-arg]
            many=True, required=False, max_length=60, default=list
        ),
        max_length=60,
    )

    def validate_dias(self, valor: list[dict[str, Any]]) -> list[dict[str, Any]]:
        numeros = [d["numero_dia"] for d in valor]
        if len(numeros) != len(set(numeros)):
            raise serializers.ValidationError("El número de día no puede repetirse.")
        return valor


class ItinerarioEntradaSerializer(EntradaEstricta, ComunesMixin, ItinerarioCamposMixin):
    pass


class ItinerarioActualizacionSerializer(
    EntradaEstricta, ComunesMixin, ItinerarioCamposMixin, VersionMixin
):
    pass


class ItinerarioVistaPreviaSerializer(
    EntradaEstricta, ComunesMixin, ItinerarioCamposMixin, IdOpcionalMixin
):
    pass


# ---------------------------------------------------------------------------
# Guía
# ---------------------------------------------------------------------------
class GuiaCamposMixin(serializers.Serializer[Any]):
    categoria_id = _id_opcional()
    resumen = _texto(300)
    cuerpo = _html()
    destinos_ids = _id_lista(20)
    tipos_ids = _id_lista(12)
    remite_a_metodologia = serializers.BooleanField(required=False, default=False)
    portada_id = _id_opcional()


class GuiaEntradaSerializer(EntradaEstricta, ComunesMixin, GuiaCamposMixin):
    pass


class GuiaActualizacionSerializer(EntradaEstricta, ComunesMixin, GuiaCamposMixin, VersionMixin):
    pass


class GuiaVistaPreviaSerializer(EntradaEstricta, ComunesMixin, GuiaCamposMixin, IdOpcionalMixin):
    pass


# ---------------------------------------------------------------------------
# Tipo de aventura
# ---------------------------------------------------------------------------
class ChecklistEntradaSerializer(EntradaEstricta):
    texto = texto_sin_nul(min_length=1, max_length=200)
    grupo = _texto(60)
    esencial = serializers.BooleanField()
    orden = serializers.IntegerField(min_value=0, max_value=1000)


class TipoAventuraCamposMixin(serializers.Serializer[Any]):
    resumen = _texto(300)
    descripcion = _html()
    nivel_exigencia = serializers.IntegerField(
        min_value=1, max_value=5, required=False, allow_null=True
    )
    portada_id = _id_opcional()
    orden = serializers.IntegerField(min_value=0, max_value=1000, required=False, default=0)
    checklist = _con_limite(
        ChecklistEntradaSerializer(  # type: ignore[call-arg]
            many=True, required=False, max_length=100, default=list
        ),
        max_length=100,
    )

    def validate_checklist(self, valor: list[dict[str, Any]]) -> list[dict[str, Any]]:
        textos = [c["texto"] for c in valor]
        if len(textos) != len(set(textos)):
            raise serializers.ValidationError(
                "El texto de la lista de comprobación no puede repetirse."
            )
        return valor


class TipoAventuraEntradaSerializer(EntradaEstricta, ComunesMixin, TipoAventuraCamposMixin):
    pass


class TipoAventuraActualizacionSerializer(
    EntradaEstricta, ComunesMixin, TipoAventuraCamposMixin, VersionMixin
):
    pass


class TipoAventuraVistaPreviaSerializer(
    EntradaEstricta, ComunesMixin, TipoAventuraCamposMixin, IdOpcionalMixin
):
    pass


# ---------------------------------------------------------------------------
# Colección
# ---------------------------------------------------------------------------
@extend_schema_field({"type": "string", "enum": ["DESTINO", "ITINERARIO"]})
class _CampoTipoElementoColeccion(serializers.ChoiceField):
    """`ElementoColeccionEntrada.tipo_contenido` con el enum inline."""


class ElementoColeccionEntradaSerializer(EntradaEstricta):
    tipo_contenido = _CampoTipoElementoColeccion(choices=[T.DESTINO, T.ITINERARIO])
    contenido_id = id_contrato()
    orden = serializers.IntegerField(min_value=0, max_value=1000)
    nota_editorial = _texto(300)


class ColeccionCamposMixin(serializers.Serializer[Any]):
    resumen = _texto(300)
    descripcion = _html()
    portada_id = _id_opcional()
    elementos = _con_limite(
        ElementoColeccionEntradaSerializer(  # type: ignore[call-arg]
            many=True, required=False, max_length=100, default=list
        ),
        max_length=100,
    )

    def validate_elementos(self, valor: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pares = [(e["tipo_contenido"], e["contenido_id"]) for e in valor]
        if len(pares) != len(set(pares)):
            raise serializers.ValidationError("Un elemento no puede repetirse en la colección.")
        return valor


class ColeccionEntradaSerializer(EntradaEstricta, ComunesMixin, ColeccionCamposMixin):
    pass


class ColeccionActualizacionSerializer(
    EntradaEstricta, ComunesMixin, ColeccionCamposMixin, VersionMixin
):
    pass


class ColeccionVistaPreviaSerializer(
    EntradaEstricta, ComunesMixin, ColeccionCamposMixin, IdOpcionalMixin
):
    pass


# ---------------------------------------------------------------------------
# Término de glosario
# ---------------------------------------------------------------------------
class TerminoGlosarioCamposMixin(serializers.Serializer[Any]):
    titulo = texto_sin_nul(min_length=1, max_length=150)
    slug = serializers.RegexField(PATRON_SLUG, max_length=120, required=False, allow_null=True)
    definicion = _texto(600)
    fecha_ultima_revision = serializers.DateField(required=False, allow_null=True)


class TerminoGlosarioEntradaSerializer(EntradaEstricta, TerminoGlosarioCamposMixin):
    pass


class TerminoGlosarioActualizacionSerializer(
    EntradaEstricta, TerminoGlosarioCamposMixin, VersionMixin
):
    pass


# ---------------------------------------------------------------------------
# Página institucional
# ---------------------------------------------------------------------------
class PaginaInstitucionalCamposMixin(serializers.Serializer[Any]):
    titulo = texto_sin_nul(min_length=1, max_length=150)
    cuerpo = texto_html(max_length=100_000, trim_whitespace=False)
    version_documento = texto_sin_nul(min_length=1, max_length=20)
    vigente_desde = serializers.DateField()
    fecha_ultima_revision = serializers.DateField(required=False, allow_null=True)
    seo_titulo = _texto(70)
    seo_descripcion = _texto(160)


class PaginaInstitucionalActualizacionSerializer(
    EntradaEstricta, PaginaInstitucionalCamposMixin, VersionMixin
):
    pass


class PaginaInstitucionalVistaPreviaSerializer(
    EntradaEstricta, PaginaInstitucionalCamposMixin, IdOpcionalMixin
):
    titulo = texto_sin_nul(min_length=1, max_length=150, required=False)
    cuerpo = texto_html(max_length=100_000, required=False, trim_whitespace=False)
    version_documento = texto_sin_nul(min_length=1, max_length=20, required=False)
    vigente_desde = serializers.DateField(required=False)


# ---------------------------------------------------------------------------
# Ciclo editorial (común a todos los tipos)
# ---------------------------------------------------------------------------
class TransicionEntradaSerializer(EntradaEstricta):
    version = serializers.IntegerField(min_value=1)


class PublicacionEntradaSerializer(EntradaEstricta):
    version = serializers.IntegerField(min_value=1)
    copublicar_tipos = _copublicar_tipos()


class RetiroEntradaSerializer(EntradaEstricta):
    version = serializers.IntegerField(min_value=1)
    motivo = serializers.RegexField(
        PATRON_NO_NUL, min_length=1, max_length=300, trim_whitespace=False
    )
    confirmar_cascada = serializers.BooleanField(required=False, default=False)
    cascada_confirmada = _cascada_confirmada(212)


class AnalisisPublicacionEntradaSerializer(EntradaEstricta):
    version = serializers.IntegerField(min_value=1)
    # TKT-032: `uniqueItems: true` del contrato aplicado (antes `[1, 1]` daba 200). `_id_lista`
    # (TKT-012) ya emite los ítems como `Id` sin `maximum` y rechaza ids fuera de bigint.
    tipos_ids = _id_lista(12)
    tipo_principal_id = _id_opcional()


# ---------------------------------------------------------------------------
# Salidas (referencias y metadatos comunes)
# ---------------------------------------------------------------------------
class ActorRefSerializer(serializers.Serializer[Any]):
    """components.schemas.ActorRef. `ref_name` propio: evita colisionar en el esquema generado
    con los `ActorRefSerializer` de otros dominios (apps.auditoria, apps.medios, apps.inicio),
    cada uno definido en su propia capa API por Skill_Backend §5 (sin importar entre dominios)."""

    id = _CampoIdNuloInt64(allow_null=True)
    etiqueta = serializers.CharField(max_length=60)

    class Meta:
        ref_name = "ActorRefContenido"


class ContenidoRefPanelSerializer(serializers.Serializer[Any]):
    tipo = _tipo_entidad_field()
    id = IdSerializerField()
    titulo = serializers.CharField(max_length=150)
    slug = serializers.CharField(max_length=120, allow_null=True, required=False)
    estado_editorial = _campo_estado_editorial()


@extend_schema_field({"type": "string", "enum": list(EstadoMedio.values)})
class _CampoEstadoMedio(serializers.ChoiceField):
    """`MedioMiniatura.estado` con el enum inline (TKT-006, ciclo oasdiff)."""


class MedioRefPanelSerializer(serializers.Serializer[Any]):
    """components.schemas.MedioMiniatura (`ContenidoPanelMeta.referencias.medios[]`)."""

    id = IdSerializerField()
    estado = _CampoEstadoMedio(choices=EstadoMedio.choices)
    texto_alternativo = serializers.CharField(max_length=250, allow_null=True, required=False)
    licencia_codigo = serializers.CharField(max_length=40, allow_null=True, required=False)
    url_miniatura = _CampoUriReferencia()

    class Meta:
        ref_name = "MedioMiniaturaContenido"


class TerminoRefPanelSerializer(serializers.Serializer[Any]):
    """`ContenidoPanelMeta.referencias.terminos[]` (esquema en línea: {id, termino})."""

    id = IdSerializerField()
    termino = serializers.CharField(max_length=150)


class TaxonomiaRefPanelSerializer(serializers.Serializer[Any]):
    """`ContenidoPanelMeta.referencias.taxonomias[]` (esquema en línea: {clase, id, nombre})."""

    clase = serializers.ChoiceField(choices=["PAIS", "TIPO", "CATEGORIA"])
    id = IdSerializerField()
    nombre = serializers.CharField(max_length=150)


class ErrorReglaSerializer(serializers.Serializer[Any]):
    campo = serializers.CharField(max_length=100)
    code = serializers.RegexField(r"^[a-z][a-z0-9_]{2,63}$")
    mensaje = serializers.CharField(max_length=300)
    referencias = _con_limite(ContenidoRefPanelSerializer(many=True, required=False), max_length=50)


class RequisitosPublicacionSerializer(serializers.Serializer[Any]):
    cumple = serializers.BooleanField()
    pendientes = _con_limite(ErrorReglaSerializer(many=True), max_length=200)


class EntidadTransitadaSerializer(ContenidoRefPanelSerializer):
    version = serializers.IntegerField(min_value=1)
    numero_revision = serializers.IntegerField(min_value=1, allow_null=True)
    url_publica = serializers.RegexField(r"^/[a-z0-9/-]*$", allow_null=True, required=False)
    origen = _campo_rol_entidad_operacion()


class ResultadoTransicionSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    tipo = _tipo_entidad_field()
    estado_editorial = _campo_estado_editorial()
    version = serializers.IntegerField(min_value=1)
    numero_revision = serializers.IntegerField(min_value=1, allow_null=True)
    url_publica = serializers.RegexField(r"^/[a-z0-9/-]*$", allow_null=True, required=False)
    afectados = _con_limite(ContenidoRefPanelSerializer(many=True), max_length=200)
    entidades = _con_limite(EntidadTransitadaSerializer(many=True), max_length=213, min_length=1)


class BloqueoCascadaSerializer(serializers.Serializer[Any]):
    tipo_aventura = ContenidoRefPanelSerializer()
    itinerarios = _con_limite(ContenidoRefPanelSerializer(many=True), max_length=100, min_length=1)
    total_itinerarios = serializers.IntegerField(min_value=1)


class ImpactoRetiroSerializer(serializers.Serializer[Any]):
    retirable = serializers.BooleanField()
    itinerarios_en_cascada = _con_limite(ContenidoRefPanelSerializer(many=True), max_length=200)
    tipos_en_cascada = _con_limite(ContenidoRefPanelSerializer(many=True), max_length=12)
    bloqueos_cascada = _con_limite(BloqueoCascadaSerializer(many=True), max_length=12)
    colecciones = _con_limite(ContenidoRefPanelSerializer(many=True), max_length=200)
    destacados = serializers.ListField(
        child=serializers.ChoiceField(choices=["DESTINOS", "ITINERARIOS", "GUIAS"]),
        max_length=3,
    )
    enlaces_entrantes = serializers.IntegerField(min_value=0)
    bloqueos = _con_limite(ReferenciaUsoSerializer(many=True), max_length=100)


class ValidacionEntidadSerializer(serializers.Serializer[Any]):
    tipo = _tipo_entidad_field()
    id = IdSerializerField()
    titulo = serializers.CharField(max_length=150)
    slug = serializers.CharField(max_length=120, allow_null=True, required=False)
    estado_editorial = _campo_estado_editorial()
    version = serializers.IntegerField(min_value=1)
    rol = _campo_rol_entidad_operacion()
    cumple = serializers.BooleanField()
    pendientes = _con_limite(ErrorReglaSerializer(many=True), max_length=200)


class TipoVersionadoSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    version = serializers.IntegerField(min_value=1)


class AnalisisPublicacionSerializer(serializers.Serializer[Any]):
    operacion = serializers.ChoiceField(choices=["PUBLICAR", "ACTUALIZAR_PUBLICACION"])
    confirmable = serializers.BooleanField()
    entidad = ValidacionEntidadSerializer()
    copublicacion = _con_limite(ValidacionEntidadSerializer(many=True), max_length=12)
    copublicar_tipos = _con_limite(TipoVersionadoSerializer(many=True), max_length=12)
    tipos_en_cascada = _con_limite(ContenidoRefPanelSerializer(many=True), max_length=12)
    bloqueos_cascada = _con_limite(BloqueoCascadaSerializer(many=True), max_length=12)


class RevisionResumenSerializer(serializers.Serializer[Any]):
    numero_revision = serializers.IntegerField(min_value=1)
    motivo = serializers.ChoiceField(
        choices=["PUBLICACION", "ACTUALIZACION", "RETIRO", "RESTAURACION"]
    )
    creado_en = serializers.DateTimeField()
    creado_por = ActorRefSerializer()


class RevisionDetalleSerializer(RevisionResumenSerializer):
    instantanea = _ObjetoOpacoField()


class RestauracionRevisionSerializer(serializers.Serializer[Any]):
    numero_revision = serializers.IntegerField(min_value=1)
    version_actual = serializers.IntegerField(min_value=1)
    datos = _ObjetoOpacoField()


class PaginaRevisionResumenSerializer(PaginaMetaSerializer):
    resultados = RevisionResumenSerializer(many=True)


# ---------------------------------------------------------------------------
# Salidas Panel por tipo (ContenidoPanelMeta + ContenidoComunCampos + {Tipo}Campos)
# ---------------------------------------------------------------------------
class ReferenciasPanelSerializer(serializers.Serializer[Any]):
    medios = _con_limite(MedioRefPanelSerializer(many=True, required=False), max_length=60)
    contenidos = _con_limite(ContenidoRefPanelSerializer(many=True, required=False), max_length=200)
    terminos = _con_limite(TerminoRefPanelSerializer(many=True, required=False), max_length=50)
    taxonomias = _con_limite(TaxonomiaRefPanelSerializer(many=True, required=False), max_length=100)


class ContenidoPanelMetaSerializer(serializers.Serializer[Any]):
    id = IdSerializerField()
    tipo = _tipo_entidad_field()
    estado_editorial = _campo_estado_editorial()
    version = serializers.IntegerField(min_value=1)
    slug_bloqueado = serializers.BooleanField()
    primera_publicacion_en = serializers.DateTimeField(allow_null=True, required=False)
    publicado_actualizado_en = serializers.DateTimeField(allow_null=True, required=False)
    retirado_en = serializers.DateTimeField(allow_null=True, required=False)
    motivo_retiro = serializers.CharField(allow_null=True, max_length=300, required=False)
    creado_en = serializers.DateTimeField()
    actualizado_en = serializers.DateTimeField()
    creado_por = ActorRefSerializer()
    actualizado_por = ActorRefSerializer()
    url_publica = serializers.RegexField(r"^/[a-z0-9/-]*$", allow_null=True, required=False)
    requisitos_publicacion = RequisitosPublicacionSerializer()
    referencias = ReferenciasPanelSerializer()

    def to_representation(self, instance: Any) -> dict[str, Any]:
        from apps.contenido import services

        contenido = instance
        return {
            "id": contenido.pk,
            "tipo": contenido.tipo,
            "estado_editorial": contenido.estado_editorial,
            "version": contenido.version,
            "slug_bloqueado": contenido.primera_publicacion_en is not None,
            "primera_publicacion_en": contenido.primera_publicacion_en,
            "publicado_actualizado_en": contenido.publicado_actualizado_en,
            "retirado_en": contenido.retirado_en,
            "motivo_retiro": contenido.motivo_retiro,
            "creado_en": contenido.creado_en,
            "actualizado_en": contenido.actualizado_en,
            "creado_por": {
                "id": contenido.creado_por_id,
                "etiqueta": f"#{contenido.creado_por_id}" if contenido.creado_por_id else "sistema",
            },
            "actualizado_por": {
                "id": contenido.actualizado_por_id,
                "etiqueta": f"#{contenido.actualizado_por_id}"
                if contenido.actualizado_por_id
                else "sistema",
            },
            "url_publica": services._url_publica(contenido),
            "requisitos_publicacion": _requisitos_publicacion(contenido),
            "referencias": {"medios": [], "contenidos": [], "terminos": [], "taxonomias": []},
        }


def _requisitos_publicacion(contenido: Any) -> dict[str, Any]:
    from apps.contenido import services

    if contenido.tipo == T.PAGINA or contenido.estado_editorial == "RETIRADO":
        return {"cumple": True, "pendientes": []}
    subtipo = services.subtipo_de(contenido)
    errores = services._validar_entidad_para_publicar(
        contenido.tipo,
        contenido,
        subtipo,
        exigir_destino_publicado=(contenido.estado_editorial == "PUBLICADO"),
    )
    return {"cumple": not errores, "pendientes": errores}


def _comunes_representacion(contenido: Any) -> dict[str, Any]:
    return {
        "titulo": contenido.titulo,
        "slug": contenido.slug,
        "fecha_ultima_revision": contenido.fecha_ultima_revision,
        "seo_titulo": contenido.seo_titulo,
        "seo_descripcion": contenido.seo_descripcion,
        "relaciones": [
            {"tipo": r.relacionado_tipo, "id": r.relacionado_id}
            for r in contenido.relacionados.order_by("orden", "id")
        ],
        "terminos_ids": list(contenido.terminos.values_list("termino_id", flat=True)),
        "fuentes": [
            {
                "titulo": f.titulo,
                "entidad_editora": f.entidad_editora,
                "url": f.url,
                "fecha_consulta": f.fecha_consulta,
            }
            for f in contenido.fuentes.order_by("orden", "id")
        ],
    }


class DestinoPanelSerializer(ContenidoPanelMetaSerializer, ComunesMixin, DestinoCamposMixin):
    """Herencia múltiple de los mismos Mixin que ya usa `DestinoEntradaSerializer` (TKT-006,
    ciclo oasdiff): declara los campos de ContenidoComunCampos/DestinoCampos para que
    drf-spectacular los vea (antes solo estaban en `to_representation`, nunca como atributos de
    clase, así que el esquema generado no tenía ninguno). `to_representation` sigue siendo el
    único responsable de la serialización real; esta herencia es solo para introspección de
    esquema (Skill_Backend Regla 02: sin lógica nueva)."""

    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        destino = instance.destino
        base.update(_comunes_representacion(instance))
        base.update(
            {
                "pais_id": destino.pais_id,
                "resumen": destino.resumen,
                "descripcion_experta": destino.descripcion_experta,
                "tipos_ids": list(destino.tipos_aventura.values_list("contenido_id", flat=True)),
                "tipo_principal_id": destino.tipo_principal_id,
                "dificultad": destino.dificultad,
                "meses_mejor_epoca": list(destino.meses_mejor_epoca or []),
                "duracion_min_dias": destino.duracion_min_dias,
                "duracion_max_dias": destino.duracion_max_dias,
                "nivel_presupuesto": destino.nivel_presupuesto,
                "clima": destino.clima,
                "altitud_max_m": destino.altitud_max_m,
                "como_llegar": destino.como_llegar,
                "seguridad_riesgos": destino.seguridad_riesgos,
                "sostenibilidad": destino.sostenibilidad,
                "latitud": float(destino.latitud) if destino.latitud is not None else None,
                "longitud": float(destino.longitud) if destino.longitud is not None else None,
                "portada_id": instance.portada_id,
                "galeria_ids": list(
                    instance.galeria.order_by("orden").values_list("medio_id", flat=True)
                ),
            }
        )
        return base


class DestinoGuardadoSerializer(DestinoPanelSerializer):
    entidades_afectadas = _con_limite(EntidadTransitadaSerializer(many=True), max_length=24)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        contenido, entidades_afectadas = instance
        base = super().to_representation(contenido)
        base["entidades_afectadas"] = entidades_afectadas
        return base


class ItinerarioPanelSerializer(ContenidoPanelMetaSerializer, ComunesMixin, ItinerarioCamposMixin):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        itinerario = instance.itinerario
        base.update(_comunes_representacion(instance))
        base.update(
            {
                "destino_id": itinerario.destino_id,
                "resumen": itinerario.resumen,
                "duracion_dias": itinerario.duracion_dias,
                "dificultad": itinerario.dificultad,
                "tipos_ids": list(itinerario.tipos_aventura.values_list("contenido_id", flat=True)),
                "distancia_total_km": float(itinerario.distancia_total_km)
                if itinerario.distancia_total_km is not None
                else None,
                "desnivel_acumulado_m": itinerario.desnivel_acumulado_m,
                "riesgos_seguridad": itinerario.riesgos_seguridad,
                "portada_id": instance.portada_id,
                "galeria_ids": list(
                    instance.galeria.order_by("orden").values_list("medio_id", flat=True)
                ),
                "dias": [
                    {
                        "numero_dia": d.numero_dia,
                        "titulo": d.titulo,
                        "actividades": d.actividades,
                        "distancia_km": float(d.distancia_km)
                        if d.distancia_km is not None
                        else None,
                        "desnivel_positivo_m": d.desnivel_positivo_m,
                        "desnivel_negativo_m": d.desnivel_negativo_m,
                        "alojamiento_orientativo": d.alojamiento_orientativo,
                        "consejos": d.consejos,
                    }
                    for d in itinerario.dias.order_by("numero_dia")
                ],
            }
        )
        return base


class GuiaPanelSerializer(ContenidoPanelMetaSerializer, ComunesMixin, GuiaCamposMixin):
    palabras = serializers.IntegerField(min_value=0, allow_null=True, read_only=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        guia = instance.guia
        base.update(_comunes_representacion(instance))
        base.update(
            {
                "categoria_id": guia.categoria_id,
                "resumen": guia.resumen,
                "cuerpo": guia.cuerpo,
                "destinos_ids": list(guia.destinos.values_list("contenido_id", flat=True)),
                "tipos_ids": list(guia.tipos_aventura.values_list("contenido_id", flat=True)),
                "remite_a_metodologia": guia.remite_a_metodologia,
                "portada_id": instance.portada_id,
                "palabras": guia.palabras,
            }
        )
        return base


class TipoAventuraPanelSerializer(
    ContenidoPanelMetaSerializer, ComunesMixin, TipoAventuraCamposMixin
):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        tipo = instance.tipo_aventura
        base.update(_comunes_representacion(instance))
        base.update(
            {
                "resumen": tipo.resumen,
                "descripcion": tipo.descripcion,
                "nivel_exigencia": tipo.nivel_exigencia,
                "portada_id": instance.portada_id,
                "orden": tipo.orden,
                "checklist": [
                    {"texto": c.texto, "grupo": c.grupo, "esencial": c.esencial, "orden": c.orden}
                    for c in tipo.checklist.order_by("orden", "id")
                ],
            }
        )
        return base


class ColeccionPanelSerializer(ContenidoPanelMetaSerializer, ComunesMixin, ColeccionCamposMixin):
    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        coleccion = instance.coleccion
        base.update(_comunes_representacion(instance))
        base.update(
            {
                "resumen": coleccion.resumen,
                "descripcion": coleccion.descripcion,
                "portada_id": instance.portada_id,
                "elementos": [
                    {
                        "tipo_contenido": e.tipo_contenido,
                        "contenido_id": e.contenido_id,
                        "orden": e.orden,
                        "nota_editorial": e.nota_editorial,
                    }
                    for e in coleccion.elementos.order_by("orden", "id")
                ],
            }
        )
        return base


class TerminoGlosarioPanelSerializer(ContenidoPanelMetaSerializer, TerminoGlosarioCamposMixin):
    vinculado_en = _con_limite(
        ContenidoRefPanelSerializer(many=True, read_only=True), max_length=200
    )

    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        termino = instance.termino_glosario
        base.update(
            {
                "titulo": instance.titulo,
                "slug": instance.slug,
                "definicion": termino.definicion,
                "fecha_ultima_revision": instance.fecha_ultima_revision,
                "vinculado_en": [
                    {
                        "tipo": u.contenido.tipo,
                        "id": u.contenido_id,
                        "titulo": u.contenido.titulo,
                        "estado_editorial": u.contenido.estado_editorial,
                    }
                    for u in termino.usos.select_related("contenido")
                ],
            }
        )
        return base


class PaginaInstitucionalPanelSerializer(
    ContenidoPanelMetaSerializer, PaginaInstitucionalCamposMixin
):
    clave = serializers.ChoiceField(
        choices=[
            ClavePagina.ACERCA_DE,
            ClavePagina.POLITICA_DATOS,
            ClavePagina.POLITICA_COOKIES,
            ClavePagina.AVISO_LEGAL,
        ],
        read_only=True,
    )
    solo_administrador = serializers.BooleanField(read_only=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        base = super().to_representation(instance)
        pagina = instance.pagina
        base.update(
            {
                "titulo": instance.titulo,
                "cuerpo": pagina.cuerpo,
                "version_documento": pagina.version_documento,
                "vigente_desde": pagina.vigente_desde,
                "fecha_ultima_revision": instance.fecha_ultima_revision,
                "seo_titulo": instance.seo_titulo,
                "seo_descripcion": instance.seo_descripcion,
                "clave": pagina.clave,
                "solo_administrador": pagina.clave != ClavePagina.ACERCA_DE,
            }
        )
        return base


class ContenidoResumenPanelSerializer(serializers.Serializer[Any]):
    """components.schemas.ContenidoResumenPanel. Declara los campos (Skill_Backend Regla 13,
    TKT-006 ciclo oasdiff): un `to_representation` propio sin campos declarados no genera
    ninguna propiedad en el esquema drf-spectacular (`serializer.fields` queda vacío y el
    componente se descarta por no tener `properties`), aunque la respuesta real sea correcta."""

    id = IdSerializerField()
    tipo = _tipo_entidad_field()
    titulo = serializers.CharField(max_length=150)
    slug = serializers.CharField(max_length=120, allow_null=True, required=False)
    estado_editorial = _campo_estado_editorial()
    version = serializers.IntegerField(min_value=1)
    fecha_ultima_revision = serializers.DateField(allow_null=True, required=False)
    actualizado_en = serializers.DateTimeField()
    actualizado_por = ActorRefSerializer()
    publicado = serializers.BooleanField()
    url_publica = serializers.RegexField(r"^/[a-z0-9/-]*$", allow_null=True, required=False)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        from apps.contenido import services

        contenido = instance
        return {
            "id": contenido.pk,
            "tipo": contenido.tipo,
            "titulo": contenido.titulo,
            "slug": contenido.slug,
            "estado_editorial": contenido.estado_editorial,
            "version": contenido.version,
            "fecha_ultima_revision": contenido.fecha_ultima_revision,
            "actualizado_en": contenido.actualizado_en,
            "actualizado_por": {
                "id": contenido.actualizado_por_id,
                "etiqueta": f"#{contenido.actualizado_por_id}"
                if contenido.actualizado_por_id
                else "sistema",
            },
            "publicado": contenido.estado_editorial == "PUBLICADO",
            "url_publica": services._url_publica(contenido),
        }


class PaginaContenidoResumenSerializer(PaginaMetaSerializer):
    resultados = ContenidoResumenPanelSerializer(many=True)


PANEL_SERIALIZER: dict[str, type[serializers.Serializer[Any]]] = {
    T.DESTINO: DestinoPanelSerializer,
    T.ITINERARIO: ItinerarioPanelSerializer,
    T.GUIA: GuiaPanelSerializer,
    T.TIPO: TipoAventuraPanelSerializer,
    T.COLECCION: ColeccionPanelSerializer,
    T.TERMINO: TerminoGlosarioPanelSerializer,
    T.PAGINA: PaginaInstitucionalPanelSerializer,
}
ENTRADA_SERIALIZER: dict[str, type[serializers.Serializer[Any]]] = {
    T.DESTINO: DestinoEntradaSerializer,
    T.ITINERARIO: ItinerarioEntradaSerializer,
    T.GUIA: GuiaEntradaSerializer,
    T.TIPO: TipoAventuraEntradaSerializer,
    T.COLECCION: ColeccionEntradaSerializer,
    T.TERMINO: TerminoGlosarioEntradaSerializer,
}
ACTUALIZACION_SERIALIZER: dict[str, type[serializers.Serializer[Any]]] = {
    T.DESTINO: DestinoActualizacionSerializer,
    T.ITINERARIO: ItinerarioActualizacionSerializer,
    T.GUIA: GuiaActualizacionSerializer,
    T.TIPO: TipoAventuraActualizacionSerializer,
    T.COLECCION: ColeccionActualizacionSerializer,
    T.TERMINO: TerminoGlosarioActualizacionSerializer,
    T.PAGINA: PaginaInstitucionalActualizacionSerializer,
}
VISTA_PREVIA_SERIALIZER: dict[str, type[serializers.Serializer[Any]]] = {
    T.DESTINO: DestinoVistaPreviaSerializer,
    T.ITINERARIO: ItinerarioVistaPreviaSerializer,
    T.GUIA: GuiaVistaPreviaSerializer,
    T.TIPO: TipoAventuraVistaPreviaSerializer,
    T.COLECCION: ColeccionVistaPreviaSerializer,
    T.PAGINA: PaginaInstitucionalVistaPreviaSerializer,
}


class VistaPreviaSerializer(serializers.Serializer[Any]):
    """components.schemas.VistaPrevia (respuesta de POST .../vista-previa, TKT-006 ciclo
    oasdiff): antes sin esquema (`OpenApiResponse(description=...)` sin `response=`), por lo que
    drf-spectacular no documentaba ningún `content` para el 200 (response-media-type-removed)."""

    marca = serializers.ChoiceField(choices=["VISTA PREVIA – NO PUBLICADO"])
    forma = serializers.ChoiceField(
        choices=[
            "DestinoDetalle",
            "ItinerarioDetalle",
            "GuiaDetalle",
            "TipoAventuraDetalle",
            "ColeccionDetalle",
            "PaginaInstitucionalPublica",
        ]
    )
    datos = _ObjetoOpacoField()
    requisitos_publicacion = RequisitosPublicacionSerializer()
