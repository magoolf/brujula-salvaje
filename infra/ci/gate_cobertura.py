"""Gate de cobertura POR MÓDULO del backend (TKT-OPS-021/022, DEC-AUTO-940; Skill_Backend §8).

Uso:  python gate_cobertura.py COVERAGE_JSON UMBRALES_TOML RAIZ_BACKEND [--hoy AAAA-MM-DD]
                               [--vistas-urlconf VISTAS_JSON]
      Sale 0 si todo cumple; 1 si algo incumple o no se puede evaluar (falla CERRADO);
      2 si la invocación es incorrecta. Solo biblioteca estándar (json, tomllib, fnmatch).
      VISTAS_JSON lo genera infra/ci/vistas_urlconf.py (vistas REALES del URLconf de Django).

Qué comprueba (umbrales y listas en UMBRALES_TOML, versionado en infra/ci/):
  - Cada [[reglas]]: todo archivo de RAIZ_BACKEND que casa con algún "patrones" (glob relativo,
    "/" como separador) debe tener cobertura ESTRICTAMENTE MAYOR que "umbral" (Skill_Backend §8:
    "Services > 90 %", "Endpoints críticos > 95 %", "Total > 80 %"). La regla especial con
    patrones = ["TOTAL"] usa totals.percent_covered. "patrones_si_existen" se aplican igual pero
    pueden no casar con nada todavía (p. ej. paquetes apps/*/services/*.py).
  - Falla cerrado si: falta o no es JSON válido el coverage.json; un patrón de "patrones" no casa
    con ningún archivo (renombrado silencioso); un archivo que casa existe en disco pero no está en
    el coverage.json (no medido).
  - Clasificación de vistas SIN depender del nombre del archivo (TKT-OPS-022, F-QA021-01):
    1) estructural: todo archivo que casa con [clasificar_vistas].patrones (apps/*/api/*.py, ...) y
       no con "excluir" ni está en [api_soporte] (con motivo) debe ser crítico (en una regla con
       clasifica_vistas = true) o no crítico ([vistas_no_criticas], con motivo);
    2) URLconf (--vistas-urlconf): todo archivo que sirve una ruta o un handlerXXX debe estar
       clasificado igual, esté donde esté y se llame como se llame; un archivo excluido o de
       [api_soporte] que sirve rutas falla; un módulo externo (fuera de backend/) debe estar en
       [vistas_externas] con motivo. Con urlconf_obligatorio = true, omitir --vistas-urlconf falla.
    3) rutas críticas (TKT-OPS-027, F-QA022-02): todo archivo que sirve una ruta bajo un prefijo de
       [clasificar_vistas].prefijos_criticos (p. ej. "/api/v1/panel/") debe estar en una regla de
       vistas críticas; si está en [vistas_no_criticas], [api_soporte], excluido o sin clasificar,
       falla. Con urlconf_obligatorio = true la lista no puede estar vacía (falla cerrado).
  - [[excepciones]] nombradas, con caducidad (como .trivyignore): rebajan el umbral de UN archivo a
    "umbral_minimo" (suelo: tampoco puede bajar de ahí) hasta "caduca". Al caducar el gate falla.
    Obligatorios: archivo, umbral_minimo, registrada, caduca, ticket, decision, motivo. Reglas:
      registrada <= hoy (no se registran en el futuro) y registrada <= caduca;
      registrada -> caduca <= MAX_DIAS_EXCEPCION y también hoy -> caduca <= MAX_DIAS_EXCEPCION;
      umbral_minimo < umbral normal, >= umbral normal - MAX_REBAJA_PUNTOS y >= SUELO_ABSOLUTO
      (F-QA021-03: una excepción no puede vaciar el gate con un suelo 0).
    Una excepción ya innecesaria (el archivo cumple el umbral normal) solo avisa (::warning::).
La cobertura es percent_covered de coverage.py (con branch = true incluye ramas), sin redondear.
"""

from __future__ import annotations

import datetime as dt
import fnmatch
import json
import os
import pathlib
import re
import sys
import tomllib
from typing import Any

