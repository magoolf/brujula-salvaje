"""Guardia de ejecución previa a trivy (TKT-OPS-009, DEC-AUTO-1261; RSK-OPS-001, QA-OPS006-04,
OBS-C3-1). Defensa en profundidad de infra/ci/politica_trivy.py: la política revisa el TEXTO de
los workflows; la guardia revisa el ENTORNO REAL del paso justo antes de invocar trivy, para los
canales que trivy lee por su cuenta y que pueden fijarse sin que el texto lo muestre literalmente
(p. ej. una variable escrita en $GITHUB_ENV por un paso anterior o un fichero generado).

Uso:  /usr/bin/python3 infra/ci/trivy_guardia.py [--binario RUTA]
      En los workflows se invoca SIEMPRE sin argumentos (la política exige la línea exacta);
      --binario solo lo usan sus controles (infra/ci/trivy_guardia_controles.py).
      Sale 1 (anotaciones ::error::) si:
  1. hay en el entorno alguna variable cuyo nombre empiece por TRIVY_ (trivy las lee todas);
  2. el directorio actual no es $GITHUB_WORKSPACE (si está definido): el .trivyignore y el
     trivy.yaml que trivy busca son los del directorio actual;
  3. existe trivy.yaml, trivy.yml, .trivyignore.yaml o .trivyignore.yml en el directorio
     actual (también como enlace roto): trivy lee ./trivy.yaml por defecto;
  4. .trivyignore no es un fichero normal o difiere del commit del job ($GITHUB_SHA o HEAD)
     (OBS-C3-1: sin escrituras a .trivyignore durante el job);
  5. "trivy" no se resuelve en el PATH al binario verificado (/usr/local/bin/trivy);
  6. hay variables que cambian lo que ejecuta el bash del paso sin verse en su texto:
     BASH_ENV/ENV (script previo, p. ej. una función "trivy" que no escanea), BASH_FUNC_*
     (funciones exportadas), SHELLOPTS/BASHOPTS y LD_PRELOAD.
La guardia se invoca con /usr/bin/python3 (ruta absoluta): un $GITHUB_PATH manipulado no puede
sustituir el intérprete.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys

CONFIGS = ("trivy.yaml", "trivy.yml", ".trivyignore.yaml", ".trivyignore.yml")
BINARIO = "/usr/local/bin/trivy"
SHELL_PROHIBIDAS = {"BASH_ENV", "ENV", "SHELLOPTS", "BASHOPTS", "LD_PRELOAD"}


def main(argv: list[str]) -> int:
    binario = BINARIO
    if len(argv) == 2 and argv[0] == "--binario":
        binario = argv[1]
    elif argv:
        sys.stdout.write("::error::uso: trivy_guardia.py [--binario RUTA]\n")
        return 2
    errores: list[str] = []
    variables = sorted(k for k in os.environ if k.upper().startswith("TRIVY_"))
    if variables:
        errores.append(f"variables TRIVY_* en el entorno (trivy las lee): {', '.join(variables)}")
    shell = sorted(k for k in os.environ if k in SHELL_PROHIBIDAS or k.startswith("BASH_FUNC_"))
    if shell:
        errores.append(f"variables que alteran el bash del paso: {', '.join(shell)}")
    raiz = pathlib.Path.cwd().resolve()
    ws = os.environ.get("GITHUB_WORKSPACE")
    if ws and pathlib.Path(ws).resolve() != raiz:
        errores.append(f"directorio actual {raiz} distinto de GITHUB_WORKSPACE {ws}")
    for nombre in CONFIGS:
        p = raiz / nombre
        if p.exists() or p.is_symlink():
            errores.append(f"{nombre} presente: trivy lo leería como configuración")
    ign = raiz / ".trivyignore"
    if ign.is_symlink() or not ign.is_file():
        errores.append(".trivyignore no es un fichero normal del repositorio")
    else:
        ref = os.environ.get("GITHUB_SHA") or "HEAD"
        git = shutil.which("git")
        if git is None:
            errores.append("git no disponible: no se puede comprobar .trivyignore")
        else:
            seguido = subprocess.run(  # noqa: S603
                [git, "ls-files", "--error-unmatch", "--", ".trivyignore"],
                capture_output=True,
                check=False,
            )
            igual = subprocess.run(  # noqa: S603
                [git, "diff", "--quiet", ref, "--", ".trivyignore"],
                capture_output=True,
                check=False,
            )
            if seguido.returncode != 0 or igual.returncode != 0:
                errores.append(f".trivyignore modificado o no seguido respecto de {ref} (OBS-C3-1)")
    resuelto = shutil.which("trivy")
    if resuelto is None or os.path.realpath(resuelto) != os.path.realpath(binario):
        errores.append(f"trivy se resuelve a {resuelto}, no al binario verificado {binario}")
    for e in errores:
        sys.stdout.write(f"::error::guardia de trivy: {e}\n")
    if errores:
        return 1
    sys.stdout.write("guardia de trivy OK: sin TRIVY_*, sin trivy.yaml, .trivyignore del commit\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
