"""Postproceso del esquema de drf-spectacular: convenciones estructurales del contrato.

contracts/openapi.yaml (API-first, ADR-API-002 §16) usa construcciones que drf-spectacular no
genera por sí solo. Sin cambiar el comportamiento de la API, este hook emite el esquema con la
misma estructura, para que el gate incremental de contrato (oasdiff breaking --fail-on WARN,
DEC-AUTO-196) compare significado y no forma:

1. Parámetros de ruta comunes a todas las operaciones de una ruta → a nivel de ruta (IdPath).
   Se hace en `GeneradorContrato`, después del saneado propio de spectacular (que no admite la
   clave `parameters` a nivel de ruta).
2. `{allOf: [$ref], readOnly}` que spectacular usa para enums de solo lectura → `$ref`.
3. Errores: los componentes ProblemaValidacion y ProblemaConUsos, cuando una vista los declara
   explícitamente (serializers de apps/core/api), se emiten como `allOf` sobre Problem. Las
   respuestas NO se reasignan por código de estado (OBS-QA004-09).
4. Páginas: `allOf` de PaginaMeta + `resultados` (DEC-AUTO-104).
5. Recursos del panel (DEC-AUTO-918, TKT-006 ciclo oasdiff): el contrato compone los schemas
   Panel/Entrada/Actualizacion/VistaPrevia de los 7 tipos de contenido y Pais/Region de
   taxonomías como `allOf` de componentes con nombre (ContenidoPanelMeta, ContenidoComunCampos,
   {Tipo}Campos, VersionCampo, IdOpcionalCampo, CamposOperacionPublicada). drf-spectacular no
   genera `allOf` a partir de herencia de clases Python (verificado empíricamente): los
   serializers Python declaran esos mismos campos por herencia múltiple de Mixins compartidos
   (apps/contenido/api/panel_serializers.py, apps/catalogos/api/serializers.py), así que el
   esquema aplanado ya trae, con tipo/formato/patrón correctos, la unión exacta de propiedades
   que el contrato reparte en esas ramas; aquí solo se reparte esa unión ya generada en los
   mismos sub-componentes, igual mecanismo que `_paginas` generalizado (`_dividir_en_allof`).
6. Campos con esquema declarado (TKT-012, deuda de los WARNING de oasdiff): `CampoConEsquema` y
   sus fábricas (`texto_plano`, `texto_html`, `url_http`, `id_contrato`, `lista_ids`...) emiten
   en el esquema las restricciones del contrato que drf-spectacular no deduce de un campo DRF
   (`contentMediaType`, `uniqueItems`, `format: int64` sin `maximum`, `number` sin `format`) y,
   cuando el contrato restringe más que el campo DRF por defecto, las APLICAN además en la
   validación real (patrón sin NUL, `https?://`, elementos únicos, rango bigint): el contrato
   manda y el esquema nunca documenta una restricción que la API no cumpla.
Es infraestructura (Skill_Backend Regla 10): no importa ninguna app.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.utils.deconstruct import deconstructible
from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.generators import SchemaGenerator
from rest_framework import serializers

METODOS = frozenset({"get", "put", "post", "delete", "patch", "head", "options", "trace"})
_CAMPOS_META = ("total", "pagina", "tamano_pagina", "total_paginas", "siguiente", "anterior")
_REF = "#/components/schemas/"

PAGINA_META: dict[str, Any] = {
    "type": "object",
    "required": list(_CAMPOS_META),
    "properties": {
        "total": {"type": "integer", "minimum": 0},
        "pagina": {"type": "integer", "minimum": 1},
        "tamano_pagina": {"type": "integer", "minimum": 1},
        "total_paginas": {"type": "integer", "minimum": 0},
        "siguiente": {"type": ["string", "null"], "format": "uri-reference"},
        "anterior": {"type": ["string", "null"], "format": "uri-reference"},
    },
}
PROBLEMA_VALIDACION: dict[str, Any] = {
    "allOf": [{"$ref": f"{_REF}Problem"}, {"type": "object", "required": ["errors"]}]
}
REFERENCIA_USO: dict[str, Any] = {
    "type": "object",
    "required": ["tipo_entidad", "id", "titulo"],
    "properties": {
        "tipo_entidad": {"type": "string", "maxLength": 40},
        "id": {"type": "integer", "format": "int64", "minimum": 1},
        "titulo": {"type": "string", "maxLength": 150},
        "estado_editorial": {
            "oneOf": [{"$ref": f"{_REF}EstadoEditorial"}, {"type": "null"}],
        },
    },
}
ESTADO_EDITORIAL: dict[str, Any] = {"type": "string", "enum": ["BORRADOR", "PUBLICADO", "RETIRADO"]}
PROBLEMA_CON_USOS: dict[str, Any] = {
    "allOf": [
        {"$ref": f"{_REF}Problem"},
        {
            "type": "object",
            "properties": {
                "usos": {
                    "type": "array",
                    "maxItems": 100,
                    "items": {"$ref": f"{_REF}ReferenciaUso"},
                },
                "total_usos": {"type": "integer", "minimum": 0},
            },
        },
    ]
}


def _parametros_a_nivel_de_ruta(rutas: dict[str, Any]) -> None:
    for item in rutas.values():
        operaciones = [op for metodo, op in item.items() if metodo in METODOS]
        if not operaciones:
            continue
        comunes = [
            parametro
            for parametro in operaciones[0].get("parameters", [])
            if parametro.get("in") == "path"
            and all(parametro in op.get("parameters", []) for op in operaciones)
        ]
        if not comunes:
            continue
        item["parameters"] = comunes
        for op in operaciones:
            restantes = [p for p in op.get("parameters", []) if p not in comunes]
            if restantes:
                op["parameters"] = restantes
            else:
                op.pop("parameters", None)


def _sin_envoltorio_readonly(nodo: Any) -> Any:
    if isinstance(nodo, list):
        return [_sin_envoltorio_readonly(elemento) for elemento in nodo]
    if not isinstance(nodo, dict):
        return nodo
    todos = nodo.get("allOf")
    if (
        isinstance(todos, list)
        and len(todos) == 1
        and isinstance(todos[0], dict)
        and set(todos[0]) == {"$ref"}
        and set(nodo) <= {"allOf", "readOnly", "description"}
    ):
        return {"$ref": todos[0]["$ref"]}
    return {clave: _sin_envoltorio_readonly(valor) for clave, valor in nodo.items()}


# ---------------------------------------------------------------------------------------------
# Composición allOf de los recursos del panel (DEC-AUTO-918, punto 5 del docstring del módulo).
# ---------------------------------------------------------------------------------------------
# Nombres de campo de cada "capa" compartida (contracts/openapi.yaml): coinciden con los Mixin de
# Python que las declaran (ComunesMixin, VersionMixin, IdOpcionalMixin, OperacionPublicadaMixin,
# ContenidoPanelMetaSerializer) — nunca hay que tocar esto si solo cambian tipo/formato/patrón de
# un campo (drf-spectacular ya los genera bien); solo si el contrato o los Mixin AÑADEN o QUITAN
# un campo de una de estas capas.
_CONTENIDO_PANEL_META = frozenset(
    {
        "id", "tipo", "estado_editorial", "version", "slug_bloqueado", "primera_publicacion_en",
        "publicado_actualizado_en", "retirado_en", "motivo_retiro", "creado_en", "actualizado_en",
        "creado_por", "actualizado_por", "url_publica", "requisitos_publicacion", "referencias",
    }
)  # fmt: skip
_CONTENIDO_PANEL_META_REQUERIDO = (
    "id", "tipo", "estado_editorial", "version", "slug_bloqueado", "creado_en", "actualizado_en",
    "creado_por", "actualizado_por", "requisitos_publicacion", "referencias",
)  # fmt: skip
_CONTENIDO_COMUN_CAMPOS = frozenset(
    {
        "titulo", "slug", "fecha_ultima_revision", "seo_titulo", "seo_descripcion", "relaciones",
        "terminos_ids", "fuentes",
    }
)  # fmt: skip
_VERSION_CAMPO = frozenset({"version"})
_ID_OPCIONAL_CAMPO = frozenset({"id"})
_CAMPOS_OPERACION_PUBLICADA = frozenset(
    {"copublicar_tipos", "confirmar_cascada", "cascada_confirmada"}
)

# Rama = (nombre_de_componente | None, campos_exactos | None, requerido_de_la_rama | None).
#   - nombre + campos: crea/reusa un componente con nombre con exactamente esos campos.
#   - nombre + campos=None ("resto"): idem, con los campos que no caen en ninguna otra rama --
#     para la parte específica del tipo ({Tipo}Campos), sin enumerar aquí sus nombres.
#   - nombre=None: rama anónima sin $ref, con exactamente esos campos (composiciones inline del
#     contrato: el `id` de Pais/Region, los campos de solo lectura de Guia/TerminoGlosario/
#     PaginaInstitucional Panel).
# Como máximo una rama "resto" por composición.
Rama = tuple[str | None, frozenset[str] | None, tuple[str, ...] | None]

_META: Rama = ("ContenidoPanelMeta", _CONTENIDO_PANEL_META, _CONTENIDO_PANEL_META_REQUERIDO)
_COMUN: Rama = ("ContenidoComunCampos", _CONTENIDO_COMUN_CAMPOS, None)
_VERSION: Rama = ("VersionCampo", _VERSION_CAMPO, ("version",))
_ID_OPC: Rama = ("IdOpcionalCampo", _ID_OPCIONAL_CAMPO, None)
_OPERACION_PUBLICADA: Rama = ("CamposOperacionPublicada", _CAMPOS_OPERACION_PUBLICADA, None)


def _resto(nombre_componente: str) -> Rama:
    return (nombre_componente, None, None)


def _anon(campos: frozenset[str], requerido: tuple[str, ...] | None = None) -> Rama:
    return (None, campos, requerido)


# (nombre generado por drf-spectacular, ramas en el mismo orden que el contrato, requerido a
# nivel superior o None). Los nombres de request llevan el sufijo "Request" que añade
# COMPONENT_SPLIT_REQUEST=True cuando el serializer solo se usa como cuerpo de petición
# (verificado leyendo el esquema generado, no supuesto).
_COMPOSICIONES: tuple[tuple[str, tuple[Rama, ...], tuple[str, ...] | None], ...] = (
    # --- Destino ---
    ("DestinoPanel", (_META, _COMUN, _resto("DestinoCampos")), None),
    ("DestinoEntradaRequest", (_COMUN, _resto("DestinoCampos")), ("titulo",)),
    (
        "DestinoActualizacionRequest",
        (_COMUN, _resto("DestinoCampos"), _VERSION, _OPERACION_PUBLICADA),
        ("titulo", "version"),
    ),
    (
        "DestinoVistaPreviaRequest",
        (_COMUN, _resto("DestinoCampos"), _ID_OPC),
        ("titulo",),
    ),
    # --- Itinerario ---
    ("ItinerarioPanel", (_META, _COMUN, _resto("ItinerarioCampos")), None),
    ("ItinerarioEntradaRequest", (_COMUN, _resto("ItinerarioCampos")), ("titulo",)),
    (
        "ItinerarioActualizacionRequest",
        (_COMUN, _resto("ItinerarioCampos"), _VERSION),
        ("titulo", "version"),
    ),
    (
        "ItinerarioVistaPreviaRequest",
        (_COMUN, _resto("ItinerarioCampos"), _ID_OPC),
        ("titulo",),
    ),
    # --- Guía (Panel: rama anónima final "palabras", solo lectura) ---
    (
        "GuiaPanel",
        (_META, _COMUN, _resto("GuiaCampos"), _anon(frozenset({"palabras"}))),
        None,
    ),
    ("GuiaEntradaRequest", (_COMUN, _resto("GuiaCampos")), ("titulo",)),
    (
        "GuiaActualizacionRequest",
        (_COMUN, _resto("GuiaCampos"), _VERSION),
        ("titulo", "version"),
    ),
    ("GuiaVistaPreviaRequest", (_COMUN, _resto("GuiaCampos"), _ID_OPC), ("titulo",)),
    # --- Tipo de aventura ---
    ("TipoAventuraPanel", (_META, _COMUN, _resto("TipoAventuraCampos")), None),
    ("TipoAventuraEntradaRequest", (_COMUN, _resto("TipoAventuraCampos")), ("titulo",)),
    (
        "TipoAventuraActualizacionRequest",
        (_COMUN, _resto("TipoAventuraCampos"), _VERSION),
        ("titulo", "version"),
    ),
    (
        "TipoAventuraVistaPreviaRequest",
        (_COMUN, _resto("TipoAventuraCampos"), _ID_OPC),
        ("titulo",),
    ),
    # --- Colección ---
    ("ColeccionPanel", (_META, _COMUN, _resto("ColeccionCampos")), None),
    ("ColeccionEntradaRequest", (_COMUN, _resto("ColeccionCampos")), ("titulo",)),
    (
        "ColeccionActualizacionRequest",
        (_COMUN, _resto("ColeccionCampos"), _VERSION),
        ("titulo", "version"),
    ),
    (
        "ColeccionVistaPreviaRequest",
        (_COMUN, _resto("ColeccionCampos"), _ID_OPC),
        ("titulo",),
    ),
    # --- Término de glosario (sin ContenidoComunCampos: TerminoGlosarioCampos ya trae titulo) ---
    (
        "TerminoGlosarioPanel",
        (
            _META,
            _resto("TerminoGlosarioCampos"),
            _anon(frozenset({"vinculado_en"}), ("vinculado_en",)),
        ),
        None,
    ),
    ("TerminoGlosarioEntradaRequest", (_resto("TerminoGlosarioCampos"),), ("titulo",)),
    (
        "TerminoGlosarioActualizacionRequest",
        (_resto("TerminoGlosarioCampos"), _VERSION),
        ("titulo", "version"),
    ),
    # --- Página institucional (sin ContenidoComunCampos ni Entrada: no se crean, AC-033) ---
    (
        "PaginaInstitucionalPanel",
        (
            _META,
            _resto("PaginaInstitucionalCampos"),
            _anon(frozenset({"clave", "solo_administrador"}), ("clave", "solo_administrador")),
        ),
        None,
    ),
    (
        "PaginaInstitucionalActualizacionRequest",
        (_resto("PaginaInstitucionalCampos"), _VERSION),
        ("titulo", "cuerpo", "version_documento", "vigente_desde", "version"),
    ),
    (
        "PaginaInstitucionalVistaPreviaRequest",
        (_resto("PaginaInstitucionalCampos"), _ID_OPC),
        ("titulo",),
    ),
    # --- Taxonomías: Región y País (composición propia, sin ContenidoPanelMeta) ---
    ("Region", (_anon(frozenset({"id"}), ("id",)), _resto("RegionCampos")), None),
    (
        "RegionEntradaRequest",
        (_resto("RegionCampos"),),
        ("nombre", "slug", "continente", "orden", "activo"),
    ),
    ("Pais", (_anon(frozenset({"id"}), ("id",)), _resto("PaisCampos")), None),
    (
        "PaisEntradaRequest",
        (_resto("PaisCampos"),),
        ("nombre", "slug", "codigo_iso2", "region_id", "activo"),
    ),
    # --- TKT-012: resto de recursos compuestos con allOf en el contrato. La salida va SIEMPRE
    # antes que la entrada: el componente {X}Campos compartido se crea (setdefault) con la
    # primera composición que lo usa, y en dirección "response" drf-spectacular no añade el
    # `minLength: 1` implícito de `allow_blank=False` que el contrato no declara.
    (
        "CategoriaGuiaPanel",
        (_anon(frozenset({"id"}), ("id",)), _resto("CategoriaGuiaCampos")),
        None,
    ),
    (
        "CategoriaGuiaEntradaRequest",
        (_resto("CategoriaGuiaCampos"),),
        ("nombre", "slug", "descripcion", "orden", "activo"),
    ),
    ("Licencia", (_anon(frozenset({"id"}), ("id",)), _resto("LicenciaCampos")), None),
    (
        "LicenciaEntradaRequest",
        (_resto("LicenciaCampos"),),
        ("codigo", "nombre", "requiere_atribucion", "compatible_publicacion", "activo"),
    ),
    # NivelEscala (pública) ya existe con exactamente esos campos: la rama la reutiliza.
    ("NivelEscalaPanel", (_anon(frozenset({"id"}), ("id",)), _resto("NivelEscala")), None),
    (
        "ConfigInicioPanel",
        (
            _resto("ConfigInicioCampos"),
            _anon(
                frozenset({"actualizado_en", "actualizado_por", "referencias"}),
                ("actualizado_en", "actualizado_por", "referencias"),
            ),
        ),
        None,
    ),
    (
        "ConfigInicioEntradaRequest",
        (_resto("ConfigInicioCampos"),),
        (
            "hero_titular",
            "hero_subtitulo",
            "hero_medio_id",
            "destinos_ids",
            "itinerarios_ids",
            "guias_ids",
        ),
    ),
    (
        "ConfiguracionSitio",
        (
            _resto("ConfiguracionSitioCampos"),
            _anon(frozenset({"actualizado_en"}), ("actualizado_en",)),
        ),
        None,
    ),
    (
        "ConfiguracionSitioEntradaRequest",
        (_resto("ConfiguracionSitioCampos"),),
        ("nombre_marca", "texto_descargo"),
    ),
    # Contenido: extensiones de un componente ya existente ($ref + rama anónima).
    (
        "RevisionDetalle",
        (_resto("RevisionResumen"), _anon(frozenset({"instantanea"}), ("instantanea",))),
        None,
    ),
    (
        "EntidadTransitada",
        (
            _resto("ContenidoRefPanel"),
            _anon(
                frozenset({"version", "numero_revision", "url_publica", "origen"}),
                ("version", "origen"),
            ),
        ),
        None,
    ),
    (
        "DestinoGuardado",
        (
            _resto("DestinoPanel"),
            _anon(frozenset({"entidades_afectadas"}), ("entidades_afectadas",)),
        ),
        None,
    ),
)


def _rama_schema(
    esquemas: dict[str, Any],
    propiedades: dict[str, Any],
    ref_nombre: str | None,
    campos: frozenset[str],
    requerido: tuple[str, ...] | None,
) -> dict[str, Any]:
    cuerpo: dict[str, Any] = {
        "type": "object",
        "properties": {nombre: propiedades[nombre] for nombre in sorted(campos)},
    }
    if requerido:
        cuerpo["required"] = list(requerido)
    if ref_nombre is None:
        return cuerpo
    esquemas.setdefault(ref_nombre, cuerpo)
    return {"$ref": f"{_REF}{ref_nombre}"}


def _dividir_en_allof(
    esquemas: dict[str, Any],
    nombre: str,
    ramas: tuple[Rama, ...],
    requerido_top: tuple[str, ...] | None,
) -> None:
    """Reescribe `esquemas[nombre]` (un objeto plano ya generado por drf-spectacular) como
    `allOf` de `ramas`, replicando la composición del contrato para ese componente. No reescribe
    si el conjunto de propiedades generado no coincide EXACTAMENTE con la unión de las ramas
    (mismo criterio de seguridad que `_paginas`): evita enmascarar una diferencia real de campos
    entre la implementación y el contrato en vez de corregirla."""
    if nombre not in esquemas:
        return
    esquema = esquemas[nombre]
    propiedades = esquema.get("properties") or {}
    nombres_propiedades = set(propiedades)

    con_campos: list[tuple[str | None, frozenset[str], tuple[str, ...] | None]] = [
        (ref, campos, req) for ref, campos, req in ramas if campos is not None
    ]
    num_resto = sum(1 for _ref, campos, _req in ramas if campos is None)
    if num_resto > 1:
        return  # composición mal declarada (más de un "resto"): no reescribir

    asignadas: set[str] = set()
    for _ref, campos, _req in con_campos:
        if campos & asignadas:
            return  # ramas solapadas: no reescribir
        asignadas |= campos
    if not asignadas <= nombres_propiedades:
        return  # el generado no tiene todos los campos esperados: posible diferencia real

    resto = nombres_propiedades - asignadas
    if num_resto and not resto:
        return  # se esperaban campos propios del tipo y no queda ninguno sin asignar
    if not num_resto and resto:
        return  # sobran propiedades sin asignar a ninguna rama: no coincide

    resto_congelado = frozenset(resto)
    ramas_finales = [
        _rama_schema(
            esquemas, propiedades, ref, campos if campos is not None else resto_congelado, req
        )
        for ref, campos, req in ramas
    ]
    nuevo: dict[str, Any] = {"allOf": ramas_finales}
    if requerido_top:
        nuevo["required"] = list(requerido_top)
    esquemas[nombre] = nuevo


def _recursos_del_panel(esquemas: dict[str, Any]) -> None:
    for nombre, ramas, requerido_top in _COMPOSICIONES:
        _dividir_en_allof(esquemas, nombre, ramas, requerido_top)


def _paginas(esquemas: dict[str, Any]) -> None:
    for nombre, esquema in list(esquemas.items()):
        propiedades = esquema.get("properties") or {}
        if set(propiedades) != {*_CAMPOS_META, "resultados"}:
            continue
        esquemas[nombre] = {
            "allOf": [
                {"$ref": f"{_REF}PaginaMeta"},
                {
                    "type": "object",
                    "required": ["resultados"],
                    "properties": {"resultados": propiedades["resultados"]},
                },
            ]
        }
        esquemas.setdefault("PaginaMeta", PAGINA_META)


def alinear_con_contrato(
    result: dict[str, Any], generator: Any, request: Any, public: bool
) -> dict[str, Any]:
    """POSTPROCESSING_HOOK de drf-spectacular (se ejecuta tras el de enums)."""
    rutas = result.get("paths") or {}
    esquemas = result.setdefault("components", {}).setdefault("schemas", {})
    _paginas(esquemas)
    _recursos_del_panel(esquemas)
    # Solo se reescribe la DEFINICIÓN de los componentes que las vistas declaran explícitamente
    # (OBS-QA004-09): una respuesta documentada con otro esquema no se toca y el gate la compara.
    if "ProblemaValidacion" in esquemas:
        esquemas["ProblemaValidacion"] = PROBLEMA_VALIDACION
    if "ProblemaConUsos" in esquemas:
        esquemas["ProblemaConUsos"] = PROBLEMA_CON_USOS
        esquemas["ReferenciaUso"] = REFERENCIA_USO
        esquemas.setdefault("EstadoEditorial", ESTADO_EDITORIAL)
    result["paths"] = _sin_min_length_marcado(_sin_envoltorio_readonly(rutas))
    result["components"]["schemas"] = _sin_min_length_marcado(_sin_envoltorio_readonly(esquemas))
    return result


class GeneradorContrato(SchemaGenerator):
    """DEFAULT_GENERATOR_CLASS: aplica el paso 1 sobre el esquema ya saneado."""

    def get_schema(self, request: Any = None, public: bool = False) -> dict[str, Any]:
        esquema: dict[str, Any] = super().get_schema(  # type: ignore[no-untyped-call]
            request=request, public=public
        )
        _parametros_a_nivel_de_ruta(esquema.get("paths") or {})
        return esquema


# ---------------------------------------------------------------------------------------------
# 6. Campos con esquema declarado (TKT-012, punto 6 del docstring del módulo).
# ---------------------------------------------------------------------------------------------
ID_MAXIMO = 2**63 - 1
# drf-spectacular emite `\x00` como `\u0000` (`_insert_field_validators`, "unify escaping"): el
# patrón generado es literalmente el del contrato (`^[^\u0000]*$`).
PATRON_SIN_NUL = r"^[^\x00]*$"
PATRON_URL_HTTP = r"^https?://[^\x00]*$"


@deconstructible
class ValidadorRangoBigint:
    """Rechaza un id mayor que el máximo de un bigint de PostgreSQL (DB_HANDOFF) sin declararlo
    como `maximum` en el esquema: `components.schemas.Id` del contrato no tiene `maximum`, pero
    la API nunca debe dejar pasar al ORM un entero que la columna no puede representar."""

    def __call__(self, valor: int | None) -> None:
        if valor is not None and valor > ID_MAXIMO:
            raise serializers.ValidationError(
                f"Asegúrese de que este valor es menor o igual a {ID_MAXIMO}.", code="max_value"
            )

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, ValidadorRangoBigint)

    def __hash__(self) -> int:
        return hash(ValidadorRangoBigint)


@deconstructible
class ValidadorSinRepetidos:
    """`uniqueItems: true` del contrato aplicado de verdad: una lista con elementos repetidos es
    un 400 de validación, no se deduplica en silencio."""

    def __call__(self, valor: list[Any]) -> None:
        try:
            repetidos = len(valor) != len(set(valor))
        except TypeError:  # elementos no hashables
            repetidos = any(elemento in valor[:i] for i, elemento in enumerate(valor))
        if repetidos:
            raise serializers.ValidationError(
                "No puede haber elementos repetidos.", code="elementos_repetidos"
            )

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, ValidadorSinRepetidos)

    def __hash__(self) -> int:
        return hash(ValidadorSinRepetidos)


class CampoConEsquema:
    """Mixin de campo DRF con ajustes declarativos de su esquema OpenAPI.

    `esquema_extra` se fusiona sobre el esquema que drf-spectacular genera para el campo y
    `esquema_sin` quita claves de él (también el `minLength: 1` que drf-spectacular añade por
    `allow_blank=False` después de la extensión: lo retira el postproceso, TKT-032). Se pasan
    como kwargs del constructor (no como atributos puestos después): `Field.__deepcopy__`
    reconstruye cada campo desde sus `_args`/`_kwargs` originales al instanciar el serializer,
    así que solo lo que viaja en el constructor sobrevive (mismo motivo que `_con_limite` en
    apps/contenido/api/panel_serializers.py). Las restricciones de validación (min/max,
    longitud, patrón) se siguen declarando con los argumentos normales del campo, que
    drf-spectacular ya traduce y DRF ya aplica."""

    esquema_extra: dict[str, Any]
    esquema_sin: frozenset[str]

    def __init__(
        self,
        *args: Any,
        esquema_extra: dict[str, Any] | None = None,
        esquema_sin: Iterable[str] = (),
        **kwargs: Any,
    ) -> None:
        self.esquema_extra = dict(esquema_extra or {})
        self.esquema_sin = frozenset(esquema_sin)
        super().__init__(*args, **kwargs)


class TextoConEsquema(CampoConEsquema, serializers.RegexField):
    """`RegexField` (patrón validado y documentado) con ajustes de esquema."""


class EnteroConEsquema(CampoConEsquema, serializers.IntegerField):
    """`IntegerField` con ajustes de esquema."""


class NumeroConEsquema(CampoConEsquema, serializers.FloatField):
    """`FloatField` con ajustes de esquema."""


class ListaConEsquema(CampoConEsquema, serializers.ListField):
    """`ListField` con ajustes de esquema."""


_MARCA_SIN_MIN_LENGTH = "x-brujula-sin-minLength"


def _sin_min_length_marcado(nodo: Any) -> Any:
    """Postproceso de `esquema_sin=("minLength",)` (TKT-032): quita el `minLength` que
    drf-spectacular añade fuera de la extensión de campo y la marca interna."""
    if isinstance(nodo, list):
        return [_sin_min_length_marcado(elemento) for elemento in nodo]
    if not isinstance(nodo, dict):
        return nodo
    marcado = nodo.get(_MARCA_SIN_MIN_LENGTH) is True
    return {
        clave: _sin_min_length_marcado(valor)
        for clave, valor in nodo.items()
        if clave != _MARCA_SIN_MIN_LENGTH and not (marcado and clave == "minLength")
    }


class _ExtensionCampoConEsquema(OpenApiSerializerFieldExtension):  # type: ignore[no-untyped-call]
    target_class = CampoConEsquema
    match_subclasses = True

    def map_serializer_field(self, auto_schema: Any, direction: Any) -> Any:
        esquema = auto_schema._map_serializer_field(self.target, direction, bypass_extensions=True)
        if esquema is None:
            return None
        sin = self.target.esquema_sin
        esquema = {clave: valor for clave, valor in esquema.items() if clave not in sin}
        # drf-spectacular vuelve a aplicar `nullable` (append_meta) sobre lo que devuelve la
        # extensión: se quita aquí para no duplicar el "null" de `type`.
        tipo = esquema.get("type")
        if isinstance(tipo, list) and "null" in tipo:
            resto = [t for t in tipo if t != "null"]
            esquema["type"] = resto[0] if len(resto) == 1 else resto
        esquema.update(self.target.esquema_extra)
        if "minLength" in sin:
            # El `minLength: 1` implícito de `allow_blank=False` lo añade drf-spectacular DESPUÉS
            # de la extensión (`append_meta`); se marca aquí y lo quita el postproceso.
            esquema[_MARCA_SIN_MIN_LENGTH] = True
        return esquema


def texto_sin_nul(**kwargs: Any) -> serializers.RegexField:
    """Texto plano del contrato (`pattern: '^[^\\u0000]*$'`)."""
    return serializers.RegexField(PATRON_SIN_NUL, **kwargs)


def texto_html(**kwargs: Any) -> TextoConEsquema:
    """Texto enriquecido del contrato (`contentMediaType: text/html` + patrón sin NUL)."""
    return TextoConEsquema(
        PATRON_SIN_NUL, esquema_extra={"contentMediaType": "text/html"}, **kwargs
    )


def url_http(**kwargs: Any) -> TextoConEsquema:
    """URL absoluta http(s) del contrato (`format: uri` + `pattern: '^https?://[^\\u0000]*$'`)."""
    return TextoConEsquema(PATRON_URL_HTTP, esquema_extra={"format": "uri"}, **kwargs)


def id_contrato(**kwargs: Any) -> EnteroConEsquema:
    """`components.schemas.Id` (`integer`, `int64`, `minimum: 1`, sin `maximum`)."""
    validadores = [*kwargs.pop("validators", []), ValidadorRangoBigint()]
    return EnteroConEsquema(
        min_value=1, validators=validadores, esquema_extra={"format": "int64"}, **kwargs
    )


def numero(**kwargs: Any) -> NumeroConEsquema:
    """`type: number` sin `format` (el contrato no declara `double`)."""
    return NumeroConEsquema(esquema_sin=("format",), **kwargs)


def lista_unica(child: Any, **kwargs: Any) -> ListaConEsquema:
    """Lista con `uniqueItems: true` validado de verdad (`ValidadorSinRepetidos`). Admite
    `esquema_extra` adicional (p. ej. el `default: []` que drf-spectacular no documenta cuando el
    `default` es un callable)."""
    validadores = [*kwargs.pop("validators", []), ValidadorSinRepetidos()]
    extra = {"uniqueItems": True, **kwargs.pop("esquema_extra", {})}
    return ListaConEsquema(child=child, validators=validadores, esquema_extra=extra, **kwargs)


def lista_ids(max_length: int, **kwargs: Any) -> ListaConEsquema:
    """Lista de `Id` sin repetidos (`uniqueItems: true`, `maxItems`); opcional y vacía por
    defecto salvo que se indique `required=True`."""
    kwargs.setdefault("required", False)
    if not kwargs["required"]:
        kwargs.setdefault("default", list)
    return lista_unica(id_contrato(), max_length=max_length, **kwargs)
