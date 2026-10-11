#!/usr/bin/env bash
# =============================================================================
# Restauración LOCAL de una copia (simulacro AC-054; ADR-DB-004 §4) — TKT-F6-001, TKT-OPS-007, TKT-OPS-008
# SOLO para entornos locales/efímeros. Restaurar sobre datos reales es Puerta Humana
# (CLAUDE.md §0.5): el script exige --confirmar-entorno-local y RESTORE_ENV=local.
#
# Uso (dentro del contenedor backup, con la clave PRIVADA age disponible solo durante el simulacro;
# runbook completo en docs/05_operacion/DEVOPS_HANDOFF.md §35.6):
#   restore-local.sh --confirmar-entorno-local <AAAAMMDD> <ruta_clave_privada_age>
# Destino de los medios: exactamente UNA de estas variables
#   RESTORE_STAGING_DIR  (recomendado; TKT-OPS-008) directorio VACÍO en disco (p. ej. /backups/.restauracion)
#                        donde se dejan, verificados por sha256, medios.tar, medios.sha256 (manifiesto),
#                        el libro de anonimizaciones de la copia y COPIA (fecha). Los reinstala en los
#                        volúmenes, con su propietario 10001, el servicio one-shot "reinstalar-volumenes"
#                        (perfil "restauracion", scripts/ops/reinstalar-volumenes.sh, RSK-OPS-027).
#   MEDIA_RESTORE_DIR    (solo verificación, TKT-OPS-007) directorio VACÍO donde se extraen los medios
#                        para comprobar el manifiesto con sha256sum -c. No los devuelve al volumen.
#
# Pasos que ejecuta:
#   1. verificación sha256 de los cifrados -> descifrado -> verificación sha256 en claro
#   2. comprobación de la BD destino: INFRA-DB-000 aplicado (esquemas app/ext de app_migrator,
#      pg_stat_statements en ext) y esquema app VACÍO: 0 relaciones, 0 funciones y 0 tipos, dominios,
#      colaciones, operadores, familias de operadores, configuraciones/diccionarios de búsqueda de texto
#      y conversiones (OBS-QAOPS007-03, DEC-AUTO-1204). Nunca restaura encima de datos
#   3. lista TOC (pg_restore -l) SIN los objetos que ya crea INFRA-DB-000 (DEC-AUTO-240):
#        SCHEMA app, SCHEMA ext, EXTENSION pg_stat_statements, COMMENT ON EXTENSION
#        pg_stat_statements y ACL de SCHEMA public
#      y pg_restore -L --exit-on-error -> psql ON_ERROR_STOP en UNA transacción (todo o nada) como
#      app_migrator, retirando antes sus privilegios por defecto (los recrea el dump; DEC-AUTO-242)
#   4. medios: tar descifrado EN STREAMING (sha256 en claro comprobado contra SHA256SUMS) hacia el
#      staging o extraído en MEDIA_RESTORE_DIR + sha256sum -c del manifiesto
#   5. libro de anonimizaciones de la copia (verificado) al staging, si la copia lo incluye
# Memoria acotada (RSK-OPS-029, DEC-AUTO-1201): el directorio de trabajo (dump en claro) está en DISCO,
# dentro del volumen de copias (RESTORE_WORK_PARENT, por defecto BACKUP_DIR), nunca en /tmp (tmpfs =
# memoria del cgroup de 512 MiB); el tar de medios no pasa por el directorio de trabajo.
# Los pasos de la aplicación (reaplicar_anonimizaciones ... /health/ready) los ejecuta
# scripts/ops/post-restore-local.sh desde el host (este contenedor no tiene Django).
# Códigos de salida: 0 OK; 2 salvaguarda/uso; 3 directorio de medios/staging no vacío;
#   4 BD destino no limpia o sin INFRA-DB-000; 5 TOC inesperada; otro != 0: fallo del paso.
# =============================================================================
set -Eeuo pipefail
umask 077

