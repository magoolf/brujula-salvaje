# ADR-DB-004 — Auditoría inmutable, retención y anonimización, copias de seguridad y restauración

| Campo | Valor |
|---|---|
| Estado | PROPOSED |
| Fecha | 2026-09-25 |
| Ticket | TKT-F4-002; revisado en TKT-F4-004 (CHG-DB-001) y TKT-F4-006 (CHG-DB-002, 2026-09-26) |
| Trazabilidad | REQ-054 (RPO ≤24 h / RTO ≤4 h, AC-054), REQ-055, REQ-057 (AC-058), REQ-070, RULE-015, RULE-017, AC-108, THREAT-012, THREAT-013, THREAT-020, THREAT-025, AC-030, AC-107; BLUEPRINT §39.2, §39.6; DEC-AUTO-027, 034, 052; DEC-AUTO-091..094, 096; DEC-AUTO-190, DEC-AUTO-200..204; OBS-QA003-01, OBS-QA003-05 |

## Contexto
- [OBSERVADO] DATA-025 es de solo inserción: ningún rol puede modificar ni borrar eventos, con dos excepciones. La primera es la purga automática de los eventos con más de 365 días; la segunda, la sustitución de `actor_etiqueta` por un seudónimo al anonimizar una cuenta (§18.4, THREAT-013).
- [OBSERVADO] Las cuentas DESACTIVADAS se anonimizan en un plazo ≤30 días (o con "Anonimizar ahora"). Las copias son diarias con rotación ≤30 días (DEC-AUTO-052). Una restauración debe volver a aplicar las anonimizaciones pendientes antes de reabrir el panel.
- [OBSERVADO] RPO ≤24 h y RTO ≤4 h para contenido **y medios**. AC-054 exige un simulacro con conteos y checksums de medios coincidentes.
- [INFERIDO] Tamaño de la base de datos <1 GB y de los medios ~5 GB a 3 años. Un `pg_dump`/`pg_restore` de <1 GB tarda minutos.

## Decisión
### 1. Auditoría inmutable (defensa en profundidad) — `DEC-AUTO-091`
1. **Privilegios**: `app_rw` solo tiene SELECT e INSERT en `evento_auditoria` (sin UPDATE, DELETE ni TRUNCATE). Lo mismo se aplica a `revision_contenido`.
2. **Trigger `trg_auditoria_inmutable`** (BEFORE UPDATE OR DELETE, FOR EACH ROW, y BEFORE TRUNCATE, FOR EACH STATEMENT). Afecta también al propietario, salvo que un superusuario desactive triggers:
   - UPDATE: solo se permite si únicamente cambian `actor_etiqueta` (hacia un valor con el prefijo `Cuenta anonimizada #`) e `ip_truncada` (hacia NULL). Cualquier otro cambio → EXCEPTION.
   - DELETE: solo se permite si `OLD.ocurrido_en < now() - interval '365 days'`.
   - TRUNCATE: siempre EXCEPTION.
3. **Funciones SECURITY DEFINER** (propietario `app_migrator`, `SET search_path = pg_catalog, app, pg_temp` desde CHG-DB-002 —en la v1.1 era `pg_catalog, app`—, EXECUTE solo para `app_rw`). `pg_temp` se lista explícitamente y al final porque, si no aparece, PostgreSQL lo busca **el primero** para relaciones, y un llamante con privilegio TEMP podría suplantar una tabla no cualificada ([OBSERVADO] documentación de PostgreSQL, *CREATE FUNCTION — Writing SECURITY DEFINER Functions Safely*). Se aplica con `ALTER FUNCTION ... SET search_path` en la migración nueva `auditoria.0003_endurecimiento`, que conserva propietario, SECURITY DEFINER y GRANT. `DEC-AUTO-201`.
   - `app.fn_auditoria_purgar() RETURNS integer`: borra los eventos con `ocurrido_en < now() - interval '365 days'` (el corte está fijado en el cuerpo de la función; el llamante no lo decide).
   - `app.fn_auditoria_seudonimizar(p_cuenta_id bigint) RETURNS integer`: pone `actor_etiqueta = 'Cuenta anonimizada #' || p_cuenta_id` e `ip_truncada = NULL` en los eventos de esa cuenta, **solo si** la cuenta está en estado ANONIMIZADA (se comprueba dentro de la función).
