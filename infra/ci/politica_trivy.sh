#!/usr/bin/env bash
# =============================================================================
# Política de excepciones de trivy (RSK-OPS-001; decisión humana 2026-09-26, TKT-OPS-005,
# DEC-AUTO-225). Extraída del paso de CI a un script para poder probarla con controles negativos
# (TKT-OPS-006, QA-OPS005-04, DEC-AUTO-252).
#
# Uso:  bash infra/ci/politica_trivy.sh [RAÍZ]      (RAÍZ por defecto: directorio actual)
#       Examina RAÍZ/.trivyignore y RAÍZ/.github/workflows/. Sale 1 si algo incumple la política.
#
# Reglas:
#   - Las únicas excepciones están en .trivyignore: CVE/GHSA sin parche, una por línea, cada una con
#     exp:AAAA-MM-DD (una entrada caducada deja de suprimir y el job vuelve a fallar).
#   - Ninguna vía paralela: trivy.yaml, .trivyignore.yaml, variables TRIVY_* de configuración.
#   - Toda invocación de trivy image/fs/rootfs usa exactamente --severity CRITICAL,HIGH y ninguna de
#     --config/-c, --vex, --ignore-status, --ignore-unfixed, --ignore-policy ni --skip-*.
#   - NUEVO (QA-OPS005-04): antes de buscar, se UNEN las líneas de continuación de shell
#     ("\" + salto de línea), así una opción prohibida en la línea siguiente de la invocación se ve.
# =============================================================================
set -euo pipefail

raiz="${1:-.}"
wf="${raiz}/.github/workflows"
ign="${raiz}/.trivyignore"
fallo() { echo "::error::$*"; exit 1; }

test -f "$ign" || fallo "falta .trivyignore"
test -d "$wf" || fallo "falta ${wf}"

# QA-OPS005-03: ninguna vía alternativa de configurar o suprimir hallazgos de trivy.
otros="$(find "$raiz" -path "${raiz}/.git" -prune -o -type f \( -name 'trivy.yaml' -o -name 'trivy.yml' \
  -o -name '.trivyignore.yaml' -o -name '.trivyignore.yml' \) -print)"
test -z "$otros" || { echo "$otros"; fallo "configuración de trivy no permitida (ver lista)"; }

# Texto de los workflows con las continuaciones "\"+salto unidas (y sin CR). Una línea lógica por
# línea física: una invocación partida en varias líneas se evalúa entera.
unido="$(mktemp)"
trap 'rm -f "$unido"' EXIT
find "$wf" -type f \( -name '*.yaml' -o -name '*.yml' \) -print0 | sort -z | while IFS= read -r -d '' f; do
  tr -d '\r' < "$f" | sed -e ':a' -e '/\\$/{N;s/\\\n[[:space:]]*/ /;ta' -e '}'
done > "$unido"

if grep -nE 'TRIVY_(CONFIG|VEX|SEVERITY|IGNOREFILE|IGNORE_UNFIXED|IGNORE_STATUS|IGNORE_POLICY|SKIP_[A-Z_]*)[[:space:]]*[:=]' "$unido"; then
  fallo "variable TRIVY_* prohibida por RSK-OPS-001"
fi

# Invocaciones reales (no comentarios) de trivy image/fs/rootfs, ya unidas.
invocaciones="$(grep -E '^[^#]*trivy[[:space:]]+(image|fs|rootfs)([[:space:]]|$)' "$unido" || true)"
test -n "$invocaciones" || fallo "no se encontró ninguna invocación de trivy"
while IFS= read -r l; do
  if ! grep -qE -- '--severity CRITICAL,HIGH([[:space:]]|$)' <<<"$l" \
     || grep -qE -- '(--config|[[:space:]]-c[[:space:]]|--vex|--ignore-status)' <<<"$l"; then
    fallo "invocación de trivy fuera de política: $l"
  fi
done <<<"$invocaciones"

# Opciones prohibidas en cualquier invocación (incluida "trivy config"), sobre el texto unido.
if grep -nE '^[^#]*trivy[[:space:]]+(image|fs|rootfs|config)[^#]*--(ignore-unfixed|ignore-policy|skip-(pkgs|files|dirs))' "$unido" \
   || grep -nE 'TRIVY_(IGNORE_UNFIXED|IGNORE_POLICY|SKIP_)[A-Z_]*[[:space:]]*[:=]' "$unido"; then
  fallo "opción de trivy prohibida por RSK-OPS-001"
fi

malas="$(grep -vE '^[[:space:]]*(#|$)' "$ign" | tr -d '\r' \
  | grep -vE '^(CVE-[0-9]{4}-[0-9]{4,}|GHSA(-[23456789cfghjmpqrvwx]{4}){3}) exp:[0-9]{4}-[0-9]{2}-[0-9]{2}$' || true)"
test -z "$malas" || { echo "$malas"; fallo "entradas de .trivyignore fuera de política (ver lista)"; }

hoy="$(date -u +%F)"
grep -oE 'exp:[0-9-]+' "$ign" | cut -d: -f2 | sort -u | while read -r d; do
  if [[ "$d" < "$hoy" ]]; then
    echo "::warning::excepciones de .trivyignore CADUCADAS ($d): trivy las tratará como hallazgos"
  fi
done
echo "política de trivy OK; excepciones vigentes: $(grep -cE '^(CVE|GHSA)-' "$ign" || true)"
