# Informe de Entrega — Brújula Salvaje

> F10 (CLAUDE.md §0.4, §0.6). Fecha: 2026-10-13. Repositorio: https://github.com/magoolf/brujula-salvaje (`main`).
> Fuentes de verdad: `kanban.md`, `audit_log.md`, `docs/05_operacion/DEVOPS_HANDOFF.md`, auditoría de seguridad en `~/security-audit-skill/brujula-salvaje/run-1/`.

## 1. Veredicto

**Estado: COMPLETADO en entorno local. NO desplegado en producción.** La publicación es una Puerta Humana (§0.5) y queda pendiente de las decisiones del §8.

- **Qué es:** portal editorial de viajes de aventura en español, pensado para Colombia (Ley 1581).
  - 24 destinos con itinerarios día a día, guías, tipos de aventura, colecciones, glosario, búsqueda, mapa, «cuándo ir», páginas legales y créditos.
  - Panel editorial `/panel` con inicio de sesión por pasos y MFA para administradores, editores, medios, taxonomías, configuración, cuentas y auditoría.
- **Stack** (fijado por los Contratos Técnicos):
  - Angular 22 con SSR;
  - Django 5.2 con DRF;
  - PostgreSQL 18;
  - nginx;
  - Docker Compose.
- **Cómo verlo en local:** `docker compose -p brujulalocal up -d` y abrir http://localhost:8080. El panel está en http://localhost:8080/panel.
- **Tickets:**

  | Grupo | Total | DONE |
  |---|---|---|
  | Todos | 130 | 113 (+1 RESUELTO) |
  | HIGH/MEDIUM antes de la entrega | 23 | 23 |

  Los 16 LOW/INFO están aplazados como `BLOCKED_HUMAN` (§6).
- **Volumen de trabajo:** 103 PR integrados con CI obligatorio en verde, unos 950 commits y unas 254 decisiones autónomas registradas (`DEC-AUTO-*`).

## 2. Decisiones del usuario (Puertas Humanas y preferencias)

| Fecha | Decisión |
|---|---|
| 2026-09-27 | RSK-OPS-001: se aceptan 16 CVE de Debian sin parche en `.trivyignore`. **Caducan el 2026-10-26**: a partir de ese día el CI fallará hasta que se decida de nuevo. |
| 2026-10-09 | E2E y QA solo en Chromium (Firefox/WebKit = NOT_RUN por decisión humana). |
| 2026-10-11 | TKT-OPS-009: se integra con el riesgo RSK-OPS-053 (búsqueda adversarial de evasiones del guardia de trivy NOT_RUN). |
| 2026-10-12 | Auditoría de seguridad F9 con perfil **quick** en lugar de *standard* (por tiempo). |
| 2026-10-12 | Las mediciones de rendimiento pueden hacerse con el portátil en batería; se anotan las condiciones. |
| — | Alcance cerrado: solo HIGH/MEDIUM antes de la entrega; los LOW/INFO pasan a post-entrega. |

## 3. Decisiones autónomas

Todas están en `audit_log.md` con la etiqueta `ORIGEN: EXPANSIÓN_AUTÓNOMA`, alternativas, riesgo y reversibilidad. Estas son las más relevantes para quien herede el sistema:

- **Arquitectura:** sesión del panel propia en BD (cookie de ruta `/api/v1/panel/`), denegación por defecto, CSRF por cabecera, idempotencia por cuenta, throttling con claves HMAC e IP truncada, auditoría inmutable para `app_rw` y libro de anonimizaciones fuera de la BD para la Ley 1581.
- **Medios** (DEC-AUTO-044, 1310-1324):
  - recodificación sin EXIF/GPS/XMP/ICC y derivados AVIF/WebP/JPEG;
  - presupuesto de peso AVIF de 0,15 B/px;
  - derivado máximo de 2560 px;
  - procesamiento fuera de la transacción;
  - el panel sube un archivo por petición.
