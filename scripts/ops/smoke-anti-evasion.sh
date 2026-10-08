#!/usr/bin/env bash
# =============================================================================
# Smoke anti-evasión del limitador de borde (TKT-OPS-018; ADR-OPS-001, RSK-OPS-040; TKT-OPS-019).
# Comprueba contra el stack de compose YA levantado (proxy + frontend) que:
#   C5  NG_ALLOWED_HOSTS (config resuelta de compose y entorno real del contenedor) no contiene "*" ni
#       ningún host ".invalid" (con cualquiera de ellos un asset inexistente volvería a renderizar);
#   C1  un asset inexistente (/no-existe-<N>.js) da 404 application/problem+json y NO se renderiza en
#       el SSR: Angular lo rechaza por Host ("estaticos.invalid" no permitido) antes de renderizar y no
#       hay ningún error_ssr para esa ruta (la respuesta sola no basta: el proxy convierte también un
#       404 renderizado en 404 Problem Details);
#   C6  /no-existe-<N>.js%0A NO lo atiende la location de assets (ancla "\z", DEC-AUTO-935): con "$"
#       el "\n" de $uri viajaría crudo hacia el SSR y el proxy respondería 404 Problem Details
#       (/_errores_proxy/404); con "\z" va por location "/" y el SSR responde su 404 HTML;
#   C4  la query de un asset inexistente no llega a los logs del proxy ni del SSR (REQ-057, THREAT-020);
#   C2  una ráfaga de 120 assets estáticos reales no recibe ningún 429 (zona "estaticos");
#   C3  /api sigue en la zona "por_ip": con por_ip saturada por peticiones baratas que nunca llegan a un
#       upstream (POST / -> 403 de limit_except, evaluado DESPUÉS de limit_req), unas sondas GET
#       /api/v1/publico/inicio reciben 429 DEL PROPIO LIMITADOR (log JSON del proxy: /_errores_proxy/429
#       sin upstream). No depende de la velocidad del backend ni del estado del límite de DRF. El log
#       se analiza como JSON y se filtra por campos (no depende del orden del log_format, TKT-OPS-020).
#       Tras C3, por_ip queda saturada ~3 s: C3 termina con una espera explícita de
#       SMOKE_ESPERA_TRAS_C3 s (por defecto 4) para no dar 429 a pasos HTTP posteriores.
# Ejecuta TODAS las comprobaciones y sale con 1 si alguna falla (diagnóstico completo en una pasada).
# Uso (desde la raíz del repositorio, con las mismas variables de compose que levantaron el stack):
#   bash scripts/ops/smoke-anti-evasion.sh [URL_BASE]     (por defecto http://127.0.0.1:8080)
#   SMOKE_COMPROBACIONES="C3" bash scripts/ops/smoke-anti-evasion.sh ...   (solo las indicadas)
# Requiere: bash, curl, python3, docker compose. No modifica el stack (solo envía peticiones).
# =============================================================================
set -Eeuo pipefail
cd "$(dirname "$0")/../.."

B="${1:-http://127.0.0.1:8080}"
COMPROBACIONES="${SMOKE_COMPROBACIONES:-C5 C1 C6 C4 C2 C3}"
N="$(date +%s)$$"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
fallos=0
hechas=0
ok()    { echo "OK    $*"; }
fallo() { echo "::error::FALLO $*"; fallos=$((fallos + 1)); }
logs()  { docker compose logs --no-color --no-log-prefix "$1" 2>&1; }

