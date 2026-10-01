"""Gate de cobertura POR MÓDULO del backend (TKT-OPS-021, DEC-AUTO-940; Skill_Backend §8).

Uso:  python gate_cobertura.py COVERAGE_JSON UMBRALES_TOML RAIZ_BACKEND [--hoy AAAA-MM-DD]
      Sale 0 si todo cumple; 1 si algo incumple o no se puede evaluar (falla CERRADO);
      2 si la invocación es incorrecta. Solo biblioteca estándar (json, tomllib, fnmatch).

Qué comprueba (umbrales y listas en UMBRALES_TOML, versionado en infra/ci/):
  - Cada [[reglas]]: todo archivo de RAIZ_BACKEND que casa con algún "patrones" (glob relativo,
    "/" como separador) debe tener cobertura ESTRICTAMENTE MAYOR que "umbral" (Skill_Backend §8:
    "Services > 90 %", "Endpoints críticos > 95 %", "Total > 80 %"). La regla especial con
    patrones = ["TOTAL"] usa totals.percent_covered.
  - Falla cerrado si: falta o no es JSON válido el coverage.json; una regla no casa con ningún
    archivo (renombrado silencioso); un archivo que casa existe en disco pero no está en el
    coverage.json (no medido); un archivo de vistas ("clasificar_vistas") no está clasificado como
    crítico (en una regla) ni como no crítico (en [vistas_no_criticas], con motivo).
  - [[excepciones]] nombradas, con caducidad (como .trivyignore): rebajan el umbral de UN archivo a
    "umbral_minimo" (suelo: tampoco puede bajar de ahí) hasta "caduca". Al caducar el gate falla.
    Obligatorios: archivo, umbral_minimo, registrada, caduca, ticket, decision, motivo; la ventana
    registrada -> caduca no puede superar MAX_DIAS_EXCEPCION. Una excepción ya innecesaria (el
    archivo cumple el umbral normal) solo avisa (::warning::) para que se retire.
La cobertura es percent_covered de coverage.py (con branch = true incluye ramas), sin redondear.
"""

from __future__ import annotations

import datetime as dt
import fnmatch
import json
import pathlib
import sys
import tomllib
from typing import Any

MAX_DIAS_EXCEPCION = 45
CAMPOS_EXCEPCION = (
    "archivo",
    "umbral_minimo",
    "registrada",
    "caduca",
    "ticket",
    "decision",
    "motivo",
)
PODAR = {".venv", "__pycache__", "node_modules", "tests"}


def out(texto: str = "") -> None:
    sys.stdout.write(texto + "\n")


def error(msg: str) -> None:
    out(f"::error::cobertura: {msg}")


def archivos_backend(raiz: pathlib.Path) -> list[str]:
    salida = []
    for p in raiz.rglob("*.py"):
        rel = p.relative_to(raiz)
        if PODAR.intersection(rel.parts[:-1]):
            continue
        salida.append(rel.as_posix())
    return sorted(salida)


def casa(ruta: str, patrones: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(ruta, pat) for pat in patrones)


