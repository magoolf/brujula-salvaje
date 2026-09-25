#!/usr/bin/env bash
# =============================================================================
# Genera el .env LOCAL a partir de .env.example (TKT-F6-001).
# Sustituye cada CHANGE_ME por un valor aleatorio local (no son secretos reales: solo sirven
# para este equipo y se pueden regenerar). Nunca sobrescribe un .env existente.
#   Uso:  bash scripts/ops/init-env.sh [ruta_destino]      (por defecto ./.env)
#   CI:   bash scripts/ops/init-env.sh .env   (valores efímeros por ejecución)
# Requiere: openssl (incluido en Git for Windows, macOS y Linux).
# =============================================================================
set -Eeuo pipefail
cd "$(dirname "$0")/../.."

DEST="${1:-.env}"
SRC=".env.example"

if [[ -e "${DEST}" ]]; then
  echo "${DEST} ya existe: no se sobrescribe (bórralo a mano si quieres regenerarlo)." >&2
  exit 1
fi
command -v openssl >/dev/null || { echo "openssl no encontrado" >&2; exit 1; }

hex32()   { openssl rand -hex 32; }
fernet()  { openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n'; }

tmp="$(mktemp)"
trap 'rm -f "${tmp}"' EXIT
while IFS= read -r line || [[ -n "${line}" ]]; do
  line="${line%$'\r'}"
  case "${line}" in
    *=CHANGE_ME_FERNET) printf '%s=%s\n' "${line%%=*}" "$(fernet)" ;;
    *=CHANGE_ME)        printf '%s=%s\n' "${line%%=*}" "$(hex32)" ;;
    *)                  printf '%s\n' "${line}" ;;
  esac
done < "${SRC}" > "${tmp}"

mv "${tmp}" "${DEST}"
chmod 600 "${DEST}" 2>/dev/null || true
echo "Creado ${DEST} con valores locales aleatorios. BACKUP_AGE_RECIPIENT sigue sin configurar (ver DEVOPS_HANDOFF.md §5.4)."
