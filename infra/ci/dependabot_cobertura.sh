#!/usr/bin/env bash
# =============================================================================
# Cobertura de Dependabot (RSK-OPS-025, OBS-4; TKT-OPS-006, DEC-AUTO-254/257).
# Uso:  bash infra/ci/dependabot_cobertura.sh [RAÍZ]
# Falla si algún Dockerfile/Containerfile (cualquier mayúscula; Dockerfile, *.Dockerfile,
# Dockerfile.*, Containerfile, *.Containerfile, Containerfile.*) está en un directorio que no figura
# en el ecosistema "docker" de .github/dependabot.yml, o si algún FROM (también "from", con
# --platform) usa una variable: Dependabot no resuelve ARG en FROM y la imagen quedaría sin vigilar.
# =============================================================================
set -euo pipefail
cd "${1:-.}"
bloque="$(awk '/package-ecosystem: "docker"$/{d=1;next} d&&/package-ecosystem:/{d=0} d' .github/dependabot.yml | grep -E '^[[:space:]]*directories?:')"
echo "dependabot docker: ${bloque}"
rc=0
while IFS= read -r f; do
  dir="/$(dirname "${f#./}")"
  grep -qF "\"${dir}\"" <<<"$bloque" || { echo "::error::${f} no está en el ecosistema docker de Dependabot (${dir})"; rc=1; }
  if grep -niE '^[[:space:]]*FROM[[:space:]]+(--[^[:space:]]+[[:space:]]+)*[^[:space:]]*\$' "$f"; then
    echo "::error::${f}: FROM con variable (Dependabot no la resuelve)"; rc=1
  fi
done < <(find . -path ./.git -prune -o -path ./.agent -prune -o -path ./.claude -prune -o -name node_modules -prune -o -name .venv -prune -o -type f \( -iname 'Dockerfile' -o -iname '*.Dockerfile' -o -iname 'Dockerfile.*' -o -iname 'Containerfile' -o -iname '*.Containerfile' -o -iname 'Containerfile.*' \) ! -iname '*.dockerignore' ! -iname '*.containerignore' -print)
exit $rc
