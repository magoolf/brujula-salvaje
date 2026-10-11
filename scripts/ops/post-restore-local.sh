#!/usr/bin/env bash
# =============================================================================
# Pasos de APLICACIÓN tras restore-local.sh (simulacro AC-054; ADR-DB-004 §4) — TKT-OPS-007, TKT-OPS-008
# SOLO local/efímero (Puerta Humana §0.5 para datos reales): exige --confirmar-entorno-local y
# RESTORE_ENV=local. Se ejecuta desde la raíz del repo, en el HOST (usa docker compose).
# Proyecto/entorno de compose con las variables estándar: COMPOSE_PROJECT_NAME, COMPOSE_ENV_FILES
# (o el .env de la raíz), COMPOSE_FILE. Runbook: docs/05_operacion/DEVOPS_HANDOFF.md §35.6.
#
# Uso: post-restore-local.sh --confirmar-entorno-local [--libro-vacio-confirmado] [--sin-perfil-ops]
#                                                      [--arrancar-incompleto]
#   --libro-vacio-confirmado  se pasa a reaplicar_anonimizaciones. Instalación SIN eventos: no falla con
#                             LIBRO_AUSENTE. Es una decisión humana (ADR-DB-004 §4.4 b)
#   --sin-perfil-ops          arranca solo la aplicación. Por defecto también el perfil "ops" (scheduler +
#                             backup), que el runbook paró con "--profile ops down": sin él no habría copias
#                             ni tareas programadas después de restaurar (DEC-AUTO-1203)
#   --arrancar-incompleto     arranca la aplicación aunque falte algún comando (NO_DISPONIBLE). Aun así el
#                             script termina con exit 5. Sin esta opción la aplicación NO se arranca
#                             (DEC-AUTO-908, NV-QAOPS007-01)
#
# Orden (con la aplicación PARADA = "panel cerrado"):
#   1. migrate (app_migrator): lleva el esquema restaurado a la versión del código
#   2. comandos de gestión (app_rw, imagen scheduler), en este orden, deteniéndose en el primero que falle:
#      reaplicar_anonimizaciones -> anonimizar_cuentas -> purgar_auditoria -> purgar_sesiones
#      -> reindexar_busqueda -> verificar_busqueda
#   3. SOLO si los 6 pasos se ejecutaron: arranque de la aplicación (up --wait) y /health/ready = 200
# Un comando que EXISTE y falla detiene el script (exit 1) sin arrancar nada. Un comando que el backend
# no implementa se marca NO_DISPONIBLE, el resto continúa y el script termina con exit 5 SIN arrancar
# la aplicación (salvo --arrancar-incompleto). Nunca se da por bueno un paso no ejecutado.
# Avisos de la relectura del libro v2 (CHG-DB-003; ADR-DB-004 §4.4): OMITIDA_ULTIMO_ADMIN, INCONSISTENTE,
# REACTIVADA_NO_REPRODUCIDA y avisos_libro (líneas ignoradas) no detienen nada (exit 0 del comando),
# pero se destacan en el resumen como AVISO y deben revisarse y adjuntarse a la evidencia.
# Códigos de salida: 0 completo; 1 fallo de un paso; 2 salvaguarda/uso; 5 pasos NO_DISPONIBLE.
# =============================================================================
set -Eeuo pipefail

[[ "${1:-}" == "--confirmar-entorno-local" ]] || { echo "Falta --confirmar-entorno-local (Puerta Humana §0.5 para datos reales)" >&2; exit 2; }
shift
[[ "${RESTORE_ENV:-}" == "local" ]] || { echo "RESTORE_ENV debe ser 'local'" >&2; exit 2; }
libro_vacio=0 perfil_ops=1 arrancar_incompleto=0
for a in "$@"; do
  case "$a" in
    --libro-vacio-confirmado) libro_vacio=1 ;;
    --sin-perfil-ops) perfil_ops=0 ;;
    --arrancar-incompleto) arrancar_incompleto=1 ;;
    *) echo "opción desconocida: $a" >&2; exit 2 ;;
  esac
