# Plan de continuación — Brújula Salvaje

> Documento vivo del Orquestador (DEC-AUTO-901). Se actualiza en cada integración para que, ante un corte por
> límite de uso, cualquier sesión pueda retomar sin rehacer trabajo. Fuente de verdad del estado: `kanban.md`
> y `audit_log.md`. Última actualización: 2026-09-27.

## 1. Estado en una línea

F1–F6 terminadas. En `main`: backend base (TKT-001), modelo de datos (TKT-003), frontend base (TKT-002) e
infraestructura completa (TKT-OPS-001..005) con CI verde, incluido trivy con `.trivyignore` aprobado por el
usuario. En QA final: TKT-004 (acceso al panel, PR #8, ciclo 3/3). Avance estimado ≈ 50 %.

## 2. Cómo reanudar tras un corte (verificar y corregir, no rehacer)

1. `git fetch origin` y `git worktree list`: ver qué ramas `tkt-*` tienen commits o cambios sin commit.
2. `gh pr list -R magoolf/brujula-salvaje` y `gh pr checks <n>`: estado de cada PR y su CI.
3. `docker ps -a --filter name=brujula`: bajar con `docker compose -p <proyecto> down -v` los stacks de prueba huérfanos.
4. Leer las últimas 20 líneas de `audit_log.md` y los tickets `IN_PROGRESS`/`READY_FOR_VALIDATION`/`QA_FAIL` de `kanban.md`.
5. Reanudar cada agente cortado desde donde quedó (commit intermedio primero). No relanzar tickets ya en `DONE`.
6. Solo corregir lo que la verificación muestre roto; registrar la corrección en `audit_log.md`.

## 3. Reglas de trabajo que no cambian

- Solo el Developer escribe código de aplicación; DevOps solo infraestructura (CLAUDE.md §0.3).
- Cada ticket: rama `tkt-XXX-…` en su worktree → Developer → QA (máx. 3 ciclos) → PR → CI verde → merge `--merge`.
- `main` protegida (PR + checks obligatorios strict). Nunca `--admin` ni force-push.
- Antes de un PR, la rama debe incorporar `origin/main` con merge normal (o `gh pr update-branch`).
- Si el contrato (`contracts/openapi.yaml`) cambia: regenerar el cliente del frontend (`npm run api:generate`) en la rama del frontend afectada.
- DEC-AUTO del Orquestador: rango 900+. Rangos por subagente: asignar uno nuevo y no reutilizarlo.
- Máximo 2–3 agentes a la vez (memoria del equipo y límites de uso).

## 4. Lo que falta, en orden, y cómo hacerlo

### 4.1 Cerrar lo que está en curso
| Tarea | Cómo |
|---|---|
| TKT-004 (PR #8) QA final 3/3 | Si PASS: `gh pr update-branch 8`, esperar CI, merge. Si FAIL: pasa a `BLOCKED_HUMAN` (§0.7) y se presenta al usuario. |
| PR #12 Dependabot (mypy 1.20.2) | Probable incompatibilidad con django-stubs 5.2.9 (exige mypy < 1.20). Si el CI falla, cerrarlo con comentario; si pasa, requiere QA ligera. |

### 4.2 Backend restante
| Ticket | Qué construir | Entradas | Criterios clave |
|---|---|---|---|
| **CHG-API-003 / CHG-DB** (antes de TKT-006) | Alinear `maxLength` del contrato (HTML 200 000, actividades 50 000) con el CHECK de BD (100 000) | contrato + DB_HANDOFF | lint Redocly 0 errores; una sola cifra en contrato, BD y nginx |
| **TKT-005** API pública + búsqueda + comandos | `/api/v1/publico/**` (inicio, destinos con filtros/facetas/mapa/aleatorio, itinerarios, guías, tipos, colecciones, glosario, créditos, páginas, 410 para retirados), búsqueda `es_unaccent` + `pg_trgm`, throttling público, comandos del crontab (`purgar_sesiones`, `purgar_auditoria`, `anonimizar_cuentas`, `purgar_ops`, `verificar_busqueda`, `reindexar_busqueda`, `reaplicar_anonimizaciones`) + migraciones CHG-DB-002 de medios/contenido/catálogos/inicio | Blueprint MOD-001..008/014, contrato, DB_HANDOFF v1.2 | Vistas públicas con `authentication_classes = []`; filtros array declarados en `multiples` de `validar_parametros`; schemathesis sin 5xx; gate de contrato; p95 ≤ 300 ms (búsqueda ≤ 500 ms) |
| **TKT-006** API del panel editorial | CRUD de contenidos, vista previa (también de contenido nuevo, DEC-AUTO-120), publicar/retirar/reactivar, revisiones, bloqueo optimista, subida de medios (DEC-AUTO-044: JPEG/PNG/WebP ≤ 10 MB, recodificar, sin EXIF, derivados AVIF/WebP/JPEG en `publico/`/`privado/`), taxonomías, inicio, configuración, tablero; idempotencia con el servicio común de `apps/core` | Blueprint MOD-010..012, contrato, DB_HANDOFF | acceso horizontal por objeto; THREAT de subida de archivos con tests; schemathesis Editor y Admin |
| **TKT-007** Contenido semilla | Comando idempotente `cargar_semilla`: 24 destinos reales (4 en Colombia), itinerarios día a día, guías (8 categorías), 12 tipos de aventura (Surf y Ciclismo de montaña: tipo secundario veraz o en borrador, PRB-BP-002), colecciones, glosario, páginas legales, configuración de inicio y medios propios con licencia | PRD §6, requirements.yaml `contenido_semilla` | publicado vía servicio (auditoría "sistema", índice de búsqueda), sin cifras volátiles, autoría de equipo y fecha de revisión |

### 4.3 Frontend restante (la web visible)
| Ticket | Qué construir | Notas |
|---|---|---|
| **TKT-008** Público 1 | Inicio, Explorar destinos (filtros en URL, mapa SVG Natural Earth, por mes, Sorpréndeme), ficha de destino, Guardados (localStorage) y compartir, SEO; destacados en la 404 | Incluye OBS-QA002-C2-01..03 (regex de hash de assets, `trustProxyHeaders` de @angular/ssr, test E2E que exija CSP en modo proxy). LCP ≤ 2,5 s (margen actual ~250 ms: vigilar bundle). |
| **TKT-009** Público 2 | Itinerarios, guías, tipos de aventura, colecciones, glosario, búsqueda, institucional/legal, créditos | Mismo presupuesto de rendimiento y axe 0 serious/critical |
| **TKT-010** Panel `/panel` | Login por pasos (MFA con reautenticación, DEC-AUTO-215), tablero, editores, medios, taxonomías, inicio, configuración, cuentas, auditoría | Añadir `{path:'panel', renderMode: Client}` en `app.routes.server.ts`; el interceptor no debe tratar como sesión expirada el 401 `credenciales_invalidas` de la reautenticación MFA |

### 4.4 Infraestructura pendiente (LOW, en paralelo cuando haya capacidad)
- **TKT-OPS-006**: gate de contrato con memoización y `timeout-minutes`; objeto abierto vs cerrado; 405 de medios en Problem Details; `/infra/db` en Dependabot; alerta de tamaño de `cache_limites`; política de trivy robusta a líneas de continuación.
- **TKT-OPS-007**: `scripts/ops/restore-local.sh` con lista TOC filtrada (excluir `SCHEMA app/ext`, `pg_stat_statements`, ACL de `public`) para que el simulacro AC-054 pase sobre BD limpia. **Bloquea F9.**

### 4.5 F9 — Release (tras todos los tickets DONE)
1. DevOps: build final de las 6 imágenes, SBOM (syft), trivy con `.trivyignore` vigente, firma (cosign keyless opcional), simulacro de restauración (AC-054), pruebas de carga (p95).
2. Orquestador: auditoría de seguridad completa con `security-audit-skill` en *Full audit mode*, perfil `standard`, salida en `~/security-audit-skill/<repo>/run-<N>`; cualquier `confirmed` CRITICAL/HIGH bloquea.
3. Producción: **Puerta Humana**. Requiere decisión del usuario sobre plataforma, dominio, costes, secretos reales, responsable del tratamiento (Ley 1581, GAP-004) y revisión humana del contenido (GAP-008).

### 4.6 F10 — Entrega
`docs/INFORME_ENTREGA.md`: decisiones autónomas, fallos corregidos, riesgos residuales, checks NOT_RUN y motivo.

## 5. Fechas y decisiones humanas pendientes
- **2026-10-26**: caducan las 16 excepciones de `.trivyignore` (RSK-OPS-001). El CI volverá a fallar hasta nueva decisión.
- Producción, dominio, costes, secretos reales y responsable del tratamiento: solo con aprobación explícita del usuario.

## 6. Dónde está cada cosa
| Qué | Ruta |
|---|---|
| Requisitos | `docs/01_requerimientos/` |
| Blueprint (pantallas, flujos, amenazas) | `docs/02_blueprint/BLUEPRINT.md` |
| Diseño y tokens | `docs/03_diseno/` |
| Base de datos | `docs/04_datos/DB_HANDOFF.yaml`, `docs/adr/ADR-DB-*` |
| Contrato API | `contracts/openapi.yaml`, `docs/adr/ADR-API-*` |
| Operación / DevOps | `docs/05_operacion/DEVOPS_HANDOFF.md`, `compose*.yaml`, `infra/`, `scripts/ops/` |
| CI | `.github/workflows/ci.yaml`, `.github/dependabot.yml`, `.trivyignore`, `.gitleaksignore` |
| Código | `backend/` (Django), `frontend/` (Angular) |
| Estado y trazabilidad | `kanban.md`, `audit_log.md`, este documento |
