"""Política de trivy por LISTA BLANCA (RSK-OPS-001; decisión humana 2026-09-26, TKT-OPS-005,
DEC-AUTO-225). TKT-OPS-006: ciclo 2 (DEC-AUTO-256) y ciclo 3 (DEC-AUTO-915 del Orquestador,
DEC-AUTO-258: de lista negra a lista blanca; QA-OPS006-03, OBS-C2-1).

Uso:  python politica_trivy.py [RAÍZ]   (RAÍZ por defecto: directorio actual; requiere PyYAML)
      Sale 1 si algo incumple la política (anotaciones ::error::).

Análisis (se mantiene del ciclo 2):
  - Los workflows se CARGAN con PyYAML: se analizan los valores RESUELTOS (folded, planos
    multilínea), sin comentarios YAML. Un workflow con YAML no válido es un error.
  - Los valores "run:" (y los *.sh del repositorio) se tratan como shell: una "\\" final solo
    continúa la línea fuera de un comentario; los comentarios de shell se quitan.

LISTA BLANCA. TODA aparición de la palabra "trivy" en posición de comando o de argumento (con
cualquier ruta al binario, p. ej. /usr/local/bin/trivy; también tras "=", comillas o "(") en un
"run:" o en un *.sh es una invocación y debe cumplir TODO lo siguiente, salvo las excepciones
literales de EXCEPCIONES_LINEA:
  1. Subcomando explícito del conjunto SUBCOMANDOS (hoy solo "image"; el CI no usa otros).
  2. Solo flags de FLAGS_BOOL (sin "=valor") y de FLAGS_VALOR (con su valor permitido):
       --severity/-s        exactamente "CRITICAL,HIGH", obligatorio y UNA sola vez
       --scanners           exactamente "vuln" (opcional, una vez)
       --ignorefile         exactamente ".trivyignore" (o la excepción del control negativo)
       --exit-code          exactamente "1"
       --format/-f          "json" o "table"
       --output/-o          ruta; admite expansiones SOLO si todo el valor va entre comillas dobles
       --timeout            \\d+[smh]
       --cache-dir          ruta literal [\\w./-]+
       --quiet/-q, --no-progress, --show-suppressed   (booleanos)
     Cualquier otro flag (--ignore-unfixed, --skip-*, --pkg-types, --db-repository,
     --skip-db-update, --config, --vex…) o un flag conocido con otro valor -> error.
  3. Un único objetivo posicional: literal ([a-z0-9][\\w./:@-]*) o, si lleva expansiones, entre
     comillas dobles y empezando por "brujula/" literal (imágenes construidas por el propio CI).
  4. Argumentos NO literales ($VAR, $(...), `...`, ${{ ... }}) -> error, salvo los dos casos
     de los puntos 2 (--output) y 3 (objetivo).
  5. GATE = invocación con --ignorefile: exige --exit-code 1. En el mismo "run:" no puede haber
     "cd"/"pushd" y el paso/job no puede fijar working-directory (el .trivyignore es el de la
     raíz del repositorio). Debe existir al menos un gate con --ignorefile .trivyignore.
  6. Excepción del CONTROL NEGATIVO (única): --ignorefile /tmp/trivyignore-caducado solo si
     la invocación es la condición de un "if … ; then" cuya rama ejecuta "exit 1" (se exige que
     trivy FALLE) y el mismo "run:" genera ese fichero con el sed literal de GENERADOR_CADUCADO.
Además: prohibidos claves env TRIVY_* de configuración y asignaciones TRIVY_*=,
aquasecurity/trivy-action, aquasecurity/setup-trivy, la imagen aquasec/trivy y los "with:" con
parámetros de trivy; sin trivy.yaml ni .trivyignore.yaml; .trivyignore solo con
"CVE-…|GHSA-… exp:AAAA-MM-DD". En valores YAML que NO son "run:" (name, with, env…) una
"trivy <subcomando>" también es un error.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re
import sys
from typing import Any

import yaml

EXCLUIDOS_SH = {"infra/ci/politica_trivy_controles.sh"}
PODAR = {".git", ".agent", ".claude", "node_modules", ".venv", "__pycache__"}
SUBCOMANDOS = {"image"}
SUBCOMANDOS_TRIVY = {
    "image", "i", "fs", "filesystem", "rootfs", "repo", "repository", "vm", "sbom", "k8s",
    "kubernetes", "config", "conf", "clean", "server", "plugin", "module", "convert", "registry",
    "vex", "version",
}  # fmt: skip
FLAGS_BOOL = {"--quiet", "-q", "--no-progress", "--show-suppressed"}
FLAGS_VALOR = {
    "--severity": "sev", "-s": "sev", "--scanners": "scan", "--ignorefile": "ign",
    "--exit-code": "exit", "--format": "fmt", "-f": "fmt", "--output": "out", "-o": "out",
    "--timeout": "timeout", "--cache-dir": "cache",
}  # fmt: skip
IGNOREFILE_GATE = ".trivyignore"
IGNOREFILE_CONTROL = "/tmp/trivyignore-caducado"  # noqa: S108 (ruta del control negativo del CI)
GENERADOR_CADUCADO = (
    "sed -E 's/exp:[0-9]{4}-[0-9]{2}-[0-9]{2}/exp:2000-01-01/' .trivyignore > " + IGNOREFILE_CONTROL
)
# Líneas lógicas EXACTAS (sin sangría) en las que "trivy" aparece sin ser una invocación.
EXCEPCIONES_LINEA = {
    "tar -xzf /tmp/trivy.tgz -C /usr/local/bin trivy",  # instalación del binario verificado
}
VAR_TRIVY = re.compile(
    r"\bTRIVY_(CONFIG|VEX|SEVERITY|IGNOREFILE|IGNORE_UNFIXED|IGNORE_STATUS|IGNORE_POLICY|"
    r"SKIP_[A-Z_]*|EXIT_CODE|IGNORE[A-Z_]*|SCANNERS|PKG_TYPES|DB_REPOSITORY|CACHE_DIR)\b"
)
ASIGNA_TRIVY = re.compile(VAR_TRIVY.pattern + r"\s*[:=]")
USO_PROHIBIDO = re.compile(r"aquasecurity/(trivy-action|setup-trivy)|aquasec/trivy\b")
# "trivy" como palabra: al inicio o tras espacio, operador, comilla, "=" o "(" (con ruta opcional
# al binario), y seguida de fin, espacio, operador o comilla. /tmp/trivy.tgz, trivy_x o
# aquasecurity/trivy/releases no son apariciones.
APARICION = re.compile(r"(?:^|(?<=[\s;&|(`'\"=]))(?:[\w.~-]*/)*trivy(?=$|[\s;&|)`'\"])")
OBJETIVO_LITERAL = re.compile(r"^[a-z0-9][\w./:@-]*$")
ENTRADA_IGNORE = re.compile(
    r"^(CVE-[0-9]{4}-[0-9]{4,}|GHSA(-[23456789cfghjmpqrvwx]{4}){3}) exp:[0-9]{4}-[0-9]{2}-[0-9]{2}$"
)
CD = re.compile(r"(?:^|[;&|(]|\s)(?:cd|pushd)(?:\s|$)")

errores: list[str] = []
gates = 0
invocaciones = 0


def error(msg: str) -> None:
    errores.append(msg)


# ---------------------------------------------------------------------------------------------
# Shell: comentarios, continuaciones y palabras
# ---------------------------------------------------------------------------------------------
def quitar_comentario(linea: str) -> tuple[str, bool]:
    """(código sin comentario de shell, había comentario). Respeta comillas y escapes."""
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


def lineas_logicas(texto: str) -> list[str]:
    """Líneas lógicas sin comentarios; "\\" final continúa solo fuera de un comentario."""
    logicas: list[str] = []
    actual = ""
    for bruta in texto.replace("\r", "").split("\n"):
        codigo, comentario = quitar_comentario(bruta)
        if not comentario and codigo.endswith("\\") and not codigo.endswith("\\\\"):
            actual += codigo[:-1] + " "
            continue
        logicas.append(actual + codigo)
        actual = ""
    if actual:
        logicas.append(actual)
    return logicas


def _fin_expansion(texto: str, i: int) -> int:
    """Índice tras la expansión que empieza en texto[i] ("$" o "`"); -1 si no cierra."""
    n = len(texto)
    if texto[i] == "`":
        j = texto.find("`", i + 1)
        return -1 if j < 0 else j + 1
    if texto.startswith("$(", i):
        prof, j = 0, i + 1
        while j < n:
            if texto[j] == "(":
                prof += 1
            elif texto[j] == ")":
                prof -= 1
                if prof == 0:
                    return j + 1
            j += 1
        return -1
    if texto.startswith("${", i):
        j = texto.find("}", i)
        return -1 if j < 0 else j + 1
    m = re.match(r"\$[\w@*#?$!-]?\w*", texto[i:])
    return i + (len(m.group()) if m else 1)


def palabras(texto: str) -> tuple[list[dict[str, Any]], bool]:
    """Palabras de shell hasta el primer operador de control sin comillas.
    Cada palabra: valor (sin comillas), literal (sin expansiones), dq (toda entre comillas
    dobles). Devuelve (palabras, ok); ok=False si hay comillas o expansiones sin cerrar."""
    toks: list[dict[str, Any]] = []
    i, n = 0, len(texto)
    while True:
        while i < n and texto[i] in " \t":
            i += 1
        if i >= n or texto[i] in ";&|)\n":
            return toks, True
        valor, literal, partes = "", True, []
        while i < n and texto[i] not in " \t;&|)\n":
            c = texto[i]
            if c == "'":
                j = texto.find("'", i + 1)
                if j < 0:
                    return toks, False
                valor += texto[i + 1 : j]
                partes.append("sq")
                i = j + 1
            elif c == '"':
                j, buf = i + 1, ""
                while j < n and texto[j] != '"':
                    if texto[j] == "\\" and j + 1 < n:
                        buf += texto[j + 1]
                        j += 2
                        continue
                    if texto[j] in "$`":
                        literal = False
                    buf += texto[j]
                    j += 1
                if j >= n:
                    return toks, False
                valor += buf
                partes.append("dq")
                i = j + 1
            elif c == "\\" and i + 1 < n:
                valor += texto[i + 1]
                partes.append("bare")
                i += 2
            elif c in "$`":
                j = _fin_expansion(texto, i)
                if j < 0:
                    return toks, False
                valor += texto[i:j]
                literal = False
                partes.append("exp")
                i = j
            else:
                valor += c
                partes.append("bare")
                i += 1
        toks.append({"valor": valor, "literal": literal, "dq": partes == ["dq"]})


# ---------------------------------------------------------------------------------------------
# Validación de una invocación
# ---------------------------------------------------------------------------------------------
def validar(linea: str, inicio: int, fin: int, texto: str, donde: str, logicas: list[str], k: int):
    """Valida la invocación cuyo "trivy" ocupa linea[inicio:fin]. Devuelve True si es un gate
    con --ignorefile .trivyignore."""
    global invocaciones
    invocaciones += 1
    cita = linea.strip()[:160]
    toks, ok = palabras(linea[fin:])
    if not ok:
        error(f"{donde}: invocación de trivy no analizable (comillas/expansiones): {cita}")
        return False
    fallos: list[str] = []
    vals: dict[str, list[str]] = {}
    posicionales: list[dict[str, Any]] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        v = t["valor"]
        if t["literal"] and v.startswith("-"):
            nombre, sep, igual = v.partition("=")
            if nombre in FLAGS_BOOL and not sep:
                i += 1
                continue
            if nombre in FLAGS_VALOR:
                clave = FLAGS_VALOR[nombre]
                if sep:
                    valor = {"valor": igual, "literal": True, "dq": False}
                elif i + 1 < len(toks):
                    valor = toks[i + 1]
                    i += 1
                else:
                    fallos.append(f"{nombre} sin valor")
                    break
                if not valor["literal"] and not (clave == "out" and valor["dq"]):
                    fallos.append(f"valor NO literal en {nombre}")
                vals.setdefault(clave, []).append(valor["valor"])
                i += 1
                continue
            fallos.append(f"flag fuera de la lista blanca: {v}")
            i += 1
            continue
        if not t["literal"] and not posicionales:
            fallos.append(f"subcomando NO literal: {v}")
        posicionales.append(t)
        i += 1
    sub = posicionales[0]["valor"] if posicionales else ""
    if sub not in SUBCOMANDOS:
        fallos.append(f"subcomando no permitido: {sub or '(ninguno)'}")
    objetivos = posicionales[1:]
    if len(objetivos) != 1:
        fallos.append(f"se espera exactamente 1 objetivo y hay {len(objetivos)}")
    for o in objetivos:
        if o["literal"]:
            if not OBJETIVO_LITERAL.match(o["valor"]):
                fallos.append(f"objetivo no válido: {o['valor']}")
        elif not (o["dq"] and o["valor"].startswith("brujula/")):
            fallos.append(f"objetivo NO literal: {o['valor']}")
    sev = vals.get("sev", [])
    if sev != ["CRITICAL,HIGH"]:
        fallos.append(f"--severity debe aparecer una vez con CRITICAL,HIGH: {sev}")
    for clave, permitido in (("scan", {"vuln"}), ("exit", {"1"}), ("fmt", {"json", "table"})):
        if len(vals.get(clave, [])) > 1 or any(x not in permitido for x in vals.get(clave, [])):
            fallos.append(f"valor no permitido para {clave}: {vals[clave]}")
    for x in vals.get("timeout", []):
        if not re.fullmatch(r"\d+[smh]", x):
            fallos.append(f"--timeout no válido: {x}")
    for x in vals.get("cache", []):
        if not re.fullmatch(r"[\w./-]+", x):
            fallos.append(f"--cache-dir no válido: {x}")
    es_gate = False
    ign = vals.get("ign", [])
    if ign:
        if vals.get("exit") != ["1"]:
            fallos.append("un gate (--ignorefile) exige --exit-code 1")
        if len(ign) > 1:
            fallos.append(f"--ignorefile repetido: {ign}")
        elif ign[0] == IGNOREFILE_GATE:
            es_gate = True
        elif ign[0] == IGNOREFILE_CONTROL:
            prefijo = linea[:inicio].strip()
            rama = " ".join(logicas[k + 1 : k + 4])
            forma_if = prefijo == "if" and re.search(r";\s*then(?:\s|$)", linea[fin:]) is not None
            if not forma_if or GENERADOR_CADUCADO not in texto or "exit 1" not in rama:
                fallos.append(
                    "--ignorefile del control negativo fuera de su forma: if trivy …; then …"
                    " exit 1, con el generador sed en el mismo run"
                )
        else:
            fallos.append(f"--ignorefile no permitido: {ign[0]}")
        if CD.search("\n".join(logicas)):
            fallos.append("cd/pushd en el mismo run que un gate (--ignorefile)")
    if fallos:
        error(f"{donde}: {'; '.join(fallos)}: {cita}")
        return False
    return es_gate


def revisar_shell(texto: str, donde: str) -> int:
    """Revisa un texto de shell; devuelve el número de gates válidos."""
    if ASIGNA_TRIVY.search(texto) or re.search(r"\bexport\s+" + VAR_TRIVY.pattern, texto):
        error(f"{donde}: variable TRIVY_* prohibida por RSK-OPS-001")
    if USO_PROHIBIDO.search(texto):
        error(f"{donde}: uso de trivy-action / setup-trivy / imagen aquasec/trivy prohibido")
    n_gates = 0
    logicas = lineas_logicas(texto)
    for k, linea in enumerate(logicas):
        if linea.strip() in EXCEPCIONES_LINEA:
            continue
        for m in APARICION.finditer(linea):
            if validar(linea, m.start(), m.end(), texto, donde, logicas, k):
                n_gates += 1
    return n_gates


def tiene_trivy(texto: str) -> bool:
    return any(
        APARICION.search(linea) and linea.strip() not in EXCEPCIONES_LINEA
        for linea in lineas_logicas(texto)
    )


# ---------------------------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------------------------
def recorrer(nodo: Any, ruta: str, fichero: str) -> None:
    global gates
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            if isinstance(k, str) and VAR_TRIVY.fullmatch(k.strip()):
                error(f"{fichero}:{ruta}.{k}: variable TRIVY_* prohibida por RSK-OPS-001")
            if k == "uses" and isinstance(v, str) and USO_PROHIBIDO.search(v):
                error(f"{fichero}:{ruta}: uses: {v} prohibido (solo el binario verificado)")
            if k == "with" and isinstance(v, dict):
                claves = {str(x).lower() for x in v}
                if claves & {"ignore-unfixed", "trivyignores", "trivy-config", "skip-files"}:
                    error(f"{fichero}:{ruta}.with: parámetros de trivy {sorted(claves)}")
            if k == "run" and isinstance(v, str):
                gates += revisar_shell(v, f"{fichero}:{ruta}.run")
            else:
                recorrer(v, f"{ruta}.{k}", fichero)
    elif isinstance(nodo, list):
        for i, v in enumerate(nodo):
            recorrer(v, f"{ruta}[{i}]", fichero)
    elif isinstance(nodo, str):
        # Fuera de "run:": no se ejecuta como shell, pero "trivy <subcomando>" es sospechoso.
        for m in APARICION.finditer(nodo):
            siguiente = nodo[m.end() :].split()
            if siguiente and siguiente[0] in SUBCOMANDOS_TRIVY:
                error(f"{fichero}:{ruta}: invocación de trivy fuera de un run: {nodo[:120]}")
        if ASIGNA_TRIVY.search(nodo) or USO_PROHIBIDO.search(nodo):
            error(f"{fichero}:{ruta}: configuración de trivy prohibida en un valor YAML")


def revisar_directorios(doc: Any, fichero: str) -> None:
    """Un paso que ejecuta trivy no puede cambiar de directorio con working-directory."""
    if not isinstance(doc, dict):
        return
    wd_flujo = ((doc.get("defaults") or {}).get("run") or {}).get("working-directory")
    for nombre, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        wd_job = ((job.get("defaults") or {}).get("run") or {}).get("working-directory")
        for i, paso in enumerate(job.get("steps") or []):
            if not isinstance(paso, dict) or not isinstance(paso.get("run"), str):
                continue
            wd = paso.get("working-directory") or wd_job or wd_flujo
            if wd and wd not in {".", "./"} and tiene_trivy(paso["run"]):
                error(
                    f"{fichero}:.jobs.{nombre}.steps[{i}]: trivy con working-directory {wd} "
                    "(el .trivyignore es el de la raíz)"
                )


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
            revisar_directorios(doc, rel)
    for f in ficheros(raiz, ("*.sh",)):
        rel = f.relative_to(raiz).as_posix()
        if rel not in EXCLUIDOS_SH:
            revisar_shell(f.read_text(encoding="utf-8", errors="replace"), rel)
    if invocaciones == 0:
        error("no se encontró ninguna invocación de trivy en los workflows")
    if gates == 0:
        error(
            "ningún workflow ejecuta el gate: trivy image … --ignorefile .trivyignore --exit-code 1"
        )
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
    sys.stdout.write(f"política de trivy OK (lista blanca); {resumen}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
