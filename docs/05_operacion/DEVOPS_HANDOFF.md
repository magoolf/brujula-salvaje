# DEVOPS HANDOFF — TKT-F6-001 (F6 [PRE-DESARROLLO])

Proyecto: Brújula Salvaje. Fecha: 2026-09-25. Autor: Skill_devops.
Actualizado por **TKT-OPS-001** (F7, soporte de infraestructura, 2026-09-25): ver §13.
Actualizado por **TKT-OPS-003** (F7, CI verde + proxy/gzip + Dependabot, 2026-09-26): ver §15.
Actualizado por **TKT-OPS-004** (F7, gate de contrato por operación + límite de /health + errores del proxy + Dependabot sin mayores, 2026-09-26): ver §16.
Actualizado por **TKT-OPS-005** (F7, RSK-OPS-001 según decisión humana: `.trivyignore` con caducidad, runtimes sin gestores de paquetes, backup mínimo, `Cache-Control` del HTML SSR, `DJANGO_TRUSTED_PROXIES`, 2026-09-26): ver §17. **RSK-OPS-001 queda aceptado con caducidad hasta el 2026-10-26** (§17.10). Ciclo 2 (imagen de la BD derivada y en el gate): §17.14.
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