done
cd "$(dirname "$0")/../.."

DC=(docker compose)
ts() { date -u +%FT%TZ; }
COMANDOS=(reaplicar_anonimizaciones anonimizar_cuentas purgar_auditoria purgar_sesiones reindexar_busqueda verificar_busqueda)
declare -a RESUMEN=() AVISOS=()
t_ini=$(date +%s)

# Panel cerrado: la aplicación no puede estar sirviendo mientras se reaplican anonimizaciones
en_marcha="$("${DC[@]}" --profile ops ps --status running --services 2>/dev/null | grep -Ex 'backend|frontend|proxy|scheduler' || true)"
if [[ -n "${en_marcha}" ]]; then
  echo "La aplicación está en marcha (${en_marcha//$'\n'/, }). Pararla antes: docker compose stop proxy frontend backend scheduler" >&2
  exit 2
fi

echo "$(ts) [1/3] migrate (app_migrator)"
t=$(date +%s)
salida_migrate="$("${DC[@]}" run --rm --no-deps -T migrate 2>&1)" || { printf '%s\n' "${salida_migrate}" >&2; echo "migrate FALLÓ: la aplicación NO se arranca" >&2; exit 1; }
printf '%s\n' "${salida_migrate}" | tail -n 5
if grep -q 'No migrations to apply' <<< "${salida_migrate}"; then
  RESUMEN+=("migrate: OK, sin migraciones pendientes (copia al día con el código) $(( $(date +%s) - t ))s")
else
  RESUMEN+=("migrate: OK, se aplicaron migraciones (copia anterior al código) $(( $(date +%s) - t ))s")
fi

echo "$(ts) [2/3] comandos de gestión (ADR-DB-004 §4)"
disponibles="$("${DC[@]}" --profile ops run --rm --no-deps -T scheduler python manage.py help --commands 2>&1)" \
  || { printf '%s\n' "${disponibles}" >&2; echo "no se pudo listar los comandos de gestión: la aplicación NO se arranca" >&2; exit 1; }
disponibles="$(tr -d '\r' <<< "${disponibles}" | sed 's/^[[:space:]]*//')"
faltan=0
for c in "${COMANDOS[@]}"; do
  if ! grep -qx "${c}" <<< "${disponibles}"; then
    echo "  ${c}: NO_DISPONIBLE (el backend no implementa el comando; paso NO ejecutado)" >&2
    RESUMEN+=("${c}: NO_DISPONIBLE (NOT_RUN)")
    faltan=$((faltan + 1))
    continue
  fi
  args=()
  [[ "${c}" == reaplicar_anonimizaciones && "${libro_vacio}" == 1 ]] && args+=(--libro-vacio-confirmado)
  t=$(date +%s)
  echo "  ${c} ${args[*]:-}"
  rc=0
  salida="$("${DC[@]}" --profile ops run --rm --no-deps -T scheduler python manage.py "${c}" "${args[@]}" 2>&1)" || rc=$?
  salida="$(tr -d '\r' <<< "${salida}")"
  printf '%s\n' "${salida}" | sed 's/^/    /'
  if (( rc != 0 )); then
    echo "  ${c}: FALLO (exit ${rc}) -> restauración NO completada; la aplicación NO se arranca" >&2
    if grep -q 'LIBRO_AUSENTE' <<< "${salida}"; then
      cat >&2 <<'EOF'
  LIBRO_AUSENTE (ADR-DB-004 §4.4): no hay libro de anonimizaciones en el volumen ops_libro. Continuar exige
  una DECISIÓN HUMANA (sobre datos reales, Puerta Humana §0.5):
    (a) instalar la copia del libro de la copia restaurada (no conoce los eventos posteriores a su fecha):
        docker compose --profile restauracion run --rm reinstalar-volumenes --confirmar-entorno-local --libro-copia
    (b) instalación sin eventos: repetir con --libro-vacio-confirmado
