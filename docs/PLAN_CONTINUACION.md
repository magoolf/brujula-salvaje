# Plan de continuación — Brújula Salvaje

> Documento vivo del Orquestador (DEC-AUTO-901). Se actualiza en cada integración para que, ante un corte por
> límite de uso, cualquier sesión pueda retomar sin rehacer trabajo. Fuente de verdad del estado: `kanban.md`
> y `audit_log.md`. Última actualización: 2026-10-09 (cierre del día, pausa pedida por el usuario).

## 1. Estado en una línea

2026-10-09 (CIERRE DEL DÍA, pausa pedida por el usuario; reanudar con 'continuar'): main @ origin al día, CI verde. Agentes detenidos a propósito (no es un corte). (1) TKT-048 HIGH IN_PROGRESS: código SIN COMMIT en el worktree .claude/worktrees/agent-ac49e7c60ce40b9df (rama tkt-048-lcp-imagenes, detrás de main 7 commits de docs): medios/services.py (codificación + regenerar_derivados), comando regenerar_derivados, test_tkt048_codificacion.py, inicio <picture> (imagen-principal.ts), destino SIZES_PORTADA, precarga-portada.ts (sin cablear). Checkpoint: %TEMP%/claude/C--Users-HOME-Music-STACK-TECNOLOIGICO/7e63c98e-ae89-4471-a470-c4dee4f7dde7/scratchpad/PROGRESO_TKT048.md y t48/ (Lighthouse antes/B1/B2: el preload no mejora; la causa restante del LCP simulado es el bundle JS). Falta: medición devtools, pytest/ruff (E501 corregido), unit/lint/build, E2E SOLO Chromium, commit, PR, CI. Stacks brujuladev048 y brujulaci048 parados (docker compose -p <p> start). Reanudar con un Developer nuevo: commit intermedio primero. (2) TKT-049 READY_FOR_VALIDATION: PR #82 @ 0ac94e8 CI verde; QA ciclo 1/3 cortada al empezar las E2E (worktrees de QA en scratchpad qa049 y qa049main, stack brujulaqa049 parado): relanzar QA desde cero solo en Chromium y borrar esos worktrees/stack. DECISIÓN HUMANA 2026-10-09: E2E/QA SOLO en Chromium (Google Chrome). Siguientes TODO: TKT-024 (panel 4/4), TKT-042/043/046/047/052/053/054, CHG-API-007, TKT-OPS-023/030/032, TKT-025/026/028/029/030/021/036/038/039, TKT-OPS-008/009, Dependabot #54-#57/#73/#74. Luego F9/F10. Memoria: 16 GB (el usuario valora ampliar a 32 GB); máx. 3 agentes.

2026-10-09 (noche): DONE hoy TKT-OPS-031, TKT-044, TKT-041, TKT-045, TKT-050, TKT-OPS-033 (CI con espejo mirror.gcr.io), TKT-016, TKT-023 (panel de contenidos completo), TKT-051; CI de main verde. En curso: Developer TKT-048 HIGH (LCP: codificación de derivados, imagen LCP de ficha e inicio; worktree aislado, checkpoint PROGRESO_TKT048.md) y Developer TKT-049 (rótulos de navegación; worktree aislado). Siguientes TODO: TKT-024 (panel 4/4, grande), TKT-042/043/046/047/052/053/054, CHG-API-007 (incluye OBS de TKT-045 y TKT-051), TKT-OPS-023/030/032, TKT-025/026/028/029/030/021/036/038/039, TKT-OPS-008/009, Dependabot #54-#57/#73/#74. Luego F9/F10. Memoria del equipo justa: máx. 3 agentes, workers=1; nunca matar procesos por nombre.

