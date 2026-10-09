"""Controles del gate de contrato con fixtures SINTÉTICOS (TKT-OPS-006, DEC-AUTO-250/251).

Uso:  python gate_contrato_controles.py [GATE]   (por defecto: gate_contrato.py de este directorio)

No dependen del contrato ni del backend reales (que cambian en cada ticket): un contrato mínimo y su
"implementación" idéntica, y en cada caso UNA variación con el código de salida esperado del gate.
Cada ejecución del gate tiene un límite de 60 s: los casos autorreferenciados (A*) colgaban el gate
anterior (explosión exponencial de comparar()/forma(), OBS-QA-OPS004-01) y ahora terminan en
milisegundos. Salida 1 si algún caso no da el resultado esperado o agota el tiempo.
F-QA022-01 (TKT-OPS-027): el gate hijo se lanza con PYTHONUTF8=1 y PYTHONIOENCODING=utf-8 y su
salida se decodifica con errors="replace" (en Windows sin PYTHONUTF8 fallaba con stdout None).
"""

from __future__ import annotations

import copy
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from typing import Any

import yaml

Doc = dict[str, Any]
# F-QA022-01: el hijo escribe UTF-8 sea cual sea la página de códigos local (Windows cp1252).
ENV_HIJO = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def ref(n: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{n}"}


def base() -> Doc:
    return {
        "openapi": "3.1.0",
        "info": {"title": "controles", "version": "1"},
        "paths": {
            "/x/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {"application/json": {"schema": ref("Obj")}},
                        },
                        "400": {
                            "description": "error",
                            "content": {"application/problem+json": {"schema": ref("Problem")}},
                        },
                    }
                }
            },
            "/lista": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {"application/json": {"schema": ref("Pagina")}},
                        }
                    }
                }
            },
        },
        "components": {
            "schemas": {
                "Obj": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "etiqueta": {"type": "string", "maxLength": 60},
                        "nodo": ref("Nodo"),
                    },
                },
                "Pagina": {
                    "allOf": [
                        {
                            "type": "object",
                            "properties": {"total": {"type": "integer"}},
                        },
                        {
                            "type": "object",
                            "properties": {"resultados": {"type": "array", "items": ref("Obj")}},
                        },
                    ]
                },
                "Problem": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "errors": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                },
                "Nodo": {"type": "object", "properties": {"v": {"type": "string"}}},
            }
        },
    }


def s(doc: Doc, nombre: str) -> Doc:
    return doc["components"]["schemas"][nombre]


# --- esquemas recursivos (se instalan en "Nodo" de ambos documentos) ---------------------------
NODO: Doc = {
    "type": "object",
    "properties": {
        "a": ref("Nodo"),
        "b": ref("Nodo"),
        "c": {"type": "array", "items": ref("Nodo")},
        "v": {"type": "string"},
    },
}
NODO_ANY: Doc = {
    "anyOf": [
        ref("Nodo"),
        ref("Nodo"),
        ref("Nodo"),
        {"type": "object", "properties": {"a": ref("Nodo"), "b": ref("Nodo")}},
    ]
}
MUTUO_A: Doc = {
    "type": "object",
    "properties": {"x": ref("B"), "y": ref("B"), "z": ref("B")},
}
MUTUO_B: Doc = {
    "type": "object",
    "properties": {
        "p": ref("Nodo"),
        "q": ref("Nodo"),
        "r": {"type": "array", "items": ref("Nodo")},
    },
}


def recursivo(nodo_c: Doc, nodo_g: Doc, b_c: Doc | None = None, b_g: Doc | None = None):
    def mutar(c: Doc, g: Doc) -> None:
        c["components"]["schemas"]["Nodo"] = copy.deepcopy(nodo_c)
        g["components"]["schemas"]["Nodo"] = copy.deepcopy(nodo_g)
        if b_c is not None and b_g is not None:
            c["components"]["schemas"]["B"] = copy.deepcopy(b_c)
            g["components"]["schemas"]["B"] = copy.deepcopy(b_g)

    return mutar


def con(cambio: Callable[[Doc], None], en_contrato: bool = False) -> Callable[[Doc, Doc], None]:
    return lambda c, g: cambio(c if en_contrato else g)


def _nodo_extra() -> Doc:
    n = copy.deepcopy(NODO)
    n["properties"]["z"] = {"type": "string"}
    return n


def _any_abierto() -> Doc:
    n = copy.deepcopy(NODO_ANY)
    n["anyOf"][3]["additionalProperties"] = {}
    return n


def _b_abierto() -> Doc:
    n = copy.deepcopy(MUTUO_B)
    n["additionalProperties"] = True
    return n


def _b_items_libres() -> Doc:
    n = copy.deepcopy(MUTUO_B)
    n["properties"]["r"]["items"] = {}
    return n


def _set(nombre: str, *ruta: str | int, valor: Any) -> Callable[[Doc], None]:
    def f(doc: Doc) -> None:
        nodo: Any = s(doc, nombre)
        for p in ruta[:-1]:
            nodo = nodo[p]
        nodo[ruta[-1]] = copy.deepcopy(valor)

    return f


def _ruta_extra(g: Doc) -> None:
    g["paths"]["/nueva"] = copy.deepcopy(g["paths"]["/lista"])


def _codigo_201(g: Doc) -> None:
    r = g["paths"]["/x/{id}"]["get"]["responses"]
    r["201"] = r.pop("200")


def _media_html(g: Doc) -> None:
    r = g["paths"]["/x/{id}"]["get"]["responses"]["200"]["content"]
    r["text/html"] = r.pop("application/json")


