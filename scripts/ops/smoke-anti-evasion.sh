#!/usr/bin/env bash
# =============================================================================
# Smoke anti-evasión del limitador de borde (TKT-OPS-018; ADR-OPS-001, RSK-OPS-040; TKT-OPS-019).
# Comprueba contra el stack de compose YA levantado (proxy + frontend) que:
#   C1  un asset inexistente (/no-existe-<N>.js) da 404 application/problem+json y NO se renderiza en
#       el SSR: Angular lo rechaza por Host ("estaticos.invalid" no permitido) antes de renderizar y no
#       hay ningún error_ssr para esa ruta;
#   C2  una ráfaga de 120 assets estáticos reales no recibe ningún 429 (zona "estaticos");
#   C3  una ráfaga a /api sigue recibiendo 429 Problem Details DEL PROPIO LIMITADOR del proxy (zona
#       "por_ip" intacta; los 429 de DRF no cuentan: se distinguen en el log JSON del proxy);
#   C4  la query de un asset inexistente no llega a los logs del proxy ni del SSR (REQ-057, THREAT-020);
#   C5  NG_ALLOWED_HOSTS (config resuelta de compose y entorno real del contenedor) no contiene "*" ni
#       ningún host ".invalid" (con cualquiera de ellos un asset inexistente volvería a renderizar).
# Ejecuta TODAS las comprobaciones y sale con 1 si alguna falla (diagnóstico completo en una pasada).
# Uso (desde la raíz del repositorio, con las mismas variables de compose que levantaron el stack):
#   bash scripts/ops/smoke-anti-evasion.sh [URL_BASE]     (por defecto http://127.0.0.1:8080)
# Requiere: bash, curl, python3, docker compose. Solo lectura: no modifica el stack.
# =============================================================================
set -Eeuo pipefail
cd "$(dirname "$0")/../.."

B="${1:-http://127.0.0.1:8080}"
N="$(date +%s)$$"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
fallos=0
ok()    { echo "OK    $*"; }
fallo() { echo "::error::FALLO $*"; fallos=$((fallos + 1)); }
logs()  { docker compose logs --no-color --no-log-prefix "$1" 2>&1; }
# Ráfaga concurrente con conexiones keep-alive (como el smoke de /health): rápida y determinista en
# cualquier runner. Uso: rafaga <hilos> <fichero de rutas> -> una línea "<estado> <content-type>" por petición.
rafaga() {
  python3 - "${B}" "$1" "$2" <<'PY'
import concurrent.futures as cf, http.client, sys, urllib.parse
u = urllib.parse.urlsplit(sys.argv[1]); hilos = int(sys.argv[2])
rutas = [r.strip() for r in open(sys.argv[3], encoding="utf-8") if r.strip()]
def tramo(lote):
    c, r = http.client.HTTPConnection(u.hostname, u.port, timeout=15), []
    for ruta in lote:
        try:
            c.request("GET", ruta); resp = c.getresponse(); resp.read()
            r.append(f"{resp.status} {resp.getheader('Content-Type')}")
            cerrar = (resp.getheader("Connection") or "").lower() == "close"
        except OSError as e:  # conexión caída: se registra como fallo, no aborta el smoke
            r.append(f"000 {type(e).__name__}"); cerrar = True
        if cerrar:
            c.close(); c = http.client.HTTPConnection(u.hostname, u.port, timeout=15)
    return r
with cf.ThreadPoolExecutor(hilos) as ex:
    for f in [ex.submit(tramo, rutas[i::hilos]) for i in range(hilos)]:
        for linea in f.result():
            print(linea)
PY
}

