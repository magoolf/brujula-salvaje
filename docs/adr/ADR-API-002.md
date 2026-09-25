# ADR-API-002 — Convenciones del contrato OpenAPI v1 (API-first) de Brújula Salvaje

| Campo | Valor |
|---|---|
| Estado | PROPOSED (Autoridad Delegada, CLAUDE.md §0.2) |
| Fecha | 2026-09-25 |
| Ticket | TKT-F4-003; modificado por TKT-F4-005 (CHG-API-001, §5) |
| Contrato | `contracts/openapi.yaml` (OpenAPI 3.1.0, 127 operaciones) |
| Trazabilidad | Skill_Backend §7 (reglas 11-13), §12.1-§12.6; BLUEPRINT §9, §12, §15, §16, §18, §38, §39.3, §40; DB_HANDOFF (PostgreSQL 18.6, bigint identity, ADR-DB-002/003/005) |
| DEC-AUTO | 100..119 (tabla final). ORIGEN: EXPANSIÓN_AUTÓNOMA; todas reversibles |

## Contexto
El Blueprint §38 enumera las operaciones públicas y del panel. Skill_Backend exige: versión en la URL, paginación en toda colección, errores RFC 9457 con `trace_id`, contrato documentado para cada endpoint, límites de tasa, idempotencia y health checks. El contrato se escribe antes del código (API-first). El pipeline lo compara con el esquema que genera drf-spectacular y ejecuta schemathesis (§12.5).

## Decisiones

### 1. Superficies y versionado (DEC-AUTO-100)
- `/api/v1/publico/**`: GET anónimo, solo PUBLICADO, acceso por slug y nunca por id, sin datos del staff (RULE-001, THREAT-011/019). La consume el SSR de Angular (CON-007).
- `/api/v1/panel/**`: sesión + CSRF (ADR-API-001).
- `/health/live` y `/health/ready`: fuera de la versión y con respuesta mínima `{status}` (THREAT-028). Readiness comprueba solo PostgreSQL (no hay broker, ADR-DB-005).
- Un cambio incompatible exige `/api/v2/` con cabecera `Deprecation` y ventana documentada (§12.4).

### 2. Errores (DEC-AUTO-103, DEC-AUTO-118)
- Todas las respuestas de error usan `application/problem+json` con `type`, `title`, `status`, `detail`, `code`, `errors` y `trace_id` (obligatorio). El mismo valor va en la cabecera `X-Trace-Id` (W3C trace-id de 32 hex; el request puede traer `traceparent`).
- `type` = `{PROBLEM_TYPE_BASE_URL}/errors/{code}`. La base es configuración porque el dominio de producción está pendiente (DEC-004). En desarrollo se usa `https://brujulasalvaje.example`.
- `title` y `detail` van en español y sin datos técnicos. `code` es un identificador estable en snake_case ASCII (catálogo en `components.schemas.Problem`).
- Semántica de estados: **400** formato o parámetros (incluye parámetros desconocidos, AC-113) · **401** sin sesión o credenciales · **403** rol, CSRF o paso pendiente · **404** inexistente o página fuera de rango · **409** conflicto de estado, versión o dependencia · **410** retirado · **422** regla de negocio (publicación, idempotencia) · **429** límite de tasa o bloqueo.

### 3. Paginación (DEC-AUTO-104, DEC-AUTO-105)
- Paginación por número de página (`pagina`, base 1) y envoltorio `{total, pagina, tamano_pagina, total_paginas, siguiente, anterior, resultados}`.
- El tamaño es fijo por recurso (`x-tamano-pagina`) y no existe parámetro de tamaño (THREAT-009): 24 en listados públicos, 50 en el panel, 48 en medios, 100 en catálogos pequeños, 500 en el mapa (una página con ≤500 destinos, ASM-008) y 1000 en el índice del sitemap.
- Las colecciones **acotadas por diseño** y que no crecen con los datos (12 meses, 9 niveles de escala, facetas, bloques del inicio, relacionados ≤6, días ≤60) se exponen como arrays con `maxItems` declarado. Es una excepción documentada a la Regla 11, no una omisión.
- Una página fuera de rango devuelve 404 `pagina_fuera_de_rango`. Un parámetro desconocido o fuera de dominio (slug inexistente en un filtro, `dificultad_min > dificultad_max`) devuelve 400 `parametro_invalido`, nunca 500. El Frontend descarta esos parámetros antes de llamar, de modo que la UI "los ignora" (AC-113).

