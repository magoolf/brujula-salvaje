#!/usr/bin/env bash
# =============================================================================
# INFRA-DB-000 — Bootstrap de PostgreSQL 18.6 para Brújula Salvaje
# Fuente: docs/04_datos/DB_HANDOFF.yaml v1.1 (plan_migraciones n=0, roles, roles_notas)
#         docs/adr/ADR-DB-001.md §3, §4, §6 (locale builtin C.UTF-8, esquemas app/ext, roles)
# Owner: Skill_devops (F6, TKT-F6-001).
#
# Lo ejecuta el entrypoint oficial de la imagen postgres SOLO sobre un volumen de datos
# vacío (/docker-entrypoint-initdb.d). initdb ya se ha ejecutado con
# POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale-provider=builtin --builtin-locale=C.UTF-8"
# (checksums de datos activos por defecto en la 18).
#
# Idempotente: todas las sentencias comprueban existencia, de modo que puede re-ejecutarse
# a mano contra un clúster ya inicializado (p. ej. para rotar contraseñas locales):
#   docker compose exec db bash /docker-entrypoint-initdb.d/10-bootstrap.sh
#
# Las contraseñas llegan por variables de entorno (valores locales NO reales, .env).
# Contraseñas reales = Puerta Humana (CLAUDE.md §0.5). Nunca se imprimen.
# =============================================================================
set -Eeuo pipefail

: "${DB_NAME:?DB_NAME es obligatoria}"
: "${APP_MIGRATOR_PASSWORD:?APP_MIGRATOR_PASSWORD es obligatoria}"
: "${APP_RW_PASSWORD:?APP_RW_PASSWORD es obligatoria}"
: "${READONLY_PASSWORD:?READONLY_PASSWORD es obligatoria}"
: "${APP_BACKUP_PASSWORD:?APP_BACKUP_PASSWORD es obligatoria}"
DB_BOOTSTRAP_TEST_TEMPLATE="${DB_BOOTSTRAP_TEST_TEMPLATE:-false}"

PSQL=(psql -v ON_ERROR_STOP=1 --no-psqlrc --quiet --username "${POSTGRES_USER:-postgres}")

echo "[INFRA-DB-000] roles y base de datos '${DB_NAME}'"

# --- 1. Parámetros de clúster y roles (a nivel de clúster) --------------------
"${PSQL[@]}" --dbname postgres \
  -v db_name="${DB_NAME}" \
  -v pw_migrator="${APP_MIGRATOR_PASSWORD}" \
  -v pw_rw="${APP_RW_PASSWORD}" \
  -v pw_readonly="${READONLY_PASSWORD}" \
  -v pw_backup="${APP_BACKUP_PASSWORD}" <<'SQL'
-- password_encryption=scram-sha-256 también se fija en el servidor (compose: command -c).
SET password_encryption = 'scram-sha-256';

-- Roles (mínimo privilegio, ADR-DB-001 §6). Ninguno es superusuario.
SELECT format('CREATE ROLE app_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_migrator') \gexec
SELECT format('CREATE ROLE app_rw LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') \gexec
SELECT format('CREATE ROLE readonly LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'readonly') \gexec
SELECT format('CREATE ROLE app_backup LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_backup') \gexec

-- Contraseñas (se re-aplican siempre: permite rotarlas re-ejecutando el script).
ALTER ROLE app_migrator PASSWORD :'pw_migrator';
ALTER ROLE app_rw       PASSWORD :'pw_rw';
ALTER ROLE readonly     PASSWORD :'pw_readonly';
ALTER ROLE app_backup   PASSWORD :'pw_backup';

-- Parámetros por rol (ADR-DB-001 §6, DB_HANDOFF roles[].uso)
ALTER ROLE app_migrator SET search_path = app, ext;
ALTER ROLE app_migrator SET lock_timeout = '5s';
ALTER ROLE app_rw SET search_path = app, ext;
ALTER ROLE app_rw SET statement_timeout = '5s';
ALTER ROLE app_rw SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE app_rw SET lock_timeout = '3s';
ALTER ROLE readonly SET search_path = app, ext;
ALTER ROLE readonly SET statement_timeout = '30s';
ALTER ROLE readonly SET default_transaction_read_only = on;
ALTER ROLE app_backup SET search_path = app, ext;
ALTER ROLE app_backup SET default_transaction_read_only = on;

-- app_backup: solo lectura de todos los datos para pg_dump (ADR-DB-004 §3)
GRANT pg_read_all_data TO app_backup;
-- readonly: estadísticas (pg_stat_statements) para diagnóstico, sin acceso a datos extra
GRANT pg_read_all_stats TO readonly;

-- Base de datos: locale builtin C.UTF-8, plantilla template0 (ADR-DB-001 §3, DEC-AUTO-087).
-- Propietario = superusuario de bootstrap; app_migrator recibe CREATE (extensiones trusted).
SELECT format('CREATE DATABASE %I WITH TEMPLATE template0 ENCODING %L LOCALE_PROVIDER builtin BUILTIN_LOCALE %L',
              :'db_name', 'UTF8', 'C.UTF-8')
 WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db_name') \gexec

SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'db_name') \gexec
SELECT format('GRANT CONNECT, CREATE, TEMPORARY ON DATABASE %I TO app_migrator', :'db_name') \gexec
SELECT format('GRANT CONNECT, TEMPORARY ON DATABASE %I TO app_rw', :'db_name') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO readonly, app_backup', :'db_name') \gexec
SQL

