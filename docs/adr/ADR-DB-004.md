# ADR-DB-004 — Auditoría inmutable, retención y anonimización, copias de seguridad y restauración

| Campo | Valor |
|---|---|
| Estado | PROPOSED |
| Fecha | 2026-09-25 |
| Ticket | TKT-F4-002; revisado en TKT-F4-004 (CHG-DB-001), TKT-F4-006 (CHG-DB-002, 2026-09-26) y TKT-F4-010 (CHG-DB-003, 2026-09-28) |
| Trazabilidad | REQ-054 (RPO ≤24 h / RTO ≤4 h, AC-054), REQ-055, REQ-057 (AC-058), REQ-070, RULE-015, RULE-017, AC-108, THREAT-012, THREAT-013, THREAT-020, THREAT-025, AC-030, AC-107; BLUEPRINT §39.2, §39.6; DEC-AUTO-027, 034, 052; DEC-AUTO-091..094, 096; DEC-AUTO-190, DEC-AUTO-200..204; DEC-AUTO-913, DEC-AUTO-260..264; OBS-QA003-01, OBS-QA003-05, QA-TKT005-03 |

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
| Cuentas DESACTIVADAS | Anonimizar si `desactivado_en < now() - 30 days` (desde CHG-DB-003: plazo contado desde la desactivación **vigente** y exclusión de las cuentas cuyo último evento del libro es REACTIVADA; §4.3) | `anonimizar_cuentas`: en una transacción por cuenta, `usuario`, `nombre_visible`, `secreto_mfa` y `ultimo_acceso_en` pasan a NULL; `password` pasa a un valor inutilizable (`!` + aleatorio); se borran los códigos de recuperación, las sesiones y las filas de `idempotencia_peticion` de la cuenta; `estado=ANONIMIZADA`, `anonimizado_en=now()`; luego `fn_auditoria_seudonimizar` y el evento CUENTA_ANONIMIZAR | Diaria |
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
4. **Panel cerrado** (aplicación parada) hasta completar los pasos 5 a 7.
5. Con el esquema llevado a la versión del código (`migrate` con `app_migrator`), y **en este orden**, deteniéndose en el primer comando que termine con código ≠ 0:
   1. `reaplicar_anonimizaciones` — relectura del libro del **volumen vivo** (§4.1 a §4.4). Es el único paso que puede cambiar estados de cuenta a partir del libro.
   2. `anonimizar_cuentas` — plazo de 30 días contado desde la desactivación vigente (§4.3). Se ejecuta **después** de la relectura porque depende de que `desactivado_en` ya esté alineado con el libro.
   3. `purgar_auditoria`.
6. `purgar_sesiones` (se invalidan todas las sesiones), `reindexar_busqueda` y `verificar_busqueda`.
7. Verificación: conteos por tipo y estado frente a la copia, invariante de búsqueda y `/health/ready`. El resumen de la relectura (cuentas omitidas y su motivo, §4.4) se adjunta a la evidencia del simulacro.
- **Prueba de restauración**: el simulacro de AC-054 en F8 (evidencia: registro con tiempos y resultados de la verificación del manifiesto) y después **mensual**. Un backup no restaurado se considera no válido (Skill_Base_datos §2).

#### 4.1 Libro de anonimizaciones: formato (v2, CHG-DB-003) — `DEC-AUTO-260`
Contexto: [OBSERVADO en el QA de TKT-005, QA-TKT005-03, MEDIUM] con los eventos {DESACTIVADA, ANONIMIZADA} la relectura no sabía que una cuenta se había reactivado: tras restaurar, `reaplicar_anonimizaciones` la volvía a desactivar y `anonimizar_cuentas` podía anonimizarla de forma **irreversible** si habían pasado más de 30 días desde la desactivación original. Afectaba también a las cuentas reactivadas que estaban en PENDIENTE_ACTIVACION, y la desactivación por sistema no comprobaba RULE-015. Decisión del Orquestador: `DEC-AUTO-913`.

