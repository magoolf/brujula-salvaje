#!/usr/bin/env bash
# =============================================================================
# Espejo de Docker Hub para el Docker Engine del runner de CI (TKT-OPS-033, DEC-AUTO-989).
# Uso:  bash infra/ci/espejo_registro.sh
# Desde el 2026-10-09 auth.docker.io devuelve 429 (límite anónimo) y 504 a los runners de GitHub y
# el build falla ya al resolver el frontend "# syntax=docker/dockerfile:1". Sin credenciales nuevas
# (autenticarse en Docker Hub exige un secreto: Puerta Humana, CLAUDE.md §0.5), se configura
# "registry-mirrors" en el daemon con mirror.gcr.io (espejo público y anónimo de Docker Hub de
# Google). Afecta SOLO a referencias docker.io (imágenes base, frontend de sintaxis y moby/buildkit
# de setup-buildx-action); ghcr.io/astral-sh/uv no cambia. Las referencias FROM NO se tocan: siguen
# siendo docker.io literales con el MISMO digest (contenido direccionado: el espejo no puede servir
# otro contenido para un digest fijado) y Dependabot las sigue entendiendo. Si el espejo falla, el
# Engine y BuildKit vuelven solos a registry-1.docker.io (degradación al comportamiento anterior).
# Fusiona con el daemon.json existente del runner (no lo reemplaza), reinicia el Engine y verifica.
# Variable opcional: ESPEJO_REGISTRO (por defecto https://mirror.gcr.io).
# =============================================================================
set -euo pipefail
espejo="${ESPEJO_REGISTRO:-https://mirror.gcr.io}"
[[ "$espejo" =~ ^https://[a-z0-9.-]+$ ]] || { echo "::error::ESPEJO_REGISTRO inválido: ${espejo}"; exit 2; }
cfg=/etc/docker/daemon.json
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
if sudo test -s "$cfg"; then sudo cat "$cfg" > "$tmp/actual.json"; else echo '{}' > "$tmp/actual.json"; fi
# El espejo queda el PRIMERO de la lista y sin duplicados; el resto de claves del runner se conserva.
jq --arg m "$espejo" '."registry-mirrors" = ([$m] + ((."registry-mirrors" // []) - [$m]))' \
  "$tmp/actual.json" > "$tmp/nuevo.json"
echo "daemon.json resultante:"; cat "$tmp/nuevo.json"
sudo install -m 0644 "$tmp/nuevo.json" "$cfg"
sudo systemctl restart docker
listo=0
for _ in $(seq 1 30); do
  if docker info >/dev/null 2>&1; then listo=1; break; fi
  sleep 1
done
[ "$listo" = 1 ] || { echo "::error::el Docker Engine no volvió tras reiniciarlo"; exit 1; }
espejos="$(docker info --format '{{json .RegistryConfig.Mirrors}}')"
echo "registry-mirrors activos: ${espejos}"
grep -qF "\"${espejo%/}/\"" <<<"$espejos" || grep -qF "\"${espejo%/}\"" <<<"$espejos" \
  || { echo "::error::el Engine no informa del espejo ${espejo}"; exit 1; }
