#!/usr/bin/env bash
# =============================================================================
# Pasos de APLICACIÓN tras restore-local.sh (simulacro AC-054; ADR-DB-004 §4) — TKT-OPS-007
# SOLO local/efímero (Puerta Humana §0.5 para datos reales): exige --confirmar-entorno-local y
# RESTORE_ENV=local. Se ejecuta desde la raíz del repo, en el HOST (usa docker compose).
# Proyecto/entorno de compose con las variables estándar: COMPOSE_PROJECT_NAME, COMPOSE_ENV_FILES
# (o el .env de la raíz), COMPOSE_FILE. Runbook: docs/05_operacion/DEVOPS_HANDOFF.md §18.9.
#
# Orden (con la aplicación PARADA = "panel cerrado"):
#   1. migrate (app_migrator): lleva el esquema restaurado a la versión del código
#   2. comandos de gestión (app_rw, imagen scheduler), en este orden:
#      reaplicar_anonimizaciones -> anonimizar_cuentas -> purgar_auditoria -> purgar_sesiones
#      -> reindexar_busqueda -> verificar_busqueda
#   3. arranque de la aplicación (up --wait) y /health/ready = 200
# Un comando que EXISTE y falla detiene el script (exit 1). Un comando que el backend todavía
# NO implementa (F7) se marca NO_DISPONIBLE, el resto continúa y el script termina con exit 5:
# la restauración NO está completa (DEC-AUTO-241). Nunca se da por bueno un paso no ejecutado.
# Códigos de salida: 0 completo; 1 fallo de un paso; 2 salvaguarda/uso; 5 pasos NO_DISPONIBLE.
# =============================================================================
set -Eeuo pipefail

[[ "${1:-}" == "--confirmar-entorno-local" ]] || { echo "Falta --confirmar-entorno-local (Puerta Humana §0.5 para datos reales)" >&2; exit 2; }
[[ "${RESTORE_ENV:-}" == "local" ]] || { echo "RESTORE_ENV debe ser 'local'" >&2; exit 2; }
cd "$(dirname "$0")/../.."

DC=(docker compose)
ts() { date -u +%FT%TZ; }
COMANDOS=(reaplicar_anonimizaciones anonimizar_cuentas purgar_auditoria purgar_sesiones reindexar_busqueda verificar_busqueda)
declare -a RESUMEN=()
t_ini=$(date +%s)

# Panel cerrado: la aplicación no puede estar sirviendo mientras se reaplican anonimizaciones
en_marcha="$("${DC[@]}" --profile ops ps --status running --services 2>/dev/null | grep -Ex 'backend|frontend|proxy|scheduler' || true)"
if [[ -n "${en_marcha}" ]]; then
  echo "La aplicación está en marcha (${en_marcha//$'\n'/, }). Pararla antes: docker compose stop proxy frontend backend scheduler" >&2
  exit 2
fi

echo "$(ts) [1/3] migrate (app_migrator)"
t=$(date +%s)
salida_migrate="$("${DC[@]}" run --rm --no-deps -T migrate 2>&1)" || { printf '%s\n' "${salida_migrate}" >&2; echo "migrate FALLÓ" >&2; exit 1; }
printf '%s\n' "${salida_migrate}" | tail -n 5
if grep -q 'No migrations to apply' <<< "${salida_migrate}"; then
  RESUMEN+=("migrate: OK, sin migraciones pendientes (copia al día con el código) $(( $(date +%s) - t ))s")
else
  RESUMEN+=("migrate: OK, se aplicaron migraciones (copia anterior al código) $(( $(date +%s) - t ))s")
fi

echo "$(ts) [2/3] comandos de gestión (ADR-DB-004 §4)"
disponibles="$("${DC[@]}" --profile ops run --rm --no-deps -T scheduler python manage.py help --commands 2>&1)" \
  || { printf '%s\n' "${disponibles}" >&2; echo "no se pudo listar los comandos de gestión" >&2; exit 1; }
faltan=0
for c in "${COMANDOS[@]}"; do
  if ! grep -qx "${c}" <<< "$(tr -d '\r' <<< "${disponibles}" | sed 's/^[[:space:]]*//')"; then
    echo "  ${c}: NO_DISPONIBLE (el backend aún no implementa el comando; paso NO ejecutado)" >&2
    RESUMEN+=("${c}: NO_DISPONIBLE (NOT_RUN)")
    faltan=$((faltan + 1))
    continue
  fi
  t=$(date +%s)
  echo "  ${c}"
  "${DC[@]}" --profile ops run --rm --no-deps -T scheduler python manage.py "${c}" \
    || { echo "  ${c}: FALLO (exit $?) -> restauración NO completada" >&2; exit 1; }
  RESUMEN+=("${c}: OK $(( $(date +%s) - t ))s")
done

echo "$(ts) [3/3] arranque de la aplicación y /health/ready"
t=$(date +%s)
"${DC[@]}" up -d --wait
codigo="$("${DC[@]}" exec -T backend python -c "import urllib.request,urllib.error
try:
    print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5).status)
except urllib.error.HTTPError as e:
    print(e.code)" | tr -d '\r')"
[[ "${codigo}" == 200 ]] || { echo "/health/ready respondió ${codigo}" >&2; exit 1; }
RESUMEN+=("arranque + /health/ready: 200 $(( $(date +%s) - t ))s")

echo "$(ts) resumen (total $(( $(date +%s) - t_ini ))s):"
printf '  - %s\n' "${RESUMEN[@]}"
if (( faltan > 0 )); then
  echo "RESTAURACIÓN INCOMPLETA: ${faltan} paso(s) de ADR-DB-004 §4 NO_DISPONIBLE. Datos y esquema restaurados; los pasos pendientes deben ejecutarse cuando el backend los implemente." >&2
  exit 5
fi
echo "Restauración completa (ADR-DB-004 §4)."