4. `ip_truncada` es de tipo `cidr`, con `CHECK ((family(ip_truncada)=4 AND masklen(ip_truncada)=24) OR (family(ip_truncada)=6 AND masklen(ip_truncada)=48))`. El tipo `cidr` rechaza los bits de host distintos de cero, así que la base de datos **no puede** almacenar una IP completa. Solo se admite en las acciones de autenticación (CHECK). `DEC-AUTO-092`.
5. En un LOGIN_FALLIDO con un usuario inexistente: `actor_id` NULL y `actor_etiqueta = 'desconocido'`. **Nunca** se guarda el texto tecleado, que podría ser una contraseña o PII de un tercero.

### 2. Retención y tareas programadas
| Dato | Regla | Mecanismo (comando idempotente + `pg_try_advisory_lock`) | Frecuencia |
|---|---|---|---|
| Auditoría | 365 días | `purgar_auditoria` → `app.fn_auditoria_purgar()` | Diaria |
| Cuentas DESACTIVADAS | Anonimizar si `desactivado_en < now() - 30 days` | `anonimizar_cuentas`: en una transacción por cuenta, `usuario`, `nombre_visible`, `secreto_mfa` y `ultimo_acceso_en` pasan a NULL; `password` pasa a un valor inutilizable (`!` + aleatorio); se borran los códigos de recuperación, las sesiones y las filas de `idempotencia_peticion` de la cuenta; `estado=ANONIMIZADA`, `anonimizado_en=now()`; luego `fn_auditoria_seudonimizar` y el evento CUENTA_ANONIMIZAR | Diaria |
| Sesiones | Hasta expirar (≤12 h) | `purgar_sesiones`: DELETE de `sesion_panel` con `expire_date < now()` | Cada hora |
| Registro de tareas (`ops_ejecucion_tarea`) | ≤30 días | `purgar_ops` | Diaria |
| Claves de idempotencia (`idempotencia_peticion`, CHG-DB-001) | 24 h lógicas (`expira_en`) | `purgar_ops`: DELETE con `expira_en <= now()`; las filas vencidas se ignoran y se reemplazan en línea (ADR-DB-005 §5) | Diaria |
| Caché de limitación (`cache_limites`, si existe) | TTL ≤1 h | Expiración de Django + tabla UNLOGGED | Continua |
| Borradores nunca publicados | Hasta su borrado | DELETE desde el panel (FEAT-038); la base de datos impide el borrado si el contenido se publicó alguna vez | Bajo demanda |

- Se conservan `autorizacion_otorgada_en` y `autorizacion_version_politica` tras la anonimización, como prueba de la autorización (REQ-070). Al desaparecer usuario y nombre dejan de identificar a la persona. Se anula `ultimo_acceso_en` (minimización). `DEC-AUTO-096`.
- Los registros técnicos (logs de la aplicación y del motor) no están en la base de datos. Su rotación ≤30 días es de DevOps (FEAT-048).

### 3. Copias de seguridad — `DEC-AUTO-093`
- **Base de datos**: `pg_dump --format=custom --no-unlogged-table-data` diario con el rol `app_backup`. Nombre `brujula-AAAAMMDD.dump`, más el sha256 del fichero.
- **Medios**: copia diaria del volumen de medios (originales saneados y derivados) + un **manifiesto** `medios-AAAAMMDD.sha256` generado desde la base de datos (`medio.sha256_saneado` y `medio_derivado.sha256`). Orden: primero el dump y después los medios. Como los medios son inmutables una vez escritos (un cambio implica un archivo nuevo con una ruta nueva), la copia de medios posterior al dump es un superconjunto consistente.
- **Retención**: 30 copias diarias rotativas (≤30 días, DEC-AUTO-052). Las copias contienen PII del staff: se cifran en reposo (p. ej. `age`/`gpg` con una clave fuera del repositorio; clave real = Puerta Humana §0.5) y se guardan en un volumen distinto del de datos.
- **Sin archivado de WAL ni PITR**: con RPO = 24 h basta la copia diaria (alternativa descartada por su complejidad; se revalúa si el RPO baja de 24 h).