### 4. Concurrencia y ciclo editorial (DEC-AUTO-106)
- Bloqueo optimista con `version` en el cuerpo (PUT y transiciones) o en la query (DELETE); si no coincide, 409 `conflicto_version` (AC-110; `UPDATE ... WHERE version = $2` según DB_HANDOFF).
- `PUT` depende del estado: BORRADOR → guarda el borrador (validación de formato) · PUBLICADO → "Actualizar publicación" con validación completa (422), instantánea y auditoría `ACTUALIZAR_PUBLICACION`, porque no existe un borrador paralelo (DEC-AUTO-045) · RETIRADO → 409 `transicion_invalida`.
- Las transiciones (`publicar`, `retirar` con `impacto-retiro` previo y `confirmar_cascada`, `reactivar`, `DELETE` de borradores nunca publicados) usan rutas genéricas `/panel/contenidos/{tipo}/{id}/...`, porque STATE-001 es uniforme. El CRUD y la vista previa van por tipo, porque los esquemas difieren.

### 5. Idempotencia (DEC-AUTO-107, actualizada por CHG-API-001 / TKT-F4-005 y DEC-AUTO-129)
- Cabecera opcional `Idempotency-Key` (UUID) en las 11 operaciones: creación de los 6 tipos de contenido, `publicar`, `retirar`, `reactivar`, la subida de medios y el alta de cuentas (ALT-017).
- **Ámbito: (cuenta, clave)**, único en todas las operaciones del panel (DB_HANDOFF v1.1, tabla persistente `idempotencia_peticion`, `UNIQUE (cuenta_id, clave)`). Esto corrige la versión anterior de este ADR, que decía (cuenta, operación, clave). El cliente genera una clave nueva por petición lógica.
- La huella es sha256 de la operación, los parámetros de ruta y el cuerpo canónico (en multipart, las huellas de los archivos y los campos). Solo se guardan respuestas **2xx confirmadas**, durante 24 h lógicas. Un fallo 4xx/5xx hace ROLLBACK junto con el efecto, y un reintento con la misma clave vuelve a ejecutar la operación.
- Respuestas:
  - Misma clave, misma operación y misma huella, ya completada → se devuelven el código y el cuerpo originales sin repetir el efecto.
  - Misma clave con otra operación u otra huella → **422 `idempotencia_conflicto`**.
  - Petición concurrente con la misma clave aún sin confirmar y espera por encima de `lock_timeout` = 3 s → **409 `idempotencia_en_curso`** con `Retry-After`. Es reintentable con la misma clave.
  - `panelCrearCuenta` **no persiste su respuesta** porque la contraseña temporal nunca se guarda (AC-106, DEC-AUTO-125 de BD). Repetirla con una clave ya completada → **409 `idempotencia_respuesta_no_reproducible`** con cabecera `Location: /api/v1/panel/cuentas/{id}`. El Administrador emite otra contraseña temporal con `POST /cuentas/{id}/restablecer-contrasena` (DEC-AUTO-129, decisión del Orquestador).
- El protocolo transaccional exacto está en `DB_HANDOFF.yaml` (`idempotencia_peticion.notas`, DEC-AUTO-123..128). El Developer lo implementa como un servicio o decorador común de las 11 operaciones.

