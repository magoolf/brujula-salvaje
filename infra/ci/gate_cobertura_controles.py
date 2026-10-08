"""Controles del gate de cobertura por módulo (TKT-OPS-021/022). Solo biblioteca estándar.

Uso:  python gate_cobertura_controles.py GATE_PY
      python gate_cobertura_controles.py GATE_PY COVERAGE_JSON UMBRALES_TOML RAIZ VISTAS_JSON
Sale 1 si algún control no da el resultado esperado (exit y mensaje).

Sintéticos (árbol de backend falso en un directorio temporal):
  P1 todo cumple -> 0                    P2 excepción vigente con suelo respetado -> 0
  P3 suelo exactamente en el límite (95 - 25 = 70) -> 0
  P4 .venv y node_modules NO se recorren (os.scandir vigilado) -> 0
  P5 inventario del URLconf coherente -> 0
  N1 falta coverage.json -> 1            N2 coverage.json no es JSON / sin "files" -> 1
  N3 services en 90,00 % (no > 90) -> 1  N4 vista crítica en 95,00 % (no > 95) -> 1
  N5 excepción caducada -> 1             N6 excepción bajo su suelo -> 1
  N7 patrón que no casa (renombrado) -> 1  N8 archivo en disco no medido -> 1
  N9 vista nueva sin clasificar -> 1     N10 total en 80,00 % -> 1
  N11 excepción > 45 días -> 1           N12 excepción sin campo obligatorio -> 1
  N13 excepción huérfana -> 1
  TKT-OPS-022 (QA X1-X5 y F-QA021-01..04):
  N14 (X1) excepción con 'registrada' futura -> 1
  N15 (X2) excepción con umbral_minimo 0 -> 1      N16 suelo 69 < 95 - 25 -> 1
  N17 umbral_minimo no numérico -> 1
  N18 (X3) apps/c/api/vistas_mfa.py sin clasificar -> 1
  N19 (X4) apps/c/api/endpoints.py sin clasificar -> 1
  N20 (X5) apps/a/services/publicar.py no medido -> 1
  N21 (X5) apps/a/services/publicar.py medido al 50 % -> 1
  N22 URLconf: vista fuera de api/ (apps/a/vistas_mfa.py) sin clasificar -> 1
  N23 URLconf: un *serializers.py (excluido por nombre) sirve rutas -> 1
  N24 URLconf: un archivo de [api_soporte] sirve rutas -> 1
  N25 URLconf: módulo externo sin [vistas_externas] -> 1
  N26 urlconf_obligatorio sin --vistas-urlconf -> 1
  N27 inventario del URLconf vacío -> 1
Con coverage.json e inventario del URLconf REALES (en CI, tras pytest y vistas_urlconf.py):
  R1 configuración versionada -> 0       R2 umbral imposible (services > 100) -> 1
  R3 coverage.json real manipulado (un services a 50 %) -> 1
  R4 fecha simulada tras la caducidad de las excepciones vigentes -> 1 (si hay excepciones)
  R5 inventario real + vista nueva apps/cuentas/vistas_mfa.py -> 1
  R6 configuración real sin --vistas-urlconf -> 1
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import tempfile

BASE_TOML = """
[[reglas]]
nombre = "total"
umbral = 80.0
patrones = ["TOTAL"]
[[reglas]]
nombre = "services"
umbral = 90.0
patrones = ["apps/*/services.py"]
patrones_si_existen = ["apps/*/services/*.py"]
[[reglas]]
nombre = "endpoints criticos"
umbral = 95.0
clasifica_vistas = true
patrones = ["apps/a/api/views.py"]
[clasificar_vistas]
patrones = ["apps/*/api/*.py", "apps/*/views.py", "apps/*/views/*.py"]
excluir = ["*/__init__.py", "*serializers.py", "*urls.py", "*/filtros.py"]
[vistas_no_criticas]
"apps/b/api/views.py" = "pública de solo lectura"
[api_soporte]
"apps/b/api/base.py" = "mixins"
"""
EXC = """
[[excepciones]]
archivo = "apps/a/api/views.py"
umbral_minimo = {suelo}
registrada = {registrada}
caduca = {caduca}
ticket = "TKT-X"
decision = "DEC-AUTO-X"
motivo = "control"
"""
ARCHIVOS = [
    "apps/a/services.py",
    "apps/b/services.py",
    "apps/a/api/views.py",
    "apps/a/api/serializers.py",
    "apps/b/api/views.py",
    "apps/b/api/base.py",
]
URLCONF_ARCHIVOS = {"apps/a/api/views.py": ["/panel/a"], "apps/b/api/views.py": ["/publico/b"]}


def inventario(
    extra: dict[str, list[str]] | None = None, externos: dict[str, list[str]] | None = None
) -> dict[str, dict[str, list[str]]]:
    return {"archivos": {**URLCONF_ARCHIVOS, **(extra or {})}, "externos": externos or {}}


URLCONF_OK = inventario()
# P4: el gate se ejecuta con os.scandir vigilado; si entra en .venv o node_modules, aborta.
VIGILANTE = """
import os, runpy, sys
_orig = os.scandir
def _vigilado(ruta="."):
    partes = os.fspath(ruta).replace("\\\\", "/").split("/")
    if ".venv" in partes or "node_modules" in partes:
        raise SystemExit("RECORRIDO PROHIBIDO: " + os.fspath(ruta))
    return _orig(ruta)
