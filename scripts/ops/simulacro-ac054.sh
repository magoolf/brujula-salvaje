#!/usr/bin/env bash
# =============================================================================
# Simulacro AC-054 de extremo a extremo (REQ-054; ADR-DB-004 §4) — TKT-OPS-008, DEC-AUTO-1202
# Copia -> PÉRDIDA TOTAL (BD, medios y libro) -> restauración sobre BD limpia -> reinstalación de
# medios y libro -> pasos de aplicación -> aplicación arriba y verificada. Lo usan el job
# "simulacro AC-054" (.github/workflows/simulacro-ac054.yaml) y el runbook local (DEVOPS_HANDOFF §35.6).
#
# DESTRUCTIVO para el proyecto de compose indicado: borra sus volúmenes db_data, media y ops_libro.
# Solo para proyectos locales/efímeros. Nunca sobre datos reales (Puerta Humana §0.5). Por eso exige:
#   - RESTORE_ENV=local
#   - COMPOSE_PROJECT_NAME explícito, distinto de "brujula" (el proyecto por defecto del desarrollador)
#   - --confirmar-destruccion <proyecto>, que debe coincidir con COMPOSE_PROJECT_NAME
# Requisitos: imágenes ya construidas (docker compose --profile ops build) y .env (scripts/ops/init-env.sh;
#   COMPOSE_ENV_FILES si no es ./.env). Bash, docker compose v2 y curl en el host.
# Uso (desde la raíz del repo):
#   COMPOSE_PROJECT_NAME=brujulaops008 RESTORE_ENV=local \
#     bash scripts/ops/simulacro-ac054.sh --confirmar-destruccion brujulaops008 [--evidencia <dir>]
# La clave age es EFÍMERA: se genera aquí, la privada solo viaja por stdin al contenedor de restauración
# (tmpfs) y se borra al terminar. No es un secreto real.
# Controles negativos incluidos: restauración sobre una BD con un DOMINIO en app -> exit 4
# (OBS-QAOPS007-03); post-restore sin libro -> exit 1 LIBRO_AUSENTE y la aplicación NO arranca (CHG-DB-003).
# shellcheck disable=SC2016  # los bash -c '...' se expanden dentro del contenedor ($1 = AAAAMMDD)
# Exit 0 = simulacro superado; cualquier otro valor = fallo (el motivo queda en la salida y en la evidencia).
# =============================================================================
set -Eeuo pipefail

[[ "${RESTORE_ENV:-}" == "local" ]] || { echo "RESTORE_ENV debe ser 'local'" >&2; exit 2; }
P="${COMPOSE_PROJECT_NAME:-}"
[[ -n "${P}" && "${P}" != brujula ]] || { echo "COMPOSE_PROJECT_NAME explícito y distinto de 'brujula' (el simulacro borra sus volúmenes)" >&2; exit 2; }
EVID=""
while (( $# )); do
  case "$1" in
    --confirmar-destruccion) [[ "${2:-}" == "${P}" ]] || { echo "--confirmar-destruccion debe valer '${P}'" >&2; exit 2; }; confirmado=1; shift 2 ;;
    --evidencia) EVID="${2:?directorio}"; shift 2 ;;
    *) echo "opción desconocida: $1" >&2; exit 2 ;;
  esac
done
[[ "${confirmado:-0}" == 1 ]] || { echo "Falta --confirmar-destruccion ${P}" >&2; exit 2; }
cd "$(dirname "$0")/../.."
ENVF="${COMPOSE_ENV_FILES:-.env}"
[[ -f "${ENVF}" ]] || { echo "no existe ${ENVF} (bash scripts/ops/init-env.sh)" >&2; exit 2; }
valor_env() { grep -E "^$1=" "${ENVF}" | tail -n 1 | cut -d= -f2- | tr -d '\r'; }
DB_NAME="$(valor_env DB_NAME)"; DB_NAME="${DB_NAME:-brujula}"
PUERTO="${PROXY_HOST_PORT:-$(valor_env PROXY_HOST_PORT)}"; PUERTO="${PUERTO:-8080}"
RESTORE_PGPASSWORD="$(valor_env APP_MIGRATOR_PASSWORD)"
[[ -n "${RESTORE_PGPASSWORD}" ]] || { echo "APP_MIGRATOR_PASSWORD vacío en ${ENVF}" >&2; exit 2; }
export RESTORE_PGPASSWORD RESTORE_ENV

