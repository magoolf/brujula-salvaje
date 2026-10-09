#!/usr/bin/env bash
# =============================================================================
# Controles de infra/ci/enmascarar_env.sh (TKT-OPS-027, F-QA022-04 de la QA de TKT-OPS-022).
# Uso:  bash infra/ci/enmascarar_env_controles.sh [ENMASCARAR_SH] [INIT_ENV_SH] [ENV_EXAMPLE]
#       (por defecto: infra/ci/enmascarar_env.sh, scripts/ops/init-env.sh y .env.example del repo)
# Sale 1 si algún control no da el resultado esperado (exit y salida).
#   P1 .env real de init-env.sh + --plantilla .env.example -> 0 y TODOS los valores que init-env.sh
#      generó desde CHANGE_ME/CHANGE_ME_FERNET aparecen como ::add-mask:: (los cuenta y compara)
#   P2 invocación antigua (sin --plantilla, 4 obligatorias explícitas) -> 0
#   P3 plantilla con CRLF -> 0 y enmascara igual
#   N1 variable CHANGE_ME de la plantilla SIN sufijo de secreto (OTRO_VALOR) -> 0 y su valor
#      enmascarado (control negativo del hueco F-QA022-04: el script anterior la dejaba en claro)
#   N2 variable CHANGE_ME de la plantilla ausente del .env -> 1
#   N3 variable CHANGE_ME de la plantilla vacía en el .env -> 1
#   N4 plantilla inexistente -> 1           N5 plantilla sin ningún CHANGE_ME -> 1
#   N6 .env inexistente -> 1                N7 obligatoria explícita ausente -> 1
# Los valores son aleatorios por ejecución, no secretos reales (CLAUDE.md §0.5).
# =============================================================================
set -uo pipefail
raiz="$(cd "$(dirname "$0")/../.." && pwd)"
script="${1:-${raiz}/infra/ci/enmascarar_env.sh}"
init_env="${2:-${raiz}/scripts/ops/init-env.sh}"
example="${3:-${raiz}/.env.example}"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

total=0
fallos=0
caso() { # nombre exit_esperado patron_esperado -- comando...
  local nombre="$1" esperado="$2" patron="$3"
  shift 4
  local salida rc
  salida="$("$@" 2>&1)"
  rc=$?
  total=$((total + 1))
  if [ "$rc" -eq "$esperado" ] && grep -qE -- "$patron" <<<"$salida"; then
    echo "OK   ${nombre}: exit ${rc} (esperado ${esperado})"
  else
    fallos=$((fallos + 1))
    echo "MAL  ${nombre}: exit ${rc} (esperado ${esperado}) / falta: ${patron}"
    sed 's/^::add-mask::.*/::add-mask::<omitido>/' <<<"$salida"
  fi
}

# --- P1: el .env REAL que genera init-env.sh a partir de la plantilla REAL ---
bash "$init_env" "${tmp}/p1.env" >/dev/null
salida_p1="$(bash "$script" "${tmp}/p1.env" --plantilla "$example" 2>&1)"
rc_p1=$?
generadas=0
sin_mascara=()
while IFS= read -r linea || [ -n "$linea" ]; do
  linea="${linea%$'\r'}"
  case "${linea}" in
    *=CHANGE_ME_FERNET|*=CHANGE_ME)
      nombre="${linea%%=*}"
      generadas=$((generadas + 1))
      valor="$(grep -m1 "^${nombre}=" "${tmp}/p1.env" | cut -d= -f2-)"
      if [ -z "$valor" ] || ! grep -qxF "::add-mask::${valor}" <<<"$salida_p1"; then
        sin_mascara+=("$nombre")
      fi
      ;;
  esac
done < "$example"
total=$((total + 1))
if [ "$rc_p1" -eq 0 ] && [ "$generadas" -gt 0 ] && [ "${#sin_mascara[@]}" -eq 0 ]; then
  echo "OK   P1 init-env.sh real + --plantilla: exit 0, ${generadas}/${generadas} valores generados enmascarados"
else
  fallos=$((fallos + 1))
  echo "MAL  P1 init-env.sh real + --plantilla: exit ${rc_p1}, generadas ${generadas}, sin máscara: ${sin_mascara[*]:-}"
  sed 's/^::add-mask::.*/::add-mask::<omitido>/' <<<"$salida_p1"
fi

caso "P2 invocación antigua (4 obligatorias)" 0 "obligatorias \(4\)" -- \
  bash "$script" "${tmp}/p1.env" DJANGO_SECRET_KEY THROTTLE_HMAC_KEY MFA_FERNET_KEY APP_MIGRATOR_PASSWORD

# --- Sintéticos ---
printf 'A_PASSWORD=CHANGE_ME\r\nOTRO_VALOR=CHANGE_ME_FERNET\r\nPUBLICO=hola\r\n' >"${tmp}/crlf.example"
printf 'A_PASSWORD=aaaa1111\nOTRO_VALOR=bbbb2222\nPUBLICO=hola\n' >"${tmp}/ok.env"
caso "P3 plantilla con CRLF" 0 "^::add-mask::bbbb2222$" -- \
  bash "$script" "${tmp}/ok.env" --plantilla "${tmp}/crlf.example"

printf 'A_PASSWORD=CHANGE_ME\nOTRO_VALOR=CHANGE_ME\nPUBLICO=hola\n' >"${tmp}/s.example"
caso "N1 CHANGE_ME sin sufijo de secreto se enmascara" 0 "^::add-mask::bbbb2222$" -- \
  bash "$script" "${tmp}/ok.env" --plantilla "${tmp}/s.example"

printf 'A_PASSWORD=aaaa1111\nPUBLICO=hola\n' >"${tmp}/falta.env"
caso "N2 CHANGE_ME de la plantilla ausente del .env" 1 "OTRO_VALOR falta o está vacía" -- \
  bash "$script" "${tmp}/falta.env" --plantilla "${tmp}/s.example"

printf 'A_PASSWORD=aaaa1111\nOTRO_VALOR=\nPUBLICO=hola\n' >"${tmp}/vacia.env"
caso "N3 CHANGE_ME de la plantilla vacía en el .env" 1 "OTRO_VALOR falta o está vacía" -- \
  bash "$script" "${tmp}/vacia.env" --plantilla "${tmp}/s.example"

caso "N4 plantilla inexistente" 1 "no existe la plantilla" -- \
  bash "$script" "${tmp}/ok.env" --plantilla "${tmp}/no-existe.example"

printf 'PUBLICO=hola\n# X=CHANGE_ME_NO\n' >"${tmp}/sin.example"
caso "N5 plantilla sin CHANGE_ME" 1 "no declara ninguna variable CHANGE_ME" -- \
  bash "$script" "${tmp}/ok.env" --plantilla "${tmp}/sin.example"

caso "N6 .env inexistente" 1 "no existe .*no-existe.env" -- \
  bash "$script" "${tmp}/no-existe.env" --plantilla "${tmp}/s.example"

caso "N7 obligatoria explícita ausente" 1 "FALTA_KEY falta o está vacía" -- \
  bash "$script" "${tmp}/ok.env" --plantilla "${tmp}/s.example" FALTA_KEY

echo "controles de enmascarar_env: $((total - fallos))/${total} correctos"
[ "$fallos" -eq 0 ]