- Fichero de texto UTF-8, append-only, en `LIBRO_ANONIMIZACIONES_PATH` (volumen `ops_libro`, distinto del volumen de datos de PostgreSQL). Solo contiene ids de cuenta, sin PII.
- **Línea de evento**: `cuenta_id;evento;fecha_utc\n`, que debe cumplir exactamente `^[1-9][0-9]{0,18};(DESACTIVADA|REACTIVADA|ANONIMIZADA);[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$` y cuya fecha debe ser válida en el calendario.
  - `DESACTIVADA`: la cuenta pasó a DESACTIVADA. `fecha_utc` es el valor de `desactivado_en` grabado en esa misma transacción, truncado a segundos.
  - `REACTIVADA` (**nuevo**): la cuenta salió de DESACTIVADA mediante "Reactivar" (queda en PENDIENTE_ACTIVACION). `fecha_utc` es el instante de la reactivación.
  - `ANONIMIZADA`: la cuenta pasó a ANONIMIZADA ("Anonimizar ahora" o `anonimizar_cuentas`).
- **Líneas de control**: las que empiezan por `#` no son eventos. La única que se define es `#REPARACION;<fecha_utc>`, que escribe el escritor cuando encuentra el fichero terminado sin `\n` (§4.2).
- **Compatibilidad**: el formato de línea no cambia respecto a la v1; los libros existentes (con solo DESACTIVADA y ANONIMIZADA) se leen sin migración.
- **Quién escribe**: toda transición confirmada hacia DESACTIVADA o ANONIMIZADA, o desde DESACTIVADA mediante reactivación, la haga el panel o una tarea (`anonimizar_cuentas` escribe ANONIMIZADA). **Excepción**: `reaplicar_anonimizaciones` **nunca** escribe en el libro, porque solo reproduce eventos que ya están en él.
- **Retención**: indefinida, sin rotación ni compactación (≤10 cuentas: unos pocos KB). Truncarlo podría eliminar un REACTIVADA que protege una cuenta.

#### 4.2 Escritura durable y *fail-closed* — `DEC-AUTO-261`
1. La línea se escribe **dentro de la transacción de la operación, como último paso antes del commit** (no en `on_commit`), y siempre después de `SET CONSTRAINTS app.trg_cuenta_admin_minimo IMMEDIATE`, para que la comprobación diferida de RULE-015 ya se haya ejecutado. Así, los únicos fallos posibles después de escribir son de infraestructura (caída del proceso o de la conexión).
2. Procedimiento: `os.open(ruta, O_WRONLY | O_APPEND | O_CREAT | O_NOFOLLOW | O_CLOEXEC, 0o640)` → `fcntl.flock(LOCK_EX)` → si el fichero no está vacío y su último byte no es `\n`, se escribe primero `\n#REPARACION;<fecha_utc>\n` → **un único** `write()` con la línea completa → `os.fsync()` → se libera el lock. Al crear el fichero se hace además `fsync` del directorio.
3. Si cualquier paso falla (`OSError`), la operación **se deshace** (excepción → rollback: sin cambio de estado ni evento de auditoría) y el cliente recibe un error genérico 503 sin detalle. Se registra en el log estructurado `libro_anonimizaciones_no_escrito` con `cuenta_id` y el tipo de error. Se descarta el comportamiento anterior (escribir en `on_commit` y solo registrar el error), porque un REACTIVADA perdido en silencio lleva, tras una restauración, a una anonimización irreversible.
4. El `FOR UPDATE` sobre la fila de la cuenta, que ya toman los servicios, serializa las operaciones de una misma cuenta. Como la línea se escribe antes del commit y con el lock de fila tomado, **el orden de las líneas de una misma cuenta en el fichero es el orden real de sus transiciones**.
5. Riesgo residual: si la transacción falla después de escribir, la línea queda "espuria" (describe una transición que el actor pidió pero que no se confirmó). Lo acepta RSK-DB-016, porque es preferible a una línea perdida: una línea espuria reproduce la intención del actor, mientras que una línea perdida contradice un hecho confirmado.

#### 4.3 Relectura: "el último evento por cuenta gana" — `DEC-AUTO-260` (concreta `DEC-AUTO-913`)
**Lectura** (común a `reaplicar_anonimizaciones` y `anonimizar_cuentas`): se abre en solo lectura con `O_NOFOLLOW` y `flock(LOCK_SH)`. Se exige que sea un fichero regular y que no sea escribible por "otros" (§4.5). Se recorre en orden y se clasifica cada línea:
- línea de evento válida → se guarda (número de línea, id, evento, fecha);
- línea vacía o que empieza por `#` → se ignora;
- línea mal formada **seguida inmediatamente** de `#REPARACION;…` → escritura interrumpida de una operación que no se confirmó: se ignora con WARNING;
- última línea del fichero sin `\n` → escritura en curso o interrumpida: se ignora con WARNING;
- **cualquier otra línea mal formada** → el libro está **corrupto** (§4.4).