CASOS: list[tuple[str, Callable[[Doc, Doc], None] | None, int]] = [
    ("BASE contrato == implementación", None, 0),
    ("N1 operación no documentada", con(_ruta_extra), 1),
    ("N3 200 -> 201", con(_codigo_201), 1),
    ("N8 media type cambia", con(_media_html), 1),
    (
        "N10 propiedad extra",
        con(_set("Obj", "properties", "extra", valor={"type": "string"})),
        1,
    ),
    (
        "N13a additionalProperties {} vs cerrado",
        con(_set("Obj", "additionalProperties", valor={})),
        1,
    ),
    (
        "N13b additionalProperties true vs cerrado",
        con(_set("Obj", "additionalProperties", valor=True)),
        1,
    ),
    (
        "N13c additionalProperties tipado vs cerrado",
        con(_set("Obj", "additionalProperties", valor={"type": "string"})),
        1,
    ),
    (
        "N14a propiedad {} vs tipada",
        con(_set("Obj", "properties", "etiqueta", valor={})),
        1,
    ),
    (
        "N14b propiedad solo descriptiva vs tipada",
        con(
            _set(
                "Obj",
                "properties",
                "etiqueta",
                valor={"description": "x", "readOnly": True},
            )
        ),
        1,
    ),
    (
        "N14c items {} vs $ref",
        con(_set("Pagina", "allOf", 1, "properties", "resultados", "items", valor={})),
        1,
    ),
    (
        "N14d valor de mapa {} vs array tipado",
        con(_set("Problem", "properties", "errors", "additionalProperties", valor={})),
        1,
    ),
    (
        "N14e valor de mapa true vs array tipado",
        con(_set("Problem", "properties", "errors", "additionalProperties", valor=True)),
        1,
    ),
    (
        "N14f rama oneOf {} vs tipada",
        con(
            _set(
                "Obj",
                "properties",
                "etiqueta",
                valor={"oneOf": [{"type": "string"}, {}]},
            )
        ),
        1,
    ),
    (
        "N14g rama anyOf solo descriptiva vs tipada",
        con(
            _set(
                "Obj",
                "properties",
                "etiqueta",
                valor={"anyOf": [{"type": "string"}, {"description": "x"}]},
            )
        ),
        1,
    ),
    (
        "N14h {type: object} sin properties vs estructura",
        con(_set("Obj", "properties", "nodo", valor={"type": "object"})),
        1,
    ),
    (
        "N14i {type: array} sin items vs items",
        con(
            _set(
                "Pagina",
                "allOf",
                1,
                "properties",
                "resultados",
                valor={"type": "array"},
            )
        ),
        1,
    ),
    (
        "P1 solo cambia description",
        con(_set("Obj", "properties", "etiqueta", "description", valor="nueva")),
        0,
    ),
    (
        "P2 contrato sin tipo, implementación tipada",
        con(
            _set("Obj", "properties", "etiqueta", valor={"description": "libre"}),
            en_contrato=True,
        ),
        0,
    ),
    (
        "P3 contrato abierto, implementación con propiedad extra",
        lambda c, g: (
            _set("Obj", "additionalProperties", valor=True)(c),
            _set("Obj", "properties", "extra", valor={"type": "string"})(g),
        ),
        0,
    ),
    ("A1 autorreferenciado idéntico", recursivo(NODO, NODO), 0),
    ("A2 autorreferenciado + propiedad extra", recursivo(NODO, _nodo_extra()), 1),
    ("A3 anyOf autorreferenciado idéntico", recursivo(NODO_ANY, NODO_ANY), 0),
    (
        "A4 anyOf autorreferenciado + objeto abierto",
        recursivo(NODO_ANY, _any_abierto()),
        1,
    ),
    ("A5 recursión mutua idéntica", recursivo(MUTUO_A, MUTUO_A, MUTUO_B, MUTUO_B), 0),
    (
        "A6 recursión mutua + objeto abierto",
        recursivo(MUTUO_A, MUTUO_A, MUTUO_B, _b_abierto()),
        1,
    ),
    (
        "A7 recursión mutua + items {}",
        recursivo(MUTUO_A, MUTUO_A, MUTUO_B, _b_items_libres()),
        1,
    ),
]


def main() -> int:
    gate = (
        sys.argv[1]
        if len(sys.argv) > 1
        else str(pathlib.Path(__file__).with_name("gate_contrato.py"))
    )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # F-QA022-01
    fallos = 0
    with tempfile.TemporaryDirectory() as d:
        fc, fg, ff = (str(pathlib.Path(d, n)) for n in ("c.yaml", "g.yaml", "f.yaml"))
        for nombre, mutar, esperado in CASOS:
            c, g = base(), base()
            if mutar:
                mutar(c, g)
            for ruta, doc in ((fc, c), (fg, g)):
                with open(ruta, "w", encoding="utf-8") as f:
                    yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
            t = time.monotonic()
            try:
                p = subprocess.run(  # noqa: S603 (intérprete y gate propios, sin entrada externa)
                    [sys.executable, gate, fc, fg, ff],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=ENV_HIJO,
                    timeout=60,
                    check=False,
                )
                rc: int | str = p.returncode
                err = next(
                    (x[9:] for x in (p.stdout or "").splitlines() if x.startswith("::error::")),
                    "",
                )
            except subprocess.TimeoutExpired:
                rc, err = "TIMEOUT", ""
            ok = rc == esperado
            fallos += not ok
            marca = "OK " if ok else "MAL"
            dt = time.monotonic() - t
            sys.stdout.write(
                f"{marca} | {nombre:50} | esp {esperado} | rc {rc} | {dt:5.2f} s | {err[:80]}\n"
            )
    sys.stdout.write(f"controles: {len(CASOS)}; fallos: {fallos}\n")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
