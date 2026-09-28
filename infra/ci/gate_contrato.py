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
     Además (TKT-OPS-006, OBS-QA-OPS004-02, DEC-AUTO-251):
       - un objeto ABIERTO en lo generado (additionalProperties true o esquema, p. ej. {})
         donde el contrato lo tiene cerrado es un error                           (N13)
       - un esquema SIN TIPO en lo generado ({} o solo claves descriptivas) donde el
         contrato declara un tipo o una estructura es un error (propiedades, items y
         valores de additionalProperties)                                         (N14)
     Recorrido memoizado por par (esquema del contrato, esquema generado): los esquemas
     autorreferenciados o con referencias compartidas se comparan una sola vez y el coste
     es lineal en el número de pares distintos, no exponencial (OBS-QA-OPS004-01, DEC-AUTO-250).
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


# Claves que no restringen el valor: un esquema que solo tiene estas (o {}) acepta cualquier cosa.
DESCRIPTIVAS = {
    "description",
    "title",
    "example",
    "examples",
    "default",
    "readOnly",
    "writeOnly",
    "deprecated",
    "nullable",
    "externalDocs",
    "xml",
    "$comment",
}


def sin_tipo(doc: dict[str, Any], esquema: Any) -> bool:
    """True si el esquema acepta cualquier valor: {} , true o solo claves descriptivas / x-*."""
    esquema = resolver(doc, esquema)
    if esquema is True:
        return True
    if not isinstance(esquema, dict) or "$ref" in esquema:
        return False
    return all(k in DESCRIPTIVAS or str(k).startswith("x-") for k in esquema)


def forma(
    doc: dict[str, Any], esquema: Any, en_curso: frozenset[int] = frozenset()
) -> dict[str, Any]:
    """Forma estructural de un esquema: propiedades (fusionando allOf y uniendo oneOf/anyOf),
    si admite propiedades adicionales, sus esquemas (mapas) y el esquema de items (arrays).
    "en_curso" corta los ciclos de allOf/oneOf/anyOf autorreferenciados (DEC-AUTO-250)."""
    esquema = resolver(doc, esquema)
    f: dict[str, Any] = {"props": {}, "abierto": False, "ap": [], "items": [], "objeto": False}
    if not isinstance(esquema, dict) or id(esquema) in en_curso:
        return f
    en_curso = en_curso | {id(esquema)}
    for clave in ("allOf", "oneOf", "anyOf"):
        for sub in esquema.get(clave) or []:
            fs = forma(doc, sub, en_curso)
            for n, s in fs["props"].items():
                f["props"].setdefault(n, []).extend(s)
            f["abierto"] |= fs["abierto"]
            f["ap"].extend(fs["ap"])
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
        f["ap"].append(ap)
    if "items" in esquema:
        f["items"].append(esquema["items"])
    return f


def comparar(dc, sc, dg, sg, donde: str, visitados: set[tuple[int, int]] | None = None) -> None:
    """Compara el esquema generado (sg) con el del contrato (sc), recursivo y memoizado por par de
    esquemas RESUELTOS (id): cada par se visita una vez, también en ciclos (DEC-AUTO-250)."""
    if visitados is None:
        visitados = set()
    if sc is None or sg is None:
        return
    rc, rg = resolver(dc, sc), resolver(dg, sg)
    par = (id(rc), id(rg))
    if par in visitados:
        return
    visitados.add(par)
    # N14: lo generado no restringe nada donde el contrato fija tipo o estructura.
    if sin_tipo(dg, rg) and not sin_tipo(dc, rc):
        errores.append(f"esquema SIN TIPO en la implementación donde el contrato lo tipa: {donde}")
        return
    fc, fg = forma(dc, rc), forma(dg, rg)
    cerrado_c = fc["objeto"] and not fc["abierto"]
    if fg["props"] and cerrado_c:
        for nombre in sorted(set(fg["props"]) - set(fc["props"])):
            errores.append(f"propiedad de respuesta NO documentada: {donde}.{nombre}")
    # N13: objeto abierto en la implementación donde el contrato lo cierra.
    if fg["abierto"] and cerrado_c:
        errores.append(
            "objeto ABIERTO (additionalProperties) en la implementación y CERRADO en el "
            f"contrato: {donde}"
        )
    for nombre in sorted(set(fg["props"]) & set(fc["props"])):
        for s_g in fg["props"][nombre]:
            for s_c in fc["props"][nombre]:
                comparar(dc, s_c, dg, s_g, f"{donde}.{nombre}", visitados)
    for i_g in fg["items"]:
        for i_c in fc["items"]:
            comparar(dc, i_c, dg, i_g, f"{donde}[]", visitados)
    # Valores de mapas (additionalProperties con esquema) en ambos lados.
    for a_g in fg["ap"]:
        for a_c in fc["ap"]:
            if a_c is True:
                continue  # el contrato admite cualquier valor
            comparar(dc, a_c, dg, a_g, f"{donde}{{*}}", visitados)


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