[[ "${1:-}" == "--confirmar-entorno-local" ]] || { echo "Falta --confirmar-entorno-local (Puerta Humana §0.5 para datos reales)" >&2; exit 2; }
[[ "${RESTORE_ENV:-}" == "local" ]] || { echo "RESTORE_ENV debe ser 'local'" >&2; exit 2; }
STAMP="${2:?AAAAMMDD}"
KEY="${3:?ruta a la clave privada age}"
[[ "${STAMP}" =~ ^[0-9]{8}$ ]] || { echo "AAAAMMDD inválido: ${STAMP}" >&2; exit 2; }
[[ -r "${KEY}" ]] || { echo "clave privada age no legible: ${KEY}" >&2; exit 2; }
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RESTORE_WORK_PARENT="${RESTORE_WORK_PARENT:-${BACKUP_DIR}}"
RESTORE_STAGING_DIR="${RESTORE_STAGING_DIR:-}"
MEDIA_RESTORE_DIR="${MEDIA_RESTORE_DIR:-}"
if [[ -n "${LIBRO_RESTORE_DIR:-}" ]]; then
  # TKT-OPS-008: el libro copiado por el uid 999 quedaba 0600 y la aplicación (10001) no podía leerlo
  # (LIBRO_ILEGIBLE). Ahora lo instala reinstalar-volumenes.sh --libro-copia con propietario 10001.
  echo "LIBRO_RESTORE_DIR ya no se admite: usar RESTORE_STAGING_DIR + reinstalar-volumenes.sh --libro-copia" >&2
  exit 2
fi
if [[ -n "${RESTORE_STAGING_DIR}" && -n "${MEDIA_RESTORE_DIR}" ]] || [[ -z "${RESTORE_STAGING_DIR}${MEDIA_RESTORE_DIR}" ]]; then
  echo "Definir exactamente UNA de RESTORE_STAGING_DIR (reinstalación) o MEDIA_RESTORE_DIR (solo verificación)" >&2
  exit 2
