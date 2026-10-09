#!/usr/bin/env bash
# =============================================================================
# Controles del control de receta supercronic (TKT-OPS-031). Uso:
#   bash infra/ci/supercronic_receta_controles.sh infra/ci/supercronic_receta.sh
# P0: el repositorio real pasa. N1..N6: mutaciones sintéticas sobre una copia que DEBEN fallar.
# =============================================================================
set -euo pipefail
script="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
raiz="$(pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
fallos=0
preparar() {
  rm -rf "$tmp/r"; mkdir -p "$tmp/r/infra/backup" "$tmp/r/infra/docker"
  cp "$raiz/infra/backup/Dockerfile" "$tmp/r/infra/backup/Dockerfile"
  cp "$raiz/infra/docker/backend.Dockerfile" "$tmp/r/infra/docker/backend.Dockerfile"
}
caso() { # nombre esperado(0|1) mutación
  preparar
  (cd "$tmp/r" && eval "$3")
  if bash "$script" "$tmp/r" >"$tmp/out" 2>&1; then got=0; else got=1; fi
  if [ "$got" = "$2" ]; then echo "OK   $1"; else echo "FAIL $1 (esperado rc=$2, obtenido rc=$got)"; cat "$tmp/out"; fallos=1; fi
}
caso "P0 repositorio real" 0 ":"
caso "N1 golang distinto en un solo Dockerfile" 1 "sed -i -E 's/^(FROM golang:)[0-9.]+/\\11.26.8/' infra/backup/Dockerfile"
caso "N2 golang sin digest (ambos)" 1 "sed -i -E 's/@sha256:[0-9a-f]{64} AS supercronic/ AS supercronic/' infra/backup/Dockerfile infra/docker/backend.Dockerfile"
caso "N3 commit no SHA (ambos)" 1 "sed -i -E 's/^ARG SUPERCRONIC_COMMIT=.*/ARG SUPERCRONIC_COMMIT=v0.2.49/' infra/backup/Dockerfile infra/docker/backend.Dockerfile"
caso "N4 sin marcador de fin" 1 "sed -i '/^# <<< receta supercronic/d' infra/docker/backend.Dockerfile"
caso "N5 vuelve el binario descargado" 1 "printf 'ADD https://github.com/aptible/supercronic/releases/download/v0.2.49/supercronic-linux-amd64 /usr/local/bin/supercronic\n' >> infra/backup/Dockerfile"
caso "N6 no copia el binario compilado" 1 "sed -i '/^COPY --from=supercronic .*\/usr\/local\/bin\/supercronic$/d' infra/docker/backend.Dockerfile"
exit $fallos
