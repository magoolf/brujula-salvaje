"""Política de excepciones de trivy (RSK-OPS-001; decisión humana 2026-09-26, TKT-OPS-005,
DEC-AUTO-225). TKT-OPS-006, ciclo 2 (QA-OPS006-01/02, OBS-3; DEC-AUTO-256).

Uso:  python politica_trivy.py [RAÍZ]   (RAÍZ por defecto: directorio actual; requiere PyYAML)
      Examina RAÍZ/.trivyignore, RAÍZ/.github/workflows/*.y*ml y los *.sh del repositorio.
      Sale 1 si algo incumple la política (anotaciones ::error::).

Por qué con un parser YAML y no con grep sobre el texto:
  - Los workflows se CARGAN con PyYAML y se analizan los valores RESUELTOS: un escalar "folded"
    (run: >) o plano multilínea que YAML junta en un solo comando se ve junto (QA-OPS006-02), y
    los comentarios YAML desaparecen.
  - Cada cadena se trata como shell: una "\\" final SOLO continúa la línea si no está dentro de un
    comentario de shell (en bash, "# nota \\" no continúa; QA-OPS006-01). Los comentarios se quitan.
  - Las opciones PROHIBIDAS se buscan en las líneas lógicas (unidas) Y en las físicas: unir nunca
    puede ocultar nada. Las opciones OBLIGATORIAS se exigen sobre la línea lógica completa.

Reglas (toda invocación de trivy con subcomando de escaneo: image, fs, rootfs, repo, vm, sbom...):
  - al menos un --severity/-s y TODOS exactamente CRITICAL,HIGH (una 2.ª --severity o -s la anula);
  - prohibidos --config/-c, --vex, --ignore-status, --ignore-unfixed, --ignore-policy,
    --skip-files/--skip-dirs/--skip-pkgs y --exit-code 0;
  - --ignorefile solo con el valor exacto ".trivyignore", y quien lo use debe llevar --exit-code
    distinto de 0 (es el gate); debe existir al menos una invocación así en los workflows;
  - prohibidas las variables TRIVY_* de configuración (claves env: o asignaciones en shell),
    aquasecurity/trivy-action, aquasecurity/setup-trivy y la imagen aquasec/trivy;
  - .trivyignore: solo "CVE-…|GHSA-… exp:AAAA-MM-DD" (sin comodines); sin trivy.yaml ni
    .trivyignore.yaml en el repositorio.
Los *.sh del repositorio se analizan con las mismas reglas de opciones prohibidas (salvo el de
controles, que contiene los casos de prueba y no se ejecuta en ningún workflow ni imagen).
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re
import shlex
import sys
from typing import Any

import yaml

EXCLUIDOS_SH = {"infra/ci/politica_trivy_controles.sh"}
PODAR = {".git", ".agent", ".claude", "node_modules", ".venv", "__pycache__"}
SUBCOMANDOS_ESCANEO = {
    "image", "i", "fs", "filesystem", "rootfs", "repo", "repository", "vm", "sbom",
    "k8s", "kubernetes",
}  # fmt: skip
SUBCOMANDOS = SUBCOMANDOS_ESCANEO | {
    "config",
    "conf",
    "clean",
    "server",
    "plugin",
    "module",
}
PROHIBIDAS = re.compile(
    r"^(--config|-c|--vex|--ignore-status|--ignore-unfixed|--ignore-policy|"
    r"--skip-files|--skip-dirs|--skip-pkgs|--skip-java-db-update)(=.*)?$"
)
VAR_TRIVY = re.compile(
    r"\bTRIVY_(CONFIG|VEX|SEVERITY|IGNOREFILE|IGNORE_UNFIXED|IGNORE_STATUS|IGNORE_POLICY|"
    r"SKIP_[A-Z_]*|EXIT_CODE|IGNORE[A-Z_]*)\b"
)
ASIGNA_TRIVY = re.compile(VAR_TRIVY.pattern + r"\s*[:=]")
USO_PROHIBIDO = re.compile(r"aquasecurity/(trivy-action|setup-trivy)|aquasec/trivy\b")
TRIVY = re.compile(r"(?<![\w./-])(?:[\w./-]*/)?trivy(?![\w.-])")
ENTRADA_IGNORE = re.compile(
    r"^(CVE-[0-9]{4}-[0-9]{4,}|GHSA(-[23456789cfghjmpqrvwx]{4}){3}) exp:[0-9]{4}-[0-9]{2}-[0-9]{2}$"
)
CONTROL = re.compile(r"(\|\||&&|[;|&()`]|\$\()")

errores: list[str] = []
gates = 0
invocaciones = 0


def error(msg: str) -> None:
    errores.append(msg)


def quitar_comentario(linea: str) -> tuple[str, bool]:
    """Devuelve (código sin comentario de shell, había comentario). Respeta comillas y escapes."""
    comilla = ""
    i = 0
    while i < len(linea):
        ch = linea[i]
        if comilla == "'":
            if ch == "'":
                comilla = ""
        elif ch == "\\":
            i += 2
            continue
        elif comilla == '"':
            if ch == '"':
                comilla = ""
        elif ch in "'\"":
            comilla = ch
        elif ch == "#" and (i == 0 or linea[i - 1] in " \t;&|()"):
            return linea[:i], True
        i += 1
    return linea, False


def lineas(texto: str) -> tuple[list[str], list[str]]:
    """(líneas lógicas con continuaciones unidas, líneas físicas), ambas sin comentarios."""
    logicas: list[str] = []
    fisicas: list[str] = []
    actual = ""
    for bruta in texto.replace("\r", "").split("\n"):
        codigo, comentario = quitar_comentario(bruta)
        fisicas.append(codigo)
        if not comentario and codigo.endswith("\\") and not codigo.endswith("\\\\"):
            actual += codigo[:-1] + " "
            continue
        logicas.append(actual + codigo)
        actual = ""
    if actual:
        logicas.append(actual)
    return logicas, fisicas


def tokens(segmento: str) -> list[str]:
    try:
        return shlex.split(segmento, posix=True)
    except ValueError:
        return segmento.split()


def invocaciones_en(linea: str) -> list[tuple[str, list[str]]]:
    """[(subcomando, argumentos)] de cada "trivy …" de la línea, cortando en operadores de shell."""
    salida = []
    for m in TRIVY.finditer(linea):
        resto = CONTROL.split(linea[m.end() :], maxsplit=1)[0]
        args = tokens(resto)
        sub = next((a for a in args if not a.startswith("-")), "")
        # Flags globales antes del subcomando (p. ej. "trivy -q image"): se conservan todas.
        if sub in SUBCOMANDOS:
            salida.append((sub, args))
    return salida


def valores(args: list[str], *nombres: str) -> list[str]:
    out = []
    for i, a in enumerate(args):
        for n in nombres:
            if a == n:
                out.append(args[i + 1] if i + 1 < len(args) else "")
            elif a.startswith(n + "=") and n.startswith("--"):
                out.append(a.split("=", 1)[1])
            elif n == "-s" and a.startswith("-s") and len(a) > 2 and not a.startswith("--"):
                out.append(a[2:])
    return out


def prohibidas(args: list[str]) -> list[str]:
    malas = [a for a in args if PROHIBIDAS.match(a)]
    malas += [f"--exit-code {v}" for v in valores(args, "--exit-code") if v.strip() in {"0", ""}]
    return malas


def revisar_texto(texto: str, donde: str, estricto: bool) -> None:
    """estricto=True (workflows): además de lo prohibido exige severidad y cuenta los gates."""
    global gates, invocaciones
    if ASIGNA_TRIVY.search(texto) or re.search(r"\bexport\s+" + VAR_TRIVY.pattern, texto):
        error(f"{donde}: variable TRIVY_* prohibida por RSK-OPS-001")
    if USO_PROHIBIDO.search(texto):
        error(f"{donde}: uso de trivy-action / setup-trivy / imagen aquasec/trivy prohibido")
    logicas, fisicas = lineas(texto)
    # Prohibido: en físicas Y lógicas (unir nunca oculta nada).
    for linea in fisicas + logicas:
        for _sub, args in invocaciones_en(linea):
            malas = prohibidas(args)
            if malas:
                error(f"{donde}: opción de trivy prohibida {malas}: {linea.strip()[:160]}")
    for linea in logicas:
        for sub, args in invocaciones_en(linea):
            if sub not in SUBCOMANDOS_ESCANEO:
                continue
            invocaciones += 1
            txt = linea.strip()[:160]
            sev = valores(args, "--severity", "-s")
            if not sev or any(v != "CRITICAL,HIGH" for v in sev):
                error(f"{donde}: severidad fuera de política {sev or '(ausente)'}: {txt}")
            ign = valores(args, "--ignorefile")
            if ign:
                if any(v != ".trivyignore" for v in ign):
                    error(f"{donde}: --ignorefile distinto de .trivyignore {ign}: {txt}")
                codigos = valores(args, "--exit-code")
                if not codigos or any(c in {"0", ""} for c in codigos):
                    error(f"{donde}: el gate (--ignorefile) necesita --exit-code != 0: {txt}")
                elif estricto:
                    gates += 1


def recorrer(nodo: Any, ruta: str, fichero: str) -> None:
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            if isinstance(k, str) and VAR_TRIVY.fullmatch(k.strip()):
                error(f"{fichero}:{ruta}.{k}: variable TRIVY_* prohibida por RSK-OPS-001")
            if k == "uses" and isinstance(v, str) and USO_PROHIBIDO.search(v):
                error(
                    f"{fichero}:{ruta}: uses: {v} prohibido (solo el binario verificado por sha256)"
                )
            if k == "with" and isinstance(v, dict):
                claves = {str(x).lower() for x in v}
                if claves & {
                    "ignore-unfixed",
                    "trivyignores",
                    "severity",
                    "trivy-config",
                    "skip-files",
                    "skip-dirs",
                }:
                    error(f"{fichero}:{ruta}.with: parámetros de trivy-action {sorted(claves)}")
            recorrer(v, f"{ruta}.{k}", fichero)
    elif isinstance(nodo, list):
        for i, v in enumerate(nodo):
            recorrer(v, f"{ruta}[{i}]", fichero)
    elif isinstance(nodo, str):
        revisar_texto(nodo, f"{fichero}:{ruta}", estricto=True)


def ficheros(raiz: pathlib.Path, patrones: tuple[str, ...]) -> list[pathlib.Path]:
    out = []
    for p in sorted(raiz.rglob("*")):
        rel = p.relative_to(raiz)
        if any(parte in PODAR for parte in rel.parts) or not p.is_file():
            continue
        if any(p.match(pat) for pat in patrones):
            out.append(p)
    return out


def main() -> int:
    raiz = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    ign = raiz / ".trivyignore"
    wf = raiz / ".github" / "workflows"
    if not ign.is_file():
        error("falta .trivyignore")
    if not wf.is_dir():
        error(f"falta {wf}")
    for p in ficheros(raiz, ("trivy.yaml", "trivy.yml", ".trivyignore.yaml", ".trivyignore.yml")):
        error(f"configuración de trivy no permitida: {p.relative_to(raiz)}")
    if wf.is_dir():
        for f in sorted(list(wf.glob("*.yaml")) + list(wf.glob("*.yml"))):
            rel = f.relative_to(raiz).as_posix()
            try:
                doc = yaml.safe_load(f.read_text(encoding="utf-8"))
            except yaml.YAMLError as e:
                error(f"{rel}: YAML no válido ({str(e).splitlines()[0]})")
                continue
            recorrer(doc, "", rel)
    for f in ficheros(raiz, ("*.sh",)):
        rel = f.relative_to(raiz).as_posix()
        if rel not in EXCLUIDOS_SH:
            revisar_texto(f.read_text(encoding="utf-8", errors="replace"), rel, estricto=False)
    if invocaciones == 0:
        error("no se encontró ninguna invocación de trivy en los workflows")
    if gates == 0:
        error("ningún workflow ejecuta el gate: trivy … --ignorefile .trivyignore --exit-code 1")
    vigentes = 0
    if ign.is_file():
        hoy = dt.datetime.now(dt.UTC).date().isoformat()
        for n, linea in enumerate(ign.read_text(encoding="utf-8").replace("\r", "").split("\n"), 1):
            if not linea.strip() or linea.lstrip().startswith("#"):
                continue
            if not ENTRADA_IGNORE.match(linea):
                error(f".trivyignore:{n}: entrada fuera de política: {linea}")
                continue
            vigentes += 1
            fecha = linea.rsplit("exp:", 1)[1]
            if fecha < hoy:
                aviso = f".trivyignore:{n} CADUCADA ({fecha}): trivy la tratará como hallazgo"
                sys.stdout.write(f"::warning::{aviso}\n")
    for e in errores:
        sys.stdout.write(f"::error::{e}\n")
    if errores:
        return 1
    resumen = f"invocaciones: {invocaciones}; gates: {gates}; excepciones: {vigentes}"
    sys.stdout.write(f"política de trivy OK; {resumen}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
