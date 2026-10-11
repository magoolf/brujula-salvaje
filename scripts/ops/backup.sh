#!/usr/bin/env bash
# =============================================================================
# Copia de seguridad diaria — Brújula Salvaje (ADR-DB-004 §3, DEC-AUTO-093; TKT-F6-001)
#   1. pg_dump --format=custom --no-unlogged-table-data con el rol app_backup (+ sha256)
#   2. Manifiesto de medios desde la BD (medio.sha256_saneado, medio_derivado.sha256)
#   3. Copia del volumen de medios (tar) + copia del libro de anonimizaciones
#   4. Cifrado con age (clave pública BACKUP_AGE_RECIPIENT) y rotación de BACKUP_RETENTION_DAYS
# Idempotente por día: una segunda ejecución el mismo día sustituye la copia de ese día.
# Nunca imprime secretos. Falla (exit != 0) ante cualquier error: la alerta la da el log JSON.
#
# Memoria acotada (RSK-OPS-029, DEC-AUTO-1201, TKT-OPS-008). El contenedor tiene un límite de 512 MiB
# y /tmp es tmpfs, es decir, memoria del cgroup. Por eso nada voluminoso pasa por /tmp:
#   - el directorio de trabajo está en DISCO, dentro del volumen de copias (BACKUP_WORK_PARENT, 0700,
#     uid 999). Solo guarda el dump y los ficheros pequeños, y se borra al terminar (los restos de una
#     ejecución interrumpida se borran al empezar la siguiente);
#   - el tar de medios (~5 GB previstos) NUNCA existe en claro: tar -> tee (sha256 en claro) -> age.
# El formato de la copia no cambia: mismos nombres y SHA256SUMS-AAAAMMDD.txt con la línea del tar.
# =============================================================================
set -Eeuo pipefail
umask 077

: "${PGHOST:?}" "${PGDATABASE:?}" "${PGUSER:?}" "${PGPASSWORD:?}"
: "${BACKUP_AGE_RECIPIENT:?BACKUP_AGE_RECIPIENT (clave pública age) es obligatoria: sin cifrado no hay copia}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
MEDIA_DIR="${MEDIA_DIR:-/srv/media}"
OPS_DIR="${OPS_DIR:-/srv/ops}"
RETENTION="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_WORK_PARENT="${BACKUP_WORK_PARENT:-${BACKUP_DIR}}"

log() { printf '{"ts":"%s","componente":"backup","nivel":"%s","mensaje":"%s"}\n' "$(date -u +%FT%TZ)" "$1" "$2"; }
trap 'log ERROR "fallo en la línea ${LINENO}"' ERR
# Limpieza siempre: el directorio de trabajo (dump en claro) y, si la copia no terminó, el .tmp
fin() {
  local rc=$?
  [[ -z "${pid_sha:-}" ]] || kill "${pid_sha}" 2>/dev/null || true
  rm -rf "${WORK:-/nonexistent}"
  (( rc == 0 )) || rm -rf "${DEST:-/nonexistent}.tmp"
}
trap fin EXIT

case "${BACKUP_AGE_RECIPIENT}" in
  *CHANGE_ME*) log ERROR "BACKUP_AGE_RECIPIENT sin configurar (placeholder)"; exit 2 ;;
  age1*) ;;
  *) log ERROR "BACKUP_AGE_RECIPIENT no parece una clave pública age (age1...)"; exit 2 ;;
esac

STAMP="$(date -u +%Y%m%d)"
# Restos de una copia interrumpida (OOM, kill...): solo los directorios de trabajo de COPIA
# (.trabajo-copia.*). Los de restauración (.trabajo-restaurar.*) pertenecen a restore-local.sh.
find "${BACKUP_WORK_PARENT}" -mindepth 1 -maxdepth 1 -type d -name '.trabajo-copia.*' -exec rm -rf -- {} +
WORK="$(mktemp -d "${BACKUP_WORK_PARENT}/.trabajo-copia.XXXXXX")"
DEST="${BACKUP_DIR}/diarias/${STAMP}"
rm -rf "${DEST}.tmp"
mkdir -p "${DEST}.tmp"
t0=$(date +%s)

