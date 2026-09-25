# ADR-DB-005 — Sin broker ni caché externa desde la capa de datos: sesiones, tareas programadas y limitación de tasa en PostgreSQL

| Campo | Valor |
|---|---|
| Estado | PROPOSED |
| Fecha | 2026-09-25 |
| Ticket | TKT-F4-002 |
| Revisión | 1.1: CHG-DB-001 / TKT-F4-004 (idempotencia, §5 de Decisión); CONFLICT-001 resuelto (DEC-AUTO-122) |
| Trazabilidad | ADR-API-002 §5, DEC-AUTO-107, DEC-AUTO-123..128; Skill_Base_datos §4.E y §7.5; Skill_Backend §12.3/§12.4 (Celery y broker con ADR); BLUEPRINT §38 (Procesos del Sistema), STATE-004, THREAT-001, 002, 009, 025; REQ-050, 057; DEC-AUTO-049; DEC-AUTO-089, 090 |

## Contexto
- [OBSERVADO] El Blueprint pide estos procesos del sistema: procesamiento de medios, purga de auditoría (>365 d), anonimización de cuentas (≤30 d), purga de registros técnicos (≤30 d) y liveness/readiness (§38). También una sesión del panel con invalidación en el servidor de todas las sesiones de una cuenta (THREAT-002, THREAT-025) y limitación de tasa por origen en login, búsqueda y listados (THREAT-001, THREAT-009).
- [OBSERVADO] Carga: menos de 100 escrituras/día en el panel, ≤10 cuentas, subidas de hasta 10 imágenes de ≤10 MB por operación (DEC-AUTO-044). Tráfico público de 20 req/s en la prueba de carga.
- [HECHO] El Orquestador indica: Celery o un broker solo si el Blueprint lo requiere, con ADR y DEC-AUTO.
- [INFERIDO] Ningún proceso del Blueprint exige mensajería asíncrona con garantía de entrega. Los procesos periódicos son diarios u horarios e idempotentes, y el procesamiento de medios afecta a un panel de ≤10 usuarios.

## Alternativas
| Alternativa | Pros | Contras |
|---|---|---|
| Celery + Redis (broker, caché y sesiones) | Estándar de Skill_Backend; procesamiento asíncrono de medios | Segundo motor (§4.E), otro SPOF, otro healthcheck (REQ-050), PII (IP) en Redis, más superficie de ataque |
| Celery con broker en PostgreSQL (kombu SQLAlchemy) | Un solo motor | Transporte experimental en kombu; sondeo continuo |
| **Sin broker: comandos de gestión programados + `pg_try_advisory_lock`; sesiones en tabla propia; limitación de tasa en una tabla UNLOGGED de PostgreSQL** | Un solo motor; cero dependencias nuevas; idempotente; auditable (`ops_ejecucion_tarea`) | El procesamiento de medios es síncrono (latencia del panel en subidas grandes) |

## Decisión
1. **Desde la capa de datos no se requiere broker** (no se activa la excepción §7.5). `DEC-AUTO-090`.
   - Tareas periódicas: comandos `manage.py` idempotentes (`purgar_auditoria`, `anonimizar_cuentas`, `purgar_sesiones`, `purgar_ops`, `reindexar_busqueda`, `reaplicar_anonimizaciones`, `verificar_busqueda`), que lanza un planificador del contenedor (DevOps F6, p. ej. `supercronic` en un servicio `scheduler` de Compose). Cada comando adquiere `pg_try_advisory_lock(hashtext('<tarea>'))`: si no lo obtiene, sale sin error. Registra el inicio y el fin en `ops_ejecucion_tarea` (sin PII) y usa transacciones cortas por lote.
   - Procesamiento de medios: síncrono dentro de la petición de subida. [SUPUESTO] 10 imágenes × (decodificación + re-codificación + derivados) cabe en el timeout del panel; Backend y DevOps fijan el timeout. **Si Skill_Backend decide Celery** por su estándar (§12.4), le corresponde el ADR-API y el DEC-AUTO del broker. Para la base de datos solo cambiaría el estado intermedio del medio (se añadiría PROCESANDO con una migración expand).
