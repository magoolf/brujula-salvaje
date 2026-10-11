#!/usr/bin/env bash
# =============================================================================
# Reinstalación de los volúmenes de medios y del libro tras restaurar (AC-054; ADR-DB-004 §4)
# TKT-OPS-008: RSK-OPS-027 y DEC-AUTO-1200.
# SOLO local/efímero (Puerta Humana §0.5 para datos reales): exige --confirmar-entorno-local y
# RESTORE_ENV=local.
#
# Se ejecuta en el servicio one-shot "reinstalar-volumenes" (perfil "restauracion" de compose.yaml).
# Usa la imagen brujula/db y corre como root, pero solo con CHOWN, FOWNER y DAC_READ_SEARCH, con
# network_mode none y el rootfs en solo lectura. Monta:
#   /backups (ro)  volumen de copias: en él está el staging que deja restore-local.sh (RESTORE_STAGING_DIR)
#   /vol/media     volumen de medios
#   /vol/ops       volumen del libro de anonimizaciones
#
# Uso:
#   docker compose --profile restauracion run --rm reinstalar-volumenes --confirmar-entorno-local \
#     (--medios | --verificar-medios) [--libro-copia]
#   --medios           pérdida TOTAL del volumen de medios. El volumen debe estar vacío (como mucho, los
#                      directorios publico/ y privado/ vacíos que crea init-volumes). Antes de extraer se
#                      valida el tar del staging: sha256, solo ficheros regulares y directorios, todo de
#                      10001:10001, sin setuid/setgid/sticky, sin rutas absolutas ni "..". Se extrae
#                      conservando propietario, modo y fecha, y después se verifica el manifiesto de la
#                      copia con sha256sum -c --strict
#   --verificar-medios el volumen de medios SOBREVIVIÓ: solo se verifica contra el manifiesto de la copia,
#                      sin escribir nada. Los archivos posteriores a la copia se informan, pero no son error
#   --libro-copia      instala la COPIA del libro (0640, 10001:10001) si NO existe libro vivo. Es una
#                      decisión humana: la copia no conoce los eventos posteriores a su fecha (ADR-DB-004
#                      §4.4 a). Nunca sobrescribe un libro vivo
# Códigos de salida: 0 OK; 2 uso/salvaguarda; 3 el destino no está vacío o ya existe un libro vivo;
#   4 staging incompleto o alterado; 5 el contenido del tar no es aceptable; 1 fallo de verificación.
# =============================================================================
set -Eeuo pipefail
umask 022

uso() { echo "uso: reinstalar-volumenes.sh --confirmar-entorno-local (--medios | --verificar-medios) [--libro-copia]" >&2; exit 2; }
[[ "${1:-}" == "--confirmar-entorno-local" ]] || { echo "Falta --confirmar-entorno-local (Puerta Humana §0.5 para datos reales)" >&2; exit 2; }
shift
[[ "${RESTORE_ENV:-}" == "local" ]] || { echo "RESTORE_ENV debe ser 'local'" >&2; exit 2; }
modo_medios="" libro=0
for a in "$@"; do
  case "$a" in
    --medios|--verificar-medios) [[ -z "${modo_medios}" ]] || uso; modo_medios="$a" ;;
    --libro-copia) libro=1 ;;
    *) uso ;;
  esac
done
[[ -n "${modo_medios}" || "${libro}" == 1 ]] || uso

STAGING="${RESTORE_STAGING_DIR:-/backups/.restauracion}"
MEDIA="${MEDIA_VOL:-/vol/media}"
OPS="${OPS_VOL:-/vol/ops}"
APP_UID=10001
ts() { date -u +%FT%TZ; }
t0=$(date +%s)
# Si algo falla a mitad, los directorios raíz no se quedan de root (init-volumes también lo corrige)
fin() {
  local rc=$?
  if (( rc != 0 )); then
    chown "${APP_UID}:${APP_UID}" "${MEDIA}" "${OPS}" 2>/dev/null || true
    for d in "${MEDIA}/publico" "${MEDIA}/privado"; do [[ -d "$d" ]] && chown "${APP_UID}:${APP_UID}" "$d" 2>/dev/null; done
    echo "reinstalación NO completada (exit ${rc}): la aplicación no debe arrancarse" >&2
  fi
  return "${rc}"
}
trap fin EXIT

[[ -f "${STAGING}/COPIA" ]] || { echo "staging incompleto: falta ${STAGING}/COPIA (¿se ejecutó restore-local.sh con RESTORE_STAGING_DIR?)" >&2; exit 4; }
echo "$(ts) staging de la copia $(cat "${STAGING}/COPIA") en ${STAGING}"

verificar_manifiesto() {   # $1 = --strict (pérdida total) o "" (volumen superviviente)
  local m="${STAGING}/medios.sha256"
  [[ -f "$m" ]] || { echo "staging incompleto: falta medios.sha256" >&2; exit 4; }
  if [[ ! -s "$m" ]]; then
    echo "  manifiesto vacío (la BD no tenía medios al copiar): nada que verificar"
    return 0
  fi
  ( cd "${MEDIA}" && sha256sum -c --quiet --strict "$m" ) || { echo "MANIFIESTO NO VERIFICADO: hay archivos ausentes o alterados en ${MEDIA}" >&2; exit 1; }
  echo "  manifiesto: $(grep -c . "$m") archivos verificados con sha256sum -c en el volumen"
}

