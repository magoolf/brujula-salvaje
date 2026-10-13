"""Política de trivy por LISTA BLANCA (RSK-OPS-001; decisión humana 2026-09-26, TKT-OPS-005,
DEC-AUTO-225). TKT-OPS-006: ciclo 2 (DEC-AUTO-256) y ciclo 3 (DEC-AUTO-915 del Orquestador,
DEC-AUTO-258: de lista negra a lista blanca; QA-OPS006-03, OBS-C2-1). TKT-OPS-009 (DEC-AUTO-1260..
1265): canales implícitos (QA-OPS006-04/05, OBS-C3-1..3), ver "CANALES IMPLÍCITOS" más abajo.

Uso:  python politica_trivy.py [RAÍZ]   (RAÍZ por defecto: directorio actual; requiere PyYAML)
      Sale 1 si algo incumple la política (anotaciones ::error::).

Análisis (se mantiene del ciclo 2):
  - Los workflows se CARGAN con PyYAML: se analizan los valores RESUELTOS (folded, planos
    multilínea), sin comentarios YAML. Un workflow con YAML no válido es un error.
  - Los valores "run:" (y los *.sh del repositorio) se tratan como shell: una "\\" final solo
    continúa la línea fuera de un comentario; los comentarios de shell se quitan.

LISTA BLANCA. TODA aparición de la palabra "trivy" en posición de comando o de argumento (con
cualquier ruta al binario, p. ej. /usr/local/bin/trivy; también tras "=", comillas o "(") en un
"run:" o en un *.sh es una invocación y debe cumplir TODO lo siguiente, salvo la instalación
verificada (INSTALACION, ver OBS-C3-3):
  1. Subcomando explícito del conjunto SUBCOMANDOS (hoy solo "image"; el CI no usa otros).
  2. Solo flags de FLAGS_BOOL (sin "=valor") y de FLAGS_VALOR (con su valor permitido):
       --severity/-s        exactamente "CRITICAL,HIGH", obligatorio y UNA sola vez
       --scanners           exactamente "vuln" (opcional, una vez)
       --ignorefile         exactamente ".trivyignore" (o la excepción del control negativo)
       --exit-code          exactamente "1"
       --format/-f          "json" o "table"
       --output/-o          reports/… o /tmp/… terminado en .json/.txt (SALIDA); admite
                            expansiones SOLO si todo el valor va entre comillas dobles
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
  6. Excepción del CONTROL NEGATIVO (única): --ignorefile /tmp/trivyignore-caducado (ver 7).
  7. (TKT-OPS-009) Ninguna invocación lleva nada antes ni después en su línea lógica (ni "&",
     "&&", "|", "; true", "|| true", redirecciones), salvo: el gate puede terminar en
     "|| rc=1" y el control negativo es exactamente "if trivy …; then".
     Un "run:"/*.sh con un gate o con el control negativo es un ESQUELETO cerrado: cada línea
     lógica debe ser una de LINEAS_ESQUELETO, FOR, ECHO, la guardia, una invocación o (solo con
     control) el generador y la comprobación GREP_CONTROL. Sin "set +e", "trap", "exit 0", "if"
     ni funciones: el gate no puede quedar sin efecto (OBS-C3-2). Con "|| rc=1": "rc=0" una vez
     antes del primer gate y "exit $rc" como ÚLTIMA línea. El control negativo: generador antes
     del "if trivy …; then", la línea siguiente termina en "exit 1" y la siguiente es "fi"
     (QA-OPS006-05: analizado como shell, líneas lógicas exactas, no subcadenas).
     La GUARDIA (/usr/bin/python3 infra/ci/trivy_guardia.py) debe ejecutarse antes de la primera
     invocación del run. El paso y su job no pueden tener continue-on-error (salvo false), el
     paso no puede tener "if:" y el shell (paso, job o workflow) solo puede ser "bash".

CANALES IMPLÍCITOS (TKT-OPS-009):
  - QA-OPS006-04: trivy lee CUALQUIER variable TRIVY_* (no solo una lista) y ./trivy.yaml.
    Se prohíbe el prefijo TRIVY_ en todo el código de los workflows (claves, valores, run:,
    también vía $GITHUB_ENV) y de los *.sh, y la mención de trivy.yaml/.yml o
    .trivyignore.yaml/.yml en run:/*.sh y en valores de with:/env:. Las versiones del binario
    se llaman TRIVYCLI_VERSION/TRIVYCLI_SHA256 (solo en el env de nivel de workflow, literales).
    En ejecución, la guardia comprueba el entorno real (defensa en profundidad).
  - OBS-C3-1: ninguna línea de run:/*.sh menciona .trivyignore salvo el gate y el generador del
    control negativo (que solo lo LEE); tampoco valores de with:/env:. La guardia verifica en
    ejecución que .trivyignore no difiere del commit.
  - QA-OPS006-05: "trivyignore-caducado" solo aparece en el generador, en GREP_CONTROL y en la
    invocación del control, dentro del mismo run.
  - OBS-C3-3: la línea que extrae el binario es válida solo si las dos líneas lógicas previas
    son exactamente la descarga y "sha256sum -c" (INSTALACION); /tmp/trivy.tgz no aparece en
    ninguna otra línea.
Además: aquasecurity/trivy-action, aquasecurity/setup-trivy, la imagen aquasec/trivy y el
instalador contrib/install.sh prohibidos; "with:" con parámetros de trivy prohibido; sin
trivy.yaml ni .trivyignore.yaml en el repositorio; .trivyignore solo con
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
NOMBRE_CONTROL = "trivyignore-caducado"
GENERADOR_CADUCADO = (
    "sed -E 's/exp:[0-9]{4}-[0-9]{2}-[0-9]{2}/exp:2000-01-01/' .trivyignore > " + IGNOREFILE_CONTROL
)
GREP_CONTROL = (
    "if ! grep -qE '^(CVE|GHSA)-' " + IGNOREFILE_CONTROL + '; then echo "sin excepciones: control'
    ' no aplicable"; exit 0; fi'
)
GUARDIA = "/usr/bin/python3 infra/ci/trivy_guardia.py"
# OBS-C3-3: instalación del binario verificado; las tres líneas lógicas, seguidas y exactas.
TGZ = "/tmp/trivy.tgz"  # noqa: S108
INSTALACION = (
    'curl -fsSLo /tmp/trivy.tgz "https://github.com/aquasecurity/trivy/releases/download/'
    'v${TRIVYCLI_VERSION}/trivy_${TRIVYCLI_VERSION}_Linux-64bit.tar.gz"',
    'echo "${TRIVYCLI_SHA256}  /tmp/trivy.tgz" | sha256sum -c -',
    "tar -xzf /tmp/trivy.tgz -C /usr/local/bin trivy",
)
VERSION_BIN = {"TRIVYCLI_VERSION": r"\d+\.\d+\.\d+", "TRIVYCLI_SHA256": r"[0-9a-f]{64}"}
# Esqueleto de un run con gate/control (OBS-C3-2, QA-OPS006-05).
LINEAS_ESQUELETO = {GUARDIA, "mkdir -p reports", "rc=0", "done", "fi", "exit $rc", 'exit "$rc"'}
FOR = re.compile(r"^for s in [a-z][a-z ]*; do$")
_TEXTO_ECHO = r'echo "(?:[^"`$\\]|\$\{s\})*"'
ECHO = re.compile("^" + _TEXTO_ECHO + "$")
ECHO_EXIT1 = re.compile("^(?:" + _TEXTO_ECHO + "; )?exit 1$")
SALIDA = re.compile(r"^(?:reports|/tmp)/(?:[\w.-]|\$\{s\}|\$\{APP_VERSION\})+\.(?:json|txt)$")
# QA-OPS006-04: trivy lee TODA variable TRIVY_* (viper, prefijo TRIVY). Prefijo como palabra:
# TRIVYCLI_VERSION o BIN_TRIVY_X no lo son.
VAR_TRIVY = re.compile(r"(?<![A-Za-z0-9_])TRIVY_")
ASIGNA_TRIVYCLI = re.compile(r"(?<![A-Za-z0-9_])TRIVYCLI_\w*\s*[:=]|GITHUB_(ENV|PATH)\b.*TRIVYCLI")
CONFIG_TRIVY = re.compile(r"trivy(?:ignore)?\.ya?ml(?![\w-])", re.IGNORECASE)
MENCION_IGNORE = re.compile(r"\.trivyignore(?![\w-])")
USO_PROHIBIDO = re.compile(
    r"aquasecurity/(trivy-action|setup-trivy)|aquasec/trivy\b|"
    r"aquasecurity/trivy/[\w./-]*install\.sh|get\.trivy\.dev"
)
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
# texto de cada run/sh revisado -> tipos de invocación ("gate", "control", "otro")
TIPOS_RUN: dict[str, set[str]] = {}
RUNS_INSTALACION: set[str] = set()


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


def palabras(texto: str) -> tuple[list[dict[str, Any]], bool, int]:
    """Palabras de shell hasta el primer operador de control sin comillas.
    Cada palabra: valor (sin comillas), literal (sin expansiones), dq (toda entre comillas
    dobles). Devuelve (palabras, ok, índice de parada); ok=False si hay comillas o expansiones
    sin cerrar."""
    toks: list[dict[str, Any]] = []
    i, n = 0, len(texto)
    while True:
        while i < n and texto[i] in " \t":
            i += 1
        if i >= n or texto[i] in ";&|)\n":
            return toks, True, i
        valor, literal, partes = "", True, []
        while i < n and texto[i] not in " \t;&|)\n":
            c = texto[i]
            if c == "'":
                j = texto.find("'", i + 1)
                if j < 0:
                    return toks, False, i
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
                    return toks, False, i
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
                    return toks, False, i
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
def validar(linea: str, fin: int, donde: str, logicas: list[str]) -> tuple[str, str] | None:
    """Valida la invocación cuyo "trivy" termina en linea[fin]. Devuelve (tipo, resto de la
    línea tras la invocación) con tipo "gate" (--ignorefile .trivyignore), "control"
    (--ignorefile del control negativo) u "otro"; None si incumple la lista blanca."""
    global invocaciones
    invocaciones += 1
    cita = linea.strip()[:160]
    toks, ok, parada = palabras(linea[fin:])
    if not ok:
        error(f"{donde}: invocación de trivy no analizable (comillas/expansiones): {cita}")
        return None
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
    salidas = vals.get("out", [])
    if len(salidas) > 1 or any(not SALIDA.match(x) or ".." in x for x in salidas):
        fallos.append(f"--output fuera de reports/ o /tmp/ (*.json|*.txt): {salidas}")
    tipo = "otro"
    ign = vals.get("ign", [])
    if ign:
        if vals.get("exit") != ["1"]:
            fallos.append("un gate (--ignorefile) exige --exit-code 1")
        if len(ign) > 1:
            fallos.append(f"--ignorefile repetido: {ign}")
        elif ign[0] == IGNOREFILE_GATE:
            tipo = "gate"
        elif ign[0] == IGNOREFILE_CONTROL:
            tipo = "control"
        else:
            fallos.append(f"--ignorefile no permitido: {ign[0]}")
        if CD.search("\n".join(logicas)):
            fallos.append("cd/pushd en el mismo run que un gate (--ignorefile)")
    if fallos:
        error(f"{donde}: {'; '.join(fallos)}: {cita}")
        return None
    return tipo, linea[fin + parada :]


def revisar_esqueleto(
    logicas: list[str], invs: dict[int, list[tuple[str, str, str]]], donde: str
) -> None:
    """OBS-C3-2 / QA-OPS006-05: un run con gate o control negativo es un esqueleto cerrado."""
    lineas = [(k, linea.strip()) for k, linea in enumerate(logicas) if linea.strip()]
    pos = {k: p for p, (k, _) in enumerate(lineas)}
    primera = min(invs)
    tipos = {t for lst in invs.values() for t, _, _ in lst}
    hay_control = "control" in tipos
    k_guardia = [k for k, s in lineas if s == GUARDIA]
    if not k_guardia or k_guardia[0] > primera:
        error(f"{donde}: falta la guardia '{GUARDIA}' antes de la primera invocación de trivy")
    k_gates = sorted(k for k, lst in invs.items() if any(t == "gate" for t, _, _ in lst))
    usa_rc = False
    permitidas: set[int] = set()
    for k, s in lineas:
        if k in invs:
            lst = invs[k]
            if len(lst) != 1:
                error(f"{donde}: más de una invocación de trivy en una línea: {s[:120]}")
                continue
            tipo, prefijo, resto = lst[0]
            resto = resto.strip()
            if tipo == "gate":
                if prefijo or resto not in ("", "|| rc=1"):
                    error(
                        f"{donde}: el gate no admite nada antes ni después salvo '|| rc=1' "
                        f"(sin '|| true', '&', '&&', '|', '; …'): {s[:160]}"
                    )
                usa_rc |= resto == "|| rc=1"
            elif tipo == "control":
                p = pos[k]
                rama = lineas[p + 1][1] if p + 1 < len(lineas) else ""
                cierre = lineas[p + 2][1] if p + 2 < len(lineas) else ""
                if (
                    prefijo != "if"
                    or not re.fullmatch(r";\s*then", resto)
                    or not ECHO_EXIT1.match(rama)
                    or cierre != "fi"
                ):
                    error(
                        f"{donde}: control negativo fuera de su forma: 'if trivy …; then', "
                        f"línea siguiente terminada en 'exit 1' y después 'fi': {s[:120]}"
                    )
                else:
                    permitidas.add(lineas[p + 1][0])
            elif prefijo or resto:
                error(f"{donde}: invocación de trivy con algo antes o después: {s[:160]}")
            continue
        if k in permitidas or s in LINEAS_ESQUELETO or FOR.match(s) or ECHO.match(s):
            continue
        if hay_control and s in (GENERADOR_CADUCADO, GREP_CONTROL):
            continue
        error(f"{donde}: línea no permitida en un run con gate/control de trivy: {s[:160]}")
    textos = [s for _, s in lineas]
    if textos.count("rc=0") > 1:
        error(f"{donde}: 'rc=0' repetido en el run del gate")
    for k, s in lineas:
        if s in ("exit $rc", 'exit "$rc"') and k != lineas[-1][0]:
            error(f"{donde}: 'exit $rc' solo puede ser la última línea del run del gate")
    if usa_rc:
        k_rc = [k for k, s in lineas if s == "rc=0"]
        if not k_rc or k_rc[0] > k_gates[0]:
            error(f"{donde}: '|| rc=1' exige 'rc=0' antes del primer gate")
        if lineas[-1][1] not in ("exit $rc", 'exit "$rc"'):
            error(f"{donde}: '|| rc=1' exige 'exit $rc' como última línea del run")
    if hay_control:
        k_gen = [k for k, s in lineas if s == GENERADOR_CADUCADO]
        k_ctl = [k for k, lst in invs.items() if any(t == "control" for t, _, _ in lst)]
        if len(k_gen) != 1 or k_gen[0] > min(k_ctl):
            error(f"{donde}: el control negativo exige el generador sed una vez y antes del 'if'")


def revisar_shell(texto: str, donde: str) -> int:
    """Revisa un texto de shell; devuelve el número de gates válidos."""
    logicas = lineas_logicas(texto)
    codigo = "\n".join(logicas)
    if VAR_TRIVY.search(codigo):
        error(f"{donde}: variable TRIVY_* prohibida (trivy lee cualquier TRIVY_*; QA-OPS006-04)")
    if ASIGNA_TRIVYCLI.search(codigo):
        error(f"{donde}: TRIVYCLI_* solo se define en el env del workflow (OBS-C3-3)")
    if CONFIG_TRIVY.search(codigo):
        error(f"{donde}: trivy.yaml/.trivyignore.yaml mencionado en el código (QA-OPS006-04)")
    if USO_PROHIBIDO.search(codigo):
        error(f"{donde}: uso de trivy-action / setup-trivy / aquasec/trivy / install.sh prohibido")
    invs: dict[int, list[tuple[str, str, str]]] = {}
    tipos: set[str] = set()
    for k, linea in enumerate(logicas):
        s = linea.strip()
        if s == INSTALACION[2]:
            previas = [x.strip() for x in logicas[:k] if x.strip()][-2:]
            if previas != list(INSTALACION[:2]):
                error(
                    f"{donde}: la extracción de trivy exige justo antes la descarga y "
                    f"'sha256sum -c' exactas (OBS-C3-3)"
                )
            RUNS_INSTALACION.add(donde)
            continue
        for m in APARICION.finditer(linea):
            r = validar(linea, m.end(), donde, logicas)
            if r is None:
                tipos.add("error")
                continue
            invs.setdefault(k, []).append((r[0], linea[: m.start()].strip(), r[1]))
            tipos.add(r[0])
    for k, linea in enumerate(logicas):
        s = linea.strip()
        if TGZ in s and s not in INSTALACION:
            error(f"{donde}: {TGZ} solo en las 3 líneas de la instalación verificada: {s[:120]}")
        es_control = any(t == "control" for t, _, _ in invs.get(k, []))
        if NOMBRE_CONTROL in s and not (es_control or s in (GENERADOR_CADUCADO, GREP_CONTROL)):
            error(f"{donde}: {IGNOREFILE_CONTROL} fuera del control negativo: {s[:120]}")
        es_gate = any(t == "gate" for t, _, _ in invs.get(k, []))
        if MENCION_IGNORE.search(s) and not (es_gate or s == GENERADOR_CADUCADO):
            error(f"{donde}: .trivyignore fuera del gate y del generador (OBS-C3-1): {s[:120]}")
    if invs and tipos & {"gate", "control"}:
        revisar_esqueleto(logicas, invs, donde)
    elif invs:
        for k, lst in invs.items():
            for _, prefijo, resto in lst:
                if prefijo or resto.strip():
                    error(f"{donde}: invocación de trivy con algo antes o después: {logicas[k]}")
    TIPOS_RUN[texto] = tipos
    return sum(1 for lst in invs.values() for t, _, _ in lst if t == "gate")


def tiene_trivy(texto: str) -> bool:
    return any(
        APARICION.search(linea) and linea.strip() != INSTALACION[2]
        for linea in lineas_logicas(texto)
    )


# ---------------------------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------------------------
def recorrer(nodo: Any, ruta: str, fichero: str, sensible: bool = False) -> None:
    """sensible: dentro de with:/env: (valores que acaban en ficheros o en el entorno)."""
    global gates
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            clave = str(k).strip()
            if VAR_TRIVY.search(clave):
                error(f"{fichero}:{ruta}.{k}: variable TRIVY_* prohibida (QA-OPS006-04)")
            if clave in VERSION_BIN:
                if ruta != ".env":
                    error(f"{fichero}:{ruta}.{k}: {clave} solo en el env del workflow (OBS-C3-3)")
                elif not (isinstance(v, str) and re.fullmatch(VERSION_BIN[clave], v)):
                    error(f"{fichero}:{ruta}.{k}: valor no válido: {v!r}")
            elif clave.startswith("TRIVYCLI_"):
                error(f"{fichero}:{ruta}.{k}: TRIVYCLI_* no reconocida")
            if k == "uses" and isinstance(v, str) and USO_PROHIBIDO.search(v):
                error(f"{fichero}:{ruta}: uses: {v} prohibido (solo el binario verificado)")
            if k == "with" and isinstance(v, dict):
                claves = {str(x).lower() for x in v}
                if claves & {"ignore-unfixed", "trivyignores", "trivy-config", "skip-files"}:
                    error(f"{fichero}:{ruta}.with: parámetros de trivy {sorted(claves)}")
            if k == "run" and isinstance(v, str):
                gates += revisar_shell(v, f"{fichero}:{ruta}.run")
            else:
                recorrer(v, f"{ruta}.{k}", fichero, sensible or k in ("with", "env"))
    elif isinstance(nodo, list):
        for i, v in enumerate(nodo):
            recorrer(v, f"{ruta}[{i}]", fichero, sensible)
    elif isinstance(nodo, str):
        # Fuera de "run:": no se ejecuta como shell, pero "trivy <subcomando>" es sospechoso.
        for m in APARICION.finditer(nodo):
            siguiente = nodo[m.end() :].split()
            if siguiente and siguiente[0] in SUBCOMANDOS_TRIVY:
                error(f"{fichero}:{ruta}: invocación de trivy fuera de un run: {nodo[:120]}")
        if VAR_TRIVY.search(nodo) or USO_PROHIBIDO.search(nodo):
            error(f"{fichero}:{ruta}: configuración de trivy prohibida en un valor YAML")
        if sensible and (CONFIG_TRIVY.search(nodo) or MENCION_IGNORE.search(nodo)):
            error(f"{fichero}:{ruta}: .trivyignore/trivy.yaml en un valor de with:/env: (OBS-C3-1)")


def _wd_y_shell(nodo: Any) -> tuple[Any, Any]:
    run = ((nodo or {}).get("defaults") or {}).get("run") or {}
    return run.get("working-directory"), run.get("shell")


def revisar_pasos(doc: Any, fichero: str) -> None:
    """working-directory (todo paso con trivy) y, para pasos con gate o control negativo,
    continue-on-error, if: y shell (OBS-C3-2)."""
    if not isinstance(doc, dict):
        return
    wd_flujo, sh_flujo = _wd_y_shell(doc)
    for nombre, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        wd_job, sh_job = _wd_y_shell(job)
        for i, paso in enumerate(job.get("steps") or []):
            if not isinstance(paso, dict) or not isinstance(paso.get("run"), str):
                continue
            donde = f"{fichero}:.jobs.{nombre}.steps[{i}]"
            wd = paso.get("working-directory") or wd_job or wd_flujo
            if wd and wd not in {".", "./"} and tiene_trivy(paso["run"]):
                error(
                    f"{donde}: trivy con working-directory {wd} (el .trivyignore es el de la raíz)"
                )
            if not TIPOS_RUN.get(paso["run"], set()) & {"gate", "control"}:
                continue
            for ambito, valor in (("paso", paso), ("job", job)):
                if valor.get("continue-on-error", False) is not False:
                    error(f"{donde}: continue-on-error en el {ambito} de un gate (OBS-C3-2)")
            if "if" in paso:
                error(f"{donde}: 'if:' en el paso de un gate/control: podría no ejecutarse")
            shell = paso.get("shell") or sh_job or sh_flujo
            if shell not in (None, "bash"):
                error(f"{donde}: shell '{shell}' en un gate (solo bash: -e y pipefail)")


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
            revisar_pasos(doc, rel)
            if any(d.startswith(rel + ":") for d in RUNS_INSTALACION):
                env = (doc.get("env") if isinstance(doc, dict) else None) or {}
                if any(c not in env for c in VERSION_BIN):
                    error(f"{rel}: la instalación de trivy exige TRIVYCLI_* en el env del workflow")
    for f in ficheros(raiz, ("*.sh",)):
        rel = f.relative_to(raiz).as_posix()
        if rel not in EXCLUIDOS_SH:
            # un gate en un *.sh también se valida, pero el obligatorio está en un workflow
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
