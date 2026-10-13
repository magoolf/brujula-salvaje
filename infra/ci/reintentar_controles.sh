#!/usr/bin/env bash
# Controles de infra/ci/reintentar.sh (TKT-OPS-033): éxito al primer intento, éxito tras fallos,
# fallo definitivo con el código del último intento, y argumentos inválidos.
# Uso:  bash infra/ci/reintentar_controles.sh infra/ci/reintentar.sh
set -uo pipefail
R="${1:?ruta de reintentar.sh}"
t="$(mktemp -d)"; trap 'rm -rf "$t"' EXIT
rc=0
caso() { # nombre rc_esperado intentos_esperados -- comando...
  local n="$1" esp="$2" ie="$3"; shift 3
  : > "$t/cuenta"
  bash "$R" "$@" >/dev/null 2>&1; local got=$?
  local it; it="$(wc -l < "$t/cuenta" | tr -d ' ')"
  if [ "$got" = "$esp" ] && [ "$it" = "$ie" ]; then echo "OK   ${n} (rc=${got}, intentos=${it})"
  else echo "::error::FALLO ${n}: rc=${got} (esperado ${esp}), intentos=${it} (esperados ${ie})"; rc=1; fi
}
# cmd que falla las primeras K veces con código 7
f() { echo "x=\$(wc -l < '$t/cuenta'); echo . >> '$t/cuenta'; [ \"\$x\" -ge $1 ] || exit 7"; }
caso "P1 éxito al primer intento"        0 1 3 0 -- bash -c "$(f 0)"
caso "P2 éxito al tercer intento"        0 3 3 0 -- bash -c "$(f 2)"
caso "N1 agota intentos, conserva rc=7"  7 3 3 0 -- bash -c "$(f 99)"
caso "N2 INTENTOS no numérico"           2 0 x 0 -- bash -c "$(f 0)"
caso "N3 INTENTOS = 0"                   2 0 0 0 -- bash -c "$(f 0)"
caso "N4 sin comando"                    2 0 3 0 --
exit "$rc"