os.scandir = _vigilado
gate = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(gate, run_name="__main__")
"""


def out(texto: str = "") -> None:
    sys.stdout.write(texto + "\n")


def cov(pcts: dict[str, float], total: float = 97.0) -> str:
    return json.dumps(
        {
            "files": {f: {"summary": {"percent_covered": p}} for f, p in pcts.items()},
            "totals": {"percent_covered": total},
        }
    )


OK = {
    "apps/a/services.py": 99.0,
    "apps/b/services.py": 91.0,
    "apps/a/api/views.py": 96.0,
    "apps/b/api/views.py": 10.0,
}


def exc(suelo: str = "70.0", registrada: str = "2026-10-01", caduca: str = "2026-10-31") -> str:
    return EXC.format(suelo=suelo, registrada=registrada, caduca=caduca)


def ejecutar(
    gate: str,
    cov_json: str | None,
    toml: str,
    extra_files: tuple[str, ...] = (),
    hoy: str = "2026-10-15",
    cov_text: str | None = None,
    urlconf: dict[str, dict[str, list[str]]] | str | None = None,
    vigilar: bool = False,
) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as d:
        raiz = pathlib.Path(d) / "backend"
        for f in ARCHIVOS + list(extra_files):
            (raiz / f).parent.mkdir(parents=True, exist_ok=True)
            (raiz / f).write_text("x = 1\n", encoding="utf-8")
        cj = pathlib.Path(d) / "coverage.json"
        if cov_text is not None:
            cj.write_text(cov_text, encoding="utf-8")
        elif cov_json is not None:
            cj.write_text(cov_json, encoding="utf-8")
        tt = pathlib.Path(d) / "umbrales.toml"
        tt.write_text(toml, encoding="utf-8")
        extra: list[str] = []
        if urlconf is not None:
            uj = pathlib.Path(d) / "vistas_urlconf.json"
            uj.write_text(
                urlconf if isinstance(urlconf, str) else json.dumps(urlconf), encoding="utf-8"
            )
            extra = ["--vistas-urlconf", str(uj)]
        prefijo = [sys.executable, "-c", VIGILANTE] if vigilar else [sys.executable]
        r = subprocess.run(  # noqa: S603 (intérprete y gate propios, sin entrada externa)
            [*prefijo, gate, str(cj), str(tt), str(raiz), "--hoy", hoy, *extra],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return r.returncode, r.stdout + r.stderr


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 6):
        sys.stderr.write("\n".join(__doc__.splitlines()[2:4]) + "\n")
        return 2
    gate = argv[1]
    casos: list[tuple[str, int, str, tuple[int, str]]] = []

    def caso(nombre: str, esperado: int, patron: str, res: tuple[int, str]) -> None:
        casos.append((nombre, esperado, patron, res))

    con_exc = BASE_TOML + exc()
    bajo = cov({**OK, "apps/a/api/views.py": 75.0})
    caso("P1 todo cumple", 0, r"-> PASS", ejecutar(gate, cov(OK), BASE_TOML))
    caso("P2 excepción vigente", 0, r"EXCEPCIÓN hasta 2026-10-31", ejecutar(gate, bajo, con_exc))
    caso(
        "P3 suelo en el límite 70",
        0,
        r"-> PASS",
        ejecutar(gate, bajo, BASE_TOML + exc(suelo="70")),
    )
    caso(
        "P4 .venv y node_modules sin recorrer",
        0,
        r"-> PASS",
        ejecutar(
            gate,
            cov(OK),
            BASE_TOML,
            extra_files=(".venv/lib/apps/z/api/views.py", "apps/a/node_modules/x/views.py"),
            vigilar=True,
        ),
    )
    caso(
        "P5 URLconf coherente",
        0,
        r"2 archivos de vistas del URLconf.*-> PASS",
        ejecutar(gate, cov(OK), BASE_TOML, urlconf=URLCONF_OK),
    )
    caso("N1 sin coverage.json", 1, r"no existe .*falla cerrado", ejecutar(gate, None, BASE_TOML))
    caso(
        "N2a no es JSON",
        1,
        r"no es un coverage.json válido",
        ejecutar(gate, None, BASE_TOML, cov_text="{roto"),
    )
    caso(
        "N2b sin files",
        1,
        r"no es un coverage.json válido",
        ejecutar(gate, None, BASE_TOML, cov_text='{"totals": {}}'),
    )
    caso(
        "N3 services = 90,00",
        1,
        r"apps/b/services.py: 90.00 %",
        ejecutar(gate, cov({**OK, "apps/b/services.py": 90.0}), BASE_TOML),
    )
    caso(
        "N4 crítico = 95,00",
        1,
        r"apps/a/api/views.py: 95.00 %",
        ejecutar(gate, cov({**OK, "apps/a/api/views.py": 95.0}), BASE_TOML),
    )
    caso(
        "N5 excepción caducada",
        1,
        r"CADUCADA el 2026-10-31",
        ejecutar(gate, bajo, con_exc, hoy="2026-11-01"),
    )
    caso(
        "N6 bajo suelo de excepción",
        1,
        r"BAJO SUELO DE EXCEPCIÓN",
        ejecutar(gate, cov({**OK, "apps/a/api/views.py": 70.0}), con_exc),
    )
    caso(
        "N7 patrón sin coincidencias",
        1,
        r"no casa con ningún archivo",
        ejecutar(
            gate, cov(OK), BASE_TOML.replace('apps/a/api/views.py"]', 'apps/a/api/vistas.py"]')
        ),
    )
    caso(
        "N8 archivo no medido",
        1,
        r"apps/c/services.py: no medido",
        ejecutar(gate, cov(OK), BASE_TOML, extra_files=("apps/c/services.py",)),
    )
    caso(
        "N9 vista sin clasificar",
        1,
        r"vista sin clasificar: apps/c/api/panel_views.py",
        ejecutar(gate, cov(OK), BASE_TOML, extra_files=("apps/c/api/panel_views.py",)),
    )
    caso("N10 total = 80,00", 1, r"TOTAL: 80.00 %", ejecutar(gate, cov(OK, total=80.0), BASE_TOML))
    caso(
        "N11 excepción > 45 días",
        1,
        r"fuera de 0..45 días",
        ejecutar(gate, bajo, BASE_TOML + exc(caduca="2026-12-31")),
    )
    caso(
        "N12 excepción sin ticket",
        1,
        r"excepción sin ticket",
        ejecutar(gate, cov(OK), con_exc.replace('ticket = "TKT-X"\n', "")),
    )
    caso(
        "N13 excepción huérfana",
        1,
        r"excepción huérfana",
        ejecutar(
            gate,
            cov(OK),
            con_exc.replace('archivo = "apps/a/api/views.py"', 'archivo = "apps/b/api/views.py"'),
        ),
    )
    caso(
        "N14 (X1) registrada futura",
        1,
        r"registrada 2026-10-20 es POSTERIOR a hoy \(2026-10-15\)",
        ejecutar(gate, bajo, BASE_TOML + exc(registrada="2026-10-20", caduca="2026-11-30")),
    )
    caso(
        "N15 (X2) suelo 0",
        1,
        r"umbral_minimo 0 por debajo del suelo permitido 70",
        ejecutar(gate, bajo, BASE_TOML + exc(suelo="0.0")),
    )
    caso(
        "N16 suelo 69 (< 95 - 25)",
        1,
        r"umbral_minimo 69 por debajo del suelo permitido 70",
        ejecutar(gate, bajo, BASE_TOML + exc(suelo="69.0")),
    )
    caso(
        "N17 suelo no numérico",
        1,
        r"umbral_minimo debe ser un número",
        ejecutar(gate, bajo, BASE_TOML + exc(suelo='"70"')),
    )
    caso(
        "N18 (X3) vistas_mfa.py",
        1,
        r"vista sin clasificar: apps/c/api/vistas_mfa.py",
        ejecutar(gate, cov(OK), BASE_TOML, extra_files=("apps/c/api/vistas_mfa.py",)),
    )
    caso(
        "N19 (X4) endpoints.py",
        1,
        r"vista sin clasificar: apps/c/api/endpoints.py",
        ejecutar(gate, cov(OK), BASE_TOML, extra_files=("apps/c/api/endpoints.py",)),
    )
    caso(
        "N20 (X5) services/publicar.py no medido",
        1,
        r"apps/a/services/publicar.py: no medido",
        ejecutar(gate, cov(OK), BASE_TOML, extra_files=("apps/a/services/publicar.py",)),
    )
    caso(
        "N21 (X5) services/publicar.py al 50 %",
        1,
        r"apps/a/services/publicar.py: 50.00 % \(exige > 90 %, services\)",
        ejecutar(
            gate,
            cov({**OK, "apps/a/services/publicar.py": 50.0}),
            BASE_TOML,
            extra_files=("apps/a/services/publicar.py",),
        ),
    )
    fuera = inventario({"apps/a/vistas_mfa.py": ["/panel/mfa"]})
    caso(
        "N22 URLconf: vista fuera de api/",
        1,
        r"vista del URLconf sin clasificar: apps/a/vistas_mfa.py",
        ejecutar(gate, cov(OK), BASE_TOML, extra_files=("apps/a/vistas_mfa.py",), urlconf=fuera),
    )
    disfrazada = inventario({"apps/a/api/serializers.py": ["/panel/x"]})
    caso(
        "N23 URLconf: serializers.py sirve rutas",
        1,
        r"apps/a/api/serializers.py sirve rutas .* soporte/excluido",
        ejecutar(gate, cov(OK), BASE_TOML, urlconf=disfrazada),
    )
    soporte = inventario({"apps/b/api/base.py": ["/panel/y"]})
    caso(
        "N24 URLconf: [api_soporte] sirve rutas",
        1,
        r"apps/b/api/base.py sirve rutas .* soporte/excluido",
        ejecutar(gate, cov(OK), BASE_TOML, urlconf=soporte),
    )
    externo = inventario(externos={"django.views.static": ["/media/<path>"]})
    caso(
        "N25 URLconf: módulo externo",
        1,
        r"vista externa sin clasificar: módulo django.views.static",
        ejecutar(gate, cov(OK), BASE_TOML, urlconf=externo),
    )
    caso(
        "N26 urlconf_obligatorio sin inventario",
        1,
        r"urlconf_obligatorio = true y no se pasó --vistas-urlconf",
        ejecutar(
            gate,
            cov(OK),
            BASE_TOML.replace(
                "[clasificar_vistas]\n", "[clasificar_vistas]\nurlconf_obligatorio = true\n"
            ),
        ),
    )
    caso(
        "N27 inventario del URLconf vacío",
        1,
        r"ilegible o vacío",
        ejecutar(gate, cov(OK), BASE_TOML, urlconf={"archivos": {}, "externos": {}}),
    )

    if len(argv) == 6:
        real_cov, real_toml, raiz = pathlib.Path(argv[2]), pathlib.Path(argv[3]), argv[4]
        real_urlconf = pathlib.Path(argv[5])
        toml_txt = real_toml.read_text(encoding="utf-8")

        def real(
            toml: str,
            cov_txt: str | None = None,
            hoy: list[str] | None = None,
            urlconf_txt: str | None = None,
            con_urlconf: bool = True,
        ) -> tuple[int, str]:
            with tempfile.TemporaryDirectory() as d:
                tt = pathlib.Path(d) / "u.toml"
                tt.write_text(toml, encoding="utf-8")
                cj = real_cov
                if cov_txt is not None:
                    cj = pathlib.Path(d) / "coverage.json"
                    cj.write_text(cov_txt, encoding="utf-8")
                uj = real_urlconf
                if urlconf_txt is not None:
                    uj = pathlib.Path(d) / "vistas_urlconf.json"
                    uj.write_text(urlconf_txt, encoding="utf-8")
                extra = ["--vistas-urlconf", str(uj)] if con_urlconf else []
                r = subprocess.run(  # noqa: S603 (intérprete y gate propios, sin entrada externa)
                    [sys.executable, gate, str(cj), str(tt), raiz, *(hoy or []), *extra],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                return r.returncode, r.stdout + r.stderr

        caso("R1 configuración real", 0, r"-> PASS", real(toml_txt))
        imposible = re.sub(
            r'(nombre = "services"\s*\n\s*umbral = )[0-9.]+', r"\g<1>100.0", toml_txt
        )
        caso("R2 umbral imposible", 1, r"exige > 100 %, services", real(imposible))
        datos = json.loads(real_cov.read_text(encoding="utf-8"))
        clave = next(k for k in datos["files"] if k.replace("\\", "/").endswith("services.py"))
        datos["files"][clave]["summary"]["percent_covered"] = 50.0
        caso("R3 coverage.json manipulado", 1, r"50.00 %", real(toml_txt, json.dumps(datos)))
        cads = re.findall(r"^caduca = (\d{4}-\d{2}-\d{2})", toml_txt, flags=re.M)
        if cads:
            caso(
                "R4 tras la caducidad", 1, r"CADUCADA", real(toml_txt, hoy=["--hoy", "2099-01-01"])
            )
        inv = json.loads(real_urlconf.read_text(encoding="utf-8"))
        inv["archivos"]["apps/cuentas/vistas_mfa.py"] = ["/api/v1/panel/auth/mfa/nueva"]
        caso(
            "R5 URLconf real + vistas_mfa.py",
            1,
            r"vista del URLconf sin clasificar: apps/cuentas/vistas_mfa.py",
            real(toml_txt, urlconf_txt=json.dumps(inv)),
        )
        caso(
            "R6 configuración real sin --vistas-urlconf",
            1,
            r"urlconf_obligatorio",
            real(toml_txt, con_urlconf=False),
        )

    fallos = 0
    for nombre, esperado, patron, (rc, salida) in casos:
        ok = rc == esperado and re.search(patron, salida) is not None
        fallos += not ok
        out(
            f"{'OK ' if ok else 'MAL'}  {nombre}: exit {rc} (esperado "
            f"{esperado}){'' if ok else ' / falta: ' + patron}"
        )
        if not ok:
            out(salida)
    out(f"controles del gate de cobertura: {len(casos) - fallos}/{len(casos)} correctos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