# Lee el log del proxy por stdin, analiza cada línea como JSON (las que no lo son -avisos de nginx- se
# ignoran) y cuenta los 429 que emite el PROPIO limitador para /api/v1/publico/inicio, filtrando por
# CAMPOS: ruta == /_errores_proxy/429, ruta_pedida == /api/v1/publico/inicio, upstream_s == "" (sin
# upstream) y estado == 429. Independiente del orden de los campos del log_format. Imprime el número,
# o "ERROR <motivo>" si no hay líneas JSON o les faltan esos campos (falla cerrado con mensaje claro).
log_proxy_borde_api() {
  python3 -c '
import json, sys
CAMPOS = ("ruta", "ruta_pedida", "upstream_s", "estado")
n_json, sin_campos, n = 0, 0, 0
for linea in sys.stdin:
    try:
        d = json.loads(linea)
    except ValueError:
        continue
    if not isinstance(d, dict):
        continue
    n_json += 1
    if any(c not in d for c in CAMPOS):
        sin_campos += 1
        continue
    if (d["ruta"] == "/_errores_proxy/429" and d["ruta_pedida"] == "/api/v1/publico/inicio"
            and d["upstream_s"] in ("", None) and str(d["estado"]) == "429"):
        n += 1
if n_json == 0:
    print("ERROR el log del proxy no tiene ninguna línea JSON (¿cambió access_log/log_format?)")
elif sin_campos:
    print(f"ERROR {sin_campos} de {n_json} líneas JSON del log del proxy sin alguno de los campos {CAMPOS} (¿se renombraron en el log_format?)")
else:
    print(n)
'
}

# Ráfaga concurrente con conexiones keep-alive: rápida y determinista en cualquier runner.
# Uso: rafaga <hilos> <fichero de rutas> -> una línea "<estado> <content-type>" por petición.
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
c5() {
  local cfg cid real peligro
  hosts_peligrosos() { tr ',' '\n' <<<"$1" | tr -d ' \r' | grep -iE '\*|\.invalid\.?$' || true; }
  cfg="$(docker compose config --format json | python3 -c 'import json,sys; print((json.load(sys.stdin)["services"]["frontend"].get("environment") or {}).get("NG_ALLOWED_HOSTS",""))')"
  cid="$(docker compose ps -q frontend)"
  [[ -n "${cid}" ]] || { fallo "C5 el servicio frontend no está en ejecución (¿stack levantado con las mismas variables de compose?)"; return; }
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
}

# --- C1: asset inexistente -> 404 Problem Details sin render ------------------------------------
c1() {
  local ruta="/no-existe-${N}.js" res rechazos errores codigo
  res="$(curl -s -o "${TMP}/c1.json" -w '%{http_code} %{content_type}' "${B}${ruta}" || true)"
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
}

# --- C6: un "\n" final no entra en la location de assets (ancla \z) -----------------------------
c6() {
  local pedida="/no-existe-n${N}.js%0A" res linea
  res="$(curl -s -o /dev/null -w '%{http_code} %{content_type}' "${B}${pedida}" || true)"
  echo "C6 ${pedida} -> ${res}"
  sleep 1
  linea="$(logs proxy | grep -F "\"ruta_pedida\":\"${pedida}\"" | tail -1 || true)"
  # Sin "${linea:-...}" con "<" en el valor por defecto: semgrep no sabía analizar esa expansión y
  # dejaba el script entero sin analizar (QA TKT-OPS-018 c2, F-QA018c2-04; TKT-OPS-020).
  if [[ -n "${linea}" ]]; then echo "C6 log del proxy: ${linea}"; else echo "C6 log del proxy: (sin línea)"; fi
  if [[ -z "${linea}" ]]; then
    fallo "C6 la petición ${pedida} no aparece en el log del proxy"
  elif [[ "${res}" == 404\ text/html* && "${linea}" != *'"ruta":"/_errores_proxy/'* ]]; then
    ok "C6 ${pedida} no la atiende la location de assets (404 HTML del SSR por location /; ancla \\z)"
  else
    fallo "C6 ${pedida} la atendió la location de assets (respuesta='${res}'): ¿la regex volvió a '\$' en lugar de '\\z'? (DEC-AUTO-935)"
  fi
}

# --- C4: la query de un asset inexistente no llega a los logs ------------------------------------
c4() {
  local token="secreto${N}" r en_fe en_px llego vistas
  for r in "/no-existe-q${N}.js" "/no-existe-q${N}.css" "/fonts/no-existe-q${N}.woff2" "/media/publico/no-existe-q${N}"; do
    echo "C4 ${r}?${token}=1 -> $(curl -s -o /dev/null -w '%{http_code} %{content_type}' "${B}${r}?${token}=1" || true)"
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
}

