# DEVOPS HANDOFF — TKT-F6-001 (F6 [PRE-DESARROLLO])

Proyecto: Brújula Salvaje. Fecha: 2026-09-25. Autor: Skill_devops.
Actualizado por **TKT-OPS-001** (F7, soporte de infraestructura, 2026-09-25): ver §13.
Actualizado por **TKT-OPS-003** (F7, CI verde + proxy/gzip + Dependabot, 2026-09-26): ver §15.
Actualizado por **TKT-OPS-004** (F7, gate de contrato por operación + límite de /health + errores del proxy + Dependabot sin mayores, 2026-09-26): ver §16.
Actualizado por **TKT-OPS-005** (F7, RSK-OPS-001 según decisión humana: `.trivyignore` con caducidad, runtimes sin gestores de paquetes, backup mínimo, `Cache-Control` del HTML SSR, `DJANGO_TRUSTED_PROXIES`, 2026-09-26): ver §17. **RSK-OPS-001 queda aceptado con caducidad hasta el 2026-10-26** (§17.10). Ciclo 2 (imagen de la BD derivada y en el gate): §17.14.
Actualizado por **TKT-OPS-007** (F7, QA-OPS005-02: `restore-local.sh` restaura sobre la BD de INFRA-DB-000 sin errores y sin ampliar privilegios, pasos de aplicación posteriores y runbook de restauración, 2026-09-27): ver §18. **Runbook de restauración: §18.9.**
Actualizado por **TKT-OPS-006** (F7, mejoras LOW: gate de contrato memoizado + objeto abierto/sin tipo, `timeout-minutes`, 405 de medios en Problem Details, Dependabot sobre todos los Dockerfile, política de trivy multilínea, alerta de tamaño de `cache_limites`, 2026-09-28): ver §19.
Actualizado por **TKT-OPS-010** (F7, gate de contrato: `oasdiff breaking --fail-on WARN` → `--fail-on ERR`, decisión del usuario, 2026-09-29): ver §20. Línea de índice añadida por TKT-OPS-011 (omitida en la entrega original de TKT-OPS-010; corrección de consistencia documental menor, sin cambio de contenido de §20).
Actualizado por **TKT-OPS-011** (F7, gate de contrato: excepción puntual `--err-ignore` para `request-body-type-changed` en `POST /api/v1/panel/medios`, decisión del usuario DEC-AUTO-920, 2026-09-29): ver §21.
Actualizado por **TKT-OPS-012** (F7, línea de `infra/scheduler/crontab` para `vigilar_cache_limites` (TKT-011, DONE) cada 15 min; cierra RSK-OPS-032, 2026-09-29): ver §22.
Actualizado por **TKT-OPS-016** (F7, HIGH, condición de F9). El limitador de borde gana la zona propia `estaticos` para los assets (fin de la navegación rota tras una IP compartida) y una defensa para que un asset inexistente no se renderice en el SSR. Además, `ruta_pedida` en el log y `X-Robots-Tag` en `/panel/**` (DEC-AUTO-929). 2026-09-30. Ver §23 y **ADR-OPS-001**.
Actualizado por **TKT-OPS-017** (F7, URGENTE: CVE-2026-103111 HIGH en `libpcre2-8-0` 10.46-1~deb13u2 de las 5 imágenes Debian; actualización fijada a 10.46-1~deb13u3 de trixie-security, sin tocar `.trivyignore`, 2026-10-01): ver §24 (§23 reservado para TKT-OPS-016, PR #38).
Actualizado por **TKT-OPS-019** (F7, LOW, hallazgos F-1/F-2 de la QA de TKT-OPS-016: la location de assets envía al SSR solo la ruta, sin query; ancla `\z`; sin `X-Forwarded-Host`/`X-Forwarded-Proto`; RSK-OPS-041 medido: 8 → 4 líneas, 2026-10-01): ver §25 y **ADR-OPS-001** (punto 7).
Entorno: solo local con Docker Compose. Sin despliegue, sin costes y sin secretos reales (CLAUDE.md §0.5, DEC-AUTO-002).
Host de validación: Windows 11, Docker Engine 29.6.1 (Docker Desktop, linux/amd64), Compose v5.2.0, buildx v0.35.0.

## 1. Estado

**COMPLETADO**, con una salvedad que **REQUIERE INTERVENCIÓN** (§10, RSK-OPS-001): las imágenes base oficiales con parche vigente arrastran CVE HIGH de Debian **sin corrección publicada**. El gate de trivy del CI (CRITICAL/HIGH = fail) fallará hasta que se publique el parche o una persona acepte las excepciones (CLAUDE.md §0.5). Esto bloquea F9, no F7.

Todo lo que depende del código de aplicación (backend/, frontend/) está marcado NOT_RUN. La infraestructura se validó con **fixtures desechables** creados en el scratchpad, fuera del repositorio (§8.2). Esa prueba valida la infraestructura, no la aplicación.

## 2. Objetivo

Dejar preparados, antes de F7, la matriz de interoperabilidad, el entorno Compose (db con INFRA-DB-000, migrate, backend, frontend SSR, proxy de mismo origen, scheduler y backup), los Dockerfiles multi-stage sin root, `.env.example` y el CI base de Skill_devops §23.2 hasta build + scan + SBOM. Además, la lista de archivos que debe crear el Developer.

## 3. Cambios realizados

- **INFRA-DB-000** (`infra/db/init/10-bootstrap.sh`): se ejecuta después de initdb (`--locale-provider=builtin --builtin-locale=C.UTF-8`, UTF8, checksums). Hace lo siguiente:
  - Crea los roles `app_migrator`, `app_rw`, `readonly` y `app_backup` (NOSUPERUSER) con contraseñas SCRAM y parámetros por rol (search_path `app, ext`, timeouts, `readonly` en solo lectura).
  - Crea la BD `brujula` (template0, builtin C.UTF-8) con REVOKE a PUBLIC.
  - Crea los esquemas `app` y `ext`, propiedad de `app_migrator`, con ALTER DEFAULT PRIVILEGES hacia `app_rw` (DML) y `readonly` (SELECT).
  - Da a `app_backup` el rol `pg_read_all_data` y a `readonly` el rol `pg_read_all_stats`.
  - Crea `pg_stat_statements` en `ext`.
  - Verifica el locale, la collation `es-x-icu`, que `unaccent`/`pg_trgm` estén disponibles y los checksums. Si algo falla, el init falla.
  - Es idempotente. Tiene un modo de prueba (`DB_BOOTSTRAP_TEST_TEMPLATE=true`, solo en `compose.ci.yaml`): da CREATEDB a `app_migrator` y prepara `template1` para la BD de test de pytest-django.
- **Proxy de mismo origen** (`infra/proxy/`, nginx 1.30.5 sin privilegios):
  - Rutas: `/api/**` y `/health/{live,ready}` → Django; `/media/publico/**` → volumen de medios (solo `.avif`, `.webp` y `.jpg`, en solo lectura); el resto → SSR de Angular.
  - Sobrescribe `X-Forwarded-For` con la IP real. Sustituye cualquier `traceparent` inválido.
  - Genera el nonce de CSP por petición y lo envía al SSR en `X-CSP-Nonce`; el valor que envíe el cliente se descarta.
  - Cabeceras de seguridad en el HTML. Límite de cuerpo de 2 MB en general y 105 MB en `POST /api/v1/panel/medios`, con timeout de 120 s.
  - Access log JSON con IP truncada (/24; IPv6 omitida) y sin query string. `error_log` en `crit` (DEC-AUTO-148).
- **Dockerfiles**:
  - `infra/docker/backend.Dockerfile`: targets `runtime` (gunicorn, uid 10001) y `scheduler` (runtime + supercronic 0.2.49 verificado por sha256).
  - `infra/docker/frontend.Dockerfile`: deps → build → runtime (Node, uid 1000, solo `dist/`).
  - `infra/proxy/Dockerfile` e `infra/backup/Dockerfile` (postgres 18.6 + age 1.2.1 + supercronic, uid 999).
  - Cada Dockerfile tiene su `.dockerignore` específico (`<Dockerfile>.dockerignore`), así que no hace falta escribir dentro de backend/ ni de frontend/.
- **Compose**:
  - `compose.yaml`: servicios `init-volumes`, `db`, `migrate`, `backend`, `frontend`, `proxy`; con el perfil `ops`, además `scheduler` y `backup`.
  - `compose.ci.yaml`: BD efímera en tmpfs, modo prueba y puerto de loopback configurable.
  - `compose.debug.yaml`: BD en `127.0.0.1:55432`.
- **Planificador**: `infra/scheduler/crontab` (UTC) con purgar_sesiones (horaria), purgar_auditoria, anonimizar_cuentas, purgar_ops y verificar_busqueda (diarias) y reindexar_busqueda (semanal) (DEC-AUTO-144).
- **Copias**:
  - `scripts/ops/backup.sh`: pg_dump custom `--no-unlogged-table-data` con `app_backup` + manifiesto sha256 generado desde la BD + tar de medios + libro de anonimizaciones; cifrado con age (clave pública); sumas antes y después de cifrar; rotación de 30. Falla si la clave es el placeholder.
  - `scripts/ops/restore-local.sh`: simulacro AC-054, solo en local. Exige `--confirmar-entorno-local` y `RESTORE_ENV=local`.
  - `scripts/ops/post-restore-local.sh` (TKT-OPS-007): pasos de aplicación posteriores a la restauración (migrate, comandos de ADR-DB-004 §4, arranque y `/health/ready`). Runbook completo en §18.9.
  - `infra/backup/crontab`: 01:30 UTC.
- **Entorno**: `.env.example` documentado y `scripts/ops/init-env.sh`, que genera el `.env` local con valores aleatorios y nunca sobrescribe uno existente.
- **CI**: `.github/workflows/ci.yaml` (§8.3).

## 4. Versiones aprobadas (matriz de interoperabilidad)

Digests consultados en Docker Hub y GHCR el 2026-09-25 (índice multi-arquitectura). Las imágenes marcadas VALIDADO se descargaron y ejecutaron con ese digest.

| Componente | Versión exacta | Requerido por | Compatible con | Estado | Evidencia |
|---|---|---|---|---|---|
| Docker Engine / Compose | 29.6.1 / v5.2.0 (buildx 0.35.0) | Infraestructura | Compose spec: `additional_contexts`, `!override`, `--wait` | APROBADO | `docker compose config` en 4 variantes; `up --wait` |
| PostgreSQL | 18.6 — `postgres:18.6-trixie@sha256:5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722` | DB_HANDOFF / ADR-DB-001 | Django 5.2 (PG ≥14), psycopg 3.3.6 | APROBADO | Init + pruebas de roles; migrate de Django (fixture) |
| Python | 3.13.15 — `python:3.13.15-slim-trixie@sha256:8d9d0b8bcf6506481eae4907c18f5e3e7902e629f5f6d684f9e7c32e85e3ddf0` | Backend | Django 5.2 (3.10–3.14) | APROBADO | Build + ejecución (fixture) |
| uv | 0.12.19 — `ghcr.io/astral-sh/uv:0.12.19@sha256:04d046b13e60d6bcec73cbc5e1cad25d680dea90c8573340950a0ac2d1aef424` | Backend (lock) | Python 3.13 | APROBADO | `uv sync --frozen` en el build (fixture) |
| Django | 5.2.17 (LTS, soporte hasta 04/2028) | Skill_Backend | Python 3.13, PG 18 | APROBADO (recomendado; lo fija el Developer) | Fixture: migrate OK en esquema `app` |
| DRF / drf-spectacular | 3.18.1 / 0.30.0 (últimas en PyPI el 2026-09-25) | Skill_Backend | Django 5.2 | RECOMENDADO — NO VALIDADO | Sin código |
| psycopg (binary) | 3.3.6 | Backend | PG 18, Django 5.2 (≥3.1.8) | APROBADO | Conexión app_migrator/app_rw (fixture) |
| gunicorn | 26.2.0 | Backend runtime | Python 3.13 | APROBADO | `/health/ready` 200 (fixture) |
| Node.js | 24.21.0 LTS "Krypton" — `node:24.21.0-trixie-slim@sha256:8ec5d7557396cfe32d21c3f9c13072355ceab22b584578ca4bb28af31120cffe` | Frontend | Angular 22 (`^22.22.3 \|\| ^24.15.0 \|\| ^26.0.0`) | APROBADO | `ng new` + build + SSR (fixture) |
| npm | 11.19.0 (incluido en Node 24.21.0) | Frontend | lockfileVersion 3 | APROBADO | `npm ci` (fixture) |
| Angular / CLI / SSR | 22.2.0 | Skill_Frontend | TypeScript 6.0.x, Node 24.21, Express 5 | APROBADO | Build SSR `dist/brujula-salvaje/{browser,server/server.mjs}` (fixture) |
| TypeScript | 6.0.x (lo fija `ng new` 22.2.0; `>=6.0.0 <6.1.0`) | Frontend | Angular 22 | APROBADO | Build (fixture) |
| nginx (proxy) | 1.30.5 stable — `nginxinc/nginx-unprivileged:1.30.5-alpine@sha256:4714e0b1b2577eaa1a6131d07c958b67f0eb68e6d0521e90c6e5287db8cf0bc5` (+ libexpat 2.8.5-r0) | Mismo origen (ADR-API-001) | SSR 4000, gunicorn 8000 | APROBADO | `nginx -t`; pruebas con stubs y stack completo; trivy 0 CRITICAL/HIGH |
| supercronic | v0.2.49 (sha256 amd64 `a53ae236…30c1`, arm64 `02aa0cb2…dd5`) | Planificador (DEC-AUTO-122) | — | APROBADO | `supercronic -test` OK en los 2 crontabs |
| age | 1.2.1-1+b5 (Debian trixie) | Copias cifradas | — | APROBADO | Ida y vuelta cifrar → descifrar → sha256 OK |
| gitleaks / trivy / syft / cosign | 8.30.1 / 0.74.0 / 1.51.0 / 3.1.3 (sha256 en ci.yaml) | CI §23.2 (VERSIONS.md) | — | APROBADO | trivy y gitleaks ejecutados en local |
| semgrep / bandit / pip-audit / schemathesis | 1.178.0 / 1.9.4 / 2.10.1 / 4.28.0 | CI §23.2 | — | APROBADO (versiones) — NOT_RUN | Sin código |
| oasdiff | 1.32.1 (sha256 en ci.yaml) | Contrato (Skill_Backend §12.5) | OpenAPI 3.1 | NOT_RUN | Sin código |
| GitHub Actions | checkout v7.0.1 `3d3c42e5…`, setup-node v7.0.0 `82076278…`, setup-python v7.0.0 `5fda3b95…`, setup-uv v10.2.0 `c18668ad…`, setup-buildx v4.4.1 `f87e5991…`, upload-artifact v7.0.1 `043fb46d…`, download-artifact v8.0.1 `3e5f45b2…` | CI | ubuntu-24.04 | APROBADO (fijadas por SHA) | `action-validator` rc=0; YAML válido |

Arquitectura: se validó linux/amd64. El scheduler y el backup incluyen checksum para arm64, que no se ha probado (NOT_RUN).

## 5. Infraestructura

### 5.1 Topología
```
navegador ──127.0.0.1:8080──▶ proxy (nginx, uid 101) ──┬─▶ frontend SSR (node, uid 1000) ──▶ backend (API interna)
                             red "publica" + "app"    └─▶ backend (gunicorn, uid 10001) ──▶ db (postgres, uid 999)
redes: publica (bridge; solo proxy) · app (internal) · datos (internal: db, backend, migrate, scheduler, backup)
```
- Red `app` (TKT-OPS-002, DEC-AUTO-155): subred fija `${APP_NET_PREFIX}.0/24` (por defecto `10.231.40.0/24`). El proxy tiene la IP fija `.10`; el resto de contenedores reciben una IP dinámica de `.128/25`. gunicorn solo confía en las cabeceras `X-Forwarded-*` que llegan desde `.10` (§14).
- La BD no publica puertos. Con `compose.debug.yaml` se publica en 127.0.0.1:55432, y con `compose.ci.yaml` en 127.0.0.1:${DB_CI_HOST_PORT:-5432}. Ambos overrides añaden una red puente propia, porque una red `internal` no admite publicar puertos.
- Endurecimiento por defecto: `read_only`, `cap_drop: ALL`, `no-new-privileges`, tmpfs en /tmp, límites de CPU y memoria en todos los servicios y logs json-file (10 MB × 5).
- La BD corre con `user: 999` (sin fase root ni gosu). `init-volumes` es un one-shot root con solo CHOWN y FOWNER y sin red: fija los propietarios de los volúmenes independientemente del orden en que se creen (DEC-AUTO-149).
- Orden de arranque: `init-volumes` → `db` (healthy) → `migrate` (`app_migrator`, completado) → `backend` (healthy en `/health/ready`) → `frontend` (healthy en `/healthz`) → `proxy`. El healthcheck de la BD usa TCP 127.0.0.1, de modo que "healthy" implica que INFRA-DB-000 terminó.
- Volúmenes:
  - `db_data`
  - `media`: `publico/` 0755 y `privado/` 0750, propiedad de 10001. El proxy solo ve `publico/`.
  - `ops_libro`: libro de anonimizaciones.
  - `backups`: 0700, propiedad de 999.
  - `backup` usa `group_add: 10001` para leer los medios privados y el libro.

### 5.2 Comandos
```bash
bash scripts/ops/init-env.sh                         # crea .env local (una vez; nunca sobrescribe)
docker compose up -d --wait db                       # solo PostgreSQL + INFRA-DB-000
docker compose up -d --build --wait                  # stack completo (cuando existan backend/ y frontend/)
docker compose --profile ops up -d --build           # + scheduler + backup
docker compose run --rm migrate                      # re-aplicar migraciones
docker compose --profile ops run --rm scheduler python manage.py purgar_ops   # comando manual
docker compose -f compose.yaml -f compose.debug.yaml up -d db                 # BD en 127.0.0.1:55432
docker compose exec db bash /docker-entrypoint-initdb.d/10-bootstrap.sh      # re-ejecutar el bootstrap (idempotente)
docker compose --profile ops down -v                 # borrar TODO, datos incluidos (solo local)
# Proyecto paralelo (QA, tickets): -p propio, puerto propio y prefijo de red propio (§14)
APP_NET_PREFIX=10.231.41 PROXY_HOST_PORT=18081 docker compose -p brujula-qa002 up -d --build --wait
```
En Git Bash, anteponer `MSYS_NO_PATHCONV=1` a los comandos que pasan rutas absolutas del contenedor.

### 5.3 CSP y RSK-UX-001 (DEC-AUTO-146)
`script-src 'self' 'nonce-<por petición>'`, sin `unsafe-inline` ni `unsafe-eval`. `style-src 'self' 'unsafe-inline'`: Skill_Frontend §27.4 solo prohíbe `unsafe-inline` en scripts, y un nonce en `style-src` haría que los navegadores bloquearan los estilos de componente que Angular inserta en el cliente y los `style=""` de CDK.

Validado con un fixture Angular 22.2.0:
- Con el inlining de CSS crítico activo, Beasties inyecta un `<script>` en línea **sin nonce** (quedaría bloqueado).
- Con `optimization.styles.inlineCritical: false` en la configuración production, el HTML queda sin scripts en línea ejecutables ni manejadores `on*=`.
- El `<style>` del SSR recibe el nonce vía `CSP_NONCE`.

Las rutas con nonce deben ser `RenderMode.Server` o `Client`: una página prerenderizada no puede llevar un nonce por petición.

### 5.4 Clave de copias local (desechable)
```bash
docker compose --profile ops build backup
MSYS_NO_PATHCONV=1 docker run --rm --entrypoint age-keygen brujula/backup:0.0.0-dev-brujula > ~/.brujula/age-local.key   # FUERA del repo; etiqueta = APP_VERSION o 0.0.0-dev-<proyecto> (§14)
# copiar la línea "# public key: age1..." en BACKUP_AGE_RECIPIENT del .env
```
La clave real de copias es una Puerta Humana (§0.5). Sin una clave `age1…` válida, backup.sh termina con exit 2.

## 6. Dependencias y tareas del Developer (F7) para que el entorno funcione

Archivos que DevOps **no** puede crear (CLAUDE.md §0.3) y que el entorno espera:

**backend/**
1. Proyecto creado con CLI: `django-admin startproject config .` dentro de `backend/`. Módulo de settings: `config.settings` y WSGI: `config.wsgi:application`.
2. `pyproject.toml` con dependencias `==`, `requires-python = "==3.13.*"` y `[tool.uv] package = false`; también `uv.lock` (`uv lock`) y dependency-group `dev` (ruff, mypy, pytest, pytest-django, pytest-cov…). El build usa `uv sync --frozen --no-dev`.
3. Los settings leen las variables de §7: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD` (psycopg 3 y pool o `CONN_MAX_AGE` según ADR-DB-001 §7), `DJANGO_*`, `THROTTLE_HMAC_KEY`, `MFA_FERNET_KEY`, `MEDIA_ROOT`, `MEDIA_PUBLIC_URL`, `LIBRO_ANONIMIZACIONES_PATH` y `OTEL_*`. Además, `TEST: {"NAME": "test_brujula"}`.
4. Confianza en el proxy:
   - La IP del cliente se toma de `X-Forwarded-For` con `NUM_PROXIES = DJANGO_NUM_PROXIES` (= 1).
   - `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`.
   - `USE_X_FORWARDED_HOST = False`: el proxy ya envía `Host` con el puerto.
   - **Pendiente desde TKT-OPS-002 (REQ-OPS002-01, §14.3)**: `SECURE_PROXY_SSL_HEADER = None`, para que el esquema lo decida gunicorn, que solo confía en la IP del proxy. Con la tupla actual, cualquier contenedor de la red `app` puede hacerse pasar por HTTPS.
5. `GET /health/live` (sin BD) y `GET /health/ready` (`SELECT 1` con timeout de 1 s), ambos accesibles con `Host: 127.0.0.1:8000`.
6. Medios:
   - Los derivados de medios DISPONIBLES se escriben en `MEDIA_ROOT/publico/…`, con URL `MEDIA_PUBLIC_URL`, nombres `[A-Za-z0-9/_-]+` y extensión `.avif`, `.webp` o `.jpg`.
   - Los originales saneados y los derivados no públicos van en `MEDIA_ROOT/privado/…`.
   - Permisos: `FILE_UPLOAD_PERMISSIONS` 0o640 en privado y 0o644 en publico; directorios 0o750 y 0o755.
   - Al retirar o reactivar un medio, el servicio mueve sus derivados entre `privado/` y `publico/` (DEC-AUTO-147).
7. Comandos de gestión con los nombres del crontab: `purgar_sesiones`, `purgar_auditoria`, `anonimizar_cuentas`, `purgar_ops`, `verificar_busqueda`, `reindexar_busqueda` y `reaplicar_anonimizaciones`. Deben ser idempotentes, usar `pg_try_advisory_lock` (si no obtienen el lock, salen con código 0), registrar en `ops_ejecucion_tarea` y no escribir PII en los logs.
8. Las migraciones RunSQL aplican las excepciones de privilegios que no son de F6: `django_migrations` solo SELECT para `app_rw`; los REVOKE de `readonly` y `app_rw` de DB_HANDOFF (n=10 y n=12); y el REVOKE EXECUTE FROM PUBLIC de las funciones SECURITY DEFINER.
9. Logging JSON a stdout y sin IP completas. gunicorn corre sin access log (lo emite el proxy).
   Desde TKT-OPS-001, las líneas propias de gunicorn usan el formatter `apps.core.observabilidad.formateador_json` (referenciado desde `infra/docker/gunicorn-logging.json`): si se renombra o se mueve, hay que avisar a DevOps (DEC-AUTO-153).
10. `pytest` con `--cov-fail-under` según Skill_Backend y `drf-spectacular` con el comando `spectacular` disponible (el CI lo compara con `contracts/openapi.yaml` usando oasdiff).

**frontend/**
1. `ng new brujula-salvaje --directory frontend --ssr` con `@angular/cli@22.2.0`. El nombre del proyecto debe ser `brujula-salvaje` (ARG `ANGULAR_PROJECT`); si cambia, hay que avisar a DevOps.
2. `package.json` sin `^` ni `~` (`ng new` los genera: hay que reescribirlos), `package-lock.json` y `.npmrc` con `save-exact=true`. Los tres son obligatorios porque el Dockerfile los copia.
3. `angular.json` production: `outputMode: "server"` y `optimization.styles.inlineCritical: false` (RSK-UX-001). No usar `externalDependencies`: el runtime solo copia `dist/`.
4. `src/server.ts`: `app.get('/healthz', …)` responde 200 sin llamar a la API. En las peticiones del servidor a la API se usa `API_INTERNAL_URL` y se reenvían sin modificar `X-Forwarded-For`, `traceparent` y `X-Request-Id` recibidos (ADR-API-002 §9).
5. `app.config.server.ts`: `{provide: CSP_NONCE, useFactory: () => inject(REQUEST, {optional: true})?.headers.get('x-csp-nonce') ?? null}`. Rutas públicas con `RenderMode.Server`; panel con `RenderMode.Client`. No usar `RenderMode.Prerender` en páginas que incluyan scripts en línea.
6. Scripts npm: `api:generate` (cliente desde `../contracts/openapi.yaml`, con salida bajo `src/app`), `eslint` en devDependencies y cobertura de Vitest con umbrales (Skill_Frontend §27.2).
7. `NG_ALLOWED_HOSTS` llega por entorno (`localhost,127.0.0.1`).

Si hace falta un paquete de sistema en las imágenes (p. ej. `libmagic1`), se emite un ticket a DevOps: no se instala a mano.

## 7. Variables de entorno

La referencia completa, con comentarios y valores ficticios, está en `/.env.example`. Grupos:
- Compose: `COMPOSE_PROJECT_NAME`, `PROXY_HOST_PORT`, `DB_DEBUG_HOST_PORT`, `APP_VERSION` (vacío en local: `0.0.0-dev-<proyecto>`), `APP_NET_PREFIX` (TKT-OPS-002, §14).
- PostgreSQL: `POSTGRES_SUPERUSER_PASSWORD` (solo el init), `DB_NAME`, `APP_MIGRATOR_PASSWORD`, `APP_RW_PASSWORD`, `READONLY_PASSWORD`, `APP_BACKUP_PASSWORD`.
- Django: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_SESSION_COOKIE_SECURE`, `DJANGO_CSRF_COOKIE_SECURE`, `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS`, `DJANGO_NUM_PROXIES`, `DJANGO_LOG_LEVEL`, `THROTTLE_HMAC_KEY`, `MFA_FERNET_KEY`, `MEDIA_PUBLIC_URL`, `PROBLEM_TYPE_BASE_URL`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `OTEL_SDK_DISABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`.
- Compose las inyecta por servicio: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `MEDIA_ROOT`, `LIBRO_ANONIMIZACIONES_PATH`, `OTEL_SERVICE_NAME`, `TZ=UTC` y, solo en backend, `GUNICORN_FORWARDED_ALLOW_IPS` (= `${APP_NET_PREFIX}.10`, la IP del proxy).
- SSR: `NG_ALLOWED_HOSTS`, `API_INTERNAL_URL`.
- Copias: `BACKUP_AGE_RECIPIENT`, `BACKUP_RETENTION_DAYS`.
- Solo CI: `DB_BOOTSTRAP_TEST_TEMPLATE`, `DB_CI_HOST_PORT`.

`PROBLEM_TYPE_BASE_URL` (TKT-OPS-001, DEC-AUTO-103) es la base de las URI `type` de los errores `application/problem+json` (RFC 9457). Su valor es ficticio: `https://brujulasalvaje.example` (dominio reservado `.example`). compose la inyecta en backend, migrate y scheduler con ese mismo valor por defecto. En producción se sustituye por el dominio real (no es secreto).

Todas las variables secretas usan `${VAR:?}` en compose: sin `.env`, `docker compose config` falla. Esto está verificado.

## 8. Validaciones ejecutadas

### 8.1 Sobre los artefactos reales del repositorio
| Check | Resultado |
|---|---|
| `docker compose config --quiet` (base, `--profile ops`, +ci, +debug) | VALIDADO: 4/4 OK. Sin `.env` falla con un mensaje claro (fail-closed) |
| `docker compose up -d --wait db`: INFRA-DB-000 en un volumen vacío | VALIDADO: healthy en unos 7 s |
| BD `brujula`: provider `b`, locale `C.UTF-8`, UTF8, `data_checksums=on`, collation `es-x-icu` presente | VALIDADO |
| Roles: 4 NOSUPERUSER/NOCREATEDB; contraseñas SCRAM-SHA-256; parámetros por rol; `pg_read_all_data` → app_backup | VALIDADO |
| app_migrator: `CREATE EXTENSION unaccent/pg_trgm` en ext sin superusuario, DDL, orden es-x-icu (Andes, árbol, nube, Ñandú, Zafiro) | VALIDADO |
| app_rw: DML sí; CREATE en app/public → permission denied; statement_timeout 5s | VALIDADO |
| readonly: SELECT sí; INSERT → read-only transaction | VALIDADO |
| app_backup: pg_dump custom OK; conexión TCP sin contraseña → rechazada | VALIDADO |
| Re-ejecución de 10-bootstrap.sh sobre el clúster existente | VALIDADO (idempotente) |
| Modo CI: CREATEDB, template1 con app/ext, `SET ROLE app_rw`, puerto en loopback accesible | VALIDADO |
| `nginx -t`; build de las imágenes proxy y backup | VALIDADO |
| `init-volumes`: propietarios y permisos; segunda ejecución | VALIDADO (idempotente) |
| backup.sh: placeholder → exit 2; copia real → cifrado, descifrado y `sha256sum -c` OK; el tar incluye `privado/` y `publico/`; libro incluido; `pg_restore --list` OK | VALIDADO (BD sin esquema: manifiesto vacío) |
| `supercronic -test` en ambos crontabs; servicios scheduler y backup en ejecución | VALIDADO |
| ci.yaml: YAML válido (js-yaml) y esquema de GitHub Actions (`@action-validator/cli` 0.6.0, rc=0) | VALIDADO |
| gitleaks 8.30.1 `dir` sobre compose*, .env.example, infra/, scripts/, .github/ | VALIDADO: no leaks found |
| trivy 0.74.0 (CRITICAL,HIGH) | Ver §9 |

### 8.2 Con fixtures desechables (scratchpad, fuera del repo): validan la INFRAESTRUCTURA, no la aplicación
- **Stubs Python** que devuelven como eco las cabeceras recibidas, detrás del proxy endurecido (read-only, cap_drop ALL):
  - Se comprobó que `X-Forwarded-For: 6.6.6.6` del cliente se sustituye por la IP real, que el `X-CSP-Nonce` del cliente se descarta, que el nonce del SSR coincide con el de la CSP, que la API no recibe nonce, que un `traceparent` inválido se regenera y uno válido se propaga, y que se ocultan `X-Powered-By` y la CSP del upstream.
  - Respuestas: POST `/` → 403; `/health/otro` → 404.
  - Medios: la imagen pública → 200 con `nosniff`; `.html`, `privado/`, traversal y directorios → 404.
  - Límites de cuerpo: 3 MB → 413 en la API general y 200 en la subida de medios.
  - Logs: IP /24 y sin query string. El error_log mostraba la IP completa, lo que motivó DEC-AUTO-148 (ahora en `crit`).
- **Fixture Django 5.2.17 + gunicorn + psycopg**, generado con `django-admin startproject` y `uv lock`:
  - build de los targets `runtime` y `scheduler`;
  - `migrate` con `app_migrator` → 10 tablas en el esquema `app`;
  - con los default privileges, `app_rw` tiene DML y `readonly` tiene SELECT;
  - backend healthy como uid 10001, con raíz de solo lectura y medios escribibles.
- **Fixture Angular 22.2.0** (`ng new --ssr`):
  - build con frontend.Dockerfile y SSR healthy en `/healthz`;
  - stack completo `docker compose up --wait` con los 6 servicios (más ops) healthy y `/health/ready` 200 a través del proxy;
  - comprobación de la CSP (§5.3).
- Limpieza: `docker compose -p brujula --profile ops down -v` (sin volúmenes ni redes brujula restantes) y borrado de las imágenes `brujula/*:0.0.0-dev`, `*:f6-fixture` y `proxy:f6-test`.
  - No se tocaron los contenedores `backend`, `frontend` y `db` del proyecto ajeno PROYECTO1. Docker Desktop estaba parado y lo arranqué para validar; al arrancar, esos contenedores se iniciaron solos por su política de reinicio.
  - `age-test.key` es una clave desechable de prueba que solo existe en el scratchpad de la sesión: no está en el repo (`git status` sin claves) y no protege ningún dato real.

### 8.3 NOT_RUN (y por qué)
- `docker compose build/up` de backend y frontend reales, migraciones reales (core.0001…ops.0001), manifiesto de medios con tablas reales y simulacro AC-054 completo: **no existe código** (F7).
- Todos los jobs del CI (no hay remoto ni ejecución en GitHub). ruff, mypy, pytest, `check --deploy`, oasdiff, schemathesis, semgrep, bandit, pip-audit, eslint, tsc, vitest y npm audit: no hay código.
- SBOM con syft sobre las imágenes finales: se ejecutará en el CI y en F9. Firma cosign: desactivada por diseño.
- E2E Playwright + axe (lo hace QA en F8). arm64. Carga (AC-051/053).

## 9. Seguridad

- Sin secretos en el repositorio: `.env.example` solo contiene `CHANGE_ME`, gitleaks no encontró nada y `.env`, `*.key` y `*.pem` ya están en `.gitignore`. En el CI, `.env` se genera con valores aleatorios en cada ejecución.
- Ningún contenedor de la aplicación corre como root. `init-volumes` es la única excepción: one-shot, sin red, con solo CHOWN y FOWNER, y justificado (DEC-AUTO-149). TKT-OPS-001 corrige su fallo sin añadir capacidades (DEC-AUTO-151; se descartó DAC_OVERRIDE).
- Privacidad de los logs (REQ-057, THREAT-020):
  - nginx: IP truncada y sin query string; `error_log crit`.
  - PostgreSQL: `log_connections=off`, `log_min_duration_statement=-1`, `log_min_error_statement=panic` y `log_parameter_max_length*=0` (DEC-AUTO-145).
  - gunicorn: sin access log (`gunicorn.access` sin handlers ni propagación, verificado en TKT-OPS-001) y sin socket de control (DEC-AUTO-152).
- **trivy 0.74.0 (CRITICAL/HIGH)**:
  | Imagen | Total | Con corrección disponible | Detalle |
  |---|---|---|---|
  | proxy | 0 | 0 | La libexpat de la imagen base tenía CVE-2026-93990 (HIGH): corregido fijando 2.8.5-r0 |
  | backup | 62 (1 CRITICAL, 61 HIGH) | 0 | CVE-2026-6653 (libxml2, CRITICAL, sin fix en Debian) y paquetes Debian 13.7. Los 22 CVE de Go stdlib de `gosu` se eliminaron quitando el binario |
  | backend (fixture) | 46 HIGH | 0 | Paquetes Debian 13.7 de la base python slim, sin corrección publicada |
  | frontend (fixture) | 47 HIGH | 0 | Paquetes Debian de la base node slim y del npm incluido, sin corrección publicada |
  | db (postgres oficial) | no escaneada por separado | — | Misma base que backup; incluye `gosu` (no se ejecuta: user 999) |
- El CI mantiene el gate estricto de §23.2 (`--exit-code 1` en CRITICAL/HIGH, sin `--ignore-unfixed`). **Aceptar esas excepciones es una Puerta Humana** (§0.5): no se han aceptado.

## 10. Riesgos / pendientes

| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-001 | CVE HIGH/CRITICAL sin corrección en las bases Debian (python, node, postgres): el gate de trivy fallará | HIGH | Reconstruir con digests nuevos cuando haya parche (revisión semanal). Alternativas: bases distroless o alpine (requiere ADR y prueba de ICU/es-x-icu en postgres) o una excepción `.trivyignore` con caducidad → **decisión humana** | REQUIERE INTERVENCIÓN (antes de F9) |
| RSK-OPS-002 | `style-src 'unsafe-inline'` permite inyección de CSS | LOW | Los scripts siguen estrictos con nonce. Endurecimiento futuro: `ngCspNonce` en la raíz + nonce en style-src | ABIERTO |
| RSK-OPS-003 | Copia de medios completa (tar) × 30 días ≈ 150 GB con 5 GB de medios | MEDIUM | Válido en local. En producción, copias deduplicadas (restic/borg) con ADR y Puerta Humana de costes | ABIERTO |
| RSK-OPS-004 | Desviaciones respecto a ADR-DB-001 §8: `log_min_duration_statement=-1` en lugar de 250 ms (con psycopg 3 y binding en cliente, el texto de la sentencia llevaría los literales de búsqueda). La latencia se observa con pg_stat_statements (normalizado) | LOW | Pedir a Base de Datos que lo reconozca; alternativa: `server_side_binding` en Django | ABIERTO |
| RSK-OPS-005 | `error_log crit` en nginx reduce el diagnóstico de fallos de upstream | LOW | El access log JSON registra estado y upstream_s; se puede bajar a `error` temporalmente en local | ACEPTADO (local) |
| RSK-OPS-006 | Rotación de logs por tamaño (10 MB × 5), no por días (FEAT-048 ≤30 días) | LOW | En producción, logs centralizados con TTL de 30 días (§23.5) | ABIERTO |
| RSK-OPS-007 | Algunas opciones del CI dependen del código real (nombre de `api:generate`, `--include-path-regex` y nombres de checks de schemathesis 4.28, `tsconfig.app.json`) | LOW | Verificar en la primera ejecución del CI y ajustarlas mediante un ticket a DevOps | NOT_RUN |
| RSK-TKT001-01 | `init-volumes` fallaba (`mkdir /vol/media/publico: Permission denied`) cuando el volumen de medios vacío se poblaba desde la imagen del backend (propietario 10001) | MEDIUM | DEC-AUTO-151: chown 0:0 del raíz del volumen antes de `mkdir` (TKT-OPS-001) | CERRADO (validado) |
| RSK-TKT001-02 | gunicorn 26: `Control server error: Read-only file system: /app/.gunicorn` y líneas propias que no son JSON | LOW | DEC-AUTO-152 (`--no-control-socket`) + DEC-AUTO-153 (`--log-config-json`) (TKT-OPS-001) | CERRADO (validado) |
| RSK-OPS-009 | gunicorn ignora en silencio un `--log-config-json` inexistente o ilegible y vuelve al formato de texto | LOW | Paso del smoke del CI: para el backend y falla si hay alguna línea no JSON o ninguna línea (DEC-AUTO-158, TKT-OPS-002) | CERRADO (validado en local; CI NOT_RUN) |
| RSK-OPS-010 | Las etiquetas `brujula/*:0.0.0-dev` son comunes a todos los proyectos Compose del host (p. ej. `brujula-qa001`): el build de un proyecto sustituye la imagen de otro | LOW | Etiqueta por defecto `0.0.0-dev-<proyecto compose>` (DEC-AUTO-156, TKT-OPS-002). Los `.env` locales antiguos con `APP_VERSION=0.0.0-dev` deben vaciar esa línea | CERRADO (validado) |
| RSK-OPS-011 | Django confía en `X-Forwarded-Proto` venga de donde venga (`SECURE_PROXY_SSL_HEADER`): un contenedor de la red `app` puede hacerse pasar por HTTPS aunque gunicorn ya no confíe en él | MEDIUM | Ticket al Developer: REQ-OPS002-01 (§14.3). Validado con un fixture | ABIERTO (requiere ticket) |
| RSK-OPS-012 | DRF toma la IP de `X-Forwarded-For` con `NUM_PROXIES` sin mirar quién la envía: un contenedor de la red `app` puede falsificarla para eludir el throttling por IP | LOW | Propuesta REQ-OPS002-02 (§14.3). Hoy la red `app` solo tiene proxy, frontend y backend | ABIERTO |
| RSK-OPS-013 | La subred de `app` es fija: dos proyectos compose simultáneos con el mismo `APP_NET_PREFIX` chocan (`Pool overlaps`) | LOW | Usar `APP_NET_PREFIX` distinto en cada proyecto paralelo (§5.2). El error es explícito y no afecta al otro proyecto | ACEPTADO (local) |
| RSK-OPS-014 | Con `DJANGO_SECURE_SSL_REDIRECT=true` (producción), las llamadas directas del SSR al backend (`API_INTERNAL_URL`, http) reciben 301, porque el SSR no reenvía `X-Forwarded-Proto` (§6 frontend, punto 4). Esto ya ocurre sin TKT-OPS-002 | MEDIUM | Decidir en el ADR de plataforma de producción (§23.5): IP fija del frontend + incluirla en `GUNICORN_FORWARDED_ALLOW_IPS` + reenviar `X-Forwarded-Proto`, o bien TLS interno | ABIERTO (F9) |
| RSK-OPS-008 | Las reglas de semgrep del registro (`p/django`…) no están fijadas por versión | LOW | Vendorizar las reglas en F9 si se requiere reproducibilidad estricta | ABIERTO |

Pendientes que no son de DevOps: el CHG-API-001 (TKT-F4-005) sigue en curso, así que el contrato puede cambiar antes de F7; y RSK-DB-011.

**Decisiones autónomas (ORIGEN: EXPANSIÓN_AUTÓNOMA, reversibles)**: DEC-AUTO-140 a DEC-AUTO-150; el detalle está en el HANDOFF_ENVELOPE de este ticket.

## 11. Archivos modificados (todos nuevos)

- `compose.yaml`, `compose.ci.yaml`, `compose.debug.yaml`, `.env.example`
- `infra/db/init/10-bootstrap.sh`
- `infra/proxy/{Dockerfile,nginx.conf}`, `infra/proxy/snippets/{proxy-headers,security-headers-html,security-headers-static}.conf`
- `infra/docker/{backend,frontend}.Dockerfile` + `*.Dockerfile.dockerignore`
- `infra/scheduler/crontab`, `infra/backup/{Dockerfile,crontab}`
- `scripts/ops/{init-env,backup,restore-local}.sh`
- `.github/workflows/ci.yaml`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

## 12. Próximo agente

**Orquestador**, que debe:
1. Registrar DEC-AUTO-140 a DEC-AUTO-150 y RSK-OPS-001 (Puerta Humana antes de F9).
2. Inyectar el §6 de este documento en los Micro-Tickets de F7 (bootstrap de backend/ y frontend/).
3. Después, **Skill_Developer** (F7).

## 13. TKT-OPS-001 — correcciones de infraestructura (F7, soporte)

### 13.1 Estado
**COMPLETADO.** Rama `tkt-ops-001-infra-fixes`, sin merge: la integra el Orquestador.

### 13.2 Objetivo
Corregir los defectos de infraestructura que informó el Developer de TKT-001 (RSK-TKT001-01 y RSK-TKT001-02) y exponer `PROBLEM_TYPE_BASE_URL` (DEC-AUTO-103).

### 13.3 Cambios realizados
- **RSK-TKT001-01 → DEC-AUTO-151** (`compose.yaml`, servicio `init-volumes`):
  - Cambio: el script hace `chown 0:0 /vol/media` y `chmod 0755 /vol/media` antes de `mkdir -p publico privado`. Al final devuelve la propiedad a 10001, igual que antes.
  - Causa: al crear un contenedor, Docker copia el propietario y los permisos del directorio de la imagen a un volumen vacío. Si el último contenedor creado que monta `media` es el backend (`/var/lib/brujula/media`, 10001, 0755), el raíz del volumen queda como 10001. Entonces root sin `CAP_DAC_OVERRIDE` no puede escribir en él.
  - Por eso el resultado depende del orden de creación: `docker compose up backend` falla siempre en un volumen limpio, mientras que el stack completo pasa si el proxy se crea después (su `/srv/media` es de root).
  - Alternativas:
    - (a) `cap_add: DAC_OVERRIDE`. Descartada: root podría saltarse todos los permisos del volumen, incluida la lectura de `privado/`.
    - (b) Quitar `/var/lib/brujula/media` de la imagen. Descartada como única medida: no repara los volúmenes ya poblados y cambia el comportamiento de la imagen fuera de compose.
    - (c) **Elegida**: tomar la propiedad con la capacidad CHOWN que el servicio ya tenía. No añade privilegios, no depende del orden y repara los volúmenes existentes. Es reversible (una línea).
- **RSK-TKT001-02 → DEC-AUTO-152 y DEC-AUTO-153** (`infra/docker/backend.Dockerfile` y el nuevo `infra/docker/gunicorn-logging.json`):
  - `--no-control-socket`: desde la 25.1, gunicorn abre un socket de control en `$HOME/.gunicorn`, que aquí es `/app` (solo lectura). En el contenedor no se usa `gunicornc`, porque la gestión se hace con señales y compose. Por eso se desactiva en lugar de moverlo a `/tmp`: así hay menos superficie.
  - `--log-config-json /etc/brujula/gunicorn-logging.json` sustituye a `--error-logfile -`:
    - `gunicorn.error` escribe en stdout con el formatter JSON del backend (`apps.core.observabilidad.formateador_json`), con las mismas claves `event`, `level`, `logger` y `timestamp` y el mismo filtro de claves sensibles.
    - `gunicorn.access` queda sin handlers, a nivel CRITICAL y sin propagar. Con un logconfig, gunicorn emitiría el access log con la IP completa (REQ-057).
  - `/etc/brujula` se crea con 0755 en el `RUN` que crea el usuario, porque `COPY --chmod=0444` aplica ese modo también al directorio padre que crea. La primera prueba lo mostró con un `Permission denied`.
  - **No hizo falta ningún archivo en backend/** (tampoco `gunicorn.conf.py`), así que no hay ticket al Developer. El único requisito es que la ruta del formatter no cambie (§6, punto 9).
- **DEC-AUTO-103**: `PROBLEM_TYPE_BASE_URL=https://brujulasalvaje.example` en `.env.example` y en `x-backend-env` de `compose.yaml` (antes el backend solo usaba su valor por defecto interno) (§7).

### 13.4 Versiones aprobadas
No cambian las versiones ni las imágenes base. Validado con el backend real de TKT-001 (rama `tkt-001-backend-base` @ 7e84ed0): Django 5.2.17, gunicorn 26.2.0, psycopg 3.3.6 y structlog 26.1.0, sobre `python:3.13.15-slim-trixie` fijado por digest.

### 13.5 Infraestructura
Sin cambios de topología, redes, puertos, límites ni healthchecks.

### 13.6 Dependencias
No se modificó ninguna dependencia ni ningún lockfile.

### 13.7 Variables de entorno
Nueva: `PROBLEM_TYPE_BASE_URL` (§7). Valor ficticio; no es un secreto.

### 13.8 Validaciones ejecutadas (2026-09-25, Docker Engine 29.6.1, Compose v5.2.0)
Entorno de validación montado **fuera del repositorio**, en el scratchpad:
- Copia de `compose.yaml`, `infra/`, `scripts/ops/` y `.env.example` de la rama.
- `backend/` copiado del worktree de TKT-001, sin `.venv`.
- `.env` generado con `scripts/ops/init-env.sh` (valores aleatorios locales).
- Proyecto `-p brujula-ops001` con `PROXY_HOST_PORT=18081`.

**El frontend todavía no existe.** Se sustituyó por un stub: un override `compose.stub.yaml` no versionado que usa python:3.13.15-slim fijado, corre con uid 65534 y responde 200 en el puerto 4000. La validación cubre db, init-volumes, migrate, backend y proxy; el frontend real queda NOT_RUN.

| Check | Resultado |
|---|---|
| Reproducción con la infra de `main`: `up --wait backend` en volúmenes limpios | FALLA como se informó: `mkdir: cannot create directory '/vol/media/publico': Permission denied` (exit 1). Aislado con `docker run`: con CapEff=CHOWN+FOWNER sobre un raíz 10001 0755, el acceso se deniega |
| Reproducción con la infra de `main`: logs del backend | `[ERROR] Control server error: [Errno 30] Read-only file system: '/app/.gunicorn'` y 6 líneas de gunicorn que no son JSON |
| `docker compose config --quiet`: base, `--profile ops`, +ci y +debug | VALIDADO: 4/4 |
| `up -d --build --wait` del stack completo en volúmenes limpios (db, init-volumes, migrate, backend, proxy y el stub del frontend) | VALIDADO: rc=0. db, backend, frontend (stub) y proxy healthy; init-volumes y migrate terminan con exit 0 |
| `up --wait backend` en volúmenes limpios (el caso que fallaba) | VALIDADO: rc=0 |
| Volumen `media` poblado antes desde la imagen del backend (raíz 10001) y después `up --wait backend` | VALIDADO: rc=0. También repara un volumen existente |
| Permisos finales: media 10001 0755, publico 0755, privado 0750, ops 0750 | VALIDADO |
| Segunda ejecución de init-volumes (`--force-recreate`) | VALIDADO (idempotente) |
| Peticiones a través del proxy: `/health/ready` → 200; `/api/v1/no-existe-ops001` → 404 con `type` `https://brujulasalvaje.example/errors/no_encontrado`; `/` → 200 (stub) | VALIDADO |
| Logs del backend: 11/11 líneas JSON (arranque, peticiones y `stop`, de `Handling signal: term` a `Shutting down: Master`) | VALIDADO: 0 líneas no JSON, ninguna con "Control server" ni "Read-only" y ninguna de access log |
| `PROBLEM_TYPE_BASE_URL` presente en el entorno del contenedor backend | VALIDADO |
| Build del target `scheduler` | VALIDADO (el perfil ops completo no se ejecutó) |
| JSON de `gunicorn-logging.json` | VALIDADO |
| gitleaks 8.30.1 sobre compose.yaml, .env.example e infra/ | VALIDADO: no leaks found |
| Limpieza con `--profile ops down -v` | VALIDADO: no queda ningún volumen ni red `brujula-ops001`. No se tocaron los contenedores `backend`, `frontend` y `db` (PROYECTO1) ni los de `brujula-qa001` |

NOT_RUN y por qué:
- Frontend real: todavía no existe.
- Perfil `ops` en ejecución (scheduler y backup).
- trivy y syft sobre la imagen reconstruida: la base no cambió; quedan para CI/F9 (RSK-OPS-001).
- CI en GitHub: no hay remoto.

### 13.9 Seguridad
No se añaden capacidades ni privilegios, y se quita un socket de control que no se usaba. El access log de gunicorn sigue anulado. No hay secretos: solo un dominio `.example`.

### 13.10 Riesgos / pendientes
- RSK-TKT001-01 y RSK-TKT001-02: CERRADOS.
- Nuevos: RSK-OPS-009 y RSK-OPS-010 (§10).
- Las imágenes `brujula/backend:0.0.0-dev` y `brujula/scheduler:0.0.0-dev` del host se reconstruyeron durante la validación (RSK-OPS-010). No se borraron, para no afectar a otros proyectos.

### 13.11 Archivos modificados
- `compose.yaml`
- `.env.example`
- `infra/docker/backend.Dockerfile`
- `infra/docker/gunicorn-logging.json` (nuevo)
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 13.12 Próximo agente
**Orquestador**, que debe:
1. Registrar DEC-AUTO-151, DEC-AUTO-152 y DEC-AUTO-153, y cerrar RSK-TKT001-01 y RSK-TKT001-02.
2. Integrar esta rama en `main`.
3. Después, el Developer de TKT-001 hace rebase o merge de `main` y repite su `docker compose up --wait`.

## 14. TKT-OPS-002 — endurecimiento tras QA (F7, soporte)

### 14.1 Estado
**COMPLETADO**, con un requisito para el Developer (REQ-OPS002-01, §14.3). Sin ese cambio, la protección frente a `X-Forwarded-Proto` falsificado queda a medias. Rama `tkt-ops-002-hardening`, sin merge: la integra el Orquestador tras QA.

### 14.2 Objetivo
Cerrar las observaciones de QA de TKT-001 y TKT-OPS-001: OBS-06, OBS-08/NV-QAOPS-01, RSK-OPS-010, NV-QAOPS-02 y RSK-OPS-009.

### 14.3 Cambios realizados
- **OBS-06 → DEC-AUTO-154** (`infra/docker/backend.Dockerfile.dockerignore`): se excluyen `**/tests`, `**/conftest.py` y `**/urls_prueba.py` del contexto de build.
  - Así no llegan a las imágenes `runtime` ni `scheduler`.
  - Nada del runtime los importa: pytest es dependencia `dev` y `uv sync --no-dev` no la instala.
  - Alternativa descartada: filtrar en el `COPY` del stage runtime. Es más frágil, y el `.dockerignore` además acelera el build.
- **OBS-08 / NV-QAOPS-01 → DEC-AUTO-155** (`compose.yaml`, `infra/docker/backend.Dockerfile`, `.env.example`):
  - La red `app` tiene una subred fija `${APP_NET_PREFIX:-10.231.40}.0/24`, con `ip_range` `.128/25` para las IP dinámicas.
  - El proxy tiene `ipv4_address` `.10`, fuera del rango dinámico, así que ningún otro contenedor puede recibir esa IP. Con `cap_drop: ALL` (sin NET_ADMIN), un contenedor tampoco puede cambiar su propia IP.
  - El backend recibe `GUNICORN_FORWARDED_ALLOW_IPS=${APP_NET_PREFIX}.10`. El `CMD` usa `--forwarded-allow-ips="${GUNICORN_FORWARDED_ALLOW_IPS:-127.0.0.1}"`: entrecomillado, para que un `*` no se expanda como glob, y con `127.0.0.1` por defecto (el de gunicorn), nunca `'*'`.
  - Alternativas descartadas:
    - (a) Confiar en toda la subred de `app`. No protege frente al frontend ni frente a servicios futuros.
    - (b) Resolver `proxy` por DNS al arrancar. Hay un ciclo: el proxy depende de que el backend esté healthy.
    - (c) Una red propia proxy-backend. También necesita una subred fija, y no aporta nada frente a una IP fija.
  - **Límite de la medida (demostrado, §14.8)**: gunicorn solo decide `wsgi.url_scheme` a partir de la cabecera. No la elimina: Django sigue recibiendo `HTTP_X_FORWARDED_PROTO`, y con `SECURE_PROXY_SSL_HEADER` la acepta venga de quien venga. La protección completa requiere un cambio en `backend/`, que DevOps no puede hacer (CLAUDE.md §0.3):
    - **REQ-OPS002-01 (ticket al Developer, `backend/config/settings/base.py`)**: `SECURE_PROXY_SSL_HEADER = None`. Con eso, `request.is_secure()` usa `wsgi.url_scheme`, que gunicorn solo toma de `X-Forwarded-Proto` si la petición viene de `GUNICORN_FORWARDED_ALLOW_IPS`.
      - Validado con un fixture de settings no versionado (§14.8, caso B).
      - Con este cambio, `check --deploy` no debería generar avisos nuevos: `security.W008` depende de `SECURE_SSL_REDIRECT`, no de `SECURE_PROXY_SSL_HEADER`. Debe confirmarlo el CI del Developer.
      - Afecta a RSK-OPS-014.
    - **REQ-OPS002-02 (propuesta, prioridad baja)**: la IP del cliente para el throttling (DRF `NUM_PROXIES`) se sigue tomando de `X-Forwarded-For` sin comprobar quién la envía (RSK-OPS-012).
      - Propuesta: usar `X-Forwarded-For` solo si `REMOTE_ADDR` está en una lista de emisores de confianza (proxy y frontend SSR, que la reenvía) inyectada por entorno.
      - Si no, usar `REMOTE_ADDR`.
- **RSK-OPS-010 → DEC-AUTO-156** (`compose.yaml`, `.env.example`): la etiqueta de todas las imágenes `brujula/*` y el ARG `APP_VERSION` usan `${APP_VERSION:-0.0.0-dev-${COMPOSE_PROJECT_NAME:-brujula}}`.
  - Compose v5 expone el `-p` como `COMPOSE_PROJECT_NAME` en la interpolación (verificado), así que `-p brujula-qa002` genera `brujula/backend:0.0.0-dev-brujula-qa002`.
  - `.env.example` deja `APP_VERSION=` vacío. El CI y las releases siguen fijando `APP_VERSION` explícito (`ci-<sha>`), por lo que los nombres que usa trivy/syft no cambian.
  - **Acción local**: los `.env` creados antes contienen `APP_VERSION=0.0.0-dev`. Hay que vaciar esa línea para obtener la etiqueta por proyecto.
- **NV-QAOPS-02 → DEC-AUTO-157** (`compose.yaml`, `init-volumes`):
  - Antes de `mkdir` y `chmod`, el script aborta con exit 1 si `/vol/media/publico` o `/vol/media/privado` son un enlace simbólico, o si existen y no son un directorio.
  - Los `chown` usan `-h`, así que nunca siguen enlaces.
  - **No hay carrera TOCTOU**: la comprobación se hace después de `chown 0:0 /vol/media`, así que en ese momento solo root puede crear, renombrar o sustituir entradas en `/vol/media`. `/vol/*` son puntos de montaje y no pueden ser enlaces.
  - Si aborta, `/vol/media` queda `root:root` y el backend no arranca, porque depende de `init-volumes` completado. La reparación es manual y como root (`rm` del enlace) y después se vuelve a ejecutar `up`. Es intencionado: un enlace ahí indica que se ha manipulado el volumen.
- **RSK-OPS-009 → DEC-AUTO-158** (`.github/workflows/ci.yaml`, job `images`): nuevo paso tras el smoke, "smoke: logs del backend 100 % JSON (arranque + parada)".
  - Ejecuta `docker compose stop backend`, guarda `reports/backend.log` (se publica como artefacto) y un script python3 falla si alguna línea no vacía no es un objeto JSON, o si no hay ninguna línea.
- **DEC-AUTO-159**: `APP_NET_PREFIX` es un único prefijo /24 (`10.231.40`) en lugar de tres variables (subred, rango, IP).
  - Está fuera de los pools por defecto de Docker (172.17-31.x, 192.168.x), para no chocar con las redes creadas automáticamente.
  - Coste: los proyectos simultáneos necesitan prefijos distintos (RSK-OPS-013; el error `Pool overlaps` es inmediato y no afecta al otro proyecto).

### 14.4 Versiones aprobadas
No cambia ninguna versión, imagen base ni acción. Validado con el backend de `main` @ 0151a4b (TKT-001): Django 5.2.17 y gunicorn 26.2.0.

### 14.5 Infraestructura
- Cambio de topología: la red `app` pasa a tener subred fija, y el proxy, IP fija.
- No cambian los puertos, límites, healthchecks ni capacidades.

### 14.6 Dependencias
No se modificó ninguna dependencia ni ningún lockfile.

### 14.7 Variables de entorno
- Nueva: `APP_NET_PREFIX` (Compose).
- Nueva e inyectada por compose: `GUNICORN_FORWARDED_ALLOW_IPS` (solo backend).
- `APP_VERSION` pasa a ser vacío por defecto en `.env.example`.
- Ninguna es un secreto.

### 14.8 Validaciones ejecutadas (2026-09-25, Docker Engine 29.6.1, Compose v5.2.0)
Entorno:
- Worktree de la rama.
- `.env` generado con `scripts/ops/init-env.sh` (valores aleatorios locales) y borrado al terminar.
- `-p brujula-ops002`, `APP_VERSION=ops002`, `PROXY_HOST_PORT=18082`, `APP_NET_PREFIX` por defecto.
- Frontend sustituido por un stub no versionado (python:3.13.15-slim fijado, uid 65534, 200 en :4000). Los fixtures están en el scratchpad, fuera del repo.

| Check | Resultado |
|---|---|
| `docker compose config --quiet`: base, `--profile ops`, +ci y +debug | VALIDADO: 4/4 |
| Etiquetas: sin `-p` → `0.0.0-dev-brujula`; con `-p brujula-ops002` → `0.0.0-dev-brujula-ops002`; con `APP_VERSION=ops002` → `ops002` | VALIDADO (`docker compose config`) |
| `up -d --build --wait` en volúmenes limpios: db, init-volumes, migrate, backend, proxy y el stub del frontend | VALIDADO: rc=0 en 48 s. Servicios de larga duración healthy; init-volumes y migrate con exit 0 |
| IPs: proxy `10.231.40.10`; backend `.129`, frontend `.130` y un contenedor efímero `.131` (rango dinámico) | VALIDADO |
| Proceso 1 del backend: `--forwarded-allow-ips=10.231.40.10` | VALIDADO (`/proc/1/cmdline`) |
| OBS-06: `find /app -name tests -o -name conftest.py -o -name urls_prueba.py` en `brujula/backend:ops002` y en `brujula/scheduler:ops002` | VALIDADO: 0 resultados en ambas. Contraste: la imagen anterior del host (`brujula/backend:0.0.0-dev`) contiene los 3. `manage.py`, `apps/` y `config/` presentes; migrate exit 0; `supercronic -test` del crontab: válido |
| **Falsificación de X-Forwarded-Proto** con `DJANGO_SECURE_SSL_REDIRECT=true`, `GET /api/v1/no-existe-ops002` directo a `backend:8000` | Ver las 3 filas siguientes |
| A) Settings actuales + gunicorn restringido | Contenedor efímero en `app`: sin XFP → **301**; con `XFP: https` → **404** (Django la trata como https: **la protección de infra sola NO basta**). Desde la IP del proxy: sin XFP → 301; con https → 404 |
| B) Fixture `SECURE_PROXY_SSL_HEADER = None` (REQ-OPS002-01) + gunicorn restringido | Contenedor efímero: sin XFP → **301**; con `XFP: https` → **301** (no se trata como https). Desde la IP del proxy (de confianza): con https → **404** (sí se trata como https). **Protección completa** |
| C) Control: fixture + `GUNICORN_FORWARDED_ALLOW_IPS="*"` | Contenedor efímero con `XFP: https` → 404: la restricción de gunicorn también es necesaria. El `*` llegó literal al proceso (sin expandirse como glob) |
| A través del proxy (config normal): `/health/ready` → 200 `{"status":"ok"}`; `/api/v1/no-existe-ops002` → 404; `/` → 200 (stub). Con `SSL_REDIRECT=true`: `/api/...` → 301 a https (el proxy envía `X-Forwarded-Proto: http`, correcto sin TLS) y `/health/ready` → 200 (exento) | VALIDADO |
| NV-QAOPS-02: `publico` sustituido (uid 10001) por un enlace a `/vol/backups` → init-volumes | VALIDADO: exit 1 "ABORTA: … es un enlace simbólico"; `/vol/backups` sigue 999:999 0700 (no se siguió el enlace) |
| NV-QAOPS-02: `publico` como archivo regular | VALIDADO: exit 1 "existe y no es un directorio" |
| Tras la reparación manual: init-volumes ×2 | VALIDADO: exit 0 las dos veces (idempotente). media 10001 0755, publico 0755, privado 0750, ops 0750, backups 999 0700 |
| RSK-OPS-009: script del paso nuevo del CI, extraído del YAML parseado, sobre el log real del backend tras `stop` | VALIDADO: 20/20 líneas JSON (rc=0, incluye `Shutting down: Master`). Con una línea de texto de gunicorn añadida → rc=1 con `::error::`. Con un log vacío → rc=1 |
| ci.yaml: YAML válido (js-yaml 4.1.0) y esquema de GitHub Actions (`@action-validator/cli` 0.6.0) | VALIDADO: rc=0 |
| gitleaks 8.30.1 (`dir`) sobre compose.yaml, .env.example, infra/, .github/ y docs/05_operacion/ | VALIDADO: no leaks found |
| Choque de subredes: segunda red `10.231.40.0/24` → `Pool overlaps`; `10.231.41.0/24` → OK | VALIDADO (RSK-OPS-013) |
| Limpieza: `--profile ops down -v` + `docker rmi` de `brujula/{backend,proxy,scheduler}:ops002` | VALIDADO: no queda ningún contenedor, volumen, red ni imagen `ops002`. No se tocaron `backend`, `frontend` y `db` (PROYECTO1) ni `brujula-tkt003-db-1`. El contenedor `backend` de PROYECTO1 ya estaba en `Restarting` antes de empezar: es ajeno a este ticket |

NOT_RUN y por qué:
- Frontend real: todavía no está en `main` (TKT-002 en curso).
- Perfil `ops` en ejecución: solo se construyó y probó el crontab del `scheduler`.
- trivy y syft: la imagen base no cambió (RSK-OPS-001, CI/F9).
- CI en GitHub: no hay remoto. El paso nuevo solo se validó en local, extraído del YAML.
- Un `check --deploy` con el fixture de REQ-OPS002-01: le corresponde al Developer en su ticket.

### 14.9 Seguridad
- Se reduce la superficie: gunicorn ya no acepta `X-Forwarded-*` de cualquier IP.
- init-volumes no sigue enlaces.
- La imagen runtime ya no incluye código de pruebas (rutas `urls_prueba`).
- No se añaden capacidades ni privilegios, y no hay secretos.
- Riesgo residual: RSK-OPS-011 hasta que se implemente REQ-OPS002-01, y RSK-OPS-012 y RSK-OPS-014 (§10).

### 14.10 Riesgos / pendientes
- Cerrados: RSK-OPS-009 y RSK-OPS-010.
- Nuevos: RSK-OPS-011 a RSK-OPS-014 (§10).

### 14.11 Archivos modificados
- `compose.yaml`
- `.env.example`
- `infra/docker/backend.Dockerfile`
- `infra/docker/backend.Dockerfile.dockerignore`
- `.github/workflows/ci.yaml`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 14.12 Próximo agente
**Orquestador**, que debe:
1. Enviar la rama a QA.
2. Registrar DEC-AUTO-154 a DEC-AUTO-159, cerrar RSK-OPS-009 y RSK-OPS-010 y abrir RSK-OPS-011 a RSK-OPS-014.
3. Emitir un Micro-Ticket al Developer para REQ-OPS002-01 (`backend/config/settings/base.py`; AC: con `DJANGO_SECURE_SSL_REDIRECT=true`, una petición directa a `backend:8000` desde una IP distinta de `${APP_NET_PREFIX}.10` con `X-Forwarded-Proto: https` → 301; desde el proxy → no redirige; `check --deploy` sin avisos). REQ-OPS002-02 es opcional.
4. Tras el merge, avisar a quien use un `.env` local antiguo de que vacíe `APP_VERSION`, y a los proyectos paralelos de que usen su propio `APP_NET_PREFIX`.

## 15. TKT-OPS-003 — CI verde, proxy conforme al contrato, gzip y Dependabot (F7, soporte)

### 15.1 Estado
**COMPLETADO**. Rama `tkt-ops-003-ci-verde`, que parte de `tkt-ops-002-hardening` y la incluye. Sin merge: la integra el Orquestador mediante PR con pipeline verde.

CI de GitHub:
- `infraestructura` y `backend`: en verde.
- `frontend`, `images` (build + trivy + SBOM + smoke) y `sign`: se omiten por diseño en esta rama, porque no hay `frontend/`.
- Por eso trivy **no se ha ejecutado** en GitHub y RSK-OPS-001 sigue abierto (Puerta Humana).

### 15.2 Objetivo
- CI rojo de `main` (run 36218734526).
- F-01 de QA TKT-002: JS del SSR sin comprimir.
- HALLAZGO-QA-OPS002-02: 429 del proxy en `text/html`.
- DEC-AUTO-180: Dependabot.
- OBS-QA-OPS002-03: runbook de init-volumes.
- OBS-QA-OPS002-04: semgrep `p/docker-compose`.
- Ampliación OBS-QA003-02: código solo de pruebas en la imagen del backend.

### 15.3 Cambios realizados

**CI (`.github/workflows/ci.yaml`)**
- **INFRA-DB-000** (job `infraestructura`):
  - `datlocprovider` es de tipo `"char"`, y en PostgreSQL 18 `"char" || unknown` es ambiguo. Se cambia a `datlocprovider::text||':'||datlocale`. No había más SQL con ese patrón.
  - El valor se imprime (`brujula locale: b:C.UTF-8`) y se compara con `test`.
  - La BD se para en un paso aparte con `if: always()`.
- **Job `backend`** (DEC-AUTO-197): el `.env` efímero y las variables se generan antes del typecheck.
  - Variables: `DJANGO_SECRET_KEY`, `THROTTLE_HMAC_KEY`, `MFA_FERNET_KEY` y `DB_PASSWORD`.
  - Motivo: el plugin de django-stubs de mypy carga los settings, que fallan cerrados si falta `DB_PASSWORD`.
  - Además, "parar BD" necesitaba el `.env` para interpolar `compose.yaml`.
- **Gate de contrato incremental** (DEC-AUTO-196). El `oasdiff diff --fail-on-diff` literal no podía pasar nunca: el contrato API-first tiene 127 operaciones y componentes escritos a mano, y drf-spectacular solo genera lo implementado, con sus propios nombres de componentes. Ahora:
  - (1) Falla si una operación implementada no está en el contrato.
  - (2) `oasdiff breaking contrato → generado --match-path <rutas implementadas> --fail-on WARN`.
  - En el job `images`, schemathesis se limita a las rutas públicas y de health que expone el backend en ejecución (esquema generado dentro del contenedor).
- **SAST de compose** (OBS-QA-OPS002-04, DEC-AUTO-192). Las reglas `p/docker-compose` de semgrep solo se aplican a YAML con clave `version:` y no resuelven anclas ni merge keys (`<<: *hardening`).
  - Sobre `compose.yaml` en bruto, con `version:` añadido, dan 14 falsos positivos: `read_only` y `no-new-privileges` sí están, vía `*hardening`.
  - El nuevo paso escanea la salida resuelta de `docker compose [-f compose.ci.yaml|-f compose.debug.yaml] --profile ops config`, con `version: "3.9"` antepuesto.
  - La salida se escribe en `$RUNNER_TEMP` y no se publica, porque contiene los valores efímeros del `.env`.
  - Se usa `pipx run semgrep==1.178.0`.
- **Smoke del proxy** (job `images`). Comprueba que:
  - una ráfaga de 250 peticiones produce algún 429, y todos los 429 son `application/problem+json`;
  - `/health/live` responde 200;
  - una URI de 9 KB responde `400 application/problem+json`;
  - el primer `.js` del HTML del SSR llega con `Content-Encoding: gzip`.

**Proxy (`infra/proxy/nginx.conf`)**
- **gzip** (F-01, DEC-AUTO-191):
  - Se añade `text/javascript`, el tipo con el que Express sirve `.js` y `.mjs` (RFC 9239).
  - Se añaden también `application/manifest+json`, `gzip_comp_level 5` y `gzip_proxied any`, para comprimir también detrás de un balanceador que añada `Via`.
  - `gzip_vary on` ya existía.
- **429 como Problem Details** (HALLAZGO-QA-OPS002-02, DEC-AUTO-190): `error_page 429 =429 /_errores_proxy/429`, una location `internal`. La respuesta lleva:
  - `application/problem+json`, `code: limite_tasa`, y `title`/`detail` del catálogo del backend;
  - `trace_id` igual al trace-id del `traceparent` propagado (el del cliente si es válido; si no, `$request_id`, 32 hex);
  - `X-Trace-Id`, `Retry-After: 1` (la zona repone 20 r/s), `Cache-Control: no-store` y `nosniff`.
- **Resto de errores propios del proxy** (DEC-AUTO-194). Se usan locations internas por URI porque una location con nombre no admite URI vacía, y el 414 acababa en 500.
  - 400/414/494 → 400 `parametro_invalido`, con `errors._general`, porque varios 400 del contrato son `ProblemaValidacion`.
  - 413 → `carga_demasiado_grande`.
  - 502/503/504 → 503 `servicio_no_disponible`, con `Retry-After: 5`.
  - `proxy_intercept_errors` sigue en off: los errores que genera el backend no se tocan.
- **`/health/*` fuera del límite de borde** (DEC-AUTO-193): la clave de `limit_req_zone` es un `map` que vale "" (no contabiliza) para `/health/live|ready`. El contrato solo documenta 200/503 para health, y schemathesis lo detectaba.
- **`large_client_header_buffers 4 4k`** (DEC-AUTO-195):
  - gunicorn rechaza las líneas de petición de más de 4094 bytes con un 400 `text/html`. Con este ajuste, nginx rechaza antes y responde con Problem Details.
  - El total es 16 KB, igual que el límite de cabeceras por defecto de Node (SSR).

**Dependabot (`.github/dependabot.yml`, DEC-AUTO-180/198)**

Frecuencia semanal, los lunes a las 06:00 Europe/Madrid.

| Ecosistema | Directorio | Límite de PR | Notas |
|---|---|---|---|
| npm | `/frontend` | 3 | Grupo Angular minor/patch, `versioning-strategy: increase` |
| uv | `/backend` | 3 | Ecosistema nativo |
| docker | `/infra/docker`, `/infra/proxy`, `/infra/backup` | 2 | |
| docker-compose | `/` | 1 | Imágenes postgres de `compose.yaml` |
| github-actions | `/` | 2 | Agrupadas |

- Sin `labels`: una etiqueta personalizada que no existe genera errores.
- Los PR de manifest los propone Dependabot, pero se integran como ticket al Developer y pasan por QA (CLAUDE.md §0.3).

**Imagen del backend (`infra/docker/backend.Dockerfile.dockerignore`)** (OBS-QA003-02, DEC-AUTO-199)
- Se excluyen `apps/ops/bd_pruebas` y `config/settings/test.py`, además de `**/tests`, `**/conftest.py` y `**/urls_prueba.py`.
- Efecto intencionado: con `DJANGO_ENV=test`, un contenedor falla al arrancar (`ModuleNotFoundError`) en lugar de activar la configuración de pruebas.

### 15.4 Versiones aprobadas
No cambia ninguna imagen base, acción ni herramienta. Se usan versiones ya fijadas: oasdiff 1.32.1, semgrep 1.178.0 y nginx 1.30.5.

### 15.5 Infraestructura
- Proxy: gzip, errores propios como Problem Details, health sin límite de borde y cabeceras de hasta 4 KB.
- Sin cambios de topología, puertos, límites de recursos ni capacidades.

### 15.6 Dependencias
No se modificó ningún manifest ni lockfile.

### 15.7 Variables de entorno
No hay variables nuevas.

Nota: el `type` de los Problem Details del proxy usa literalmente el valor por defecto de `PROBLEM_TYPE_BASE_URL` (`https://brujulasalvaje.example`), porque `nginx.conf` es estático (RSK-OPS-015).

### 15.8 Validaciones ejecutadas (2026-09-26, Docker Engine 29.6.1, Compose v5.2.0)

Entorno local:
- Copia temporal fuera del repo: esta rama más el `frontend/` real de `origin/tkt-002-frontend-base`.
- `-p brujula-ops003`, `APP_NET_PREFIX=10.231.43`, `PROXY_HOST_PORT=18093`, `APP_VERSION` vacío.
- `.env` generado con `init-env.sh`.

| Check | Resultado |
|---|---|
| `docker compose --profile ops config --quiet`, build de 5 imágenes y `up -d --wait` | VALIDADO: db, backend, frontend y proxy healthy. init-volumes y migrate terminan con exit 0 |
| gzip de `main-*.js` (`text/javascript`) con `Accept-Encoding: gzip` | VALIDADO: `Content-Encoding: gzip` y `Vary: Accept-Encoding`; 410.496 B → 126.062 B. CSS y HTML también salen en gzip. Antes del cambio, el JS salía sin comprimir (F-01) |
| 429 con ráfagas de 200-300 peticiones | VALIDADO: `application/problem+json` con `X-Trace-Id`, `Retry-After: 1` y `no-store`. Con `traceparent` del cliente, `trace_id` = su trace-id. El cuerpo valida contra `components.schemas.Problem` (jsonschema + FormatChecker) |
| `/health/live`: 300 peticiones, 60 en paralelo | VALIDADO: 300 × 200. Antes: 43 × 429 |
| URI de 9 KB; cabecera de 9 KB; cuerpo de 3 MB; frontend parado | VALIDADO: 400 / 400 / 413 / 503, todos `application/problem+json`. En la frontera de línea (4093-4100 B), siempre problem+json. Antes: 400 HTML de gunicorn |
| schemathesis 4.28.0 vía proxy, `^/(api/v1/publico|health)/`, 4 checks, 5 ejecuciones | Sin fallos de infraestructura. Solo quedan 404 de endpoints públicos del contrato que el backend aún no implementa (DEV-OPS003-01, no es de DevOps). Antes aparecían además: 429 en health, 414/400 en `text/html` y un 400 sin `errors` |
| schemathesis sobre las rutas implementadas (script del paso nuevo del CI) | VALIDADO: `^(/health/live|/health/ready)$`; todos los casos generados pasan |
| Smoke nuevo del CI (script extraído del YAML y ejecutado contra el stack) | VALIDADO: rc=0 (429 problem+json, URI larga 400 problem+json, JS en gzip) |
| Gate de contrato (script extraído) con oasdiff 1.32.1 | VALIDADO: caso positivo rc=0. Negativos: ruta no documentada → rc=1; `200`→`201` en `/health/ready` → `response-success-status-removed`, rc=1 |
| semgrep `p/docker-compose` sobre la config resuelta (3 variantes) | VALIDADO: 0 hallazgos. Control negativo (servicio sin endurecer): 2 hallazgos, rc=1. Sin `version:` no se aplica ninguna regla (confirma OBS-04) |
| OBS-QA003-02: backend de `origin/tkt-003-modelo-datos` con el dockerignore nuevo, targets `runtime` y `scheduler` | VALIDADO: ambos construyen. `find` de `tests`, `conftest.py`, `urls_prueba.py`, `bd_pruebas` y `test.py`: 0 resultados. `manage.py check`: sin problemas en ambos. `DJANGO_ENV=test` → `ModuleNotFoundError: config.settings.test`. El backend de esta rama, reconstruido, sigue healthy |
| Runbook de init-volumes (§15.9), con un enlace `publico -> /tmp` creado desde el backend | VALIDADO: init-volumes sale con exit 1 "ABORTA…". Inspección y reparación con los comandos del runbook. Después, `up` → exit 0 y `publico` queda 10001 0755 |
| `dependabot.yml` contra el esquema de SchemaStore (`dependabot-2.0.json`) | VALIDADO. El esquema incluye `uv` y `docker-compose` |
| `ci.yaml` con `@action-validator/cli` 0.6.0; gitleaks 8.30.1 `dir` sobre `.github` e `infra` | VALIDADO: rc=0; no leaks found |
| GitHub Actions, `workflow_dispatch` sobre la rama | Resultado en el HANDOFF_ENVELOPE. `infraestructura`: locale `b:C.UTF-8`, semgrep compose con 0 hallazgos, gitleaks sin fugas. `backend`: ruff, mypy, 79 tests, cobertura del 99 %, `check --deploy`, gate de contrato 2/127 sin cambios incompatibles, bandit y semgrep sin hallazgos, pip-audit sin vulnerabilidades. `frontend`, `images` y `sign`: SKIPPED |

NOT_RUN y por qué:
- **Job `images` en GitHub** (trivy, syft, smoke, schemathesis y el smoke nuevo): se omite porque la rama no tiene `frontend/`. Se ejecutará en el PR que integre TKT-002. Si falla SOLO por CVE HIGH/CRITICAL de las imágenes base, es RSK-OPS-001 (Puerta Humana).
- **Lighthouse (LCP)** tras el gzip: no se volvió a medir; las cifras de 2.29-2.45 s son las de QA.
- **Dependabot real**: solo se ejecuta sobre la rama por defecto. Se verifica tras el merge en Insights → Dependency graph → Dependabot.

### 15.9 Runbook: init-volumes aborta (OBS-QA-OPS002-03)

**Síntoma**
- `up` termina con `service "init-volumes" didn't complete successfully: exit 1`.
- El log dice `ABORTA: /vol/media/publico es un enlace simbólico`, o bien `existe y no es un directorio`.
- Un backend que ya estaba en marcha sigue funcionando. Uno recién creado no arranca, porque depende de init-volumes.

**Qué significa:** alguien con uid 10001 (el backend) sustituyó `publico` o `privado` en el volumen de medios. Trátalo como **posible manipulación** y conserva la evidencia antes de reparar.

    P=brujula     # el -p del proyecto compose
    IMG=postgres:18.6-trixie@sha256:5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722
    docker compose -p $P logs --no-log-prefix init-volumes | tail -5
    # 1) Evidencia (solo lectura): destino del enlace y propietario
    docker run --rm --network none --read-only --cap-drop ALL -v ${P}_media:/vol/media:ro $IMG ls -la /vol/media
    # 2) Eliminar SOLO la entrada señalada (rm de un enlace borra el enlace, nunca su destino).
    #    Si es un archivo regular con valor forense, cópialo antes.
    docker run --rm --network none --read-only --user 0:0 --cap-drop ALL --security-opt no-new-privileges:true \
      -v ${P}_media:/vol/media $IMG rm -f -- /vol/media/publico      # o /vol/media/privado
    # 3) Volver a ejecutar: init-volumes recrea el directorio (10001, 0755/0750; idempotente)
    docker compose -p $P up -d --wait

Notas:
- No hace falta `DAC_OVERRIDE`: tras el abort, `/vol/media` es `root:root 0755`, así que root, como propietario, puede borrar.
- Nunca uses `rm -rf`: el abort solo se produce con un enlace o con algo que no es un directorio.
- El Orquestador debe registrar el incidente en `audit_log.md`.

### 15.10 Riesgos / pendientes

| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-015 | El `type` de los Problem Details del proxy usa literalmente `https://brujulasalvaje.example`. Si un entorno cambia `PROBLEM_TYPE_BASE_URL`, el proxy y Django dejan de coincidir | LOW | Los clientes deciden por `code`, no por `type`. En el ADR de producción: plantilla de nginx (envsubst) o un valor fijo común | ABIERTO |
| RSK-OPS-016 | `/health/live|ready` no tiene límite de borde, y `ready` hace un `SELECT 1` | LOW | Coste mínimo por petición. En producción, los sondeos del balanceador van por la red interna y el borde TLS puede restringir `/health/` | ABIERTO (F9) |
| RSK-OPS-017 | Dependabot `docker` quizá no detecte los `FROM ${ARG}` parametrizados. La entrada npm `/frontend` falla hasta que exista `frontend/` en `main` | LOW | La entrada `docker-compose` cubre postgres. Verificar tras el merge; si no aparecen PR de Docker, pasar a `FROM` literal (ticket a DevOps) | NOT_VALIDATED |
| RSK-OPS-018 | gunicorn limita el número de cabeceras (`limit_request_fields` 100) y nginx no. Con más de 100 cabeceras, gunicorn responde 400 en `text/html` | LOW | Es un caso anómalo. Opcional: `--limit-request-fields` o un módulo de borde | ACEPTADO (local) |
| RSK-OPS-019 | El gate de contrato del CI solo cubre las operaciones implementadas: una operación del contrato sin implementar no hace fallar el CI | LOW | Intencionado durante F7 (DEC-AUTO-196). QA ejecuta schemathesis completo en cada ticket. En F9, exigir cobertura total (implementadas == contrato) | ABIERTO |
| OBS-OPS003-01 | Los assets CSS del SSR llevan `X-Content-Type-Options` duplicado (Express + snippet de nginx) | INFO | Inocuo; se puede quitar de uno de los dos lados | ABIERTO |
| DEV-OPS003-01 | Endpoints públicos del contrato que responden 404 porque aún no están implementados: `/api/v1/publico/busqueda`, `/inicio`, `/escalas`, `/configuracion`, `/facetas/destinos`, `/meses`, entre otros | — | Tickets de backend en F7 | Fuera del alcance de DevOps |

Estado de riesgos anteriores:
- **RSK-OPS-007**: validado en GitHub para `infraestructura` y `backend`; `frontend` e `images` siguen NOT_RUN.
- **RSK-OPS-001**: sin cambios (REQUIERE INTERVENCIÓN).

### 15.11 Archivos modificados
- `.github/workflows/ci.yaml`
- `.github/dependabot.yml` (nuevo)
- `infra/proxy/nginx.conf`
- `infra/docker/backend.Dockerfile.dockerignore`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 15.12 Próximo agente
**Orquestador**, que debe:
1. Enviar la rama a QA.
2. Integrarla mediante un PR a `main`. La rama incluye TKT-OPS-002, así que este PR sustituye al de `tkt-ops-002-hardening`.
3. Registrar DEC-AUTO-190 a DEC-AUTO-199 y RSK-OPS-015 a RSK-OPS-019.
4. Tras integrar TKT-002 (frontend), comprobar que el job `images` llega a ejecutarse. Si trivy falla solo por las imágenes base, aplicar RSK-OPS-001 como Puerta Humana.

### 15.13 Corrección antes del merge: gitleaks en el PR #4 (DEC-AUTO-207)
- **Causa:** `actions/checkout` con `fetch-depth: 0` trae todas las ramas publicadas, y `gitleaks git` (por defecto `--all`) las escanea todas. Encontró un falso positivo `generic-api-key` en la rama `tkt-004-acceso-panel`: el vector público de TOTP del RFC 6238 apéndice B, verificado por el Orquestador.
- **Cambio en el workflow:** el paso de gitleaks usa `--log-opts="--full-history HEAD"`. Escanea todo el historial alcanzable desde el commit que se prueba: el merge de prueba en un PR, o `main` en un push.
- **`.gitleaksignore`** (raíz, nuevo, DEC-AUTO-207): contiene una única huella exacta, `b9f1a34…:backend/apps/cuentas/tests/test_ac_tkt004_01_login.py:generic-api-key:396`. Sin reglas ni rutas genéricas.
- **Validado en un clon del scratchpad**, con el merge de prueba `main` + esta rama y `tkt-004` presente:

  | Caso | Resultado |
  |---|---|
  | `--all` sin cambios | 1 hallazgo (reproduce el fallo del CI) |
  | Paso nuevo | 0 hallazgos |
  | `--all` con `.gitleaksignore` | 0 hallazgos |
  | `tkt-004` integrado en HEAD, con `.gitleaksignore` | 0 hallazgos |
  | `tkt-004` integrado en HEAD, sin `.gitleaksignore` | 1 hallazgo (la huella es lo que lo suprime) |
  | Control negativo: commit con una clave AWS y una API key falsas | 2 hallazgos, rc=1 |

## 16. TKT-OPS-004 — gate de contrato por operación, límite de /health y errores del proxy (F7, soporte)

### 16.1 Estado
**COMPLETADO**: validado en local (§16.8) y en GitHub Actions (§16.13).
Rama: `tkt-ops-004-gate-health`, creada desde `origin/main` (1e597be).

### 16.2 Objetivo
Cerrar los hallazgos de la QA de TKT-OPS-003:
- HALLAZGO-QA-OPS003-01 (MEDIUM): el gate no detectaba N9 (código de estado no documentado) ni N10 (propiedad de respuesta extra).
- HALLAZGO-QA-OPS003-02 (LOW): el gate daba un falso positivo con una ruta implementada solo en parte (N11).
- RSK-OPS-016: `/health/live|ready` no tenía límite de borde.
- OBS-QA-OPS003-03 y OBS-QA-OPS003-04: cabeceras de seguridad en los errores del proxy, y 403/404 del proxy como Problem Details.
- DEC-AUTO-210: Dependabot sin actualizaciones semver-major.

### 16.3 Cambios realizados
- **`infra/ci/gate_contrato.py`** (nuevo, DEC-AUTO-211). Sustituye al script en línea del paso de contrato del job `backend`. Solo depende de PyYAML.
  1. Operaciones (método + ruta, con los parámetros de ruta normalizados) generadas ⊆ contrato. Detecta N1 y N2.
  2. Por operación, cada código de estado generado debe estar en el contrato: exacto, rango `NXX` o `default`. Detecta N3 y N9.
  3. Por operación y código, cada media type generado debe estar en el contrato. Detecta N8.
  4. Por operación, código y media type, las propiedades de respuesta generadas ⊆ las del contrato. Es recursivo (propiedades, `items`, `$ref`), fusiona `allOf` y trata `oneOf`/`anyOf` como unión. Detecta N10.
     - Un objeto del contrato solo admite propiedades nuevas si declara `additionalProperties: true` o un esquema, como el mapa `errors`.
     - Sin `additionalProperties`, el objeto se trata como cerrado: exponer un campo no documentado es un riesgo de fuga de datos.
  5. Escribe el **contrato filtrado por operación**: solo las operaciones implementadas, con la ruta tal como está en el contrato y los parámetros y claves comunes del path item.
     - `oasdiff breaking contrato-filtrado generado --fail-on WARN` compara el resto (N4-N7, N12).
     - Ya no se usa `--match-path` por ruta, que era la causa del falso positivo `api-removed-without-deprecation` de N11.
- **`.github/workflows/ci.yaml`, job `backend`:** el paso "contrato" invoca `../infra/ci/gate_contrato.py` y después `oasdiff breaking` sobre el contrato filtrado. oasdiff sigue en la versión 1.32.1, verificado con sha256.
- **`infra/proxy/nginx.conf`:**
  - **Zona `salud`** (DEC-AUTO-214, sustituye a DEC-AUTO-193): `limit_req_zone $binary_remote_addr zone=salud:1m rate=50r/s` con `limit_req zone=salud burst=200 nodelay` en `= /health/live` y `= /health/ready`.
    - Un `limit_req` en la location anula el heredado del servidor, así que `/health` solo cuenta contra `salud` y no compite con el cupo de `/api`.
    - Se elimina el `map $clave_limite`: `por_ip` vuelve a usar `$binary_remote_addr`.
    - El 429 sale por la misma location interna Problem Details, con `Retry-After: 1`.
  - **403/404 del proxy como Problem Details** (DEC-AUTO-213):
    - `error_page 403 =403 /_errores_proxy/403`: `permiso_denegado`, para `limit_except ... deny all` en el SSR y en los medios.
    - `error_page 404 =404 /_errores_proxy/404`: `no_encontrado`, para `return 404`, `/health/*` desconocido, `/media/**` no público y medios inexistentes.
    - Se mantiene el estado 403, sin cambiarlo a 405, para no alterar el comportamiento. Los 403/404 del SSR y de Django no pasan por aquí (`proxy_intercept_errors off`).
- **`infra/proxy/snippets/security-headers-error.conf`** (nuevo, DEC-AUTO-212). Se incluye en todas las `/_errores_proxy/*` (400, 403, 404, 413, 429, 503). Contiene:
  - `X-Trace-Id`, `Cache-Control: no-store` y `nosniff`.
  - La CSP de API del contrato, igual que `API_CONTENT_SECURITY_POLICY` de Django.
  - `Referrer-Policy`, `Permissions-Policy`, COOP, CORP, `X-Frame-Options: DENY` y `X-Robots-Tag: noindex, nofollow`.
  - El Dockerfile del proxy ya copia `snippets/*.conf`, así que no cambia.
- **Smoke del proxy en el CI (job `images`):** comprueba los 404 (`/health/otra`, `/media/privado/x.jpg`), el 403 (`POST /`) y el 400 (URI larga). Para cada uno exige Problem Details, `status` y `trace_id` en el cuerpo, y 6 cabeceras de seguridad. Además:
  - 120 sondeos secuenciales a `/health/live`, todos con 200.
  - Una ráfaga keep-alive de 1000 peticiones (20×50), con Python y no con `curl`/`xargs`, que es lento en runners o hosts Windows. Debe producir `429 application/problem+json`, y solo 200 o 429.
  - Tras 5 s, `/health/ready` devuelve 200.
- **`.github/dependabot.yml`** (DEC-AUTO-210): `ignore: [{dependency-name: "*", update-types: ["version-update:semver-major"]}]` en los 5 ecosistemas (npm, uv, docker, docker-compose, github-actions).
  - Parches y menores se mantienen.
  - Según la documentación de GitHub, `ignore` afecta a las actualizaciones de versión. Las de seguridad dependen del ajuste del repositorio (ver RSK-OPS-021).
  - Sin anclas YAML, por compatibilidad con el parser de Dependabot.

### 16.4 Versiones aprobadas
Sin cambios: nginx-unprivileged 1.30.5-alpine con digest, oasdiff 1.32.1, schemathesis 4.28.0 y PyYAML del lock del backend.

### 16.5 Infraestructura
- Topología sin cambios.
- Límites de borde:
  - `por_ip`: 20 r/s, burst 60, todo el servidor salvo `/health/live|ready`.
  - `salud`: 50 r/s, burst 200, solo `/health/live|ready`.

### 16.6 Dependencias
Ninguna.

### 16.7 Variables de entorno
Ninguna nueva.

### 16.8 Validaciones ejecutadas (2026-09-26, Docker Engine 29.6.1, Compose v5.2.0)

#### 16.8.1 Gate de contrato
Réplica exacta del paso de CI: `gate_contrato.py` y `oasdiff 1.32.1` linux_amd64, con sha256 verificado. Los controles N1-N12 son los de la QA de TKT-OPS-003.

| Control | Contrato | Esperado | rc | Detectado por |
|---|---|---|---|---|
| Base (esquema generado de `main`) | main | 0 | 0 | — |
| N1 ruta no documentada | main | 1 | 1 | gate: operación no documentada |
| N2 método no documentado | main | 1 | 1 | gate: operación no documentada |
| N3 200 → 201 | main | 1 | 1 | gate: código no documentado |
| N4 parámetro requerido nuevo | main | 1 | 1 | oasdiff `new-required-request-parameter` |
| N5 tipo de respuesta cambia | main | 1 | 1 | oasdiff `response-property-type-changed` |
| N6 enum de respuesta ampliado | main | 1 | 1 | oasdiff `response-property-enum-value-added` |
| N7 propiedad pasa a opcional | main | 1 | 1 | oasdiff `response-property-became-optional` |
| N8 media type cambia | main | 1 | 1 | gate: media type no documentado |
| **N9** 500 text/html nuevo | main | 1 | **1** | gate: código no documentado (antes rc=0) |
| **N10** propiedad extra (`additionalProperties: false`) | main | 1 | **1** | gate: propiedad no documentada (antes rc=0) |
| N11 (fixture de QA: GET *stub* sin POST) | main | 1 | 1 | oasdiff `api-security-removed`, `response-media-type-removed`, `request-parameter-removed` (nota 1) |
| N12 parámetro de ruta renombrado | main | 1 | 1 | oasdiff `new-request-path-parameter`, … |
| **P1** (N11 fiel: GET copiado del contrato, sin POST) | main | 0 | **0** | — (antes rc=1 por `api-removed-without-deprecation`) |
| P2 esquema real de TKT-004 sin el PATCH de `/cuentas/{id}` | main | 0 | 0 | — |
| Esquema real de TKT-004 (`origin/tkt-004-acceso-panel` 9c63bec, con `apps/core/esquema.py`) | tkt-004 | 0 | 0 | 25 operaciones comparadas, 0 errores |
| T1 TKT-004 + propiedad extra en `SesionEstado` | tkt-004 | 1 | 1 | gate: propiedad no documentada |
| T2 TKT-004 + `500 text/html` en login | tkt-004 | 1 | 1 | gate: media type no documentado |
| T3 TKT-004 + propiedad extra en `Cuenta` (dentro de `resultados[]`) | tkt-004 | 1 | 1 | gate: propiedad no documentada (anidada) |
| T4 TKT-004 + propiedad extra en `Problem` | tkt-004 | 1 | 1 | gate: propiedad no documentada |

Nota 1: el fixture N11 de QA define el GET como *stub*, sin `security`, parámetros ni `content`, así que sigue fallando por esas diferencias reales. El falso positivo de la operación POST "eliminada" desaparece (0 apariciones de `api-removed`). P1 es el control fiel y pasa.

El gate anterior, sobre los mismos ficheros, da P1 rc=1 (`api-removed-without-deprecation`), N9 rc=0 y N10 rc=0. Reproduce los hallazgos.

`ruff check` y `ruff format --check` (ruff 0.16.9 y configuración del backend) pasan sobre `infra/ci/gate_contrato.py`.

#### 16.8.2 Proxy
Stack local `-p brujula-ops004`, `APP_NET_PREFIX=10.231.49`, puerto 18494 e imágenes con `APP_VERSION=ops004`, para no pisar `brujula/*:0.0.0-dev` de las QA. Árbol temporal fuera del repositorio: esta rama más `frontend/` de `origin/tkt-002-frontend-base`.

| Comprobación | Resultado |
|---|---|
| `docker compose config -q`, build y `up --wait` | OK. proxy, backend, frontend y db en estado healthy; migrate terminó (Exited) |
| `nginx -t` | OK |
| Paso "smoke: errores del proxy…" del CI, extraído literalmente (solo cambian el puerto y `/tmp`) | rc=0 |
| Ráfaga a `/api` (250 × P50) | 217 × 404 y 33 × 429, todas `application/problem+json`. El 404 es del backend: `publico/inicio` aún no está implementado (DEV-OPS003-01) |
| 120 sondeos secuenciales a `/health/live` | 120 × 200 |
| Ráfaga keep-alive a `/health/live` (1000) | 222 × 200 y 778 × `429 application/problem+json` |
| Cabeceras de 429 (`/health/ready`), 404 (`/media/publico/no/existe.webp`) y 503 (backend parado) | Las 11 cabeceras de `security-headers-error.conf`. `Retry-After` 1 en el 429 y 5 en el 503 |
| 403 en `POST /` y 404 en `/health/otra` | Problem Details con `permiso_denegado` / `no_encontrado` y `trace_id` de 32 hex |
| HTML del SSR | CSP con nonce y `X-Frame-Options` sin cambios |
| schemathesis 4.28.0 sobre `/health/live|ready` a través del proxy (checks del CI) | 9 generados, 9 pasados |

- **Dependabot:** `.github/dependabot.yml` valida contra el JSON Schema `dependabot-2.0` (el mismo de la QA de TKT-OPS-003) con 0 errores. Los 5 ecosistemas tienen `ignore` semver-major.
- **Limpieza:** `docker compose -p brujula-ops004 --profile ops down -v`, imágenes `brujula/*:ops004` eliminadas y árbol temporal borrado. No se tocaron `backend`, `frontend`, `db` (PROYECTO1), `brujula-qa004` ni `brujula-qa002b`.

#### 16.8.3 GitHub Actions
Ver §16.13.

### 16.9 Seguridad
- Los errores del borde llevan la misma política de cabeceras que la API, lo que cierra OBS-QA-OPS003-03.
- `/health/ready` deja de ser un amplificador sin límite hacia la BD (RSK-OPS-016).
- El gate impide exponer campos de respuesta no documentados.
- Sin secretos nuevos; el `.env` es efímero y local.

### 16.10 Riesgos / pendientes

| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-016 | `/health` sin límite de borde | LOW-MEDIUM | Zona `salud` de 50 r/s con burst 200 (DEC-AUTO-214) | **MITIGADO** |
| RSK-OPS-020 | El contrato documenta solo 200/503 para `/health/*`, pero el borde puede responder 429 (ráfaga de más de 200 por encima de 50 r/s desde una IP) y 404 Problem Details | LOW | Ticket a **backend-contrato**: añadir `429: LimiteTasa` a `saludLive`/`saludReady`, o documentarlo como respuesta del borde. schemathesis a ritmo normal no lo alcanza (9/9) | ABIERTO |
| RSK-OPS-021 | Dependabot: `ignore` con `update-types` se aplica a las actualizaciones de versión. Las de seguridad dependen de que "Dependabot security updates" esté activado en el repositorio, un ajuste fuera del alcance del fichero | LOW | Verificar en Settings → Code security (Orquestador) | NOT_VALIDATED |
| RSK-OPS-022 | Detrás de un balanceador o CDN sin `real_ip`, todas las peticiones comparten IP y las zonas `por_ip`/`salud` se vuelven globales | MEDIUM (prod) | En el ADR de producción (F9): `set_real_ip_from` + `real_ip_header`, o sondeos por la red interna | ABIERTO (F9) |
| RSK-OPS-019 | El gate no exige cobertura total del contrato | LOW | Sin cambios: intencionado en F7 | ABIERTO |
| OBS-OPS004-01 | El job `images` (smoke y schemathesis del CI) sigue NOT_RUN en GitHub mientras `frontend/` no esté en `main` | INFO | Validado en local (§16.8.2). Se ejecutará automáticamente cuando TKT-002 se integre | NOT_RUN (GitHub) |

### 16.11 Archivos modificados
- `infra/ci/gate_contrato.py` (nuevo)
- `infra/proxy/snippets/security-headers-error.conf` (nuevo)
- `infra/proxy/nginx.conf`
- `.github/workflows/ci.yaml`
- `.github/dependabot.yml`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 16.12 Próximo agente
**Orquestador**, que debe:
1. Enviar la rama a QA.
2. Registrar DEC-AUTO-211 a DEC-AUTO-214 y RSK-OPS-020 a RSK-OPS-022.
3. Emitir el ticket de contrato de RSK-OPS-020 a backend-contrato.
4. Tras integrar esta rama, TKT-004 (PR #8) ejecutará el gate nuevo al actualizarse con `main`. Su backend ya lo pasa (§16.8.1). Los checks obligatorios son de job, y sus nombres no cambian.

### 16.13 Validación en GitHub Actions
- Run `workflow_dispatch` sobre `tkt-ops-004-gate-health` en c50a196: https://github.com/magoolf/brujula-salvaje/actions/runs/36253555771. Resultado: **success**.
  - `infraestructura`: OK (35 s).
  - `detectar código`: OK.
  - `backend`: OK (1 min 38 s). El paso de contrato imprime `contrato: 127 operaciones; implementadas: 2; comparadas: 2; no documentadas: 0; errores: 0`, y `oasdiff breaking` sobre el contrato filtrado no encuentra cambios incompatibles.
  - `frontend`, `images` y `firma`: omitidos (NOT_RUN), porque `frontend/` aún no está en `main` (OBS-OPS004-01). El smoke del proxy y schemathesis se validaron en local (§16.8.2).
- El run del commit final de la rama figura en el HANDOFF_ENVELOPE de TKT-OPS-004.

## 17. TKT-OPS-005 — RSK-OPS-001 con lista y caducidad, runtimes mínimos, Cache-Control del SSR y proxies de confianza (F7, soporte)

### 17.1 Estado
**COMPLETADO** en local. Rama `tkt-ops-005-trivy`, creada desde `tkt-ops-004-gate-health`. En GitHub, el job `images` sigue NOT_RUN en esta rama porque no contiene `frontend/` (§17.13). Se validará en el PR #9, cuando se integre este ticket.

### 17.2 Objetivo
- Aplicar la **decisión humana sobre RSK-OPS-001** (Puerta Humana §0.5, registrada por el Orquestador en `audit_log.md` el 2026-09-26): "Aceptar con lista y caducidad".
  - Solo pueden ir a `.trivyignore` las CVE de paquetes del SO Debian 13.7 **sin parche publicado**, cada una con `exp:2026-10-26`.
  - Las CVE **con parche se eliminan** de las imágenes.
- OBS-QA002-C2-04: `Cache-Control: no-store` en el HTML SSR.
- OBS-QA004-03: `DJANGO_TRUSTED_PROXIES` en el backend.

### 17.3 Cambios realizados
| Cambio | Archivo | Decisión |
|---|---|---|
| Etapa `node-sin-pm`: borra `/usr/local/lib/node_modules` (npm con brace-expansion, ip-address y tar vendorizados), `npx`, `corepack`, `yarn`/`yarnpkg`, `/opt/yarn-v*` y las cabeceras C. Se comprueba que no queda ningún gestor. Después se **aplana** (`FROM scratch` + `COPY / /`), así que esos bytes tampoco quedan en capas inferiores. El runtime usa `node-min` y re-declara `PATH` y `NODE_VERSION`. Usuario `node` (uid 1000) sin cambios. | `infra/docker/frontend.Dockerfile` | DEC-AUTO-220 |
| Etapa `python-sin-pip`: borra `pip`, `pip-*.dist-info`, los lanzadores `pip*` y `ensurepip/_bundled`. Se comprueba con `importlib` que no quedan `pip`, `setuptools` ni `wheel`. La imagen se aplana en `python-min`, que es la base de `runtime` y, por tanto, también de `scheduler`. `/opt/venv` (uv) no trae pip. | `infra/docker/backend.Dockerfile` | DEC-AUTO-221 |
| Backup **mínimo**. La etapa `pgclient` (imagen de la BD, mismo digest) extrae `pg_dump`/`pg_restore`/`psql` 18.6 y `libpq.so.5` 18.6 a `/usr/local/{bin,lib}` y deja registradas las versiones en `/usr/local/share/brujula/pgclient.versiones`. Final sobre `debian:13.7-slim@sha256:a99cfc51…` con `age=1.2.1-1+b5`, `libgssapi-krb5-2=1.21.3-5+deb13u1`, `libldap2=2.6.10+dfsg-1` y `libreadline8t64=8.2-6`, que son las dependencias obtenidas con `ldd`. Usuario `backup_app` con uid/gid 999, el mismo que antes, así que el volumen existente sigue siendo compatible. Durante el build se verifica que las tres herramientas son 18.6. Desaparecen el servidor PostgreSQL, libxml2, gnupg/gpg*, perl, libperl y perl-modules. Tamaño: 677 MB → 158 MB. | `infra/backup/Dockerfile` | DEC-AUTO-222 |
| `map $upstream_http_content_type $cache_control_ssr`: `text/html` → `no-store` siempre, también en las páginas de error HTML del SSR. El resto conserva el `Cache-Control` del upstream. En `location /` se aplican `proxy_hide_header Cache-Control` y `add_header Cache-Control $cache_control_ssr always`. | `infra/proxy/nginx.conf` | DEC-AUTO-223 |
| `DJANGO_TRUSTED_PROXIES: ${APP_NET_PREFIX:-10.231.40}.10/32` en el servicio `backend`, que es la IP fija del proxy (DEC-AUTO-155). La consume el backend de TKT-004 (`PROXIES_CONFIANZA`). El backend de `main` la ignora sin efecto. No se añade a `.env.example` como variable (compose la deriva de `APP_NET_PREFIX`): solo queda documentada. | `compose.yaml`, `.env.example` | DEC-AUTO-224 |
| `.trivyignore` (nuevo): 8 CVE, todas `exp:2026-10-26`, con un comentario por grupo que indica el paquete, las imágenes afectadas, "sin fix en Debian 13.7 a 2026-09-26" y la referencia a la decisión humana. | `.trivyignore` | DEC-AUTO-225 |
| Job `images`. (1) Paso nuevo de **política**: cada línea no comentada debe ser `CVE-…`/`GHSA-…` + ` exp:AAAA-MM-DD`, sin comodines ni nombres de paquete. Se prohíben `--ignore-unfixed`/`--ignore-policy`/`--skip-*` y las `TRIVY_*` equivalentes en los workflows, y se avisa de las excepciones caducadas. (2) El gate usa `--ignorefile .trivyignore --show-suppressed --exit-code 1`, así que lo suprimido queda visible en el log. El JSON de evidencia se genera **sin** ignorefile, con todos los hallazgos. (3) **Control negativo**: con todas las caducidades puestas en 2000-01-01, trivy sobre `backend` **debe** fallar. Si no falla, el job falla. | `.github/workflows/ci.yaml` | DEC-AUTO-225 |

### 17.4 Versiones aprobadas
| Componente | Versión | Nota |
|---|---|---|
| debian (base del backup) | `13.7-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a` | Mismo Debian 13.7 que las bases python, node y postgres. Dependabot (docker, `/infra/backup`) ya lo vigila |
| Cliente PostgreSQL | 18.6 (`libpq5=18.6-1.pgdg13+2`, `postgresql-client-18=18.6-1.pgdg13+2`) | Copiado de `postgres:18.6-trixie@sha256:5a5a84b1…`, igual que el servidor |
| age | 1.2.1-1+b5 | Sin cambios |
| node / python | 24.21.0 / 3.13.15 | Mismos digests. Solo se retiran npm/corepack/yarn y pip |
| trivy | 0.74.0 | Admite `exp:` en `.trivyignore` y `--show-suppressed` (verificado en local) |

### 17.5 Infraestructura
Topología, redes, puertos, límites y usuarios sin cambios. Usuarios: backend y scheduler 10001, frontend 1000, backup 999, proxy 101. Capas: frontend 3, backend 6, scheduler 9, backup 12.

### 17.6 Dependencias
No cambian manifests ni lockfiles de aplicación.

### 17.7 Variables de entorno
- `DJANGO_TRUSTED_PROXIES` (backend, derivada de `APP_NET_PREFIX`; CIDR separados por comas). Documentada en `.env.example`.
- En proyectos paralelos, cada uno recibe su propia `.10/32` porque `APP_NET_PREFIX` es distinto.

### 17.8 Validaciones ejecutadas (2026-09-26, Docker Engine 29.6.1, Compose v5.2.0, trivy 0.74.0, syft 1.51.0)
Copia temporal fuera del repositorio (scratchpad): `backend/` de `main` (1e597be), `frontend/` de `origin/tkt-002-frontend-base` (cfb98d7), e infraestructura de esta rama. Proyecto `-p brujula-ops005`, `APP_NET_PREFIX=10.231.51`, proxy en `127.0.0.1:18051`. Etiquetas `ops005-antes` (infraestructura de TKT-OPS-004) y `ops005-despues`.

**17.8.1 trivy (CRITICAL,HIGH) por imagen, antes → después (sin ignorefile)**

| Imagen | Antes (hallazgos / CVE únicas) | Después | CVE eliminadas (con parche o por adelgazar) | CVE restantes (todas sin fix, Debian 13.7) |
|---|---|---|---|---|
| backend | 46 HIGH / 10 | 44 HIGH / 8 | GHSA-6v7p-g79w-8964 (msgpack de pip, fix 1.2.1), CVE-2025-47273 (setuptools 70.3.0 declarado por pip, fix 78.1.1) | util-linux ×4, libacl1, libsystemd0/libudev1, ncurses, perl-base |
| scheduler | 46 HIGH / 10 | 44 HIGH / 8 | las mismas que backend | las mismas que backend |
| frontend | 47 HIGH / 12 | 43 HIGH / 8 | CVE-2026-14257 y CVE-2026-69152 (brace-expansion), CVE-2026-69192 (ip-address), CVE-2026-73566 (tar); todas de npm | las mismas 8 |
| backup | 61 HIGH + 1 CRITICAL / 17 | 43 HIGH / 8 | CVE-2026-6653 **CRITICAL** + CVE-2026-74860, -86138, -86139, -86140, -86142, -86143, -86144 (libxml2); CVE-2026-24882 (gnupg/gpg*/dirmngr/gpgsm); de CVE-2026-9538 desaparecen perl, libperl5.40 y perl-modules (queda perl-base, Essential) | las mismas 8 |
| proxy | 0 | 0 | — | — |

Las 8 CVE restantes, que son el contenido de `.trivyignore`, son CVE-2026-76642, -78408, -78409 y -78410 (util-linux), CVE-2026-54369 (libacl1), CVE-2026-16742 (libsystemd0/libudev1), CVE-2025-69720 (ncurses) y CVE-2026-9538 (perl-base). Ninguna tiene `FixedVersion`. Siete tienen `Status: affected`; **CVE-2026-9538 (perl-base) está en `fix_deferred`** (Debian aplaza el parche), no en `affected` (corrección OBS-DOC, ciclo 2). La lista coincide con la que reportó QA para el SO. De las de backup no persiste ninguna.

**17.8.2 Gate con `.trivyignore`**
- Positivo: las 5 imágenes `ops005-despues` con `--ignorefile .trivyignore --exit-code 1` dan **exit 0**.
- Negativo 1 (caducada): `CVE-2026-9538 exp:2026-09-25` → backend **exit 1** (reaparece solo esa CVE).
- Negativo 2 (no listada): sin la línea de CVE-2026-16742 → frontend **exit 1**.
- Negativo 3: backup **antes** con el `.trivyignore` final → **exit 1**, con 1 CRITICAL y 14 HIGH no cubiertas (libxml2 y gnupg). Confirma que no se aceptó nada con parche ni ajeno a la lista.
- Política del paso nuevo: sobre el `.trivyignore` real, 0 entradas fuera de política. Con `CVE-2026-1*`, una CVE sin `exp:` o un nombre de paquete, las rechaza. El grep de opciones prohibidas no coincide consigo mismo.
- `actionlint` 1.7.7, con shellcheck, sobre `.github/workflows/`: 0 hallazgos. El YAML se parsea con PyYAML 6.0.3.

**17.8.3 Stack (proxy → frontend SSR / backend → db)**
- `docker compose up -d --no-build --wait`: db, backend, frontend y proxy **healthy**; init-volumes y migrate **exit 0**. Con `--profile ops`, scheduler y backup quedan Up y supercronic lee el crontab.
- `GET /health/ready` → 200 `{"status":"ok"}`.
- `GET /` → 200 `text/html`, **`Cache-Control: no-store`**, con CSP y nonce. El SSR no enviaba `Cache-Control` para el HTML (comprobado con `wget -S` directo a `frontend:4000`).
- `GET /no-existe-xyz` → 404 `text/html` del SSR, con **`Cache-Control: no-store`**.
- `GET /main-*.js` → 200 `text/javascript`, `Cache-Control: public, max-age=31536000, immutable` (el del SSR, conservado) y `Content-Encoding: gzip`. El CSS responde igual.
- API: `GET /api/v1/publico/inicio` → 404 `application/problem+json`. Es el backend de `main` (sin cambios de este ticket).
- Frontend: `npm`, `npx`, `corepack` y `yarn` ausentes; `/usr/local/lib/node_modules` no existe; `node v24.21.0`.
- Backend: `pip` ausente y `find_spec` de pip/setuptools/wheel → `[]`. Entorno con `DJANGO_TRUSTED_PROXIES=10.231.51.10/32` y `GUNICORN_FORWARDED_ALLOW_IPS=10.231.51.10`.
- Scheduler: `manage.py check` → 0 issues; sin pip; supercronic v0.2.49.
- Backup, con una clave age **efímera** generada dentro del contenedor y borrada al terminar (no es un secreto real): `backup.sh` → exit 0, 5 archivos `.age` y `sha256sum -c` OK. Tras descifrar, `pg_restore --list` lee el dump (454 entradas TOC, BD `brujula`). `pg_dump (PostgreSQL) 18.6 (Debian 18.6-1.pgdg13+2)`. El proceso se ejecuta como uid 999 con el grupo 10001.
- SBOM (syft, CycloneDX). Corrección OBS-DOC (ciclo 2): la cifra total incluye entradas de tipo `file`.
  - frontend: 503 componentes = 84 `library` + 3 `application` + 1 `operating-system` + 415 `file`.
  - backup: 548 = 116 `library` + 3 `application` + 1 `operating-system` + 428 `file`.
  - Ambos detectan `debian 13.7`, y ninguno contiene npm, pip, libxml2, perl, gnupg ni libpq5 (ver RSK-OPS-023).
  - Recuento de todas las imágenes finales: §17.14.6.
- Limpieza: `down -v --remove-orphans` del proyecto `brujula-ops005`, borrado de las 10 imágenes `ops005-*` y de la copia temporal. No se tocaron `backend`, `frontend` ni `db` (PROYECTO1), ni `brujula-tkt004-*` ni `brujula-qaops004-*`.

**NOT_RUN**:
- Simulacro de restauración completo (`restore-local.sh` sobre una BD limpia, AC-054). Se comprobó el descifrado y `pg_restore --list`, pero no la restauración.
- Build arm64: los argumentos de supercronic y la ruta de libpq son independientes de la arquitectura, pero no se ha construido.
- Job `images` en GitHub (§17.13).

### 17.9 Seguridad
- Todas las CVE CRITICAL/HIGH **con parche** desaparecen de las 5 imágenes: 6 en total, más la CRITICAL de libxml2 y 8 HIGH de libxml2/gnupg, que se eliminan al adelgazar la imagen.
- Solo quedan excepciones Debian sin parche, con caducidad a 30 días. Al caducar, el CI vuelve a fallar y hará falta una **nueva decisión humana**.
- Superficie reducida: sin gestores de paquetes de lenguaje en ningún runtime y sin servidor PostgreSQL, gpg ni perl completo en backup.
- El HTML con nonce y los posibles datos del panel ya no se pueden almacenar en caché (OBS-QA002-C2-04).
- `X-Forwarded-For` solo se acepta desde la IP del proxy (OBS-QA004-03).
- Sin secretos nuevos.

### 17.10 Riesgos / pendientes

| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-001 | CVE HIGH/CRITICAL de Debian 13.7 sin parche en las bases | HIGH (incluye 1 CRITICAL de libxml2 en db) | Aceptadas por dos decisiones humanas (2026-09-26): primero 8 CVE comunes y después, en el ciclo 2, 8 CVE de libxml2 de la imagen de la BD. Lista cerrada de 16 CVE con `exp:2026-10-26`. El CI falla ante cualquier CVE nueva, no listada o caducada | **ACEPTADO CON CADUCIDAD (vence 2026-10-26)** |
| RSK-OPS-023 | El cliente PostgreSQL del backup (binarios + `libpq.so.5`) se copia sin registro dpkg: trivy y syft no ven `libpq5` ni `postgresql-client-18` en `brujula/backup` | LOW | Versión fijada por el digest de `postgres:18.6-trixie` (la misma de la BD, que Dependabot vigila) y registrada en `/usr/local/share/brujula/pgclient.versiones`. Ciclo 2: la imagen de la BD (`brujula/db`) entra en el bucle de trivy y SBOM del CI y lleva `libpq5` 18.6-1.pgdg13+2 registrado en dpkg, la misma versión copiada al backup | **MITIGADO** (ciclo 2) |
| RSK-OPS-024 | Los paquetes Debian del backup están fijados con versión exacta. Si Debian publica una actualización de seguridad y retira la versión anterior del espejo, el build del backup falla | LOW | Es fallo visible, no silencioso. Se corrige actualizando los ARG de versión (Dependabot no los cubre) | ABIERTO |
| OBS-OPS005-01 | Job `images` NOT_RUN en GitHub en esta rama (sin `frontend/`) | INFO | Se validará en el PR #9 al integrar este ticket | NOT_RUN (GitHub) |

### 17.11 Archivos modificados
- `.trivyignore` (nuevo)
- `infra/docker/frontend.Dockerfile`
- `infra/docker/backend.Dockerfile`
- `infra/backup/Dockerfile`
- `infra/proxy/nginx.conf`
- `compose.yaml`
- `.env.example`
- `.github/workflows/ci.yaml`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 17.12 Próximo agente
**Orquestador**, que debe:
1. Enviar la rama a QA.
2. Registrar DEC-AUTO-220 a DEC-AUTO-225, RSK-OPS-023/024 y el nuevo estado de RSK-OPS-001 (caduca el 2026-10-26: conviene crear un recordatorio de revisión antes de esa fecha).
3. Tras integrar TKT-OPS-004 y este ticket, actualizar el PR #9 con `main`. Su job `images` es la validación en GitHub del gate con `.trivyignore`.

### 17.13 Validación en GitHub Actions
- Run `workflow_dispatch` sobre `tkt-ops-005-trivy` en af6ae8f: https://github.com/magoolf/brujula-salvaje/actions/runs/36268658095. Resultado: **success**.
  - `detectar código`, `infraestructura` y `backend`: OK.
  - `frontend`, `images` y `firma`: omitidos (**NOT_RUN**), porque esta rama no tiene `frontend/`. Por eso los pasos nuevos del job `images` (política de `.trivyignore`, gate con ignorefile y control negativo) **no se han ejecutado en GitHub**. Se ejecutarán en el PR #9 cuando este ticket esté integrado en `main`. La lógica equivalente se validó en local (§17.8.2).

### 17.14 Ciclo 2 (QA_VERDICT FAIL 1/3): imagen de la BD en el gate, BD derivada mínima y política de trivy ampliada

**17.14.1 Hallazgos atendidos**
- **QA-OPS005-01 (HIGH)**: la imagen de la BD (`postgres:18.6-trixie@sha256:5a5a84b1…`), que ejecutan `db` e `init-volumes`, no se escaneaba. Mientras backup heredaba de ella, el gate veía libxml2 y gnupg por esa vía. Además, `gosu` traía 22 CVE de la stdlib de Go **con parche** (1 CRITICAL).
- **QA-OPS005-03 (LOW)**: faltaba cerrar las vías paralelas de configurar trivy.
- **OBS-DOC**: estado de CVE-2026-9538 y recuento del SBOM (corregido en §17.8).
- QA-OPS005-02 (simulacro de `restore-local.sh`) queda fuera de este ciclo y pasa a TKT-OPS-007.

**17.14.2 Cambios**

| Cambio | Archivo | Decisión |
|---|---|---|
| Nueva imagen `brujula/db`: `FROM postgres:18.6-trixie@sha256:5a5a84b1…` (el mismo digest). Retira `gosu`; purga `gnupg`, `dirmngr`, `gnupg-l10n`, `gpg`, `gpg-agent`, `gpgsm` y `gpgconf` con `--auto-remove` (arrastra `pinentry-curses`, `libassuan9`, `libgnutls30t64`, `libksba8`, `libnpth0t64`, `libp11-kit0` y `libtasn1-6`, que nadie más usa; libldap2 usa OpenSSL). Purga `perl`, `libperl5.40` y `perl-modules-5.40` con `dpkg --force-depends`: solo los usa `postgresql-common` (pg_wrapper y pg_ctlcluster), que el entrypoint oficial no llama. Borra los enlaces `/usr/bin/* -> pg_wrapper` y antepone `/usr/lib/postgresql/18/bin` al `PATH`. Al construir comprueba que no queda nada de lo retirado, que postgres, initdb, pg_ctl, psql y pg_isready resuelven a `/usr/lib/postgresql/18/bin`, que la versión es 18.6 y que libxml2 está enlazada. Queda `USER 999:999`. El servidor, las extensiones, `docker-entrypoint.sh` e initdb no cambian. | `infra/db/Dockerfile` (nuevo) | DEC-AUTO-226 |
| `db` e `init-volumes` usan `build: *db-build` e `image: brujula/db:${APP_VERSION:-0.0.0-dev-<proyecto>}`, en lugar de la imagen oficial | `compose.yaml` | DEC-AUTO-226 |
| `pull_policy: build` en los 8 servicios con `build`. El primer run de CI del ciclo 2 (36285126112) mostró que, sin esto, `up --wait db` intenta primero un **pull de `brujula/db` desde Docker Hub** ("pull access denied") antes de construir: un tercero que publicara ese nombre haría que se ejecutara su imagen. Con `build` no hay pull nunca, y `up --no-build` sin imagen local falla sin descargar nada (comprobado con un compose de prueba). Tras el cambio, `up --wait db` en modo CI construye sin intentar el pull y llega a healthy con `b:C.UTF-8` | `compose.yaml` | DEC-AUTO-226 |
| `db` entra en los bucles de trivy (gate y JSON) y de SBOM. El control negativo, con todas las caducidades en el pasado, se ejecuta sobre `backend` **y** `db` | `.github/workflows/ci.yaml` | DEC-AUTO-227 |
| El paso de política falla si ocurre cualquiera de estas cosas: existe `trivy.yaml`, `trivy.yml`, `.trivyignore.yaml` o `.trivyignore.yml` en el repositorio; aparece `TRIVY_(CONFIG\|VEX\|SEVERITY\|IGNOREFILE\|IGNORE_UNFIXED\|IGNORE_STATUS\|IGNORE_POLICY\|SKIP_*)` asignada en los workflows; alguna invocación real de `trivy image/fs/rootfs` no lleva exactamente `--severity CRITICAL,HIGH` o lleva `--config`, `-c`, `--vex` o `--ignore-status`; o no hay ninguna invocación de trivy | `.github/workflows/ci.yaml` | DEC-AUTO-228 |
| Se añaden 8 CVE de libxml2 (solo `db`) por la **2.ª decisión humana** (2026-09-26, "Aceptar con caducidad" las CVE sin parche de la imagen derivada de PostgreSQL). Los comentarios de las 8 comunes añaden `db` y las versiones de paquete. Total: 16 entradas, todas `exp:2026-10-26` | `.trivyignore` | DEC-AUTO-229 |

**17.14.3 trivy 0.74.0 (CRITICAL,HIGH) sobre la imagen de la BD, antes → después (sin ignorefile)**

| | Oficial `postgres:18.6-trixie@5a5a84b1…` | Derivada `brujula/db` |
|---|---|---|
| Hallazgos | 82 HIGH + 2 CRITICAL | 51 HIGH + 1 CRITICAL |
| CVE únicas | 39 (22 con fix + 17 sin fix) | 16 (0 con fix) |
| gosu (Go stdlib, **con fix**) | 22: CVE-2025-68121 CRITICAL; CVE-2025-61726, -61729; CVE-2026-25679, -27145, -32280, -32281, -32283, -33811, -33814, -33818, -39820, -39821, -39822, -39836, -42499, -42504, -56853, -56858, -56859, -56860, -56862 | **0** (se retira el binario) |
| gnupg/gpg*/dirmngr/gpgsm | CVE-2026-24882 | **0** (paquetes purgados) |
| CVE-2026-9538 | en perl, libperl5.40, perl-modules-5.40 y perl-base | solo perl-base (Essential) |

CVE sin fix que quedan en `brujula/db` (todas con `FixedVersion` vacío):

| CVE | Sev. | Paquete(s) y versión | Estado Debian | ¿Lo necesita el servidor PostgreSQL? |
|---|---|---|---|---|
| CVE-2026-6653 | **CRITICAL** | libxml2 2.12.7+dfsg+really2.9.14-2.1+deb13u3 | affected | **Sí**: el binario `postgres` enlaza `libxml2.so.2` (tipo `xml`, `xmlparse`…); también dependen de ella libxslt1.1 y libllvm19 (JIT) |
| CVE-2026-74860, -86138, -86139, -86140, -86142, -86143, -86144 | HIGH | libxml2 (misma versión) | affected | Sí (como la anterior) |
| CVE-2026-76642, -78408, -78409, -78410 | HIGH | util-linux, bsdutils, mount, login, libblkid1, libmount1, libsmartcols1, libuuid1, liblastlog2-2 — 2.41.5-0+deb13u1 | affected | Base del SO (Essential/required); postgres enlaza libuuid1 |
| CVE-2026-54369 | HIGH | libacl1 2.3.2-2+b1 | affected | Base del SO (coreutils) |
| CVE-2026-16742 | HIGH | libsystemd0, libudev1 257.13-1~deb13u1 | affected | Sí: postgres enlaza libsystemd0 (dependencia de `postgresql-18`) |
| CVE-2025-69720 | HIGH | ncurses-base, ncurses-bin, libtinfo6, libncursesw6 — 6.5+20250216-2 | affected | Base del SO (bash) y psql (readline/libtinfo) |
| CVE-2026-9538 | HIGH | perl-base 5.40.1-6+deb13u1 | **fix_deferred** | No directamente: es paquete Essential de Debian (dpkg, debconf) |

La BD solo está en la red `datos` (`internal: true`), no publica puertos (salvo `compose.debug.yaml` y `compose.ci.yaml`, en 127.0.0.1) y se ejecuta como 999:999 con `cap_drop: ALL`, `no-new-privileges` y raíz de solo lectura.

**17.14.4 Gate y controles (local, trivy 0.74.0, imágenes `ops005-c2`)**
- Con `--ignorefile .trivyignore --exit-code 1`, backend, frontend, proxy, scheduler, backup y **db** dan **exit 0**.
- Controles negativos (todos **exit 1**):
  - db con `CVE-2026-6653 exp:2026-09-25`: reaparece solo la CRITICAL.
  - db sin la línea de CVE-2026-86144.
  - backend y db con todas las caducidades en 2000-01-01 (el mismo control que ejecuta el CI).
  - La imagen **oficial** `postgres:18.6-trixie@5a5a84b1…` con el `.trivyignore` final queda con 1 CRITICAL y 28 HIGH, 23 CVE únicas: las 22 de gosu (con fix) y la de gnupg. Esto demuestra que ninguna CVE con parche está aceptada.
- Paso de política, simulado con el script extraído del workflow:
  - Sobre el repositorio real, exit 0 con "excepciones vigentes: 16".
  - Da exit 1 con cada uno de estos casos: `trivy.yaml` en la raíz, `sub/.trivyignore.yaml`, `--severity CRITICAL`, `--vex x.json`, `--config t.yaml`, `TRIVY_CONFIG:` en `env` y una invocación sin `--severity`.
- `actionlint` 1.7.7 (con shellcheck): 0 hallazgos.

**17.14.5 BD derivada en funcionamiento (`-p brujula-ops005`, `APP_NET_PREFIX=10.231.51`)**
- Stack completo con el perfil ops: db, backend, frontend y proxy **healthy**; init-volumes (imagen `brujula/db`, como root, con `chown`/`chmod`) y migrate terminan con exit 0; scheduler y backup Up.
- Contenedor db:
  - Se ejecuta como `uid=999(postgres)`. `psql` y `pg_isready` resuelven a `/usr/lib/postgresql/18/bin`; el healthcheck da `accepting connections`.
  - `PostgreSQL 18.6 (Debian 18.6-1.pgdg13+2)`.
  - INFRA-DB-000: la BD `brujula` tiene locale `b:C.UTF-8`; existen los roles `app_backup`, `app_migrator`, `app_rw` y `readonly`; `shared_preload_libraries=pg_stat_statements`.
  - `xmlparse(content '<a>1</a>')` funciona (libxml2 operativa).
  - `/usr/local/bin/gosu` no existe. Los logs no muestran errores ni referencias a perl.
- `docker compose restart db`: vuelve a healthy con 0 reinicios (arranque con datos existentes).
- Modo CI (`-f compose.yaml -f compose.ci.yaml up --wait db`, con tmpfs y `DB_BOOTSTRAP_TEST_TEMPLATE=true`): healthy, `b:C.UTF-8`, BD `brujula`. Es la misma comprobación que el paso INFRA-DB-000 del job `infraestructura`.
- Backup contra la BD nueva, con una clave age efímera: exit 0; `sha256sum -c` OK; tras descifrar, `pg_restore --list` lee 454 entradas TOC.
- Proxy: `/health/ready` → 200; `/` → 200 con `Cache-Control: no-store`.
- Limpieza: `down -v`, 6 imágenes `ops005-c2` borradas y copia temporal eliminada. Quedan 0 contenedores, volúmenes o redes `ops005`; no se tocaron otros proyectos.

**17.14.6 SBOM (syft 1.51.0, CycloneDX) de las imágenes finales**

| Imagen | Total | library | application | operating-system | file |
|---|---|---|---|---|---|
| backend | 620 | 129 | 4 | debian 13.7 | 486 |
| scheduler | 638 | 146 | 4 | debian 13.7 | 487 |
| frontend | 503 | 84 | 3 | debian 13.7 | 415 |
| backup | 548 | 116 | 3 | debian 13.7 | 428 |
| db | 711 | 133 | 6 | debian 13.7 | 571 |
| proxy | 1281 | 70 | 0 | alpine 3.24.2 | 1210 |

Ninguna imagen contiene npm, pip, setuptools ni msgpack. Solo db contiene gosu, gnupg o perl completo, y ninguno de los tres: se han retirado. db mantiene `libpq5` y `libxml2` porque el servidor los necesita. proxy (alpine) contiene `libxml2` de Alpine, sin CVE CRITICAL/HIGH.

**17.14.7 Riesgos nuevos o cambiados**

| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-025 | Dependabot deja de vigilar el digest de PostgreSQL. `compose.yaml` ya no lo contiene (lo tiene `infra/db/Dockerfile`) y `.github/dependabot.yml` no incluye `/infra/db`. Ese archivo está fuera de mis `archivos_permitidos` (`.github/workflows/**`) | MEDIUM | Ticket para el Orquestador: añadir `"/infra/db"` a `directories` del ecosistema `docker` en `.github/dependabot.yml`. Mientras tanto, `/infra/backup` (mismo `ARG POSTGRES_IMAGE`) sigue vigilado y cualquier subida de digest debe replicarse en `infra/db/Dockerfile` | ABIERTO (ticket) |
| RSK-OPS-026 | `postgresql-common` y `postgresql-client-common` quedan con la dependencia `perl:any` sin satisfacer en dpkg (`--force-depends`). Un `apt-get install` sobre `brujula/db` fallaría | LOW | La imagen es final y no se instala nada encima. Si hiciera falta, se reconstruye desde el `Dockerfile`. `pg_wrapper`, `pg_ctlcluster` y el resto no se usan | ACEPTADO (DEC-AUTO-226) |
| RSK-OPS-001 | Ver §17.10: ahora 16 CVE (2 decisiones humanas), vencen el 2026-10-26 | HIGH | — | ACEPTADO CON CADUCIDAD |

**17.14.8 Archivos del ciclo 2**
- `infra/db/Dockerfile` (nuevo)
- `compose.yaml`
- `.github/workflows/ci.yaml`
- `.trivyignore`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

**17.14.9 Próximo agente**: **Orquestador**, que debe:
1. Reenviar la rama a QA (ciclo 2/3).
2. Registrar DEC-AUTO-226 a DEC-AUTO-229, RSK-OPS-025/026 y la 2.ª decisión humana aplicada.
3. Emitir el ticket de Dependabot `/infra/db` (RSK-OPS-025).
4. La validación del job `images` en GitHub, que ahora incluye db, llegará con el PR #9 una vez integrado este ticket.

## 18. TKT-OPS-007 — restauración fiel sobre INFRA-DB-000 (QA-OPS005-02, AC-054) (F7, soporte)

### 18.1 Estado
**COMPLETADO** para la parte de infraestructura. La restauración de la BD y de los medios es fiel y termina con exit 0. Los 6 comandos de gestión de ADR-DB-004 §4 **todavía no existen en el backend**: `post-restore-local.sh` los marca `NO_DISPONIBLE` y termina con **exit 5** (restauración incompleta). No los da por buenos (§18.10, RSK-OPS-030).

### 18.2 Objetivo
Corregir QA-OPS005-02: sobre una BD recién creada por INFRA-DB-000, `restore-local.sh` terminaba con exit 1 (`schema "app" already exists`). Validarlo con un simulacro AC-054 completo y medir el RTO (objetivo ≤ 4 h, DB_HANDOFF `rpo_rto`).

### 18.3 Cambios realizados

| Cambio | Archivo | Decisión |
|---|---|---|
| Lista TOC con `pg_restore -l` que excluye **exactamente** las 5 entradas precreadas por INFRA-DB-000: `SCHEMA - app`, `SCHEMA - ext`, `EXTENSION - pg_stat_statements`, `COMMENT - EXTENSION pg_stat_statements` y `ACL - SCHEMA public`. Cada patrón puede coincidir con una entrada como máximo: si coincide con más, exit 5; si no coincide con ninguna, se avisa (copias antiguas). Se restaura con `-L`. **No** se excluyen las ACL de los esquemas `app`/`ext` (propiedad de app_migrator: se aplican sin error y reproducen el origen) ni `unaccent`/`pg_trgm` (las crea la migración `busqueda.0001` con app_migrator; no existen en una BD recién creada) | `scripts/ops/restore-local.sh` | DEC-AUTO-240 |
| **Defecto nuevo detectado en el simulacro (más grave que el original)**: con los 4 errores ignorados, los conteos coincidían, pero los **privilegios no**. INFRA-DB-000 ya crea `ALTER DEFAULT PRIVILEGES FOR ROLE app_migrator IN SCHEMA app` (arwd para app_rw y SELECT para readonly), así que cada `CREATE TABLE` del restore los concede. `pg_dump` solo emite GRANT relativos al ACL de fábrica, nunca REVOKE, de modo que se perdían en silencio los REVOKE de las migraciones en 9 relaciones: `readonly` pasaba a leer `cuenta_staff` completa (hash de contraseña, `secreto_mfa`), `cuenta_codigo_recuperacion` y `sesion_panel`, y `app_rw` recibía UPDATE/DELETE en `evento_auditoria`, `revision_contenido` y `django_migrations`, además de sobre `cache_limites`, `idempotencia_peticion` y `v_medio_uso`. Corrección: en la **misma transacción**, un preludio retira los privilegios por defecto del rol de restauración (DO genérico sobre `pg_default_acl`); después se restaura, y las entradas `DEFAULT ACL` del propio dump los recrean al final. Tras restaurar se comprueba que el número de privilegios por defecto coincide con el de la copia | `scripts/ops/restore-local.sh` | DEC-AUTO-242 |
| Ejecución todo o nada: `pg_restore --exit-on-error -L … --file=-` alimenta a `psql` con `ON_ERROR_STOP`, un `BEGIN` explícito y un `COMMIT` que solo se envía si pg_restore generó el script completo. Ante cualquier fallo, exit 1 y la BD queda como la dejó INFRA-DB-000. (`pg_restore --single-transaction` directo no permite ejecutar el preludio dentro de la misma transacción) | `scripts/ops/restore-local.sh` | DEC-AUTO-242 |
| Salvaguarda previa: la BD destino debe tener el estado de INFRA-DB-000 (esquemas `app`/`ext` de app_migrator y `pg_stat_statements` en `ext`) y el esquema `app` debe estar **vacío** (0 relaciones y 0 funciones). En otro caso, exit 4. Se conservan las salvaguardas anteriores: `--confirmar-entorno-local`, `RESTORE_ENV=local`, clave legible, `sha256sum -c` antes y después de descifrar y `MEDIA_RESTORE_DIR` vacío (exit 3) | `scripts/ops/restore-local.sh` | DEC-AUTO-243 |
| Manifiesto de medios vacío (BD sin medios): `sha256sum -c` lo trataría como error, así que ahora se informa y se continúa. Con contenido: `sha256sum -c --quiet --strict` (cualquier ausencia o alteración da exit ≠ 0). Libro de anonimizaciones: si la copia lo incluye y se define `LIBRO_RESTORE_DIR`, se deposita la copia verificada sin sobrescribir; por defecto se usa el libro vivo del volumen `ops_libro`, que es más reciente (DEC-AUTO-094) | `scripts/ops/restore-local.sh` | DEC-AUTO-244 |
| **Nuevo** `post-restore-local.sh` (host). Con la aplicación parada (si backend, frontend, proxy o scheduler están en marcha, exit 2), ejecuta `migrate` (y dice si había migraciones pendientes) y después los 6 comandos de ADR-DB-004 §4 en orden, con la imagen scheduler y el rol app_rw. Solo ejecuta los que existen en `manage.py help --commands`: un comando que existe y falla detiene el script con exit 1, y uno que no existe se marca `NO_DISPONIBLE (NOT_RUN)`. Al final hace `up -d --wait` y comprueba `/health/ready` = 200. Si falta algún comando, **exit 5** (nunca 0) | `scripts/ops/post-restore-local.sh` (nuevo) | DEC-AUTO-241 |

### 18.4 Versiones aprobadas
Sin cambios. Cliente `pg_restore`/`psql` 18.6, el mismo del servidor (imagen `brujula/backup`). shellcheck v0.10.0 (`koalaman/shellcheck:v0.10.0@sha256:2097951f…`) usado solo como herramienta local de validación.

### 18.5 Infraestructura
Sin cambios en compose, Dockerfiles, redes, puertos, límites, usuarios ni capacidades. La imagen `brujula/backup` incorpora el nuevo `restore-local.sh` en el siguiente build (`COPY --from=ops`). `post-restore-local.sh` no entra en ninguna imagen: se ejecuta en el host.

### 18.6 Dependencias
Ninguna.

### 18.7 Variables de entorno
Ninguna variable nueva en `.env.example`. Variables del runbook (solo en la sesión del operador, nunca en archivos versionados):
- `RESTORE_ENV=local`.
- `RESTORE_PGPASSWORD`, igual a `APP_MIGRATOR_PASSWORD` del `.env` local. Se pasa por nombre (`-e RESTORE_PGPASSWORD`), nunca por valor en la línea de órdenes.
- `MEDIA_RESTORE_DIR`.
- `LIBRO_RESTORE_DIR`, opcional.
- `COMPOSE_PROJECT_NAME` y `COMPOSE_ENV_FILES`, las estándar de compose para `post-restore-local.sh`.

### 18.8 Validaciones ejecutadas (2026-09-27, Docker Engine 29.6.1, Compose v5.2.0)
Proyecto `-p brujula-ops007`, `APP_NET_PREFIX=10.231.56`, `PROXY_HOST_PORT=18507` e imágenes `*:ops007` construidas desde `origin/main` b929b7d más esta rama. `.env` generado con `init-env.sh` en el scratchpad, fuera del repo. Clave age **efímera** (`age-keygen` de la imagen backup) en el scratchpad y borrada al terminar: no es un secreto real.

**Preparación**
- Stack completo `up --wait`: las migraciones reales de `main` (auditoria 0001-0002, busqueda 0001-0002, catalogos 0001-0002 con semilla, contenido 0001-0002, cuentas 0001, inicio 0001, medios 0001 y ops 0001) terminan en OK.
- Datos de prueba insertados como `app_rw`: 12 `pais`, 2 `cuenta_staff` (una DESACTIVADA), 50 `evento_auditoria` con `ip_truncada`, 1 `ops_ejecucion_tarea`, y 1 `medio` con 1 `medio_derivado` que apuntan a 2 archivos reales escritos en el volumen de medios (privado/ y publico/) por el backend (uid 10001).
- Instantánea **antes**, tomada como superusuario, solo para comparar:
  - `pg_dump --schema-only`.
  - Conteo de las 39 tablas de `app`.
  - md5 del contenido de 5 tablas.
  - 244 líneas de privilegios: relaciones, columnas, esquemas `app`/`ext`/`public`, privilegios por defecto, funciones (propietario, ACL, `SECURITY DEFINER`, `proconfig`), extensiones, ACL de la BD y triggers.
  - Valores de las 28 secuencias.
- `backup.sh` con app_backup: exit 0, 5 archivos `.age` y manifiesto de medios con 2 entradas.

**Reproducción del defecto (script anterior)**: sobre la BD recién creada por INFRA-DB-000, exit 1 con `ERROR: schema "app" already exists`.

**Simulacro AC-054 final (scripts definitivos)**: `down` → `docker volume rm brujula-ops007_db_data` → `up --wait db` (INFRA-DB-000) → `restore-local.sh` → `post-restore-local.sh`.

| Hito (desde T0 = 2026-09-27T13:35:43Z) | Tiempo |
|---|---|
| BD destruida (`down` + borrado del volumen de datos) | +1 s |
| INFRA-DB-000 terminado (db healthy) | +9 s |
| `restore-local.sh` exit 0: descifrado y sha256 → comprobación de BD limpia → TOC 449 entradas, 444 restauradas y 5 excluidas → una transacción → privilegios por defecto 2 = copia → 2 medios verificados con `sha256sum -c` | +11 s |
| `post-restore-local.sh`: migrate "No migrations to apply" (3 s); 6 comandos `NO_DISPONIBLE`; `up --wait` + `/health/ready` 200 (29 s) | exit **5** |
| **RTO medido (incidente → `/health/ready` 200)** | **48 s** (objetivo ≤ 4 h) |

Dos simulacros previos durante el desarrollo midieron 46 s y 57 s. El de 46 s todavía tenía el defecto de privilegios.

**Comparación antes/después (simulacro final)**
- Conteos (39 tablas): **idénticos**. Por ejemplo `cuenta_staff` 2, `evento_auditoria` 50, `pais` 12, `medio` 1, `medio_derivado` 1 y `django_migrations` 12.
- md5 del contenido: **idéntico** (`d9129711ae89c9befdf07340bc439aee`).
- Privilegios (244 líneas): **idénticos**. Con el preludio de DEC-AUTO-242 retirado, 9 relaciones diferían (§18.3).
- Secuencias (28): **idénticas**. Extensiones: `pg_stat_statements` (postgres) y `unaccent`/`pg_trgm` (app_migrator), igual que antes.
- Esquema: 0 diferencias salvo 27 líneas de CHECK en las que PostgreSQL vuelve a analizar la expresión y la reescribe de otra forma (`= ANY ((ARRAY['X'::varchar])::text[])` → `= ANY (ARRAY[('X'::varchar)::text])`). Son semánticamente iguales (comprobado evaluando las dos formas con un valor válido y uno inválido) y no afectan a Django (RSK-OPS-028).
- Pruebas funcionales tras restaurar:
  - `readonly`: `SELECT password FROM app.cuenta_staff` → permission denied; `sesion_panel` → permission denied; las columnas permitidas de `cuenta_staff` sí se leen.
  - `app_rw`: `DELETE` en `evento_auditoria` → permission denied; `UPDATE` en `revision_contenido` → permission denied.
- Proxy: `GET /health/ready` → 200 y `GET /` (SSR) → 200.
- `manage.py help --commands` lista 106 comandos (incluidos `check` y `migrate`) y **ninguno** de los 6 de ADR-DB-004 §4. `grep` en `backend/apps` tampoco los encuentra. El `NO_DISPONIBLE` es real, no un error al leer la lista.

**Pruebas negativas**

| Caso | Resultado |
|---|---|
| `restore-local.sh` sobre la BD poblada | exit 4 ("NO está limpia: 202 relaciones, 9 funciones"), sin cambios |
| Sin `--confirmar-entorno-local` / con `RESTORE_ENV=prod` | exit 2 / exit 2 |
| `post-restore-local.sh` con la aplicación en marcha | exit 2 ("pararla antes") |
| **Atomicidad**: BD limpia más un objeto conflictivo que la comprobación previa no detecta (`app.es_unaccent`), lo que provoca un fallo a mitad de la restauración | exit 1 "transacción deshecha". Después: 0 relaciones y 0 funciones en `app`, privilegios por defecto 2 (los de INFRA-DB-000) y extensiones solo `plpgsql` y `pg_stat_statements` |
| shellcheck v0.10.0 sobre `restore-local.sh`, `post-restore-local.sh` y `backup.sh` | 0 hallazgos |

**Limpieza**: `down -v --remove-orphans` de `brujula-ops007`, imágenes `*:ops007` borradas, y `.env`, clave age e instantáneas del scratchpad eliminados. No se tocaron otros proyectos (`brujula-tkt004-*`, `brujula_*`).

**NOT_RUN**:
- Los 6 comandos de gestión, porque no existen (RSK-OPS-030).
- Restauración de medios tras **pérdida total** del volumen de medios. En el simulacro el volumen sobrevive y los medios se extraen y verifican en un tmpfs (RSK-OPS-027).
- RTO con el volumen de datos objetivo (< 1 GB de BD y ~5 GB de medios): se midió con un dump de 190 KB (RSK-OPS-029).
- Job de CI que ejecute el simulacro: `.github/workflows/**` está fuera de los `archivos_permitidos` de este ticket (§18.12).

### 18.9 Runbook de restauración (AC-054, simulacro mensual; ADR-DB-004 §4)
Solo en entornos locales o efímeros. Restaurar sobre datos reales, usar la clave age real o hacerlo en un entorno compartido es **Puerta Humana** (CLAUDE.md §0.5). Se ejecuta en bash desde la raíz del repo (en Windows, Git Bash con `MSYS_NO_PATHCONV=1` en las órdenes con `-v`).

```bash
# 0. Contexto del proyecto (ejemplo con proyecto aislado)
export COMPOSE_PROJECT_NAME=brujula COMPOSE_ENV_FILES=.env RESTORE_ENV=local
set -a; . ./.env; set +a; export RESTORE_PGPASSWORD="$APP_MIGRATOR_PASSWORD"
# Localizar la copia: ls de /backups/diarias en el volumen <proyecto>_backups (AAAAMMDD)

# 1. Parar la aplicación ("panel cerrado") y recrear la BD vacía con INFRA-DB-000
docker compose --profile ops down                      # SIN -v: conserva medios, libro y copias
docker volume rm "${COMPOSE_PROJECT_NAME}_db_data"     # solo en el simulacro o con la BD perdida
docker compose up -d --wait db                         # NO levantar el stack: migrate crearía el esquema

# 2. Restaurar BD + verificar medios (contenedor backup; la clave privada, montada en solo lectura
#    y solo durante el simulacro, nunca dentro del repo)
docker compose --profile ops run --rm --no-deps \
  -e RESTORE_ENV -e RESTORE_PGPASSWORD -e MEDIA_RESTORE_DIR=/tmp/medios \
  -v "$HOME/.brujula/age-local.key:/run/age.key:ro" \
  backup bash -c 'mkdir /tmp/medios && restore-local.sh --confirmar-entorno-local AAAAMMDD /run/age.key'
#    exit 0 = BD restaurada en una transacción + manifiesto de medios OK
#    exit 4 = BD no limpia (repetir el paso 1); exit 1 = fallo (la BD queda como la dejó INFRA-DB-000)

# 3. Pasos de aplicación + arranque + /health/ready
bash scripts/ops/post-restore-local.sh --confirmar-entorno-local
#    exit 0 = restauración completa; exit 5 = datos restaurados, pero faltan comandos de gestión
#    (NO_DISPONIBLE): la restauración NO se da por completa; exit 1 = un paso falló
```

Evidencia que se registra en cada simulacro:
- Las líneas de tiempo de ambos scripts (descifrado, pg_restore, medios, cada comando, arranque) y el RTO total.
- Conteos por tipo y estado.
- `verificar_busqueda`, cuando exista.
- `/health/ready` = 200.

Si `restore-local.sh` avisa de que la copia "no contiene" alguna de las 5 entradas excluidas, hay que revisar si INFRA-DB-000 o el origen han cambiado antes de dar la copia por buena.

### 18.10 Riesgos / pendientes

| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-027 | Pérdida **total** del volumen de medios: `restore-local.sh` extrae como uid 999 en un directorio vacío, pero el volumen real lo recrea init-volumes con `publico/` y `privado/` de 10001, que 999 no puede escribir (y el directorio no está vacío). No hay procedimiento automatizado ni validado para devolver los medios al volumen con propietario 10001 | MEDIUM | Ticket DevOps de seguimiento: paso one-shot (imagen `brujula/db`, root con `CHOWN`/`DAC_OVERRIDE`/`FOWNER`, `network_mode: none`) que copie desde un volumen de staging al volumen de medios con `chown 10001:10001` y vuelva a verificar el manifiesto. En este ticket, los medios se verifican íntegros contra el manifiesto (AC-054), pero no se reinstalan | ABIERTO (ticket) |
| RSK-OPS-028 | Tras restaurar, PostgreSQL reescribe los CHECK con `= ANY (ARRAY[...])` de otra forma | INFO | Semánticamente iguales. Una comparación de esquema entre entornos restaurados y migrados debe normalizar esas expresiones | ACEPTADO |
| RSK-OPS-029 | `backup.sh` y `restore-local.sh` trabajan en `/tmp` (tmpfs) dentro de un contenedor limitado a 512 MiB. El tar de medios (~5 GB previstos) y el dump descifrado ocupan memoria del cgroup: a escala de producción, la copia o la restauración terminarían por OOM **[INFERIDO, no medido]**. El RTO de 48 s se midió con 190 KB | MEDIUM (prod) | Ticket DevOps para F9 / ADR de producción: directorio de trabajo en un volumen dedicado (o `tar` → `age` en streaming) y un simulacro con un volumen representativo. No afecta al entorno local actual | ABIERTO (F9) |
| RSK-OPS-030 | Los comandos `reaplicar_anonimizaciones`, `anonimizar_cuentas`, `purgar_auditoria`, `purgar_sesiones`, `reindexar_busqueda` y `verificar_busqueda` no existen. El crontab del scheduler ya los invoca (DEVOPS_HANDOFF §6.7), y sin `reaplicar_anonimizaciones` una restauración podría reactivar cuentas anonimizadas después de la copia (RSK-DB-006) | MEDIUM | Tickets del Developer (TKT-004 y siguientes, según DB_HANDOFF). `post-restore-local.sh` los ejecutará automáticamente en cuanto existan; hasta entonces termina con exit 5. **AC-054 no puede cerrarse como PASS completo** hasta que termine con exit 0 | ABIERTO (Developer) |

### 18.11 Archivos modificados
- `scripts/ops/restore-local.sh`
- `scripts/ops/post-restore-local.sh` (nuevo)
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 18.12 Próximo agente
**Orquestador**, que debe:
1. Enviar la rama `tkt-ops-007-restore` a QA para volver a verificar QA-OPS005-02.
2. Registrar DEC-AUTO-240 a DEC-AUTO-244 y RSK-OPS-027 a RSK-OPS-030.
3. Registrar como hallazgo de seguridad corregido la ampliación de privilegios tras restaurar (§18.3, DEC-AUTO-242). Existía también con la solución de ignorar los 4 errores.
4. Emitir tres tickets:
   - DevOps: restauración de medios con pérdida total (RSK-OPS-027) y directorio de trabajo fuera de tmpfs (RSK-OPS-029).
   - Developer: los 6 comandos de gestión (RSK-OPS-030).
   - Recomendado: un job de CI (`.github/workflows/**`) que ejecute este simulacro sobre una BD migrada con datos de prueba y compare privilegios, para evitar regresiones.

---

## 19. TKT-OPS-006: mejoras LOW de QA (gate, CI, proxy, Dependabot, política de trivy, cache_limites) (F7, soporte)

### 19.1 Estado
**COMPLETADO** en la rama `tkt-ops-006-mejoras`, pendiente de QA. Sin despliegue, sin secretos reales y sin costes (CLAUDE.md §0.5).

### 19.2 Objetivo
| Origen | Hallazgo | Resolución |
|---|---|---|
| OBS-QA-OPS004-01 | `comparar()`/`forma()` del gate de contrato crecían de forma exponencial con esquemas autorreferenciados, y los jobs de CI no tenían `timeout-minutes` | Recorrido memoizado + `timeout-minutes` en todos los jobs (DEC-AUTO-250) |
| OBS-QA-OPS004-02 | El gate aceptaba un objeto abierto en la implementación cuando el contrato lo cierra, y una propiedad sin tipo (`{}`) frente a una tipada | Controles N13 y N14 (DEC-AUTO-251) |
| QA-OPS005-04 | La política de `.trivyignore` no veía opciones prohibidas en líneas de continuación (`\` + salto) | Script que une las continuaciones + controles multilínea (DEC-AUTO-252) |
| OBS-QA-OPS004-03 | `PUT`/`DELETE`/`PATCH` sobre `/media/publico/<imagen>` respondían `405 text/html` con `Cache-Control: immutable` | `405 metodo_no_permitido` en Problem Details (DEC-AUTO-253) |
| RSK-OPS-021 | El comentario de `.github/dependabot.yml` sobre las security updates estaba desactualizado | Corregido: están activadas (DEC-AUTO-230) |
| RSK-OPS-025 | Dependabot no vigilaba `/infra/db` | Añadido, y además corregido un **hallazgo nuevo**: Dependabot no veía ninguna imagen base (§19.3.4, DEC-AUTO-254) |
| RSK-QA004-02 | No había alerta de tamaño de `app.cache_limites` | Script SQL + runbook (DEC-AUTO-255) |

### 19.3 Cambios realizados

#### 19.3.1 Gate de contrato (`infra/ci/gate_contrato.py`)
- **Memoización (DEC-AUTO-250).**
  - `comparar()` guarda los pares `(id(esquema del contrato resuelto), id(esquema generado resuelto))` ya visitados y no los repite. Así termina aunque haya ciclos (`Nodo → Nodo`, `A → B → A`) y su coste es lineal en el número de pares distintos.
  - `forma()` corta los ciclos de `allOf`/`oneOf`/`anyOf` con el conjunto de esquemas en curso.
  - Se elimina el límite artificial de profundidad 40, que era lo que producía la explosión (4 ramas por nivel → 4^40 llamadas).
  - Consecuencia: si el mismo par de esquemas aparece por varias rutas, el error se informa una vez, con la primera ruta.
- **N13, objeto abierto frente a cerrado (DEC-AUTO-251).** El gate falla si el esquema generado declara `additionalProperties: true` o un esquema (incluido `{}`) donde el contrato tiene el objeto cerrado. "Cerrado" usa el mismo criterio que N10: objeto sin `additionalProperties` o con `false`.
- **N14, sin tipo frente a tipado (DEC-AUTO-251).** El gate falla si el esquema generado no restringe nada donde el contrato fija un tipo o una estructura.
  - "No restringe nada" significa `{}`, `true` o solo claves descriptivas: `description`, `title`, `example(s)`, `default`, `readOnly`, `writeOnly`, `deprecated`, `nullable`, `externalDocs`, `xml`, `$comment` y `x-*`.
  - Se aplica a propiedades, `items` y valores de mapas (`additionalProperties` con esquema en ambos lados).
- **Controles.** `infra/ci/gate_contrato_controles.py` contiene 23 casos con fixtures SINTÉTICOS, que no dependen del contrato ni del backend reales (cambian en cada ticket). Cada ejecución del gate tiene un límite de 60 s.

#### 19.3.2 CI (`.github/workflows/ci.yaml`)
- `timeout-minutes` en los 6 jobs, con holgura sobre el último run verde de `main` (36341493130):

  | Job | Duración observada | Límite |
  |---|---|---|
  | detect | ~6 s | 5 min |
  | infra | ~40 s | 15 min |
  | backend | ~4 min 45 s | 30 min |
  | frontend | ~1 min | 20 min |
  | images | ~3 min | 45 min |
  | sign | — | 10 min |

  Los pasos del gate, de sus controles y de la política de trivy tienen además un límite de 5 min cada uno.
- Pasos nuevos:
  - `backend`: "contrato: controles del gate", que ejecuta `gate_contrato_controles.py` antes del gate real.
  - `infra`: "Dependabot cubre todos los Dockerfile" (§19.3.4).
  - `images`: controles de la política de trivy, y después la política desde `infra/ci/politica_trivy.sh` (§19.3.3).
- Smoke del proxy: `PUT`/`DELETE`/`PATCH` sobre `/media/publico/x/y.jpg` deben devolver 405 Problem Details con:
  - `code` `metodo_no_permitido`;
  - `Allow: GET, HEAD`;
  - `Cache-Control: no-store`, sin `immutable`.

#### 19.3.3 Política de trivy (`infra/ci/politica_trivy.sh` + `politica_trivy_controles.sh`, DEC-AUTO-252)
- Antes de buscar nada, el script une las líneas de continuación de shell de todos los workflows (`\` + salto de línea, sin CR). Después aplica sobre las líneas lógicas completas las mismas reglas que antes:
  - variables `TRIVY_*`;
  - `--severity CRITICAL,HIGH` exacto;
  - ni `--config`/`-c`/`--vex`/`--ignore-status`;
  - ni `--ignore-unfixed`/`--ignore-policy`/`--skip-(pkgs|files|dirs)`;
  - `.trivyignore` con caducidad;
  - sin `trivy.yaml` ni `.trivyignore.yaml`.
- Admite `trivy` + espacios variables + subcomando, también con el subcomando en la línea siguiente.
- Los textos de prueba viven en `infra/ci/`, no en `.github/workflows/`: la política no los ve en el repositorio real y el truco `[t]rivy` ya no hace falta.
- Corrige también dos **falsos positivos** de la política anterior: una invocación válida partida en varias líneas y una opción prohibida dentro de un comentario (`# trivy image … --ignore-unfixed`).

#### 19.3.4 Dependabot y Dockerfile (RSK-OPS-021, RSK-OPS-025, DEC-AUTO-254)
- **Hallazgo nuevo (MEDIUM, corregido).** El `file_parser` de Dependabot para Docker (dependabot-core, `docker/lib/dependabot/docker/file_parser.rb`) solo reconoce `FROM` con la imagen **literal** y no resuelve `ARG`.
  - Los 5 Dockerfile usaban `ARG X_IMAGE=…` + `FROM ${X_IMAGE}`, así que el ecosistema `docker` **no vigilaba ninguna imagen base**, no solo la de `/infra/db`.
  - Es coherente con el historial: nunca se abrió un PR `dependabot/docker/*`.
- **Corrección.** `FROM` literal, con la misma referencia `tag@sha256`, en `infra/db/Dockerfile`, `infra/backup/Dockerfile`, `infra/docker/backend.Dockerfile`, `infra/docker/frontend.Dockerfile` e `infra/proxy/Dockerfile`.
  - Ningún `compose*.yaml` ni el CI sobrescribían esos `ARG` (verificado con grep), así que las imágenes resultantes son idénticas.
  - Se quitan los `ARG` para que no quede una segunda copia del digest que Dependabot no actualizaría.
- **`.github/dependabot.yml`:**
  - `directories` del ecosistema `docker`: `/infra/db`, `/infra/docker`, `/infra/proxy`, `/infra/backup`.
  - Grupo `postgres`: `infra/db` (servidor) e `infra/backup` (cliente `pg_dump`) deben compartir digest (ADR-DB-004), así que se actualizan en un solo PR.
  - Comentario de las security updates corregido: están **activadas** en el repositorio (DEC-AUTO-230). Verificado el 2026-09-28 con `gh api repos/magoolf/brujula-salvaje/automated-security-fixes` → `{"enabled":true,"paused":false}`.
  - Comentario del ecosistema `docker-compose` actualizado: hoy `compose*.yaml` no fija imágenes de terceros.
- **Paso de CI "Dependabot cubre todos los Dockerfile".** Falla si algún `Dockerfile`, `*.Dockerfile` o `Dockerfile.*` del repositorio:
  - está en un directorio que no figura en el ecosistema `docker`, o
  - tiene un `FROM` con variable (`$X` o `${X}`, también con `--platform`).

#### 19.3.5 Proxy: 405 de medios (`infra/proxy/nginx.conf`, DEC-AUTO-253)
- `error_page 405 =405 /_errores_proxy/405` y una location interna que devuelve Problem Details `metodo_no_permitido` con:
  - título y detalle del catálogo `apps/core/problemas.py`;
  - `trace_id`;
  - las 11 cabeceras de `security-headers-error.conf` (incluido `Cache-Control: no-store`);
  - `Allow: GET, HEAD` (RFC 9110 §15.5.6).
- La redirección interna cambia de location, así que la respuesta ya no hereda el `Cache-Control … immutable` de la location de imágenes.
- `POST` y `OPTIONS` sobre una imagen también devolvían 405 (módulo estático de nginx) y ahora salen igual.
- Sin cambios en `GET`/`HEAD` de imágenes, en el 404 (medios inexistentes o que no son imagen) ni en el 403 de `limit_except` (p. ej. `PUT` sobre `/media/publico/a/foto.txt` o `POST /`).

#### 19.3.6 Alerta de tamaño de `app.cache_limites` (RSK-QA004-02, DEC-AUTO-255)
- `infra/ops/cache_limites_tamano.sql` es de solo lectura.
  - Umbrales por defecto: **> 50 000 filas o > 64 MB** (tabla + índices + TOAST), configurables con `-v max_filas=…` y `-v max_bytes=…`.
  - Informa de filas, filas caducadas y tamaño.
  - Si se supera un umbral, termina con `ERROR` (psql con `ON_ERROR_STOP` → exit 3); si no, con exit 0.
  - Con un rol sin `SELECT` sobre la tabla (p. ej. `readonly`, que por diseño no la lee, ADR-DB-001) usa la estimación de `pg_class.reltuples` y el tamaño, que no requieren privilegios.
- **Ejecución manual** (stack local):
  ```bash
  docker compose exec -T db psql -U postgres -d brujula -X -q -v ON_ERROR_STOP=1 -f - < infra/ops/cache_limites_tamano.sql
  # umbrales propios:
  docker compose exec -T db psql -U postgres -d brujula -X -q -v ON_ERROR_STOP=1 -v max_filas=20000 -v max_bytes=33554432 -f - < infra/ops/cache_limites_tamano.sql
  ```
- **Ejecución programada.** La imagen del scheduler (Django, rol `app_rw`) no trae `psql`, y un comando de gestión es código de aplicación (`backend/`, fuera de lo que §0.3 permite a DevOps).
  - Propuesta de ticket para el Developer: comando `vigilar_cache_limites` con la misma consulta y los mismos umbrales (settings `CACHE_LIMITES_MAX_FILAS=50000` y `CACHE_LIMITES_MAX_BYTES=67108864`).
  - Si se supera un umbral, sale con código ≠ 0 y un log JSON `nivel=ERROR`.
  - Como el resto de comandos, usa `pg_try_advisory_lock` y registra su ejecución en `ops_ejecucion_tarea`.
  - Cuando exista, se añade a `infra/scheduler/crontab`, p. ej. `*/15 * * * * python manage.py vigilar_cache_limites`.
  - En producción, la alerta la recoge el sistema de logs y alertas (Skill_devops §23.5, F9).
- **Runbook si salta la alerta:**
  1. Mirar la proporción `caducadas / filas`. Si es alta, autovacuum o la purga de `DatabaseCache` (que solo purga al superar `MAX_ENTRIES`) no dan abasto. Ejecutar `VACUUM (VERBOSE) app.cache_limites` y revisar `pg_stat_user_tables` (`n_dead_tup`, `last_autovacuum`).
  2. Si hay pocas caducadas y muchas filas, hay tráfico anómalo (muchas IP o claves distintas). Revisar la ráfaga en el access log del proxy (IP truncada) y, si procede, endurecer `limit_req` en el borde (RSK-DB-008).
  3. La tabla es UNLOGGED y efímera (TTL ≤ 1 h). En una emergencia, `TRUNCATE app.cache_limites` reinicia los contadores de throttling y los bloqueos temporales, **y por tanto desbloquea las cuentas bloqueadas por intentos**. Es una decisión operativa; en un entorno compartido requiere aprobación humana (CLAUDE.md §0.5).

### 19.4 Versiones aprobadas
No cambia ninguna versión ni ningún digest: las mismas referencias `tag@sha256` pasan de `ARG` a `FROM`.

Herramientas usadas solo para validar (no entran en el repositorio):
- actionlint `rhysd/actionlint:1.7.7` (incluye shellcheck);
- `koalaman/shellcheck:v0.10.0`;
- check-jsonschema 0.33.0 (esquemas `vendor.dependabot` y `vendor.github-workflows`);
- js-yaml 4.1.0.

### 19.5 Infraestructura
- Proxy: una location interna nueva.
- Dockerfile: `FROM` literal.
- CI: 3 pasos nuevos y 1 bloque de smoke.

### 19.6 Dependencias
Sin cambios de manifest ni de lockfile.

### 19.7 Variables de entorno
Sin cambios. Los umbrales de la alerta son variables de psql.

### 19.8 Validaciones ejecutadas (2026-09-27/28, Docker Engine 29.6.1)

#### 19.8.1 Gate de contrato
**Sobre el contrato y el esquema REALES.** `contracts/openapi.yaml` (127 operaciones) frente a `manage.py spectacular --validate` de esta rama (25 operaciones implementadas), con mutaciones en el scratchpad:

| Caso | Esperado | Gate nuevo | Gate anterior (`origin/main`), límite 120 s |
|---|---|---|---|
| BASE (esquema real) | 0 | 0 (1,6 s) | 0 |
| N1, N3, N8, N9, N10 | 1 | 1 | 1 |
| N13a/b/c: `additionalProperties` `{}` / `true` / `{type: string}` en `Cuenta`/`SesionEstado` | 1 | **1** | 0 (no detectado) |
| N14a/b: propiedad `{}` / solo descriptiva frente a tipada | 1 | **1** | 0 |
| N14c: `items: {}` frente a `$ref Cuenta` | 1 | **1** | 0 |
| N14d/e: valor de `errors{*}` `{}` / `true` frente a array tipado | 1 | **1** | 0 |
| P3 (solo cambia `description`) y P4 (contrato sin tipo, implementación tipada) | 0 | 0 | 0 |
| A1: `Nodo` autorreferenciado idéntico (2 referencias + array) | 0 | **0 (1,5 s)** | **TIMEOUT 120 s** |
| A2: A1 + propiedad extra | 1 | **1 (1,5 s)** | TIMEOUT |
| A3: `anyOf` con 3 autorreferencias | 0 | **0 (1,5 s)** | TIMEOUT |
| A4: A3 + objeto abierto | 1 | **1** | TIMEOUT |
| A5: recursión mutua `Nodo ↔ B` | 0 | **0** | TIMEOUT |
| A6: A5 + `B` abierto | 1 | **1** | TIMEOUT |
| A7: A5 + `items: {}` | 1 | **1** | TIMEOUT |

- Gate nuevo: 23/23. Gate anterior: 8/23 (8 omisiones y 7 timeouts). Casi todo el tiempo del gate nuevo es la carga del YAML.
- Con `infra/ci/gate_contrato_controles.py` (los casos sintéticos que ejecuta el CI): gate nuevo 23/23, entre 0,10 y 0,16 s por caso. Gate anterior: 15 fallos (8 omisiones y 7 `TIMEOUT` de 60 s).
- `ruff check` y `ruff format --check` (configuración del backend) sobre `infra/ci/`: OK.

#### 19.8.2 Política de trivy
`bash infra/ci/politica_trivy_controles.sh` pasa **18/18**:
- P0: repositorio real.
- P1: invocación válida en 3 líneas.
- P2: opción prohibida dentro de un comentario.
- S1-S6, en una línea: `--ignore-unfixed`, `TRIVY_IGNORE_UNFIXED`, severidad distinta, `trivy.yaml`, entrada sin caducidad, comodín.
- M1-M9, multilínea:
  - `--ignore-unfixed`;
  - `--config` en la 3.ª línea;
  - `-c`;
  - `--skip-files`;
  - `trivy` e `image` en líneas distintas, con `--vex`;
  - `--ignore-status`;
  - `trivy config --ignore-policy`;
  - invocación partida sin `--severity`;
  - continuación con CRLF.

Cada caso negativo falla por su regla (mensaje `::error::` comprobado).

La política anterior (extraída tal cual del CI de `origin/main`) con los mismos controles da 9 fallos:
- **7 falsos negativos**: M1, M3, M4, M5, M6, M7 y M9 pasan con rc 0. Reproduce QA-OPS005-04.
- **2 falsos positivos**: P1 y P2.

`shellcheck v0.10.0` sobre los dos scripts: 0 avisos.

#### 19.8.3 Proxy (405)
- Imagen `brujula/proxy:ops006` construida desde `infra/proxy`. Por la memoria justa del host se ejecutó sola:
  - `--read-only`, tmpfs en `/tmp`, `--add-host` para backend/frontend y 128 MiB;
  - un volumen de medios de prueba de solo lectura.
- Los errores del proxy no dependen de los upstreams. `nginx -t`: OK.

| Petición | Resultado |
|---|---|
| `GET`/`HEAD /media/publico/a/foto.jpg` | 200 `image/jpeg` con `Cache-Control: public, max-age=31536000, immutable` (sin cambios) |
| `PUT`/`DELETE`/`PATCH`/`POST`/`OPTIONS` sobre la imagen | **405 `application/problem+json`**: `code` `metodo_no_permitido`, `trace_id` de 32 hex, `Allow: GET, HEAD`, `Cache-Control: no-store` y las 11 cabeceras de seguridad |
| `PUT /media/publico/no/existe.jpg` | 405 Problem Details |
| `PUT /media/publico/a/foto.txt` y `POST /` | 403 Problem Details (sin cambios) |
| `GET` de `/media/publico/no/existe.webp`, `/media/publico/a/foto.txt`, `/media/privado/x.jpg` y `/health/otra` | 404 Problem Details (sin cambios) |
| **Línea base**: la misma imagen con el `nginx.conf` de `origin/main`, `PUT` sobre la imagen | `405 text/html` + `Cache-Control: public, max-age=31536000, immutable` (reproduce OBS-QA-OPS004-03) |

#### 19.8.4 Dependabot y Dockerfile
- `check-jsonschema --builtin-schema vendor.dependabot .github/dependabot.yml`: OK.
- `docker build --check` sobre los 5 Dockerfile (con `--build-context ops=scripts/ops` en backup e `infra=infra` en backend): "Check complete, no warnings found".
- Las 6 imágenes se construyen de verdad en el job `images` del CI.
- Paso "Dependabot cubre todos los Dockerfile", extraído del CI:

| Caso | rc | Motivo |
|---|---|---|
| P0: repositorio | 0 | |
| N1: sin `/infra/db` | 1 | directorio no listado |
| N2: proxy con `FROM ${NGINX_IMAGE}` (versión de `main`) | 1 | `FROM` con variable |
| N3: Dockerfile nuevo en `infra/nuevo` | 1 | directorio no listado |
| N4: `FROM --platform=… ${IMG}` | 1 | `FROM` con variable |
| N5: `FROM $IMG` | 1 | `FROM` con variable |

#### 19.8.5 `cache_limites`
PostgreSQL 18.6 desechable (misma imagen y digest que `infra/db`, 256 MiB) con la DDL exacta de `ops.0001_inicial` (tabla UNLOGGED + índice):

| Caso | rc |
|---|---|
| T1: 1000 filas (100 caducadas), 272 kB, umbrales por defecto | 0 (OK) |
| T2: `max_filas=500` | 3 (ALERTA) |
| T3: `max_bytes=100000` | 3 |
| T4: 53 000 filas / 84 MB, umbrales por defecto | 3 |
| T5: rol `readonly` sin `SELECT` (estimación `reltuples` = 53 000) | 3 |

#### 19.8.6 CI, YAML y secretos
- `actionlint 1.7.7` (con shellcheck) sobre `ci.yaml`: 0 errores.
- `check-jsonschema vendor.github-workflows`: OK.
- `js-yaml 4.1.0` sobre `ci.yaml` y `dependabot.yml`: OK.
- gitleaks y el run de GitHub Actions: ver el `HANDOFF_ENVELOPE` de TKT-OPS-006 (SHA y URL del run).

#### 19.8.7 Limpieza
- Contenedores `brujula-ops006-proxy`, `brujula-ops006-proxy-viejo` y `brujula-ops006-pg` eliminados; imagen `brujula/proxy:ops006` eliminada.
- No se tocó `brujula-tkt005-db-1`.
- Los fixtures quedaron en el scratchpad de la sesión, fuera del repositorio.

#### 19.8.8 NOT_RUN
- **Stack completo local `-p brujula-ops006` (`APP_NET_PREFIX` 10.231.60)**: sustituido por el proxy aislado de §19.8.3 porque el host tiene la memoria justa. El 405 sobre el stack completo lo cubre el smoke del CI.
- **`oasdiff` local**: el gate nuevo no cambia su entrada (el contrato filtrado); se ejecuta en CI.
- **Primer PR real de Dependabot docker**: llegará en la próxima ventana semanal (lunes 06:00, Europe/Madrid) tras integrar la rama.

### 19.9 Seguridad
- Sin secretos: la contraseña del PostgreSQL desechable fue un literal local que no entra en el repositorio.
- El 405 del borde no revela la versión (`server_tokens off`) y lleva las cabeceras de seguridad.
- La política de trivy es más estricta (opciones prohibidas en líneas de continuación) y más precisa (sin falsos positivos).

### 19.10 Riesgos / pendientes
| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-021 | Security updates de Dependabot | LOW | Activadas (DEC-AUTO-230) y comentario corregido | CERRADO |
| RSK-OPS-025 | Dependabot no vigilaba `/infra/db` y, en realidad, ninguna imagen base (`ARG` en `FROM`) | MEDIUM | `FROM` literal + los 5 directorios + paso de cobertura en CI | MITIGADO (se confirma con el primer PR `dependabot/docker/*`) |
| RSK-OPS-031 | Los PR de Dependabot docker cambiarán el SO base (digest de `postgres`, imágenes de runtime) y, con él, las CVE que cubre `.trivyignore` | LOW | Pasan por el CI completo (trivy con `.trivyignore` caducable) y por QA. El `.trivyignore` solo lo cambia una decisión humana (RSK-OPS-001) | ABIERTO (proceso) |
| RSK-OPS-032 | La alerta de `cache_limites` solo se podía ejecutar a mano hasta que existiera el comando `vigilar_cache_limites` (Developer) | LOW | TKT-011 (Developer, DONE) entregó el comando; TKT-OPS-012 añadió la línea `*/15 * * * * python manage.py vigilar_cache_limites` a `infra/scheduler/crontab` (§22) | CERRADO |
| RSK-QA004-02 | Nadie vigila el tamaño de `cache_limites` | LOW | Consulta y umbrales documentados y probados (§19.3.6); ejecución programada cada 15 min desde TKT-OPS-012 (§22) | MITIGADO (programado) |

### 19.11 Archivos modificados
- `infra/ci/gate_contrato.py`
- `infra/ci/gate_contrato_controles.py` (nuevo)
- `infra/ci/politica_trivy.sh` (nuevo)
- `infra/ci/politica_trivy_controles.sh` (nuevo)
- `infra/ops/cache_limites_tamano.sql` (nuevo)
- `infra/proxy/nginx.conf`
- `infra/proxy/Dockerfile`
- `infra/db/Dockerfile`
- `infra/backup/Dockerfile`
- `infra/docker/backend.Dockerfile`
- `infra/docker/frontend.Dockerfile`
- `.github/workflows/ci.yaml`
- `.github/dependabot.yml`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 19.12 Próximo agente
**Orquestador**, que debe:
1. Enviar a QA la rama `tkt-ops-006-mejoras`.
2. Registrar DEC-AUTO-250 a DEC-AUTO-255 y RSK-OPS-031/032, y cerrar RSK-OPS-021.
3. Emitir el ticket del Developer `vigilar_cache_limites` (RSK-OPS-032).

## 20. TKT-OPS-010 — gate de contrato: `oasdiff breaking --fail-on WARN` → `--fail-on ERR` (decisión del usuario) (F7, soporte)

### 20.1 Estado
**COMPLETADO.** Cambio mínimo y acotado de CI, en la rama `tkt-ops-010-gate-error`. Sin despliegue, sin secretos reales y sin costes (CLAUDE.md §0.5); no activa ninguna Puerta Humana adicional porque la decisión humana que autoriza este cambio ya se tomó (audit_log.md, 2026-09-29).

### 20.2 Objetivo
Durante TKT-006 (panel editorial, ~128 operaciones), el paso "contrato: gate por operación + oasdiff" del job `backend` se ejecutó por primera vez hasta el final contra una superficie de API grande y encontró 677 diferencias entre `contracts/openapi.yaml` (API-first, escrito a mano) y el esquema generado por drf-spectacular a partir de la implementación real: 69 de severidad `error` y 608 de severidad `warning`. Tras cuatro rondas de corrección del Developer sin convergencia (el conteo de hallazgos empeoró de 296 a 677 entre la ronda 2 y la 4, porque corregir el `allOf` de paginación permitió que oasdiff recorriera más profundidad y revelara una capa nueva de hallazgos de bajo nivel: 177 `pattern`, 199 `maxItems`, 58 `max`, 36 `tipo`, 32 `uniqueItems`, 60 `content-media-type`, 28 `required`, etc.), el Orquestador presentó la situación al usuario, que decidió explícitamente: **relajar el gate para que solo los hallazgos de severidad `error` bloqueen el CI**, no los `warning`.

Los `warning` son abrumadoramente de fidelidad de formato/patrón/límites en campos anidados (`pattern`, `maxItems`, `minItems`, `content-media-type`, `uniqueItems`) — diferencias de documentación del esquema, no rupturas de compatibilidad real: DRF no aplica esas anotaciones como validación en tiempo de ejecución. Los `error` (`max/min-items` añadidos o quitados, `one-of-added`, `min-length/max` añadidos, una propiedad que pasa a opcional, tipo de body cambiado) sí son señales de posibles rupturas reales de compatibilidad y **siguen bloqueando**.

### 20.3 Cambios realizados
- **`.github/workflows/ci.yaml`, job `backend`, paso "contrato: gate por operación + oasdiff"**: el único cambio funcional es el flag del comando `oasdiff breaking`:
  - Antes: `oasdiff breaking /tmp/contrato-filtrado.yaml /tmp/generado.yaml --fail-on WARN`
  - Ahora: `oasdiff breaking /tmp/contrato-filtrado.yaml /tmp/generado.yaml --fail-on ERR`
  - Ningún otro flag de ese comando, ni de los pasos vecinos, cambia. El paso anterior de la misma etapa (`infra/ci/gate_contrato.py`, controles N1-N14) es un gate distinto y separado, ya en 0 errores, y no se toca.
  - Se actualiza también el comentario explicativo que precede al paso (líneas ~194-200), que documentaba literalmente `--fail-on WARN` como parte del gate: ahora documenta `--fail-on ERR` y referencia esta sección.
- **`infra/ci/gate_contrato.py`**: el docstring (líneas 1-33) menciona el flag dos veces como parte del contrato documentado del propio script (uso en la cabecera y en el punto 5). Se actualizan ambas menciones a `--fail-on ERR`, con nota de que antes era `WARN` y referencia a TKT-OPS-010. **Ningún cambio de lógica**: el script sigue siendo el mismo gate N1-N14, byte a byte salvo esos dos comentarios.
- **Búsqueda de consistencia (obligatoria por el ticket)**: se buscó `--fail-on WARN` y `oasdiff breaking` en todo el repositorio. Aparecen además en `docs/adr/ADR-API-002.md`, `backend/apps/core/esquema.py` y `backend/apps/core/tests/test_ac_tkt004_09_contrato.py` — los tres fuera de `archivos_permitidos` de este ticket (`.github/workflows/**`, `docs/05_operacion/**`); no se tocan, quedan como referencia histórica/del Developer. No hay ningún otro workflow ni script en `infra/ci/**` que invoque `oasdiff breaking` de forma independiente: es una única invocación real en todo el pipeline (la de `ci.yaml`), ya corregida.
- **Ninguna migración de datos, ninguna imagen, ninguna dependencia ni lockfile.**

### 20.4 Versiones aprobadas
Sin cambios: `oasdiff` sigue en `1.32.1` (verificado con sha256 en el propio paso), PyYAML del lock del backend.

### 20.5 Infraestructura
Sin cambios de topología, redes, healthchecks ni contenedores. Cambio exclusivamente de un flag de un paso de CI.

### 20.6 Dependencias
Ninguna.

### 20.7 Variables de entorno
Ninguna nueva ni modificada.

### 20.8 Validaciones ejecutadas
- **VALIDADO** — sintaxis YAML: `.github/workflows/ci.yaml` se parseó con éxito con PyYAML 6.0.3 (venv efímero local) tras el cambio; el paso "contrato: gate por operación + oasdiff" se extrajo del árbol resultante y su `run:` contiene exactamente `oasdiff breaking /tmp/contrato-filtrado.yaml /tmp/generado.yaml --fail-on ERR`, sin alterar ningún otro flag ni línea vecina.
- **NO VALIDADO (corrección tras CI real)** — el valor correcto del flag `--fail-on`. La primera entrega de este ticket usó `--fail-on ERROR`, sin poder ejecutar el binario `oasdiff` localmente (no está instalado en este entorno) ni `oasdiff breaking --help`. El CI real del PR #25 (run 36561133019) lo ejecutó con el binario real y falló con un error de uso, no de contrato: `Error: invalid argument "ERROR" for "-o, --fail-on" flag: ERROR is not one of the allowed values: ERR or WARN`. Se corrigió a `--fail-on ERR` en los tres archivos (`ci.yaml`, `gate_contrato.py`, este documento). Confirmado además por fuente externa (no ejecución local): `docs/BREAKING-CHANGES.md` y `internal/breaking_changes.go`/`internal/level_test.go` del repositorio upstream `oasdiff/oasdiff` (consultados vía `gh search code`) documentan los valores `ERR`, `WARN`, `INFO`; ningún uso de `ERROR` aparece en el código o la documentación del proyecto. Esta corrección queda pendiente de la confirmación final que solo puede dar la re-ejecución real del CI del PR, como pidió el Orquestador.
- **NO VALIDADO** — `actionlint`: no está disponible en este entorno local en el momento de este cambio (`actionlint: command not found`; tampoco se encontró el binario en el PATH esperado). VERSIONS.md registra su uso en TKT-OPS-006 (ciclo 3), pero no está instalado ahora. No se afirma una validación de esquema de GitHub Actions que no se ejecutó. Este segundo fallo (un valor de enum inválido en un flag) es exactamente el tipo de error que `actionlint` con `action-validator`/schema de `oasdiff` no habría detectado tampoco (es un error del binario `oasdiff`, no de sintaxis de GitHub Actions); no habría cambiado el resultado.
- **NO VALIDADO** — `docker compose config`: no aplica a este cambio (no toca ningún `compose*.yaml`), tal como indicó el ticket.
- **NO APLICABLE / pendiente de confirmación separada** — ejecución real del pipeline de CI con el flag corregido: este PR, al recibir el push de corrección, volverá a disparar su CI (que usará `--fail-on ERR`); no hay ninguna superficie de API grande en `main` todavía (TKT-006 no está fusionado) para observar el efecto completo del cambio (pasar de 677 a solo los `error`). Si el PR de TKT-006 se beneficia de este cambio, se confirmará por separado cuando se re-ejecute su CI, tal como pidió el Orquestador.
- **NO NECESARIO A JUICIO DE DEVOPS** — QA formal (Skill_QA): es un cambio de un único flag de un comando de CI ya existente, sin lógica nueva, sin superficie de ataque nueva y sin cambio de comportamiento de la aplicación; el propio pipeline de CI del PR (que ejecutará el paso con el flag nuevo) sirve de validación funcional del cambio. Se deja constancia explícita por si el Orquestador prefiere pasarlo de todos modos por QA.

### 20.9 Seguridad
- Sin secretos, sin cambios de superficie de red ni de imágenes.
- **Riesgo aceptado por el usuario** (registrado en `audit_log.md`, 2026-09-29): a partir de este cambio, la documentación de contrato pierde precisión de formato/patrón/límites (`pattern`, `maxItems`, `minItems`, `content-media-type`, `uniqueItems`) frente a lo realmente implementado, hasta que se cierre TKT-012. Esto no relaja ninguna validación en tiempo de ejecución de DRF (esas anotaciones no se aplican como validación real), solo la fidelidad de la especificación publicada.
- Lo que sigue bloqueando el CI sin cambios: los 69 hallazgos de severidad `error` (posibles rupturas reales de compatibilidad: `max/min-items` añadidos o quitados, `one-of-added`, `min-length/max` añadidos, propiedad que pasa a opcional, tipo de body cambiado) y el gate `gate_contrato.py` (N1-N14, operaciones/códigos/media types/propiedades no documentados), que sigue en 0 errores.

### 20.10 Riesgos / pendientes
| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-035 | Los 608 hallazgos `warning` (fidelidad de formato/patrón/límites) dejan de bloquear el CI y quedan como deuda técnica hasta que se cierren | LOW | TKT-012 (Backend, deuda técnica, seguimiento) | ABIERTO (ticket) |
| RSK-OPS-036 | `actionlint` no está disponible en este entorno local; el YAML del workflow solo se validó como sintaxis (PyYAML), no contra el esquema de GitHub Actions | LOW | Instalar `actionlint` (versión fijada en VERSIONS.md) antes del próximo cambio de `.github/workflows/**`, o confiar en el propio CI del PR como validación de esquema | ABIERTO |
| RSK-OPS-037 | La primera entrega de este ticket usó `--fail-on ERROR`, un valor inválido para `oasdiff breaking` (solo admite `ERR`/`WARN`/`INFO`), sin poder validarlo localmente por falta del binario. El CI real del PR #25 (run 36561133019) lo detectó como fallo de uso del comando, no de contrato | LOW (detectado antes de fusionar, sin efecto en `main`) | Corregido a `--fail-on ERR` en los 3 archivos; confirmado además contra la documentación y el código fuente upstream de `oasdiff/oasdiff` (§20.8). Pendiente de re-ejecución del CI del PR para confirmación final | CORREGIDO (pendiente confirmación CI) |

### 20.11 Archivos modificados
- `.github/workflows/ci.yaml`
- `infra/ci/gate_contrato.py` (solo comentarios del docstring, sin cambio de lógica)
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 20.12 Próximo agente
**Orquestador**, que debe:
1. Confirmar en el CI real del PR #25 (tras el push de corrección de §20.13) que el paso de contrato ya no falla por uso del comando (`invalid argument "ERROR"...`) y que `--fail-on ERR` se comporta como se espera (verde esperado: sin nuevos hallazgos `error` en la superficie actual de `main`, sin operaciones del panel de TKT-006).
2. Cuando TKT-006 re-ejecute su CI con este cambio ya integrado (o mediante rebase/merge de `main`), confirmar si los 69 hallazgos `error` restantes siguen bloqueando y si el Developer necesita una quinta ronda de corrección, o si ya puede pasar a QA.
3. Mantener TKT-012 (deuda técnica de los 608 `warning`) en el backlog, con trazabilidad a TKT-006 y TKT-OPS-010.

### 20.13 Corrección (mismo ticket, mismo PR): `--fail-on ERROR` → `--fail-on ERR`
- **Origen:** el Orquestador verificó el CI real del PR #25 (run 36561133019): el paso de contrato falló, pero no por un hallazgo del gate — el binario `oasdiff` rechazó el propio flag: `Error: invalid argument "ERROR" for "-o, --fail-on" flag: ERROR is not one of the allowed values: ERR or WARN`.
- **Causa:** en la entrega original de este ticket, DevOps no tenía el binario `oasdiff` disponible localmente para verificar `oasdiff breaking --help` y asumió (incorrectamente) que el valor era `ERROR` en vez de `ERR`. La instrucción original del Orquestador y el estado de `kanban.md`/`audit_log.md` también usan la forma `ERROR` en prosa; ninguno de los dos es la fuente de verdad del flag — el binario lo es.
- **Corrección aplicada:** `--fail-on ERROR` → `--fail-on ERR` en los tres archivos: `.github/workflows/ci.yaml` (comando real + comentario explicativo), `infra/ci/gate_contrato.py` (dos menciones del docstring) y esta sección del handoff (título, §20.3, §20.8, §20.12). Ningún otro contenido cambia.
- **Verificación antes de este segundo commit:** sin binario `oasdiff` local (confirmado de nuevo: `oasdiff: command not found`, sin resultado en una búsqueda de archivo por todo el sistema), por lo que **no se pudo ejecutar `oasdiff breaking --help` ni reproducir el comando real**. Se buscó en su lugar el código fuente y la documentación del proyecto upstream `oasdiff/oasdiff` en GitHub (`gh search code "fail-on" repo:oasdiff/oasdiff`): `docs/BREAKING-CHANGES.md` ("To exit with return code 1 if ERR-level changes are found, add the `--fail-on ERR` flag" / "...if ERR-level or WARN-level changes are found, add the `--fail-on WARN` flag"), `docs/VALIDATE.md` (tabla: `-o, --fail-on` acepta `ERR`, `WARN`, o `INFO`), `internal/breaking_changes.go` y `internal/level_test.go` (enum de niveles soportados) — ninguno menciona `ERROR` como valor válido en ningún comando. Esto es **NO VALIDADO por ejecución local**, pero sí corroborado por el propio mensaje de error del binario real en el CI del PR y por el código/documentación fuente del proyecto.
- **Pendiente:** la confirmación definitiva es que el CI del PR #25, tras este push, pase el paso de contrato sin el error de uso (quedando solo, si acaso, hallazgos reales de severidad `error` del contrato) — a verificar por el Orquestador.

### 19.13 Ciclo 2 (QA_VERDICT FAIL, ciclo_qa 1/3): política de trivy con parser YAML, OBS-1/3/4/5

**Estado:** COMPLETADO, pendiente de re-QA. En el ciclo 1 pasaron el gate, el 405, Dependabot, el SQL y el CI. Esta sección sustituye a §19.3.3 en lo que difiera.

#### 19.13.1 Correcciones
| Hallazgo | Corrección |
|---|---|
| **QA-OPS006-01** (MEDIUM, regresión): el `sed` unía un COMENTARIO que acaba en `\` con la línea siguiente y ocultaba la invocación real | La política es ahora `infra/ci/politica_trivy.py`, y `politica_trivy.sh` queda como envoltorio. Recorre cada cadena como shell, carácter a carácter y respetando comillas y escapes. Cuando encuentra un comentario (`#` al principio de una palabra), lo quita y **no** une la línea siguiente, igual que bash. Además, las opciones prohibidas se buscan en las líneas **físicas** y en las **lógicas**, así que unir nunca puede ocultar nada. Las opciones obligatorias (severidad, `--exit-code` del gate) se exigen sobre la línea lógica completa (DEC-AUTO-256) |
| **QA-OPS006-02** (LOW): escalares YAML `run: >` (folded) y planos multilínea | Los workflows se cargan con **PyYAML** y se analizan los valores **resueltos** de **todas** las cadenas (`run:`, `with:`, `env:`…). Un folded o plano que YAML junta en un solo comando se analiza junto. Los comentarios YAML desaparecen. Un workflow con YAML no válido hace fallar la política |
| **OBS-3** | Falla ante: <br>- `--severity`/`-s`/`--severity=` que no sea exactamente `CRITICAL,HIGH`, aunque haya varias (la 2.ª anula la 1.ª); <br>- `--ignorefile` distinto de `.trivyignore`; <br>- `--exit-code 0`; <br>- una invocación con `--ignorefile` (el gate) sin `--exit-code` distinto de 0; <br>- `uses: aquasecurity/trivy-action` o `setup-trivy`; <br>- la imagen `aquasec/trivy`; <br>- un `with:` con `ignore-unfixed`/`trivyignores`/`severity`/`trivy-config`/`skip-*`; <br>- claves `env:` `TRIVY_*` de configuración. <br>Exige al menos un gate (`--ignorefile .trivyignore --exit-code 1`) en los workflows. Reconoce `trivy` con ruta absoluta (`/usr/local/bin/trivy`), flags globales antes del subcomando (`trivy -q image`) y tabuladores. También revisa los `*.sh` del repositorio (salvo el fichero de controles) |
| Consecuencia de OBS-3 en el CI | El control negativo "`.trivyignore` caducado" ya no puede usar `--ignorefile /tmp/trivyignore-caducado`. Ahora escribe `/tmp/neg/.trivyignore` y ejecuta `(cd /tmp/neg && trivy … --ignorefile .trivyignore --exit-code 1 …)`. Mismo efecto |
| Ubicación en el CI | La política y sus controles pasan del job `images` al job **`infra`**: se ejecutan siempre y antes (fail-fast). PyYAML `${PYYAML_VERSION}` = 6.0.3 se instala en un venv efímero en `$RUNNER_TEMP` y la política lo usa mediante `$PYTHON` |
| **OBS-4** | La cobertura de Dependabot pasa a `infra/ci/dependabot_cobertura.sh`, con controles en `dependabot_cobertura_controles.sh` (DEC-AUTO-257): <br>- `FROM` sin distinguir mayúsculas (`from ${IMG}`); <br>- nombres `Dockerfile`, `*.Dockerfile`, `Dockerfile.*`, `Containerfile`, `*.Containerfile` y `Containerfile.*`, sin distinguir mayúsculas (`app.dockerfile`) |
| **OBS-5** | `\set ON_ERROR_STOP on` dentro de `infra/ops/cache_limites_tamano.sql`: la alerta sale con código ≠ 0 aunque no se pase `-v ON_ERROR_STOP=1` |
| **OBS-1** (y lo que se encontró con `qa_gate2.py`) | Nuevos errores de clase N14 en el gate: <br>- N14h: `{type: object}` sin `properties` ni `additionalProperties` donde el contrato tiene estructura; <br>- N14i: `{type: array}` sin `items` donde el contrato tiene `items`; <br>- N14f/g: rama de `oneOf`/`anyOf` sin tipo (`{}` o solo descriptiva) donde el contrato está tipado (Q-N6/Q-N7 de QA daban rc 0) |

**Nota sobre los casos Q1, Q2 y Q5 del arnés `qa_trivy.sh` de QA.** Esos fixtures están escritos entre comillas dobles con una sola `\` antes del salto de línea. Dentro de comillas dobles, bash **elimina** `\` + salto, así que el fichero generado no contiene la continuación:
- Q1 queda como una sola línea: `# nota trivy image … --ignore-unfixed img`. Es un comentario completo, y en bash no ejecuta nada.
- Q2 queda como `echo a # ver trivy image …`, igualmente dentro de un comentario.

Con esos ficheros, la política da rc 0, que es la semántica correcta de shell y la misma que QA exige en Q7 (comentario al final de la línea con la opción prohibida → 0). Los casos que QA pretendía (comentario terminado en `\` seguido de la invocación real en la línea siguiente) están en `politica_trivy_controles.sh`, escritos con `\\`, y fallan como deben: Q1, Q2 → rc 1. Es la trampa que avisa la cabecera del script de controles.

#### 19.13.2 Validaciones (2026-09-28)
- **`politica_trivy_controles.sh`**: **39/39**. Se mantienen los 18 casos anteriores (P0-P2, S1-S6, M1-M9) y se añaden 21:
  - Q1: comentario terminado en `\` seguido de la invocación con `--ignore-unfixed` → 1.
  - Q2: `echo a # ver \` seguido de `--config` → 1.
  - Q3: `run: >` → 1.
  - Q4: escalar plano multilínea → 1.
  - Q7: opción en un comentario al final de la línea → 0.
  - Q8: comentario terminado en `\` seguido de una línea inocua → 0.
  - Q9: segunda `--severity` → 1.
  - Q10: `-s LOW` → 1.
  - Q10b: `--severity=LOW` → 1.
  - Q11: `--ignorefile /tmp/otro` → 1.
  - Q12: `--exit-code 0` → 1.
  - Q12b: gate sin `--exit-code` → 1.
  - Q13: `trivy-action` → 1.
  - Q13b: `aquasec/trivy` → 1.
  - Q13c: `env: TRIVY_IGNORE_UNFIXED` → 1.
  - Q14: `\` seguida de espacio (no continúa) → 0.
  - Q15: tabulador y continuación con `--vex` → 1.
  - Q16: `trivy -q image` → 1.
  - Q17: `/usr/local/bin/trivy` → 1.
  - Q18: `*.sh` del repositorio con continuación → 1.
  - Q19: YAML no válido → 1.

  Todos los negativos fallan por su regla (mensaje `::error::` comprobado). Sobre el repositorio real: "política de trivy OK; invocaciones: 3; gates: 2; excepciones: 16".
- **`qa_trivy.sh` de QA con la política nueva**: Q3-Q15 dan el resultado esperado. Q1 y Q2 dan rc 0 porque sus ficheros no contienen continuación (ver la nota de §19.13.1).
- **`dependabot_cobertura_controles.sh`**: **11/11**:
  - P0: repositorio → 0.
  - P1: `Dockerfile.dev` en un directorio listado → 0.
  - N1: falta `/infra/db` → 1.
  - N2: `FROM ${X}` → 1.
  - N3: directorio no listado → 1.
  - N4: `--platform` con variable → 1.
  - N5: `FROM $IMG` → 1.
  - N6: `from ${IMG}` → 1.
  - N7: `Containerfile` → 1.
  - N8: `app.dockerfile` → 1.
  - N9: `Containerfile.dev` con variable → 1.
- **Gate**:
  - `gate_contrato_controles.py`: **27/27**, con los nuevos N14f-i.
  - `qa_gate2.py` de QA: **20/20** (antes fallaban Q-N6, Q-N7, Q-N12 y Q-N13).
  - Esquema real generado (50 operaciones implementadas frente al contrato): 0 errores.
- **SQL**: PostgreSQL 18.6 desechable, **sin** `-v ON_ERROR_STOP=1`:
  - con `max_filas=10` → rc 3;
  - con los umbrales por defecto → rc 0.
- **Estilo y validación**:
  - `ruff check`/`format` (configuración del backend) sobre `infra/ci/`: OK.
  - `shellcheck v0.10.0` sobre los 4 `.sh`: 0 avisos.
  - `actionlint 1.7.7` sobre `ci.yaml`: 0 errores. En la primera pasada detectó un paréntesis sin cerrar en el control negativo, que se corrigió.
  - `check-jsonschema vendor.github-workflows`: OK.
- **CI**: run de GitHub Actions, SHA y URL en el `HANDOFF_ENVELOPE`.

#### 19.13.3 Riesgos
| ID | Riesgo | Sev. | Mitigación | Estado |
|---|---|---|---|---|
| RSK-OPS-033 | La política cubre workflows (todas las cadenas) y `*.sh`. Una invocación de trivy desde otro lenguaje (Python `subprocess`, Makefile) o con argumentos construidos en variables (`trivy $ARGS`) no se analiza | LOW | Hoy no existe ninguno de esos casos. La revisión de QA de cada cambio en el CI sigue siendo la barrera | ACEPTADO (documentado) |
| RSK-OPS-034 | Con `cd <dir> && trivy --ignorefile .trivyignore`, se puede usar un `.trivyignore` de otro directorio (es lo que hace el control negativo) | LOW | Solo en el paso de control negativo, que exige que trivy FALLE. Un uso así en otro sitio es visible en revisión | ACEPTADO |
| RSK-OPS-035 | PyYAML se instala en el CI con la versión fijada (6.0.3), pero sin hash | LOW | Venv efímero, sin privilegios, solo para leer YAML del propio repositorio | ACEPTADO |

#### 19.13.4 Archivos (ciclo 2)
- `infra/ci/politica_trivy.py` (nuevo)
- `infra/ci/politica_trivy.sh` (ahora envoltorio)
- `infra/ci/politica_trivy_controles.sh`
- `infra/ci/dependabot_cobertura.sh` (nuevo)
- `infra/ci/dependabot_cobertura_controles.sh` (nuevo)
- `infra/ci/gate_contrato.py`
- `infra/ci/gate_contrato_controles.py`
- `infra/ops/cache_limites_tamano.sql`
- `.github/workflows/ci.yaml`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

#### 19.13.5 Próximo agente
**Orquestador**, que debe:
1. Enviar a re-QA la rama `tkt-ops-006-mejoras` (ciclo 2/3).
2. Registrar DEC-AUTO-256 y DEC-AUTO-257.
3. Registrar RSK-OPS-033 a RSK-OPS-035.
4. Registrar la nota sobre los fixtures Q1, Q2 y Q5 del arnés de QA.

### 19.14 Ciclo 3 (QA_VERDICT FAIL, ciclo_qa 2/3): la política de trivy pasa a LISTA BLANCA

**Estado:** COMPLETADO, pendiente de re-QA (último ciclo, CLAUDE.md §0.7).

**Decisiones:**
- DEC-AUTO-915 (Orquestador).
- DEC-AUTO-258 (implementación): sustituye a la lista negra de §19.3.3 y §19.13.

**Hallazgos que corrige:**
- **QA-OPS006-03 (MEDIUM):** un flag global con valor antes del subcomando (`trivy --cache-dir /tmp/c image …`) hacía que el valor se tomara por subcomando y la invocación se descartaba.
- **OBS-C2-1:** `--scanners` sin `vuln`, `--pkg-types os`, `--db-repository` ajeno y `--skip-db-update` pasaban la política.

#### 19.14.1 Qué es una invocación
El análisis de los ciclos anteriores se mantiene:
- PyYAML con los valores resueltos.
- Shell con continuaciones: una `\` dentro de un comentario no continúa la línea.

Además, ahora cuenta como invocación **toda aparición** de la palabra `trivy` dentro de un `run:` o de un `*.sh` del repositorio:
- Da igual la ruta del binario (`/usr/local/bin/trivy`).
- Se detecta también detrás de `=`, comillas, `(` o un operador (`T=trivy;`, `python -c "…'trivy …'"`).
- No son apariciones `/tmp/trivy.tgz`, `trivy_…` ni `aquasecurity/trivy/releases`.

Hay una sola **excepción literal** (`EXCEPCIONES_LINEA`): `tar -xzf /tmp/trivy.tgz -C /usr/local/bin trivy`, la instalación del binario verificado por sha256.

En valores YAML que no son `run:` (por ejemplo, `with: script:`), `trivy <subcomando>` es error directamente.

#### 19.14.2 Lista blanca (`infra/ci/politica_trivy.py`)
| Elemento | Permitido |
|---|---|
| Subcomando | `image` (el único que usa el CI). Cualquier otro (`fs`, `rootfs`, `repo`, `config`…) → error |
| `--severity` / `-s` | Exactamente `CRITICAL,HIGH`. **Obligatorio y una sola vez** |
| `--scanners` | Exactamente `vuln` (opcional, una vez). No se admiten `secret` ni `vuln,secret` |
| `--ignorefile` | Exactamente `.trivyignore`, con la excepción del control negativo (ver más abajo) |
| `--exit-code` | Exactamente `1`. Un gate (una invocación con `--ignorefile`) lo exige |
| `--format` / `-f` | `json` o `table` |
| `--output` / `-o` | Una ruta. Admite expansiones **solo** si el valor completo va entre comillas dobles |
| `--timeout` | `\d+[smh]` |
| `--cache-dir` | Ruta literal `[\w./-]+` |
| `--quiet` / `-q`, `--no-progress`, `--show-suppressed` | Booleanos, sin `=valor` |
| Objetivo | **Exactamente 1** argumento posicional. Puede ser literal (`[a-z0-9][\w./:@-]*`) o ir entre comillas dobles empezando por `brujula/` literal (las imágenes que construye el CI) |

Reglas adicionales:
- **Cualquier otro flag es error**, en cualquier posición (antes o después del subcomando) y aunque vaya entre comillas. Por ejemplo `--ignore-unfixed`, `--skip-*`, `--pkg-types`, `--db-repository`, `--skip-db-update`, `--config`, `--vex`, `--ignore-status` o `--ignore-policy`.
- Los **argumentos no literales** (`$VAR`, `$(...)`, `` `...` ``, `${{ … }}`) son error. Hay dos únicas excepciones: el valor de `--output` y el objetivo `"brujula/…"`, ambos entre comillas dobles.
- Unas comillas o una expansión sin cerrar hacen la invocación "no analizable", y eso también es error.
- **Gate:** es cualquier invocación con `--ignorefile .trivyignore` y `--exit-code 1`. Tiene que haber al menos uno en los workflows. Para que el `.trivyignore` usado sea el de la raíz:
  - el mismo `run:` no puede contener `cd` ni `pushd`;
  - el paso, su job y el workflow no pueden fijar `working-directory`.
- **Control negativo (excepción única):** se admite `--ignorefile /tmp/trivyignore-caducado` solo si se cumplen las tres condiciones:
  - la invocación es la condición de un `if …; then`;
  - la rama `then` ejecuta `exit 1`, es decir, se exige que trivy FALLE;
  - el mismo `run:` genera ese fichero con el `sed` literal que cambia todas las caducidades a `2000-01-01`.

  Por eso el paso de CI ha vuelto a esa forma. La variante `cd /tmp/neg` del ciclo 2 queda prohibida; corresponde a B14.
- Se mantienen las reglas de los ciclos anteriores:
  - sin claves ni asignaciones `TRIVY_*` de configuración;
  - sin `trivy-action`, `setup-trivy` ni la imagen `aquasec/trivy`;
  - sin `trivy.yaml` ni `.trivyignore.yaml`;
  - `.trivyignore` solo con `CVE/GHSA exp:AAAA-MM-DD`.
- Para ampliar la lista blanca (un flag o un subcomando nuevo) hay que tocar `SUBCOMANDOS`, `FLAGS_BOOL`/`FLAGS_VALOR` y los controles. Queda en el diff y lo revisa QA.

**Cambios en `ci.yaml`:**
- El objetivo de los dos `trivy image` del escaneo pasa de `"$img"` a `"brujula/${s}:${APP_VERSION}"`, para cumplir la regla del objetivo.
- El mensaje "…trivy falla…" del control negativo se cambia a "…el escáner falla…": con la nueva regla, la palabra `trivy` dentro de un `echo` también cuenta como aparición.

#### 19.14.3 Validaciones (2026-09-28)
- **`politica_trivy_controles.sh`: 66/66.** Incluye:
  - los 39 casos anteriores. **Q14 cambia de 0 a 1:** `img \ ` no continúa la línea y pasa un segundo argumento `" "` a trivy, que la lista blanca rechaza (se espera exactamente 1 objetivo);
  - los 16 de QA, B01-B16: B13 → 0 y el resto → 1;
  - 11 nuevos:

  | Caso | Resultado |
  |---|---|
  | B17 flags globales permitidos antes del subcomando | 0 |
  | B18 `--scanners vuln,secret` | 1 |
  | B19 `trivy fs` | 1 |
  | B20 `"$img"` | 1 |
  | B21 `--output "…${s}…"` + `"brujula/${s}:…"` | 0 |
  | B22 `--output reports/$s.json` sin comillas | 1 |
  | B23 dos objetivos | 1 |
  | B24 `--ignorefile /tmp/trivyignore-caducado` fuera de su forma | 1 |
  | B25 `working-directory` en un paso con trivy | 1 |
  | B26 trivy en `with: script:` | 1 |
  | B27 comillas sin cerrar | 1 |

  Cada caso negativo falla por la regla que le toca (`::error::` comprobado).
- **Arnés de QA `run_fx.sh`:**
  - `fx3/`: B01-B16, **16/16**.
  - `fx2/`: 15 de 16. La diferencia es Q14 (esperado 0, rc 1), por el mismo motivo explicado arriba. Es un cambio intencionado al pasar a lista blanca, no un falso positivo: trivy recibiría un segundo objetivo `" "`.
- **Repositorio real**: "política de trivy OK (lista blanca); invocaciones: 3; gates: 1; excepciones: 16". No hay falsos positivos en `ci.yaml` ni en los `*.sh` (`scripts/ops/*.sh`, `infra/ci/*.sh`, `infra/db/init/*.sh`).
- **Estilo y estática:**
  - `ruff check`/`format` en `infra/ci/`: OK.
  - `shellcheck 0.10.0` en los 4 `.sh`: 0 avisos. SC2016 está desactivado en el fichero de controles, porque los casos van entre comillas simples a propósito.
  - `actionlint 1.7.7`: 0 errores.

#### 19.14.4 Riesgos
- **RSK-OPS-033:** sigue abierto solo para trivy invocado desde otro lenguaje fuera de `run:`/`*.sh` (Makefile, `.py`). Queda **mitigado** para:
  - las variables: `$T image` no se detecta como invocación, pero `T=trivy` sí aparece y falla (B10);
  - los argumentos construidos: los no literales son error;
  - `python -c` dentro de un `run:` (B16).
- **RSK-OPS-034:** CERRADO. `cd`/`pushd` y `working-directory` están prohibidos con un gate, y la excepción del control negativo está acotada.

#### 19.14.5 Archivos (ciclo 3)
- `infra/ci/politica_trivy.py` (reescrito, lista blanca)
- `infra/ci/politica_trivy_controles.sh`
- `.github/workflows/ci.yaml`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

## 21. TKT-OPS-011 — gate de contrato: excepción puntual `--err-ignore` para `request-body-type-changed` (POST /api/v1/panel/medios) (F7, soporte)

### 21.1 Estado
**COMPLETADO**, pendiente de confirmación por el CI real del PR (igual que TKT-OPS-010). Cambio mínimo y acotado de CI, en la rama `tkt-ops-011-err-ignore`. Sin despliegue, sin secretos reales y sin costes (CLAUDE.md §0.5); no activa ninguna Puerta Humana adicional porque la decisión humana que autoriza este cambio ya se tomó (DEC-AUTO-920, `audit_log.md`, 2026-09-29).

### 21.2 Objetivo
Continuación de TKT-OPS-010. Tras varias rondas de corrección del Developer sobre el panel editorial (TKT-006, ~128 operaciones, PR #24, rama `tkt-006-panel-editorial`), el paso "contrato: gate por operación + oasdiff" quedó con **un único hallazgo `error` restante**: `request-body-type-changed` en `POST /api/v1/panel/medios`. `contracts/openapi.yaml` (API-first, escrito a mano) modela el cuerpo de esa petición de forma abstracta como `type: object` (propiedad `archivos`, array de `string`/`binary`); drf-spectacular, al generar el esquema real desde la implementación de una subida `multipart/form-data` con `OpenApiTypes.BINARY`, representa el cuerpo del media type directamente como `type: string, format: binary` — así es como Django/DRF reciben el archivo en la práctica. Ninguna de las dos correcciones "precisas" es viable dentro del alcance de este ticket: remodelar el multipart en el contrato es trabajo de especificación (fuera del alcance de DevOps y del Developer de este ticket) y forzar una anotación de esquema que imite `object` sería inexacta respecto a lo que la API realmente acepta.

El Orquestador (DEC-AUTO-920) decidió: en vez de relajar el gate en general (como TKT-OPS-010 ya hizo, deliberadamente, para toda la clase de hallazgos `warning`), crear una **excepción quirúrgica y nombrada**, análoga en espíritu a `.trivyignore` (RSK-OPS-001) — puntual, documentada y de alcance mínimo, no un relajamiento general. `--fail-on ERR` (TKT-OPS-010) **no cambia**: todo hallazgo `error` que no sea exactamente este sigue bloqueando el CI.

### 21.3 Investigación del mecanismo (obligatoria antes de escribir nada)
El propio binario ya exponía, desde TKT-OPS-010, dos flags relevantes en su ayuda: `--err-ignore string` ("configuration file for ignoring errors") y `--warn-ignore string` (equivalente para `warning`). Su formato **no está documentado como YAML ni JSON**: es un archivo de texto plano, leído línea a línea. Se verificó contra dos fuentes, no una sola:

1. **Documentación oficial** (`docs/BREAKING-CHANGES.md`, sección "Ignoring Specific Breaking Changes", obtenida vía `WebFetch` del repositorio `oasdiff/oasdiff`, rama `main`): cada línea debe contener (a) el método y la ruta de la operación (el primer campo de la línea que empieza por `/`), o la palabra `components` para un cambio de componentes, y (b) una descripción del cambio. "Las partes requeridas pueden aparecer en cualquier orden, en mayúsculas o minúsculas, y la línea puede contener texto adicional" — es decir, admite comentarios/prosa alrededor, no exige que la línea sea *solo* esas dos partes.
2. **Código fuente**, en el **tag `v1.32.1`** (la versión exacta fijada en `OASDIFF_VERSION` de `ci.yaml`/`VERSIONS.md`, no `main`, para no asumir comportamiento de una versión distinta a la que corre en el CI):
   - `checker/ignore.go` (`ProcessIgnoredBackwardCompatibilityErrors`, `ignoreLinePath`): por cada línea del archivo (en minúsculas), extrae como "ruta" el primer campo separado por espacios que empieza por `/`; si no hay ninguno, la línea no puede ignorar nada (así, un archivo con solo comentarios en prosa que no contengan un campo `/algo` es inocuo).
   - `checker/api_change.go` (`ApiChange.MatchIgnore`): una línea ignora un hallazgo con nivel `ERR`/`WARN` **si y solo si**, todo en minúsculas: (a) esa "ruta" extraída es **exactamente igual** (no una subcadena, no una regex) a la ruta de la operación del hallazgo; (b) la línea **contiene** la subcadena `"<método> <ruta>"` (p. ej. `"post /api/v1/panel/medios"`); y (c) la línea **contiene** la subcadena del texto exacto, sin colorear, con el que oasdiff renderiza ese hallazgo concreto.
   - **No es una expresión regular.** El propio repositorio tiene un archivo de ejemplo, `examples/ignore-err-example.txt`, cuyo comentario de cabecera dice "Each line is a regex…" — se verificó que ese comentario **no coincide** con la implementación real leída en `checker/ignore.go`/`checker/api_change.go` en el tag fijado. Se documenta esta discrepancia explícitamente porque de haber seguido el comentario del ejemplo (en vez del código fuente) se habría escrito un archivo con una sintaxis que no funciona.
   - El texto exacto del hallazgo se generó a partir de: `checker/localizations_src/en/messages.yaml` (plantilla `request-body-type-changed: "the request's body %s changed from %s to %s"`), `checker/check_request_property_type_changed.go` (arma los argumentos con `getTypeFormatDimension`/`getBaseTypeFormat`/`getRevisionTypeFormat`) y `checker/type_format.go` (calcula esos tres argumentos a partir del esquema base y de revisión). Con base `type: object` sin `format` y revisión `type: string, format: binary`, cambian tanto el tipo como el formato ⇒ dimensión `"type/format"`; el lado base se renderiza como `` `object` `` (sin formato) y el lado revisión como `` `string/binary` ``. Los argumentos se citan entre comillas invertidas (`checker/colorize.go`, `quotedValues`). Mensaje resultante: `` the request's body `type/format` changed from `object` to `string/binary` ``.
   - Se confirmó también, leyendo `contracts/openapi.yaml` (líneas 2647-2690 y 5929-5937), que la ruta exacta es `/api/v1/panel/medios` (sin barra final) y que el `requestBody` del contrato es en efecto `type: object` en su esquema `SubidaMediosEntrada`, consistente con el hallazgo descrito por el usuario.

**Conclusión sobre el alcance:** el mecanismo real de oasdiff **sí permite** un alcance tan preciso como "ignora `request-body-type-changed` SOLO para `POST /api/v1/panel/medios`" — no es una excepción global por tipo de check. La combinación obligatoria de ruta exacta + método + texto exacto del hallazgo (§21.3, punto 2) hace que una línea ignore, como máximo, hallazgos de ese check exacto en esa operación exacta con ese cambio de tipos exacto: no existe una forma de ignorar `request-body-type-changed` de forma más amplia (por ejemplo, "en cualquier operación") con este mismo mecanismo, así que no hizo falta buscar una alternativa ni detenerse a pedir ampliar el alcance.

### 21.4 Cambios realizados
- **`infra/ci/oasdiff_err_ignore.txt`** (nuevo): archivo de configuración de `--err-ignore`, con una única línea activa:
  ```
  POST /api/v1/panel/medios the request's body `type/format` changed from `object` to `string/binary`
  ```
  Precedida de un comentario extenso (formato válido: "los archivos de configuración pueden ser de cualquier tipo de texto", `docs/BREAKING-CHANGES.md`) que documenta: la operación exacta, el tipo de cambio exacto, el motivo (multipart real vs. contrato abstracto), la referencia a TKT-006/TKT-012 y a esta decisión (DEC-AUTO-920), el formato del mecanismo (con la aclaración sobre la discrepancia del comentario de `ignore-err-example.txt`, §21.3) y el hecho de que el texto se derivó leyendo el código fuente de la versión fijada, no ejecutando el binario (§21.6).
- **`.github/workflows/ci.yaml`, job `backend`, paso "contrato: gate por operación + oasdiff"**: único cambio funcional, un flag añadido al comando ya existente:
  - Antes: `oasdiff breaking /tmp/contrato-filtrado.yaml /tmp/generado.yaml --fail-on ERR`
  - Ahora: `oasdiff breaking /tmp/contrato-filtrado.yaml /tmp/generado.yaml --fail-on ERR --err-ignore ../infra/ci/oasdiff_err_ignore.txt`
  - La ruta es relativa a `backend/` (directorio de trabajo por defecto del job, `defaults.run.working-directory: backend`), igual que `../contracts/openapi.yaml` y `../infra/ci/gate_contrato.py` en el mismo paso. Se pasa por línea de comandos (no por un archivo `.oasdiff.yaml`), así que **no** aplica la reescritura de rutas relativas de `docs/CONFIG-FILES.md` ("relative paths in these flags are resolved against the config file's directory" — eso solo afecta a `err-ignore:` declarado *dentro* de un archivo de configuración de oasdiff; "Absolute paths and paths set via CLI flag are not rewritten"). Se resuelve, por tanto, contra el directorio de trabajo del proceso en ese paso (`backend/`), igual que los demás argumentos relativos del mismo comando.
  - Se actualiza el comentario explicativo que precede al paso (nuevo punto 3, antes del bloque de "Controles N1..N12"), referenciando este archivo y esta sección.
- **`docs/05_operacion/DEVOPS_HANDOFF.md`**: esta sección, y una corrección de consistencia menor en el índice de cabecera (§0): se añadió la línea de TKT-OPS-010 (§20), que había quedado sin entrada en esa lista desde su propia entrega, y la línea de este ticket (§21). Sin cambio de contenido de §20.
- **Ningún cambio en `contracts/openapi.yaml` ni en `backend/apps/**`**, como exige el ticket. Se verificó con `git status`/`git diff --stat` tras todos los cambios: solo los tres archivos de §21.9 aparecen modificados o nuevos.

### 21.5 Versiones aprobadas
Sin cambios: `oasdiff` sigue en `1.32.1` (sha256 ya verificado en el paso, TKT-OPS-005/010). El comportamiento de `--err-ignore` se verificó específicamente contra el código fuente del tag `v1.32.1` (§21.3), no contra `main`.

### 21.6 Validaciones ejecutadas
- **VALIDADO** — sintaxis YAML de `.github/workflows/ci.yaml`: se parseó con éxito con PyYAML 6.0.3 (venv efímero local) tras el cambio. El `run:` del paso "contrato: gate por operación + oasdiff" se extrajo del árbol resultante y termina exactamente en `oasdiff breaking /tmp/contrato-filtrado.yaml /tmp/generado.yaml --fail-on ERR --err-ignore ../infra/ci/oasdiff_err_ignore.txt`, sin alterar ninguna otra línea del paso.
- **VALIDADO (simulación del algoritmo real, no ejecución del binario)** — se reprodujo en Python, línea por línea, exactamente la lógica de `ignoreLinePath` + `ApiChange.MatchIgnore` leída en el código fuente (§21.3: primer campo que empieza por `/`, comparado con igualdad exacta; `strings.Contains` para el método+ruta y para el texto del hallazgo, todo en minúsculas) contra el archivo `infra/ci/oasdiff_err_ignore.txt` real. Resultado: de las 43 líneas del archivo (comentarios incluidos), **exactamente una** cumple las tres condiciones a la vez — la línea 43, la directiva real. Una línea de comentario (línea 11) que menciona la misma ruta y el mismo método en prosa **no** cumple la tercera condición (no contiene el texto exacto del hallazgo) y por tanto no genera un falso positivo. Esto confirma que el archivo, tal como está escrito, no ignora nada por accidente además del hallazgo previsto.
- **NO VALIDADO por ejecución local** — el binario `oasdiff` no está instalado en este entorno (igual que en TKT-OPS-010: `oasdiff: command not found`, sin resultado en una búsqueda de archivo por todo el sistema), así que no se pudo ejecutar `oasdiff breaking --err-ignore infra/ci/oasdiff_err_ignore.txt` contra el esquema real generado por drf-spectacular para confirmar que (a) el hallazgo de multipart efectivamente deja de bloquear y (b) el texto exacto que renderiza el binario coincide, carácter por carácter (incluida la puntuación de `request's`, las comillas invertidas y la barra de `type/format`/`string/binary`), con lo escrito en el archivo. El texto se derivó leyendo la plantilla de mensaje y el código que arma sus argumentos en el tag `v1.32.1` (§21.3), no ejecutándolo. Si el texto real difiriera en un solo carácter, la línea no ignoraría el hallazgo y el CI seguiría fallando (fail-closed: un archivo de `--err-ignore` que no coincide con nada no oculta ningún otro hallazgo, y `--fail-on ERR` seguiría exigiendo cero errores) — no hay riesgo de que un desajuste en el texto ignore de más.
- **NO VALIDADO** — `actionlint` y `shellcheck`: no están disponibles en este entorno local en el momento de este cambio (`command not found`, igual que en TKT-OPS-010). No se afirma una validación de esquema de GitHub Actions ni de estilo de shell que no se ejecutó.
- **NO APLICABLE** — `docker compose config`: este cambio no toca ningún `compose*.yaml`.
- **PENDIENTE (Puerta de confirmación pedida explícitamente por el Orquestador, igual que en TKT-OPS-010)** — ejecución real del CI del PR de este ticket: confirmar (a) que el hallazgo `request-body-type-changed` de `POST /api/v1/panel/medios` deja de bloquear el paso de contrato, y (b) que ningún otro hallazgo se ve afectado por error (por ejemplo, que el archivo no ignore de más por un fallo de sintaxis o de coincidencia parcial). El PR de TKT-006 (panel editorial) es el que tiene la superficie de API real donde este cambio tiene efecto observable; si TKT-OPS-011 se integra primero en `main`, TKT-006 debe hacer rebase/merge de `main` para heredar la excepción antes de su siguiente ejecución de CI.

### 21.7 Seguridad
- Sin secretos, sin cambios de superficie de red, de imágenes ni de contenedores.
- **Riesgo aceptado por el usuario** (DEC-AUTO-920, `audit_log.md`, 2026-09-29): a partir de este cambio, un hallazgo `error` concreto —posible ruptura real de compatibilidad según la clasificación de oasdiff— deja de bloquear el CI para esa única operación. Se acepta porque el hallazgo es un falso positivo respecto a la intención real: el contrato declara el cuerpo como `object` de forma deliberadamente abstracta para una subida de archivos, y la representación de drf-spectacular (`string`/`binary`) es la forma correcta y estándar de documentar un `multipart/form-data` con OpenAPI — no una ruptura de compatibilidad real para los clientes, que ya deben enviar el archivo como binario en el multipart en ambos casos.
- Lo que sigue bloqueando el CI sin cambios: todo hallazgo `error` que no sea exactamente este (ruta exacta + texto exacto), el gate `gate_contrato.py` (N1-N14, sin cambios) y los 608 `warning` de TKT-OPS-010 siguen sin bloquear (deuda técnica, TKT-012, sin tocar).
- Superficie de la excepción: **una** línea activa, en **un** archivo nuevo dentro de `infra/ci/**` (visible en cualquier revisión de PR), no un flag global ni una supresión por tipo de check.

### 21.8 Riesgos / pendientes
| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-038 | El texto exacto del hallazgo en `infra/ci/oasdiff_err_ignore.txt` se derivó del código fuente (tag v1.32.1), no de una ejecución real del binario; si difiriera en un solo carácter, la excepción no ignoraría nada y el CI seguiría fallando (fail-closed, sin riesgo de ignorar de más, pero sí de no lograr el objetivo del ticket) | LOW (fail-closed) | Confirmar con el CI real del PR (§21.6); si no coincide, ajustar el texto de la línea con el mensaje real que reporte oasdiff en ese run | ABIERTO (pendiente de confirmación CI) |
| RSK-OPS-039 | La deuda de modelado del contrato para `multipart/form-data` (el contrato usa `object` en vez de una representación más fiel del binario) sigue sin resolverse; esta excepción la documenta pero no la corrige | LOW | TKT-012 (ya existente, deuda técnica de fidelidad del contrato, TKT-OPS-010 §20.10 RSK-OPS-035) puede ampliar su alcance para cubrir también este caso | ABIERTO (ticket existente) |
| RSK-OPS-036 | `actionlint`/`shellcheck` no disponibles en este entorno local (heredado de TKT-OPS-010) | LOW | Sin cambios respecto a TKT-OPS-010: instalar antes del próximo cambio de `.github/workflows/**`, o confiar en el CI del PR | ABIERTO |

### 21.9 Archivos modificados
- `infra/ci/oasdiff_err_ignore.txt` (nuevo)
- `.github/workflows/ci.yaml`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 21.10 Próximo agente
**Orquestador**, que debe:
1. Confirmar en el CI real del PR de este ticket que el paso de contrato ya no falla por `request-body-type-changed` en `POST /api/v1/panel/medios`, y que ningún otro hallazgo se ve afectado (§21.6, punto PENDIENTE).
2. Si TKT-006 (panel editorial) sigue abierto, asegurarse de que su rama incorpore este cambio (rebase/merge de `main` tras integrar este ticket) antes de su siguiente ejecución de CI o de pasar a QA.
3. Registrar DEC-AUTO-920 (ya referenciada aquí como decisión previa del Orquestador) y RSK-OPS-038/039 en `audit_log.md`/`kanban.md`.
4. Mantener TKT-012 como seguimiento de la deuda de modelado del contrato (ahora también para el caso multipart, RSK-OPS-039).

## 22. TKT-OPS-012 — línea de `infra/scheduler/crontab` para `vigilar_cache_limites` (cierra RSK-OPS-032) (F7, soporte)

### 22.1 Estado
**COMPLETADO.** Cambio mínimo y acotado de una sola línea de infraestructura (más comentario descriptivo), en la rama `tkt-ops-012-crontab-cache-limites`. Sin despliegue, sin secretos reales y sin costes (CLAUDE.md §0.5).

### 22.2 Objetivo
TKT-011 (Developer, DONE, PR #31 integrado en `main` @ `8babd75`) entregó el comando de gestión `vigilar_cache_limites` (alerta de tamaño de `app.cache_limites`, RSK-QA004-02) con QA_VERDICT PASS. La propuesta de §19.3.6 quedaba pendiente de un paso final que sí es de DevOps: añadir la línea al planificador (`infra/scheduler/crontab`, RSK-OPS-032). Este ticket cierra ese pendiente.

### 22.3 Cambios realizados
- **`infra/scheduler/crontab`**: una línea nueva, siguiendo el mismo estilo que las 6 líneas existentes (comentario descriptivo en mayúsculas con nombre de tarea + justificación, luego la línea cron):
  ```
  # Cada 15 min: alerta de tamaño de app.cache_limites (VIGILANCIA_CACHE_LIMITES, RSK-QA004-02/RSK-OPS-032).
  # Cadencia más alta que las tareas diarias porque cache_limites es una tabla UNLOGGED efímera de
  # throttling (TTL <= 1h, DEVOPS_HANDOFF.md §19.3.6): un umbral superado debe detectarse dentro de esa
  # misma hora, no al día siguiente.
  */15 * * * * python manage.py vigilar_cache_limites
  ```
  - Frecuencia y comando exactos según la especificación de §19.3.6 (sin inventar umbrales ni cadencia distintos): `*/15 * * * * python manage.py vigilar_cache_limites`.
  - El comando ya implementa `pg_try_advisory_lock` y registro en `ops_ejecucion_tarea` (mismo patrón que el resto de `TRABAJOS`, verificado por QA de TKT-011): no requiere ningún cambio adicional en el crontab (sin `flock` externo, igual que las demás líneas).
  - Ninguna otra línea del archivo se tocó.
- **`docs/05_operacion/DEVOPS_HANDOFF.md`**: línea de índice de cabecera (§0) para este ticket; fila `RSK-OPS-032` de §19.10 pasa de "ABIERTO (ticket)" a "CERRADO"; fila `RSK-QA004-02` de §19.10 se actualiza a "MITIGADO (programado)" (antes "MITIGADO (manual)"); esta sección §22.
- **Ningún archivo de `backend/apps/ops/**` tocado** (eso ya lo hizo el Developer en TKT-011, DONE). Verificado con `git status`/`git diff --stat`: solo los dos archivos de §22.9 aparecen modificados.

### 22.4 Versiones aprobadas
Sin cambios de versión. Se reconstruyó la imagen real `brujula/scheduler:0.0.0-dev-brujula` (`infra/docker/backend.Dockerfile`, target `scheduler`) para la validación de §22.6: mismo `supercronic` `v0.2.49` ya fijado por sha256 (§4), sin cambios.

### 22.5 Infraestructura
Sin cambios de topología, redes, imágenes, healthchecks ni recursos. El servicio `scheduler` de `compose.yaml` (perfil `ops`) ya montaba `infra/scheduler/crontab` en la imagen (`COPY --from=infra ... scheduler/crontab /etc/brujula/crontab`); esta línea nueva viaja con la siguiente reconstrucción de esa imagen, sin cambios en `compose.yaml` ni en el Dockerfile.

### 22.6 Validaciones ejecutadas (2026-09-29, Docker Engine 29.6.1, Compose v5.2.0)
- **Precondición confirmada por lectura directa** (no solo por el kanban): `backend/apps/ops/management/commands/vigilar_cache_limites.py` existe en `main` (heredado del merge de TKT-011 @ `8babd75`) y define `nombre = "vigilar_cache_limites"`.
- **VALIDADO — sintaxis real del crontab con el binario real**: como el formato lo consume `supercronic` (comentario de cabecera del propio archivo) y no hay binario `supercronic` instalado sueltamente en este entorno local (Windows, no es una de las herramientas de `VERSIONS.md` §"Toolchain local"), se optó por construir la imagen real del servicio `scheduler` (`docker compose build scheduler`, éxito, incluye la descarga y verificación por sha256 de `supercronic v0.2.49` y el `COPY` del `infra/scheduler/crontab` real, las 12 líneas con la nueva) y ejecutar el binario real dentro del contenedor:
  ```
  MSYS_NO_PATHCONV=1 docker run --rm --entrypoint supercronic brujula/scheduler:0.0.0-dev-brujula -test /etc/brujula/crontab
  ```
  Resultado: `level=info msg="read crontab: /etc/brujula/crontab"` seguido de `level=info msg="crontab is valid"`, código de salida 0. Esto es una validación real del archivo tal como quedará en la imagen de producción del scheduler (no una aproximación ni una lectura manual), con el mismo binario y la misma ruta que usa `CMD ["supercronic", "-json", "-passthrough-logs", "/etc/brujula/crontab"]` en tiempo de ejecución.
  - Nota de entorno: la primera invocación sin `MSYS_NO_PATHCONV=1` falló (`open C:/Program Files/Git/etc/brujula/crontab: no such file or directory`) porque Git Bash/MSYS reescribe la ruta absoluta del contenedor como si fuera una ruta de Windows — el mismo comportamiento ya documentado en §5.2 para otros comandos con rutas absolutas. No es un defecto del crontab; se repitió con la variable de entorno correcta y funcionó.
- **NO VALIDADO** — ejecución real de `vigilar_cache_limites` disparada por `supercronic` en tiempo (esperar a que pase un intervalo de 15 min con BD real conectada): fuera de alcance de este cambio de una línea; el comportamiento en tiempo de ejecución del comando en sí ya lo validó QA de forma independiente en TKT-011 (reproducción con datos reales bajo el rol `app_rw` real). Este ticket solo valida que el planificador **parsea y acepta** la línea nueva, no una ejecución end-to-end del propio comando vía cron.
- **VALIDADO** — `git status`/`git diff --stat` tras todos los cambios: solo `infra/scheduler/crontab` y `docs/05_operacion/DEVOPS_HANDOFF.md` aparecen modificados; nada bajo `backend/`.
- **NO APLICABLE** — `docker compose config`: este cambio no toca ningún `compose*.yaml`.
- Limpieza: no se eliminó la imagen `brujula/scheduler:0.0.0-dev-brujula` construida para la validación (es la misma etiqueta de desarrollo que ya usan otros tickets/compose local de este proyecto, RSK-OPS-010; reconstruir a partir de la misma base no tiene coste ni efecto colateral). Se generó un `.env` local con `scripts/ops/init-env.sh` (nunca sobrescribe uno existente; gitignored, no llega al repositorio) porque `docker compose build` lo exige.

### 22.7 Seguridad
- Sin secretos: solo se añadió un comentario y una línea de comando ya usada por el resto del crontab (sin argumentos, sin credenciales).
- Sin cambios de superficie de red, imágenes ni contenedores. El comando se ejecuta con el rol `app_rw` (nunca `app_migrator`), igual que el resto de tareas del planificador (comentario de cabecera del propio archivo, sin cambios).
- Sin cambios de privilegios: la imagen `scheduler` sigue ejecutándose como uid 10001 (sin root), y `supercronic` no requiere ningún cambio de configuración para la tarea nueva.

### 22.8 Riesgos / pendientes
| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-032 | La alerta de `cache_limites` solo se podía ejecutar a mano hasta que existiera el comando `vigilar_cache_limites` (Developer) | LOW | TKT-011 (Developer, DONE) entregó el comando; esta línea de crontab lo programa cada 15 min | CERRADO |

Sin riesgos nuevos: es un cambio de una línea sobre un mecanismo (`supercronic` + `ops_ejecucion_tarea` + `pg_try_advisory_lock`) ya validado por 6 tareas previas y por QA de TKT-011.

### 22.9 Archivos modificados
- `infra/scheduler/crontab`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 22.10 Próximo agente
**Orquestador**, que debe:
1. Registrar el cierre de RSK-OPS-032 y la actualización de RSK-QA004-02 en `audit_log.md`/`kanban.md`.
2. Marcar TKT-OPS-012 DONE tras confirmar el CI real del PR (build de la imagen `scheduler` y cualquier smoke que la ejercite).
3. Sin tickets dependientes conocidos: `vigilar_cache_limites` ya corre programada; el runbook de §19.3.6 sigue vigente sin cambios.

## 23. TKT-OPS-016: limitador de borde con zona propia para los assets estáticos y X-Robots-Tag del panel (F7, soporte; condición de F9)

### 23.1 Estado
**COMPLETADO** en local, en la rama `tkt-ops-016-limitador-estaticos`. Sin despliegue, sin secretos reales y sin costes (CLAUDE.md §0.5). La decisión, las alternativas y los riesgos están en **ADR-OPS-001**.

### 23.2 Objetivo
QA de TKT-018 (F-3, HIGH) midió que 2-3 visitantes en frío tras una misma IP (NAT, CGNAT, oficina) agotan `por_ip` (20 r/s, burst 60). El 429 cae sobre los chunks JS lazy y el router de Angular no completa la navegación. El problema no se puede corregir desde el frontend. Objetivos:
- sacar los assets estáticos del cupo de `/api/**` y del HTML SSR, sin debilitar esos dos;
- que un asset inexistente no se convierta en un render SSR ilimitado.

Ampliación (DEC-AUTO-929): `X-Robots-Tag: noindex, nofollow` en las respuestas de `/panel/**` (RULE-029).

### 23.3 Cambios realizados (solo `infra/proxy/nginx.conf`)
- **Zona `estaticos`**: `limit_req_zone $binary_remote_addr zone=estaticos:10m rate=50r/s`, con `limit_req zone=estaticos burst=300 nodelay` en:
  - la nueva location regex de assets: `^/(?:[A-Za-z0-9_-]+\.(?:js|mjs|css)|fonts/[A-Za-z0-9_-]+\.woff2|favicon\.ico)$`;
  - `location /media/publico/`.
- **Location de assets**:
  - envía al SSR `Host: estaticos.invalid` (y `X-Forwarded-Host`, retirado en TKT-OPS-019, §25). `express.static` sirve el archivo si existe. Si no existe, Angular rechaza el Host con 400 sin renderizar;
  - `proxy_intercept_errors on`: 400/404 → `404 no_encontrado` (Problem Details), 403/429/5xx → los del catálogo. Los `error_page` se redefinen en la location;
  - cabeceras idénticas a las de antes: CSP, nosniff, COOP/CORP, XFO, Referrer y Permissions-Policy vía `security-headers-html.conf`, y `Cache-Control $cache_control_ssr`, que conserva el `immutable`;
  - `limit_except GET HEAD`.
- **Zonas resultantes**:

  | Zona | Ritmo | Burst | Ámbito |
  |---|---|---|---|
  | `por_ip` | 20 r/s | 60 | `/api/**`, HTML del SSR y cualquier otra ruta (incluidas `/destinos/x.js`, `/x.html` y `/api/…/x.js`) |
  | `salud` | 50 r/s | 200 | `/health/live\|ready` (sin cambios) |
  | `estaticos` | 50 r/s | 300 | assets en la raíz, `/fonts/*.woff2`, `/favicon.ico` y `/media/publico/**` (nuevo) |
- **Log**: campo `ruta_pedida` en `brujula_json`. Es la ruta original sin query string, para saber qué recurso recibió un 429. Antes los 429 se registraban como `/_errores_proxy/429`.
- **`X-Robots-Tag`**: `map $uri $x_robots_borde` vale `"noindex, nofollow"` para `^/panel(/|$)` y está vacío en el resto, así que no se emite. Se añade con `add_header ... always` en `location /`, la misma location que ya define las cabeceras de seguridad, por lo que no se rompe la herencia.

### 23.4 Versiones aprobadas
Sin cambios. Proxy `nginxinc/nginx-unprivileged:1.30.5-alpine@sha256:4714e0b1…`, Angular/`@angular/ssr` 22.2.0 y Express 5.2.1.

### 23.5 Infraestructura
Sin cambios de topología, redes, volúmenes, healthchecks, recursos ni `compose*.yaml`.

**Requisito operativo nuevo (RSK-OPS-040):** `NG_ALLOWED_HOSTS` nunca debe contener `*` ni `*.invalid`. Si lo hiciera, un asset inexistente volvería a renderizar en el SSR, aunque acotado por la zona `estaticos`.

### 23.6 Dependencias
Ninguna.

### 23.7 Variables de entorno
Sin variables nuevas. `NG_ALLOWED_HOSTS` sigue igual (por defecto `localhost,127.0.0.1`), con la restricción de §23.5.

### 23.8 Validaciones ejecutadas
Fecha: 2026-09-30. Entorno: Docker Engine 29.6.1 y Compose v5.2.0. Proyecto `-p brujula-ops016` con `APP_NET_PREFIX=10.231.66` y `PROXY_HOST_PORT=18166`. Semilla real (`cargar_semilla`: 98 entidades, 68 publicadas). Chromium de Playwright 1.63.0. Los scripts de medición estaban en el scratchpad, fuera del repositorio.

**Escenario.** N contextos Chromium fríos y simultáneos (misma IP) abren Inicio y a los 300 ms hacen clic en un enlace de la cabecera (rotando entre /destinos, /guias, /itinerarios, /colecciones, /cuando-ir y /tipos-de-aventura). Cada serie tiene 5 rondas con 3 s de reposo entre rondas.

**Criterio de navegación rota.** La URL no llega al destino en 15 s, o aparece "Failed to fetch dynamically imported module". Los 429 se cuentan en el navegador y en el log JSON del proxy.

- **VALIDADO — AC_OPS016_01:**

  | Serie | Antes (`main` @ 1bf5e94) | Después |
  |---|---|---|
  | N=2 s1 | 1/10 rotas, 18 × 429 | 0/10 rotas, 0 × 429 (proxy: 0) |
  | N=2 s2 | 0/10 rotas, 17 × 429 | 0/10 rotas, 0 × 429 (proxy: 0) |
  | N=3 s1 | 15/15 rotas, 112 × 429 | 0/15 rotas, 0 × 429 (proxy: 0) |
  | N=3 s2 | 13/15 rotas, 107 × 429 | 0/15 rotas, 0 × 429 (proxy: 0) |
  | N=5 y N=8 (holgura) | — | 0/15 y 0/24 rotas, 0 × 429 |

  Antes, 252 de los 254 × 429 caían en `chunk-*.js` y `/media/publico/**` (los otros 2, en `/api`).
- **VALIDADO — AC_OPS016_02** (ráfagas concurrentes desde una IP):
  - 200 a `/api/v1/publico/destinos`: 61 × 200 y 139 × 429.
  - 200 a `/`: 62 × 200 y 138 × 429.
  - 200 a `/destinos`: 61 × 200 y 139 × 429.
  - Los tres casos coinciden con `por_ip` (burst 60 + reposición).
  - Separación de cupos: 250 assets y 50 `/api` simultáneos dan 300 × 200.
- **VALIDADO — AC_OPS016_03:**
  - 200 assets inexistentes con nombre único: 200 × 404 Problem Details en unos 5 ms. 400 inexistentes: 307 × 404 y 93 × 429 (la zona `estaticos` también los limita).
  - En el log del SSR: 507 rechazos `Header "host" with value "estaticos.invalid" is not allowed` y **0 renders** (0 `error_ssr`). Antes, `/no-existe-123.js` devolvía el HTML 404 renderizado por Angular.
  - Rutas con aspecto de asset fuera del patrón (`/api/v1/publico/x.js`, `/destinos/x.js`, `/x.html`, 150 de cada una): 61-62 × 404 y 88-89 × 429. Siguen en `por_ip` y el backend nunca recibe nada de la location de assets.
- **VALIDADO — AC_OPS016_04:**
  - `nginx -t` OK en el contenedor; `docker compose config -q` OK (base y base + `compose.ci.yaml`); los 4 servicios healthy y `/health/ready` 200.
  - Cabeceras de `/main-*.js` idénticas a las de antes: `Cache-Control: public, max-age=31536000, immutable`, CSP con nonce, nosniff, Referrer, Permissions, COOP, CORP y XFO.
  - gzip activo (`Content-Encoding: gzip`), `If-None-Match` → 304, `POST /main-*.js` → 403 Problem Details.
  - Medios: `image/avif`, `immutable`, CSP `sandbox` y nosniff, igual que antes. Un medio inexistente da 404 Problem Details.
- **VALIDADO — AC_OPS016_06:**
  - `curl -I` a `/panel`, `/panel/` y `/panel/acceso` devuelve `X-Robots-Tag: noindex, nofollow` junto a CSP, nosniff, Referrer, Permissions, COOP, CORP, XFO y `Cache-Control: no-store`.
  - `/`, `/destinos`, `/main-*.js` y `/panelx` no la devuelven.
  - El panel aún no está en `main`: el SSR responde hoy 404 HTML en `/panel/**`, y la cabecera se aplica igualmente (`always`).
- **AC_OPS016_05:** este apartado y ADR-OPS-001.
- **NOT_RUN:** la ejecución en GitHub Actions se registra en §23.13 tras abrir el PR. Hoy el smoke de CI no cubre la zona `estaticos` ni AC_OPS016_03 (ver §23.10).

### 23.9 Seguridad
- `/api/**` y el HTML del SSR conservan exactamente la política `por_ip` (DEC-AUTO-111/214).
- La superficie nueva queda acotada:
  - los assets tienen un cupo propio de 50 r/s y burst 300 por IP;
  - un asset inexistente no renderiza;
  - las rutas fuera del patrón siguen en `por_ip`.
- El log no contiene query strings: `ruta_pedida` corta en `?` (THREAT-020, REQ-057).
- Sin cambios de privilegios: uid 101, raíz de solo lectura.

### 23.10 Riesgos / pendientes
| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-040 | `NG_ALLOWED_HOSTS` con `*` reabre el render de assets inexistentes (acotado por `estaticos`) | MEDIUM (si se configura mal) | Requisito de §23.5. Recomendado: ticket de CI con un smoke que exija que `/no-existe-<n>.js` dé 404 `application/problem+json` y que una ráfaga de 120 assets no dé 429 (`.github/workflows` queda fuera del alcance de este ticket) | ABIERTO (ticket CI) |
| RSK-OPS-041 | Cada asset inexistente escribe líneas de error en el log del SSR (posible inflado del log). Corrección TKT-OPS-019: medido, eran **8 líneas** por petición, no ~3; tras §25 son **4** | LOW | json-file de 10 MB × 5. Filtrar o muestrear en los logs centralizados de producción | ACEPTADO |
| RSK-OPS-042 | Ancho de banda por IP en los assets (50 r/s) | LOW / MEDIUM (prod) | CDN o caché de borde en el ADR de producción (F9), junto con RSK-OPS-022 | ABIERTO (F9) |
| RSK-OPS-043 | Más de unas 8 cargas en frío por segundo tras una misma IP aún podrían ver 429 en assets | LOW | Recalibrar con métricas reales; en producción, CDN | ACEPTADO |
| RSK-OPS-022 | Sin `real_ip` tras un balanceador o CDN, todas las zonas se vuelven globales | MEDIUM (prod) | Sin cambios: ADR de producción (F9) | ABIERTO (F9) |

### 23.11 Archivos modificados
- `infra/proxy/nginx.conf`
- `docs/adr/ADR-OPS-001.md` (nuevo)
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 23.12 Próximo agente
**Orquestador.** Pasos:
1. Registrar en `audit_log.md` y `kanban.md` la decisión de ADR-OPS-001 y RSK-OPS-040 a RSK-OPS-043. Los DEC-AUTO los numera el Orquestador.
2. Lanzar QA de TKT-OPS-016: escenario de AC_OPS016_01 con el mismo método, ráfagas de AC_02/03 y cabeceras de AC_04/06.
3. Abrir el ticket de CI del smoke de RSK-OPS-040.
4. Integrar tras QA PASS y CI verde.

### 23.13 Validación en GitHub Actions (PR #38)
- **Ejecución 36803048434** (commit 7218b10):
  - `detectar código`, `infraestructura`, `frontend`: PASS.
  - `backend`: GitHub canceló el paso `pytest` a los ~6 min con `##[error]The operation was canceled.` (01:58:32Z). No fue `timeout-minutes` (30) ni un relevo por concurrencia (no hubo otro push en la rama).
  - Desde entonces la ejecución quedó **huérfana** en `in_progress`: `gh run cancel`, `force-cancel` y `rerun` fueron rechazados por la API (409 / "already running").
  - La rama no toca `backend/` (en `main` @ 1bf5e94 el mismo job pasó en 9 min).
  - Se relanza con este commit de documentación: la concurrencia `ci-${{ github.ref }}` con `cancel-in-progress` sustituye la ejecución huérfana.
- Resultado de la nueva ejecución: en el HANDOFF_ENVELOPE de la entrega al Orquestador.

## 24. TKT-OPS-017: CVE-2026-103111 (HIGH) en `libpcre2-8-0` de las imágenes Debian (F7, soporte; desbloquea el CI)

> Numeración: §23 queda para TKT-OPS-016 (PR #38, abierto en paralelo). Si este PR se integra antes, el PR #38 tendrá que reubicar su línea de índice y su §23 tras rebase (solo conflicto textual de "añadido al final"; mantener ambas secciones).

### 24.1 Estado
COMPLETADO en local (AC_OPS017_01 local, AC_OPS017_02 y AC_OPS017_03). El CI real del PR se reporta en el HANDOFF_ENVELOPE al Orquestador.

### 24.2 Objetivo
En la ejecución de CI 36806399271 (PR #38) el paso `image scan` del job `build + trivy + SBOM` falla con CVE-2026-103111 HIGH en `libpcre2-8-0` 10.46-1~deb13u2 (corregida en 10.46-1~deb13u3). La corrección existe, por lo que aceptar el CVE en `.trivyignore` no procede (sería además Puerta Humana, CLAUDE.md §0.5): hay que eliminarlo de las imágenes con el cambio mínimo y reproducible.

### 24.3 Diagnóstico
- Imágenes afectadas (trivy 0.74.0, BD de vulnerabilidades del 2026-10-01 01:24 UTC): `backend`, `scheduler` (deriva del `runtime` de backend), `frontend`, `backup`, `db`. `proxy` (alpine) = 0. El único paquete PCRE presente en las bases es `libpcre2-8-0` (`dpkg-query -W 'libpcre*'` en las bases fijadas por digest).
- Origen por imagen (todas Debian 13 trixie, fijadas por tag + digest):

  | Imagen | Base (etapa final) | Digest fijado |
  |---|---|---|
  | backend / scheduler | `python:3.13.15-slim-trixie` (etapa `python-sin-pip`, aplanada con `FROM scratch`) | `sha256:8d9d0b8b…3ddf0` |
  | frontend | `node:24.21.0-trixie-slim` (etapa `node-sin-pm`, aplanada) | `sha256:8ec5d755…0cffe` |
  | db | `postgres:18.6-trixie` | `sha256:5a5a84b1…a9722` |
  | backup | `debian:13.7-slim` | `sha256:a99cfc51…1b20a` |

- ¿Basta con subir el digest? NO (comprobado el 2026-10-01 con `docker buildx imagetools inspect` y `dpkg-query` dentro de las imágenes):
  - `node:24.21.0-trixie-slim`, `postgres:18.6-trixie` y `debian:13.7-slim`: el digest publicado del tag es el MISMO que el fijado (sigue con deb13u2).
  - `python:3.13.15-slim-trixie`: hay un digest nuevo (`sha256:7c61056e…cd3b`), pero también trae `libpcre2-8-0` 10.46-1~deb13u2 (y `libssl3t64` deb13u2).
  - Rama de Dependabot `dependabot/docker/infra/docker/python-3.14.7-slim-trixie`: `python:3.14.7-slim-trixie@sha256:51dafde8…5b3d` también trae deb13u2 y además cambia el runtime de Python 3.13 a 3.14 (dependencia de producto, Skill_Backend; rutas `python3.13` del Dockerfile y `PYTHON_VERSION` del CI). No sirve para este ticket; no se integra (sin merge de PR de Dependabot).
- `10.46-1~deb13u3` está publicado en `trixie-security/main` (`apt-cache madison libpcre2-8-0` sobre `debian:13.7-slim` fijada).

### 24.4 Cambios realizados (mismo patrón ya aprobado en TKT-OPS-014/015 para openssl)
Se añade `libpcre2-8-0=10.46-1~deb13u3` (versión exacta, sin rangos) a la actualización de paquetes que ya existía en cada Dockerfile, más un control en el build que falla si la versión instalada no es exactamente la esperada:
- `infra/docker/backend.Dockerfile` (etapa `python-sin-pip`, antes del aplanado; llega a `runtime` y a `scheduler`): `apt-get install -y --only-upgrade … libpcre2-8-0=10.46-1~deb13u3`.
- `infra/docker/frontend.Dockerfile` (etapa `node-sin-pm`, antes del aplanado): ídem.
- `infra/db/Dockerfile`: `apt-get download … libpcre2-8-0=10.46-1~deb13u3` + `dpkg --force-depends -i … libpcre2-8-0_10.46-1~deb13u3_amd64.deb` (mismo motivo que openssl: el purge de perl con `--force-depends` impide `apt-get install`).
- `infra/backup/Dockerfile`: `ARG PCRE2_DEB_VERSION=10.46-1~deb13u3` y `"libpcre2-8-0=${PCRE2_DEB_VERSION}"` en el `apt-get install` fijado existente.

Sin cambios de tag ni digest de ninguna imagen base, ni de `.trivyignore`, ni del workflow, ni de `infra/proxy/**`.

### 24.5 Versiones aprobadas
| Componente | Versión | Imágenes | Estado | Evidencia |
|---|---|---|---|---|
| libpcre2-8-0 | 10.46-1~deb13u3 (trixie-security) | backend, scheduler, frontend, backup, db | APROBADO | `dpkg-query -W libpcre2-8-0` en las 5 imágenes + control del build + trivy 0 |
| Imágenes base | sin cambios (mismos tag + digest) | todas | APROBADO | diff |

### 24.6 Infraestructura / dependencias / variables de entorno
Sin cambios de compose, redes, healthchecks, variables ni lockfiles.

### 24.7 Validaciones ejecutadas (2026-10-01, Docker Engine 29.6.1, Compose v5.2.0, trivy 0.74.0, proyecto compose `t017`)
- ANTES (main @ 7ee17b5, imágenes `t017-antes`), misma política del CI (`--scanners vuln --severity CRITICAL,HIGH --ignorefile .trivyignore --exit-code 1`): backend, frontend, scheduler, backup y db -> exit 1, 1 hallazgo no suprimido cada una (CVE-2026-103111 libpcre2-8-0 10.46-1~deb13u2 -> 10.46-1~deb13u3, HIGH); proxy -> exit 0.
- DESPUÉS (imágenes `t017-despues`, `docker compose --profile ops build --pull`): las 6 imágenes exit 0, 0 CRITICAL/HIGH no suprimidos. VALIDADO.
- `docker compose config --quiet` en las 4 variantes (base, `--profile ops`, `+compose.ci.yaml`, `+compose.debug.yaml`): OK.
- `docker compose up -d --no-build --wait`: db, backend, frontend y proxy healthy; init-volumes y migrate Exited (0).
- Smoke por el proxy: `/` 200 text/html, `/destinos` 200 text/html, `/api/v1/publico/destinos` 200 application/json, `/health/live` 200, `/health/ready` 200.
- `supercronic -test` del crontab de `scheduler` y de `backup`: "crontab is valid". `pg_dump --version` 18.6 en backup; `grep -P` (enlaza libpcre2) funciona en backup.
- Suites de tests de backend/frontend: no afectadas (solo cambian Dockerfiles); NOT_RUN en local, las ejecuta el CI del PR.
- `docker compose --profile ops down -v` del proyecto `t017` al terminar.

### 24.8 Seguridad
- CVE-2026-103111 (HIGH, `libpcre2-8-0`) eliminado de las 5 imágenes Debian con la corrección oficial de Debian. `.trivyignore` intacto: las excepciones vigentes (RSK-OPS-001, exp:2026-10-26) siguen siendo solo CVE sin parche.
- HALLAZGO operativo: la BD de trivy de la caché local compartida (UpdatedAt 2026-09-30 07:10 UTC) aún no contenía CVE-2026-103111 y daba 0 hallazgos con las imágenes vulnerables (falso negativo). Se reprodujo con una BD recién descargada (2026-10-01 01:24 UTC) en una caché privada.

### 24.9 Riesgos / pendientes
- RSK-OPS-044 (MEDIUM, nuevo): versiones de paquetes Debian fijadas a mano en los Dockerfiles (openssl deb13u3 desde TKT-OPS-014/015, ahora pcre2 deb13u3). Cuando la imagen base publique un digest con estas versiones o superiores, la actualización queda redundante; si Debian retira la versión de `trixie-security` tras un nuevo DSA, el build fallará (fail-fast, deseado) y habrá que subirla. Mitigación: al aceptar un PR de Dependabot de imagen base, revisar si las líneas `--only-upgrade`/`apt-get download` siguen siendo necesarias.
- RSK-OPS-045 (LOW, nuevo): falso negativo de trivy en local por BD desactualizada (§24.8). Recomendación: en los escaneos locales de evidencia, forzar BD fresca (`trivy image --download-db-only` en una `--cache-dir` propia) y registrar el `UpdatedAt` de la BD junto al resultado.
- `infra/db/Dockerfile` sigue con nombres `_amd64.deb` fijos (preexistente desde TKT-OPS-014): build solo amd64.
- Conflicto textual previsible con el PR #38 en este documento (nota inicial de §24).

### 24.10 Archivos modificados
- `infra/docker/backend.Dockerfile`
- `infra/docker/frontend.Dockerfile`
- `infra/db/Dockerfile`
- `infra/backup/Dockerfile`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 24.11 Próximo agente
**Orquestador**: confirmar el CI real del PR, integrarlo (sin editar contenido) y relanzar el CI del PR #38 tras rebase sobre `main` para que su job de imágenes pase a verde. Registrar RSK-OPS-044/045 en `audit_log.md`.

## 25. TKT-OPS-019: assets sin query hacia el SSR, sin `X-Forwarded-*` redundantes y RSK-OPS-041 medido (F7, soporte, LOW)

### 25.1 Estado
**COMPLETADO** en local, en la rama `tkt-ops-019-assets-sin-query`. Sin despliegue, sin secretos reales y sin costes (CLAUDE.md §0.5). La decisión está en **ADR-OPS-001**, punto 7.

### 25.2 Objetivo
Corregir los hallazgos de la QA de TKT-OPS-016:
- **F-1 (LOW)**: un asset inexistente con query (p. ej. `/no-existe.js?secreto=1`) dejaba la URL completa, query incluida, en el stdout del SSR (`ERROR: Bad Request ("http://estaticos.invalid/qaB.js?x=1")`). Contradice REQ-057/THREAT-020: los logs no contienen query strings.
- **F-2 (INFO)**: `X-Forwarded-Host` redundante en la location de assets (2 avisos por petición) y RSK-OPS-041 mal dimensionado ("~3 líneas").

### 25.3 Cambios realizados (solo `infra/proxy/nginx.conf`, location de assets)
- `proxy_pass http://frontend$uri;` en lugar de `proxy_pass http://frontend;`. Con una variable en `proxy_pass`, nginx envía esa URI tal cual y no añade `$args`: la query no sale del proxy hacia el SSR.
  - Verificación de la afirmación de la QA sobre la regex: `$uri` es la ruta decodificada y normalizada (nginx resuelve `%2e`, `%2f`, `/./`, `/../` y `//` antes de elegir la location) y es la cadena contra la que se evalúa la regex. La regex solo deja pasar `[A-Za-z0-9_-]`, `/` y `.` en posiciones fijas: nada que recodificar (`%`, `?`, `#`, espacio, controles).
  - **Hallazgo propio al verificarla**: en PCRE, `$` también casa antes de un `\n` final. `/x.js%0A` entraba en la location y, con `$uri`, el `\n` viajaba crudo en la línea de petición al SSR (medido con `$`: 404 con `upstream_s` > 0 y sin pasar por Angular; Node rechazó la petición mal formada). Corregido con el ancla **`\z`**: esa ruta queda fuera del patrón y va por `location /` (zona `por_ip`), como `/x.js%20` o `/x.JS` en `main`.
  - `frontend` es el `upstream` declarado: sin resolver DNS en tiempo de ejecución y con el mismo `keepalive`.
- Retirados `proxy_set_header X-Forwarded-Host` y `X-Forwarded-Proto` de esa location (F-2). Angular 22.2 los ignora sin `trustProxyHeaders` (la validación SSRF usa solo `Host`) y cada uno escribía 2 avisos por asset inexistente; `express.static` tampoco los usa (`trust proxy` desactivado). `X-Forwarded-Proto` no lo citaba la QA: se retira por la misma causa medida (decisión propuesta, a numerar por el Orquestador). Se mantienen `Host: estaticos.invalid`, `X-Request-Id` y `traceparent`.
- Sin cambios en zonas, `error_page`, cabeceras de respuesta, `limit_except` ni en el resto de locations.

### 25.4 Versiones, infraestructura, dependencias y variables de entorno
Sin cambios (proxy `nginxinc/nginx-unprivileged:1.30.5-alpine@sha256:4714e0b1…`, Angular/`@angular/ssr` 22.2.0, Express 5.2.1; sin cambios de compose, redes, healthchecks ni lockfiles). Sigue vigente el requisito de §23.5: `NG_ALLOWED_HOSTS` nunca con `*` ni hosts `.invalid` (RSK-OPS-040; smoke de CI en TKT-OPS-018).

### 25.5 Validaciones ejecutadas
Fecha: 2026-10-01. Docker Engine 29.6.1, Compose v5.2.0. Proyecto propio `-p ops019` (`APP_NET_PREFIX=10.231.119`, `PROXY_HOST_PORT=18219`), desmontado con `down -v` al terminar. A/B cambiando **solo** el contenedor `proxy` (imagen de `main` @ 7df7c77 frente a la de la rama) sobre el mismo backend/frontend/db. Scripts de medición en el scratchpad, fuera del repositorio.
- **VALIDADO — AC_OPS019_01**: `/no-existe-N.js?secreto=1`, `/no-existe-N.css?secreto=1`, `/fonts/xN.woff2?secreto=1`, `/media/publico/xN?secreto=1` y `/media/publico/a/bN.jpg?secreto=1` → 404 Problem Details. Coincidencias de `secreto`: `main` SSR 3 / proxy 0; rama **SSR 0 / proxy 0**. Ráfaga de 400 inexistentes únicos con query: 0 apariciones del token en SSR y proxy.
- **VALIDADO — AC_OPS019_02** (matriz de 37 variantes, misma batería en `main` y en la rama):
  - `/x.js`, `/x.css`, `/x.mjs`, `/fonts/x.woff2`, `/media/publico/x`, `?x=1`, `?` vacía, `%2e`, `%2E`, `/fonts%2fx.woff2`, `/a/..%2fx.js`, `/a/../x.js`, `/./x.js`, `//x.js`, `///fonts//x.woff2`, Host `localhost`/`estaticos.invalid`, `X-Forwarded-Host`, `X-Forwarded-Host+Proto+For`, `Forwarded`, `X-Forwarded-Port/Prefix`, forma absoluta (con y sin Host): 404 `application/problem+json`, rechazo de Host en el SSR (22 de 22) y **0 renders** (0 `error_ssr`). En la rama la URI que llega al SSR es la ruta normalizada sin query (p. ej. `/a/..%2fx.js` → `/x.js`; `main` reenviaba la cruda).
  - POST/PUT/DELETE/PATCH/OPTIONS → 403 y TRACE → 405, Problem Details, sin upstream. `%00` → 400 Problem Details del proxy.
  - Fuera del patrón, igual que en `main` (zona `por_ip`, render 404 del SSR): `%0D%0A…`, `%3F`, `%23`, `%20`, `.JS`, `;x=1`. Única diferencia A/B: `%0A` pasa de la location de assets a este grupo (ancla `\z`, §25.3).
  - Peticiones al backend durante la matriz: 0 (fuera de `/health`).
  - 400 inexistentes únicos: 313 × 404 + 87 × 429 (zona `estaticos`), 313 rechazos de Host, 0 `error_ssr`, 0 peticiones al backend.
- **VALIDADO — AC_OPS019_03**: `main-*.js`, `styles-*.css`, `chunk-*.js`, una fuente `/fonts/*.woff2` y `/favicon.ico`, con y sin `?v=1`, `Accept-Encoding` identity y gzip: 20 × 200; `If-None-Match` → 304 (5/5); HEAD 200; `Content-Encoding: gzip` en JS/CSS; `Cache-Control: public, max-age=31536000, immutable` en los que llevan hash (fuentes y favicon conservan `max-age=3600`, como en `main`). Cabeceras normalizadas (sin Date, nonce de CSP ni valor de ETag) **idénticas** a las de `main` (`diff` vacío): CSP, nosniff, Referrer, Permissions, COOP, CORP y XFO.
- **VALIDADO — AC_OPS019_04**: `nginx -t` OK en el contenedor; `docker compose config --quiet` OK en las 4 variantes (base, `--profile ops`, `+compose.ci.yaml`, `+compose.debug.yaml`); db, backend, frontend y proxy healthy; `/health/ready` 200.
- **Medición RSK-OPS-041**: líneas del log del SSR por asset inexistente: `main` **8** (2 avisos `x-forwarded-host`, 2 `x-forwarded-proto`, 4 del rechazo de Host incluida una en blanco) → rama **4** (`ERROR: Bad Request ("http://estaticos.invalid/<ruta>")`, `Header "host" … is not allowed`, línea en blanco, enlace). Ráfaga: 1252 líneas para 313 rechazos (4,0 por petición).
- **Control cruzado con el smoke de TKT-OPS-018** (`scripts/ops/smoke-anti-evasion.sh`, se versiona en el PR de TKT-OPS-018): rama 5/5 OK; proxy de `main` falla solo C4 (query en el log del SSR: 3 apariciones).
- **trivy** (proxy de la rama, `--severity CRITICAL,HIGH --ignorefile .trivyignore`, BD fresca en caché propia, `UpdatedAt` 2026-10-01 01:24:14 UTC, RSK-OPS-045): 0 hallazgos, exit 0.
- **AC_OPS019_05**: ADR-OPS-001 (estado, puntos 1, 3 y 7, RSK-OPS-041, evidencia) y §23.3/§23.10 de este documento corregidos.
- **NOT_RUN en local**: suites de backend/frontend (no se tocan); las ejecuta el CI del PR.

### 25.6 Seguridad
- REQ-057/THREAT-020: ninguna query de una petición de asset sale del proxy hacia el SSR. El log del proxy ya la omitía (`ruta`/`ruta_pedida`).
- Se cierra además un vector que el cambio habría abierto (`\n` crudo hacia el upstream) con el ancla `\z`.
- La defensa anti-evasión no cambia: `Host: estaticos.invalid`, zona `estaticos`, `proxy_intercept_errors`. Sin cambios de privilegios (uid 101, raíz de solo lectura).

### 25.7 Riesgos / pendientes
| ID | Riesgo | Sev. | Mitigación / acción | Estado |
|---|---|---|---|---|
| RSK-OPS-041 | Inflado del log del SSR por assets inexistentes | LOW | 4 líneas por petición (antes 8), acotado por la zona `estaticos`; json-file 10 MB × 5; filtrar en los logs centralizados de producción | ACEPTADO (reducido) |
| RSK-OPS-040 | `NG_ALLOWED_HOSTS` con `*` o `*.invalid` | MEDIUM (si se configura mal) | Smoke de CI de TKT-OPS-018 | ABIERTO (TKT-OPS-018) |
| — | `/x.js%0A` va ahora por `location /` (`por_ip`, render 404 del SSR) en vez de rechazarse por Host | INFO | Cupo estricto `por_ip`, igual que `/x.js%20` o `/x.JS` en `main` | ACEPTADO |

### 25.8 Archivos modificados
- `infra/proxy/nginx.conf`
- `docs/adr/ADR-OPS-001.md`
- `docs/05_operacion/DEVOPS_HANDOFF.md`

### 25.9 Próximo agente
**Orquestador**: registrar en `audit_log.md`/`kanban.md` la revisión del ADR (ancla `\z` y retirada de `X-Forwarded-Proto`), lanzar QA de TKT-OPS-019 e integrar tras QA PASS y CI verde. El resultado del CI real del PR se reporta en el HANDOFF_ENVELOPE.

## 26. TKT-OPS-021: retirada de la excepción de oasdiff (DEC-AUTO-920) y gate de cobertura por módulo (Skill_Backend §8) (F7, soporte, LOW)

### 26.1 Estado
**COMPLETADO** en la rama `tkt-ops-021-cobertura-oasdiff`. Sin despliegue, sin secretos reales y sin costes (CLAUDE.md §0.5). Origen: CHG-OPS del Developer de TKT-012 (DEC-AUTO-940).

### 26.2 Objetivo
(a) Retirar la excepción `--err-ignore` de DEC-AUTO-920 (`request-body-type-changed` en `POST /api/v1/panel/medios`), que tras TKT-012 ya no casa con ningún hallazgo. (b) Hacer cumplir en CI los umbrales por módulo de Skill_Backend §8, que hasta ahora solo se revisaban a mano (el CI solo exigía el total con `--cov-fail-under=80`).

### 26.3 Cambios realizados
- `infra/ci/oasdiff_err_ignore.txt`: **sin reglas**. Se mantiene el archivo y el flag `--err-ignore` en `ci.yaml` como punto único y versionado de futuras excepciones del gate de contrato (análogo a `.trivyignore`); así ninguna excepción entra por una vía paralela. Cabecera con historial, procedimiento para añadir una excepción y formato real de `MatchIgnore` (oasdiff v1.32.1). Los comentarios no contienen "método + espacio + ruta", así que no casan con ningún hallazgo.
- `infra/ci/cobertura_umbrales.toml` (nuevo): reglas versionadas (`total` > 80, `apps/*/services.py` > 90, endpoints críticos > 95), clasificación obligatoria de vistas y excepciones nombradas con caducidad.
  - **Endpoints críticos** (> 95 %): todas las vistas del panel (`contenido/api/panel_views.py`, `medios/api/views.py`, `catalogos/api/views.py`, `inicio/api/views.py`, `auditoria/api/views.py`) y las de cuentas/autenticación (`cuentas/api/views.py`).
  - **No críticas, con motivo**: `contenido/api/views.py` (API pública de solo lectura) y `core/api/views.py` (health). Siguen sujetas al total.
  - Una vista nueva (`apps/*/api/*views*.py`, `apps/*/views.py`, `apps/*/views/*.py`) que no esté clasificada hace fallar el gate.
- `infra/ci/gate_cobertura.py` (nuevo, solo biblioteca estándar: `json`, `tomllib`, `fnmatch`): lee `coverage.json` (`percent_covered` sin redondear, con ramas porque `branch = true`) y compara de forma **estricta** (`>`), como dice §8. Falla cerrado si falta el `coverage.json` o no es válido, si un patrón no casa con ningún archivo (renombrado), si un archivo existe en disco y no está medido, o si una vista no está clasificada. Imprime una tabla de módulos y, al final, la lista de los que quedan por debajo (`::error::`).
  - **Excepciones**: campos obligatorios `archivo`, `umbral_minimo` (suelo: tampoco puede bajar de él), `registrada`, `caduca`, `ticket`, `decision` y `motivo`. La ventana no puede superar 45 días y el gate falla al caducar. Una excepción ya innecesaria solo genera un aviso (`::warning::`), para no bloquear el PR del Developer que sube la cobertura: se retira en el siguiente ticket de DevOps.
- `infra/ci/gate_cobertura_controles.py` (nuevo): 16 controles sintéticos (P1-P2, N1-N13) + 4 sobre el `coverage.json` real (R1 configuración real → 0; R2 umbral imposible → 1; R3 `coverage.json` manipulado → 1; R4 fecha simulada tras la caducidad → 1).
- `.github/workflows/ci.yaml` (job backend): `pytest --cov-report=json:coverage.json` y, a continuación, dos pasos nuevos: los controles del gate y el gate. Comentario del gate de contrato actualizado (excepción retirada).

### 26.4 Excepciones vigentes (propuestas: el Orquestador debe registrarlas como DEC-AUTO)
| Id | Archivo | Cobertura en main | Suelo | Caduca | Retirar con |
|---|---|---|---|---|---|
| TKT-OPS-021-EXC-01 | `apps/catalogos/api/views.py` | 71,81 % | 71 % | 2026-10-31 | TKT-032 (en QA) |
| TKT-OPS-021-EXC-02 | `apps/inicio/api/views.py` | 93,75 % | 93 % | 2026-10-31 | TKT-032 (en QA) |

### 26.5 Versiones, infraestructura, dependencias y variables de entorno
Sin cambios. oasdiff v1.32.1 (binario Windows verificado contra `checksums.txt` de la release; el sha256 Linux de ese archivo coincide con `OASDIFF_SHA256` de `ci.yaml`). Python 3.13 del runner (`tomllib` en la biblioteca estándar); sin dependencias nuevas.

### 26.6 Validaciones ejecutadas (2026-10-01, en local)
- **oasdiff** (mismos pasos y flags que el CI: `spectacular --validate` → `gate_contrato.py` → `oasdiff breaking … --fail-on ERR --err-ignore`): 128/128 operaciones, 0 errores del gate; oasdiff sin cambios rompedores con el archivo nuevo, con el anterior y con `--fail-on WARN`.
- **Control del mecanismo `--err-ignore`**: reintroduciendo el hallazgo histórico en una copia del esquema generado (cuerpo `string/binary`), el archivo nuevo da **exit 1** (`1 error`) y el anterior **exit 0**. El flag sigue leyendo el archivo y el archivo nuevo no ignora nada.
- **pytest** contra PostgreSQL 18.6 efímero (proyecto `brujulaops020`, `compose.yaml + compose.ci.yaml`): 1069 passed, 4 skipped, total 96,38 %. Gate: 15 módulos evaluados, 0 por debajo, PASS (con las 2 excepciones de §26.4). El CI de `main` (run 36883312241) da las mismas cifras por módulo.
- **Controles**: 20/20 correctos. Falla cerrado sin `coverage.json` (exit 1).
- `ruff check` y `ruff format --check` (configuración del backend) limpios en los dos scripts nuevos; `ci.yaml` se carga con PyYAML.
- El CI real del PR se reporta en el HANDOFF_ENVELOPE.

### 26.7 Riesgos / pendientes
| ID | Riesgo | Sev. | Acción | Estado |
|---|---|---|---|---|
| — | Dos vistas del panel bajo 95 % con excepción hasta el 2026-10-31 | LOW | TKT-032 las sube; después, retirar las excepciones (el gate avisará) | ABIERTO |
| — | `coverage.json` no está en `.gitignore` | INFO | Ticket al Developer/Orquestador (`.gitignore` está fuera del alcance de DevOps) | PENDIENTE |
| — | Comparación estricta (`>`, §8) frente a "≥" del título del ticket | INFO | Se aplica §8 (mayor rango, CLAUDE.md §0.1); solo difiere si un módulo queda exactamente en el umbral | REGISTRAR |
| — | Smoke anti-evasión (TKT-OPS-018) sin documentar aquí | INFO | Se documenta en F9 | PENDIENTE |

### 26.8 Archivos modificados
`infra/ci/oasdiff_err_ignore.txt`, `infra/ci/cobertura_umbrales.toml` (nuevo), `infra/ci/gate_cobertura.py` (nuevo), `infra/ci/gate_cobertura_controles.py` (nuevo), `.github/workflows/ci.yaml`, `docs/05_operacion/DEVOPS_HANDOFF.md`.

### 26.9 Próximo agente
**Orquestador**: registrar las excepciones de §26.4 como DEC-AUTO, lanzar QA de TKT-OPS-021 y, al integrar TKT-032, abrir la retirada de las excepciones.