MAX_DIAS_EXCEPCION = 45
# F-QA021-03 (TKT-OPS-022): suelo de una excepción. Nunca más de 25 puntos por debajo del umbral
# normal de su regla (crítico 95 -> suelo >= 70; services 90 -> >= 65) ni por debajo de 60 %.
MAX_REBAJA_PUNTOS = 25.0
SUELO_ABSOLUTO = 60.0
CAMPOS_EXCEPCION = (
    "archivo",
    "umbral_minimo",
    "registrada",
    "caduca",
    "ticket",
    "decision",
    "motivo",
)
# F-QA021-06: directorios que NO se recorren (se podan en os.walk, no se filtran después).
PODAR = {
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "tests",
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "htmlcov",
}


def out(texto: str = "") -> None:
    sys.stdout.write(texto + "\n")


def error(msg: str) -> None:
    out(f"::error::cobertura: {msg}")


def archivos_backend(raiz: pathlib.Path) -> list[str]:
    salida = []
    for actual, dirs, ficheros in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in PODAR and not d.startswith(".")]
        base = pathlib.Path(actual)
        for nombre in ficheros:
            if nombre.endswith(".py"):
                salida.append((base / nombre).relative_to(raiz).as_posix())
    return sorted(salida)


def casa(ruta: str, patrones: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(ruta, pat) for pat in patrones)


def ruta_normalizada(ruta: str) -> str:
    """Ruta del URLconf comparable con un prefijo: sin anclas ^ de re_path y sin // repetidas."""
    return re.sub(r"/+", "/", ruta.replace("^", ""))


def es_ruta_critica(ruta: str, prefijos: list[str]) -> bool:
    r = ruta_normalizada(ruta)
    return any(r == p.rstrip("/") or r.startswith(p.rstrip("/") + "/") for p in prefijos)


