#!/usr/bin/env bash
# =============================================================================
# Controles de scripts/ops/post-restore-local.sh (TKT-OPS-008: DEC-AUTO-908, CHG-DB-003, DEC-AUTO-1203).
# Sustituye "docker" por un doble de prueba que simula compose sin contenedores, para cubrir en segundos
# las ramas que el simulacro real no puede provocar (comando NO_DISPONIBLE, app en marcha...).
#   Uso: bash scripts/ops/post-restore-local_controles.sh        (exit 0 = todos los controles OK)
# =============================================================================
set -Eeuo pipefail
RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="${RAIZ}/scripts/ops/post-restore-local.sh"
TMPD="$(mktemp -d)"
trap 'rm -rf "${TMPD}"' EXIT
mkdir -p "${TMPD}/bin"
# Doble de "docker compose": registra cada llamada en $SHIM_LOG y responde según SHIM_*
cat > "${TMPD}/bin/docker" <<'SHIM'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${SHIM_LOG}"
args=" $* "
case "${args}" in
  *" ps "*)   # antes de cualquier "up": lo que diga el caso; después: todo en marcha (salvo SHIM_OPS_CAIDO)
    if grep -q ' up ' "${SHIM_LOG}"; then
      printf '%s\n' backend frontend proxy; [[ -n "${SHIM_OPS_CAIDO:-}" ]] || printf '%s\n' scheduler backup
    else printf '%s' "${SHIM_EN_MARCHA:-}"; fi
    exit 0 ;;
  *" run "*" migrate "*) echo "  No migrations to apply."; exit 0 ;;
  *" manage.py help --commands "*) printf '  %s\n' check migrate ${SHIM_COMANDOS}; exit 0 ;;
  *" manage.py "*)
    c="$(sed -E 's/.* manage\.py ([a-z_]+).*/\1/' <<< "${args}")"
    if [[ "${c}" == "${SHIM_FALLA:-}" ]]; then
      echo "CommandError: ${c}: FALLO (${SHIM_ERROR:-LIBRO_AUSENTE})" >&2; exit 1
    fi
    v="SHIM_DETALLE_${c}"; echo "${c}: EXITO (${!v:-filas=0})"; exit 0 ;;
  *" up "*) exit 0 ;;
  *" exec "*) echo 200; exit 0 ;;
esac
echo "doble de docker: llamada no prevista: $*" >&2; exit 99
SHIM
chmod +x "${TMPD}/bin/docker"

TODOS="reaplicar_anonimizaciones anonimizar_cuentas purgar_auditoria purgar_sesiones reindexar_busqueda verificar_busqueda"
fallos=0
# caso <nombre> <exit esperado> <regex que DEBE estar en el log de llamadas | -> <regex que NO debe estar | -> <regex en la salida | -> [args...]
caso() {
  local nombre="$1" esperado="$2" si="$3" no="$4" en_salida="$5"; shift 5
  : > "${TMPD}/llamadas.log"
  local rc=0
  SHIM_LOG="${TMPD}/llamadas.log" PATH="${TMPD}/bin:${PATH}" bash "${SCRIPT}" "$@" > "${TMPD}/salida.txt" 2>&1 || rc=$?
  local ok=1
  [[ "${rc}" == "${esperado}" ]] || ok=0
  [[ "${si}" == - ]] || grep -qE -- "${si}" "${TMPD}/llamadas.log" || ok=0
  [[ "${no}" == - ]] || ! grep -qE -- "${no}" "${TMPD}/llamadas.log" || ok=0
  [[ "${en_salida}" == - ]] || grep -qE -- "${en_salida}" "${TMPD}/salida.txt" || ok=0
  if (( ok )); then
    echo "OK   ${nombre} (exit ${rc})"
  else
    echo "FALLO ${nombre}: exit ${rc} (esperado ${esperado})"; sed 's/^/    | /' "${TMPD}/salida.txt"; sed 's/^/    > /' "${TMPD}/llamadas.log"
    fallos=$((fallos + 1))
  fi
}
export RESTORE_ENV=local SHIM_COMANDOS="${TODOS}" SHIM_EN_MARCHA="" SHIM_FALLA=""

caso "C1 completo: 6 comandos, app con --wait y perfil ops sin --wait, exit 0" 0 '--profile ops up -d --no-build scheduler backup' - 'Restauración completa' --confirmar-entorno-local
caso "C2 sin --confirmar-entorno-local -> exit 2, nada se ejecuta" 2 - 'migrate|up ' - --otra-cosa
RESTORE_ENV=prod caso "C3 RESTORE_ENV=prod -> exit 2" 2 - 'migrate|up ' - --confirmar-entorno-local
SHIM_EN_MARCHA=$'backend\nproxy' caso "C4 aplicación en marcha -> exit 2, sin migrate" 2 - 'migrate' 'está en marcha' --confirmar-entorno-local
SHIM_COMANDOS="${TODOS% verificar_busqueda}" caso "C5 (DEC-AUTO-908) falta verificar_busqueda -> exit 5 SIN arrancar" 5 'reindexar_busqueda' ' up ' 'NO se arranca' --confirmar-entorno-local
SHIM_COMANDOS="${TODOS% verificar_busqueda}" caso "C6 falta un comando + --arrancar-incompleto -> arranca y exit 5" 5 ' up -d --wait' - 'arrancó por --arrancar-incompleto' --confirmar-entorno-local --arrancar-incompleto
SHIM_FALLA=reaplicar_anonimizaciones caso "C7 (CHG-DB-003) LIBRO_AUSENTE -> exit 1, se detiene antes de anonimizar_cuentas, sin arrancar" 1 'reaplicar_anonimizaciones' 'anonimizar_cuentas| up ' 'DECISIÓN HUMANA' --confirmar-entorno-local
caso "C8 --libro-vacio-confirmado se pasa a reaplicar_anonimizaciones" 0 'reaplicar_anonimizaciones --libro-vacio-confirmado' 'anonimizar_cuentas --libro' - --confirmar-entorno-local --libro-vacio-confirmado
SHIM_DETALLE_reaplicar_anonimizaciones='desactivadas=0 anonimizadas=0 alineadas=1[7] OMITIDA_ULTIMO_ADMIN=1[3] REACTIVADA_NO_REPRODUCIDA=0 avisos_libro=2' \
  caso "C9 avisos del libro v2 destacados (exit 0)" 0 - - 'AVISO reaplicar_anonimizaciones: OMITIDA_ULTIMO_ADMIN=1\[3\]' --confirmar-entorno-local
caso "C10 --sin-perfil-ops arranca sin el perfil ops" 0 'compose up -d --wait' '--profile ops up' - --confirmar-entorno-local --sin-perfil-ops
SHIM_FALLA=anonimizar_cuentas SHIM_ERROR=LIBRO_CORRUPTO caso "C11 LIBRO_CORRUPTO en anonimizar_cuentas -> exit 1 sin arrancar" 1 'anonimizar_cuentas' 'purgar_auditoria| up ' 'ilegible o corrupto' --confirmar-entorno-local
caso "C12 opción desconocida -> exit 2" 2 - 'migrate' - --confirmar-entorno-local --forzar
SHIM_OPS_CAIDO=1 caso "C13 el perfil ops no queda en marcha -> exit 1" 1 '--profile ops up -d --no-build scheduler backup' - 'perfil ops no quedó en marcha' --confirmar-entorno-local

if (( fallos > 0 )); then echo "${fallos} control(es) FALLIDO(S)"; exit 1; fi
echo "post-restore-local.sh: 13/13 controles OK"
