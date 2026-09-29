#!/usr/bin/env bash
# =============================================================================
# Controles de infra/ci/dependabot_cobertura.sh (TKT-OPS-006, RSK-OPS-025, OBS-4, DEC-AUTO-257).
# Uso:  bash infra/ci/dependabot_cobertura_controles.sh [SCRIPT]
# Copia infra/ y .github/dependabot.yml a raíces temporales, introduce UNA variante y exige el
# código de salida esperado.
# =============================================================================
set -uo pipefail

script="$(cd "$(dirname "${1:-infra/ci/dependabot_cobertura.sh}")" && pwd)/$(basename "${1:-infra/ci/dependabot_cobertura.sh}")"
base="$(mktemp -d)"
trap 'rm -rf "$base"' EXIT
fallos=0
n=0

# caso <nombre> <rc esperado> <comando de preparación, se ejecuta dentro de la raíz temporal>
caso() {
  local nombre="$1" esperado="$2" prep="$3" r rc
  n=$((n + 1))
  r="${base}/c${n}"
  mkdir -p "${r}/.github"
  cp -R infra "${r}/infra"
  cp .github/dependabot.yml "${r}/.github/dependabot.yml"
  (cd "$r" && eval "$prep")
  bash "$script" "$r" > "${r}.log" 2>&1
  rc=$?
  if [ "$rc" = "$esperado" ]; then
    echo "OK  | ${nombre} | esperado ${esperado} | rc ${rc} | $(grep -m1 -oE '::error::.{0,80}' "${r}.log" || true)"
  else
    echo "MAL | ${nombre} | esperado ${esperado} | rc ${rc}"; sed 's/^/      /' "${r}.log"; fallos=$((fallos + 1))
  fi
}

caso "P0 repositorio tal cual" 0 ":"
caso "P1 Dockerfile nuevo en un directorio ya listado, FROM literal" 0 "printf 'FROM alpine:3.22\n' > infra/proxy/Dockerfile.dev"
caso "N1 falta /infra/db en dependabot.yml" 1 "sed -i 's#\"/infra/db\", ##' .github/dependabot.yml"
caso "N2 FROM \${X}" 1 "printf 'ARG X=a:1\nFROM \${X}\n' > infra/proxy/Dockerfile"
caso "N3 Dockerfile nuevo en directorio no listado" 1 "mkdir -p infra/nuevo && printf 'FROM alpine:3.22\n' > infra/nuevo/Dockerfile"
caso "N4 FROM --platform con variable" 1 "printf 'FROM --platform=linux/amd64 \${IMG} AS x\n' > infra/db/Dockerfile"
caso "N5 FROM \$IMG sin llaves" 1 "printf 'FROM \$IMG\n' > infra/proxy/Dockerfile"
caso "N6 from \${IMG} en minúsculas" 1 "printf 'from \${IMG} as x\n' > infra/proxy/Dockerfile"
caso "N7 Containerfile en directorio no listado" 1 "mkdir -p infra/c1 && printf 'FROM alpine:3.22\n' > infra/c1/Containerfile"
caso "N8 app.dockerfile (minúsculas) en directorio no listado" 1 "mkdir -p infra/c2 && printf 'FROM alpine:3.22\n' > infra/c2/app.dockerfile"
caso "N9 Containerfile.dev con variable en directorio listado" 1 "printf 'FROM \$X\n' > infra/proxy/Containerfile.dev"

echo "controles: ${n}; fallos: ${fallos}"
test "$fallos" = 0
