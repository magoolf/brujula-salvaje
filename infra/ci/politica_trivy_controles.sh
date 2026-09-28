#!/usr/bin/env bash
# shellcheck disable=SC2016  # los casos B* van entre comillas simples a propósito: $ literal
# =============================================================================
# Controles de la política de trivy (TKT-OPS-006): QA-OPS005-04 (DEC-AUTO-252); ciclo 2 QA-OPS006-01/02,
# OBS-3 (DEC-AUTO-256); ciclo 3 LISTA BLANCA, QA-OPS006-03/OBS-C2-1 (DEC-AUTO-915/258).
# Ojo al escribir casos: dentro de comillas dobles, "\\" + salto se queda como
# "\" + salto en el fichero; una sola "\" + salto la ELIMINA bash y junta las dos líneas.
# Uso:  bash infra/ci/politica_trivy_controles.sh [POLITICA]   (por defecto infra/ci/politica_trivy.sh)
# Copia .github/workflows y .trivyignore del repositorio a raíces temporales, introduce en cada una
# UNA variante (multilínea incluida) y exige el código de salida esperado de la política.
# Los textos de prueba viven aquí (infra/ci), no en .github/workflows: la política no los ve en el
# repositorio real.
# =============================================================================
set -uo pipefail

politica="$(cd "$(dirname "${1:-infra/ci/politica_trivy.sh}")" && pwd)/$(basename "${1:-infra/ci/politica_trivy.sh}")"
base="$(mktemp -d)"
trap 'rm -rf "$base"' EXIT
fallos=0
n=0

# caso <nombre> <rc esperado> <tipo: wf|crlf|yaml|sh|ign|fichero|nada> <contenido>
caso() {
  local nombre="$1" esperado="$2" tipo="$3" contenido="${4:-}" r rc
  n=$((n + 1))
  r="${base}/c${n}"
  mkdir -p "${r}/.github"
  cp -R .github/workflows "${r}/.github/workflows"
  cp .trivyignore "${r}/.trivyignore"
  case "$tipo" in
    wf)      printf 'jobs:\n  x:\n    steps:\n      - run: |\n%s\n' "$contenido" > "${r}/.github/workflows/zz-control.yaml" ;;
    crlf)    printf 'jobs:\n  x:\n    steps:\n      - run: |\n%s\n' "$contenido" | sed 's/$/\r/' > "${r}/.github/workflows/zz-control.yaml" ;;
    yaml)    printf '%s
' "$contenido" > "${r}/.github/workflows/zz-control.yaml" ;;
    sh)      mkdir -p "${r}/scripts/ops"; printf '#!/usr/bin/env bash
%s
' "$contenido" > "${r}/scripts/ops/zz-control.sh" ;;
    ign)     printf '%s\n' "$contenido" >> "${r}/.trivyignore" ;;
    fichero) mkdir -p "$(dirname "${r}/${contenido}")"; echo 'severity: [CRITICAL]' > "${r}/${contenido}" ;;
    nada)    ;;
  esac
  bash "$politica" "$r" > "${r}.log" 2>&1
  rc=$?
  if [ "$rc" = "$esperado" ]; then
    echo "OK  | ${nombre} | esperado ${esperado} | rc ${rc} | $(grep -m1 -oE '::error::.{0,70}' "${r}.log" || true)"
  else
    echo "MAL | ${nombre} | esperado ${esperado} | rc ${rc}"; sed 's/^/      /' "${r}.log"; fallos=$((fallos + 1))
  fi
}

I='          '   # sangría del bloque "run: |"
# --- positivos -------------------------------------------------------------------------------
caso "P0 repositorio tal cual" 0 nada
caso "P1 invocación válida partida en 3 líneas" 0 wf "${I}trivy image \\
${I}  --scanners vuln \\
${I}  --severity CRITICAL,HIGH --exit-code 1 img"
caso "P2 opción prohibida solo en un comentario" 0 wf "${I}# trivy image --severity CRITICAL,HIGH --ignore-unfixed img"
# --- negativos de una línea (regresión de TKT-OPS-005) ---------------------------------------
caso "S1 --ignore-unfixed en una línea" 1 wf "${I}trivy image --severity CRITICAL,HIGH --ignore-unfixed img"
caso "S2 variable TRIVY_IGNORE_UNFIXED" 1 wf "${I}TRIVY_IGNORE_UNFIXED=true trivy image --severity CRITICAL,HIGH img"
caso "S3 severidad distinta" 1 wf "${I}trivy image --severity CRITICAL img"
caso "S4 fichero trivy.yaml" 1 fichero "sub/trivy.yaml"
caso "S5 entrada de .trivyignore sin caducidad" 1 ign "CVE-2099-12345"
caso "S6 comodín en .trivyignore" 1 ign "CVE-* exp:2099-01-01"
# --- negativos MULTILÍNEA (QA-OPS005-04) -----------------------------------------------------
caso "M1 --ignore-unfixed en la línea de continuación" 1 wf "${I}trivy image --severity CRITICAL,HIGH \\
${I}  --ignore-unfixed img"
caso "M2 --config en la 3.ª línea" 1 wf "${I}trivy image \\
${I}  --severity CRITICAL,HIGH \\
${I}  --config /tmp/t.yaml img"
caso "M3 -c en la línea de continuación" 1 wf "${I}trivy image --severity CRITICAL,HIGH \\
${I}  -c /tmp/t.yaml img"
caso "M4 --skip-files en la línea de continuación" 1 wf "${I}trivy fs --severity CRITICAL,HIGH \\
${I}  --skip-files x ."
caso "M5 'trivy' e 'image' en líneas distintas" 1 wf "${I}trivy \\
${I}  image --severity CRITICAL,HIGH --vex /tmp/v.json img"
caso "M6 --ignore-status tras continuación" 1 wf "${I}trivy rootfs --severity CRITICAL,HIGH \\
${I}  --ignore-status will_not_fix /"
caso "M7 --ignore-policy en trivy config multilínea" 1 wf "${I}trivy config \\
${I}  --ignore-policy p.rego ."
caso "M8 severidad solo en otra invocación (la partida no la lleva)" 1 wf "${I}trivy image \\
${I}  --exit-code 1 img"
caso "M9 continuación con fin de línea CRLF" 1 crlf "${I}trivy image --severity CRITICAL,HIGH \\
${I}  --ignore-unfixed img"

