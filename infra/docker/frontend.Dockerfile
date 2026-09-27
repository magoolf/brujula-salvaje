# syntax=docker/dockerfile:1
# =============================================================================
# Frontend Angular 22 (zoneless) con SSR — servidor Node de @angular/ssr (TKT-F6-001).
#   Contexto de build: ./frontend (código del Developer, F7)
#   Node 24.21.0 LTS "Krypton" (Angular 22.x exige ^22.22.3 || ^24.15.0 || ^26.0.0)
# Archivos que DEBE crear el Developer en frontend/ (DEVOPS_HANDOFF.md §6):
#   package.json (versiones exactas, sin ^/~) + package-lock.json + .npmrc (save-exact=true),
#   angular.json con SSR (outputMode server) y nombre de proyecto = ANGULAR_PROJECT,
#   src/server.ts con GET /healthz y aplicación del nonce recibido en X-CSP-Nonce.
# =============================================================================
ARG NODE_IMAGE=node:24.21.0-trixie-slim@sha256:8ec5d7557396cfe32d21c3f9c13072355ceab22b584578ca4bb28af31120cffe

# ---------------------------------------------------------------------------
# deps: instalación reproducible desde package-lock.json (npm ci falla si no cuadra)
# ---------------------------------------------------------------------------
FROM ${NODE_IMAGE} AS deps
ENV NG_CLI_ANALYTICS=false \
    npm_config_fund=false \
    npm_config_audit=false \
    npm_config_update_notifier=false
WORKDIR /src
COPY package.json package-lock.json .npmrc ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

# ---------------------------------------------------------------------------
# build: ng build (configuración production; genera dist/<proyecto>/{browser,server})
# ---------------------------------------------------------------------------
FROM deps AS build
ARG ANGULAR_PROJECT=brujula-salvaje
COPY . .
RUN npx --no-install ng build --configuration production \
 && test -f "dist/${ANGULAR_PROJECT}/server/server.mjs" \
 && test -d "dist/${ANGULAR_PROJECT}/browser"

# ---------------------------------------------------------------------------
# node-min (TKT-OPS-005, DEC-AUTO-220): la imagen oficial de Node sin gestores de paquetes.
# npm (con sus dependencias vendorizadas: brace-expansion, ip-address, tar -> 4 HIGH con parche),
# npx, corepack y yarn no se usan en ejecución (solo `node dist/server/server.mjs`). Se borran y
# el sistema de archivos se APLANA en una sola capa (FROM scratch + COPY /) para que sus bytes
# tampoco queden en capas inferiores de la imagen. Se re-declaran las ENV de la imagen base.
# ---------------------------------------------------------------------------
FROM ${NODE_IMAGE} AS node-sin-pm
RUN set -eu; \
    rm -rf /usr/local/lib/node_modules \
           /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
           /usr/local/bin/yarn /usr/local/bin/yarnpkg /opt/yarn-v* \
           /usr/local/include/node /root/.npm /tmp/*; \
    for pm in npm npx corepack yarn yarnpkg; do \
      if command -v "$pm" >/dev/null 2>&1; then echo "queda $pm en el runtime" >&2; exit 1; fi; \
    done; \
    node --version

FROM scratch AS node-min
COPY --from=node-sin-pm / /
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    NODE_VERSION=24.21.0

# ---------------------------------------------------------------------------
# runtime: solo el resultado del build (el bundle de servidor de Angular incluye sus
# dependencias); usuario no root "node" (uid 1000) de la imagen oficial.
# ---------------------------------------------------------------------------
FROM node-min AS runtime
ARG ANGULAR_PROJECT=brujula-salvaje
ARG APP_VERSION=0.0.0-dev
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="brujula-frontend" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="STACK_TECNOLOIGICO" \
      org.opencontainers.image.licenses="NOASSERTION"
ENV NODE_ENV=production \
    PORT=4000 \
    APP_VERSION=${APP_VERSION} \
    NG_CLI_ANALYTICS=false
WORKDIR /app
COPY --from=build --chown=root:root /src/dist/${ANGULAR_PROJECT} /app/dist
USER 1000:1000
EXPOSE 4000
HEALTHCHECK --interval=15s --timeout=4s --start-period=20s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:4000/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
CMD ["node", "dist/server/server.mjs"]