log INFO "inicio copia ${STAMP}"

# 1. Dump lógico de la BD (las tablas UNLOGGED, p. ej. cache_limites, se excluyen)
pg_dump --format=custom --no-unlogged-table-data --file="${WORK}/brujula-${STAMP}.dump"
pg_restore --list "${WORK}/brujula-${STAMP}.dump" > /dev/null   # verificación estructural del archivo
t1=$(date +%s)

# 2. Manifiesto de medios generado desde la BD (formato sha256sum -c, rutas relativas a MEDIA_DIR).
#    La BD guarda las rutas SIN el área física (apps/medios/services.py, TKT-017, DEC-AUTO-110): el
#    original saneado está siempre en privado/ y los derivados en publico/ si el medio está DISPONIBLE
#    y en privado/ en otro caso. Sin el prefijo, sha256sum -c no encontraba ningún archivo real
#    (hallazgo del simulacro de TKT-OPS-008, DEC-AUTO-1205).
if psql --no-psqlrc -XAtq -c "SELECT to_regclass('app.medio') IS NOT NULL AND to_regclass('app.medio_derivado') IS NOT NULL" | grep -qx t; then
  psql --no-psqlrc -XAtq -F '  ' -c "
    SELECT sha256_saneado, 'privado/' || archivo_saneado_ruta FROM app.medio
    UNION ALL
    SELECT d.sha256, CASE WHEN m.estado = 'DISPONIBLE' THEN 'publico/' ELSE 'privado/' END || d.ruta
      FROM app.medio_derivado d JOIN app.medio m ON m.id = d.medio_id
    ORDER BY 2" > "${WORK}/medios-${STAMP}.sha256"
else
  log WARN "tablas de medios inexistentes (esquema aún sin migrar): manifiesto vacío"
  : > "${WORK}/medios-${STAMP}.sha256"
fi

# 3. Medios (inmutables una vez escritos -> la copia posterior al dump es un superconjunto).
#    En streaming (RSK-OPS-029): tar -> tee (sha256 del tar en claro) -> age, sin copia en claro.
#    pipefail detecta los fallos de tar/tee/age; el de sha256sum (FIFO, en segundo plano en ESTE
#    shell para poder esperarlo), el "wait" y la validación del hash.
TAR="medios-${STAMP}.tar"
mkfifo "${WORK}/tar.fifo"
sha256sum < "${WORK}/tar.fifo" > "${WORK}/tar.sha256" &
pid_sha=$!
tar --create --file=- --directory="${MEDIA_DIR}" . \
  | tee "${WORK}/tar.fifo" \
  | age --encrypt --recipient "${BACKUP_AGE_RECIPIENT}" --output "${DEST}.tmp/${TAR}.age"
wait "${pid_sha}"
pid_sha=""
rm -f "${WORK}/tar.fifo"
read -r sha_tar _ < "${WORK}/tar.sha256"
[[ "${sha_tar}" =~ ^[0-9a-f]{64}$ ]] || { log ERROR "sha256 del tar de medios no válido"; exit 1; }
rm -f "${WORK}/tar.sha256"
# Libro de anonimizaciones (solo ids, sin PII; ADR-DB-004 §4, DEC-AUTO-094)
if [[ -f "${OPS_DIR}/libro_anonimizaciones.log" ]]; then
  cp "${OPS_DIR}/libro_anonimizaciones.log" "${WORK}/libro_anonimizaciones-${STAMP}.log"
fi
t2=$(date +%s)

# 4. Sumas en claro (incluida la del tar, calculada en el paso 3) -> cifrado -> sumas del cifrado
( cd "${WORK}" && { sha256sum -- *; printf '%s  %s\n' "${sha_tar}" "${TAR}"; } | sort -k2 > "${WORK}/.sumas" )
mv "${WORK}/.sumas" "${WORK}/SHA256SUMS-${STAMP}.txt"
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
