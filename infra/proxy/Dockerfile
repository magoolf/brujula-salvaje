# syntax=docker/dockerfile:1
# Reverse proxy de mismo origen (TKT-F6-001). Contexto de build: infra/proxy
# nginx 1.30.5 (rama stable) sin privilegios: uid 101, puerto 8080.
ARG NGINX_IMAGE=nginxinc/nginx-unprivileged:1.30.5-alpine@sha256:4714e0b1b2577eaa1a6131d07c958b67f0eb68e6d0521e90c6e5287db8cf0bc5
FROM ${NGINX_IMAGE}

LABEL org.opencontainers.image.title="brujula-proxy" \
      org.opencontainers.image.description="Reverse proxy de mismo origen (SSR Angular + API Django)" \
      org.opencontainers.image.source="STACK_TECNOLOIGICO" \
      org.opencontainers.image.licenses="NOASSERTION"

# Se sustituye la configuración por defecto (sin default.conf ni plantillas de entorno).
USER root
# libexpat 2.8.5-r0: corrige CVE-2026-93990 (HIGH) presente en la imagen base (trivy, F6).
# Retirar esta línea cuando la imagen base fijada ya la incluya.
RUN apk add --no-cache "libexpat=2.8.5-r0" \
 && rm -f /etc/nginx/conf.d/default.conf \
 && rm -rf /docker-entrypoint.d/* \
 && mkdir -p /etc/nginx/snippets /srv/media
COPY --chown=root:root --chmod=0444 nginx.conf /etc/nginx/nginx.conf
COPY --chown=root:root --chmod=0444 snippets/*.conf /etc/nginx/snippets/
USER 101

EXPOSE 8080
STOPSIGNAL SIGQUIT
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8081/nginx-health || exit 1
CMD ["nginx", "-g", "daemon off;"]