2026-10-09 (tarde): DONE hoy TKT-OPS-031 (#77, supercronic con Go 1.26.9), TKT-044 (#72), TKT-041 (#70), TKT-045 (#76); CI de main verde. En curso: QA TKT-016 c1/3 (PR #75 @ 1731b61); Developer TKT-023 (merge main + AC_TKT023_12 sin condición, worktree agent-a1e5ec9abe3b6b896, luego re-QA c2/3); Developer TKT-050 (worktree aislado, acceso a revisiones de páginas legales). Siguientes: TKT-048 HIGH (tras TKT-016, solapa destinos/inicio), TKT-049 (tras TKT-016, core/layout), TKT-042/043/046/047, CHG-API-007, TKT-OPS-023/030/032, TKT-024/025/026/028/029/030/021/036/038/039, TKT-OPS-008/009, Dependabot #54-#57/#73/#74. Luego F9/F10.

2026-10-09 (reanudación tras corte de 2026-10-08 23:05): DONE recientes TKT-019, TKT-OPS-026, TKT-OPS-027. En curso (relanzados desde checkpoint, scratchpad 56bc59a0…): QA TKT-044 c2/3 (PR #72 @ f524fbb, worktree %TEMP%/qa044, BD brujulaqa044); QA TKT-041 c2/3 (PR #70 @ e014094, worktree %TEMP%/qa041c2, stack brujulaqa041c2); Developer TKT-045 (worktree agent-ad738625364edf361, 2 commits sin push, checkpoint PROGRESO_TKT045.md, BD brujuladev045; falta pytest completo, merge main, PR). En espera: TKT-023 (PR #71 @ c75ad27, re-QA c2 tras integrar TKT-045 con E2E_TKT045=1), TKT-016 (worktree agent-a9207b2a8b8597c65, commit wip a5b9092; diagnóstico: CLS en /acerca-de y /creditos porque el contenido SSR se sustituye por esqueleto al hidratar y desplaza app-pie-sitio; spec de diagnóstico zz-diag016 sin commit; stack brujuladev016 parado). Siguientes TODO: TKT-042, TKT-043, TKT-046, TKT-047, TKT-048 (HIGH, antes de F9), CHG-API-007, TKT-OPS-023, TKT-OPS-030, TKT-024/025/026/028/029/030/021/036/038/039, TKT-OPS-008/009; Dependabot #54-#57, #73, #74 (QA de regresión). Luego F9/F10.

2026-10-08 (noche, 2.ª reanudación tras reinicio del equipo): DONE recientes TKT-034, TKT-037, CHG-API-006, TKT-022, TKT-040, TKT-OPS-029; CI de main verde. En curso (relanzados desde checkpoints en %TEMP%/claude/C--Users-HOME-Music-STACK-TECNOLOIGICO/e1176066-db5d-4635-a4e2-87432c5f81af/scratchpad/): QA TKT-019 ciclo 2/3 (PR #69, worktree %TEMP%/qa019c2, stack brujulaqa019, checkpoint qa019c2/); Developer TKT-044 (worktree agent-a115fbb767994a773, BD brujuladev044, checkpoint dev044/); Developer TKT-041 fotos reales (worktree agent-a50d7563b230a72f4, checkpoint dev041/); DevOps sincroniza PR #63 (TKT-OPS-026) y #65 (TKT-OPS-027) con main. En espera: TKT-023 (worktree agent-a1e5ec9abe3b6b896, rama ya al día con main+TKT-022, stack brujuladev023 parado; pendiente regresión panel 3 motores, build y PR; checkpoint en scratchpad 6f18847b…/dev023/) y TKT-016 (trabajo sin commit en agent-a9207b2a8b8597c65). Siguientes TODO: TKT-042, TKT-043, CHG-API-007, TKT-OPS-023, TKT-024/025/026/028/029/030/021/036/038/039, TKT-OPS-008/009; Dependabot #54-#57 (QA de regresión). Luego F9/F10.

2026-10-08 (noche, reanudación tras corte): TKT-OPS-028 DONE (PR #64 @ ea33268). Nueva CVE CRITICAL de handlebars rompe npm audit del frontend en todos los PR -> TKT-OPS-029 (DevOps, worktree .claude/worktrees/ops029). En curso: Developer TKT-037 (worktree agent-a379d59dc3af1300f, checkpoint scratchpad anterior dev037/PROGRESO.md) y Developer TKT-022 ciclo 2/3 (worktree agent-aee3d2c5be57fe466, checkpoint dev022/PROGRESO.md). En espera, con trabajo SIN commit preservado en su worktree: TKT-016 (agent-a9207b2a8b8597c65), TKT-019 (agent-a4d5ae9ee0a1d82d8); TKT-023 (agent-a1e5ec9abe3b6b896, 2 commits sin push, checkpoint dev023/PROGRESO.md). Stacks brujuladev016/019/023 parados (docker compose -p <p> start para reanudar). Tras TKT-OPS-029: update-branch y CI de #61 (TKT-034, QA PASS -> merge), #62 (CHG-API-006, QA pendiente), #63 (TKT-OPS-026), #65 (TKT-OPS-027). Checkpoints de la sesión anterior: %TEMP%/claude/C--Users-HOME-Music-STACK-TECNOLOIGICO/6f18847b-79b8-4146-946a-a6ee99b64c5b/scratchpad/.

2026-10-08 (tarde): DONE hoy TKT-OPS-025 (PR #59, source-map-js 1.2.2) y TKT-033 (PR #51 @ ee8dfda). En curso: (a) Developer TKT-022 ciclo 2/3 (F-01 axe en transición WebKit, F-02 429 de login con 4 workers, OBS-03) en el worktree agent-aee3d2c5be57fe466, checkpoint scratchpad/dev022/PROGRESO.md; luego QA ciclo 2; (b) QA TKT-OPS-022 sobre PR #52 @ 3ecc4f4 (checkpoint scratchpad/qaops022/); tras PASS: merge y desbloquea TKT-034; (c) Developer TKT-035 (core: 55P03/40P01 -> 409 global; carrera DELETE de catálogos), worktree aislado, checkpoint scratchpad/dev035/. Nuevo TODO: TKT-036 (contraste transitorio de .bs-boton). Permisos: el usuario permitió gh pr update-branch/merge, git worktree prune y docker compose -p brujulaqa*; un merge sin QA (#59) fue denegado igualmente y lo ejecutó el usuario. Dependabot #54-#58 sin tratar.

2026-10-01 (reanudación tras corte): TKT-OPS-024 DONE (PR #53 integrado @ 4c1d362; CVE del proxy corregida, CI de main desbloqueado). En curso: QA ciclo 1/3 de TKT-022 (PR #50 @ 05f5a62), TKT-033 (PR #51 @ b273b62, relanzada desde cero) y TKT-OPS-022 (PR #52 @ c9d1e79), tres subagentes qa en paralelo (stacks brujulaqa022*, brujulaqa033b/base, brujulaqaops022). PENDIENTE DEL USUARIO (denegado por el clasificador de permisos, no reintentar): (a) `gh pr update-branch 50/51/52` antes de cada merge (checks strict exigen rama al día); (b) bajar los stacks huérfanos `brujulaqa033`, `brujulaqa033m`, `brujulaqa033t` (`docker compose -p <nombre> down -v`) y quitar los worktrees `%TEMP%\qa033r1` y `qa033r1m` (`git worktree remove --force`). Tras cada QA PASS: update-branch, CI verde, `gh pr merge <n> --merge`, DONE; si QA FAIL, ticket al Developer/DevOps (ciclo 2/3). Luego TODO: TKT-023 (depende de TKT-022), TKT-024, TKT-034, TKT-035, TKT-OPS-023, TKT-016/019/021/025/026/028/029/030, TKT-OPS-008/009; después F9/F10. PR #22 y #21 (Dependabot): no integrar (#21 en conflicto). No enviar docs a main entre la sincronización de un PR y su merge.

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

### 4.5 F9 — Release (tras todos los tickets DONE, incluido TKT-OPS-016)
- Antes del release: consulta de diagnóstico de contenidos PUBLICADO con país/región/categoría retirados (OBS-01 QA TKT-037); CHG-API-006 y TKT-040 integrados.
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