# --- C2: ráfaga de 120 assets estáticos reales -> 0 respuestas 429 -------------------------------
c2() {
  local estado n_assets i
  # Sin -f ni abortar por set -e: un 429/5xx o un error de conexión en "/" es un FALLO de C2, no del script.
  estado="$(curl -s -o "${TMP}/inicio.html" -w '%{http_code}' "${B}/" 2>/dev/null || true)"
  if [[ "${estado}" != 200 ]]; then
    fallo "C2 GET / no devolvió 200 (${estado}): no se pueden obtener los assets reales"; return
  fi
  { grep -oE '(src|href)="/?[A-Za-z0-9_-]+\.(js|mjs|css)"' "${TMP}/inicio.html" | sed -E 's/^(src|href)="\/?//; s/"$//'
    grep -oE '/?fonts/[A-Za-z0-9_-]+\.woff2' "${TMP}/inicio.html" | sed 's#^/##'
    echo favicon.ico; } | sort -u > "${TMP}/assets.txt"
  echo "C2 assets reales: $(tr '\n' ' ' < "${TMP}/assets.txt")"
  if [[ "$(grep -cE '\.(js|mjs|css)$' "${TMP}/assets.txt" || true)" -lt 1 ]]; then
    fallo "C2 el HTML del SSR no referencia ningún asset JS/CSS"; return
  fi
  n_assets="$(wc -l < "${TMP}/assets.txt")"
  for i in $(seq 0 119); do sed -n "$(( i % n_assets + 1 ))s#^#/#p" "${TMP}/assets.txt"; done > "${TMP}/rafaga.txt"
  rafaga 20 "${TMP}/rafaga.txt" | cut -d' ' -f1 > "${TMP}/c2.txt"
  echo "C2 ráfaga de $(wc -l < "${TMP}/c2.txt") assets: $(sort "${TMP}/c2.txt" | uniq -c | tr -s ' ' | tr '\n' ';')"
  if [[ "$(wc -l < "${TMP}/c2.txt")" == 120 && "$(grep -vc '^200$' "${TMP}/c2.txt" || true)" == 0 ]]; then
    ok "C2 ráfaga de 120 assets estáticos: 120 x 200, 0 x 429"
  else
    fallo "C2 ráfaga de assets con respuestas distintas de 200 (429 = los assets vuelven a consumir por_ip)"
  fi
}

