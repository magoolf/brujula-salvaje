"""Gate de contrato INCREMENTAL por OPERACIÓN (DEC-AUTO-196; TKT-OPS-004, DEC-AUTO-211).

Uso:  python gate_contrato.py CONTRATO GENERADO CONTRATO_FILTRADO
      (luego: oasdiff breaking CONTRATO_FILTRADO GENERADO --fail-on WARN)

El contrato (API-first) tiene todas las operaciones escritas a mano; drf-spectacular solo genera lo
implementado. Este paso comprueba lo que "oasdiff breaking" no ve y prepara su entrada:

  1) Toda operación (método + ruta) generada existe en el contrato               (N1, N2)
  2) Por operación, códigos de estado generados ⊆ códigos del contrato
     (exacto, rango "4XX" o "default")                                            (N3, N9)
  3) Por operación y código, media types generados ⊆ los del contrato             (N8)
  4) Por operación, código y media type, las propiedades de respuesta generadas
     ⊆ las del contrato, recursivo (allOf fusionado; oneOf/anyOf como unión).
     Solo se admiten propiedades nuevas si el objeto del contrato declara
     additionalProperties true o un esquema (mapa libre, p. ej. "errors")        (N10)
  5) Escribe CONTRATO_FILTRADO: el contrato con SOLO las operaciones implementadas
     (filtrado por operación, no por ruta), para que oasdiff no marque como
     eliminadas las operaciones aún no implementadas de una ruta parcial         (N11)
     y compare el resto (N3-N8, N12) con --fail-on WARN.

Salida 1 si cualquier comprobación falla (anotaciones ::error:: de GitHub Actions).
Solo depende de PyYAML (presente en el entorno del backend vía drf-spectacular).
"""

from __future__ import annotations

import copy
import re
import sys
from typing import Any

import yaml

METODOS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}
errores: list[str] = []


