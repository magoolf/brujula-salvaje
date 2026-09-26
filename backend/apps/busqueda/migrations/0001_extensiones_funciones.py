# Migración n=1 del plan (DB_HANDOFF v1.1 plan_migraciones, "core.0001_extensiones_funciones";
# se aloja en la app busqueda porque apps/core queda fuera de los archivos del ticket TKT-003).
# OBJ-01..06 (DB_HANDOFF objetos_previos, ADR-DB-003 §1). Patrón expand, reversible.
from django.db import migrations

COMPROBAR_COLLATION = """
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_collation WHERE collname = 'es-x-icu') THEN
    RAISE EXCEPTION 'Falta la collation ICU "es-x-icu" (OBJ-06): la imagen debe compilarse con ICU';
  END IF;
END
$$;
"""

F_NORMALIZAR = """
CREATE FUNCTION app.f_normalizar(texto text) RETURNS text
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
SET search_path = pg_catalog, ext
AS $$
  SELECT lower(trim(regexp_replace(ext.unaccent('ext.unaccent'::regdictionary, texto),
                                   '[[:space:]]+', ' ', 'g')))
$$;
COMMENT ON FUNCTION app.f_normalizar(text) IS
  'OBJ-03: minúsculas, sin tildes y espacios colapsados (RULE-026, RULE-027). NULL -> NULL';
"""

F_SIN_DUPLICADOS = """
CREATE FUNCTION app.f_sin_duplicados(a smallint[]) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE
SET search_path = pg_catalog
AS $$
  SELECT cardinality(a) = cardinality(ARRAY(SELECT DISTINCT unnest(a)))
$$;
COMMENT ON FUNCTION app.f_sin_duplicados(smallint[]) IS
  'OBJ-04: true si el array no repite elementos (RULE-011)';
"""

F_TSQUERY_PREFIJO = """
CREATE FUNCTION app.f_tsquery_prefijo(q text) RETURNS tsquery
LANGUAGE plpgsql STABLE PARALLEL SAFE
SET search_path = pg_catalog, ext
AS $$
DECLARE
  tokens text[];
  n integer;
BEGIN
  -- Solo tokens alfanuméricos de la consulta normalizada: no se inyecta sintaxis tsquery
  -- (THREAT-008). Máximo 10 tokens; prefijo (:*) en el último.
  SELECT array_agg(r.m[1] ORDER BY r.pos) INTO tokens
    FROM (SELECT m, pos
            FROM regexp_matches(app.f_normalizar(q), '[a-z0-9]+', 'g') WITH ORDINALITY AS x(m, pos)
           ORDER BY pos
           LIMIT 10) AS r;
  n := coalesce(cardinality(tokens), 0);
  IF n = 0 THEN
    RETURN NULL;
  END IF;
  RETURN to_tsquery('app.es_unaccent',
                    array_to_string(tokens[1:n - 1] || (tokens[n] || ':*'), ' & '));
END
$$;
COMMENT ON FUNCTION app.f_tsquery_prefijo(text) IS
  'OBJ-05: tsquery por prefijo sin sintaxis del usuario (THREAT-008). NULL si no hay tokens';
"""


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(COMPROBAR_COLLATION, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA ext;",
            reverse_sql="DROP EXTENSION IF EXISTS unaccent;",
        ),
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA ext;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;",
        ),
        migrations.RunSQL(
            """
            CREATE TEXT SEARCH CONFIGURATION app.es_unaccent (COPY = pg_catalog.spanish);
            ALTER TEXT SEARCH CONFIGURATION app.es_unaccent
              ALTER MAPPING FOR hword, hword_part, word WITH ext.unaccent, pg_catalog.spanish_stem;
            """,
            reverse_sql="DROP TEXT SEARCH CONFIGURATION app.es_unaccent;",
        ),
        migrations.RunSQL(F_NORMALIZAR, reverse_sql="DROP FUNCTION app.f_normalizar(text);"),
        migrations.RunSQL(
            F_SIN_DUPLICADOS, reverse_sql="DROP FUNCTION app.f_sin_duplicados(smallint[]);"
        ),
        migrations.RunSQL(
            F_TSQUERY_PREFIJO, reverse_sql="DROP FUNCTION app.f_tsquery_prefijo(text);"
        ),
    ]