def es_numero(valor: Any) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def evaluar(
    cov_path: pathlib.Path,
    umb_path: pathlib.Path,
    raiz: pathlib.Path,
    hoy: dt.date,
    urlconf_path: pathlib.Path | None = None,
) -> int:
    fallos = 0
    try:
        cov = json.loads(cov_path.read_text(encoding="utf-8"))
        files_raw = cov["files"]
        total = float(cov["totals"]["percent_covered"])
        cobertura = {
            k.replace("\\", "/"): float(v["summary"]["percent_covered"])
            for k, v in files_raw.items()
        }
    except FileNotFoundError:
        error(f"no existe {cov_path} (¿falta --cov-report=json?): falla cerrado")
        return 1
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        error(
            f"{cov_path} no es un coverage.json válido ({type(exc).__name__}: {exc}): falla cerrado"
        )
        return 1
    try:
        conf = tomllib.loads(umb_path.read_text(encoding="utf-8"))
        reglas: list[dict[str, Any]] = conf["reglas"]
        no_criticas: dict[str, str] = conf.get("vistas_no_criticas", {})
        clasif: dict[str, Any] = conf["clasificar_vistas"]
        clasificar: list[str] = clasif["patrones"]
        excluir: list[str] = clasif.get("excluir", [])
        urlconf_obligatorio = clasif.get("urlconf_obligatorio", False) is True
        prefijos_criticos: list[str] = clasif.get("prefijos_criticos", [])
        soporte: dict[str, str] = conf.get("api_soporte", {})
        externas: dict[str, str] = conf.get("vistas_externas", {})
        excepciones: list[dict[str, Any]] = conf.get("excepciones", [])
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        error(f"umbrales ilegibles en {umb_path} ({type(exc).__name__}: {exc}): falla cerrado")
        return 1
    if not raiz.is_dir():
        error(f"RAIZ_BACKEND {raiz} no es un directorio: falla cerrado")
        return 1
    if not isinstance(prefijos_criticos, list) or not all(
        isinstance(p, str) and p.startswith("/") and p.strip("/") for p in prefijos_criticos
    ):
        error(
            "[clasificar_vistas].prefijos_criticos debe ser una lista de rutas que empiezan por / "
            f'(p. ej. "/api/v1/panel/"), no {prefijos_criticos!r}: falla cerrado'
        )
        return 1
    if urlconf_obligatorio and not prefijos_criticos:
        error(
            "urlconf_obligatorio = true y [clasificar_vistas].prefijos_criticos está vacío: "
            "sin prefijos no se comprueba qué archivos sirven rutas críticas: falla cerrado"
        )
        return 1

    urlconf: dict[str, list[str]] | None = None
    urlconf_ext: dict[str, list[str]] = {}
    if urlconf_path is not None:
        try:
            datos = json.loads(urlconf_path.read_text(encoding="utf-8"))
            urlconf = {str(k): list(v) for k, v in datos["archivos"].items()}
            urlconf_ext = {str(k): list(v) for k, v in datos.get("externos", {}).items()}
            if not urlconf:
                raise ValueError("sin archivos")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            error(
                f"inventario de vistas del URLconf {urlconf_path} ilegible o vacío "
                f"({type(exc).__name__}: {exc}): falla cerrado"
            )
            return 1
    elif urlconf_obligatorio:
        error(
            "urlconf_obligatorio = true y no se pasó --vistas-urlconf "
            "(infra/ci/vistas_urlconf.py): falla cerrado"
        )
        return 1

    en_disco = archivos_backend(raiz)

    # --- Reglas: qué archivo se exige a qué umbral (el más alto si casa con varias) ---
    exigido: dict[str, tuple[float, str]] = {}
    criticos: set[str] = set()
    for regla in reglas:
        nombre, umbral_raw, patrones = (
            regla.get("nombre"),
            regla.get("umbral"),
            regla.get("patrones"),
        )
        opcionales = regla.get("patrones_si_existen", [])
        if (
            not isinstance(nombre, str)
            or not isinstance(umbral_raw, (int, float))
            or isinstance(umbral_raw, bool)
            or not isinstance(patrones, list)
            or not patrones
            or not isinstance(opcionales, list)
        ):
            error(f"regla mal formada: {regla!r}")
            fallos += 1
            continue
        umbral = float(umbral_raw)
        if patrones == ["TOTAL"]:
            exigido["TOTAL"] = (umbral, nombre)
            continue
        for pat in patrones:
            if not any(fnmatch.fnmatchcase(f, pat) for f in en_disco):
                error(
                    f"regla '{nombre}': el patrón {pat} no casa con ningún archivo (¿renombrado?)"
                )
                fallos += 1
        casados = [f for f in en_disco if casa(f, patrones + opcionales)]
        if regla.get("clasifica_vistas") is True:
            criticos.update(casados)
        for f in casados:
            if f not in exigido or umbral > exigido[f][0]:
                exigido[f] = (umbral, nombre)

    def clasificada(f: str) -> bool:
        return f in criticos or f in no_criticas

    # --- Clasificación estructural: apps/*/api/*.py y similares, salvo soporte declarado ---
    for f in en_disco:
        if not casa(f, clasificar) or casa(f, excluir) or f in soporte:
            continue
        if not clasificada(f):
            error(
                f"vista sin clasificar: {f} (añádela a la regla de endpoints críticos, a "
                "[vistas_no_criticas] con motivo, o -si no sirve rutas- a [api_soporte] con motivo)"
            )
            fallos += 1
    for tabla, nombre_tabla in ((no_criticas, "vistas_no_criticas"), (soporte, "api_soporte")):
        for f, motivo in tabla.items():
            if f not in en_disco:
                error(f"[{nombre_tabla}] cita {f}, que no existe")
                fallos += 1
            elif f in criticos:
                error(f"{f} está a la vez en una regla de vistas críticas y en [{nombre_tabla}]")
                fallos += 1
            elif not str(motivo).strip():
                error(f"[{nombre_tabla}] {f} sin motivo")
                fallos += 1
    for f in set(no_criticas) & set(soporte):
        error(f"{f} está a la vez en [vistas_no_criticas] y en [api_soporte]")
        fallos += 1

    # --- Clasificación por URLconf: lo que REALMENTE sirve rutas ---
    if urlconf is not None:
        for f, rutas in sorted(urlconf.items()):
            ejemplo = ", ".join(rutas[:3]) + (" ..." if len(rutas) > 3 else "")
            criticas = [r for r in rutas if es_ruta_critica(r, prefijos_criticos)]
            if criticas and f not in criticos:
                donde = (
                    "[vistas_no_criticas]"
                    if f in no_criticas
                    else "[api_soporte]"
                    if f in soporte
                    else "excluido por nombre"
                    if casa(f, excluir)
                    else "sin clasificar"
                )
                error(
                    f"{f} sirve rutas críticas ({', '.join(criticas[:3])}"
                    f"{' ...' if len(criticas) > 3 else ''}; prefijos {prefijos_criticos}) pero "
                    f"está {donde}: debe estar en una regla de vistas críticas (> 95 %)"
                )
                fallos += 1
                continue
            if f in soporte or (casa(f, excluir) and not clasificada(f)):
                error(
                    f"{f} sirve rutas del URLconf ({ejemplo}) pero está declarado como "
                    "soporte/excluido: clasifícalo como vista crítica o no crítica"
                )
                fallos += 1
            elif not clasificada(f):
                error(
                    f"vista del URLconf sin clasificar: {f} ({ejemplo}): añádela a la regla de "
                    "endpoints críticos o a [vistas_no_criticas] con motivo"
                )
                fallos += 1
            elif f not in en_disco:
                error(f"el URLconf cita {f}, que no está en {raiz} (¿podado o fuera del árbol?)")
                fallos += 1
        for mod, rutas in sorted(urlconf_ext.items()):
            if not str(externas.get(mod, "")).strip():
                error(
                    f"vista externa sin clasificar: módulo {mod} sirve {', '.join(rutas[:3])}: "
                    "añádelo a [vistas_externas] con motivo"
                )
                fallos += 1

    # --- Excepciones nombradas con caducidad ---
    suelo: dict[str, dict[str, Any]] = {}
    for ex in excepciones:
        faltan = [c for c in CAMPOS_EXCEPCION if c not in ex or ex[c] in ("", None)]
        if faltan:
            error(f"excepción sin {', '.join(faltan)}: {ex!r}")
            fallos += 1
            continue
        archivo, reg, cad = ex["archivo"], ex["registrada"], ex["caduca"]
        if (
            not isinstance(reg, dt.date)
            or not isinstance(cad, dt.date)
            or isinstance(reg, dt.datetime)
            or isinstance(cad, dt.datetime)
        ):
            error(
                f"excepción {archivo}: 'registrada' y 'caduca' deben ser fechas TOML (AAAA-MM-DD)"
            )
            fallos += 1
            continue
        if not es_numero(ex["umbral_minimo"]):
            error(f"excepción {archivo}: umbral_minimo debe ser un número")
            fallos += 1
            continue
        if archivo not in exigido or archivo == "TOTAL":
            error(
                f"excepción {archivo}: no está sujeto a ninguna "
                "regla por archivo (excepción huérfana)"
            )
            fallos += 1
            continue
        if archivo in suelo:
            error(f"excepción duplicada para {archivo}")
            fallos += 1
            continue
        if reg > hoy:
            error(
                f"excepción {archivo}: registrada {reg} es POSTERIOR a hoy ({hoy}): la ventana de "
                f"{MAX_DIAS_EXCEPCION} días se cuenta desde una fecha real"
            )
            fallos += 1
            continue
        if cad < reg or (cad - reg).days > MAX_DIAS_EXCEPCION:
            error(
                f"excepción {archivo}: ventana {reg} -> {cad} fuera de 0..{MAX_DIAS_EXCEPCION} días"
            )
            fallos += 1
            continue
        if (cad - hoy).days > MAX_DIAS_EXCEPCION:
            error(
                f"excepción {archivo}: caduca {cad}, a más de "
                f"{MAX_DIAS_EXCEPCION} días de hoy ({hoy})"
            )
            fallos += 1
            continue
        if hoy > cad:
            error(
                f"excepción {archivo} ({ex['ticket']}, {ex['decision']}) "
                f"CADUCADA el {cad}: retírala o renuévala con una nueva decisión"
            )
            fallos += 1
            continue
        normal = exigido[archivo][0]
        minimo = float(ex["umbral_minimo"])
        if not minimo < normal:
            error(f"excepción {archivo}: umbral_minimo {minimo:g} no es menor que el umbral normal")
            fallos += 1
            continue
        limite = max(normal - MAX_REBAJA_PUNTOS, SUELO_ABSOLUTO)
        if minimo < limite:
            error(
                f"excepción {archivo}: umbral_minimo {minimo:g} por debajo del suelo permitido "
                f"{limite:g} (umbral {normal:g} - {MAX_REBAJA_PUNTOS:g} puntos, mínimo absoluto "
                f"{SUELO_ABSOLUTO:g}): una excepción no puede vaciar el gate"
            )
            fallos += 1
            continue
        suelo[archivo] = ex

    # --- Evaluación ---
    filas: list[tuple[str, float | None, float, str, str]] = []  # archivo, %, umbral, regla, estado
    for f, (umbral, nombre) in sorted(exigido.items()):
        if f == "TOTAL":
            pct: float | None = total
        else:
            pct = cobertura.get(f)
        if pct is None:
            filas.append((f, None, umbral, nombre, "NO MEDIDO"))
            continue
        if f in suelo:
            minimo = float(suelo[f]["umbral_minimo"])
            if pct > umbral:
                out(
                    f"::warning::cobertura: {f} ya cumple {nombre} (> {umbral:g} %) "
                    f"con {pct:.2f} %: retira la excepción {suelo[f]['decision']}"
                )
                filas.append((f, pct, umbral, nombre, "OK"))
            elif pct > minimo:
                filas.append(
                    (
                        f,
                        pct,
                        minimo,
                        nombre,
                        f"EXCEPCIÓN hasta {suelo[f]['caduca']} ({suelo[f]['ticket']})",
                    )
                )
            else:
                filas.append((f, pct, minimo, nombre, "BAJO SUELO DE EXCEPCIÓN"))
        else:
            filas.append((f, pct, umbral, nombre, "OK" if pct > umbral else "BAJO UMBRAL"))

    malos = [r for r in filas if r[4] in ("NO MEDIDO", "BAJO UMBRAL", "BAJO SUELO DE EXCEPCIÓN")]
    ancho = max(len(r[0]) for r in filas) if filas else 10
    out(f"{'archivo':<{ancho}}  {'cobertura':>9}  {'exige >':>7}  regla / estado")
    for f, pct, umbral, nombre, estado in filas:
        pct_s = "-" if pct is None else f"{pct:.2f} %"
        out(f"{f:<{ancho}}  {pct_s:>9}  {umbral:>5g} %  {nombre} / {estado}")
    if malos:
        out()
        out(f"Módulos por debajo del umbral ({len(malos)}):")
        for f, pct, umbral, nombre, estado in malos:
            pct_s = "no medido" if pct is None else f"{pct:.2f} %"
            error(f"{f}: {pct_s} (exige > {umbral:g} %, {nombre}) [{estado}]")
        fallos += len(malos)
    out()
    vistas = "" if urlconf is None else f", {len(urlconf)} archivos de vistas del URLconf"
    out(
        f"gate de cobertura por módulo: {len(filas)} evaluados{vistas}, {len(malos)} "
        f"por debajo, {fallos} fallos -> {'FAIL' if fallos else 'PASS'}"
    )
    return 1 if fallos else 0


def main(argv: list[str]) -> int:
    args = list(argv[1:])
    hoy = dt.date.today()
    urlconf: pathlib.Path | None = None
    if "--hoy" in args:
        i = args.index("--hoy")
        try:
            hoy = dt.date.fromisoformat(args[i + 1])
        except (IndexError, ValueError):
            sys.stderr.write("uso: --hoy AAAA-MM-DD\n")
            return 2
        del args[i : i + 2]
    if "--vistas-urlconf" in args:
        i = args.index("--vistas-urlconf")
        if i + 1 >= len(args):
            sys.stderr.write("uso: --vistas-urlconf VISTAS_JSON\n")
            return 2
        urlconf = pathlib.Path(args[i + 1])
        del args[i : i + 2]
    if len(args) != 3:
        sys.stderr.write("\n".join(__doc__.splitlines()[2:4]) + "\n")
        return 2
    return evaluar(
        pathlib.Path(args[0]), pathlib.Path(args[1]), pathlib.Path(args[2]), hoy, urlconf
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