**Orden y vigencia**: el "último evento" de una cuenta es su última línea válida **en el orden del fichero**. La `fecha_utc` **no** se usa para ordenar: solo sirve para calcular plazos. La **desactivación vigente** es la última línea DESACTIVADA posterior a la última REACTIVADA de esa cuenta (o a su primera línea, si nunca se reactivó). Si hay varias DESACTIVADA seguidas, gana la última, lo que retrasa la anonimización (criterio conservador).

**Reglas por cuenta en `reaplicar_anonimizaciones`** (una transacción por cuenta, `SELECT … FOR UPDATE` sobre la cuenta; S = estado en la BD restaurada; fD = fecha de la desactivación vigente):

| Último evento | S en la BD restaurada | Acción |
|---|---|---|
| (cualquiera) | la cuenta no existe | Ninguna (se creó después de la copia). INFO |
| (cualquiera) | ANONIMIZADA | Ninguna (estado terminal) |
| REACTIVADA | cualquier otro estado | **Ninguna. El sistema no desactiva, no anonimiza ni reactiva esa cuenta.** Si S = DESACTIVADA (se desactivó antes de la copia y se reactivó después), se informa como `REACTIVADA_NO_REPRODUCIDA`: el Administrador decide si reactivarla (con una nueva credencial temporal) o anonimizarla |
| DESACTIVADA | PENDIENTE_ACTIVACION, ACTIVA o BLOQUEADA_TEMPORAL | Guarda RULE-015 (§4.4). Si se supera: estado DESACTIVADA, `desactivado_en = fD`, contraseña inutilizable, borrado de las sesiones de la cuenta y evento CUENTA_DESACTIVAR con `actor_etiqueta = 'sistema'` (igual que `desactivar_cuenta`, pero **sin** escribir en el libro) |
| DESACTIVADA | DESACTIVADA | Si `desactivado_en > fD + 1 s` → `INCONSISTENTE` (§4.4), sin cambios. Si no, `desactivado_en = fD` cuando difiere en más de 1 s (el plazo cuenta desde la desactivación vigente) |
| ANONIMIZADA | DESACTIVADA | Anonimización completa de §2 (mismas columnas, borrado de hijos, `fn_auditoria_seudonimizar`, evento CUENTA_ANONIMIZAR 'sistema'), sin escribir en el libro |
| ANONIMIZADA | PENDIENTE_ACTIVACION, ACTIVA o BLOQUEADA_TEMPORAL | Guarda RULE-015 (§4.4). Si se supera: en **una sola** transacción, desactivación (`desactivado_en` = fD si existe o, si no, la fecha de la línea ANONIMIZADA) seguida de la anonimización completa |

**Reglas en `anonimizar_cuentas`** (diaria y en el paso 5.2 del post-restore). Son candidatas las cuentas con `estado = 'DESACTIVADA'` y `desactivado_en < now() - interval '30 days'`, donde `now()` es el reloj de **PostgreSQL**, nunca el del contenedor. Con el libro leído:
- se **excluye** toda cuenta cuyo último evento sea REACTIVADA (se informa como `OMITIDA_REACTIVADA`);
- si el libro tiene una desactivación vigente con fD > `desactivado_en`, el plazo se cuenta desde fD;
- el último administrador operativo no puede verse afectado, porque una cuenta DESACTIVADA no es operativa; aun así, `trg_cuenta_admin_minimo` sigue siendo la red de seguridad;
- al anonimizar, escribe ANONIMIZADA en el libro dentro de la transacción (§4.2).

**Idempotencia y concurrencia**: ejecutar dos veces la relectura no produce más cambios. `reaplicar_anonimizaciones` y `anonimizar_cuentas` comparten la misma clave de `pg_try_advisory_lock`, de modo que nunca se solapan, y cada ejecución se registra en `ops_ejecucion_tarea` (`detalle` ≤500 caracteres con los contadores por motivo y los ids omitidos; son ids, no PII).

