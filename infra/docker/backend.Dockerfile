# syntax=docker/dockerfile:1
# =============================================================================
# Backend Django 5.2 + DRF (TKT-F6-001). Multi-stage, usuario no root, sin herramientas de build
# en la imagen final.
#   Contexto de build: ./backend        (código del Developer, F7)
#   Contexto adicional: infra=./infra    (crontab del planificador)
#   Targets:  runtime   -> web (gunicorn) y job de migración
#             scheduler -> runtime + supercronic (comandos de gestión programados, DEC-AUTO-122;
#                          compilado desde el fuente con Go corregido, etapa "supercronic", TKT-OPS-031)
# Archivos que DEBE crear el Developer en backend/ (ver docs/05_operacion/DEVOPS_HANDOFF.md §6):
#   pyproject.toml + uv.lock (dependencias con ==), manage.py, config/{settings.py,wsgi.py},
#   ruta /health/live y /health/ready.
# =============================================================================
# Imagen base LITERAL en FROM (sin ARG): Dependabot (ecosistema docker) no resuelve ARG en FROM y
# no vería el digest (TKT-OPS-006, RSK-OPS-025, DEC-AUTO-254). Actualizar tag y digest juntos.

# >>> receta supercronic (TKT-OPS-031, DEC-AUTO-979) — BLOQUE IDÉNTICO en infra/backup/Dockerfile e
# infra/docker/backend.Dockerfile (lo exige infra/ci/supercronic_receta.sh en el job "infra").
# supercronic v0.2.49 es la última release (2026-08-14) y su binario publicado está compilado con
# Go 1.26.6 -> CVE-2026-78667 (net/http, DoS, HIGH; corregida en Go 1.26.9 / 1.27.2). Se compila
# el MISMO código fuente de la release (tag v0.2.49 verificado contra su commit SHA: el SHA-1 del
# commit cubre todo el árbol) con un Go corregido. Misma receta que build.sh de upstream
# (CGO_ENABLED=0, -X main.Version=<tag>) + -trimpath y -buildvcs=false (reproducible).
# Módulos verificados con go.sum + sum.golang.org (go mod verify). Se compila en la plataforma
# destino (TARGETARCH amd64/arm64; sin --platform=$BUILDPLATFORM: el control de Dependabot rechaza
# variables en FROM). Imagen golang LITERAL con digest (Dependabot la
# sigue; grupo "golang" en .github/dependabot.yml actualiza ambos Dockerfile en un único PR).
# Cuando upstream publique una release compilada con Go corregido, puede volverse al binario
# publicado (ADD + sha256) — ver DEVOPS_HANDOFF.md §33.
FROM golang:1.26.9-trixie@sha256:f89535b7caea67fa9ff0ba009894bff8f3be915e49cb635477c8ce04e045db5d AS supercronic
ARG TARGETARCH
ARG SUPERCRONIC_VERSION=v0.2.49
ARG SUPERCRONIC_COMMIT=8e0a4a40090de8a22942c9fa573e27885ce18311
ARG GO_MIN_VERSION=go1.26.9
ENV CGO_ENABLED=0 \
    GOOS=linux \
    GOTOOLCHAIN=local \
    GOFLAGS=-mod=readonly
WORKDIR /src
RUN set -eu; \
    git init -q .; \
    git remote add origin https://github.com/aptible/supercronic.git; \
    git fetch -q --depth 1 origin "refs/tags/${SUPERCRONIC_VERSION}"; \
    got="$(git rev-parse 'FETCH_HEAD^{commit}')"; \
    [ "$got" = "${SUPERCRONIC_COMMIT}" ] || { echo "tag ${SUPERCRONIC_VERSION} -> $got, esperado ${SUPERCRONIC_COMMIT}" >&2; exit 1; }; \
    git -c advice.detachedHead=false checkout -q "${SUPERCRONIC_COMMIT}"; \
    rm -rf .git; \
    go mod download; \
    go mod verify
RUN set -eu; \
    case "${TARGETARCH}" in amd64|arm64) ;; *) echo "arquitectura no soportada: ${TARGETARCH}" >&2; exit 1 ;; esac; \
    GOARCH="${TARGETARCH}" go build -trimpath -buildvcs=false \
      -ldflags="-X main.Version=${SUPERCRONIC_VERSION}" -o /out/supercronic .; \
    go version -m /out/supercronic > /out/supercronic.buildinfo; \
    cat /out/supercronic.buildinfo; \
    v="$(head -n1 /out/supercronic.buildinfo | awk '{print $2}')"; \
    [ "$v" = "$(go env GOVERSION)" ] || { echo "Go del binario inesperado: $v" >&2; exit 1; }; \
    [ "$(printf '%s\n%s\n' "${GO_MIN_VERSION}" "$v" | sort -V | head -n1)" = "${GO_MIN_VERSION}" ] || { echo "Go $v < ${GO_MIN_VERSION}" >&2; exit 1; }; \
    grep -qE '^[[:space:]]+build[[:space:]]+CGO_ENABLED=0$' /out/supercronic.buildinfo; \
    grep -qE "^[[:space:]]+build[[:space:]]+GOARCH=${TARGETARCH}\$" /out/supercronic.buildinfo