# --- 2. Esquemas, privilegios por defecto y extensiones (por base de datos) ----
setup_database() {
  local target_db="$1"
  echo "[INFRA-DB-000] esquemas y privilegios en '${target_db}'"
  "${PSQL[@]}" --dbname "${target_db}" <<'SQL'
-- public cerrado (DB_HANDOFF roles: PUBLIC)
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Esquemas app (negocio) y ext (extensiones), propiedad de app_migrator (DEC-AUTO-099)
CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION app_migrator;
CREATE SCHEMA IF NOT EXISTS ext AUTHORIZATION app_migrator;
ALTER SCHEMA app OWNER TO app_migrator;
ALTER SCHEMA ext OWNER TO app_migrator;
REVOKE ALL ON SCHEMA app FROM PUBLIC;
REVOKE ALL ON SCHEMA ext FROM PUBLIC;
GRANT USAGE ON SCHEMA app, ext TO app_rw, readonly;

-- Privilegios por defecto sobre los objetos que creará app_migrator (migraciones Django).
-- Las excepciones (evento_auditoria, revision_contenido, django_migrations, sesion_panel,
-- cuenta_codigo_recuperacion, cache_limites, idempotencia_peticion, columnas PII para readonly)
-- las aplican las migraciones RunSQL del Developer (DB_HANDOFF plan_migraciones n=10 y n=12).
ALTER DEFAULT PRIVILEGES FOR ROLE app_migrator IN SCHEMA app
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE app_migrator IN SCHEMA app
  GRANT USAGE, SELECT ON SEQUENCES TO app_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE app_migrator IN SCHEMA app
  GRANT SELECT ON TABLES TO readonly;

-- Observabilidad (DB_HANDOFF operacion.observabilidad; DEC-AUTO-145).
-- pg_stat_statements no es trusted: lo crea el superusuario de bootstrap en ext.
CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA ext;
SQL
}

setup_database "${DB_NAME}"

# --- 3. Modo prueba (solo CI / compose.ci.yaml): plantilla para la BD de test de Django ---
# DB_HANDOFF roles_notas: "Las pruebas de Django en CI usan un contenedor efímero con un rol
# con CREATEDB, nunca estos roles" -> en el contenedor efímero de CI, app_migrator recibe
# CREATEDB y template1 lleva los mismos esquemas/privilegios para que test_<db> los herede.
if [[ "${DB_BOOTSTRAP_TEST_TEMPLATE}" == "true" ]]; then
  echo "[INFRA-DB-000] MODO PRUEBA: CREATEDB para app_migrator y template1 preparado (solo CI/efímero)"
  "${PSQL[@]}" --dbname postgres <<'SQL'
ALTER ROLE app_migrator CREATEDB;
-- Permite a las pruebas de privilegios hacer SET ROLE app_rw / readonly (DB_HANDOFF pruebas_obligatorias).
GRANT app_rw, readonly TO app_migrator;
SQL
  setup_database template1
fi

# --- 4. Verificación mínima (falla el init si algo no cuadra) ------------------
"${PSQL[@]}" --dbname "${DB_NAME}" -v db_name="${DB_NAME}" <<'SQL'
DO $$
DECLARE
  v_provider "char";
  v_locale text;
BEGIN
  SELECT datlocprovider, datlocale INTO v_provider, v_locale
    FROM pg_database WHERE datname = current_database();
  IF v_provider <> 'b' OR v_locale <> 'C.UTF-8' THEN
    RAISE EXCEPTION 'INFRA-DB-000: locale inesperado (provider=%, locale=%)', v_provider, v_locale;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_collation WHERE collname = 'es-x-icu') THEN
    RAISE EXCEPTION 'INFRA-DB-000: falta la collation ICU es-x-icu (OBJ-06)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'unaccent')
     OR NOT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_trgm') THEN
    RAISE EXCEPTION 'INFRA-DB-000: faltan las extensiones unaccent/pg_trgm (OBJ-01)';
  END IF;
  IF current_setting('data_checksums') <> 'on' THEN
    RAISE EXCEPTION 'INFRA-DB-000: data_checksums desactivados';
  END IF;
END $$;
SQL

echo "[INFRA-DB-000] completado"