EOF
    elif grep -qE 'LIBRO_(ILEGIBLE|CORRUPTO)' <<< "${salida}"; then
      echo "  libro ilegible o corrupto (ADR-DB-004 §4.4/§4.5): revisar permisos (0640, 10001) y las líneas indicadas; no se aplicó ninguna línea" >&2
    fi
    exit 1
  fi
  RESUMEN+=("${c}: OK $(( $(date +%s) - t ))s")
  # Avisos de la relectura (libro v2): exit 0 del comando, pero hay que revisarlos
  if [[ "${c}" == reaplicar_anonimizaciones || "${c}" == anonimizar_cuentas ]]; then
    while IFS= read -r aviso; do
      [[ -n "${aviso}" ]] && AVISOS+=("${c}: ${aviso}")
    done < <(grep -oE '(OMITIDA_ULTIMO_ADMIN|INCONSISTENTE|REACTIVADA_NO_REPRODUCIDA|OMITIDA_REACTIVADA|avisos_libro)=[1-9][0-9]*(\[[^]]*\])?|LIBRO_AUSENTE_SOLO_BD' <<< "${salida}" || true)
  fi
done

if (( faltan > 0 && arrancar_incompleto == 0 )); then
  echo "$(ts) resumen (total $(( $(date +%s) - t_ini ))s):"
  printf '  - %s\n' "${RESUMEN[@]}"
  echo "RESTAURACIÓN INCOMPLETA: ${faltan} paso(s) de ADR-DB-004 §4 NO_DISPONIBLE. La aplicación NO se arranca (DEC-AUTO-908). Con --arrancar-incompleto se arranca igualmente (exit 5)." >&2
  exit 5
fi

perfiles=()
(( perfil_ops == 1 )) && perfiles=(--profile ops)
echo "$(ts) [3/3] arranque de la aplicación${perfiles[*]:+ (+ perfil ops)} y /health/ready"
t=$(date +%s)
# --no-build: se arrancan las imágenes que ya existen; restaurar no reconstruye desde el árbol de trabajo
"${DC[@]}" up -d --wait --no-build
codigo="$("${DC[@]}" exec -T backend python -c "import urllib.request,urllib.error
try:
    print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5).status)
except urllib.error.HTTPError as e:
    print(e.code)" | tr -d '\r')"
[[ "${codigo}" == 200 ]] || { echo "/health/ready respondió ${codigo}" >&2; exit 1; }
if (( perfil_ops == 1 )); then
  # scheduler y backup no tienen healthcheck (HEALTHCHECK NONE): sin --wait, que en algunas versiones de
  # compose falla con "has no healthcheck configured"; se exige después que ambos estén en marcha.
  "${DC[@]}" --profile ops up -d --no-build scheduler backup
  ops_en_marcha="$("${DC[@]}" --profile ops ps --status running --services 2>/dev/null | grep -Ex 'scheduler|backup' | sort | tr '\n' ' ' || true)"
  [[ "${ops_en_marcha}" == "backup scheduler " ]] || { echo "el perfil ops no quedó en marcha (en marcha: '${ops_en_marcha}')" >&2; exit 1; }
fi
RESUMEN+=("arranque${perfiles[*]:+ (+ perfil ops)} + /health/ready: 200 $(( $(date +%s) - t ))s")

echo "$(ts) resumen (total $(( $(date +%s) - t_ini ))s):"
printf '  - %s\n' "${RESUMEN[@]}"
if (( ${#AVISOS[@]} > 0 )); then
  echo "AVISOS de la relectura del libro (ADR-DB-004 §4.4; revisar y adjuntar a la evidencia del simulacro):"
  printf '  - AVISO %s\n' "${AVISOS[@]}"
else
  echo "Sin avisos de la relectura del libro."
fi
if (( faltan > 0 )); then
  echo "RESTAURACIÓN INCOMPLETA: ${faltan} paso(s) NO_DISPONIBLE; la aplicación se arrancó por --arrancar-incompleto." >&2
  exit 5
fi
echo "Restauración completa (ADR-DB-004 §4)."