### 4. Restauración (RTO ≤4 h) y re-aplicación de anonimizaciones — `DEC-AUTO-094`
1. Levantar PostgreSQL 18.6 limpio con los roles (script de infraestructura de DevOps).
2. `pg_restore --exit-on-error --no-owner --role=app_migrator -d brujula brujula-AAAAMMDD.dump`.
3. Restaurar el volumen de medios y verificar el manifiesto con `sha256sum -c` (AC-054).
4. **Panel cerrado** (indicador de mantenimiento de la aplicación) hasta completar los pasos 5 a 7.
5. `reaplicar_anonimizaciones`: lee el **libro de anonimizaciones**, un fichero append-only **fuera del ciclo de copias de la base de datos** (volumen de operación) con líneas `cuenta_id;evento;fecha_utc`, donde evento ∈ {DESACTIVADA, ANONIMIZADA}. Solo contiene ids, sin PII. Vuelve a desactivar y anonimizar las cuentas que en la copia restaurada estaban en un estado anterior. Después ejecuta `anonimizar_cuentas` (plazo de 30 días) y `purgar_auditoria`.
6. `purgar_sesiones` (se invalidan todas las sesiones) y `reindexar_busqueda`.
7. Verificación: conteos por tipo y estado frente a la copia, invariante de búsqueda y `/health/ready`.
- **Prueba de restauración**: el simulacro de AC-054 en F8 (evidencia: registro con tiempos y resultados de la verificación del manifiesto) y después **mensual**. Un backup no restaurado se considera no válido (Skill_Base_datos §2).

### 5. Prohibición de borrado físico defendida en la base de datos (CHG-DB-002, 2026-09-26)
Contexto: [OBSERVADO en el QA de TKT-003, OBS-QA003-01] `trg_cuenta_admin_minimo` solo vigila UPDATE y `app_rw` tenía DELETE en `cuenta_staff`: un `DELETE` SQL del único administrador sin referencias confirmaba y dejaba 0 administradores, pese a que la regla es "una cuenta nunca se borra; se anonimiza". Decisión del Orquestador: `DEC-AUTO-190`. [OBSERVADO BLUEPRINT §39.2] "Borrado físico solo en: borradores nunca publicados, medios RECHAZADOS (nunca se persisten), eventos de auditoría con más de 365 días, registros técnicos con más de 30 días y sesiones expiradas. Todo lo demás se retira o se anonimiza."

| Tabla | Privilegio de `app_rw` | Trigger (aplica también al propietario) | Migración | DEC |
|---|---|---|---|---|
| `cuenta_staff` | sin DELETE ni TRUNCATE | `trg_cuenta_sin_borrado` BEFORE DELETE por fila: rechaza siempre | `cuentas.0002_sin_borrado` | 200 |
| `revision_contenido` | sin UPDATE, DELETE ni TRUNCATE (ya en v1.1) | `trg_revision_inmutable` BEFORE UPDATE OR DELETE por fila: rechaza siempre | `auditoria.0003_endurecimiento` | 202 |
| `medio` | sin DELETE ni TRUNCATE | `trg_medio_sin_borrado` BEFORE DELETE por fila: rechaza siempre | `medios.0002_sin_borrado` | 203 |
| 7 subtipos de `contenido` | conserva DELETE (borradores) | `trg_subtipo_guarda_borrado` BEFORE DELETE por fila: rechaza si el contenido padre existe y se publicó alguna vez o es PAGINA | `contenido.0003_guardas_subtipos` | 203 |
| `region`, `pais`, `categoria_guia`, `licencia`, `nivel_escala`, `config_inicio`, `config_sitio` | sin DELETE ni TRUNCATE | ninguno (el reverso de las migraciones de semilla borra con `app_migrator`) | `catalogos.0003_sin_borrado`, `inicio.0002_sin_borrado` | 204 |