- **Infraestructura** (DEC-AUTO-1330-1372):
  - los cuerpos de subida van a disco y no a memoria;
  - `limit_conn` de 2 subidas por IP, sin tope global;
  - backend con 2 GiB sin swap y la regla «≥ 640 MiB × workers» comprobada en el CI;
  - frontend con IP fija y `x-forwarded-for` de confianza solo desde el proxy y el SSR.
- **Rendimiento:** LCP móvil ≤ 2,5 s en los listados (TKT-021/071): preload solo de Source Sans y la imagen LCP servida desde el SSR.

## 4. Fallos encontrados y corregidos

- **QA (35 ciclos FAIL en total):** todos se corrigieron dentro del límite de 3 ciclos o se escalaron como Puerta Humana. Los últimos de esta sesión:

  | Ticket | Fallo | Corrección |
  |---|---|---|
  | TKT-071 (HIGH, regresión) | La subida de fotos de unos 8 MP por el panel daba 500 por *idle-in-transaction*. | El procesamiento se hace antes de abrir la transacción. |
  | TKT-072 | Fotos de 17 a 40 MP: entre 2 y 7 min y corte de gunicorn. | Ahora tardan unos 9 s. Los lotes de 10 fotos funcionan. |
  | TKT-OPS-034 | El proxy respondía 413 en HTML en lugar de 503 en Problem Details. | Corregido. |
  | TKT-OPS-035 | Tres subidas anónimas de 104 MB tumbaban la web por falta de memoria en el proxy. | Corregido. |
  | TKT-OPS-036 | Tres subidas simultáneas de 40 MP provocaban OOM de un worker. | Corregido. |
  | TKT-OPS-037 | Un goteo anónimo desde 8 IP bloqueaba todas las subidas del panel. | Corregido. |
  | TKT-OPS-038 (auditoría) | Con 60 páginas por minuto entre todos los visitantes, toda la web pública mostraba el error de límite. Había dos causas: Angular descartaba XFF y el backend no confiaba en el SSR. | Corregido y validado con una prueba A/B. |

- **Auditoría de seguridad F9** (perfil quick, solo fuente):
  - 0 vulnerabilidades confirmadas;
  - 1 *needs_validation*, ya validado y corregido en TKT-OPS-038;
  - unas 25 notas de endurecimiento (§6.3).

## 5. Riesgos residuales

| ID | Riesgo | Nivel | Tratamiento |
|---|---|---|---|
| RSK-OPS-001 | 16 CVE de Debian aceptadas en `.trivyignore`, incluida libxml2 CRITICAL en la imagen de la BD. Caducan el **2026-10-26**. | ALTO al caducar | Decisión humana: renovar o esperar al parche. |
| OBS-OPS036-01 | Tres subidas simultáneas de 40 MP ocupan los 3 workers síncronos durante 25-60 s y la web pública espera en cola (p50 de 25 s, sin errores). | MEDIUM | DEC-AUTO-1009. Solución de arquitectura posterior: procesamiento asíncrono o un pool dedicado. |
| RSK-OPS-065 | Sin `real_ip`: detrás de un balanceador en producción, todos los clientes compartirían cupo. | MEDIUM en producción | Puerta Humana de producción. |
| RSK-OPS-053 | Búsqueda adversarial de evasiones del guardia de trivy NOT_RUN. | MEDIUM | Aceptado por el usuario (2026-10-11). |
| RSK-OPS-060 | Los temporales de subida van al disco del host. Hasta 2 × 105 MB por IP sin tope global; con IPv6 /64 el límite por IP se puede eludir. | LOW | WAF/CDN y cuota de volumen en producción. |
| RSK-OPS-063/064/066 | Memoria retenida por glibc tras subidas grandes; temporales de workers matados; agotamiento con unas 16 000 conexiones lentas. | LOW | Documentados en DEVOPS_HANDOFF §39-§40. |
| OBS-QA038-01 | Un contenedor ya comprometido en la red interna podría falsificar XFF a través del SSR. | LOW | Que el SSR solo reenvíe XFF si el peer es el proxy. |
| F-QA071-02 | Archivos huérfanos en `privado/` si la BD revierte después de escribir. | LOW | Post-entrega. |
| Auditoría parcial | Perfil quick y una unidad diferida: «acceso anónimo solo a contenido publicado». | — | **Ejecutar el perfil standard antes de producción.** |
| GAP-004 | Responsable del tratamiento (Ley 1581) sin definir; hay un marcador en la política. | HIGH para producción | Decisión humana. |
| GAP-008 | Sin revisión humana experta del contenido de aventura. | MEDIUM | Revisión antes de publicar. |

