#!/usr/bin/env bash
# =============================================================================
# Enmascara en el log de GitHub Actions los secretos EFÍMEROS del .env de CI (TKT-OPS-022, F-PRE-01;
# TKT-OPS-027, F-QA022-04).
# Uso:  bash infra/ci/enmascarar_env.sh RUTA_ENV [--plantilla RUTA_EXAMPLE] [VARIABLE_OBLIGATORIA ...]
#   Emite "::add-mask::<valor>" por cada variable del .env con valor que:
#     a) se llama *_PASSWORD, *_KEY, *_SECRET o *_TOKEN, o
#     b) (--plantilla) vale CHANGE_ME o CHANGE_ME_FERNET en RUTA_EXAMPLE: son EXACTAMENTE las que
#        scripts/ops/init-env.sh sustituye por un valor aleatorio (mismo criterio "case" que él).
#   Desde ese momento el runner sustituye el valor por *** en el log (también en los pasos
#   siguientes). DEBE ejecutarse ANTES de exportar nada a $GITHUB_ENV o de imprimir el .env.
#   Falla (exit 1) si el .env (o la plantilla) no existe, si la plantilla no declara ningún
#   CHANGE_ME, o si una variable obligatoria falta o está vacía. Son obligatorias las
#   VARIABLE_OBLIGATORIA explícitas y, con --plantilla, TODAS las CHANGE_ME de la plantilla: una
#   variable nueva con CHANGE_ME en .env.example queda enmascarada sin tocar el workflow, y un
#   cambio de nombre en init-env.sh no deja un secreto sin máscara.
# Los valores son aleatorios por ejecución (init-env.sh), no secretos reales (CLAUDE.md §0.5).
# =============================================================================
set -euo pipefail

uso="uso: enmascarar_env.sh RUTA_ENV [--plantilla RUTA_EXAMPLE] [VARIABLE_OBLIGATORIA ...]"
env_file="${1:?${uso}}"
shift
plantilla=""
if [ "${1:-}" = "--plantilla" ]; then
  plantilla="${2:?${uso}}"
  shift 2
fi
[ -f "$env_file" ] || { echo "::error::enmascarar_env: no existe ${env_file}"; exit 1; }

declare -A de_plantilla=()
obligatorias=("$@")
if [ -n "$plantilla" ]; then
  [ -f "$plantilla" ] || { echo "::error::enmascarar_env: no existe la plantilla ${plantilla}"; exit 1; }
  while IFS= read -r linea || [ -n "$linea" ]; do
    linea="${linea%$'\r'}"
    case "${linea}" in
      *=CHANGE_ME_FERNET|*=CHANGE_ME)
        de_plantilla["${linea%%=*}"]=1
        obligatorias+=("${linea%%=*}")
        ;;
    esac
  done < "$plantilla"
  if [ "${#de_plantilla[@]}" -eq 0 ]; then
    echo "::error::enmascarar_env: ${plantilla} no declara ninguna variable CHANGE_ME: falla cerrado"
    exit 1
  fi
fi

declare -A vistos=()
n=0
while IFS= read -r linea || [ -n "$linea" ]; do
  linea="${linea%$'\r'}"
  [[ "$linea" == *=* ]] || continue
  nombre="${linea%%=*}"
  valor="${linea#*=}"
  if [[ "$nombre" =~ ^[A-Z][A-Z0-9_]*(_PASSWORD|_KEY|_SECRET|_TOKEN)$ ]] || [ -n "${de_plantilla[$nombre]:-}" ]; then
    [ -n "$valor" ] || continue
    echo "::add-mask::${valor}"
    vistos["$nombre"]=1
    n=$((n + 1))
  fi
done < "$env_file"

fallos=0
declare -A revisadas=()
for obligatoria in "${obligatorias[@]}"; do
  [ -z "${revisadas[$obligatoria]:-}" ] || continue
  revisadas["$obligatoria"]=1
  if [ -z "${vistos[$obligatoria]:-}" ]; then
    echo "::error::enmascarar_env: ${obligatoria} falta o está vacía en ${env_file}: no se puede enmascarar"
    fallos=$((fallos + 1))
  fi
done
echo "enmascarar_env: ${n} valores enmascarados (${#vistos[@]} variables); obligatorias (${#revisadas[@]}): ${!revisadas[*]}"
[ "$fallos" -eq 0 ]