### 6. Entradas estrictas (DEC-AUTO-108)
- Cada tipo sigue el patrón `{T}Campos` / `{T}Entrada` / `{T}Actualizacion` / `{T}Panel` / `{T}VistaPrevia`. Las entradas llevan `unevaluatedProperties: false` (o `additionalProperties: false`). Un campo desconocido o no editable (estado, autoría, rol, version en el POST) devuelve 400 `campo_no_permitido` (THREAT-024).
- En BORRADOR todos los campos de contenido son opcionales o nullable. Los requisitos "P" se evalúan al publicar y se informan en `requisitos_publicacion`.

### 7. Texto enriquecido (DEC-AUTO-109)
HTML de lista blanca (RULE-022) saneado **en el servidor al guardar**, con un saneador basado en allowlist. Solo se admiten enlaces http, https o rutas internas (RULE-021). Los términos de glosario se representan como `<a href="/glosario#{slug}" data-glosario="{slug}">`. El Frontend lo trata como HTML ya saneado, pero la CSP sin `unsafe-inline` sigue siendo la red de seguridad (THREAT-005).

### 8. Medios (DEC-AUTO-110)
- Subida `multipart/form-data` de 1 a 10 archivos, procesada de forma **síncrona** (sin broker, ADR-DB-005). Devuelve 200 con el resultado por archivo (ACEPTADO / RECHAZADO con motivo / DUPLICADO con `medio_existente_id`). Petición mayor de 105 MB → 413.
- Los derivados son AVIF, WebP y JPEG (formatos de DB_HANDOFF). Los de medios DISPONIBLES se sirven como estáticos públicos con nombre aleatorio generado por el sistema, tipo explícito y `nosniff`. Los de medios no DISPONIBLES solo se ven por `GET /panel/medios/{id}/archivo` (con sesión). El original saneado nunca se sirve.
- `fuente_url` y `url_texto_legal` son solo texto: el servidor nunca los descarga (THREAT-022).

### 9. Límites de tasa (DEC-AUTO-111)
- Perfiles (`x-limite-tasa`): publico-lectura 120/min · publico-busqueda 30/min · publico-aleatorio 30/min por IP · panel-login 10/min por IP + bloqueo por usuario · panel-mfa 10/min · panel-lectura 600/min · panel-escritura 120/min · panel-subida 20/min · panel-vista-previa 60/min por cuenta.
- La IP cliente se toma de `X-Forwarded-For` solo desde proxies de confianza (`NUM_PROXIES`). **El SSR de Angular debe reenviar la IP del visitante**; si no, todo el tráfico público compartiría la cuota del contenedor SSR.
- El almacenamiento es `DatabaseCache` sobre `cache_limites` con clave HMAC (ADR-DB-005 §3) o, como alternativa, el proxy inverso (DevOps).

### 10. Caché HTTP (DEC-AUTO-112)
- Lecturas públicas: `Cache-Control: public, max-age=60, stale-while-revalidate=300`.
- Búsqueda y destino aleatorio: `no-store` (privacidad del texto buscado, THREAT-020; AC-122).
- Panel: `no-store` + `X-Robots-Tag: noindex, nofollow`.
- ETag/304 queda en FUTURE: añadirlo no rompe el contrato.

### 11. Retirado → 410 (DEC-AUTO-113)
Un detalle público retirado responde 410 con `ProblemaRetirado`: alternativas publicadas (máximo 6) y `listado_padre`, sin el cuerpo del contenido (DEC-AUTO-040, THREAT-011). Un contenido inexistente o un borrador nunca publicado responde 404.

### 12. Vista previa (DEC-AUTO-114)
`POST /panel/contenidos/{tipo}/vista-previa` recibe los datos del formulario y devuelve `VistaPrevia` con `datos` en la forma del detalle público y los requisitos pendientes. No persiste nada. Es POST porque el cuerpo puede superar los límites de una query.

### 13. Restaurar revisión (DEC-AUTO-115)
`POST .../revisiones/{n}/restaurar` devuelve la instantánea como cuerpo editable y audita `RESTAURAR_REVISION`. No modifica el contenido: el efecto llega al guardar y publicar (AC-121).