# --- C5: NG_ALLOWED_HOSTS ---------------------------------------------------------------------
hosts_peligrosos() {  # imprime las entradas peligrosas de una lista separada por comas
  tr ',' '\n' <<<"$1" | tr -d ' \r' | grep -iE '\*|\.invalid\.?$' || true
}
cfg="$(docker compose config --format json | python3 -c 'import json,sys; print((json.load(sys.stdin)["services"]["frontend"].get("environment") or {}).get("NG_ALLOWED_HOSTS",""))')"
cid="$(docker compose ps -q frontend)"
[[ -n "${cid}" ]] || { echo "::error::el servicio frontend no está en ejecución (¿stack levantado con las mismas variables de compose?)"; exit 1; }
real="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${cid}" | sed -n 's/^NG_ALLOWED_HOSTS=//p')"
echo "NG_ALLOWED_HOSTS: config='${cfg}' contenedor='${real}'"
peligro="$(hosts_peligrosos "${cfg}"; hosts_peligrosos "${real}")"
if [[ -z "${cfg}" || -z "${real}" ]]; then
  fallo "C5 NG_ALLOWED_HOSTS vacío o ausente (se exige una lista explícita de hosts)"
elif [[ -n "${peligro}" ]]; then
  fallo "C5 NG_ALLOWED_HOSTS admite '*' o un host .invalid: $(tr '\n' ' ' <<<"${peligro}")(RSK-OPS-040)"
else
  ok "C5 NG_ALLOWED_HOSTS sin '*' ni hosts .invalid"
fi

sleep 4   # repone el cupo por_ip de los pasos anteriores (20 r/s, burst 60)

# --- C1: asset inexistente -> 404 Problem Details sin render ------------------------------------
ruta="/no-existe-${N}.js"
res="$(curl -s -o "${TMP}/c1.json" -w '%{http_code} %{content_type}' "${B}${ruta}")"
echo "C1 ${ruta} -> ${res}"
sleep 1
logs frontend > "${TMP}/fe.log"
rechazos="$(grep -cF "\"http://estaticos.invalid${ruta}\"" "${TMP}/fe.log" || true)"
errores="$(grep -F '"evento":"error_ssr"' "${TMP}/fe.log" | grep -cF "\"ruta\":\"${ruta}\"" || true)"
codigo="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("code",""))' "${TMP}/c1.json" 2>/dev/null || true)"
if [[ "${res}" == "404 application/problem+json" && "${codigo}" == "no_encontrado" && "${rechazos}" -ge 1 && "${errores}" == 0 ]]; then
  ok "C1 asset inexistente: 404 problem+json, rechazado por Host en el SSR (${rechazos}) y 0 error_ssr"
else
  fallo "C1 asset inexistente: respuesta='${res}' code='${codigo}' rechazos_host_en_ssr=${rechazos} (se exige >=1: sin rechazo, el SSR lo RENDERIZÓ) error_ssr=${errores}"
fi

# --- C4: la query de un asset inexistente no llega a los logs ------------------------------------
token="secreto${N}"
for r in "/no-existe-q${N}.js" "/no-existe-q${N}.css" "/fonts/no-existe-q${N}.woff2" "/media/publico/no-existe-q${N}"; do
  echo "C4 ${r}?${token}=1 -> $(curl -s -o /dev/null -w '%{http_code} %{content_type}' "${B}${r}?${token}=1")"
done
sleep 1
logs frontend > "${TMP}/fe.log"
logs proxy > "${TMP}/px.log"
en_fe="$(grep -c "${token}" "${TMP}/fe.log" || true)"
en_px="$(grep -c "${token}" "${TMP}/px.log" || true)"
llego="$(grep -cF "\"http://estaticos.invalid/no-existe-q${N}.js" "${TMP}/fe.log" || true)"
vistas="$(grep -cF "\"ruta_pedida\":\"/no-existe-q${N}.js\"" "${TMP}/px.log" || true)"
if [[ "${en_fe}" == 0 && "${en_px}" == 0 && "${llego}" -ge 1 && "${vistas}" -ge 1 ]]; then
  ok "C4 query de assets inexistentes: 0 apariciones en los logs del SSR y del proxy (petición registrada sin query)"
else
  fallo "C4 query en logs: SSR=${en_fe} proxy=${en_px} (se exige 0); petición vista en SSR=${llego} y proxy=${vistas} (se exige >=1)"
fi

