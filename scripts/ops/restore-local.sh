#!/usr/bin/env bash
# =============================================================================
# Restauración LOCAL de una copia (simulacro AC-054; ADR-DB-004 §4) — TKT-F6-001
# SOLO para entornos locales/efímeros. Restaurar sobre datos reales es Puerta Humana
# (CLAUDE.md §0.5): el script exige --confirmar-entorno-local y RESTORE_ENV=local.
#
# Uso (dentro del contenedor backup, con la clave PRIVADA age montada solo durante el simulacro):
#   restore-local.sh --confirmar-entorno-local <AAAAMMDD> <ruta_clave_privada_age>
#
# Pasos que ejecuta: descifrado + verificación sha256 -> pg_restore en la BD (con app_migrator)
#   -> extracción de medios en MEDIA_RESTORE_DIR -> sha256sum -c del manifiesto.
# Pasos que quedan al operador (comandos de la aplicación, F7) y que se imprimen al final:
#   panel cerrado -> reaplicar_anonimizaciones -> anonimizar_cuentas -> purgar_auditoria
#   -> purgar_sesiones -> reindexar_busqueda -> verificar_busqueda -> /health/ready.
# =============================================================================
set -Eeuo pipefail
umask 077

[[ "${1:-}" == "--confirmar-entorno-local" ]] || { echo "Falta --confirmar-entorno-local (Puerta Humana §0.5 para datos reales)" >&2; exit 2; }
[[ "${RESTORE_ENV:-}" == "local" ]] || { echo "RESTORE_ENV debe ser 'local'" >&2; exit 2; }
STAMP="${2:?AAAAMMDD}"
KEY="${3:?ruta a la clave privada age}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
MEDIA_RESTORE_DIR="${MEDIA_RESTORE_DIR:?directorio vacío donde extraer los medios}"
: "${PGHOST:?}" "${PGDATABASE:?}"
: "${RESTORE_PGUSER:=app_migrator}" "${RESTORE_PGPASSWORD:?contraseña de app_migrator (local)}"

SRC="${BACKUP_DIR}/diarias/${STAMP}"
WORK="$(mktemp -d /tmp/restore.XXXXXX)"
trap 'rm -rf "${WORK}"' EXIT
ts() { date -u +%FT%TZ; }
t0=$(date +%s)

echo "$(ts) verificación de los archivos cifrados"
( cd "${SRC}" && sha256sum -c "SHA256SUMS-cifrado-${STAMP}.txt" )
for f in "${SRC}"/*.age; do
  age --decrypt --identity "${KEY}" --output "${WORK}/$(basename "${f%.age}")" "$f"
done
( cd "${WORK}" && sha256sum -c "SHA256SUMS-${STAMP}.txt" )
t1=$(date +%s)

echo "$(ts) pg_restore (BD limpia 18.6 creada por INFRA-DB-000)"
PGUSER="${RESTORE_PGUSER}" PGPASSWORD="${RESTORE_PGPASSWORD}" \
  pg_restore --exit-on-error --no-owner --role="${RESTORE_PGUSER}" --dbname="${PGDATABASE}" "${WORK}/brujula-${STAMP}.dump"
t2=$(date +%s)

echo "$(ts) medios + verificación del manifiesto (AC-054)"
if [[ -n "$(ls -A "${MEDIA_RESTORE_DIR}" 2>/dev/null)" ]]; then
  echo "MEDIA_RESTORE_DIR no está vacío: se aborta para no mezclar medios" >&2; exit 3
fi
tar --extract --file="${WORK}/medios-${STAMP}.tar" --directory="${MEDIA_RESTORE_DIR}"
( cd "${MEDIA_RESTORE_DIR}" && sha256sum -c --quiet "${WORK}/medios-${STAMP}.sha256" )
t3=$(date +%s)

echo "$(ts) tiempos: descifrado=$((t1 - t0))s pg_restore=$((t2 - t1))s medios=$((t3 - t2))s"
cat <<'EOF'
Pasos siguientes (ADR-DB-004 §4, los ejecuta el operador con la aplicación en modo mantenimiento):
  docker compose run --rm scheduler python manage.py reaplicar_anonimizaciones
  docker compose run --rm scheduler python manage.py anonimizar_cuentas
  docker compose run --rm scheduler python manage.py purgar_auditoria
  docker compose run --rm scheduler python manage.py purgar_sesiones
  docker compose run --rm scheduler python manage.py reindexar_busqueda
  docker compose run --rm scheduler python manage.py verificar_busqueda
  curl -fsS http://127.0.0.1:8080/health/ready
Registrar los tiempos de cada paso como evidencia del simulacro (AC-054).
EOF
