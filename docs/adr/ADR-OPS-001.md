# ADR-OPS-001 — Limitador de borde: zona propia para los assets estáticos y X-Robots-Tag del panel

| Campo | Valor |
|---|---|
| Estado | ACCEPTED para TKT-OPS-016 (QA PASS, integrado en `main` por el PR #38 @ e75ee7a). Revisión TKT-OPS-019: PROPOSED (pendiente de QA y de la integración por el Orquestador) |
| Fecha | 2026-09-30 |
| Ticket | TKT-OPS-016 (HIGH, condición de F9). Alcance ampliado por DEC-AUTO-929: X-Robots-Tag del panel. Revisión: TKT-OPS-019 (LOW, hallazgos F-1/F-2 de la QA de TKT-OPS-016) |
| Autor | Skill_devops |
| Trazabilidad | TKT-018 (QA F-3), DEC-AUTO-111, DEC-AUTO-190, DEC-AUTO-193, DEC-AUTO-195, DEC-AUTO-214, DEC-AUTO-929; ADR-API-002 §9; BLUEPRINT THREAT-009 (agotamiento por consultas costosas), THREAT-015, THREAT-020, RULE-029; RSK-OPS-016, RSK-OPS-022; REQ-052, REQ-057 |
| Archivos | `infra/proxy/nginx.conf` |

## Contexto
- [OBSERVADO] El borde nginx aplica `limit_req zone=por_ip` (20 r/s, burst 60, `nodelay`, clave `$binary_remote_addr`) a todo el servidor salvo `/health/live|ready` (zona `salud`, DEC-AUTO-214). Es defensa en profundidad: el límite fino lo aplica DRF por perfil (DEC-AUTO-111, ADR-API-002 §9).
- [MEDIDO, línea base sobre `origin/main` @ 1bf5e94] Una carga en frío de Inicio seguida de una navegación genera unas 35 peticiones de assets por visitante: chunks JS/CSS con hash, fuentes y derivados de `/media/publico/**`. Más 1-3 de HTML y API. Medición: 2 o 3 contextos Chromium fríos simultáneos desde la misma IP, clic a los 300 ms, 2 series de 5 rondas.
  - N=2: 1/10 y 0/10 navegaciones rotas, 35 respuestas 429.
  - N=3: 15/15 y 13/15 navegaciones rotas, 219 respuestas 429.
  - Los 429 caen sobre `chunk-*.js` y `/media/publico/**`. El router de Angular falla con "Failed to fetch dynamically imported module" y nunca completa la navegación.
- [HECHO] Detrás de un NAT, un CGNAT o la red de una oficina, muchos visitantes legítimos comparten IP. El frontend no puede reducir más las peticiones de una carga en frío: TKT-018 ya difirió las imágenes fuera del viewport.
- [OBSERVADO] Los assets del build los sirve `express.static` dentro del SSR. Un asset **inexistente** (p. ej. `/no-existe-123.js`) cae al motor de Angular, que **renderiza** la página 404 (HTML 404, unos 40 ms). Si se sacara a ciegas `/*.js` del cupo `por_ip`, cualquiera podría pedir renders del SSR ilimitados con nombres inventados. Eso es justo el agotamiento de recursos que el limitador previene.
- [OBSERVADO] `AngularNodeAppEngine` (Angular 22.2) valida el Host contra `NG_ALLOWED_HOSTS` **antes** de renderizar. Con un Host no permitido responde `400 text/plain` en unos 6 ms, sin renderizar (protección SSRF de Angular). `express.static` no mira el Host.

## Alternativas
| # | Alternativa | Pros | Contras |
|---|---|---|---|
| A | Subir `por_ip` (p. ej. burst 300) para todo | Cambio de una línea | Multiplica por 5 los renders SSR y las llamadas a `/api` que admite una IP. Debilita justo lo que hay que proteger (THREAT-009) |
| B | Excluir los assets de cualquier límite | Cero 429 en assets | Ancho de banda sin tope por IP. Los assets inexistentes **renderizan** en el SSR sin límite (evasión) |
| C | nginx sirve el build directamente (volumen compartido o `COPY --from` de la imagen del frontend) | Los inexistentes son un 404 de nginx, sin tocar el SSR | Cambia `compose.yaml` y acopla las imágenes proxy↔frontend. Fuera de los `archivos_permitidos` del ticket y del cambio mínimo. Queda como evolución para producción (CDN, ver Riesgos) |
| D | Zona propia generosa para los assets, que siguen pasando por el SSR, sin defensa ante inexistentes | Simple | Inexistentes = render SSR con el cupo generoso (50 r/s en lugar de 20 r/s): evasión parcial. Incumple AC_OPS016_03 |
| **E (elegida)** | **Zona `estaticos` propia + Host inválido hacia el SSR en la location de assets** | Cero 429 legítimos. `/api/**` y HTML intactos en `por_ip`. Un asset inexistente nunca se renderiza (400 de Angular → 404 Problem Details del proxy). Solo cambia `nginx.conf` | Depende de que `NG_ALLOWED_HOSTS` nunca admita `*` (RSK-OPS-040). Cada inexistente produce 4 líneas de error en el log del SSR tras TKT-OPS-019; 8 antes (RSK-OPS-041) |

## Decisión
1. **Nueva zona** `limit_req_zone $binary_remote_addr zone=estaticos:10m rate=50r/s`, aplicada con `burst=300 nodelay` en:
   - la location regex de assets del build: `^/(?:[A-Za-z0-9_-]+\.(?:js|mjs|css)|fonts/[A-Za-z0-9_-]+\.woff2|favicon\.ico)\z` (ancla `\z` desde TKT-OPS-019, ver punto 7). Solo archivos en la raíz, que es donde Angular emite `main-*`, `chunk-*`, `polyfills-*` y `styles-*`, más las fuentes y el favicon;
   - `location /media/publico/`, que sirve nginx desde el volumen. Un inexistente es un 404 de nginx, sin upstream.
   - Un `limit_req` en la location anula el heredado del servidor: estos assets **ya no consumen** el cupo `por_ip`.
   - Dimensionado: burst 300 cubre unas 8 cargas en frío simultáneas tras una misma IP. 50 r/s repone una carga en frío completa cada 0,7 s.
2. **`por_ip` sin cambios** (20 r/s, burst 60) para `/api/**`, el HTML del SSR y **cualquier otra ruta**: subdirectorios (`/destinos/x.js`), `.html` y similares. `salud` sin cambios.
3. **Defensa contra la evasión por assets inexistentes** (AC_OPS016_03):
   - La location de assets envía al SSR `Host: estaticos.invalid` (TLD reservado, RFC 2606). No incluye `proxy-headers.conf`. Desde TKT-OPS-019 ya no envía `X-Forwarded-Host` ni `X-Forwarded-Proto` (punto 7).
   - Si el archivo existe, lo sirve `express.static`. Si no existe, Angular rechaza el Host con 400 **sin renderizar**.
   - Con `proxy_intercept_errors on`, el 400/404 del upstream sale como `404 no_encontrado` Problem Details. Se redefinen los `error_page` 403/429/5xx de la location, porque nginx no hereda los del servidor si la location define alguno.
4. **Sin regresión de cabeceras**: la location de assets mantiene el tratamiento que tenían en `location /`:
   - oculta CSP, `X-Powered-By` y `Cache-Control` del upstream;
   - fija `Cache-Control $cache_control_ssr`, que conserva el `immutable` de los archivos con hash;
   - incluye `snippets/security-headers-html.conf`.
   - gzip, ETag/304 y `limit_except GET HEAD` siguen igual.
5. **Log**: nuevo campo `ruta_pedida` en `brujula_json`. Es la ruta original **sin query string** (corte en el primer `?`, THREAT-020/REQ-057). `ruta` (`$uri`) registraba los 429 como `/_errores_proxy/429` y no permitía saber qué recurso se había limitado.
6. **X-Robots-Tag del panel** (DEC-AUTO-929, RULE-029):
   - `map $uri $x_robots_borde` vale `"noindex, nofollow"` para `/panel` y `/panel/**`, y está vacío en el resto. Con valor vacío nginx no emite la cabecera.
   - Se aplica con `add_header ... always` en `location /`, junto a las cabeceras de seguridad, que ya estaban en esa misma location. No cambia la herencia de `add_header`.
   - Las rutas públicas no la reciben.

7. **Revisión TKT-OPS-019** (hallazgos F-1/F-2 de la QA de TKT-OPS-016):
   - **Sin query hacia el SSR** (F-1; REQ-057, THREAT-020): la location de assets usa `proxy_pass http://frontend$uri`. Con una variable en `proxy_pass`, nginx envía esa URI tal cual y no añade `$args`. Antes, un asset inexistente con query dejaba la URL completa en el log del SSR (`ERROR: Bad Request ("http://estaticos.invalid/qaB.js?x=1")`).
   - **Por qué `$uri` es seguro aquí**: `$uri` es la ruta ya decodificada y normalizada por nginx (sin `.`/`..` ni barras dobles) contra la que se evalúa la regex de la location. La regex solo admite `[A-Za-z0-9_-]`, `/` y `.` en posiciones fijas, así que no hay `%`, `?`, `#`, espacios ni caracteres de control que recodificar. `frontend` es el `upstream` declarado: no hay resolución DNS en tiempo de ejecución y se conserva `keepalive`.
   - **Ancla `\z` en lugar de `$`**: verificado en la revisión que, en PCRE, `$` también casa antes de un salto de línea final. `/x.js%0A` (cuyo `$uri` termina en `
`) entraba en la location; con `proxy_pass $uri` ese `
` habría viajado crudo en la línea de petición hacia el SSR (medido con `$`: 404 sin pasar por Angular, con `upstream_s` > 0, es decir, Node rechazó una petición mal formada). Con `\z` esa ruta queda fuera del patrón y sigue el camino general (`location /`, zona `por_ip`), igual que `/x.js%20` o `/x.JS`.
   - **Sin `X-Forwarded-Host` ni `X-Forwarded-Proto`** (F-2): Angular 22.2 los ignora sin `trustProxyHeaders` (la validación SSRF usa solo `Host`) y cada uno escribía 2 avisos por asset inexistente. `express.static` tampoco los usa (`trust proxy` desactivado). `X-Request-Id` y `traceparent` se mantienen (correlación de un posible `error_ssr`).

## Consecuencias y riesgos
| ID | Riesgo | Sev. | Mitigación | Estado |
|---|---|---|---|---|
| RSK-OPS-040 | Si un entorno configura `NG_ALLOWED_HOSTS` con `*` o `*.invalid`, un asset inexistente vuelve a renderizar en el SSR con el cupo `estaticos` (50 r/s, burst 300) en vez de `por_ip`: evasión parcial, acotada | MEDIUM (si se configura mal) | Requisito operativo documentado en `nginx.conf` y en DEVOPS_HANDOFF §23. Verificación: `curl /no-existe-x.js` debe tardar unos ms y el log del SSR debe mostrar `Header "host" with value "estaticos.invalid" is not allowed`. Recomendado: smoke de CI (ticket, `.github/workflows` fuera de este alcance) | ABIERTO (ticket CI) |
| RSK-OPS-041 | Cada asset inexistente escribe líneas de error en el log del SSR. MEDIDO: 8 líneas por petición con la versión de TKT-OPS-016 (no ~3, como se estimó: 2 avisos por `X-Forwarded-Host`, 2 por `X-Forwarded-Proto` y 4 del rechazo de Host, una de ellas en blanco); **4 líneas** tras TKT-OPS-019 (solo el bloque `ERROR: Bad Request ("http://estaticos.invalid/<ruta>")` + `Header "host" … is not allowed` + línea en blanco + enlace). Un atacante puede inflar el log (hasta 50 r/s por IP, más el burst) | LOW | Rotación json-file de 10 MB × 5 ya activa. Los logs centralizados de producción deben filtrar o muestrear este mensaje | ACEPTADO |
| RSK-OPS-042 | Ancho de banda: una IP puede descargar assets a 50 r/s (unos 5-20 MB/s según el asset) | LOW (local) / MEDIUM (prod) | En producción, CDN o caché de borde delante de los assets inmutables (ADR de producción, F9). Junto con RSK-OPS-022 (`real_ip` tras un balanceador) | ABIERTO (F9) |
| RSK-OPS-043 | Un CGNAT muy grande (más de unas 8 cargas en frío por segundo tras una misma IP) aún podría recibir 429 en assets | LOW | Burst 300 medido con margen (N=8 simultáneos: 0 rotas). En producción, el CDN absorbe los assets. Recalibrar con métricas reales | ACEPTADO |
| — | `return 404` de `/media/` y de `/media/publico/` (extensión no permitida) se ejecuta en la fase rewrite, antes de `limit_req`: no consume cupo | INFO | Preexistente. Es un 404 de nginx sin upstream, coste despreciable | SIN CAMBIO |

## Evidencia (local, Docker Engine 29.6.1, Compose v5.2.0, stack real con `cargar_semilla`)
| Medición | Antes (main @ 1bf5e94) | Después |
|---|---|---|
| N=2, serie 1 / serie 2 (10 navegaciones cada una) | 1 / 0 rotas; 18 / 17 respuestas 429 (33 de 35 en assets) | 0 / 0 rotas; 0 / 0 respuestas 429 (navegador y log del proxy) |
| N=3, serie 1 / serie 2 (15 navegaciones cada una) | 15 / 13 rotas; 112 / 107 respuestas 429 (todas en assets) | 0 / 0 rotas; 0 / 0 respuestas 429 |
| Holgura: N=5 (15 navegaciones), N=8 (24 navegaciones) | — | 0 rotas; 0 respuestas 429 |
| Ráfaga de 200 a `/api/v1/publico/destinos` | — | 61 × 200, 139 × 429 (por_ip intacto) |
| Ráfaga de 200 a `/` y a `/destinos` (SSR) | — | 62 y 61 × 200, 138 y 139 × 429 |
| 200 / 400 assets inexistentes con nombres únicos | render SSR (HTML 404) por petición | 200 × 404; 307 × 404 + 93 × 429. 0 renders (507 rechazos de Host en el log del SSR, 0 `error_ssr`) |
| 250 assets y a la vez 50 a `/api` | — | 300 × 200 (los assets no consumen cupo de `/api`) |
| `/api/v1/publico/x.js`, `/destinos/x.js`, `/x.html` (150 cada una) | — | 61-62 × 404 y 88-89 × 429 (siguen en por_ip) |

### Evidencia de la revisión TKT-OPS-019 (local, 2026-10-01, Docker Engine 29.6.1, Compose v5.2.0, proyecto `ops019`)
A/B cambiando solo el contenedor `proxy` (imagen de `main` @ 7df7c77 frente a la de la rama) sobre el mismo stack.
| Medición | `main` | TKT-OPS-019 |
|---|---|---|
| `"secreto"` en los logs tras `/no-existe.js?secreto=1`, `.css`, `/fonts/x.woff2`, `/media/publico/x` (con `?secreto=1`) | SSR: 3, proxy: 0 | SSR: 0, proxy: 0 |
| Líneas del log del SSR por asset inexistente | 8 | 4 |
| 400 inexistentes únicos con query (20 conexiones keep-alive) | — | 313 × 404 + 87 × 429 Problem Details; 1252 líneas de SSR (4 × 313), 313 rechazos de Host, 0 `error_ssr`, 0 apariciones del token, 0 peticiones al backend |
| Matriz de evasión (37 variantes: `.js/.css/.mjs`, `/fonts`, `/media/publico`, `?x=1`, `?` vacía, `%2e`/`%2E`, `%2f`, `..%2f`, `/../`, `/./`, `//`, `///fonts//`, `%0A`, `%0D%0A`, `%00`, `%3F`, `%23`, `%20`, `.JS`, `;x=1`, POST/PUT/DELETE/PATCH/OPTIONS/TRACE, Host y X-Forwarded-*/Forwarded manipulados, forma absoluta) | 0 `error_ssr`, 0 peticiones al backend | Idéntica salvo `%0A` (ver punto 7): 0 `error_ssr`, 0 peticiones al backend, las rutas del patrón llegan al SSR sin query y con la ruta normalizada |
| Assets existentes (`main-*.js`, `styles-*.css`, `chunk-*.js`, fuente, favicon) con y sin `?v=1`, identity y gzip | 20 × 200; 304 con `If-None-Match`; gzip en JS/CSS; `immutable` en los que llevan hash | Cabeceras normalizadas **idénticas** a `main` (`diff` vacío; solo se sustituyen Date, nonce y valor de ETag) |

## Reversibilidad
Alta. Se revierte el commit de `infra/proxy/nginx.conf` y se reconstruye la imagen del proxy. No afecta a datos, contrato ni esquema.
