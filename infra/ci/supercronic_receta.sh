#!/usr/bin/env bash
# =============================================================================
# Receta ÚNICA de supercronic (TKT-OPS-031, DEC-AUTO-979).
# Uso:  bash infra/ci/supercronic_receta.sh [RAÍZ]
# supercronic se compila desde el fuente (Go corregido, CVE-2026-78667) en una etapa "supercronic"
# que va COPIADA en infra/backup/Dockerfile e infra/docker/backend.Dockerfile (contextos de build
# distintos: no pueden compartir etapa). Este control garantiza que ambas copias son la MISMA receta:
#   - el bloque entre "# >>> receta supercronic" y "# <<< receta supercronic" existe una sola vez en
#     cada Dockerfile y es idéntico byte a byte (una actualización de Dependabot o manual que toque solo
#     uno de los dos falla aquí);
#   - el FROM de la etapa es una imagen golang con tag exacto y digest sha256;
#   - SUPERCRONIC_COMMIT es un SHA de 40 hex y no queda ningún binario descargado (ADD/curl/wget
#     de releases de supercronic) en ninguno de los dos.
# =============================================================================
set -euo pipefail
cd "${1:-.}"
archivos=(infra/backup/Dockerfile infra/docker/backend.Dockerfile)
rc=0
bloque() { awk '/^# >>> receta supercronic/{d=1} d{print} /^# <<< receta supercronic/{d=0}' "$1"; }
ref=""
for f in "${archivos[@]}"; do
  [ -f "$f" ] || { echo "::error::falta ${f}"; rc=1; continue; }
  ini="$(grep -c '^# >>> receta supercronic' "$f" || true)"
  fin="$(grep -c '^# <<< receta supercronic' "$f" || true)"
  if [ "$ini" != 1 ] || [ "$fin" != 1 ]; then
    echo "::error::${f}: marcadores de la receta supercronic: inicio=${ini} fin=${fin} (se espera 1 y 1)"; rc=1; continue
  fi
  b="$(bloque "$f")"
  grep -qE '^FROM golang:[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9]+)?@sha256:[0-9a-f]{64} AS supercronic$' <<<"$b" \
    || { echo "::error::${f}: la etapa supercronic debe ser 'FROM golang:X.Y.Z[-variante]@sha256:<digest> AS supercronic'"; rc=1; }
  grep -qE '^ARG SUPERCRONIC_COMMIT=[0-9a-f]{40}$' <<<"$b" \
    || { echo "::error::${f}: SUPERCRONIC_COMMIT debe ser un SHA de commit de 40 hex"; rc=1; }
  if grep -nE 'supercronic/releases/download|(curl|wget)[^#]*supercronic' "$f"; then
    echo "::error::${f}: supercronic debe compilarse con la receta, no descargarse"; rc=1
  fi
  grep -qE '^COPY --from=supercronic .*/out/supercronic /usr/local/bin/supercronic$' "$f" \
    || { echo "::error::${f}: falta 'COPY --from=supercronic ... /out/supercronic /usr/local/bin/supercronic'"; rc=1; }
  if [ -z "$ref" ]; then ref="$b"; refa="$f"
  elif [ "$b" != "$ref" ]; then
    echo "::error::la receta supercronic difiere entre ${refa} y ${f}:"
    diff <(printf '%s\n' "$ref") <(printf '%s\n' "$b") || true
    rc=1
  fi
done
[ "$rc" = 0 ] && echo "receta supercronic: idéntica en ${archivos[*]}"
exit $rc
