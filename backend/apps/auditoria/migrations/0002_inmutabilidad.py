# Migración n=10 del plan (DB_HANDOFF v1.1): auditoría inmutable (ADR-DB-004 §1, DEC-AUTO-091).
# - trg_auditoria_inmutable (BEFORE UPDATE OR DELETE por fila) y trg_auditoria_inmutable_truncate
#   (BEFORE TRUNCATE por sentencia; dos triggers porque TRUNCATE solo admite FOR EACH STATEMENT);
# - funciones SECURITY DEFINER app.fn_auditoria_purgar() y app.fn_auditoria_seudonimizar(id);
# - REVOKE UPDATE, DELETE, TRUNCATE a app_rw en evento_auditoria y revision_contenido.
# Patrón expand, reversible (el reverso restaura los privilegios por defecto de INFRA-DB-000).
from django.db import migrations

TRG_AUDITORIA_INMUTABLE = """
CREATE FUNCTION app.fn_auditoria_inmutable() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, app
AS $$
BEGIN
  IF TG_OP = 'TRUNCATE' THEN
    RAISE EXCEPTION 'evento_auditoria no admite TRUNCATE'
      USING ERRCODE = 'restrict_violation', CONSTRAINT = 'trg_auditoria_inmutable';
  END IF;

  IF TG_OP = 'DELETE' THEN
    -- Solo la purga de eventos con más de 365 días (REQ-057).
    IF OLD.ocurrido_en < now() - interval '365 days' THEN
      RETURN OLD;
    END IF;
    RAISE EXCEPTION 'Los eventos de auditoría con menos de 365 días no se borran (id %)', OLD.id
      USING ERRCODE = 'restrict_violation', CONSTRAINT = 'trg_auditoria_inmutable';
  END IF;

  -- UPDATE: solo la seudonimización (actor_etiqueta -> 'Cuenta anonimizada #...', ip -> NULL).
  IF (NEW.id, NEW.ocurrido_en, NEW.actor_id, NEW.accion, NEW.resultado, NEW.tipo_entidad,
      NEW.entidad_id, NEW.entidad_titulo, NEW.campos_cambiados)
     IS DISTINCT FROM
     (OLD.id, OLD.ocurrido_en, OLD.actor_id, OLD.accion, OLD.resultado, OLD.tipo_entidad,
      OLD.entidad_id, OLD.entidad_titulo, OLD.campos_cambiados) THEN
    RAISE EXCEPTION 'Los eventos de auditoría son inmutables (id %)', OLD.id
      USING ERRCODE = 'check_violation', CONSTRAINT = 'trg_auditoria_inmutable';
  END IF;
  IF NEW.actor_etiqueta IS DISTINCT FROM OLD.actor_etiqueta
     AND NEW.actor_etiqueta NOT LIKE 'Cuenta anonimizada #%' THEN
    RAISE EXCEPTION 'actor_etiqueta solo puede sustituirse por un seudónimo (id %)', OLD.id
      USING ERRCODE = 'check_violation', CONSTRAINT = 'trg_auditoria_inmutable';
  END IF;
  IF NEW.ip_truncada IS DISTINCT FROM OLD.ip_truncada AND NEW.ip_truncada IS NOT NULL THEN
    RAISE EXCEPTION 'ip_truncada solo puede anularse (id %)', OLD.id
      USING ERRCODE = 'check_violation', CONSTRAINT = 'trg_auditoria_inmutable';
  END IF;
  RETURN NEW;
END
$$;
CREATE TRIGGER trg_auditoria_inmutable
  BEFORE UPDATE OR DELETE ON app.evento_auditoria
  FOR EACH ROW EXECUTE FUNCTION app.fn_auditoria_inmutable();
CREATE TRIGGER trg_auditoria_inmutable_truncate
  BEFORE TRUNCATE ON app.evento_auditoria
  FOR EACH STATEMENT EXECUTE FUNCTION app.fn_auditoria_inmutable();
"""

REVERSO_TRG_AUDITORIA_INMUTABLE = """
DROP TRIGGER trg_auditoria_inmutable_truncate ON app.evento_auditoria;
DROP TRIGGER trg_auditoria_inmutable ON app.evento_auditoria;
DROP FUNCTION app.fn_auditoria_inmutable();
"""

FN_AUDITORIA_PURGAR = """
CREATE FUNCTION app.fn_auditoria_purgar() RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, app
AS $$
DECLARE
  n integer;
BEGIN
  -- El corte está fijado aquí: el llamante no lo decide (ADR-DB-004 §1.3).
  DELETE FROM app.evento_auditoria WHERE ocurrido_en < now() - interval '365 days';
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END
$$;
REVOKE ALL ON FUNCTION app.fn_auditoria_purgar() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.fn_auditoria_purgar() TO app_rw;
"""

FN_AUDITORIA_SEUDONIMIZAR = """
CREATE FUNCTION app.fn_auditoria_seudonimizar(p_cuenta_id bigint) RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, app
AS $$
DECLARE
  n integer;
  seudonimo text := 'Cuenta anonimizada #' || p_cuenta_id;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM app.cuenta_staff
                  WHERE id = p_cuenta_id AND estado = 'ANONIMIZADA') THEN
    RAISE EXCEPTION 'Solo se seudonimizan los eventos de una cuenta ANONIMIZADA (id %)',
      p_cuenta_id USING ERRCODE = 'check_violation';
  END IF;
  UPDATE app.evento_auditoria
     SET actor_etiqueta = seudonimo, ip_truncada = NULL
   WHERE actor_id = p_cuenta_id
     AND (actor_etiqueta IS DISTINCT FROM seudonimo OR ip_truncada IS NOT NULL);
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END
$$;
REVOKE ALL ON FUNCTION app.fn_auditoria_seudonimizar(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.fn_auditoria_seudonimizar(bigint) TO app_rw;
"""

PRIVILEGIOS = """
REVOKE UPDATE, DELETE, TRUNCATE ON app.evento_auditoria, app.revision_contenido FROM app_rw;
"""

REVERSO_PRIVILEGIOS = """
GRANT UPDATE, DELETE ON app.evento_auditoria, app.revision_contenido TO app_rw;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("auditoria", "0001_inicial"),
        ("cuentas", "0001_inicial"),
    ]

    operations = [
        migrations.RunSQL(TRG_AUDITORIA_INMUTABLE, reverse_sql=REVERSO_TRG_AUDITORIA_INMUTABLE),
        migrations.RunSQL(
            FN_AUDITORIA_PURGAR, reverse_sql="DROP FUNCTION app.fn_auditoria_purgar();"
        ),
        migrations.RunSQL(
            FN_AUDITORIA_SEUDONIMIZAR,
            reverse_sql="DROP FUNCTION app.fn_auditoria_seudonimizar(bigint);",
        ),
        migrations.RunSQL(PRIVILEGIOS, reverse_sql=REVERSO_PRIVILEGIOS),
    ]
