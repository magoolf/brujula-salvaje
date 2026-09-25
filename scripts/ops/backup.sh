#!/usr/bin/env bash
# =============================================================================
# Copia de seguridad diaria — Brújula Salvaje (ADR-DB-004 §3, DEC-AUTO-093; TKT-F6-001)
#   1. pg_dump --format=custom --no-unlogged-table-data con el rol app_backup (+ sha256)
#   2. Manifiesto de medios desde la BD (medio.sha256_saneado, medio_derivado.sha256)
#   3. Copia del volumen de medios (tar) + copia del libro de anonimizaciones
#   4. Cifrado con age (clave pública BACKUP_AGE_RECIPIENT) y rotación de BACKUP_RETENTION_DAYS
# Idempotente por día: una segunda ejecución el mismo día sustituye la copia de ese día.
# Nunca imprime secretos. Falla (exit != 0) ante cualquier error: la alerta la da el log JSON.
# =============================================================================
set -Eeuo pipefail
umask 077

: "${PGHOST:?}" "${PGDATABASE:?}" "${PGUSER:?}" "${PGPASSWORD:?}"
: "${BACKUP_AGE_RECIPIENT:?BACKUP_AGE_RECIPIENT (clave pública age) es obligatoria: sin cifrado no hay copia}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
MEDIA_DIR="${MEDIA_DIR:-/srv/media}"
OPS_DIR="${OPS_DIR:-/srv/ops}"
RETENTION="${BACKUP_RETENTION_DAYS:-30}"

log() { printf '{"ts":"%s","componente":"backup","nivel":"%s","mensaje":"%s"}\n' "$(date -u +%FT%TZ)" "$1" "$2"; }
trap 'log ERROR "fallo en la línea ${LINENO}"; rm -rf "${WORK:-/nonexistent}"' ERR

case "${BACKUP_AGE_RECIPIENT}" in
  *CHANGE_ME*) log ERROR "BACKUP_AGE_RECIPIENT sin configurar (placeholder)"; exit 2 ;;
  age1*) ;;
  *) log ERROR "BACKUP_AGE_RECIPIENT no parece una clave pública age (age1...)"; exit 2 ;;
esac

STAMP="$(date -u +%Y%m%d)"
WORK="$(mktemp -d /tmp/backup.XXXXXX)"
DEST="${BACKUP_DIR}/diarias/${STAMP}"
t0=$(date +%s)

log INFO "inicio copia ${STAMP}"

# 1. Dump lógico de la BD (las tablas UNLOGGED, p. ej. cache_limites, se excluyen)
pg_dump --format=custom --no-unlogged-table-data --file="${WORK}/brujula-${STAMP}.dump"
pg_restore --list "${WORK}/brujula-${STAMP}.dump" > /dev/null   # verificación estructural del archivo
t1=$(date +%s)

# 2. Manifiesto de medios generado desde la BD (formato sha256sum -c, rutas relativas a MEDIA_DIR)
if psql --no-psqlrc -XAtq -c "SELECT to_regclass('app.medio') IS NOT NULL AND to_regclass('app.medio_derivado') IS NOT NULL" | grep -qx t; then
  psql --no-psqlrc -XAtq -F '  ' -c "
    SELECT sha256_saneado, archivo_saneado_ruta FROM app.medio
    UNION ALL
    SELECT sha256, ruta FROM app.medio_derivado
    ORDER BY 2" > "${WORK}/medios-${STAMP}.sha256"
else
  log WARN "tablas de medios inexistentes (esquema aún sin migrar): manifiesto vacío"
  : > "${WORK}/medios-${STAMP}.sha256"
fi

# 3. Medios (inmutables una vez escritos -> la copia posterior al dump es un superconjunto)
tar --create --file="${WORK}/medios-${STAMP}.tar" --directory="${MEDIA_DIR}" .
# Libro de anonimizaciones (solo ids, sin PII; ADR-DB-004 §4, DEC-AUTO-094)
if [[ -f "${OPS_DIR}/libro_anonimizaciones.log" ]]; then
  cp "${OPS_DIR}/libro_anonimizaciones.log" "${WORK}/libro_anonimizaciones-${STAMP}.log"
fi
t2=$(date +%s)

# 4. Sumas en claro -> cifrado -> sumas del cifrado
( cd "${WORK}" && sha256sum -- * > "SHA256SUMS-${STAMP}.txt" )
rm -rf "${DEST}.tmp"
mkdir -p "${DEST}.tmp"
for f in "${WORK}"/*; do
  age --encrypt --recipient "${BACKUP_AGE_RECIPIENT}" --output "${DEST}.tmp/$(basename "$f").age" "$f"
done
( cd "${DEST}.tmp" && sha256sum -- *.age > "SHA256SUMS-cifrado-${STAMP}.txt" )
rm -rf "${DEST}"
mv "${DEST}.tmp" "${DEST}"
rm -rf "${WORK}"
t3=$(date +%s)

# 5. Rotación: se conservan las RETENTION copias diarias más recientes (DEC-AUTO-052)
mapfile -t antiguas < <(find "${BACKUP_DIR}/diarias" -mindepth 1 -maxdepth 1 -type d -name '[0-9]*' | sort -r | tail -n +"$((RETENTION + 1))")
for d in "${antiguas[@]:-}"; do
  [[ -n "$d" ]] && rm -rf -- "$d" && log INFO "rotada $(basename "$d")"
done

log INFO "fin copia ${STAMP}: dump=$((t1 - t0))s medios=$((t2 - t1))s cifrado=$((t3 - t2))s total=$((t3 - t0))s"