# <<< receta supercronic

FROM ghcr.io/astral-sh/uv:0.12.19@sha256:04d046b13e60d6bcec73cbc5e1cad25d680dea90c8573340950a0ac2d1aef424 AS uv

# ---------------------------------------------------------------------------
# builder: resuelve dependencias desde uv.lock (--frozen: falla si el lock no cuadra)
# ---------------------------------------------------------------------------
FROM python:3.14.7-slim-trixie@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /src
# Capa de dependencias (caché independiente del código)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
# Código de la aplicación (proyecto Django NO empaquetado: [tool.uv] package = false)
COPY . .
RUN find /src -name '__pycache__' -type d -prune -exec rm -rf {} +  && rm -rf /src/.venv

# ---------------------------------------------------------------------------
# python-min (TKT-OPS-005, DEC-AUTO-221): la imagen oficial de Python SIN pip. pip no se usa en
# ejecución (las dependencias ya están en /opt/venv, resueltas por uv en el builder) y vendoriza
# msgpack (GHSA-6v7p-g79w-8964) y declara setuptools 70.3.0 (CVE-2025-47273), ambas HIGH con parche.
# Se borran pip, sus lanzadores y la rueda de ensurepip, y el sistema de archivos se APLANA en una
# sola capa (FROM scratch + COPY /) para que sus bytes no queden en capas inferiores. La imagen
# base no trae setuptools ni wheel (Python 3.13); /opt/venv (uv) tampoco trae pip.
# ---------------------------------------------------------------------------
# TKT-OPS-015: mismo DSA-6531-1 que TKT-OPS-014 (infra/db/Dockerfile), aplicado aqui a
# openssl/libssl3t64/openssl-provider-legacy (corrige CVE-2026-84782 -- DTLS info disclosure -- y
# CVE-2026-75804 -- QUIC DoS --, ambos HIGH). Esta etapa NO tiene ningun purge --force-depends
# previo (a diferencia de infra/db/Dockerfile): "apt-get install --only-upgrade" con version
# fijada explicitamente (REGLA 3, cero versiones ambiguas) resuelve sin necesidad de
# "apt-get download" + "dpkg --force-depends -i". Se aplica en python-sin-pip, ANTES de aplanar
# el filesystem con FROM scratch + COPY /, para que la version corregida llegue tanto a runtime
# como a scheduler (ambos derivan de python-min).
# TKT-OPS-017: mismo patron para libpcre2-8-0 (CVE-2026-103111 HIGH en 10.46-1~deb13u2 de la base,
# corregida en 10.46-1~deb13u3 de trixie-security). A 2026-10-01 ningun digest publicado trae la
# version corregida (ni el actual de 3.13.15-slim-trixie ni el 3.14.7 que propone Dependabot).
FROM python:3.14.7-slim-trixie@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d AS python-sin-pip
RUN set -eu; \
    apt-get update; \
    apt-get install -y --only-upgrade \
      openssl=3.5.7-1~deb13u3 \
      libssl3t64=3.5.7-1~deb13u3 \
      openssl-provider-legacy=3.5.7-1~deb13u3 \
      libpcre2-8-0=10.46-1~deb13u3; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb; \
    rm -rf /usr/local/lib/python3.13/site-packages/pip \
           /usr/local/lib/python3.13/site-packages/pip-*.dist-info \
           /usr/local/lib/python3.13/ensurepip/_bundled \
           /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.13 \
           /root/.cache /tmp/*; \
    for m in pip setuptools wheel; do \
      if python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('$m') else 1)"; then \
        echo "queda $m en el runtime" >&2; exit 1; \
      fi; \
    done; \
    python --version; \
    for p in openssl libssl3t64 openssl-provider-legacy; do \
      v="$(dpkg-query -W -f='${Version}' "$p")"; \
      case "$v" in 3.5.7-1~deb13u3) ;; *) echo "$p en version inesperada '$v'" >&2; exit 1 ;; esac; \
    done; \
    v="$(dpkg-query -W -f='${Version}' libpcre2-8-0)"; \
    case "$v" in 10.46-1~deb13u3) ;; *) echo "libpcre2-8-0 en version inesperada '$v'" >&2; exit 1 ;; esac

FROM scratch AS python-min
COPY --from=python-sin-pip / /
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    PYTHON_VERSION=3.13.15

# ---------------------------------------------------------------------------
# runtime: imagen mínima, uid 10001, sin compiladores ni gestor de paquetes de Python
# ---------------------------------------------------------------------------
FROM python-min AS runtime
ARG APP_VERSION=0.0.0-dev
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="brujula-backend" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="STACK_TECNOLOIGICO" \
      org.opencontainers.image.licenses="NOASSERTION"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:${PATH}" \
    DJANGO_SETTINGS_MODULE=config.settings \
    APP_VERSION=${APP_VERSION} \
    MEDIA_ROOT=/var/lib/brujula/media \
    OPS_DIR=/var/lib/brujula/ops

RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app \
 && mkdir -p /app /var/lib/brujula/media /var/lib/brujula/ops \
 && chown -R app:app /var/lib/brujula \
 && install -d -m 0755 /etc/brujula

COPY --from=builder --chown=root:root /opt/venv /opt/venv
COPY --from=builder --chown=root:root /src /app
# Logging JSON de gunicorn (DEC-AUTO-153): reutiliza el formatter JSON del backend.
# /etc/brujula se crea antes con 0755: COPY --chmod aplicaría 0444 también al directorio padre.
COPY --from=infra --chown=root:root --chmod=0444 docker/gunicorn-logging.json /etc/brujula/gunicorn-logging.json
WORKDIR /app
USER 10001:10001

EXPOSE 8000
# Liveness del proceso; la readiness (BD) la comprueba compose con /health/ready.
HEALTHCHECK --interval=15s --timeout=4s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3).status == 200 else 1)"]

# gunicorn: workers síncronos; timeout 120 s por la subida síncrona de medios (ADR-API-002 §8).
# Sin access log (la IP completa no debe llegar a los logs, REQ-057): el access log lo emite
# el proxy con IP truncada; gunicorn.access queda sin handlers en gunicorn-logging.json.
# --no-control-socket (DEC-AUTO-152): gunicorn 26 abre por defecto un socket de control en
# $HOME/.gunicorn, imposible con la raíz de solo lectura; no se usa (gunicornc) en contenedor.
# --log-config-json (DEC-AUTO-153): las líneas propias de gunicorn salen en JSON a stdout.
# --forwarded-allow-ips (OBS-08, DEC-AUTO-155): solo la IP fija del proxy en la red "app" (la
# inyecta compose en GUNICORN_FORWARDED_ALLOW_IPS). Sin ella, el valor seguro por defecto es
# 127.0.0.1 (nunca '*'): gunicorn fija wsgi.url_scheme desde X-Forwarded-Proto solo si el
# emisor es de confianza. Django también lee esa cabecera (SECURE_PROXY_SSL_HEADER): ver
# DEVOPS_HANDOFF §14 (requisito para el Developer).
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout ${GUNICORN_TIMEOUT:-120} --graceful-timeout 30 --max-requests 2000 --max-requests-jitter 200 --worker-tmp-dir /tmp --forwarded-allow-ips=\"${GUNICORN_FORWARDED_ALLOW_IPS:-127.0.0.1}\" --no-control-socket --log-config-json /etc/brujula/gunicorn-logging.json --log-level ${GUNICORN_LOG_LEVEL:-info}"]

# ---------------------------------------------------------------------------
# scheduler: runtime + supercronic 0.2.49 (compilado desde el fuente, etapa "supercronic",
# TKT-OPS-031) + crontab versionado
# ---------------------------------------------------------------------------
FROM runtime AS scheduler
USER root
# supercronic compilado en la etapa "supercronic" (TKT-OPS-031); buildinfo (go version -m) como evidencia.
COPY --from=supercronic --chown=root:root --chmod=0755 /out/supercronic /usr/local/bin/supercronic
COPY --from=supercronic --chown=root:root /out/supercronic.buildinfo /usr/local/share/brujula/supercronic.buildinfo
RUN set -eu; \
    supercronic -version | grep -qx 'v0.2.49'; \
    install -d -m 0755 /etc/brujula
COPY --from=infra --chown=root:root --chmod=0444 scheduler/crontab /etc/brujula/crontab
USER 10001:10001
HEALTHCHECK NONE
CMD ["supercronic", "-json", "-passthrough-logs", "/etc/brujula/crontab"]