EVID="${EVID:-$(mktemp -d)}"
mkdir -p "${EVID}"
CLAVES="$(mktemp -d)"
trap 'rm -rf "${CLAVES}"' EXIT
# En Windows, el shell POSIX de Git reescribe los argumentos con forma de ruta ("-e X=/backups/...") a
# rutas de Windows antes de llamar a docker. Se desactiva SOLO para docker (curl la necesita para
# /dev/null). Sin efecto en Linux.
DC=(env MSYS_NO_PATHCONV=1 docker compose)
B="http://127.0.0.1:${PUERTO}"
ts() { date -u +%FT%TZ; }
paso() { echo; echo "=== $(ts) $*"; }
falla() { echo "SIMULACRO FALLIDO: $*" >&2; exit 1; }
psql_su() { "${DC[@]}" exec -T db psql -U postgres -d "${DB_NAME}" -XAtq -v ON_ERROR_STOP=1 "$@"; }
en_marcha() { "${DC[@]}" --profile ops ps --status running --services 2>/dev/null | grep -Ex 'backend|frontend|proxy|scheduler' || true; }

# Instantánea de la BD como superusuario (solo lectura, para comparar): conteo + md5 del contenido de cada
# tabla persistente de app (las UNLOGGED no entran en la copia), privilegios (relaciones, columnas,
# esquemas, por defecto, funciones, extensiones, BD), triggers y secuencias.
instantanea_bd() {
  psql_su <<'SQL'
\pset tuples_only on
SELECT format('SELECT %L || '' filas='' || count(*) || '' md5='' || md5(coalesce(string_agg(t::text, E''\n'' ORDER BY t::text), '''')) FROM app.%I t', c.relname, c.relname)
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'app' AND c.relkind IN ('r', 'p') AND c.relpersistence = 'p' ORDER BY c.relname
\gexec
SELECT 'rel ' || c.relname || ' ' || c.relkind::text || ' ' || pg_get_userbyid(c.relowner) || ' ' || coalesce(c.relacl::text, '-')
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'app' ORDER BY 1;
SELECT 'col ' || c.relname || '.' || a.attname || ' ' || a.attacl::text
  FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'app' AND a.attacl IS NOT NULL ORDER BY 1;
SELECT 'nsp ' || nspname || ' ' || pg_get_userbyid(nspowner) || ' ' || coalesce(nspacl::text, '-')
  FROM pg_namespace WHERE nspname IN ('app', 'ext', 'public') ORDER BY 1;
SELECT 'defacl ' || pg_get_userbyid(defaclrole) || ' ' || coalesce(n.nspname, '-') || ' ' || defaclobjtype::text || ' ' || defaclacl::text
  FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid = d.defaclnamespace ORDER BY 1;
SELECT 'fn ' || p.oid::regprocedure::text || ' ' || pg_get_userbyid(p.proowner) || ' ' || coalesce(p.proacl::text, '-')
       || ' secdef=' || p.prosecdef || ' ' || coalesce(array_to_string(p.proconfig, ','), '-')
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'app' ORDER BY 1;
SELECT 'ext ' || e.extname || ' ' || n.nspname || ' ' || pg_get_userbyid(e.extowner)
  FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace ORDER BY 1;
SELECT 'db ' || datname || ' ' || coalesce(datacl::text, '-') FROM pg_database WHERE datname = current_database();
SELECT 'trg ' || c.relname || '.' || t.tgname || ' ' || t.tgenabled::text
  FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'app' AND NOT t.tgisinternal ORDER BY 1;
SELECT 'seq ' || sequencename || ' ' || coalesce(last_value::text, 'null') FROM pg_sequences WHERE schemaname = 'app' ORDER BY 1;
SQL
}
# Volúmenes de medios y libro (lectura con el contenedor backup: grupo 10001, solo lectura):
# propietario, modo y tipo de cada entrada + sha256 de cada archivo + sha256 del libro.
instantanea_volumenes() {
  # shellcheck disable=SC2016  # el script se expande DENTRO del contenedor
  "${DC[@]}" --profile ops run --rm --no-deps -T --entrypoint bash backup -c '
    set -euo pipefail
    cd /srv/media
    find . -printf "ent %U:%G %m %y %p\n" | LC_ALL=C sort
    find . -type f -print0 | LC_ALL=C sort -z | xargs -0 -r sha256sum | sed "s/^/sha /"
    if [ -f /srv/ops/libro_anonimizaciones.log ]; then
      echo "libro $(stat -c "%u:%g %a" /srv/ops/libro_anonimizaciones.log) $(sha256sum < /srv/ops/libro_anonimizaciones.log)"
    else
      echo "libro AUSENTE"
    fi' | tr -d '\r' | grep -E '^(ent|sha|libro) '     # fuera la salida del build implícito de "run"
}

T_SIM=$(date +%s)
paso "[0] preparación del proyecto ${P}: clave age efímera, stack arriba, semilla real y libro"
"${DC[@]}" --profile ops run --rm --no-deps -T --entrypoint age-keygen backup 2>/dev/null | tr -d '\r' > "${CLAVES}/age.key"
BACKUP_AGE_RECIPIENT="$(grep -oE 'age1[0-9a-z]+' "${CLAVES}/age.key" | head -n 1)"
if [[ -z "${BACKUP_AGE_RECIPIENT}" ]] || ! grep -q '^AGE-SECRET-KEY-' "${CLAVES}/age.key"; then falla "no se pudo generar la clave age efímera"; fi
export BACKUP_AGE_RECIPIENT
"${DC[@]}" up -d --wait --no-build
"${DC[@]}" --profile ops run --rm --no-deps -T scheduler python manage.py cargar_semilla | tail -n 3
# Línea del libro v2 para una cuenta que no existe: la relectura la lee y la informa (inexistentes=1)
"${DC[@]}" --profile ops run --rm --no-deps -T scheduler python -c '
import os
fd = os.open("/var/lib/brujula/ops/libro_anonimizaciones.log", os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o640)
os.write(fd, b"900000001;DESACTIVADA;2026-01-01T00:00:00Z\n"); os.fsync(fd); os.close(fd)'

paso "[1] copia (backup.sh, rol app_backup) e instantánea de referencia"
# La aplicación se para antes de copiar SOLO para que la instantánea de comparación sea determinista
# (nada escribe entre la copia y la instantánea). pg_dump es consistente también en caliente.
"${DC[@]}" stop proxy frontend backend
"${DC[@]}" --profile ops run --rm --no-deps -T -e BACKUP_AGE_RECIPIENT backup backup.sh | tr -d '\r' | tee "${EVID}/backup.log"
STAMP="$(grep -oE 'fin copia [0-9]{8}' "${EVID}/backup.log" | grep -oE '[0-9]{8}' | tail -n 1)"
[[ -n "${STAMP}" ]] || falla "backup.sh no terminó"
instantanea_bd | tr -d '\r' > "${EVID}/bd-antes.txt"
instantanea_volumenes > "${EVID}/volumenes-antes.txt"
echo "copia ${STAMP}; instantánea: $(grep -c ' filas=' "${EVID}/bd-antes.txt") tablas, $(grep -c '^sha ' "${EVID}/volumenes-antes.txt") archivos de medios"
if ! grep -q '^sha .*publico/' "${EVID}/volumenes-antes.txt" || ! grep -q '^sha .*privado/' "${EVID}/volumenes-antes.txt"; then
  falla "la semilla no dejó medios públicos y privados (simulacro no representativo)"
fi

paso "[2] DESASTRE: pérdida total de la BD, los medios y el libro (se conserva solo el volumen de copias)"
T0=$(date +%s)
"${DC[@]}" --profile ops down
docker volume rm "${P}_db_data" "${P}_media" "${P}_ops_libro"
"${DC[@]}" run --rm init-volumes
"${DC[@]}" up -d --wait --no-build db
t_bd=$(( $(date +%s) - T0 ))

paso "[3a] control negativo (OBS-QAOPS007-03): un DOMINIO en app -> restore-local.sh exit 4"
psql_su -c "CREATE DOMAIN app.dominio_simulacro AS integer"
rc=0
"${DC[@]}" --profile ops run --rm --no-deps -T -e RESTORE_ENV -e RESTORE_PGPASSWORD -e RESTORE_STAGING_DIR=/backups/.restauracion \
  backup bash -c 'cat > /tmp/age.key; restore-local.sh --confirmar-entorno-local "$1" /tmp/age.key' _ "${STAMP}" < "${CLAVES}/age.key" || rc=$?
[[ "${rc}" == 4 ]] || falla "con un dominio en app, restore-local.sh debía terminar con exit 4 (fue ${rc})"
psql_su -c "DROP DOMAIN app.dominio_simulacro"
"${DC[@]}" --profile ops run --rm --no-deps -T --entrypoint rm backup -rf /backups/.restauracion
echo "OK: exit 4 (BD no limpia por un dominio); dominio retirado"
t_neg1=$(( $(date +%s) - T0 - t_bd ))

paso "[3] restore-local.sh: BD en una transacción + medios y libro verificados al staging"
"${DC[@]}" --profile ops run --rm --no-deps -T -e RESTORE_ENV -e RESTORE_PGPASSWORD -e RESTORE_STAGING_DIR=/backups/.restauracion \
  backup bash -c 'cat > /tmp/age.key; restore-local.sh --confirmar-entorno-local "$1" /tmp/age.key' _ "${STAMP}" < "${CLAVES}/age.key" \
  | tr -d '\r' | tee "${EVID}/restore-local.log"
instantanea_bd | tr -d '\r' > "${EVID}/bd-despues.txt"
if ! diff -u "${EVID}/bd-antes.txt" "${EVID}/bd-despues.txt" > "${EVID}/bd-diff.txt"; then
  head -n 40 "${EVID}/bd-diff.txt"; falla "la BD restaurada NO es idéntica a la de la copia (conteos/md5/privilegios/secuencias)"
fi
echo "OK: BD restaurada idéntica ($(wc -l < "${EVID}/bd-antes.txt") líneas: conteos, md5, privilegios, triggers y secuencias)"

paso "[4] reinstalar-volumenes --medios (pérdida total del volumen de medios, RSK-OPS-027)"
"${DC[@]}" --profile restauracion run --rm reinstalar-volumenes --confirmar-entorno-local --medios | tr -d '\r' | tee "${EVID}/reinstalar-medios.log"

paso "[5a] control negativo (CHG-DB-003): post-restore SIN libro -> exit 1 LIBRO_AUSENTE y la aplicación NO arranca"
t=$(date +%s)
rc=0
bash scripts/ops/post-restore-local.sh --confirmar-entorno-local > "${EVID}/post-restore-sin-libro.log" 2>&1 || rc=$?
tr -d '\r' < "${EVID}/post-restore-sin-libro.log" | tail -n 15
[[ "${rc}" == 1 ]] || falla "sin libro, post-restore-local.sh debía terminar con exit 1 (fue ${rc})"
grep -q 'LIBRO_AUSENTE' "${EVID}/post-restore-sin-libro.log" || falla "sin libro, el fallo no fue LIBRO_AUSENTE"
grep -qE '^ +anonimizar_cuentas( |$)|anonimizar_cuentas: EXITO' "${EVID}/post-restore-sin-libro.log" && falla "se ejecutó anonimizar_cuentas tras LIBRO_AUSENTE"
[[ -z "$(en_marcha)" ]] || falla "la aplicación arrancó tras LIBRO_AUSENTE: $(en_marcha)"
echo "OK: exit 1 LIBRO_AUSENTE; anonimizar_cuentas no se ejecutó; nada arrancado"
t_neg2=$(( $(date +%s) - t ))

paso "[5] reinstalar-volumenes --libro-copia (decisión humana simulada: libro perdido junto con la BD)"
"${DC[@]}" --profile restauracion run --rm reinstalar-volumenes --confirmar-entorno-local --libro-copia | tr -d '\r' | tee "${EVID}/reinstalar-libro.log"

paso "[5b] controles de reinstalar-volumenes: nunca mezcla medios ni sobrescribe el libro vivo"
t=$(date +%s)
for c in "--medios:3" "--libro-copia:3" "--verificar-medios:0"; do
  rc=0
  "${DC[@]}" --profile restauracion run --rm reinstalar-volumenes --confirmar-entorno-local "${c%%:*}" > "${EVID}/reinstalar${c%%:*}-2.log" 2>&1 || rc=$?
  [[ "${rc}" == "${c##*:}" ]] || { tail -n 5 "${EVID}/reinstalar${c%%:*}-2.log"; falla "reinstalar-volumenes ${c%%:*} con el volumen ya restaurado: exit ${rc} (esperado ${c##*:})"; }
  echo "OK: ${c%%:*} sobre volúmenes ya restaurados -> exit ${rc}"
done
t_neg2=$(( t_neg2 + $(date +%s) - t ))

paso "[6] post-restore-local.sh: migrate + 6 comandos ADR-DB-004 §4 + arranque (con perfil ops) + /health/ready"
bash scripts/ops/post-restore-local.sh --confirmar-entorno-local 2>&1 | tr -d '\r' | tee "${EVID}/post-restore.log"
codigo="$(curl -s -o /dev/null -w '%{http_code}' "${B}/health/ready")"
T_FIN=$(date +%s)
[[ "${codigo}" == 200 ]] || falla "/health/ready por el proxy respondió ${codigo}"

paso "[7] verificación: volúmenes idénticos, aplicación sirviendo datos y medios restaurados"
instantanea_volumenes > "${EVID}/volumenes-despues.txt"
if ! diff -u "${EVID}/volumenes-antes.txt" "${EVID}/volumenes-despues.txt" > "${EVID}/volumenes-diff.txt"; then
  head -n 40 "${EVID}/volumenes-diff.txt"; falla "medios o libro restaurados NO idénticos (propietario/modo/sha256)"
fi
echo "OK: medios ($(grep -c '^sha ' "${EVID}/volumenes-despues.txt") archivos) y libro idénticos: propietario, modo y sha256"
test "$(curl -s -o /dev/null -w '%{http_code}' "${B}/api/v1/publico/inicio")" = 200 || falla "GET /api/v1/publico/inicio != 200"
test "$(curl -s -o /dev/null -w '%{http_code}' "${B}/")" = 200 || falla "GET / (SSR) != 200"
ruta="$(grep -m1 -oE '^sha [0-9a-f]{64}  \./publico/.+$' "${EVID}/volumenes-despues.txt")"
sha_esperado="$(cut -d' ' -f2 <<< "${ruta}")"; ruta="${ruta#*  ./}"
sha_servido="$(curl -fsS "${B}/media/${ruta}" | sha256sum | cut -d' ' -f1)"
[[ "${sha_servido}" == "${sha_esperado}" ]] || falla "el proxy sirve /media/${ruta} con otro contenido"
echo "OK: /health/ready 200, /api/v1/publico/inicio 200, SSR 200 y /media/${ruta} servido con su sha256"
"${DC[@]}" --profile ops run --rm --no-deps -T --entrypoint rm backup -rf /backups/.restauracion

rto=$(( T_FIN - T0 ))
{
  echo "copia=${STAMP} proyecto=${P}"
  echo "T0 (desastre)=$(date -u -d "@${T0}" +%FT%TZ 2>/dev/null || echo "${T0}")"
  echo "BD recreada (INFRA-DB-000)=${t_bd}s"
  echo "controles negativos=$(( t_neg1 + t_neg2 ))s (dominio ${t_neg1}s; LIBRO_AUSENTE y reinstalar-volumenes ${t_neg2}s)"
  echo "RTO medido (desastre -> /health/ready 200 por el proxy)=${rto}s; sin los controles negativos=$(( rto - t_neg1 - t_neg2 ))s (objetivo <= 4 h)"
  echo "simulacro completo=$(( $(date +%s) - T_SIM ))s"
} | tee "${EVID}/tiempos.txt"
echo "SIMULACRO AC-054 SUPERADO. Evidencia en ${EVID}"
