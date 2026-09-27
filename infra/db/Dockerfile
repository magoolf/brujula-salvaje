# syntax=docker/dockerfile:1
# =============================================================================
# PostgreSQL 18.6 de la aplicación (servicios db e init-volumes) — TKT-OPS-005 ciclo 2,
# QA-OPS005-01, DEC-AUTO-226. Derivada de la imagen oficial FIJADA POR DIGEST, sin cambiar el
# servidor, initdb, extensiones ni el docker-entrypoint.sh oficial. Se retira lo que el servidor
# no usa y que arrastraba CVE (trivy 0.74.0, DEVOPS_HANDOFF §17.14):
#   - gosu: solo lo usa el entrypoint si arranca como root; compose ejecuta db como 999:999 e
#     init-volumes con entrypoint propio. Binario Go con 22 CVE de stdlib CON parche (1 CRITICAL).
#   - gnupg/gpg*/dirmngr/gpgsm (+ dependencias huérfanas): solo sirvieron para instalar paquetes
#     durante el build de la imagen oficial. CVE-2026-24882 (sin fix).
#   - perl, libperl5.40, perl-modules-5.40: solo los usan los scripts de postgresql-common
#     (pg_wrapper, pg_ctlcluster...), que el entrypoint oficial NO usa (llama a initdb, pg_ctl y
#     psql de /usr/lib/postgresql/18/bin). Se purgan con --force-depends (postgresql-common y
#     postgresql-client-common quedan con la dependencia perl:any sin satisfacer: la imagen es
#     final, nadie instala paquetes sobre ella) y se quitan los enlaces de /usr/bin a pg_wrapper;
#     PATH antepone /usr/lib/postgresql/18/bin (pg_isready del healthcheck, psql de INFRA-DB-000).
#     perl-base (Essential) permanece.
# Lo que NO se puede quitar: libxml2 (enlazada por el binario postgres: tipo xml, xmlparse...).
#   Contexto de build: infra/db
# =============================================================================
ARG POSTGRES_IMAGE=postgres:18.6-trixie@sha256:5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722
FROM ${POSTGRES_IMAGE}

LABEL org.opencontainers.image.title="brujula-db" \
      org.opencontainers.image.description="PostgreSQL 18.6 oficial (digest fijado) sin gosu, gnupg ni perl completo" \
      org.opencontainers.image.source="STACK_TECNOLOIGICO" \
      org.opencontainers.image.licenses="NOASSERTION"

ENV PATH=/usr/lib/postgresql/18/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

USER root
RUN set -eu; \
    rm -f /usr/local/bin/gosu; \
    # apt-get purge funciona sin red (no hace falta apt-get update)
    apt-get purge -y --auto-remove gnupg dirmngr gnupg-l10n gpg gpg-agent gpgsm gpgconf; \
    for f in /usr/bin/*; do \
      if [ -L "$f" ] && [ "$(readlink "$f")" = "../share/postgresql-common/pg_wrapper" ]; then rm -f "$f"; fi; \
    done; \
    dpkg --purge --force-depends perl libperl5.40 perl-modules-5.40; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb /var/log/apt /var/log/dpkg.log; \
    # Controles: nada de lo retirado queda y las herramientas que se usan resuelven al binario 18.6
    for b in gosu gpg gpg-agent dirmngr; do \
      if command -v "$b" >/dev/null 2>&1; then echo "queda $b" >&2; exit 1; fi; \
    done; \
    # /usr/bin/perl sigue existiendo: lo aporta perl-base (Essential); se comprueba el estado dpkg
    for p in perl libperl5.40 perl-modules-5.40 gnupg dirmngr gpg; do \
      if dpkg-query -W -f='${db:Status-Abbrev}' "$p" 2>/dev/null | grep -q '^ii'; then echo "queda el paquete $p" >&2; exit 1; fi; \
    done; \
    for b in postgres initdb pg_ctl psql pg_isready; do \
      p="$(command -v "$b")"; \
      case "$p" in /usr/lib/postgresql/18/bin/*) ;; *) echo "$b resuelve a '$p'" >&2; exit 1 ;; esac; \
    done; \
    postgres --version | grep -q ' 18\.6'; \
    ldd /usr/lib/postgresql/18/bin/postgres | grep -q 'libxml2'

# Mismo usuario sin privilegios que la imagen oficial (postgres, uid 999). compose fija user 999:999
# en db; init-volumes lo sobrescribe a 0:0 porque solo hace chown/chmod de volúmenes.
USER 999:999
