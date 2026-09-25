# DEVOPS HANDOFF — TKT-F6-001 (F6 [PRE-DESARROLLO])

Proyecto: Brújula Salvaje. Fecha: 2026-09-25. Autor: Skill_devops.
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
MSYS_NO_PATHCONV=1 docker run --rm --entrypoint age-keygen brujula/backup:0.0.0-dev > ~/.brujula/age-local.key   # FUERA del repo
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
5. `GET /health/live` (sin BD) y `GET /health/ready` (`SELECT 1` con timeout de 1 s), ambos accesibles con `Host: 127.0.0.1:8000`.
6. Medios:
   - Los derivados de medios DISPONIBLES se escriben en `MEDIA_ROOT/publico/…`, con URL `MEDIA_PUBLIC_URL`, nombres `[A-Za-z0-9/_-]+` y extensión `.avif`, `.webp` o `.jpg`.
   - Los originales saneados y los derivados no públicos van en `MEDIA_ROOT/privado/…`.
   - Permisos: `FILE_UPLOAD_PERMISSIONS` 0o640 en privado y 0o644 en publico; directorios 0o750 y 0o755.
   - Al retirar o reactivar un medio, el servicio mueve sus derivados entre `privado/` y `publico/` (DEC-AUTO-147).
7. Comandos de gestión con los nombres del crontab: `purgar_sesiones`, `purgar_auditoria`, `anonimizar_cuentas`, `purgar_ops`, `verificar_busqueda`, `reindexar_busqueda` y `reaplicar_anonimizaciones`. Deben ser idempotentes, usar `pg_try_advisory_lock` (si no obtienen el lock, salen con código 0), registrar en `ops_ejecucion_tarea` y no escribir PII en los logs.
8. Las migraciones RunSQL aplican las excepciones de privilegios que no son de F6: `django_migrations` solo SELECT para `app_rw`; los REVOKE de `readonly` y `app_rw` de DB_HANDOFF (n=10 y n=12); y el REVOKE EXECUTE FROM PUBLIC de las funciones SECURITY DEFINER.
9. Logging JSON a stdout y sin IP completas. gunicorn corre sin access log (lo emite el proxy).
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
- Compose: `COMPOSE_PROJECT_NAME`, `PROXY_HOST_PORT`, `DB_DEBUG_HOST_PORT`, `APP_VERSION`.
- PostgreSQL: `POSTGRES_SUPERUSER_PASSWORD` (solo el init), `DB_NAME`, `APP_MIGRATOR_PASSWORD`, `APP_RW_PASSWORD`, `READONLY_PASSWORD`, `APP_BACKUP_PASSWORD`.
- Django: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_SESSION_COOKIE_SECURE`, `DJANGO_CSRF_COOKIE_SECURE`, `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS`, `DJANGO_NUM_PROXIES`, `DJANGO_LOG_LEVEL`, `THROTTLE_HMAC_KEY`, `MFA_FERNET_KEY`, `MEDIA_PUBLIC_URL`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `OTEL_SDK_DISABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`.
- Compose las inyecta por servicio: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `MEDIA_ROOT`, `LIBRO_ANONIMIZACIONES_PATH`, `OTEL_SERVICE_NAME`, `TZ=UTC`.
- SSR: `NG_ALLOWED_HOSTS`, `API_INTERNAL_URL`.
- Copias: `BACKUP_AGE_RECIPIENT`, `BACKUP_RETENTION_DAYS`.
- Solo CI: `DB_BOOTSTRAP_TEST_TEMPLATE`, `DB_CI_HOST_PORT`.

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
- Ningún contenedor de la aplicación corre como root. `init-volumes` es la única excepción: one-shot, sin red, con solo CHOWN y FOWNER, y justificado (DEC-AUTO-149).
- Privacidad de los logs (REQ-057, THREAT-020):
  - nginx: IP truncada y sin query string; `error_log crit`.
  - PostgreSQL: `log_connections=off`, `log_min_duration_statement=-1`, `log_min_error_statement=panic` y `log_parameter_max_length*=0` (DEC-AUTO-145).
  - gunicorn: sin access log.
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