# --- ciclo 2: comentarios, escalares YAML, opciones que anulan, trivy-action (QA-OPS006) ---
caso "Q1 comentario terminado en \ NO continúa: la invocación siguiente se evalúa" 1 wf "${I}# nota \\
${I}trivy image --severity CRITICAL,HIGH --ignore-unfixed img"
caso "Q2 comentario tras código terminado en \ + --config en la siguiente" 1 wf "${I}echo a # ver \\
${I}trivy image --severity CRITICAL,HIGH --config /t.yaml img"
caso "Q3 escalar folded (run: >) con la opción en la 2.ª línea" 1 yaml "jobs:
  x:
    steps:
      - run: >
          trivy image --severity CRITICAL,HIGH
          --ignore-unfixed img"
caso "Q4 escalar plano multilínea con la opción en la 2.ª línea" 1 yaml "jobs:
  x:
    steps:
      - run: trivy image --severity CRITICAL,HIGH
          --ignore-unfixed img"
caso "Q7 opción prohibida solo en un comentario al final de la línea" 0 wf "${I}trivy image --severity CRITICAL,HIGH --exit-code 1 img # no usar --ignore-unfixed"
caso "Q8 comentario terminado en \ seguido de una línea inocua" 0 wf "${I}# trivy image --ignore-unfixed \\
${I}echo hola"
caso "Q9 segunda --severity que anula la primera" 1 wf "${I}trivy image --severity CRITICAL,HIGH --severity LOW img"
caso "Q10 -s que anula --severity" 1 wf "${I}trivy image --severity CRITICAL,HIGH -s LOW img"
caso "Q10b --severity=LOW" 1 wf "${I}trivy image --severity=LOW img"
caso "Q11 --ignorefile alternativo" 1 wf "${I}trivy image --severity CRITICAL,HIGH --ignorefile /tmp/otro --exit-code 1 img"
caso "Q12 --exit-code 0" 1 wf "${I}trivy image --severity CRITICAL,HIGH --exit-code 0 img"
caso "Q12b gate (--ignorefile) sin --exit-code" 1 wf "${I}trivy image --severity CRITICAL,HIGH --ignorefile .trivyignore img"
caso "Q13 aquasecurity/trivy-action" 1 yaml "jobs:
  x:
    steps:
      - uses: aquasecurity/trivy-action@0000000000000000000000000000000000000000
        with: {scan-type: image, severity: CRITICAL, ignore-unfixed: true}"
caso "Q13b imagen aquasec/trivy" 1 wf "${I}docker run --rm aquasec/trivy:0.74.0 image --severity CRITICAL,HIGH img"
caso "Q13c clave env TRIVY_IGNORE_UNFIXED" 1 yaml "env:
  TRIVY_IGNORE_UNFIXED: 'true'
jobs:
  x:
    steps:
      - run: echo hola"
# Q14: "\ " no continúa la línea: pasa un 2.º argumento " " a trivy -> la lista blanca lo rechaza.
caso "Q14 barra seguida de espacio: no continúa y añade un argumento extra" 1 wf "${I}trivy image --severity CRITICAL,HIGH img \ 
${I}echo --ignore-unfixed"
caso "Q15 tabulador + continuación con --vex" 1 wf "${I}trivy	image --severity CRITICAL,HIGH \\
${I}	--vex v.json img"
caso "Q16 flag global antes del subcomando" 1 wf "${I}trivy -q image --severity CRITICAL,HIGH --ignore-unfixed img"
caso "Q17 ruta absoluta al binario" 1 wf "${I}/usr/local/bin/trivy image --severity CRITICAL,HIGH --skip-dirs x img"
caso "Q18 script .sh del repositorio con opción prohibida" 1 sh "trivy image --severity CRITICAL,HIGH \\
  --ignore-unfixed img"
