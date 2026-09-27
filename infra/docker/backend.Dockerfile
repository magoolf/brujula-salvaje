# syntax=docker/dockerfile:1
# =============================================================================
# Backend Django 5.2 + DRF (TKT-F6-001). Multi-stage, usuario no root, sin herramientas de build
# en la imagen final.
#   Contexto de build: ./backend        (código del Developer, F7)
#   Contexto adicional: infra=./infra    (crontab del planificador)
#   Targets:  runtime   -> web (gunicorn) y job de migración
#             scheduler -> runtime + supercronic (comandos de gestión programados, DEC-AUTO-122)
# Archivos que DEBE crear el Developer en backend/ (ver docs/05_operacion/DEVOPS_HANDOFF.md §6):
#   pyproject.toml + uv.lock (dependencias con ==), manage.py, config/{settings.py,wsgi.py},
#   ruta /health/live y /health/ready.
# =============================================================================
ARG PYTHON_IMAGE=python:3.13.15-slim-trixie@sha256:8d9d0b8bcf6506481eae4907c18f5e3e7902e629f5f6d684f9e7c32e85e3ddf0
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.19@sha256:04d046b13e60d6bcec73cbc5e1cad25d680dea90c8573340950a0ac2d1aef424

FROM ${UV_IMAGE} AS uv

# ---------------------------------------------------------------------------
# builder: resuelve dependencias desde uv.lock (--frozen: falla si el lock no cuadra)
# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS builder
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
FROM ${PYTHON_IMAGE} AS python-sin-pip
RUN set -eu; \
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
    python --version

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
# scheduler: runtime + supercronic 0.2.49 (verificado por sha256) + crontab versionado
# ---------------------------------------------------------------------------
FROM runtime AS scheduler
ARG TARGETARCH
ARG SUPERCRONIC_VERSION=v0.2.49
ARG SUPERCRONIC_SHA256_AMD64=a53ae236602c7338aba3fbaff40bda6300eae3b9fedb8261eb06cfe3724430c1
ARG SUPERCRONIC_SHA256_ARM64=02aa0cb229ba09050cba6638059dadb9eedc2276632ea43d6a57a2f8c1629dd5
USER root
ADD --chmod=0755 https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH} /usr/local/bin/supercronic
RUN set -eu; \
    case "${TARGETARCH}" in \
      amd64) expected="${SUPERCRONIC_SHA256_AMD64}" ;; \
      arm64) expected="${SUPERCRONIC_SHA256_ARM64}" ;; \
      *) echo "arquitectura no soportada: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    echo "${expected}  /usr/local/bin/supercronic" | sha256sum -c -; \
    install -d -m 0755 /etc/brujula
COPY --from=infra --chown=root:root --chmod=0444 scheduler/crontab /etc/brujula/crontab
USER 10001:10001
HEALTHCHECK NONE
CMD ["supercronic", "-json", "-passthrough-logs", "/etc/brujula/crontab"]