## 6. Trabajo aplazado (post-entrega, sin bloquear)

### 6.1 Tickets LOW/INFO en `BLOCKED_HUMAN` (16)
TKT-026, TKT-028, TKT-029, TKT-036, TKT-038, TKT-039, TKT-046, TKT-053, TKT-054, TKT-055, TKT-059, TKT-066, CHG-API-007, TKT-OPS-023, TKT-OPS-030 y TKT-OPS-032. El detalle de cada uno está en `kanban.md`.

### 6.2 Observaciones de QA sin ticket
OBS-QA021-02 (target-size de los marcadores del mapa a 412 px, preexistente), OBS-QA070-01, INFO-QA070-02/03, OBS-QA072-02..05, OBS-QA034-01, O-035-02, OBS-OPS038-01/02 y OBS-QA071-04.

### 6.3 Endurecimiento propuesto por la auditoría
- `isdigit()` acepta dígitos Unicode en la paginación y en `ArchivoMedio`: devuelve 500 en lugar de 400.
- La comprobación CSRF parsea el multipart antes de verificar la sesión.
- Pasar `formats=` en `Image.open`.
- Usar MultiFernet y una clave separada para los códigos de recuperación.
- Invalidar las otras sesiones al cambiar el MFA.
- Fijar por digest `# syntax=docker/dockerfile:1`.
- Instalar con hashes las herramientas de gate.
- post-restore debería fallar con OMITIDA_ULTIMO_ADMIN.
- Validar `BACKUP_RETENTION_DAYS >= 1`.
- Firmar las copias de seguridad.

Lista completa en `REPORT.md` §5 de la auditoría.

## 7. Checks NO ejecutados (NOT_RUN) y motivo

| Check | Motivo |
|---|---|
| E2E, axe y Lighthouse en Firefox y WebKit | Decisión humana (2026-10-09): solo Chromium. |
| Auditoría de seguridad perfil *standard* | Decisión humana: se hizo la *quick*. Hay una unidad diferida (§5). |
| Ejecución de código dentro de la auditoría | El host Windows no tiene sandbox impuesto por el SO; la auditoría fue solo de fuente. El único hallazgo se validó fuera, en TKT-OPS-038. |
| Búsqueda adversarial de evasiones de trivy | RSK-OPS-053 (el clasificador de permisos lo impidió). |
| Prueba de OOM en un host Linux real sin swap | Se simuló con `memswap_limit` en Docker Desktop. |
| Despliegue, TLS, dominio, firma keyless y secretos reales | Puerta Humana §0.5. |

## 8. Para publicar en producción (Puerta Humana)

