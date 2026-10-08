"""Controles del gate de cobertura por módulo (TKT-OPS-021). Solo biblioteca estándar.

Uso:  python gate_cobertura_controles.py GATE_PY [COVERAGE_JSON_REAL UMBRALES_TOML RAIZ_BACKEND]
Sale 1 si algún control no da el resultado esperado.

Sintéticos (árbol de backend falso en un directorio temporal):
  P1 todo cumple -> 0                    P2 excepción vigente con suelo respetado -> 0
  N1 falta coverage.json -> 1            N2 coverage.json no es JSON / sin "files" -> 1
  N3 services en 90,00 % (no > 90) -> 1  N4 vista crítica en 95,00 % (no > 95) -> 1
  N5 excepción caducada -> 1             N6 excepción bajo su suelo -> 1
  N7 patrón que no casa (renombrado) -> 1  N8 archivo en disco no medido -> 1
  N9 vista nueva sin clasificar -> 1     N10 total en 80,00 % -> 1
  N11 excepción > 45 días -> 1           N12 excepción sin campo obligatorio -> 1
  N13 excepción huérfana -> 1
Con coverage.json REAL (en CI, tras pytest):
  R1 configuración versionada -> 0       R2 umbral imposible (services > 100) -> 1
  R3 coverage.json real manipulado (un services a 50 %) -> 1
  R4 fecha simulada tras la caducidad de las excepciones vigentes -> 1 (si hay excepciones)
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
[[reglas]]
nombre = "endpoints criticos"
umbral = 95.0
patrones = ["apps/a/api/views.py"]
[clasificar_vistas]
patrones = ["apps/*/api/*views*.py"]
[vistas_no_criticas]
"apps/b/api/views.py" = "pública de solo lectura"
"""
EXC = """
[[excepciones]]
archivo = "apps/a/api/views.py"
umbral_minimo = 70.0
registrada = 2026-10-01
caduca = {caduca}
ticket = "TKT-X"
decision = "DEC-AUTO-X"
motivo = "control"
"""
ARCHIVOS = [
    "apps/a/services.py",
    "apps/b/services.py",
    "apps/a/api/views.py",
    "apps/b/api/views.py",
]


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


def ejecutar(
    gate: str,
    cov_json: str | None,
    toml: str,
    extra_files: tuple[str, ...] = (),
    hoy: str = "2026-10-15",
    cov_text: str | None = None,
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
        r = subprocess.run(  # noqa: S603 (intérprete y gate propios, sin entrada externa)
            [sys.executable, gate, str(cj), str(tt), str(raiz), "--hoy", hoy],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return r.returncode, r.stdout + r.stderr


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 5):
        sys.stderr.write(__doc__.splitlines()[2] + "\n")
        return 2
    gate = argv[1]
    casos: list[tuple[str, int, str, tuple[int, str]]] = []

    def caso(nombre: str, esperado: int, patron: str, res: tuple[int, str]) -> None:
        casos.append((nombre, esperado, patron, res))

    con_exc = BASE_TOML + EXC.format(caduca="2026-10-31")
    caso("P1 todo cumple", 0, r"-> PASS", ejecutar(gate, cov(OK), BASE_TOML))
    caso(
        "P2 excepción vigente",
        0,
        r"EXCEPCIÓN hasta 2026-10-31",
        ejecutar(gate, cov({**OK, "apps/a/api/views.py": 75.0}), con_exc),
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
        ejecutar(gate, cov({**OK, "apps/a/api/views.py": 75.0}), con_exc, hoy="2026-11-01"),
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
        ejecutar(
            gate,
            cov({**OK, "apps/a/api/views.py": 75.0}),
            BASE_TOML + EXC.format(caduca="2026-12-31"),
        ),
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

    if len(argv) == 5:
        real_cov, real_toml, raiz = pathlib.Path(argv[2]), pathlib.Path(argv[3]), argv[4]
        toml_txt = real_toml.read_text(encoding="utf-8")

        def real(
            toml: str, cov_txt: str | None = None, hoy: list[str] | None = None
        ) -> tuple[int, str]:
            with tempfile.TemporaryDirectory() as d:
                tt = pathlib.Path(d) / "u.toml"
                tt.write_text(toml, encoding="utf-8")
                cj = real_cov
                if cov_txt is not None:
                    cj = pathlib.Path(d) / "coverage.json"
                    cj.write_text(cov_txt, encoding="utf-8")
                r = subprocess.run(  # noqa: S603 (intérprete y gate propios, sin entrada externa)
                    [sys.executable, gate, str(cj), str(tt), raiz, *(hoy or [])],
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
