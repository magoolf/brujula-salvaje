#!/usr/bin/env bash
# =============================================================================
# Controles de la política de trivy (TKT-OPS-006: QA-OPS005-04, DEC-AUTO-252; ciclo 2: QA-OPS006-01/02,
# OBS-3, DEC-AUTO-256). Ojo al escribir casos: dentro de comillas dobles, "\\" + salto se queda como
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
caso "Q14 barra seguida de espacio (no continúa)" 0 wf "${I}trivy image --severity CRITICAL,HIGH img \ 
${I}echo --ignore-unfixed"
caso "Q15 tabulador + continuación con --vex" 1 wf "${I}trivy	image --severity CRITICAL,HIGH \\
${I}	--vex v.json img"
caso "Q16 flag global antes del subcomando" 1 wf "${I}trivy -q image --severity CRITICAL,HIGH --ignore-unfixed img"
caso "Q17 ruta absoluta al binario" 1 wf "${I}/usr/local/bin/trivy image --severity CRITICAL,HIGH --skip-dirs x img"
caso "Q18 script .sh del repositorio con opción prohibida" 1 sh "trivy image --severity CRITICAL,HIGH \\
  --ignore-unfixed img"
caso "Q19 workflow YAML no válido" 1 yaml "jobs: [x"

echo "controles: ${n}; fallos: ${fallos}"
test "$fallos" = 0