# --- C3: /api sigue en por_ip (determinista: saturación con POST / -> 403 sin upstream) ----------
# Inundación: 4 hilos keep-alive con POST / durante ~1,5 s (cientos de r/s, >> 20 r/s + burst 60; las
# respuestas 403/429 las emite el propio proxy en ~1 ms). A los 0,4 s, 20 sondas GET /api/v1/publico/inicio
# cada 50 ms. Con por_ip intacto TODAS las sondas encuentran la zona vacía -> 429 del borde, sin tocar
# el backend. Si /api saliera de por_ip (otra zona o sin límite), las sondas llegarían a Django.
#
# El log del proxy se analiza como JSON línea a línea y se filtra POR CAMPOS (ruta, ruta_pedida,
# upstream_s, estado), no por una cadena literal: reordenar los campos del log_format no rompe C3
# (QA TKT-OPS-018 c2, F-QA018c2-01; TKT-OPS-020). Si faltan esos campos o el log deja de ser JSON,
# el mensaje de fallo lo dice en lugar de culpar a por_ip.
#
# AVISO (TKT-OPS-020): al terminar la inundación, por_ip queda saturada ~3 s (cupo de 60 a 20 r/s).
# Cualquier petición HTTP posterior que pase por por_ip (location "/", /api…) recibiría 429. Por eso
# C3 termina con una espera explícita (ESPERA_TRAS_C3) y va la última.
ESPERA_TRAS_C3="${SMOKE_ESPERA_TRAS_C3:-4}"
c3() {
  local antes inund sondas n429 borde despues
  antes="$(logs proxy | log_proxy_borde_api)"
  if [[ "${antes}" == ERROR* ]]; then
    fallo "C3 no se puede evaluar: ${antes#ERROR }"; return
  fi
  python3 - "${B}" > "${TMP}/c3.txt" <<'PY'
import collections, http.client, sys, threading, time, urllib.parse
u = urllib.parse.urlsplit(sys.argv[1]); fin = threading.Event(); inund = collections.Counter(); cerrojo = threading.Lock()
def conexion(): return http.client.HTTPConnection(u.hostname, u.port, timeout=15)
def inundar():
    c = conexion()
    while not fin.is_set():
        try:
            c.request("POST", "/", body=b"", headers={"Content-Length": "0"}); r = c.getresponse(); r.read()
            with cerrojo: inund[r.status] += 1
            if (r.getheader("Connection") or "").lower() == "close": c.close(); c = conexion()
        except OSError:
            with cerrojo: inund["err"] += 1
            c.close(); c = conexion()
        time.sleep(0.005)  # techo de ~200 r/s por hilo: satura por_ip sin inflar el log del proxy
hilos = [threading.Thread(target=inundar, daemon=True) for _ in range(4)]
for h in hilos: h.start()
time.sleep(0.4)
sondas, c = [], conexion()
for _ in range(20):
    try:
        c.request("GET", "/api/v1/publico/inicio"); r = c.getresponse(); r.read()
        sondas.append(f"{r.status} {r.getheader('Content-Type')}")
        if (r.getheader("Connection") or "").lower() == "close": c.close(); c = conexion()
    except OSError as e:
        sondas.append(f"000 {type(e).__name__}"); c.close(); c = conexion()
    time.sleep(0.05)
fin.set()
for h in hilos: h.join(5)
print("INUNDACION " + " ".join(f"{k}={v}" for k, v in sorted(inund.items(), key=str)))
for s in sondas: print("SONDA " + s)
PY
  sleep 1
  inund="$(sed -n 's/^INUNDACION //p' "${TMP}/c3.txt")"
  sondas="$(grep '^SONDA ' "${TMP}/c3.txt" | cut -d' ' -f2- | sort | uniq -c | tr -s ' ' | tr '\n' ';')"
  n429="$(grep -c '^SONDA 429 application/problem+json' "${TMP}/c3.txt" || true)"
  despues="$(logs proxy | log_proxy_borde_api)"
  echo "C3 inundación POST / (por_ip): ${inund}"
  echo "C3 sondas GET /api/v1/publico/inicio: ${sondas}"
  if [[ "${despues}" == ERROR* ]]; then
    fallo "C3 no se puede evaluar: ${despues#ERROR }"
  else
    borde=$(( despues - antes ))
    echo "C3 429 del limitador de borde para /api en el log del proxy (esta comprobación): ${borde}"
    # Las sondas son las únicas peticiones a /api de esta comprobación: con por_ip intacto son 429 del
    # borde (se exige la mitad o más como margen frente a un runner muy lento). Los 429 de DRF no cuentan.
    if [[ "${borde}" -ge 10 && "${n429}" -ge "${borde}" && "${inund}" == *"429="* ]]; then
      ok "C3 /api en por_ip: ${borde}/20 sondas con 429 del limitador de borde durante la saturación"
    elif [[ "${inund}" != *"429="* ]]; then
      fallo "C3 la inundación POST / no saturó por_ip (inundación: ${inund}): ¿location / fuera de por_ip o límite cambiado?"
    else
      fallo "C3 /api no la limita por_ip: ${borde}/20 sondas con 429 del borde (se exigen >=10; 429 Problem Details recibidos=${n429}); inundación: ${inund}"
    fi
  fi
  echo "C3 espera de ${ESPERA_TRAS_C3} s: por_ip queda saturada tras la inundación (pasos HTTP posteriores)"
  sleep "${ESPERA_TRAS_C3}"
}

# C3 deja por_ip saturada durante ~3 s: va la última (C6 usa location "/", que está en por_ip) y termina
# con la espera ESPERA_TRAS_C3, que protege a los pasos HTTP que vengan después del script en el CI.
for c in ${COMPROBACIONES}; do
  case "${c}" in
    C1|C2|C3|C4|C5|C6) ;;
    *) echo "::error::comprobación desconocida: ${c}"; exit 2 ;;
  esac
done
sleep 4   # repone el cupo por_ip de los pasos anteriores (20 r/s, burst 60)
for c in ${COMPROBACIONES}; do
  "${c,,}"
  hechas=$((hechas + 1))
done

if [[ "${fallos}" -gt 0 ]]; then
  echo "smoke anti-evasión: ${fallos} de ${hechas} comprobación(es) FALLIDA(S)"; exit 1
fi
echo "smoke anti-evasión: ${hechas}/${hechas} comprobaciones OK"