#### 4.4 Casos límite — `DEC-AUTO-262`, `DEC-AUTO-263`
| Caso | `reaplicar_anonimizaciones` (post-restore) | `anonimizar_cuentas` (diaria) |
|---|---|---|
| Libro **ausente** | `LIBRO_AUSENTE`: exit ≠ 0 sin tocar nada y FALLO. El post-restore se detiene. Para continuar hace falta una decisión humana (la restauración sobre datos reales ya es Puerta Humana §0.5): (a) depositar la copia del libro en el volumen (`LIBRO_RESTORE_DIR`), aceptando que no conoce los eventos posteriores a esa copia, o (b) volver a ejecutar con `--libro-vacio-confirmado` (instalación sin eventos) | Continúa solo con la BD y un WARNING `libro_ausente`: fuera de una restauración, la BD es la fuente de verdad |
| Libro ilegible (permisos, enlace simbólico, no es un fichero regular, escribible por otros) | `LIBRO_ILEGIBLE`: exit ≠ 0 sin cambios y FALLO | FALLO sin anonimizar a nadie en esa ejecución |
| Libro **corrupto** (una línea mal formada que no sea ninguno de los dos casos tolerados de §4.3) | `LIBRO_CORRUPTO`: exit ≠ 0 **sin aplicar ninguna línea** (una línea ilegible podría ser el REACTIVADA que protege una cuenta) y FALLO con los números de línea | FALLO sin anonimizar a nadie |
| Eventos duplicados (línea idéntica repetida o el mismo evento seguido) | Sin efecto: gana la última y la relectura es idempotente | Igual |
| Reloj: fechas no monótonas en una cuenta | Manda el orden del fichero. WARNING `fechas_no_monotonas` | Igual |
| Reloj: `fecha_utc` en el futuro (> `now()` de PostgreSQL + 5 min) | Se usa tal cual (retrasa la anonimización: criterio conservador). WARNING | Igual |
| Guarda **RULE-015**: la cuenta tiene rol ADMINISTRADOR y no queda **otra** cuenta ADMINISTRADOR en estado ACTIVA (el mismo criterio que `_exigir_otro_admin_activo` del servicio), comprobado bajo `pg_advisory_xact_lock(hashtext('cuentas_admin'))` | La cuenta **no se toca** (`OMITIDA_ULTIMO_ADMIN`). No bloquea: el comando termina con exit 0 y el aviso en la salida y en `detalle`, porque el panel debe poder abrirse para crear otro administrador. Después se vuelve a ejecutar el comando (es idempotente) o se actúa desde el panel | No aplica (solo actúa sobre cuentas DESACTIVADAS) |
| La BD es más reciente que el libro (`INCONSISTENTE`: el último evento es DESACTIVADA, S = DESACTIVADA y `desactivado_en` de la BD > fD + 1 s) | La cuenta no se toca. El comando termina con exit 0 y aviso: faltan líneas en el libro | — |
| `REACTIVADA_NO_REPRODUCIDA` | Aviso con exit 0. La cuenta sigue DESACTIVADA y no se anonimizará mientras su último evento sea REACTIVADA | `OMITIDA_REACTIVADA` en `detalle` |

Todos los avisos (`OMITIDA_*`, `INCONSISTENTE`, `REACTIVADA_NO_REPRODUCIDA`) se imprimen en el resumen del comando, que `post-restore-local.sh` muestra, y quedan en `ops_ejecucion_tarea.detalle` con resultado EXITO. Los errores (`LIBRO_*`) dejan resultado FALLO y exit ≠ 0.