2. **Sesiones del panel en PostgreSQL** (`app.sesion_panel`, backend de sesión de Django personalizado sobre `AbstractBaseSession`), con `cuenta_id` indexado para invalidar todas las sesiones de una cuenta (`DELETE ... WHERE cuenta_id = $1`) al desactivar, restablecer o anonimizar, y `autenticado_en` para la expiración absoluta de 12 h. La inactividad de 30 min se aplica con `expire_date` (SESSION_SAVE_EVERY_REQUEST). Con ≤10 cuentas el coste de escritura es despreciable. `DEC-AUTO-089`.
3. **Limitación de tasa** (si Backend usa el throttling de DRF): caché de Django `DatabaseCache` sobre la tabla **UNLOGGED** `app.cache_limites`, creada con `RunSQL` en lugar de `createcachetable`. Condiciones obligatorias: la clave de origen es un **HMAC-SHA256 de la IP truncada** (nunca la IP en claro: REQ-057, THREAT-020); TTL ≤1 h; se excluye de las copias (`--no-unlogged-table-data`) y del rol `readonly`. Tras una caída del servidor la tabla se vacía (aceptable para contadores). [SUPUESTO] Con ≤20 req/s, las escrituras de contadores (~1-2 ms) caben en el presupuesto de p95; QA lo verifica en AC-051. Si no caben, Backend puede limitar la tasa en el proxy inverso (DevOps) y la tabla desaparece.
4. **Readiness** (`/health/ready`): `SELECT 1` con `app_rw` y timeout de 1 s. No hay broker que comprobar.
5. **Claves de idempotencia (CHG-DB-001, TKT-F4-004; DEC-AUTO-123..128)**. El contrato admite `Idempotency-Key` (UUID, opcional) en 11 POST del panel con una ventana de 24 h (ADR-API-002 §5). `cache_limites` no sirve (UNLOGGED, TTL 1 h), así que se añade la tabla **persistente** `app.idempotencia_peticion`:
   - Columnas: `cuenta_id` (FK, ON DELETE CASCADE), `clave uuid`, `operacion` (CHECK con las 11 operationId), `huella_peticion` (sha256 de la operación, los parámetros de ruta y el cuerpo canónico), `codigo_http` (2xx), `recurso_id`, `cuerpo_respuesta jsonb` (≤64 KB), `cuerpo_omitido`, `creado_en` y `expira_en` (= creado_en + 24 h como máximo). `UNIQUE(cuenta_id, clave)`: la misma clave usada en otra operación o con otra huella → 422 `idempotencia_conflicto` (DEC-AUTO-126).
   - **Protocolo en la misma transacción que el efecto** (DEC-AUTO-124): borrar la fila vencida de esa clave → `INSERT ... ON CONFLICT (cuenta_id, clave) DO NOTHING` → si ya existía, comparar operación y huella y reproducir la respuesta, o devolver 422 → si es nueva, ejecutar el efecto y hacer `UPDATE` de la respuesta antes del commit. Un constraint trigger diferido (`trg_idempotencia_completa`) impide confirmar una fila sin respuesta. Un error hace ROLLBACK y no deja fila, así que solo quedan guardadas respuestas 2xx confirmadas. Los duplicados concurrentes se serializan en el índice único; si vence `lock_timeout` (3 s), la respuesta es 409 reintentable.
   - **Secretos** (DEC-AUTO-125): en `panelCrearCuenta` la contraseña temporal nunca se persiste (AC-106). Un CHECK obliga a `cuerpo_respuesta IS NULL AND cuerpo_omitido`. La respuesta de repetición de esa operación requiere un CHG a Backend-contrato (RSK-DB-011).
   - **Retención** (DEC-AUTO-127): 24 h lógicas. Las filas se borran físicamente en el comando diario existente `purgar_ops` y también al anonimizar la cuenta.
   - **Privilegios y clasificación** (DEC-AUTO-128): `app_rw` tiene SELECT, INSERT, UPDATE y DELETE; `readonly` no tiene acceso. `cuerpo_respuesta` se clasifica como PII. La tabla se incluye en las copias: tras una restauración, las claves son coherentes con los efectos restaurados.
   - Migración: dentro de `ops.0001_inicial` (reversible); si ya estuviera aplicada, en `ops.0002_idempotencia`.

## Trade-offs y riesgos
- Las subidas grandes bloquean un worker durante segundos. Mitigación: límite de 10 archivos (DEC-AUTO-044) y workers dimensionados por DevOps.
- Hay que vigilar el bloat de `cache_limites` (tabla UNLOGGED con escrituras frecuentes): autovacuum por defecto, con volumen de filas acotado por el TTL.
- ~~Si Backend impone Celery de todos modos, aparece una contradicción de estándares.~~ **Resuelto**: el Orquestador cerró CONFLICT-001 con DEC-AUTO-122 (sin Celery ni broker). RSK-DB-007 queda CERRADO.
- Idempotencia: los duplicados concurrentes esperan en el índice único hasta `lock_timeout` (RSK-DB-012), y la repetición de `panelCrearCuenta` no puede reproducir el secreto (RSK-DB-011).

## Condiciones de invalidez
- Aparecen efectos externos con garantía de entrega (correo, webhooks): hoy están fuera de alcance (§31).
- El procesamiento de medios supera el timeout razonable del panel con cargas reales.
- El tráfico público crece >10x y la limitación de tasa en la base de datos deja de caber en el presupuesto de p95.
