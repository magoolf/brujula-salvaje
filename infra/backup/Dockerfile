# syntax=docker/dockerfile:1
# =============================================================================
# Servicio de copias (ADR-DB-004 §3, DEC-AUTO-093; TKT-F6-001).
# Misma imagen base que la BD -> pg_dump/pg_restore 18.6 idénticos al servidor.
#   Contexto de build: infra/backup     Contexto adicional: ops=./scripts/ops
# Cifrado con age (clave PÚBLICA en BACKUP_AGE_RECIPIENT; la privada nunca entra al repo ni
# al contenedor; la clave real es Puerta Humana, CLAUDE.md §0.5).
# =============================================================================
ARG POSTGRES_IMAGE=postgres:18.6-trixie@sha256:5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722
FROM ${POSTGRES_IMAGE}
ARG TARGETARCH
ARG AGE_DEB_VERSION=1.2.1-1+b5
ARG SUPERCRONIC_VERSION=v0.2.49
ARG SUPERCRONIC_SHA256_AMD64=a53ae236602c7338aba3fbaff40bda6300eae3b9fedb8261eb06cfe3724430c1
ARG SUPERCRONIC_SHA256_ARM64=02aa0cb229ba09050cba6638059dadb9eedc2276632ea43d6a57a2f8c1629dd5

LABEL org.opencontainers.image.title="brujula-backup" \
      org.opencontainers.image.description="pg_dump + copia de medios + manifiesto sha256, cifrado con age, rotación 30 días"

RUN set -eu; \
    apt-get update; \
    apt-get install -y --no-install-recommends "age=${AGE_DEB_VERSION}"; \
    # gosu no se usa (el servicio arranca ya como uid 999) y arrastra CVE de Go stdlib (trivy, F6)
    rm -f /usr/local/bin/gosu; \
    rm -rf /var/lib/apt/lists/*

ADD --chmod=0755 https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH} /usr/local/bin/supercronic
RUN set -eu; \
    case "${TARGETARCH}" in \
      amd64) expected="${SUPERCRONIC_SHA256_AMD64}" ;; \
      arm64) expected="${SUPERCRONIC_SHA256_ARM64}" ;; \
      *) echo "arquitectura no soportada: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    echo "${expected}  /usr/local/bin/supercronic" | sha256sum -c -; \
    install -d -m 0755 /etc/brujula

COPY --from=ops --chown=root:root --chmod=0555 backup.sh restore-local.sh /usr/local/bin/
COPY --chown=root:root --chmod=0444 crontab /etc/brujula/backup.crontab
# Punto de montaje del volumen de copias: propiedad de 999 para que el volumen nombrado la herede.
RUN mkdir -p /backups && chown 999:999 /backups && chmod 0700 /backups

# Usuario sin privilegios de la imagen (uid 999). Nunca se usa el superusuario de la BD.
USER 999:999
WORKDIR /tmp
ENTRYPOINT []
HEALTHCHECK NONE
CMD ["supercronic", "-json", "-passthrough-logs", "/etc/brujula/backup.crontab"]
