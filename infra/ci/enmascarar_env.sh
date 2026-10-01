#!/usr/bin/env bash
# =============================================================================
# Enmascara en el log de GitHub Actions los secretos EFÍMEROS del .env de CI (TKT-OPS-022, F-PRE-01).
# Uso:  bash infra/ci/enmascarar_env.sh RUTA_ENV [VARIABLE_OBLIGATORIA ...]
#   Emite "::add-mask::<valor>" por cada variable del .env cuyo nombre termina en _PASSWORD, _KEY,
#   _SECRET o _TOKEN y tiene valor; desde ese momento el runner sustituye el valor por *** en el log
#   (también en los pasos siguientes). DEBE ejecutarse ANTES de exportar nada a $GITHUB_ENV o de
#   imprimir el .env. Falla (exit 1) si el .env no existe o si una VARIABLE_OBLIGATORIA falta o está
#   vacía: así un cambio de nombre en scripts/ops/init-env.sh no deja un secreto sin máscara.
# Los valores son aleatorios por ejecución (init-env.sh), no secretos reales (CLAUDE.md §0.5).
# =============================================================================
set -euo pipefail

env_file="${1:?uso: enmascarar_env.sh RUTA_ENV [VARIABLE_OBLIGATORIA ...]}"
shift
[ -f "$env_file" ] || { echo "::error::enmascarar_env: no existe ${env_file}"; exit 1; }

declare -A vistos=()
n=0
while IFS= read -r linea || [ -n "$linea" ]; do
  [[ "$linea" =~ ^([A-Z][A-Z0-9_]*(_PASSWORD|_KEY|_SECRET|_TOKEN))=(.*)$ ]] || continue
  nombre="${BASH_REMATCH[1]}"
  valor="${BASH_REMATCH[3]}"
  [ -n "$valor" ] || continue
  echo "::add-mask::${valor}"
  vistos["$nombre"]=1
  n=$((n + 1))
done < "$env_file"

fallos=0
for obligatoria in "$@"; do
  if [ -z "${vistos[$obligatoria]:-}" ]; then
    echo "::error::enmascarar_env: ${obligatoria} falta o está vacía en ${env_file}: no se puede enmascarar"
    fallos=$((fallos + 1))
  fi
done
echo "enmascarar_env: ${n} valores enmascarados (${#vistos[@]} variables); obligatorias: $*"
[ "$fallos" -eq 0 ]
