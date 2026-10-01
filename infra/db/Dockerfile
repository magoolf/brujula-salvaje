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
# -----------------------------------------------------------------------------------------------
# TKT-OPS-014: DSA-6531-1 ya publicado en trixie-security para openssl/libssl3t64/
# openssl-provider-legacy (corrige CVE-2026-84782 -- DTLS info disclosure -- y CVE-2026-75804 --
# QUIC DoS --, ambos HIGH). Sustituye a TKT-OPS-013 (que proponía aceptar el riesgo vía
# .trivyignore; se rechazó porque el parche ya existe: cero excepciones para CVE con fix real).
# apt-get update/download son la ÚNICA parte de este Dockerfile que necesita red durante el build
# (el resto opera solo sobre dpkg local); versión fijada explícita en la descarga (REGLA 3, cero
# versiones ambiguas) para que el build siga siendo reproducible y no arrastre silenciosamente
# futuras revisiones de paquete. Se usa "apt-get download" + "dpkg --force-depends -i" en vez de
# "apt-get install": el purge de perl con --force-depends (arriba) ya deja postgresql-common,
# postgresql-client-common y libjson-perl con la dependencia perl:any sin satisfacer a propósito
# (imagen final, nadie instala paquetes encima); el solver de apt-get install se niega a operar
# con ese estado aunque no toque esos paquetes, mismo patrón --force-depends que ya usa este
# Dockerfile para el purge.
# TKT-OPS-017: mismo patron (apt-get download + dpkg --force-depends -i, version fijada) para
# libpcre2-8-0 (CVE-2026-103111 HIGH en 10.46-1~deb13u2, corregida en 10.46-1~deb13u3 de
# trixie-security). A 2026-10-01 el digest publicado de postgres:18.6-trixie no ha cambiado.
# =============================================================================
# Imagen base LITERAL en FROM (sin ARG): Dependabot (ecosistema docker) no resuelve ARG en FROM y
# no vería el digest (TKT-OPS-006, RSK-OPS-025, DEC-AUTO-254). Actualizar tag y digest juntos.
FROM postgres:18.6-trixie@sha256:5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722

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
    # DSA-6531-1 (TKT-OPS-014): actualiza openssl/libssl3t64/openssl-provider-legacy a la version
    # parcheada de trixie-security, version fijada explicitamente (no flotante).
    apt-get update; \
    ( cd /tmp && \
      apt-get download \
        openssl=3.5.7-1~deb13u3 \
        libssl3t64=3.5.7-1~deb13u3 \
        openssl-provider-legacy=3.5.7-1~deb13u3 \
        libpcre2-8-0=10.46-1~deb13u3 && \
      dpkg --force-depends -i \
        openssl_3.5.7-1~deb13u3_amd64.deb \
        libssl3t64_3.5.7-1~deb13u3_amd64.deb \
        openssl-provider-legacy_3.5.7-1~deb13u3_amd64.deb \
        libpcre2-8-0_10.46-1~deb13u3_amd64.deb && \
      rm -f ./*.deb ); \
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
    ldd /usr/lib/postgresql/18/bin/postgres | grep -q 'libxml2'; \
    for p in openssl libssl3t64 openssl-provider-legacy; do \
      v="$(dpkg-query -W -f='${Version}' "$p")"; \
      case "$v" in 3.5.7-1~deb13u3) ;; *) echo "$p en version inesperada '$v'" >&2; exit 1 ;; esac; \
    done; \
    v="$(dpkg-query -W -f='${Version}' libpcre2-8-0)"; \
    case "$v" in 10.46-1~deb13u3) ;; *) echo "libpcre2-8-0 en version inesperada '$v'" >&2; exit 1 ;; esac

# Mismo usuario sin privilegios que la imagen oficial (postgres, uid 999). compose fija user 999:999
# en db; init-volumes lo sobrescribe a 0:0 porque solo hace chown/chmod de volúmenes.
USER 999:999