Reglas comunes:
- Errores con `ERRCODE 'restrict_violation'` (23001; `check_violation` en el UPDATE de revisiones) y `CONSTRAINT = '<nombre del trigger>'`, que Django convierte en `IntegrityError`. Funciones de trigger `SECURITY INVOKER` con `SET search_path = pg_catalog, app, pg_temp`.
- **Sin triggers de TRUNCATE nuevos.** En `cuenta_staff`, TRUNCATE exige incluir `evento_auditoria` (FK `actor_id`), cuyo trigger de TRUNCATE ya lo rechaza siempre. En el resto, `app_rw` no tiene TRUNCATE y el propietario ya puede hacer DROP. Así el backend de pruebas `apps/ops/bd_pruebas` (vaciado con TRUNCATE, que no dispara triggers de fila) no cambia.
- `trg_cuenta_admin_minimo` no se amplía a DELETE: con el borrado prohibido, el único camino a 0 administradores operativos es el UPDATE de rol o estado, que ya vigila.
- **Flujos que no cambian**: `anonimizar_cuentas`, "Anonimizar ahora" y `reaplicar_anonimizaciones` hacen UPDATE de la cuenta y DELETE solo de sus hijos (`cuenta_codigo_recuperacion`, `sesion_panel`, `idempotencia_peticion`). El borrado de borradores nunca publicados (FEAT-038) es de contenido: el Collector de Django borra el subtipo antes que el supertipo (el padre sigue en BORRADOR, así que se permite), y en la cascada SQL el padre ya no es visible (se permite). `pg_restore` solo inserta.
- **Reversibilidad**: las seis migraciones son EXPAND y su `reverse_sql` elimina triggers y funciones y devuelve los privilegios de la v1.1. `migrate <app> zero` sigue funcionando porque DROP TABLE no dispara triggers de DELETE. Cualquier migración futura que necesite borrar filas de estas tablas es destructiva y requiere Puerta Humana (CLAUDE.md §0.5). `ALTER TABLE ... DISABLE TRIGGER` queda prohibido en migraciones de avance y en el código.

## Trade-offs y riesgos
- CHG-DB-002: el propietario `app_migrator` puede sortear los triggers con DDL, igual que en `evento_auditoria` (RSK-DB-014, aceptado: solo lo usa el job de migración). Las pruebas que borren cuentas o medios por ORM deben reescribirse.
- El libro de anonimizaciones es un segundo artefacto que proteger. No contiene PII (solo ids), pero su pérdida impediría re-aplicar un "Anonimizar ahora" posterior a la copia. Mitigación: se almacena en el volumen de operación y se incluye en la copia de ese volumen, que es independiente de la rotación del dump.
- `pg_dump` lógico de una instancia única: en el peor caso se pierden 24 h de edición (aceptado en DEC-AUTO-027).
- El trigger de inmutabilidad no protege frente a un superusuario, que no se usa en la aplicación (§7.4).

## Condiciones de invalidez
- RPO < 24 h → archivado de WAL (pgBackRest o WAL-G) + PITR.
- La normativa exige conservar la auditoría más de 365 días o conservar la copia más de 30 días (conflicto con REQ-057: revisión con el Arquitecto Funcional).
- Los medios dejan de ser inmutables (edición in-place): la copia de medios tendría que hacerse con snapshot.
- (§5) Aparece un requisito legal o de producto de **supresión física** de una cuenta o de un medio (p. ej., un derecho de supresión que la anonimización no satisfaga, o la retirada de un medio por infracción de derechos que exija borrar la fila): se sustituiría el trigger por una función SECURITY DEFINER de borrado controlado y auditado, con su propia Puerta Humana.
- (§5) El diseño de subida de medios pasa a asíncrono y necesita borrar filas: revisar `DEC-AUTO-203`.
