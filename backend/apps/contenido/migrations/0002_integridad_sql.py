# Migración n=7 del plan (DB_HANDOFF v1.1): integridad que Django no modela (ADR-DB-002).
# - FK compuestas (contenido_id, tipo_contenido) -> contenido(id, tipo) de subtipos y relaciones
#   polimórficas, con la acción ON DELETE del DB_HANDOFF (CASCADE);
# - FK compuesta DEFERRABLE de tipo_principal (tipo_principal pertenece a los tipos del destino);
# - trigger trg_contenido_guardas (STATE-001, RULE-008, AC-101, AC-033, §39.2).
# El índice único parcial de la descripción SEO normalizada (RULE-027) está declarado en el
# modelo (UniqueConstraint por expresión, 0001_inicial) para que Django lo conozca.
# Patrón expand, reversible. Las pruebas de introspección verifican que todo existe (RSK-DB-003).
from django.db import migrations

# (tabla, columna id, columna tipo, nombre de la constraint)
FK_COMPUESTAS = [
    ("tipo_aventura", "contenido_id", "tipo_contenido", "fk_tipo_aventura_contenido_tipo"),
    ("destino", "contenido_id", "tipo_contenido", "fk_destino_contenido_tipo"),
    ("itinerario", "contenido_id", "tipo_contenido", "fk_itinerario_contenido_tipo"),
    ("guia", "contenido_id", "tipo_contenido", "fk_guia_contenido_tipo"),
    ("coleccion", "contenido_id", "tipo_contenido", "fk_coleccion_contenido_tipo"),
    ("termino_glosario", "contenido_id", "tipo_contenido", "fk_termino_glosario_contenido_tipo"),
    (
        "pagina_institucional",
        "contenido_id",
        "tipo_contenido",
        "fk_pagina_institucional_contenido_tipo",
    ),
    ("elemento_coleccion", "contenido_id", "tipo_contenido", "fk_elemento_coleccion_contenido_tipo"),
    ("contenido_termino", "contenido_id", "tipo_contenido", "fk_contenido_termino_contenido_tipo"),
    ("contenido_medio", "contenido_id", "tipo_contenido", "fk_contenido_medio_contenido_tipo"),
    ("relacion_contenido", "origen_id", "origen_tipo", "fk_relacion_contenido_origen_tipo"),
    (
        "relacion_contenido",
        "relacionado_id",
        "relacionado_tipo",
        "fk_relacion_contenido_relacionado_tipo",
    ),
]


def _fk(tabla, columna_id, columna_tipo, nombre):
    return migrations.RunSQL(
        f"ALTER TABLE app.{tabla} ADD CONSTRAINT {nombre} "
        f"FOREIGN KEY ({columna_id}, {columna_tipo}) REFERENCES app.contenido (id, tipo) "
        f"ON DELETE CASCADE;",
        reverse_sql=f"ALTER TABLE app.{tabla} DROP CONSTRAINT {nombre};",
    )


FK_TIPO_PRINCIPAL = """
ALTER TABLE app.destino ADD CONSTRAINT fk_destino_tipo_principal_en_tipos
  FOREIGN KEY (contenido_id, tipo_principal_id)
  REFERENCES app.destino_tipo_aventura (destino_id, tipo_aventura_id)
  DEFERRABLE INITIALLY DEFERRED;
"""

TRG_CONTENIDO_GUARDAS = """
CREATE FUNCTION app.fn_contenido_guardas() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, app
AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF OLD.primera_publicacion_en IS NOT NULL THEN
      RAISE EXCEPTION 'No se puede borrar un contenido que se publicó alguna vez (id %)', OLD.id
        USING ERRCODE = 'restrict_violation', CONSTRAINT = 'trg_contenido_guardas';
    END IF;
    IF OLD.tipo = 'PAGINA' THEN
      RAISE EXCEPTION 'Las páginas institucionales no se borran (id %)', OLD.id
        USING ERRCODE = 'restrict_violation', CONSTRAINT = 'trg_contenido_guardas';
    END IF;
    RETURN OLD;
  END IF;

  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.tipo IS DISTINCT FROM OLD.tipo THEN
    RAISE EXCEPTION 'El id y el tipo de un contenido son inmutables (id %)', OLD.id
      USING ERRCODE = 'check_violation', CONSTRAINT = 'trg_contenido_guardas';
  END IF;
  IF OLD.primera_publicacion_en IS NOT NULL THEN
    IF NEW.slug IS DISTINCT FROM OLD.slug THEN
      RAISE EXCEPTION 'El slug de un contenido publicado alguna vez es inmutable (id %)', OLD.id
        USING ERRCODE = 'check_violation', CONSTRAINT = 'trg_contenido_guardas';
    END IF;
    IF NEW.primera_publicacion_en IS DISTINCT FROM OLD.primera_publicacion_en THEN
      RAISE EXCEPTION 'primera_publicacion_en no cambia una vez fijada (id %)', OLD.id
        USING ERRCODE = 'check_violation', CONSTRAINT = 'trg_contenido_guardas';
    END IF;
  END IF;
  RETURN NEW;
END
$$;
CREATE TRIGGER trg_contenido_guardas
  BEFORE UPDATE OR DELETE ON app.contenido
  FOR EACH ROW EXECUTE FUNCTION app.fn_contenido_guardas();
"""

REVERSO_TRG_CONTENIDO_GUARDAS = """
DROP TRIGGER trg_contenido_guardas ON app.contenido;
DROP FUNCTION app.fn_contenido_guardas();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("contenido", "0001_inicial"),
    ]

    operations = [
        *[_fk(*fk) for fk in FK_COMPUESTAS],
        migrations.RunSQL(
            FK_TIPO_PRINCIPAL,
            reverse_sql=(
                "ALTER TABLE app.destino DROP CONSTRAINT fk_destino_tipo_principal_en_tipos;"
            ),
        ),
        migrations.RunSQL(TRG_CONTENIDO_GUARDAS, reverse_sql=REVERSO_TRG_CONTENIDO_GUARDAS),
    ]