# --- C2: ráfaga de 120 assets estáticos reales -> 0 respuestas 429 -------------------------------
html="$(curl -fsS "${B}/")"
{ grep -oE '(src|href)="/?[A-Za-z0-9_-]+\.(js|mjs|css)"' <<<"${html}" | sed -E 's/^(src|href)="\/?//; s/"$//'
  grep -oE '/?fonts/[A-Za-z0-9_-]+\.woff2' <<<"${html}" | sed 's#^/##'
  echo favicon.ico; } | sort -u > "${TMP}/assets.txt"
echo "C2 assets reales: $(tr '\n' ' ' < "${TMP}/assets.txt")"
if [[ "$(grep -cE '\.(js|mjs|css)$' "${TMP}/assets.txt")" -lt 1 ]]; then
  fallo "C2 el HTML del SSR no referencia ningún asset JS/CSS"
else
  n_assets="$(wc -l < "${TMP}/assets.txt")"
  for i in $(seq 0 119); do sed -n "$(( i % n_assets + 1 ))s#^#/#p" "${TMP}/assets.txt"; done > "${TMP}/rafaga.txt"
  rafaga 20 "${TMP}/rafaga.txt" | cut -d' ' -f1 > "${TMP}/c2.txt"
  echo "C2 ráfaga de $(wc -l < "${TMP}/c2.txt") assets: $(sort "${TMP}/c2.txt" | uniq -c | tr -s ' ' | tr '\n' ';')"
  if [[ "$(wc -l < "${TMP}/c2.txt")" == 120 && "$(grep -vc '^200$' "${TMP}/c2.txt" || true)" == 0 ]]; then
    ok "C2 ráfaga de 120 assets estáticos: 120 x 200, 0 x 429"
  else
    fallo "C2 ráfaga de assets con respuestas distintas de 200 (429 = los assets vuelven a consumir por_ip)"
  fi
fi

# --- C3: ráfaga a /api -> sigue habiendo 429 Problem Details --------------------------------------
sleep 4
logs proxy > "${TMP}/px.log"
borde_antes="$(grep -F '"ruta":"/_errores_proxy/429","ruta_pedida":"/api/v1/publico/inicio"' "${TMP}/px.log" | grep -cF '"upstream_s":""' || true)"
for _ in $(seq 1 200); do echo /api/v1/publico/inicio; done > "${TMP}/rafaga.txt"
rafaga 20 "${TMP}/rafaga.txt" > "${TMP}/c3.txt"
echo "C3 ráfaga de 200 a /api/v1/publico/inicio: $(sort "${TMP}/c3.txt" | uniq -c | tr -s ' ' | tr '\n' ';')"
n429="$(grep -c '^429 application/problem+json' "${TMP}/c3.txt" || true)"
# DRF también responde 429 Problem Details (límite por perfil, DEC-AUTO-111): solo cuentan los 429 que
# emite el PROPIO proxy, que el log JSON registra como ruta /_errores_proxy/429 y sin upstream.
sleep 1
logs proxy > "${TMP}/px.log"
borde_despues="$(grep -F '"ruta":"/_errores_proxy/429","ruta_pedida":"/api/v1/publico/inicio"' "${TMP}/px.log" | grep -cF '"upstream_s":""' || true)"
borde=$((borde_despues - borde_antes))
echo "C3 429 emitidos por el limitador del proxy (log): ${borde}"
if [[ "${borde}" -ge 1 && "$(grep -c '^429 ' "${TMP}/c3.txt" || true)" == "${n429}" ]]; then
  ok "C3 ráfaga a /api: ${borde} x 429 del limitador de borde (por_ip intacto), Problem Details"
else
  fallo "C3 la ráfaga a /api no produjo 429 del limitador de borde (${borde}; total 429=${n429}, que pueden ser de DRF): por_ip debilitado o ausente"
fi

if [[ "${fallos}" -gt 0 ]]; then
  echo "smoke anti-evasión: ${fallos} comprobación(es) FALLIDA(S)"; exit 1
fi
echo "smoke anti-evasión: 5/5 comprobaciones OK"