#### 4.5 Protección del fichero — `DEC-AUTO-264`
- **Permisos**: fichero `0640` y directorio `0750`, con propietario el UID de la aplicación (10001) y grupo `app`. El servicio `backup` lo monta en solo lectura con `group_add` (ya lo hace en compose). Solo `backend` y `scheduler` lo montan con escritura. El escritor crea el fichero con `O_NOFOLLOW` y modo `0640`. El lector rechaza los enlaces simbólicos, lo que no sea un fichero regular y un fichero con permiso de escritura para "otros" (`LIBRO_ILEGIBLE`).
- **Sin firma ni HMAC por línea** (se descarta): la clave estaría en el mismo proceso que escribe el libro y que ya tiene `app_rw` sobre la BD, así que un atacante capaz de falsificar líneas podría hacer más daño directamente en la BD. Además, rotar la clave invalidaría el libro entero (la relectura fallaría, *fail-closed*), y una clave real es Puerta Humana. Se revalúa si el libro llega a almacenarse fuera del host de la aplicación.
- **Integridad frente a errores accidentales**: la aportan la validación estricta línea a línea con *fail-closed* (§4.4), el `fsync` y la copia diaria del volumen de operación con su sha256 (ya en `backup.sh`). Esa copia **solo** sirve si se pierde el libro vivo, y no contiene los eventos posteriores a su fecha.
- La relectura usa **siempre el libro vivo** por defecto (es el único que contiene los eventos posteriores a la copia de la BD).

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
- El libro de anonimizaciones es un segundo artefacto que proteger. No contiene PII (solo ids), pero su pérdida impediría re-aplicar un "Anonimizar ahora" posterior a la copia. Mitigación: se almacena en el volumen de operación, distinto del de datos, y se incluye en la copia de ese volumen, que es independiente de la rotación del dump. Desde CHG-DB-003, si falta el libro la relectura **falla** (*fail-closed*) en lugar de continuar en silencio (RSK-DB-006).
- CHG-DB-003: escribir el libro antes del commit convierte un disco lleno o un error de permisos del volumen `ops_libro` en errores 503 de desactivar, reactivar y anonimizar (fallo visible y reversible), en lugar de un evento perdido en silencio. Puede quedar una línea espuria si la transacción cae después de escribirla (RSK-DB-016, LOW, aceptado).
- CHG-DB-003: una cuenta que se desactivó antes de la copia y se reactivó después sigue DESACTIVADA tras restaurar (el sistema no reactiva por su cuenta) y no se anonimiza mientras su último evento sea REACTIVADA. Si el Administrador no actúa, sus datos se conservan: es una privacidad residual pequeña, que se acepta para no perder datos de forma irreversible.
- CHG-DB-003: la desactivación y la anonimización hechas por el sistema durante la relectura respetan RULE-015 y omiten al último administrador ACTIVO. En ese caso la cuenta queda operativa con sus datos hasta que un humano cree otro administrador y vuelva a ejecutar la relectura.
- `pg_dump` lógico de una instancia única: en el peor caso se pierden 24 h de edición (aceptado en DEC-AUTO-027).
- El trigger de inmutabilidad no protege frente a un superusuario, que no se usa en la aplicación (§7.4).

## Condiciones de invalidez
- RPO < 24 h → archivado de WAL (pgBackRest o WAL-G) + PITR.
- La normativa exige conservar la auditoría más de 365 días o conservar la copia más de 30 días (conflicto con REQ-057: revisión con el Arquitecto Funcional).
- Los medios dejan de ser inmutables (edición in-place): la copia de medios tendría que hacerse con snapshot.
- (§5) Aparece un requisito legal o de producto de **supresión física** de una cuenta o de un medio (p. ej., un derecho de supresión que la anonimización no satisfaga, o la retirada de un medio por infracción de derechos que exija borrar la fila): se sustituiría el trigger por una función SECURITY DEFINER de borrado controlado y auditado, con su propia Puerta Humana.
- (§5) El diseño de subida de medios pasa a asíncrono y necesita borrar filas: revisar `DEC-AUTO-203`.
- (§4.1-§4.5) Aparece otra transición que saca una cuenta de DESACTIVADA o la lleva a ella (p. ej. una desactivación automática por inactividad): tiene que escribir su evento en el libro o, si no, la relectura será incorrecta.
- (§4.2) Más de una instancia de backend en hosts distintos, o el libro en almacenamiento de red sin `flock` fiable: `flock` y `O_APPEND` dejan de garantizar el orden y la integridad de las líneas. En ese caso habría que mover el libro a un servicio con orden total (fuera del alcance local).
- (§4.5) El libro pasa a guardarse fuera del host de la aplicación, o lo pueden escribir otros procesos: revaluar la firma HMAC por línea con una clave independiente de la aplicación (Puerta Humana).