### 14. Identificadores y nombres (DEC-AUTO-116)
- Ids internos `integer/int64` (bigint identity, DB_HANDOFF), expuestos solo en el panel. Como el supertipo `contenido` comparte id entre tipos, `(tipo, id)` es redundante pero explícito.
- Campos en español snake_case, iguales que el modelo lógico §18.
- Los decimales (lat/long, km) se serializan como número JSON: configurar `COERCE_DECIMAL_TO_STRING=False`.

### 15. Slugs reservados (DEC-AUTO-117)
`mapa` y `aleatorio` están reservados para destinos (colisionan con `/destinos/mapa` y `/destinos/aleatorio`). El validador de slug los rechaza con 400.

### 16. Comparación con el esquema generado (§12.5)
drf-spectacular genera componentes planos (sin `allOf` ni `unevaluatedProperties`), así que el gate `CONTRACT_TESTS` compara **semánticamente** (p. ej. `oasdiff breaking contracts/openapi.yaml generado.yaml`: cero cambios incompatibles en rutas, métodos, parámetros, códigos de estado y propiedades requeridas o tipos) y ejecuta `schemathesis run contracts/openapi.yaml` contra el entorno de test sin respuestas 5xx. Una diferencia real se resuelve con un CHG del contrato, nunca en silencio.