Antes de desplegar se necesita una decisión explícita sobre:
1. **Plataforma y costes:** servidor o nube, coste mensual y copias fuera del equipo.
2. **Dominio y TLS:** activar `SECURE_SSL_REDIRECT`/HSTS, ajustar `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `NG_ALLOWED_HOSTS`, y configurar `real_ip` si hay balanceador o CDN (RSK-OPS-065).
3. **Secretos reales:** gestor de secretos, clave age de las copias y su custodia.
4. **Responsable del tratamiento** (GAP-004) y publicación de la política de datos.
5. **Revisión humana del contenido** (GAP-008).
6. **CVE aceptadas que caducan el 2026-10-26** (RSK-OPS-001).
7. **Auditoría de seguridad *standard*** antes de exponer el sitio.

## 9. F9 — Pre-release (candidata `1.0.0-rc.1`, DEVOPS_HANDOFF §42, PR #115)

Sobre `main` en el stack aislado `brujularelease`; sin tags, sin publicación ni despliegue (Puerta Humana).

| Control | Resultado |
|---|---|
| Build de las 6 imágenes | PASS; huellas de capas estables |
| trivy | PASS: 0 CRITICAL/HIGH fuera de RSK-OPS-001; repetido tras TKT-OPS-038 sin cambios |
| SBOM CycloneDX (syft) | PASS, 6 imágenes |
| Arranque, migraciones, semilla, derivados | PASS |
| Smokes del CI + schemathesis | PASS, 3030/3030 casos |
| Smoke anti-evasión | PASS, 6/6 |
| `check --deploy` (ajustes de producción) | PASS |
| Copia nueva + simulacro AC-054 | PASS: BD, medios y libro idénticos; RTO 332 s (objetivo ≤ 4 h) |
| Lighthouse móvil (batería) | PASS_CONDICIONADO: CLS 0 en 30 ejecuciones; LCP sensible a la CPU (RSK-OPS-069, `/` mediana 4,0 s con batería, 1,96 s enchufado) |
| Carga de la API | ver TKT-OPS-039 (§9.1) |
| Django 5.2.18 (RSK-OPS-067) | ver TKT-073 (§9.1) |
| Firma cosign, procedencia, publicación, staging/prod | NOT_RUN (Puerta Humana) |

**Rollback:** la versión final `1.0.0` se etiqueta sobre el mismo digest de la candidata (prohibido reconstruir para producción); procedimiento en DEVOPS_HANDOFF §42.8.

### 9.1 Cierre de los MEDIUM de F9

| Ticket | Riesgo | Resultado |
|---|---|---|
| TKT-073 (PR #78) | RSK-OPS-067: Django 5.2.17 con 4 CVE corregidas en 5.2.18 (una DoS por cabeceras) | QA c1/3 PASS: pytest 1758/0, schemathesis 3051/3051, E2E Chromium 243/0, SAST/SCA/trivy 0; sonda de la CVE lineal en 5.2.18. **Integrado. Cerrado.** |
| TKT-OPS-039 (PR #116) | RSK-OPS-068: capacidad de la API (p95 1111 ms a 20 r/s con batería) | Causa: cuota de CPU (throttling CFS), no N+1. Ajuste: 4 workers, backend 4 CPU y 2560 MiB, BD 2 CPU, paso de CI «CPU ≥ workers». AC-053 (50 usuarios × 5 min): **p95 lectura 245 ms con batería (DevOps) y 139-141 ms enchufado (QA); búsqueda ≤ 87 ms; 0 % de errores**; A/B con la configuración anterior 197 ms. 3 subidas de 40 MP sin OOM y la web pública ya no se bloquea con 3 subidas. **Integrado. Cerrado.** |

Riesgos nuevos (post-entrega): RSK-OPS-070 LOW-MEDIUM (margen estrecho con batería: optimizar las 23-27 consultas por ficha, los 85 derivados por llamada y el purgado de `cache_limites` por petición; diagnóstico en DEVOPS_HANDOFF §43.6, DEC-AUTO-1012); RSK-OPS-071 LOW (un host con menos de 4 CPU necesita bajar a la vez workers, memoria y CPU, documentado en `.env.example`); con 4 o más subidas grandes simultáneas la web pública espera unos 4 s (OBS-OPS036-01, sigue abierto). OBS-QA039-01..05 INFO.

**Stack local actualizado** (2026-10-13): `brujulalocal` reconstruido desde `main` @ 2189f38 con `GUNICORN_WORKERS=4` en su `.env`; inicio, API y panel responden 200.