def cargar(ruta: str) -> dict[str, Any]:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def norm(p: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", p)


def operaciones(doc: dict[str, Any]) -> dict[tuple[str, str], tuple[str, dict[str, Any]]]:
    return {
        (norm(p), m.lower()): (p, op)
        for p, item in (doc.get("paths") or {}).items()
        for m, op in (item or {}).items()
        if m.lower() in METODOS
    }


def resolver(doc: dict[str, Any], nodo: Any) -> Any:
    """Resuelve $ref locales (#/...) encadenadas."""
    vistos = set()
    while isinstance(nodo, dict) and "$ref" in nodo:
        ref = nodo["$ref"]
        if ref in vistos or not ref.startswith("#/"):
            break
        vistos.add(ref)
        destino: Any = doc
        for parte in ref[2:].split("/"):
            destino = destino.get(parte.replace("~1", "/").replace("~0", "~"), {})
        nodo = destino
    return nodo


def respuestas(doc: dict[str, Any], op: dict[str, Any]) -> dict[str, dict[str, Any]]:
    salida = {}
    for codigo, resp in (op.get("responses") or {}).items():
        resp = resolver(doc, resp) or {}
        salida[str(codigo).upper()] = {
            mt: (resolver(doc, cont) or {}).get("schema")
            for mt, cont in (resp.get("content") or {}).items()
        }
    return salida


def codigo_documentado(codigo: str, documentados: set[str]) -> bool:
    return codigo in documentados or f"{codigo[0]}XX" in documentados or "DEFAULT" in documentados


def forma(doc: dict[str, Any], esquema: Any, prof: int = 0) -> dict[str, Any]:
    """Forma estructural de un esquema: propiedades (fusionando allOf y uniendo oneOf/anyOf),
    si admite propiedades adicionales y el esquema de items (arrays)."""
    esquema = resolver(doc, esquema)
    f: dict[str, Any] = {"props": {}, "abierto": False, "items": [], "objeto": False}
    if not isinstance(esquema, dict) or prof > 40:
        return f
    for clave in ("allOf", "oneOf", "anyOf"):
        for sub in esquema.get(clave) or []:
            fs = forma(doc, sub, prof + 1)
            for n, s in fs["props"].items():
                f["props"].setdefault(n, []).extend(s)
            f["abierto"] |= fs["abierto"]
            f["items"].extend(fs["items"])
            f["objeto"] |= fs["objeto"]
    for n, s in (esquema.get("properties") or {}).items():
        f["props"].setdefault(n, []).append(s)
    if (
        "properties" in esquema
        or esquema.get("type") == "object"
        or (isinstance(esquema.get("type"), list) and "object" in esquema["type"])
    ):
        f["objeto"] = True
    ap = esquema.get("additionalProperties")
    if ap is True or isinstance(ap, dict):
        f["abierto"] = True
    if "items" in esquema:
        f["items"].append(esquema["items"])
    return f


def comparar(dc, sc, dg, sg, donde: str, prof: int = 0) -> None:
    if prof > 40 or sc is None or sg is None:
        return
    fc, fg = forma(dc, sc), forma(dg, sg)
    if fg["props"] and fc["objeto"] and not fc["abierto"]:
        for nombre in sorted(set(fg["props"]) - set(fc["props"])):
            errores.append(f"propiedad de respuesta NO documentada: {donde}.{nombre}")
    for nombre in sorted(set(fg["props"]) & set(fc["props"])):
        for s_g in fg["props"][nombre]:
            for s_c in fc["props"][nombre]:
                comparar(dc, s_c, dg, s_g, f"{donde}.{nombre}", prof + 1)
    for i_g in fg["items"]:
        for i_c in fc["items"]:
            comparar(dc, i_c, dg, i_g, f"{donde}[]", prof + 1)


def main() -> int:
    ruta_c, ruta_g, ruta_filtrado = sys.argv[1:4]
    contrato, generado = cargar(ruta_c), cargar(ruta_g)
    c, g = operaciones(contrato), operaciones(generado)

    extra = sorted(set(g) - set(c))
    for p, m in extra:
        errores.append(f"operación implementada y NO documentada: {m.upper()} {g[(p, m)][0]}")

    comunes = sorted(set(g) & set(c))
    for clave in comunes:
        _ruta_contrato, op_c = c[clave]
        ruta_gen, op_g = g[clave]
        etiqueta = f"{clave[1].upper()} {ruta_gen}"
        rc, rg = respuestas(contrato, op_c), respuestas(generado, op_g)
        for codigo in sorted(rg):
            if not codigo_documentado(codigo, set(rc)):
                errores.append(f"código de estado NO documentado: {etiqueta} -> {codigo}")
                continue
            rango = f"{codigo[0]}XX"
            ref_c = codigo if codigo in rc else (rango if rango in rc else "DEFAULT")
            for mt, esquema_g in rg[codigo].items():
                if mt not in rc[ref_c]:
                    errores.append(f"media type NO documentado: {etiqueta} -> {codigo} {mt}")
                    continue
                comparar(contrato, rc[ref_c][mt], generado, esquema_g, f"{etiqueta} {codigo} {mt}")

    # Contrato filtrado por OPERACIÓN: solo las operaciones implementadas (con su ruta tal cual
    # está en el contrato, conservando parámetros y claves comunes del path item).
    filtrado = copy.deepcopy(contrato)
    implementadas = {c[k][0]: set() for k in comunes}
    for k in comunes:
        implementadas[c[k][0]].add(k[1])
    nuevas = {}
    for ruta, item in (contrato.get("paths") or {}).items():
        if ruta in implementadas:
            nuevas[ruta] = {
                k: v
                for k, v in item.items()
                if k.lower() not in METODOS or k.lower() in implementadas[ruta]
            }
    filtrado["paths"] = nuevas
    with open(ruta_filtrado, "w", encoding="utf-8") as f:
        yaml.safe_dump(filtrado, f, allow_unicode=True, sort_keys=False)

    for e in errores:
        sys.stdout.write(f"::error::{e}\n")
    sys.stdout.write(
        f"contrato: {len(c)} operaciones; implementadas: {len(g)}; comparadas: {len(comunes)}; "
        f"no documentadas: {len(extra)}; errores: {len(errores)}\n"
    )
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