fi
DESTINO_MEDIOS="${RESTORE_STAGING_DIR:-${MEDIA_RESTORE_DIR}}"
# Ruta absoluta obligatoria: una relativa acabaría bajo WORKDIR (/tmp = tmpfs). Ocurre p. ej. si Git Bash
# reescribe "-e VAR=/ruta" a "C:/Program Files/Git/ruta" (usar MSYS_NO_PATHCONV=1 en Windows).
[[ "${DESTINO_MEDIOS}" == /* && "${RESTORE_WORK_PARENT}" == /* ]] || { echo "RESTORE_STAGING_DIR/MEDIA_RESTORE_DIR y RESTORE_WORK_PARENT deben ser rutas absolutas: '${DESTINO_MEDIOS}', '${RESTORE_WORK_PARENT}'" >&2; exit 2; }
: "${PGHOST:?}" "${PGDATABASE:?}"
: "${RESTORE_PGUSER:=app_migrator}" "${RESTORE_PGPASSWORD:?contraseña de app_migrator (local)}"

SRC="${BACKUP_DIR}/diarias/${STAMP}"
[[ -d "${SRC}" ]] || { echo "no existe la copia ${SRC}" >&2; exit 2; }
mkdir -p "${DESTINO_MEDIOS}"
if [[ -n "$(ls -A "${DESTINO_MEDIOS}" 2>/dev/null)" ]]; then
  echo "${DESTINO_MEDIOS} no está vacío: se aborta para no mezclar medios ni restauraciones" >&2; exit 3
fi
find "${RESTORE_WORK_PARENT}" -mindepth 1 -maxdepth 1 -type d -name '.trabajo-restaurar.*' -exec rm -rf -- {} +
WORK="$(mktemp -d "${RESTORE_WORK_PARENT}/.trabajo-restaurar.XXXXXX")"
pid_sha=""
fin() {
  [[ -z "${pid_sha}" ]] || kill "${pid_sha}" 2>/dev/null || true
  rm -rf "${WORK}"
}
trap fin EXIT
ts() { date -u +%FT%TZ; }
# psql/pg_restore siempre con el rol de restauración (nunca el superusuario)
as_restore() { PGUSER="${RESTORE_PGUSER}" PGPASSWORD="${RESTORE_PGPASSWORD}" "$@"; }
t0=$(date +%s)
TAR="medios-${STAMP}.tar"
SUMAS="${WORK}/SHA256SUMS-${STAMP}.txt"

echo "$(ts) [1/5] verificación y descifrado de ${SRC}"
( cd "${SRC}" && sha256sum -c --quiet --strict "SHA256SUMS-cifrado-${STAMP}.txt" )
echo "  cifrados: sha256 OK ($(grep -c . "${SRC}/SHA256SUMS-cifrado-${STAMP}.txt") archivos)"
for f in "${SRC}"/*.age; do
  [[ "$(basename "$f")" == "${TAR}.age" ]] && continue      # el tar se descifra en streaming (paso 4)
  age --decrypt --identity "${KEY}" --output "${WORK}/$(basename "${f%.age}")" "$f"
done
# Sumas en claro: todo salvo el tar, que se comprueba en el paso 4 sin escribirlo en claro aquí
sha_tar="$(awk -v t="${TAR}" '$2 == t || $2 == "*" t {print $1}' "${SUMAS}")"
[[ "${sha_tar}" =~ ^[0-9a-f]{64}$ ]] || { echo "SHA256SUMS sin la línea del tar de medios" >&2; exit 1; }
awk -v t="${TAR}" '!($2 == t || $2 == "*" t)' "${SUMAS}" > "${WORK}/.sumas-sin-tar"
( cd "${WORK}" && sha256sum -c --quiet --strict .sumas-sin-tar )
echo "  en claro: sha256 OK ($(grep -c . "${WORK}/.sumas-sin-tar") archivos; tar en el paso 4)"
DUMP="${WORK}/brujula-${STAMP}.dump"
t1=$(date +%s)

echo "$(ts) [2/5] comprobación de la BD destino (INFRA-DB-000 aplicado y esquema app vacío)"
estado_bd="$(as_restore psql --no-psqlrc -XAtq -v ON_ERROR_STOP=1 -c "
  WITH app AS (SELECT oid FROM pg_namespace WHERE nspname = 'app')
  SELECT concat_ws(' ',
    (SELECT count(*) FROM pg_namespace WHERE nspname IN ('app','ext') AND pg_get_userbyid(nspowner) = 'app_migrator'),
    (SELECT count(*) FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace
      WHERE e.extname = 'pg_stat_statements' AND n.nspname = 'ext'),
    (SELECT count(*) FROM pg_class WHERE relnamespace IN (SELECT oid FROM app)),
    (SELECT count(*) FROM pg_proc WHERE pronamespace IN (SELECT oid FROM app)),
    -- OBS-QAOPS007-03: tipos/dominios/enums/rangos (typrelid = 0: los tipos fila de las relaciones ya
    -- cuentan arriba) y el resto de objetos con esquema que una restauración volvería a crear
    (SELECT count(*) FROM pg_type WHERE typnamespace IN (SELECT oid FROM app) AND typrelid = 0)
    + (SELECT count(*) FROM pg_collation WHERE collnamespace IN (SELECT oid FROM app))
    + (SELECT count(*) FROM pg_operator WHERE oprnamespace IN (SELECT oid FROM app))
    + (SELECT count(*) FROM pg_opfamily WHERE opfnamespace IN (SELECT oid FROM app))
    + (SELECT count(*) FROM pg_ts_config WHERE cfgnamespace IN (SELECT oid FROM app))
    + (SELECT count(*) FROM pg_ts_dict WHERE dictnamespace IN (SELECT oid FROM app))
    + (SELECT count(*) FROM pg_conversion WHERE connamespace IN (SELECT oid FROM app)))")"
read -r n_esquemas n_pgss n_rel n_fn n_otros <<< "${estado_bd}"
if [[ "${n_esquemas}" != 2 || "${n_pgss}" != 1 ]]; then
  echo "La BD destino no tiene el estado de INFRA-DB-000 (esquemas app/ext de app_migrator=${n_esquemas}/2, pg_stat_statements en ext=${n_pgss}/1)" >&2
  exit 4
fi
if [[ "${n_rel}" != 0 || "${n_fn}" != 0 || "${n_otros}" != 0 ]]; then
  echo "La BD destino NO está limpia (esquema app: ${n_rel} relaciones, ${n_fn} funciones, ${n_otros} tipos/dominios/otros objetos). Solo se restaura sobre una BD recién creada por INFRA-DB-000" >&2
  exit 4
fi

echo "$(ts) [3/5] lista TOC sin los objetos de INFRA-DB-000 + pg_restore -L (una transacción)"
pg_restore --list "${DUMP}" > "${WORK}/toc-completa.lst"
# Entradas que INFRA-DB-000 ya crea y que app_migrator no puede (o no debe) volver a crear
# (DEC-AUTO-240). Formato de línea TOC: "<id>; <tableoid> <oid> <tipo> <esquema> <nombre> <propietario>".
# Cada patrón debe coincidir con UNA entrada como máximo; la ausencia se avisa (copias antiguas).
excluir=(
  'SCHEMA - app( |$)'
  'SCHEMA - ext( |$)'
  'EXTENSION - pg_stat_statements( |$)'
  'COMMENT - EXTENSION pg_stat_statements( |$)'
  'ACL - SCHEMA public( |$)'
)
cp "${WORK}/toc-completa.lst" "${WORK}/toc-restaurar.lst"
for p in "${excluir[@]}"; do
  re="^[0-9]+; [0-9]+ [0-9]+ ${p}"
  n="$(grep -Ec "${re}" "${WORK}/toc-restaurar.lst" || true)"
  case "${n}" in
    0) echo "AVISO: la copia no contiene '${p%%(*}' (nada que excluir)" ;;
    1) echo "  excluida: $(grep -E "${re}" "${WORK}/toc-restaurar.lst")"
       grep -Ev "${re}" "${WORK}/toc-restaurar.lst" > "${WORK}/toc.tmp"
       mv "${WORK}/toc.tmp" "${WORK}/toc-restaurar.lst" ;;
    *) echo "TOC inesperada: ${n} entradas para '${p%%(*}'" >&2; exit 5 ;;
  esac
done
n_total="$(grep -Evc '^;' "${WORK}/toc-completa.lst")"
n_rest="$(grep -Evc '^;' "${WORK}/toc-restaurar.lst")"
echo "  entradas TOC: ${n_total} en la copia, ${n_rest} a restaurar, $((n_total - n_rest)) excluidas"
# Privilegios por defecto (DEC-AUTO-242): INFRA-DB-000 ya crea los ALTER DEFAULT PRIVILEGES de
# app_migrator, así que cada CREATE TABLE del restore concedería arwd a app_rw y SELECT a readonly.
# pg_dump solo emite GRANT relativos al ACL de fábrica (nunca REVOKE), de modo que los REVOKE de las
# migraciones (evento_auditoria, revision_contenido, cuenta_staff, sesion_panel...) se perderían en
# silencio. Por eso, en la MISMA transacción: se retiran los privilegios por defecto del rol de
# restauración, se restaura, y las entradas "DEFAULT ACL" del propio dump los vuelven a crear al final.
# Todo o nada: BEGIN explícito y COMMIT solo si pg_restore generó el script completo (si falla, la
# sesión termina sin COMMIT y el servidor deshace todo); psql con ON_ERROR_STOP (= --exit-on-error).
preludio_sql() {
  cat <<'SQL'
\set ON_ERROR_STOP on
BEGIN;
DO $preludio$
DECLARE
  r record;
BEGIN
  FOR r IN
    SELECT DISTINCT n.nspname AS esquema,
           CASE d.defaclobjtype WHEN 'r' THEN 'TABLES' WHEN 'S' THEN 'SEQUENCES' WHEN 'f' THEN 'FUNCTIONS'
                                WHEN 'T' THEN 'TYPES' WHEN 'n' THEN 'SCHEMAS' WHEN 'L' THEN 'LARGE OBJECTS' END AS objetos,
           CASE a.grantee WHEN 0 THEN 'PUBLIC' ELSE quote_ident(pg_get_userbyid(a.grantee)) END AS receptor
      FROM pg_default_acl d
      JOIN pg_namespace n ON n.oid = d.defaclnamespace
      CROSS JOIN LATERAL aclexplode(d.defaclacl) a
     WHERE d.defaclrole = current_user::regrole AND a.grantee <> d.defaclrole
  LOOP
    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I REVOKE ALL ON %s FROM %s',
                   current_user, r.esquema, r.objetos, r.receptor);
  END LOOP;
END
$preludio$;
SQL
}
if ! {
  preludio_sql
  as_restore pg_restore --exit-on-error --no-owner --role="${RESTORE_PGUSER}" \
    --use-list="${WORK}/toc-restaurar.lst" --file=- "${DUMP}" || exit 1
  echo 'COMMIT;'
} | as_restore psql --no-psqlrc -X --quiet --dbname="${PGDATABASE}" > /dev/null; then
  echo "pg_restore FALLÓ: transacción deshecha, la BD sigue como la dejó INFRA-DB-000" >&2
  exit 1
fi
n_defacl_toc="$(grep -Ec '^[0-9]+; [0-9]+ [0-9]+ DEFAULT ACL ' "${WORK}/toc-restaurar.lst" || true)"
n_defacl_bd="$(as_restore psql --no-psqlrc -XAtq -c "SELECT count(*) FROM pg_default_acl WHERE defaclrole = current_user::regrole")"
if [[ "${n_defacl_toc}" != "${n_defacl_bd}" ]]; then
  echo "privilegios por defecto: ${n_defacl_bd} en la BD y ${n_defacl_toc} en la copia" >&2; exit 1
fi
echo "  restaurado en una transacción; privilegios por defecto: ${n_defacl_bd} (= copia)"
rm -f "${DUMP}"     # el dump en claro no se conserva más de lo necesario
t2=$(date +%s)

echo "$(ts) [4/5] medios (AC-054): tar descifrado en streaming + sha256 contra SHA256SUMS"
MANIFIESTO="${WORK}/medios-${STAMP}.sha256"
# El sha256 del tar en claro se calcula en paralelo (FIFO + sha256sum en segundo plano en ESTE shell)
mkfifo "${WORK}/tar.fifo"
sha256sum < "${WORK}/tar.fifo" > "${WORK}/tar.sha256" &
pid_sha=$!
if [[ -n "${RESTORE_STAGING_DIR}" ]]; then
  age --decrypt --identity "${KEY}" "${SRC}/${TAR}.age" | tee "${WORK}/tar.fifo" > "${RESTORE_STAGING_DIR}/medios.tar"
else
  age --decrypt --identity "${KEY}" "${SRC}/${TAR}.age" | tee "${WORK}/tar.fifo" \
    | tar --extract --file=- --directory="${MEDIA_RESTORE_DIR}"
fi
wait "${pid_sha}"
pid_sha=""
read -r sha_real _ < "${WORK}/tar.sha256"
if [[ "${sha_real}" != "${sha_tar}" ]]; then
  echo "sha256 del tar de medios en claro NO coincide con SHA256SUMS (${sha_real} != ${sha_tar})" >&2
  [[ -z "${RESTORE_STAGING_DIR}" ]] || rm -f "${RESTORE_STAGING_DIR}/medios.tar"
  exit 1
fi
echo "  tar de medios: sha256 OK (${sha_tar})"
if [[ -n "${RESTORE_STAGING_DIR}" ]]; then
  cp "${MANIFIESTO}" "${RESTORE_STAGING_DIR}/medios.sha256"
  printf '%s  medios.tar\n' "${sha_tar}" > "${RESTORE_STAGING_DIR}/medios.tar.sha256"
  echo "  staging: medios.tar + manifiesto ($(grep -c . "${MANIFIESTO}" || true) entradas) en ${RESTORE_STAGING_DIR}; verificación del manifiesto en el volumen: reinstalar-volumenes.sh"
elif [[ -s "${MANIFIESTO}" ]]; then
  # --quiet solo imprime los fallos; cualquier archivo ausente o alterado -> exit != 0 (set -e)
  ( cd "${MEDIA_RESTORE_DIR}" && sha256sum -c --quiet --strict "${MANIFIESTO}" )
  echo "  manifiesto: $(wc -l < "${MANIFIESTO}") archivos verificados (sha256sum -c)"
else
  # backup.sh deja el manifiesto vacío si no hay filas de medios: sha256sum -c lo trataría como error
  echo "  manifiesto vacío (la BD no tenía medios al copiar): nada que verificar"
fi
t3=$(date +%s)

echo "$(ts) [5/5] libro de anonimizaciones"
LIBRO="${WORK}/libro_anonimizaciones-${STAMP}.log"
if [[ ! -f "${LIBRO}" ]]; then
  echo "  la copia no incluye libro (no existía al copiar): reaplicar_anonimizaciones usará el volumen ops_libro"
elif [[ -n "${RESTORE_STAGING_DIR}" ]]; then
  cp "${LIBRO}" "${RESTORE_STAGING_DIR}/libro_anonimizaciones.log"
  echo "  copia del libro verificada en el staging. Por defecto se usa el libro VIVO del volumen ops_libro"
  echo "  (más reciente). Si se perdió: reinstalar-volumenes.sh --libro-copia (decisión humana, ADR-DB-004 §4.4)"
else
  echo "  copia del libro verificada; se usa el libro VIVO del volumen ops_libro (más reciente)"
fi
[[ -z "${RESTORE_STAGING_DIR}" ]] || printf '%s\n' "${STAMP}" > "${RESTORE_STAGING_DIR}/COPIA"

echo "$(ts) tiempos: descifrado=$((t1 - t0))s pg_restore=$((t2 - t1))s medios=$((t3 - t2))s total=$((t3 - t0))s"
cat <<'EOF'
Siguientes pasos (ADR-DB-004 §4; runbook DEVOPS_HANDOFF §35.6), con la aplicación todavía parada:
  1. medios/libro a los volúmenes (si se perdieron) o verificación del volumen superviviente:
     docker compose --profile restauracion run --rm reinstalar-volumenes --confirmar-entorno-local --medios|--verificar-medios [--libro-copia]
  2. RESTORE_ENV=local bash scripts/ops/post-restore-local.sh --confirmar-entorno-local
     (migrate -> reaplicar_anonimizaciones -> anonimizar_cuentas -> purgar_auditoria -> purgar_sesiones
      -> reindexar_busqueda -> verificar_busqueda -> arranque -> /health/ready)
Registrar los tiempos de cada paso como evidencia del simulacro (AC-054).
EOF
