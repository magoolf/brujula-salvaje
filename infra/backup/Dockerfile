# syntax=docker/dockerfile:1
# =============================================================================
# Servicio de copias (ADR-DB-004 §3, DEC-AUTO-093; TKT-F6-001). Imagen MÍNIMA (TKT-OPS-005,
# DEC-AUTO-222): antes heredaba la imagen completa del servidor PostgreSQL (servidor, perl, gnupg,
# libxml2... -> 1 CRITICAL + 7 HIGH de libxml2 y CVE de gnupg/perl, RSK-OPS-001). Ahora:
#   - base debian:13.7-slim (la misma Debian 13.7 sobre la que está construida postgres:18.6-trixie);
#   - pg_dump / pg_restore / psql 18.6 y libpq 18.6 COPIADOS de la imagen fijada de la BD (mismo
#     digest que el servidor -> cliente idéntico al servidor, requisito de ADR-DB-004);
#   - solo las bibliotecas Debian que esos binarios necesitan (ldd, ver DEVOPS_HANDOFF §17) + age;
#   - supercronic verificado por sha256. Sin servidor, sin perl completo, sin gnupg, sin libxml2.
#   Contexto de build: infra/backup     Contexto adicional: ops=./scripts/ops
# Herramientas que usan backup.sh / restore-local.sh: bash, pg_dump, pg_restore, psql, tar,
# sha256sum, age, find, sort, tail, mktemp, date, grep (coreutils/findutils/tar/grep de la base).
# Cifrado con age (clave PÚBLICA en BACKUP_AGE_RECIPIENT; la privada nunca entra al repo ni
# al contenedor; la clave real es Puerta Humana, CLAUDE.md §0.5).
# =============================================================================
# Imagen base LITERAL en FROM (sin ARG): Dependabot (ecosistema docker) no resuelve ARG en FROM y
# no vería el digest (TKT-OPS-006, RSK-OPS-025, DEC-AUTO-254). Actualizar tag y digest juntos.

# ---------------------------------------------------------------------------
# pgclient: extrae de la imagen fijada de la BD solo el cliente 18.6 (binarios + libpq)
# ---------------------------------------------------------------------------
FROM postgres:18.6-trixie@sha256:5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722 AS pgclient
RUN set -eu; \
    mkdir -p /out/bin /out/lib; \
    for b in pg_dump pg_restore psql; do cp -a "/usr/lib/postgresql/18/bin/$b" /out/bin/; done; \
    for f in $(dpkg -L libpq5 | grep -E '/libpq\.so\.5'); do cp -a "$f" /out/lib/; done; \
    dpkg-query -W -f='${Package}=${Version}\n' libpq5 postgresql-client-18 > /out/VERSIONES

# ---------------------------------------------------------------------------
# final
# ---------------------------------------------------------------------------
FROM debian:13.7-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a
ARG TARGETARCH
ARG AGE_DEB_VERSION=1.2.1-1+b5
ARG KRB5_DEB_VERSION=1.21.3-5+deb13u1
ARG LDAP_DEB_VERSION=2.6.10+dfsg-1
ARG READLINE_DEB_VERSION=8.2-6
ARG SUPERCRONIC_VERSION=v0.2.49
ARG SUPERCRONIC_SHA256_AMD64=a53ae236602c7338aba3fbaff40bda6300eae3b9fedb8261eb06cfe3724430c1
ARG SUPERCRONIC_SHA256_ARM64=02aa0cb229ba09050cba6638059dadb9eedc2276632ea43d6a57a2f8c1629dd5
ARG OPENSSL_DEB_VERSION=3.5.7-1~deb13u3
ARG PCRE2_DEB_VERSION=10.46-1~deb13u3

LABEL org.opencontainers.image.title="brujula-backup" \
      org.opencontainers.image.description="pg_dump 18.6 + copia de medios + manifiesto sha256, cifrado con age, rotación 30 días" \
      org.opencontainers.image.source="STACK_TECNOLOIGICO" \
      org.opencontainers.image.licenses="NOASSERTION"

# Dependencias de ejecución de pg_dump/pg_restore/psql (libpq: GSSAPI, LDAP; psql: readline).
# libzstd1, liblz4-1, zlib1g, libssl3t64 y libxxhash0 ya están en la base slim.
# TKT-OPS-015: mismo DSA-6531-1 que TKT-OPS-014 (infra/db/Dockerfile), aplicado aqui a
# libssl3t64/openssl-provider-legacy (corrige CVE-2026-84782 -- DTLS info disclosure -- y
# CVE-2026-75804 -- QUIC DoS --, ambos HIGH). Esta base no trae el paquete "openssl" (solo
# libssl3t64 y openssl-provider-legacy). Version fijada explicitamente (REGLA 3, cero versiones
# ambiguas) en el mismo "apt-get install" que ya fija el resto de dependencias: no hace falta
# --only-upgrade porque estos dos paquetes ya vienen preinstalados en la base y apt-get install
# con version explicita los actualiza igual (sin ningun purge --force-depends que lo impida).
# TKT-OPS-017: mismo patron para libpcre2-8-0 (preinstalada en la base; CVE-2026-103111 HIGH en
# 10.46-1~deb13u2, corregida en 10.46-1~deb13u3 de trixie-security). A 2026-10-01 el digest
# publicado de debian:13.7-slim no ha cambiado y sigue trayendo deb13u2.
RUN set -eu; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      "age=${AGE_DEB_VERSION}" \
      "libgssapi-krb5-2=${KRB5_DEB_VERSION}" \
      "libldap2=${LDAP_DEB_VERSION}" \
      "libreadline8t64=${READLINE_DEB_VERSION}" \
      "libssl3t64=${OPENSSL_DEB_VERSION}" \
      "openssl-provider-legacy=${OPENSSL_DEB_VERSION}" \
      "libpcre2-8-0=${PCRE2_DEB_VERSION}"; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb; \
    for p in libssl3t64 openssl-provider-legacy; do \
      v="$(dpkg-query -W -f='${Version}' "$p")"; \
      case "$v" in "${OPENSSL_DEB_VERSION}") ;; *) echo "$p en version inesperada '$v'" >&2; exit 1 ;; esac; \
    done; \
    v="$(dpkg-query -W -f='${Version}' libpcre2-8-0)"; \
    case "$v" in "${PCRE2_DEB_VERSION}") ;; *) echo "libpcre2-8-0 en version inesperada '$v'" >&2; exit 1 ;; esac

COPY --from=pgclient --chown=root:root /out/lib/ /usr/local/lib/
COPY --from=pgclient --chown=root:root /out/bin/ /usr/local/bin/
COPY --from=pgclient --chown=root:root /out/VERSIONES /usr/local/share/brujula/pgclient.versiones
# Usuario sin privilegios uid/gid 999 (mismo que "postgres" en la imagen anterior: el volumen
# de copias ya existente es de 999). /usr/local/lib ya está en ld.so.conf (libc.conf).
RUN set -eu; \
    ldconfig; \
    groupadd --system --gid 999 backup_app; \
    useradd --system --uid 999 --gid 999 --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin backup_app; \
    pg_dump --version | grep -q ' 18\.6'; \
    pg_restore --version | grep -q ' 18\.6'; \
    psql --version | grep -q ' 18\.6'; \
    age --version

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

# Usuario sin privilegios (uid 999). Nunca se usa el superusuario de la BD.
USER 999:999
WORKDIR /tmp
HEALTHCHECK NONE
CMD ["supercronic", "-json", "-passthrough-logs", "/etc/brujula/backup.crontab"]
