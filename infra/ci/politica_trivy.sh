#!/usr/bin/env bash
# =============================================================================
# Política de excepciones de trivy (RSK-OPS-001). Envoltorio de infra/ci/politica_trivy.py
# (TKT-OPS-006 ciclo 2, DEC-AUTO-256): la política analiza los workflows con un parser YAML y las
# cadenas como shell (continuaciones, comentarios). Ver la cabecera de politica_trivy.py.
# Uso:  bash infra/ci/politica_trivy.sh [RAÍZ]
#       Intérprete: $PYTHON (por defecto python3) con PyYAML instalado.
# =============================================================================
set -euo pipefail
exec "${PYTHON:-python3}" "$(dirname "${BASH_SOURCE[0]}")/politica_trivy.py" "${1:-.}"
