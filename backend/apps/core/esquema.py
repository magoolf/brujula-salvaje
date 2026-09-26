"""Postproceso del esquema de drf-spectacular: convenciones estructurales del contrato.

contracts/openapi.yaml (API-first, ADR-API-002 §16) usa construcciones que drf-spectacular no
genera por sí solo. Sin cambiar el comportamiento de la API, este hook emite el esquema con la
misma estructura, para que el gate incremental de contrato (oasdiff breaking --fail-on WARN,
DEC-AUTO-196) compare significado y no forma:

1. Parámetros de ruta comunes a todas las operaciones de una ruta → a nivel de ruta (IdPath).
   Se hace en `GeneradorContrato`, después del saneado propio de spectacular (que no admite la
   clave `parameters` a nivel de ruta).
2. `{allOf: [$ref], readOnly}` que spectacular usa para enums de solo lectura → `$ref`.
3. Errores: ProblemaValidacion (400/422) y ProblemaConUsos (409) como `allOf` sobre Problem.
4. Páginas: `allOf` de PaginaMeta + `resultados` (DEC-AUTO-104).
Es infraestructura (Skill_Backend Regla 10): no importa ninguna app.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.generators import SchemaGenerator

METODOS = frozenset({"get", "put", "post", "delete", "patch", "head", "options", "trace"})
_CAMPOS_META = ("total", "pagina", "tamano_pagina", "total_paginas", "siguiente", "anterior")
_REF = "#/components/schemas/"
MEDIA_TYPE_PROBLEMA = "application/problem+json"

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


def _respuestas_de_error(rutas: dict[str, Any]) -> None:
    for item in rutas.values():
        for metodo, op in item.items():
            if metodo not in METODOS:
                continue
            for codigo, respuesta in (op.get("responses") or {}).items():
                contenido = (respuesta.get("content") or {}).get(MEDIA_TYPE_PROBLEMA)
                if contenido is None:
                    continue
                if str(codigo) in ("400", "422"):
                    contenido["schema"] = {"$ref": f"{_REF}ProblemaValidacion"}
                elif str(codigo) == "409":
                    contenido["schema"] = {"$ref": f"{_REF}ProblemaConUsos"}


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
    _respuestas_de_error(rutas)
    _paginas(esquemas)
    if "Problem" in esquemas:
        esquemas["ProblemaValidacion"] = PROBLEMA_VALIDACION
        esquemas["ProblemaConUsos"] = PROBLEMA_CON_USOS
        esquemas["ReferenciaUso"] = REFERENCIA_USO
        esquemas.setdefault("EstadoEditorial", ESTADO_EDITORIAL)
    result["paths"] = _sin_envoltorio_readonly(rutas)
    result["components"]["schemas"] = _sin_envoltorio_readonly(esquemas)
    return result


class GeneradorContrato(SchemaGenerator):
    """DEFAULT_GENERATOR_CLASS: aplica el paso 1 sobre el esquema ya saneado."""

    def get_schema(self, request: Any = None, public: bool = False) -> dict[str, Any]:
        esquema: dict[str, Any] = super().get_schema(  # type: ignore[no-untyped-call]
            request=request, public=public
        )
        _parametros_a_nivel_de_ruta(esquema.get("paths") or {})
        return esquema