## Registro DEC-AUTO-100..119
| ID | Decisión (elegida) | Alternativas | Motivo | Riesgo | Reversibilidad |
|---|---|---|---|---|---|
| DEC-AUTO-100 | Tres superficies: `/api/v1/publico`, `/api/v1/panel`, `/health/*` | API única con permisos mezclados | Aislamiento de RULE-001/029, throttling y caché distintos | Bajo | Alta |
| DEC-AUTO-101 | `sessionid` con Path=/api/v1/panel/ (HttpOnly) y `csrftoken` con Path=/ legible por JS | CSRF_USE_SESSIONS + token en el cuerpo | Alinea con el XSRF de Angular (Skill_Frontend) y limita la credencial | csrftoken visible en rutas públicas para el staff (no es credencial) | Alta |
| DEC-AUTO-102 | Login por pasos con `paso_pendiente`; bloqueo por usuario normalizado exista o no la cuenta | Bloqueo solo de cuentas existentes | Anti enumeración (THREAT-018) sin perder el bloqueo (THREAT-001) | Un atacante puede bloquear un usuario legítimo 15 min (DoS dirigido, mitigado por el límite por IP) | Alta |
| DEC-AUTO-103 | `type` de Problem con base configurable y catálogo cerrado de `code` | URN; `about:blank` | Dominio pendiente (DEC-004); clientes que se basan en `code` | Bajo | Alta |
| DEC-AUTO-104 | Paginación por número con tamaño fijo; colecciones acotadas como arrays con `maxItems` | Cursor; tamaño configurable | Coincide con la UI (24/50, páginas numeradas) y con THREAT-009 | Bajo | Alta |
| DEC-AUTO-105 | Parámetros desconocidos o inválidos → 400; página fuera de rango → 404 | Ignorar en el servidor | AC-113 lo pide literalmente para la API | El Frontend debe sanear antes de llamar | Alta |
| DEC-AUTO-106 | `version` en el cuerpo; PUT con semántica dependiente del estado; transiciones genéricas | If-Match/ETag; endpoint "actualizar-publicacion" por tipo | Clientes generados más simples; STATE-001 uniforme | PUT sobre PUBLICADO puede devolver 422 | Alta |
| DEC-AUTO-107 | `Idempotency-Key` opcional, ámbito (cuenta, clave), retención de 24 h en la tabla persistente `idempotencia_peticion` (CHG-API-001) | Solo `version`; sin idempotencia; ámbito (cuenta, operación, clave) | ALT-017, §12.4; alineado con DB_HANDOFF v1.1 | Las respuestas de alta de cuenta no son reproducibles (DEC-AUTO-129) | Alta |
| DEC-AUTO-108 | Entradas con `unevaluatedProperties:false` → 400 `campo_no_permitido` | Ignorar desconocidos (DRF por defecto) | THREAT-024 explícito y testeable | drf-spectacular no lo genera: comparación semántica | Alta |
| DEC-AUTO-109 | Texto enriquecido = HTML de lista blanca saneado en el servidor | Markdown; JSON de bloques | RULE-022 y render SSR directo | Depende del saneador | Media |
| DEC-AUTO-110 | Subida síncrona multipart, resultado por archivo, derivados estáticos públicos solo de DISPONIBLES | Asíncrona con Celery; derivados siempre públicos | ADR-DB-005 sin broker; THREAT-006/011 | Latencia en subidas grandes | Alta |
| DEC-AUTO-111 | Perfiles de throttling y clave por IP desde proxy de confianza | Sin límite en lecturas; límite solo en el proxy | THREAT-001/009 | SSR mal configurado → cuota compartida | Alta |
| DEC-AUTO-112 | Caché pública 60 s; `no-store` en búsqueda, aleatorio y panel | Sin caché | REQ-051/053; privacidad | Contenido desfasado ≤60 s tras publicar | Alta |
| DEC-AUTO-113 | 410 problem+json con alternativas y sin cuerpo | 410 con el contenido; 301 | DEC-AUTO-040, THREAT-011 | Bajo | Alta |
| DEC-AUTO-114 | Vista previa por POST por tipo, sin persistencia y con requisitos | GET de un borrador guardado | FEAT-035 ("sin persistir") | Bajo | Alta |
| DEC-AUTO-115 | Restaurar revisión devuelve los datos al formulario y audita | Restaurar persistiendo | AC-121 | Bajo | Alta |
| DEC-AUTO-116 | Ids int64 solo en el panel; campos en español snake_case; decimales como número | UUID; inglés | DB_HANDOFF bigint; coherencia con §18 | Bajo | Media |
| DEC-AUTO-117 | Slugs reservados `mapa` y `aleatorio` en destinos | Rutas `/destinos-mapa` | Coherencia con las rutas públicas de §10 | Bajo | Alta |
| DEC-AUTO-118 | Mensajes en español; `code` estable; `X-Trace-Id` en todas las respuestas | Mensajes en inglés | CON-004; §12.1 y §12.3 | Bajo | Alta |
| DEC-AUTO-119 | MFA obligatorio para el Admin como paso `CONFIGURAR_MFA` (SHOULD) | Opcional para todos | DEC-AUTO-037 | ASM-011 | Alta |

## Conflictos y coordinación
- **CONFLICT (a registrar por el Orquestador): Celery.** Skill_Backend §2, §12.3 y §12.4 tienen Celery y un broker como estándar de referencia (trazas de Celery, readiness del broker). ADR-DB-005 / DEC-AUTO-090 lo descartan porque ningún proceso del Blueprint requiere mensajería. Este contrato **no impone Celery**: subidas síncronas, tareas programadas como comandos `manage.py` con advisory lock y readiness solo de la BD. Con la precedencia de CLAUDE.md §0.1 (ambos son Contratos Técnicos de rango 4, y Skill_Backend §12.4 condiciona el broker a un ADR), se aplica "sin broker" hasta que el Orquestador resuelva. Efecto en los gates: OBSERVABILITY omite las trazas de Celery y la comprobación del broker.
- **CHG a Base de Datos:** almacenamiento de `Idempotency-Key`. **Cerrado:** DB_HANDOFF v1.1 (TKT-F4-004) + CHG-API-001 (TKT-F4-005) aplicado en el contrato (§5). DEC-AUTO-129 es una decisión del Orquestador y queda fuera del rango 100..119 de este ADR.
- **Frontend:** reenviar `X-Forwarded-For` desde el SSR; sanear los parámetros de filtro antes de llamar; generar el cliente desde este contrato.