caso "Q19 workflow YAML no válido" 1 yaml "jobs: [x"

# --- ciclo 3: LISTA BLANCA (QA-OPS006-03, OBS-C2-1, DEC-AUTO-915/258) -------------------------
# Contenido entre comillas SIMPLES: los $ y $(...) llegan literales al fixture.
caso "B01 flag global con valor antes del subcomando + --ignore-unfixed" 1 wf '          trivy --cache-dir /tmp/c image --severity CRITICAL,HIGH --ignore-unfixed img'
caso "B02 --timeout antes del subcomando + --skip-dirs" 1 wf '          trivy --timeout 10m image --severity CRITICAL,HIGH --skip-dirs x img'
caso "B03 --cache-dir antes del subcomando, sin severidad" 1 wf '          trivy --cache-dir /tmp/c image --ignore-unfixed img'
caso "B04 opción generada con \$(...)" 1 wf '          trivy image --severity CRITICAL,HIGH $(echo --ignore-unfixed) img'
caso "B05 --scanners secret" 1 wf '          trivy image --severity CRITICAL,HIGH --scanners secret --ignorefile .trivyignore --exit-code 1 img'
caso "B06 --pkg-types os" 1 wf '          trivy image --severity CRITICAL,HIGH --pkg-types os --exit-code 1 img'
caso "B07 flag prohibido entre comillas" 1 wf '          trivy image --severity CRITICAL,HIGH "--ignore-unfixed" img'
caso "B08 --ignore-unfixed=true" 1 wf '          trivy image --severity CRITICAL,HIGH --ignore-unfixed=true img'
caso "B09 opciones en variable \$OPTS" 1 wf '          OPTS=--ignore-unfixed; trivy image --severity CRITICAL,HIGH $OPTS img'
caso "B10 binario en variable (T=trivy; \$T image …)" 1 wf '          T=trivy; $T image --severity CRITICAL,HIGH --ignore-unfixed img'
caso "B11 --skip-db-update + --db-repository ajeno" 1 wf '          trivy image --severity CRITICAL,HIGH --skip-db-update --db-repository ghcr.io/evil/db --exit-code 1 img'
caso "B12 --exit-code=0" 1 wf '          trivy image --severity CRITICAL,HIGH --exit-code=0 img'
caso "B13 gate válido con -s y --ignorefile=.trivyignore" 0 wf '          trivy image -s CRITICAL,HIGH --ignorefile=.trivyignore --exit-code 1 img'
caso "B14 cd antes del gate" 1 wf '          cd /tmp/x && trivy image --severity CRITICAL,HIGH --ignorefile .trivyignore --exit-code 1 img'
caso "B15 expresión \${{ }} como argumento" 1 yaml 'jobs:
  x:
    steps:
      - run: trivy image --severity CRITICAL,HIGH ${{ env.EXTRA }} img'
caso "B16 trivy dentro de python -c" 1 yaml 'jobs:
  x:
    steps:
      - run: python -c "import os; os.system('"'"'trivy image --severity CRITICAL,HIGH --ignore-unfixed img'"'"')"'
caso "B17 flags globales permitidos antes del subcomando" 0 wf '          trivy --cache-dir /tmp/c --timeout 10m -q image --severity CRITICAL,HIGH --no-progress img'
caso "B18 --scanners vuln,secret" 1 wf '          trivy image --scanners vuln,secret --severity CRITICAL,HIGH img'
caso "B19 subcomando fs (no usado por el CI)" 1 wf '          trivy fs --severity CRITICAL,HIGH .'
caso "B20 objetivo entre comillas con variable que no empieza por brujula/" 1 wf '          trivy image --severity CRITICAL,HIGH "$img"'
caso "B21 objetivo brujula/ entre comillas con variables" 0 wf '          trivy image --severity CRITICAL,HIGH --format json --output "reports/t-${s}.json" "brujula/${s}:${APP_VERSION}"'
caso "B22 --output con variable SIN comillas" 1 wf '          trivy image --severity CRITICAL,HIGH --output reports/$s.json img'
caso "B23 dos objetivos" 1 wf '          trivy image --severity CRITICAL,HIGH img1 img2'
caso "B24 --ignorefile del control negativo fuera de su forma" 1 wf '          trivy image --severity CRITICAL,HIGH --ignorefile /tmp/trivyignore-caducado --exit-code 1 img'
caso "B25 working-directory en un paso con trivy" 1 yaml 'jobs:
  x:
    steps:
      - working-directory: sub
        run: trivy image --severity CRITICAL,HIGH img'
caso "B26 invocación en un valor que no es run" 1 yaml 'jobs:
  x:
    steps:
      - uses: actions/github-script@0000000000000000000000000000000000000000
        with: {script: "trivy image --severity CRITICAL,HIGH --ignore-unfixed img"}'
caso "B27 sin comillas de cierre" 1 wf '          trivy image --severity "CRITICAL,HIGH img'

echo "controles: ${n}; fallos: ${fallos}"
test "$fallos" = 0