def evaluar(
    cov_path: pathlib.Path, umb_path: pathlib.Path, raiz: pathlib.Path, hoy: dt.date
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
        clasificar: list[str] = conf["clasificar_vistas"]["patrones"]
        excepciones: list[dict[str, Any]] = conf.get("excepciones", [])
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        error(f"umbrales ilegibles en {umb_path} ({type(exc).__name__}: {exc}): falla cerrado")
        return 1
    if not raiz.is_dir():
        error(f"RAIZ_BACKEND {raiz} no es un directorio: falla cerrado")
        return 1

    en_disco = archivos_backend(raiz)

    # --- Reglas: qué archivo se exige a qué umbral (el más alto si casa con varias) ---
    exigido: dict[str, tuple[float, str]] = {}
    for regla in reglas:
        nombre, umbral, patrones = regla.get("nombre"), regla.get("umbral"), regla.get("patrones")
        if not isinstance(nombre, str) or not isinstance(umbral, (int, float)) or not patrones:
            error(f"regla mal formada: {regla!r}")
            fallos += 1
            continue
        if patrones == ["TOTAL"]:
            exigido["TOTAL"] = (float(umbral), nombre)
            continue
        casados = [f for f in en_disco if casa(f, patrones)]
        for pat in patrones:
            if not any(fnmatch.fnmatchcase(f, pat) for f in en_disco):
                error(
                    f"regla '{nombre}': el patrón {pat} no casa con ningún archivo (¿renombrado?)"
                )
                fallos += 1
        for f in casados:
            if f not in exigido or float(umbral) > exigido[f][0]:
                exigido[f] = (float(umbral), nombre)

    # --- Toda vista debe estar clasificada (crítica = cubierta por una regla; o no crítica) ---
    for f in en_disco:
        if casa(f, clasificar) and f not in exigido and f not in no_criticas:
            error(
                f"vista sin clasificar: {f} (añádela a una regla de "
                "endpoints críticos o a [vistas_no_criticas] con motivo)"
            )
            fallos += 1
    for f, motivo in no_criticas.items():
        if f not in en_disco:
            error(f"[vistas_no_criticas] cita {f}, que no existe")
            fallos += 1
        elif f in exigido:
            error(f"{f} está a la vez en una regla y en [vistas_no_criticas]")
            fallos += 1
        elif not str(motivo).strip():
            error(f"[vistas_no_criticas] {f} sin motivo")
            fallos += 1

    # --- Excepciones nombradas con caducidad ---
    suelo: dict[str, dict[str, Any]] = {}
    for exc in excepciones:
        faltan = [c for c in CAMPOS_EXCEPCION if c not in exc or exc[c] in ("", None)]
        if faltan:
            error(f"excepción sin {', '.join(faltan)}: {exc!r}")
            fallos += 1
            continue
        archivo, reg, cad = exc["archivo"], exc["registrada"], exc["caduca"]
        if (
            not isinstance(reg, dt.date)
            or not isinstance(cad, dt.date)
            or isinstance(cad, dt.datetime)
        ):
            error(
                f"excepción {archivo}: 'registrada' y 'caduca' deben ser fechas TOML (AAAA-MM-DD)"
            )
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
        if (cad - reg).days > MAX_DIAS_EXCEPCION or cad < reg:
            error(
                f"excepción {archivo}: ventana {reg} -> {cad} fuera de 0..{MAX_DIAS_EXCEPCION} días"
            )
            fallos += 1
            continue
        if hoy > cad:
            error(
                f"excepción {archivo} ({exc['ticket']}, {exc['decision']}) "
                f"CADUCADA el {cad}: retírala o renuévala con una nueva decisión"
            )
            fallos += 1
            continue
        if not float(exc["umbral_minimo"]) < exigido[archivo][0]:
            error(
                f"excepción {archivo}: umbral_minimo "
                f"{exc['umbral_minimo']} no es menor que el umbral normal"
            )
            fallos += 1
            continue
        suelo[archivo] = exc

    # --- Evaluación ---
    filas = []  # (archivo, cobertura, umbral, regla, estado)
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
    out(
        f"gate de cobertura por módulo: {len(filas)} evaluados, {len(malos)} "
        f"por debajo, {fallos} fallos -> {'FAIL' if fallos else 'PASS'}"
    )
    return 1 if fallos else 0


def main(argv: list[str]) -> int:
    args = list(argv[1:])
    hoy = dt.date.today()
    if "--hoy" in args:
        i = args.index("--hoy")
        try:
            hoy = dt.date.fromisoformat(args[i + 1])
        except (IndexError, ValueError):
            sys.stderr.write("uso: --hoy AAAA-MM-DD\n")
            return 2
        del args[i : i + 2]
    if len(args) != 3:
        sys.stderr.write(__doc__.splitlines()[2] + "\n")
        return 2
    return evaluar(pathlib.Path(args[0]), pathlib.Path(args[1]), pathlib.Path(args[2]), hoy)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
