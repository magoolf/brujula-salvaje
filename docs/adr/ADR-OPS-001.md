# ADR-OPS-001 — Limitador de borde: zona propia para los assets estáticos y X-Robots-Tag del panel

| Campo | Valor |
|---|---|
| Estado | PROPOSED (pendiente de QA y de la integración por el Orquestador) |
| Fecha | 2026-09-30 |
| Ticket | TKT-OPS-016 (HIGH, condición de F9). Alcance ampliado por DEC-AUTO-929: X-Robots-Tag del panel |
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
| **E (elegida)** | **Zona `estaticos` propia + Host inválido hacia el SSR en la location de assets** | Cero 429 legítimos. `/api/**` y HTML intactos en `por_ip`. Un asset inexistente nunca se renderiza (400 de Angular → 404 Problem Details del proxy). Solo cambia `nginx.conf` | Depende de que `NG_ALLOWED_HOSTS` nunca admita `*` (RSK-OPS-040). Cada inexistente produce 3 líneas de error en el log del SSR (RSK-OPS-041) |

## Decisión
1. **Nueva zona** `limit_req_zone $binary_remote_addr zone=estaticos:10m rate=50r/s`, aplicada con `burst=300 nodelay` en:
   - la location regex de assets del build: `^/(?:[A-Za-z0-9_-]+\.(?:js|mjs|css)|fonts/[A-Za-z0-9_-]+\.woff2|favicon\.ico)$`. Solo archivos en la raíz, que es donde Angular emite `main-*`, `chunk-*`, `polyfills-*` y `styles-*`, más las fuentes y el favicon;
   - `location /media/publico/`, que sirve nginx desde el volumen. Un inexistente es un 404 de nginx, sin upstream.
   - Un `limit_req` en la location anula el heredado del servidor: estos assets **ya no consumen** el cupo `por_ip`.
   - Dimensionado: burst 300 cubre unas 8 cargas en frío simultáneas tras una misma IP. 50 r/s repone una carga en frío completa cada 0,7 s.
2. **`por_ip` sin cambios** (20 r/s, burst 60) para `/api/**`, el HTML del SSR y **cualquier otra ruta**: subdirectorios (`/destinos/x.js`), `.html` y similares. `salud` sin cambios.
3. **Defensa contra la evasión por assets inexistentes** (AC_OPS016_03):
   - La location de assets envía al SSR `Host: estaticos.invalid` (TLD reservado, RFC 2606) y `X-Forwarded-Host` igual. No incluye `proxy-headers.conf`.
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

## Consecuencias y riesgos
| ID | Riesgo | Sev. | Mitigación | Estado |
|---|---|---|---|---|
| RSK-OPS-040 | Si un entorno configura `NG_ALLOWED_HOSTS` con `*` o `*.invalid`, un asset inexistente vuelve a renderizar en el SSR con el cupo `estaticos` (50 r/s, burst 300) en vez de `por_ip`: evasión parcial, acotada | MEDIUM (si se configura mal) | Requisito operativo documentado en `nginx.conf` y en DEVOPS_HANDOFF §23. Verificación: `curl /no-existe-x.js` debe tardar unos ms y el log del SSR debe mostrar `Header "host" with value "estaticos.invalid" is not allowed`. Recomendado: smoke de CI (ticket, `.github/workflows` fuera de este alcance) | ABIERTO (ticket CI) |
| RSK-OPS-041 | Cada asset inexistente escribe unas 3 líneas `ERROR: Bad Request` en el log del SSR. Un atacante puede inflar el log (hasta 50 r/s por IP, más el burst) | LOW | Rotación json-file de 10 MB × 5 ya activa. Los logs centralizados de producción deben filtrar o muestrear este mensaje | ACEPTADO |
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

## Reversibilidad
Alta. Se revierte el commit de `infra/proxy/nginx.conf` y se reconstruye la imagen del proxy. No afecta a datos, contrato ni esquema.