case "${modo_medios}" in
  --medios)
    echo "$(ts) [medios] reinstalación tras pérdida total (RSK-OPS-027)"
    for f in medios.tar medios.tar.sha256 medios.sha256; do
      [[ -f "${STAGING}/$f" ]] || { echo "staging incompleto: falta $f" >&2; exit 4; }
    done
    ( cd "${STAGING}" && sha256sum -c --quiet --strict medios.tar.sha256 ) || { echo "medios.tar del staging alterado" >&2; exit 4; }
    # Destino vacío: nada que no sea un directorio (tampoco enlaces) y solo publico/ y privado/
    if [[ -n "$(find "${MEDIA}" -mindepth 1 ! -type d -print -quit)" ]] \
       || [[ -n "$(find "${MEDIA}" -mindepth 1 -type d ! -path "${MEDIA}/publico" ! -path "${MEDIA}/privado" -print -quit)" ]]; then
      echo "El volumen de medios NO está vacío: no se mezclan medios (usar --verificar-medios si sobrevivió)" >&2
      exit 3
    fi
    # Validación del contenido del tar ANTES de extraer: tipos, propietario, bits especiales y rutas
    malas="$(tar --list --verbose --numeric-owner --file="${STAGING}/medios.tar" \
      | awk -v u="${APP_UID}/${APP_UID}" '$1 !~ /^[-d][r-][w-][x-][r-][w-][x-][r-][w-][x-]$/ || $2 != u || / link to / || / -> /' | head -n 5)"
    [[ -z "${malas}" ]] || { printf 'tar con entradas no aceptables (solo ficheros y directorios de %s, sin bits especiales ni enlaces):\n%s\n' "${APP_UID}" "${malas}" >&2; exit 5; }
    rutas="$(tar --list --file="${STAGING}/medios.tar" | grep -E '^/|(^|/)\.\.(/|$)' | head -n 5 || true)"
    [[ -z "${rutas}" ]] || { printf 'tar con rutas absolutas o "..":\n%s\n' "${rutas}" >&2; exit 5; }
    n_tar="$(tar --list --file="${STAGING}/medios.tar" | grep -vc '/$' || true)"
    # root sin DAC_OVERRIDE solo escribe en directorios suyos: se toma la propiedad de los existentes;
    # tar devuelve al final el propietario y el modo del archivo (10001, 0755/0750) a cada directorio
    chown 0:0 "${MEDIA}"
    for d in "${MEDIA}/publico" "${MEDIA}/privado"; do [[ -d "$d" ]] && chown 0:0 "$d"; done
    tar --extract --file="${STAGING}/medios.tar" --directory="${MEDIA}" \
      --same-owner --same-permissions --numeric-owner
    ajenos="$(find "${MEDIA}" \( ! -uid "${APP_UID}" -o ! -gid "${APP_UID}" \) -print -quit)"
    [[ -z "${ajenos}" ]] || { echo "tras extraer quedan entradas que no son de ${APP_UID}: ${ajenos}" >&2; exit 1; }
    n_vol="$(find "${MEDIA}" -type f | wc -l)"
    echo "  extraídos ${n_tar} archivos (en el volumen: ${n_vol}); propietario ${APP_UID}:${APP_UID} y modos de la copia"
    verificar_manifiesto
    ;;
  --verificar-medios)
    echo "$(ts) [medios] verificación del volumen superviviente contra el manifiesto de la copia"
    verificar_manifiesto
    if [[ -s "${STAGING}/medios.sha256" ]]; then
      n_vol="$(find "${MEDIA}" -type f | wc -l)"
      echo "  archivos en el volumen: ${n_vol}; en el manifiesto: $(grep -c . "${STAGING}/medios.sha256") (los de más son posteriores a la copia o derivados huérfanos: no es un error)"
    fi
    ;;
esac

if [[ "${libro}" == 1 ]]; then
  echo "$(ts) [libro] instalación de la COPIA del libro de anonimizaciones (decisión humana, ADR-DB-004 §4.4 a)"
  [[ -f "${STAGING}/libro_anonimizaciones.log" ]] || { echo "la copia no incluye libro: la alternativa es post-restore-local.sh --libro-vacio-confirmado (decisión humana)" >&2; exit 4; }
  if [[ -e "${OPS}/libro_anonimizaciones.log" || -L "${OPS}/libro_anonimizaciones.log" ]]; then
    echo "ya existe un libro VIVO en el volumen (más reciente que la copia): no se sobrescribe" >&2
    exit 3
  fi
  chown 0:0 "${OPS}"
  install -m 0640 -o "${APP_UID}" -g "${APP_UID}" "${STAGING}/libro_anonimizaciones.log" "${OPS}/libro_anonimizaciones.log"
  chown "${APP_UID}:${APP_UID}" "${OPS}"
  chmod 0750 "${OPS}"
  sync
  a="$(sha256sum < "${STAGING}/libro_anonimizaciones.log")"; b="$(sha256sum < "${OPS}/libro_anonimizaciones.log")"
  [[ "$a" == "$b" ]] || { echo "el libro instalado no coincide con la copia" >&2; exit 1; }
  echo "  libro instalado ($(grep -c . "${OPS}/libro_anonimizaciones.log" || true) líneas, 0640 ${APP_UID}:${APP_UID}, sha256 = copia)"
fi

echo "$(ts) reinstalación terminada en $(( $(date +%s) - t0 ))s. Siguiente: post-restore-local.sh (con la aplicación parada)"
