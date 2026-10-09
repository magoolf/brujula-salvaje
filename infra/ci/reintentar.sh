#!/usr/bin/env bash
# =============================================================================
# Reintentos con backoff exponencial para pasos que dependen de registros remotos (TKT-OPS-033).
# Uso:  bash infra/ci/reintentar.sh INTENTOS ESPERA_INICIAL_SEG -- comando [args...]
# Reintenta el comando hasta INTENTOS veces, esperando ESPERA_INICIAL_SEG, luego el doble, etc.
# Devuelve el código del último intento: un error real (Dockerfile roto) sigue fallando el job,
# solo tarda algo más; nunca convierte un fallo en éxito. Cada reintento deja un ::warning:: visible.
# =============================================================================
set -uo pipefail
[[ "${1:-}" =~ ^[1-9][0-9]*$ && "${2:-}" =~ ^[0-9]+$ ]] \
  || { echo "uso: reintentar.sh INTENTOS ESPERA_INICIAL_SEG -- comando..." >&2; exit 2; }
intentos="$1"; espera="$2"; shift 2
[ "${1:-}" = "--" ] && shift
[ "$#" -gt 0 ] || { echo "reintentar.sh: falta el comando" >&2; exit 2; }
i=1
while :; do
  "$@"
  rc=$?
  [ "$rc" -eq 0 ] && exit 0
  if [ "$i" -ge "$intentos" ]; then
    echo "::error::falló tras ${i} intento(s) (rc=${rc}): $*"
    exit "$rc"
  fi
  echo "::warning::intento ${i}/${intentos} falló (rc=${rc}); reintento en ${espera}s: $*"
  sleep "$espera"
  espera=$((espera * 2))
  i=$((i + 1))
done
