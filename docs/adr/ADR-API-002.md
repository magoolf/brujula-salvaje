# ADR-API-002 — Convenciones del contrato OpenAPI v1 (API-first) de Brújula Salvaje

| Campo | Valor |
|---|---|
| Estado | PROPOSED (Autoridad Delegada, CLAUDE.md §0.2) |
| Fecha | 2026-09-25 |
| Ticket | TKT-F4-003; modificado por TKT-F4-005 (CHG-API-001, §5) , TKT-F4-007 (CHG-API-002, §1, §5, §17, §18), TKT-F4-008 (CHG-API-003, §7, §19), TKT-F4-009 (CHG-API-004, §20) y TKT-F4-011 (CHG-API-005, §4, §21) |
| Contrato | `contracts/openapi.yaml` (OpenAPI 3.1.0, 128 operaciones desde CHG-API-005) |
| Trazabilidad | Skill_Backend §7 (reglas 11-13), §12.1-§12.6; BLUEPRINT §9, §12, §15, §16, §18, §38, §39.3, §40; BLUEPRINT v1.1 (CHG-BP-001: RULE-001/002/003/007/025, FLOW-011 5', FLOW-012, SCR-038, STATE-001, ALT-016/017/019, AC-124..130); DB_HANDOFF (PostgreSQL 18.6, bigint identity, ADR-DB-002/003/005) |
| DEC-AUTO | 100..119, 216..219 y 265..269 (tablas finales). ORIGEN: EXPANSIÓN_AUTÓNOMA; todas reversibles. DEC-AUTO-215 es una decisión del Orquestador (OBS-QA004-06) que este ADR aplica en §17; DEC-AUTO-912 y DEC-AUTO-914 son decisiones del Orquestador que este ADR aplica en §21 |

## Contexto
El Blueprint §38 enumera las operaciones públicas y del panel. Skill_Backend exige: versión en la URL, paginación en toda colección, errores RFC 9457 con `trace_id`, contrato documentado para cada endpoint, límites de tasa, idempotencia y health checks. El contrato se escribe antes del código (API-first). El pipeline lo compara con el esquema que genera drf-spectacular y ejecuta schemathesis (§12.5).

## Decisiones

### 1. Superficies y versionado (DEC-AUTO-100)
- `/api/v1/publico/**`: GET anónimo, solo PUBLICADO, acceso por slug y nunca por id, sin datos del staff (RULE-001, THREAT-011/019). La consume el SSR de Angular (CON-007).
- `/api/v1/panel/**`: sesión + CSRF (ADR-API-001).
- `/health/live` y `/health/ready`: fuera de la versión y con respuesta mínima `{status}` (THREAT-028). Readiness comprueba solo PostgreSQL (no hay broker, ADR-DB-005).
- **CHG-API-002 (RSK-OPS-020, DEC-AUTO-216):** ambos documentan además **429 `limite_tasa`** (`components.responses.LimiteTasaBorde`: Problem, `X-Trace-Id`, `Retry-After`). Lo emite el **proxy de borde**, no Django, desde una zona de límite propia por IP (50 r/s, burst 200). Un sondeo que reciba 429 debe reintentar y no marcar el proceso como caído. **No se documenta 404**: solo aparecería en rutas inexistentes, que no son operaciones del contrato. Documentarlo añadiría ruido y no aportaría ningún caso comprobable.
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
- **Desde CHG-API-005 (§21):** una operación puede hacer transitar varias entidades de forma atómica (co-publicación destino + tipos y retiro en cascada destino → itinerarios + tipos). El bloqueo optimista abarca todas las entidades cuya versión envía el cliente (`copublicar_tipos[].version`), y el análisis previo sin efectos es `POST .../analisis-publicacion`.

### 5. Idempotencia (DEC-AUTO-107, actualizada por CHG-API-001 / TKT-F4-005 y DEC-AUTO-129)
- Cabecera opcional `Idempotency-Key` (UUID) en las 11 operaciones: creación de los 6 tipos de contenido, `publicar`, `retirar`, `reactivar`, la subida de medios y el alta de cuentas (ALT-017).
- **Ámbito: (cuenta, clave)**, único en todas las operaciones del panel (DB_HANDOFF v1.1, tabla persistente `idempotencia_peticion`, `UNIQUE (cuenta_id, clave)`). Esto corrige la versión anterior de este ADR, que decía (cuenta, operación, clave). El cliente genera una clave nueva por petición lógica.
- La huella es sha256 de la operación, los parámetros de ruta y el cuerpo canónico (en multipart, las huellas de los archivos y los campos). Solo se guardan respuestas **2xx confirmadas**, durante 24 h lógicas. Un fallo 4xx/5xx hace ROLLBACK junto con el efecto, y un reintento con la misma clave vuelve a ejecutar la operación.
- Respuestas:
  - Misma clave, misma operación y misma huella, ya completada → se devuelven el código y el cuerpo originales sin repetir el efecto.
  - Misma clave con otra operación u otra huella → **422 `idempotencia_conflicto`**.
  - Petición concurrente con la misma clave aún sin confirmar y espera por encima de `lock_timeout` = 3 s → **409 `idempotencia_en_curso`** con `Retry-After`. Es reintentable con la misma clave.
  - `panelCrearCuenta` **no persiste su respuesta** porque la contraseña temporal nunca se guarda (AC-106, DEC-AUTO-125 de BD). Repetirla con una clave ya completada → **409 `idempotencia_respuesta_no_reproducible`** con cabecera `Location: /api/v1/panel/cuentas/{id}`. El Administrador emite otra contraseña temporal con `POST /cuentas/{id}/restablecer-contrasena` (DEC-AUTO-129, decisión del Orquestador).
  - **Generalización (CHG-API-002, OBS-QA004-02, DEC-AUTO-219):** **cualquiera** de las 11 operaciones devuelve 409 `idempotencia_respuesta_no_reproducible` si se completó pero su cuerpo de respuesta original superó 64 KB (65 536 bytes) y por eso no se guardó (DEC-AUTO-128, `TAMANO_MAXIMO_RESPUESTA`). El efecto no se repite. La cabecera `Location` **solo** aparece en `panelCrearCuenta`. En las demás operaciones no hay `Location`: el cliente trata la operación como ya realizada y relee el recurso afectado (listado, detalle o resultado de la subida). Las 11 operaciones ya declaraban la respuesta 409 `Conflicto`; ahora sus descripciones (parámetro `IdempotencyKey` y respuesta `Conflicto`) recogen el caso general.
- El protocolo transaccional exacto está en `DB_HANDOFF.yaml` (`idempotencia_peticion.notas`, DEC-AUTO-123..128). El Developer lo implementa como un servicio o decorador común de las 11 operaciones.

### 6. Entradas estrictas (DEC-AUTO-108)
- Cada tipo sigue el patrón `{T}Campos` / `{T}Entrada` / `{T}Actualizacion` / `{T}Panel` / `{T}VistaPrevia`. Las entradas llevan `unevaluatedProperties: false` (o `additionalProperties: false`). Un campo desconocido o no editable (estado, autoría, rol, version en el POST) devuelve 400 `campo_no_permitido` (THREAT-024).
- En BORRADOR todos los campos de contenido son opcionales o nullable. Los requisitos "P" se evalúan al publicar y se informan en `requisitos_publicacion`.

### 7. Texto enriquecido (DEC-AUTO-109)
HTML de lista blanca (RULE-022) saneado **en el servidor al guardar**, con un saneador basado en allowlist. Solo se admiten enlaces http, https o rutas internas (RULE-021). Los términos de glosario se representan como `<a href="/glosario#{slug}" data-glosario="{slug}">`. El Frontend lo trata como HTML ya saneado, pero la CSP sin `unsafe-inline` sigue siendo la red de seguridad (THREAT-005).
Longitud máxima: **100000 caracteres**, igual al `CHECK char_length <= 100000` de BD (DEC-AUTO-097). Ver §19 (CHG-API-003).

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

### 17. Reautenticación al iniciar la activación de MFA (CHG-API-002, DEC-AUTO-215 / DEC-AUTO-218). CAMBIO INCOMPATIBLE DELIBERADO
- **Operación afectada:** solo `panelIniciarActivacionMfa` (`POST /api/v1/panel/auth/mfa/activacion`). `panelConfirmarActivacionMfa`, `panelDesactivarMfa`, `panelRegenerarCodigosRecuperacion` y `panelVerificarMfa` no cambian. `panelDesactivarMfa` ya exigía `contrasena` + `codigo`.
- **Petición:** antes no tenía cuerpo. Ahora lleva `requestBody` **obligatorio** `MfaActivacionInicioEntrada = {contrasena}`: string de 1 a 128 caracteres, `format: password`, `writeOnly`, sin NUL y con `additionalProperties: false`. Se exige también con el paso pendiente `CONFIGURAR_MFA`.
- **Errores:**
  - Cuerpo ausente, `contrasena` vacía o con formato inválido → **400 `validacion`** con `errors.contrasena`. Un campo extra → 400 `campo_no_permitido`. Se añadió la respuesta 400 `Validacion`, que antes no estaba declarada.
  - Contraseña incorrecta → **401 `credenciales_invalidas`**, un code que ya existía en el catálogo. Tiene el mismo mensaje y un tiempo equivalente al del login (se ejecuta siempre el hash, THREAT-018). **No cierra la sesión.** El cliente distingue este caso por `code` y no lo trata como `no_autenticado` ni como `sesion_expirada`: se queda en la pantalla y marca el campo.
  - Cada fallo cuenta en el contador de fallos por usuario normalizado de RULE-017 y se audita como `LOGIN_FALLIDO`. Al 5.º fallo → **429 `acceso_bloqueado_temporalmente`** con `Retry-After`.
  - MFA ya activo → **409 `transicion_invalida`**.
- **Éxito (200):** solo con la contraseña correcta se genera el secreto provisional (`MfaActivacionInicio`, sin cambios). Cualquier secreto provisional previo de la sesión se descarta. El cuerpo de la petición nunca se registra (THREAT-020).
- **Por qué:** con una sesión robada (THREAT-002) se podría vincular el TOTP del atacante y bloquear al titular. Reautenticar con la contraseña sigue OWASP ASVS L2 (V6/V7: reautenticación antes de cambiar factores de autenticación).
- **Compatibilidad:** es un cambio **incompatible** en `/api/v1/`, porque añade un `requestBody` obligatorio. Skill_Backend §12.4 exige una versión nueva para cambios incompatibles. Se acepta como **excepción documentada** porque la operación **aún no está desplegada** en ningún entorno compartido ni tiene clientes: el MFA es SHOULD y lo implementa TKT-004. No se abre `/api/v2/` ni se emite `Deprecation`. Si la operación ya estuviera desplegada, este cambio exigiría v2. En `openapi.yaml` la operación lleva `x-cambio-incompatible`, para que la comparación semántica (`oasdiff breaking`, §16) acepte la ruptura esta única vez, con la referencia a este apartado.
- **Consecuencia para el Frontend:** el cliente generado cambia la firma del método (`panelIniciarActivacionMfa(body)`). La pantalla SCR-032 pide la contraseña antes de mostrar el QR.

### 18. Texto de entrada sin NUL (CHG-API-002, OBS-QA004-05, DEC-AUTO-217)
- El backend rechaza U+0000 en cualquier campo de texto con 400 `validacion`, o `parametro_invalido` si llega en la query, porque PostgreSQL no admite NUL en `text`/`varchar`. El contrato lo declara con `pattern: '^[^\u0000]*$'`, una regex ECMA-262 que es compatible con hypothesis-jsonschema/schemathesis. Así ni schemathesis ni los clientes generan NUL.
- Dónde se aplica el patrón:
  - credenciales: `LoginEntrada.usuario/contrasena/siguiente`, `CambioContrasenaEntrada.*`, `MfaDesactivacionEntrada.contrasena`, `MfaActivacionInicioEntrada.contrasena`;
  - cuentas: `CuentaCreacionEntrada.nombre_visible`, `CuentaActualizacionEntrada.nombre_visible`. `usuario` ya tenía un patrón cerrado `^[a-z0-9._-]{3,40}$`;
  - autorización y fuentes: `AutorizacionEntrada.version_politica`, `FuenteEntrada.*`;
  - contenido: los textos de `ContenidoComunCampos` y de cada `{T}Campos`, incluido el HTML enriquecido; `DiaEntrada`, `ChecklistEntrada`, `ElementoColeccionEntrada.nota_editorial` y `RetiroEntrada.motivo`;
  - medios, configuración y catálogos: `MedioCatalogacionEntrada`, `ConfigInicioCampos`, `ConfiguracionSitioCampos`, `RegionCampos`, `PaisCampos`, `CategoriaGuiaCampos`, `LicenciaCampos`, `NivelEscalaEntrada`;
  - esquemas y parámetros compartidos: `TextoEnriquecido`, `UrlSegura`, y los parámetros `q` (`Q`, `TextoFiltro`).
- Las URL cambian de `^https?://` a `^https?://[^\u0000]*$`. Los campos que ya tenían un patrón cerrado (slug, códigos, uuid, TOTP) no cambian, porque ya excluyen NUL.
- La regla también figura como norma general en `info.description`. Si un campo de texto nuevo no lleva el patrón, la norma sigue aplicándose.
- **Compatible hacia atrás:** esas peticiones ya recibían 400. El contrato solo documenta lo que el servidor ya hace.

### 19. Longitud del texto enriquecido alineada con la BD (CHG-API-003 / TKT-F4-008, DEC-AUTO-903)
- **Problema:** el contrato declaraba `maxLength: 200000` en el HTML enriquecido, pero DB_HANDOFF v1.2 (DEC-AUTO-097, ADR-DB-002 §6) define `CHECK char_length <= 100000` en esas columnas `text`, y el proxy (`infra/proxy/nginx.conf`) también asume ≤ 100.000. Una entrada de 100001 a 200000 caracteres cumplía el contrato y la BD la rechazaba: riesgo de 5xx en schemathesis y en TKT-006.
- **Decisión (DEC-AUTO-903, del Orquestador):** el contrato baja a `maxLength: 100000` en los campos que superaban el CHECK de BD. Los campos que ya tenían un límite **menor** que la BD se mantienen.
- **Campos cambiados (200000 → 100000; BD ≤ 100000):**

| Esquema.campo | Columna BD | Operaciones afectadas |
|---|---|---|
| `TextoEnriquecido` (salida) | todas las de abajo | `publicoObtenerDestino`, `publicoObtenerItinerario`, `publicoObtenerTipoAventura`, `publicoObtenerGuia`, `publicoObtenerColeccion`, `publicoObtenerPaginaInstitucional` y los `datos` de las vistas previas |
| `DestinoCampos.descripcion_experta`, `.como_llegar`, `.seguridad_riesgos`, `.sostenibilidad` | `destino.*` | `panelCrearDestino`, `panelActualizarDestino`, `panelVistaPreviaDestino` (entrada); `panelObtenerDestino` y respuestas `DestinoPanel` (salida) |
| `ItinerarioCampos.riesgos_seguridad` | `itinerario.riesgos_seguridad` | `panelCrearItinerario`, `panelActualizarItinerario`, `panelVistaPreviaItinerario`; `panelObtenerItinerario` / `ItinerarioPanel` |
| `GuiaCampos.cuerpo` | `guia.cuerpo` | `panelCrearGuia`, `panelActualizarGuia`, `panelVistaPreviaGuia`; `panelObtenerGuia` / `GuiaPanel` |
| `TipoAventuraCampos.descripcion` | `tipo_aventura.descripcion` | `panelCrearTipoAventura`, `panelActualizarTipoAventura`, `panelVistaPreviaTipoAventura`; `panelObtenerTipoAventura` / `TipoAventuraPanel` |
| `ColeccionCampos.descripcion` | `coleccion.descripcion` | `panelCrearColeccion`, `panelActualizarColeccion`, `panelVistaPreviaColeccion`; `panelObtenerColeccion` / `ColeccionPanel` |
| `PaginaInstitucionalCampos.cuerpo` | `pagina_institucional.cuerpo` | `panelActualizarPaginaInstitucional`, `panelVistaPreviaPaginaInstitucional`; `panelObtenerPaginaInstitucional` / `PaginaInstitucionalPanel` |

- **Campos que no cambian (límite del contrato menor que el de BD):** `DiaEntrada.actividades` y `DiaEntrada.consejos` (50000; BD ≤ 100000), `DestinoCampos.clima` (5000; BD `text` ≤ 100000), `ConfiguracionSitioCampos.texto_descargo` (5000; BD 1..100000). `DestinoDetalle.clima` y `ConfiguracionPublica.texto_descargo` (salida, 5000) tampoco cambian. El resto de textos largos son `varchar(n)` con el mismo n en el contrato.
- **Longitud después del saneado:** el saneador puede alargar el texto (entidades como `&amp;`). El servicio comprueba el límite **sobre el HTML ya saneado** y, si lo supera, responde **400 `validacion`** en el campo. Nunca deja que el CHECK de BD produzca un 5xx. Queda escrito en la descripción de `TextoEnriquecido`.
- **Compatibilidad:** para los clientes es compatible hacia atrás. La entrada es más restrictiva, pero ningún servidor implementa aún esas operaciones (TKT-006 pendiente) y ningún valor almacenable en BD supera el nuevo límite, así que la salida no cambia en la práctica. `oasdiff` puede marcar como *breaking* la reducción de `maxLength` en el cuerpo de la petición. Se acepta como excepción documentada (mismo criterio que §17): no se abre `/api/v2/` ni se emite `Deprecation`, y la versión `info.version` se mantiene en 1.0.0.

- **Ampliación: nulabilidad alineada con la BD (DEC-AUTO-905, del Orquestador).** Se revisaron todos los campos nullable de los esquemas de entrada contra las columnas de DB_HANDOFF v1.2:

| Esquema.campo | Antes | Después | Columna BD | Operaciones afectadas |
|---|---|---|---|---|
| `DiaEntrada.titulo` | `['string','null']`, opcional | `string`, **requerido**, `minLength: 1`, `maxLength: 150` | `dia_itinerario.titulo varchar(150) NOT NULL` | `panelCrearItinerario`, `panelActualizarItinerario`, `panelVistaPreviaItinerario` (array `dias`) |
| `DiaEntrada.actividades` | `['string','null']`, opcional | `string`, **requerido**, `maxLength: 50000` (sin cambio) | `dia_itinerario.actividades text NOT NULL` | las mismas |

  `DiaEntrada` es el único esquema de entrada de días (`ItinerarioCampos.dias`). Un día sin título ni actividades no se envía: el borrador guarda solo los días que ya tienen esos datos, y RULE-003 (días = duración) se sigue evaluando al publicar. `actividades` admite `""` en borrador porque la BD también lo admite. `DiaItinerario` (salida) ya los declaraba requeridos y no nullable.

  **Nullable en el contrato con columna NOT NULL que no se cambian (el servidor da el valor):**
  - `ContenidoComunCampos.slug` y `TerminoGlosarioCampos.slug` → `contenido.slug NOT NULL`. Si es null, el servicio propone el slug a partir del título antes de insertar (descripción del campo, RULE-008). No llega null a la BD.
  - `IdOpcionalCampo.id` y `LoginEntrada.siguiente` no se persisten.

  El resto de campos nullable de entrada (`DestinoCampos`, `ItinerarioCampos`, `GuiaCampos`, `TipoAventuraCampos`, `ColeccionCampos`, `ContenidoComunCampos.fecha_ultima_revision/seo_*`, `PaginaInstitucionalCampos.fecha_ultima_revision/seo_*`, `DiaEntrada.distancia_km/desniveles/alojamiento_orientativo/consejos`, `ChecklistEntrada.grupo`, `ElementoColeccionEntrada.nota_editorial`, `TerminoGlosarioCampos.definicion`, `FuenteEntrada.entidad_editora/url/fecha_consulta`, `MedioCatalogacionEntrada.*`, `ConfiguracionSitioCampos.lema/responsable_*`, `LicenciaCampos.url_texto_legal`) corresponde a columnas NULL. Sin cambios.

- **Ampliación: otras restricciones en las que el contrato admitía lo que la BD rechaza.** Aplican el criterio de DEC-AUTO-903 (el contrato se ajusta a la BD). Las propone Backend y quedan **pendientes de que el Orquestador las ratifique**:

| Esquema.campo | Antes | Después | Restricción BD | Operaciones afectadas |
|---|---|---|---|---|
| `FuenteEntrada.url` | maxLength 2000 | 500 | `fuente.url varchar(500)` | crear, actualizar y vista previa de destino, itinerario, guía, tipo de aventura y colección (`ContenidoComunCampos.fuentes`) |
| `MedioCatalogacionEntrada.fuente_url` | 2000 | 500 | `medio.fuente_url varchar(500)` | `panelCatalogarMedio` |
| `LicenciaCampos.url_texto_legal` | 2000 | 500 | `licencia.url_texto_legal varchar(500)` | `panelCrearLicencia`, `panelActualizarLicencia` (y la salida `Licencia`) |
| `LicenciaCampos.codigo` | pattern `^[A-Za-z0-9.-]+$` | `^[A-Z0-9.-]+$` | `CHECK (codigo ~ '^[A-Z0-9.-]+$')` | `panelCrearLicencia`, `panelActualizarLicencia` |
| `RegionCampos.slug` | `Slug` (maxLength 120) | en línea, maxLength 60 | `region.slug varchar(60)` | `panelCrearRegion`, `panelActualizarRegion` |
| `PaisCampos.slug` | `Slug` (120) | en línea, maxLength 80 | `pais.slug varchar(80)` | `panelCrearPais`, `panelActualizarPais` |
| `CategoriaGuiaCampos.slug` | `Slug` (120) | en línea, maxLength 80 | `categoria_guia.slug varchar(80)` | `panelCrearCategoriaGuia`, `panelActualizarCategoriaGuia` |
| `UrlSegura` (esquema compartido, sin referencias actuales) | 2000 | 500 | `varchar(500)` de las URL | ninguna |

  El parámetro de filtro por código de licencia (query del listado de medios) no se cambia: no se persiste.
- **Compatibilidad de las ampliaciones:** todas son más restrictivas en la entrada. Las peticiones que ahora se rechazan con 400 ya fallaban en la BD (5xx), así que ningún cliente correcto se ve afectado. Se aplica la misma excepción documentada ante `oasdiff breaking`.

### 20. Parámetros de ruta a nivel de path item en la superficie pública (CHG-API-004 / TKT-F4-009, DEC-AUTO-910)
- **Problema:** el esquema generado por el backend (`apps/core/esquema.py`, TKT-004) declara siempre los parámetros de ruta en el `parameters` del path item, como el contrato ya hacía en las rutas del panel. Las rutas públicas con parámetro de ruta los declaraban dentro de la operación `get`. El gate `oasdiff breaking --fail-on WARN` (§16) reportaba 8 avisos `request-parameter-removed`, aunque el significado es idéntico: con `--flatten-params` da 0 cambios.
- **Decisión (DEC-AUTO-910, del Orquestador):** el parámetro de ruta pasa al `parameters` del path item y se quita de la operación. Nombre, `in`, `required`, esquema (`SlugPath` → `Slug`, o el `enum` en línea) y descripción no cambian. Los parámetros de query (`Q`, `Pagina`) siguen en la operación.
- **Rutas modificadas (8, todas `GET`):**
  - `/api/v1/publico/paginas/{slug}` (`slug` en línea con `enum`, `publicoObtenerPaginaInstitucional`)
  - `/api/v1/publico/destinos/{slug}` (`SlugPath`, `publicoObtenerDestino`)
  - `/api/v1/publico/itinerarios/{slug}` (`SlugPath`, `publicoObtenerItinerario`)
  - `/api/v1/publico/tipos-aventura/{slug}` (`SlugPath`, `publicoObtenerTipoAventura`)
  - `/api/v1/publico/categorias-guia/{slug}` (`SlugPath`, `publicoObtenerCategoriaGuia`)
  - `/api/v1/publico/guias/{slug}` (`SlugPath`, `publicoObtenerGuia`)
  - `/api/v1/publico/colecciones/{slug}` (`SlugPath`, `publicoObtenerColeccion`)
  - `/api/v1/publico/busqueda/{grupo}` (`grupo` en línea con `enum`, `publicoBuscarPorGrupo`; `Q` y `Pagina` siguen en la operación)
- **Compatibilidad:** es un cambio estructural **sin efecto semántico**. OpenAPI 3.1 (Path Item Object, `parameters`) aplica los parámetros del path item a todas sus operaciones, y cada ruta tiene una sola operación. Los clientes generados y schemathesis ven la misma petición. `info.version` no cambia y no se necesita ninguna excepción ante `oasdiff`. Las rutas públicas sin parámetro de ruta y todas las del panel no cambian.

### 21. Operaciones multi-entidad del panel: co-publicación, retiro en cascada y errores por entidad (CHG-API-005 / TKT-F4-011, DEC-AUTO-265..269)
- **Origen:** CHG-BP-001 (Blueprint v1.1), que resuelve CONFLICT-005 con DEC-AUTO-912 (invariante de RULE-002, co-publicación de RULE-025, cascada de tipos, RULE-001 en relaciones) y DEC-AUTO-914 (el Orquestador ratifica la propuesta (d): los itinerarios publicados exigen todos sus tipos PUBLICADOS y la cascada de un tipo se bloquea si lo usa un itinerario publicado que no se retira en la misma operación). Todas las operaciones afectadas son del panel y las implementa **TKT-006, aún no iniciado**: ningún servidor las sirve todavía. El cliente Angular generado solo tiene los tipos y se regenera.
- **Invariante que el contrato hace verificable** (STATE-001 v1.1): tras cualquier operación confirmada, todo Destino PUBLICADO tiene su tipo principal y todos sus tipos PUBLICADOS, todo Itinerario PUBLICADO tiene todos sus tipos PUBLICADOS, y todo Tipo PUBLICADO tiene al menos 1 Destino PUBLICADO.

#### 21.1 Co-publicación (DEC-AUTO-265)
- `panelPublicarContenido` pasa de `TransicionEntrada` a **`PublicacionEntrada`** = `{version, copublicar_tipos?: [{id, version}]}` (`TipoVersionado`, máx. 12, sin ids repetidos). Es un superconjunto compatible: `{version}` sigue siendo válido. `TransicionEntrada` se mantiene para `panelReactivarContenido`.
- `copublicar_tipos` debe ser **exactamente** el conjunto de tipos del destino (incluido el principal) que están en BORRADOR. Se valida el **estado resultante**: el destino cuenta como destino publicado de cada tipo co-publicado (RULE-025), y cada tipo se valida con sus reglas propias. Todo o nada, en una transacción, con una instantánea y una auditoría PUBLICAR por entidad (AC-125). La huella de `Idempotency-Key` incluye el cuerpo (ALT-017), y la versión de **cada** entidad se comprueba (ALT-016): si alguna es obsoleta → 409 `conflicto_version` con `entidades_en_conflicto`.
- "Actualizar publicación" de un destino PUBLICADO que añade tipos en BORRADOR aplica la misma co-publicación. `DestinoActualizacion` incorpora `CamposOperacionPublicada` = `{copublicar_tipos, confirmar_cascada, cascada_confirmada}` (opcionales). Son campos de control, no se guardan, y en BORRADOR solo se admiten con su valor por defecto (si no, 400 `campo_no_permitido`).
- Respuesta: `ResultadoTransicion` añade **`entidades`** (requerido): `EntidadTransitada[]` con la principal primero y `origen` PRINCIPAL / COPUBLICACION / CASCADA, más su nueva `version` y `numero_revision`. `afectados` se mantiene y ahora también lista los tipos co-publicados. `panelActualizarDestino` devuelve **`DestinoGuardado`** = `DestinoPanel` + `entidades_afectadas` (requerido; vacío al guardar un borrador).
- Por qué la lista explícita y no una inferencia del servidor: la confirmación de SCR-038 muestra qué tipos se publicarán. Enviar la lista con versiones liga la confirmación a lo que el editor vio. Si otro editor cambió un tipo entretanto, la operación falla con 409 en lugar de publicar contenido no revisado.

#### 21.2 Errores agrupados por entidad (DEC-AUTO-266)
- Nueva respuesta **`ReglaNegocioPublicacion`** (422) con esquema **`ProblemaPublicacion`** = `ProblemaValidacion` + `errores_por_entidad: ErroresEntidad[]` (`{tipo, id, titulo, estado_editorial, rol, errores: ErrorRegla[]}`). La usan `panelPublicarContenido`, `panelActualizarDestino` y `panelActualizarItinerario`. El `code` de Problem sigue siendo `publicacion_invalida`. `errors` se mantiene por compatibilidad: claves `{campo}` para la principal y `copublicar_tipos.{id}.{campo}` para cada tipo co-publicado.
- **`ErrorRegla`** extrae el elemento de `RequisitosPublicacion.pendientes` (mismos campos) y añade `referencias: ContenidoRefPanel[]` opcional, para enlazar a otras entidades. Así, `requisitos_publicacion` de un Tipo (SCR-036) también muestra los destinos en BORRADOR (AC-126).
- Códigos por entidad (en `ErrorRegla.code`, no son `code` de Problem):

| code | Regla | Entidad / campo | `referencias` |
|---|---|---|---|
| `tipo_retirado` | RULE-002 (AC-124, AC-130): "Reactiva primero el tipo {nombre}" | principal, `tipos_ids` o `tipo_principal_id` (destino o itinerario) | el tipo |
| `tipo_no_publicado` | RULE-002 (AC-124): tipo en BORRADOR no incluido en `copublicar_tipos` | principal (destino), `tipos_ids` / `tipo_principal_id` | el tipo |
| `copublicacion_tipo_no_asociado` | id de `copublicar_tipos` que no es tipo del destino o no existe | principal, `copublicar_tipos` | — |
| `copublicacion_tipo_no_borrador` | tipo listado que ya está PUBLICADO | principal, `copublicar_tipos` | el tipo |
| `tipo_sin_destino_publicado` | RULE-025 (AC-126): publicar un tipo por sí solo con 0 destinos publicados | tipo principal, `_general` | destinos en BORRADOR con ese tipo (máx. 50) |
| `itinerario_tipo_no_publicado` | RULE-003 v1.1, DEC-AUTO-914: itinerario con algún tipo en BORRADOR (no hay co-publicación desde el itinerario) | principal (itinerario), `tipos_ids` | los tipos no publicados |

- Un id inexistente en `copublicar_tipos` se informa como `copublicacion_tipo_no_asociado` y no como 404. El 404 queda para la entidad de la ruta, y así no se revela la existencia de ids por otra vía.

#### 21.3 Análisis previo sin efectos: `panelAnalizarPublicacion` (DEC-AUTO-267, operación NUEVA)
- `POST /api/v1/panel/contenidos/{tipo}/{id}/analisis-publicacion`, cuerpo `AnalisisPublicacionEntrada` = `{version, tipos_ids?, tipo_principal_id?}` y respuesta `AnalisisPublicacion` = `{operacion, confirmable, entidad, copublicacion[], copublicar_tipos[], tipos_en_cascada[], bloqueos_cascada[]}`. Es de solo lectura: no persiste, no audita y no crea instantáneas. Requiere CSRF (es POST) y usa el perfil `panel-vista-previa`.
- **Por qué es imprescindible:** SCR-038 debe listar los tipos de "Se publicarán también" con la validación de cada uno en el **estado resultante**. Ni `requisitos_publicacion` del destino ni el de cada tipo pueden darla, porque evalúan el estado actual: el tipo diría "0 destinos publicados" y el destino, "tipo no publicado". En "Actualizar publicación", además, el impacto sobre los tipos depende de los `tipos_ids` del formulario **sin guardar**, algo que un GET sobre el estado guardado no puede evaluar. Se descartaron: (a) usar la escritura con 409/422 como vista previa, porque obliga a provocar errores para mostrar el diálogo y no da la validación de cada tipo cuando todo está bien; (b) ampliar la vista previa por tipo, porque su contrato es la forma pública del contenido.
- El resultado es orientativo. La escritura vuelve a validar todo bajo bloqueo.

#### 21.4 Retiro y actualización con cascada de tipos (DEC-AUTO-268)
- `ImpactoRetiro` añade `tipos_en_cascada` y `bloqueos_cascada` (requeridos; son adiciones en la respuesta y, por tanto, compatibles). `colecciones` y `destacados` pasan a incluir también los de las entidades en cascada. `retirable` = `bloqueos` y `bloqueos_cascada` vacíos.
- `panelRetirarContenido` retira en la **misma transacción** el destino, sus itinerarios PUBLICADOS y los tipos que quedan con 0 destinos publicados. Cada entidad recibe una instantánea y una auditoría RETIRAR. El motivo de los tipos es "Cascada: sin destinos publicados (RULE-025)" (AC-127).
- Nuevos `code` 409 en el catálogo de Problem, con cuerpo `ProblemaConUsos` ampliado con propiedades opcionales:
  - **`cascada_bloqueada`**: un tipo en cascada lo usa un itinerario PUBLICADO que no se retira en la misma operación. En el retiro es un itinerario de otro destino; al actualizar, cualquier itinerario publicado, porque la actualización no retira itinerarios. Nada cambia. `usos` (plano, compatible) y `bloqueos_cascada: BloqueoCascada[]` (tipo → itinerarios) llevan la lista (AC-128, ALT-019).
  - **`cascada_sin_confirmar`**: hay cascada y `confirmar_cascada` es false. Incluye `impacto_cascada: ImpactoCascada`.
  - **`impacto_modificado`**: el cliente envió `cascada_confirmada` (`EntidadRef[]`, nuevo campo opcional de `RetiroEntrada` y de `CamposOperacionPublicada`) y no coincide con la cascada calculada bajo bloqueo. Incluye `impacto_cascada` actualizado. Evita retirar en cascada entidades que el editor no vio (THREAT-012). Si se omite, rige el comportamiento anterior: `confirmar_cascada: true` confirma lo que haya.
- `dependencia_bloqueante` queda **solo** para los usos de RULE-007 (tipo, categoría, país, región, licencia o medio en uso por contenido publicado). Un tipo en uso por destinos publicados nunca se retira de forma directa: se retira al retirar su último destino.
- `panelReactivarContenido` solo reactiva la entidad indicada. Reactivar un destino **no** reactiva sus tipos ni sus itinerarios (AC-130), y un tipo reactivado vuelve a PUBLICADO solo por co-publicación. Queda documentado en la operación.

#### 21.5 Orden de evaluación, bloqueos y límites (DEC-AUTO-269)
- Orden: 400 formato → 403 → 404 (entidad de la ruta) → 409 `transicion_invalida` → 409 `conflicto_version` (principal y, en co-publicación, cada tipo listado y asociado) → 409 `dependencia_bloqueante` (RULE-007, retiro) → 422 `publicacion_invalida` (todas las entidades, agrupadas; publicar y actualizar) → 409 `cascada_bloqueada` → 409 `cascada_sin_confirmar` / `impacto_modificado`. Así el cliente recibe primero los errores que el editor puede corregir en el formulario.
- Concurrencia (Skill_Backend Regla 06): antes de validar, `SELECT ... FOR UPDATE` de la entidad principal y de **todos** sus tipos (y, en el retiro, de sus itinerarios publicados), siempre en orden ascendente de id para no provocar interbloqueos. La publicación y la actualización de itinerarios toman `FOR SHARE` de sus tipos. Con esto, dos retiros concurrentes de los dos últimos destinos de un tipo no pueden dejarlo PUBLICADO con 0 destinos, y una cascada no puede cruzarse con la publicación de un itinerario que use el tipo. El estado se relee de las filas bloqueadas.
- Límites: `entidades` ≤ 213 (1 + 200 itinerarios + 12 tipos). `afectados` conserva `maxItems: 200` para no cambiar la respuesta existente. Si una cascada superase 200 entidades → 422 `regla_negocio` (no ocurre con los datos del producto).

#### 21.6 Compatibilidad y excepción documentada
- **Compatibles** (adiciones): `PublicacionEntrada` (superconjunto de `TransicionEntrada`), campos opcionales en `DestinoActualizacion` y `RetiroEntrada`, propiedades nuevas en respuestas (`entidades`, `entidades_afectadas`, `tipos_en_cascada`, `bloqueos_cascada`, `errores_por_entidad`, `referencias`, y las opcionales de `ProblemaConUsos`), la nueva operación y los nuevos `code`. La extracción de `ErrorRegla` y los esquemas derivados (`ProblemaPublicacion`, `DestinoGuardado`) no cambian la forma JSON.
- **Cambios de comportamiento más restrictivos** (sin cambio de esquema): RULE-002 exige que los tipos estén PUBLICADOS o co-publicados, RULE-003 exige que los tipos de los itinerarios estén PUBLICADOS, y "Actualizar publicación" de un destino puede retirar tipos en cascada o responder `cascada_bloqueada`. Son reglas de negocio nuevas del Blueprint v1.1 sobre operaciones aún no implementadas.
- **Excepción documentada (mismo criterio que §17):** en `panelRetirarContenido`, la cascada sin confirmar pasaba de **409 `dependencia_bloqueante`** a **409 `cascada_sin_confirmar`**. El esquema no cambia (`oasdiff` no lo detecta), pero un cliente que se basara en el `code` anterior dejaría de reconocer el caso. Se acepta porque la operación **no está implementada ni desplegada** (TKT-006 pendiente) y ningún cliente depende del `code`. Separar "requiere confirmación" (el editor confirma) de "uso bloqueante de RULE-007" (el editor debe resolver otra cosa) elimina una ambigüedad del contrato. La operación lleva `x-cambio-incompatible`. No se abre `/api/v2/`, no se emite `Deprecation` e `info.version` sigue en 1.0.0. Si ya estuviera desplegada, este cambio exigiría v2.
- `info.x-cambios` se completa con CHG-API-003/004 (omitidos antes) y CHG-API-005.

#### 21.7 Lo que debe implementar TKT-006 (resumen verificable)
1. Servicio de publicación multi-entidad (destino + `copublicar_tipos`), atómico, con instantánea y auditoría PUBLICAR por entidad, validación sobre el estado resultante e idempotencia (AC-124, AC-125).
2. RULE-025 para un Tipo publicado por sí solo → `tipo_sin_destino_publicado` con `referencias`, también en `requisitos_publicacion` del Tipo (AC-126).
3. RULE-003 v1.1 en la publicación y actualización de itinerarios → `itinerario_tipo_no_publicado` / `tipo_retirado`.
4. `panelAnalizarPublicacion` sin efectos (PUBLICAR y ACTUALIZAR_PUBLICACION con `tipos_ids` propuestos).
5. Cálculo de la cascada (itinerarios + tipos con 0 destinos publicados) y de los bloqueos, compartido por `panelObtenerImpactoRetiro`, `panelRetirarContenido`, `panelAnalizarPublicacion` y `panelActualizarDestino` (AC-127, AC-128).
6. Los codes 409 `cascada_bloqueada`, `cascada_sin_confirmar`, `impacto_modificado` y `conflicto_version` con `entidades_en_conflicto`, y el orden de evaluación de §21.5.
7. Bloqueos `FOR UPDATE` / `FOR SHARE` en orden de id, y pruebas de concurrencia: dos retiros simultáneos de los dos últimos destinos de un tipo, y co-publicación concurrente del mismo tipo desde dos destinos.
8. Reactivar sin efectos sobre tipos ni itinerarios (AC-130), con una prueba del ciclo completo: retirar → reactivar el destino → publicar falla con `tipo_retirado` → reactivar el tipo → co-publicar.
9. Prueba del invariante tras cada operación confirmada (AC-127: ningún Tipo PUBLICADO con 0 destinos publicados).

## Registro DEC-AUTO-265..269 (CHG-API-005)
| ID | Decisión (elegida) | Alternativas | Motivo | Riesgo | Reversibilidad |
|---|---|---|---|---|---|
| DEC-AUTO-265 | Co-publicación como extensión compatible de `panelPublicarContenido` (`PublicacionEntrada.copublicar_tipos` = lista exacta de tipos en BORRADOR con versión) y de `panelActualizarDestino` (`CamposOperacionPublicada`). La respuesta enumera todas las entidades (`entidades`, `entidades_afectadas`) | Inferir los tipos en el servidor sin lista; operación nueva `publicar-con-tipos`; publicar los tipos en llamadas separadas | Liga la confirmación a lo que el editor vio (ALT-016), es todo o nada (AC-125) y reutiliza la ruta, la idempotencia y el cliente | El cliente debe enviar la lista exacta (la obtiene de `panelAnalizarPublicacion`) | Alta |
| DEC-AUTO-266 | `ProblemaPublicacion` (422) con `errores_por_entidad` y `ErrorRegla` compartido con `requisitos_publicacion` (+`referencias`). Los códigos por entidad van en `ErrorRegla.code`: `tipo_retirado`, `tipo_no_publicado`, `copublicacion_tipo_no_asociado`, `copublicacion_tipo_no_borrador`, `tipo_sin_destino_publicado`, `itinerario_tipo_no_publicado` | Solo el mapa `errors` con prefijos; nuevos `code` de Problem por caso; un 409 para el tipo retirado | Agrupación por entidad (FLOW-011 6a') sin romper `errors` ni el `code` publicacion_invalida; enlaces a entidades (AC-126, SCR-038) | Duplicación de información entre `errors` y `errores_por_entidad` (el cliente usa la segunda) | Alta |
| DEC-AUTO-267 | Operación nueva `panelAnalizarPublicacion` (POST, sin efectos) para el diálogo de publicar y de actualizar publicación | Usar la escritura con 409/422 como vista previa; ampliar la vista previa por tipo; GET sobre el estado guardado | Solo así se obtiene la validación de cada tipo en el estado resultante y el impacto de los `tipos_ids` sin guardar | Resultado desfasado si otro editor actúa entretanto (la escritura revalida bajo bloqueo; `impacto_modificado` / `conflicto_version`) | Alta |
| DEC-AUTO-268 | `ImpactoRetiro` + `tipos_en_cascada` / `bloqueos_cascada`. La cascada de tipos es atómica en retirar y en actualizar. Codes 409 `cascada_bloqueada`, `cascada_sin_confirmar` (sustituye a `dependencia_bloqueante` en ese caso, excepción §21.6) e `impacto_modificado` con `cascada_confirmada` opcional | Mantener `dependencia_bloqueante` para todo; 422 para el bloqueo; confirmar solo con el booleano | Distingue "confirmar" de "resolver otra cosa". El bloqueo es un conflicto de estado (409, como pide el ticket). Evita retirar entidades no vistas (THREAT-012) | Cambio de `code` en una operación no implementada (documentado) | Alta |
| DEC-AUTO-269 | Orden de evaluación fijo; `FOR UPDATE` del principal, sus tipos (e itinerarios al retirar) en orden de id; `FOR SHARE` de los tipos al publicar o actualizar itinerarios; límite de 200 entidades en cascada → 422 `regla_negocio` | Bloqueo optimista solo por versión; `SERIALIZABLE` con reintentos; sin límite | Hace determinista el contrato para QA/schemathesis y garantiza el invariante bajo concurrencia sin interbloqueos | Más contención en tipos muy usados (bajo: equipo ≤5, ASM-003) | Alta |

## Registro DEC-AUTO-910 (CHG-API-004)
| ID | Decisión (elegida) | Alternativas | Motivo | Riesgo | Reversibilidad |
|---|---|---|---|---|---|
| DEC-AUTO-910 | Parámetros de ruta de las 8 rutas públicas con `{slug}`/`{grupo}` declarados en el path item, no en la operación | Cambiar `esquema.py` para emitirlos por operación; ejecutar `oasdiff` con `--flatten-params` en el gate; bajar el gate a `--fail-on ERR` | Una sola convención en todo el contrato, igual que el panel y el generador; no se cambia código ni se relaja el gate | Nulo en tiempo de ejecución; un editor futuro podría volver a declararlos por operación (el gate lo detectaría) | Alta |

## Registro DEC-AUTO-903 / DEC-AUTO-905 (CHG-API-003)
| ID | Decisión (elegida) | Alternativas | Motivo | Riesgo | Reversibilidad |
|---|---|---|---|---|---|
| DEC-AUTO-905 | `DiaEntrada.titulo` (string, minLength 1, maxLength 150) y `DiaEntrada.actividades` (string) requeridos y no nullable, como las columnas NOT NULL de `dia_itinerario` | Hacer las columnas NULL en BD (CHG-DB); que el servicio convierta null en `""` | Contrato = BD; schemathesis deja de enviar null que la BD rechaza con 5xx; la salida `DiaItinerario` ya lo exigía | El editor no puede guardar un día vacío en borrador (el Frontend no envía días sin título) | Alta |
| DEC-AUTO-903 | `maxLength: 100000` en `TextoEnriquecido` y en los 9 campos HTML de entrada que declaraban 200000; se mantienen los límites menores (50000, 5000); límite comprobado tras el saneado → 400 `validacion` | Subir el CHECK de BD a 200000 (migración + ADR-DB); dejar el contrato y traducir la violación del CHECK a 400 | Una sola fuente de verdad (DEC-AUTO-097); schemathesis deja de generar entradas que la BD rechaza; no toca la BD ya migrada ni nginx | Un texto enriquecido real de más de 100000 caracteres sería rechazado (improbable: ≫ el contenido experto previsto, ADR-DB-002 §6) | Alta (subir los dos límites a la vez con CHG coordinado API + BD) |

## Registro DEC-AUTO-216..219 (CHG-API-002)
| ID | Decisión (elegida) | Alternativas | Motivo | Riesgo | Reversibilidad |
|---|---|---|---|---|---|
| DEC-AUTO-216 | Documentar 429 `limite_tasa` del proxy de borde en `/health/live` y `/health/ready` con una respuesta propia `LimiteTasaBorde`; no documentar 404 | Reutilizar `LimiteTasa` (descrita como DRF); documentar también 404 | Refleja RSK-OPS-020 (50 r/s, burst 200) sin confundirlo con los perfiles DRF; 404 solo en rutas inexistentes | Un sondeo mal configurado podría tratar el 429 como caída (mitigado: zona holgada y nota en el contrato) | Alta |
| DEC-AUTO-217 | NUL prohibido: `pattern: '^[^\u0000]*$'` en los textos de entrada + norma general en `info` | Solo una nota normativa; `x-` propio; no documentarlo | schemathesis respeta `pattern` y deja de generar NUL; los clientes generados pueden validar | Olvidar el patrón en campos nuevos (mitigado por la norma general) | Alta |
| DEC-AUTO-218 | Reautenticación en `panelIniciarActivacionMfa`: fallo → 401 `credenciales_invalidas` (sin cerrar la sesión), cuenta para el bloqueo de RULE-017 y se audita `LOGIN_FALLIDO`; MFA ya activo → 409 `transicion_invalida` | 400 `validacion` para la contraseña errónea; un code nuevo `reautenticacion_fallida`; exigir la contraseña en `confirmar` | Reutiliza el catálogo; la semántica del 401 es "credencial incorrecta"; el contador compartido evita la fuerza bruta por sesión robada | El Frontend podría interpretar el 401 como sesión expirada si no distingue por `code` (documentado) | Alta |
| DEC-AUTO-219 | 409 `idempotencia_respuesta_no_reproducible` generalizado a las 11 operaciones (respuesta >64 KB no guardada); `Location` solo en `panelCrearCuenta` | Guardar respuestas grandes; devolver 200 sin cuerpo | Alinea el contrato con `apps/core/idempotencia.py` y DEC-AUTO-128 | Los clientes deben releer el recurso tras este 409 | Alta |

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
