-- =============================================================================
-- Alerta de tamaño de app.cache_limites (RSK-QA004-02; TKT-OPS-006, DEC-AUTO-255).
-- DB_HANDOFF (observabilidad): "alertas por tamaño de cache_limites"; ADR-DB-005: vigilar el bloat
-- de esta tabla UNLOGGED con escrituras frecuentes (throttling, TTL <= 1 h, MAX_ENTRIES solo purga
-- caducadas).
--
-- Solo LECTURA. Sale con código != 0 (ERROR) si se supera algún umbral; 0 si todo está en rango.
-- Umbrales por defecto: > 50 000 filas o > 64 MB (tabla + índices + TOAST). Se cambian con -v.
--
-- Uso manual (stack local; el superusuario solo por socket local dentro del contenedor):
--   docker compose exec -T db psql -U postgres -d brujula -X -q -v ON_ERROR_STOP=1 \
--     [-v max_filas=50000] [-v max_bytes=67108864] -f - < infra/ops/cache_limites_tamano.sql
-- Con un rol sin SELECT sobre la tabla (p. ej. readonly), el número de filas es la ESTIMACIÓN de
-- pg_class.reltuples (-1 = nunca analizada); el tamaño en bytes no necesita privilegios.
-- Programado: ver docs/05_operacion/DEVOPS_HANDOFF.md §19 (comando de gestión del scheduler).
-- =============================================================================
-- OBS-5 (TKT-OPS-006 ciclo 2): el propio script activa ON_ERROR_STOP; la alerta sale con exit != 0
-- aunque se invoque sin -v ON_ERROR_STOP=1.
\set ON_ERROR_STOP on
\if :{?max_filas}
\else
  \set max_filas 50000
\endif
\if :{?max_bytes}
\else
  \set max_bytes 67108864
\endif

SELECT
  has_table_privilege('app.cache_limites', 'SELECT')                        AS exacto,
  pg_total_relation_size('app.cache_limites')                               AS bytes,
  pg_size_pretty(pg_total_relation_size('app.cache_limites'))               AS tamano,
  (SELECT c.reltuples::bigint FROM pg_class c WHERE c.oid = 'app.cache_limites'::regclass)
                                                                            AS filas_estimadas,
  :max_filas::bigint                                                        AS max_filas,
  :max_bytes::bigint                                                        AS max_bytes
\gset

\if :exacto
  SELECT count(*) AS filas, count(*) FILTER (WHERE expires < now()) AS caducadas
    FROM app.cache_limites
  \gset
\else
  \set filas :filas_estimadas
  \set caducadas 'desconocidas (sin SELECT)'
\endif

SELECT (:filas::bigint > :max_filas::bigint OR :bytes::bigint > :max_bytes::bigint) AS alerta \gset

\echo cache_limites: filas=:filas (caducadas=:caducadas) tamano=:tamano (:bytes bytes) umbrales: filas>:max_filas o bytes>:max_bytes
\if :alerta
  \echo ALERTA cache_limites: umbral superado. Revisar autovacuum, TTL y tráfico (runbook DEVOPS_HANDOFF §19).
  DO $$ BEGIN RAISE EXCEPTION 'cache_limites por encima del umbral'; END $$;
\else
  \echo OK cache_limites dentro de los umbrales
\endif
