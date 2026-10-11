"""Controles de infra/ci/trivy_guardia.py (TKT-OPS-009, DEC-AUTO-1261).

Uso:  python3 infra/ci/trivy_guardia_controles.py [GUARDIA]  (defecto: infra/ci/trivy_guardia.py)
Crea un repositorio git temporal con un .trivyignore confirmado y un binario "trivy" falso, y
ejecuta la guardia en cada caso (uno positivo y el resto negativos) exigiendo su código de salida.
Requiere git. Es Python (no *.sh) a propósito: sus casos contienen TRIVY_* y trivy.yaml, que la
política prohíbe en los *.sh del repositorio.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

IGNORE = "CVE-2026-00001 exp:2099-01-01\n"
EXE = "trivy.exe" if os.name == "nt" else "trivy"


def out(texto: str) -> None:
    sys.stdout.write(texto + "\n")


def git(cwd: pathlib.Path, *args: str) -> str:
    base = ["git", "-c", "user.name=ci", "-c", "user.email=ci@example.invalid"]
    r = subprocess.run([*base, *args], cwd=cwd, capture_output=True, text=True, check=True)  # noqa: S603
    return r.stdout.strip()


def binario(d: pathlib.Path) -> pathlib.Path:
    d.mkdir(parents=True, exist_ok=True)
    b = d / EXE
    b.write_text("#!/bin/sh\nexit 0\n")
    b.chmod(0o755)
    return b


def main() -> int:
    guardia = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "infra/ci/trivy_guardia.py")
    guardia = guardia.resolve()
    fallos = 0
    n = 0
    base_env = {k: v for k, v in os.environ.items() if not k.upper().startswith("TRIVY_")}
    with tempfile.TemporaryDirectory() as tmp:
        raiz = pathlib.Path(tmp)

        def preparar(nombre: str) -> tuple[pathlib.Path, pathlib.Path, str]:
            repo = raiz / nombre
            repo.mkdir()
            git(repo, "init", "-q")
            (repo / ".trivyignore").write_text(IGNORE)
            git(repo, "add", ".trivyignore")
            git(repo, "commit", "-q", "-m", "x")
            return repo, binario(raiz / f"{nombre}-bin"), git(repo, "rev-parse", "HEAD")

        def caso(nombre: str, esperado: int, cambio=None) -> None:
            nonlocal fallos, n
            n += 1
            repo, b, sha = preparar(f"c{n}")
            env = dict(base_env)
            env["PATH"] = str(b.parent) + os.pathsep + env.get("PATH", "")
            env["GITHUB_WORKSPACE"] = str(repo)
            env["GITHUB_SHA"] = sha
            cwd = repo
            if cambio is not None:
                nuevo = cambio(repo, env, b)
                cwd = nuevo if isinstance(nuevo, pathlib.Path) else repo
            r = subprocess.run(  # noqa: S603
                [sys.executable, str(guardia), "--binario", str(b)],
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            primera = next((x for x in r.stdout.splitlines() if "::error::" in x), "")[:110]
            if r.returncode == esperado:
                out(f"OK  | {nombre} | esperado {esperado} | rc {r.returncode} | {primera}")
            else:
                fallos += 1
                out(f"MAL | {nombre} | esperado {esperado} | rc {r.returncode}")
                out("      " + (r.stdout + r.stderr).replace("\n", "\n      "))

        def env_var(nombre: str, valor: str):
            return lambda repo, env, b: env.__setitem__(nombre, valor)

        def fichero(nombre: str):
            return lambda repo, env, b: (repo / nombre).write_text("severity: [CRITICAL]\n")

        def enlace_roto(repo, env, b):
            (repo / "trivy.yml").symlink_to(repo / "no-existe.yaml")

        def anadir(repo, env, b):
            with (repo / ".trivyignore").open("a") as f:
                f.write("CVE-2026-99999 exp:2099-01-01\n")

        def borrar(repo, env, b):
            (repo / ".trivyignore").unlink()

        def enlace_ignore(repo, env, b):
            otro = repo.parent / f"{repo.name}-otro"
            otro.write_text(IGNORE)
            (repo / ".trivyignore").unlink()
            (repo / ".trivyignore").symlink_to(otro)

        def confirmado_despues(repo, env, b):
            anadir(repo, env, b)
            git(repo, "commit", "-q", "-am", "excepción añadida durante el job")

        def otro_binario(repo, env, b):
            falso = binario(repo.parent / f"{repo.name}-falso")
            env["PATH"] = str(falso.parent) + os.pathsep + env["PATH"]

        def sin_binario(repo, env, b):
            b.unlink()

        def subdirectorio(repo, env, b):
            sub = repo / "sub"
            sub.mkdir()
            shutil.copy(repo / ".trivyignore", sub / ".trivyignore")
            return sub

        caso("G00 entorno limpio", 0)
        caso("G01 TRIVY_IGNORE_UNFIXED en el entorno", 1, env_var("TRIVY_IGNORE_UNFIXED", "true"))
        caso("G02 TRIVY_SERVER (no estaba en la lista antigua)", 1, env_var("TRIVY_SERVER", "x"))
        caso("G03 TRIVY_DB_REPOSITORY", 1, env_var("TRIVY_DB_REPOSITORY", "ghcr.io/evil/db"))
        caso("G04 trivy.yaml generado en el directorio", 1, fichero("trivy.yaml"))
        caso("G05 .trivyignore.yaml generado", 1, fichero(".trivyignore.yaml"))
        caso("G06 fichero ajeno a trivy en el directorio", 0, fichero("notas.txt"))
        if os.name != "nt":
            caso("G07 trivy.yml como enlace roto", 1, enlace_roto)
            caso("G08 .trivyignore sustituido por un enlace", 1, enlace_ignore)
        caso("G09 línea añadida a .trivyignore durante el job", 1, anadir)
        caso("G10 .trivyignore borrado", 1, borrar)
        caso("G11 .trivyignore cambiado y confirmado durante el job", 1, confirmado_despues)
        caso("G12 trivy resuelto a otro binario del PATH", 1, otro_binario)
        caso("G13 trivy ausente del PATH", 1, sin_binario)
        caso("G14 directorio distinto de GITHUB_WORKSPACE", 1, subdirectorio)
        caso("G15 BASH_ENV (función trivy que no escanea)", 1, env_var("BASH_ENV", "/opt/x/f.sh"))
        caso(
            "G16 función exportada BASH_FUNC_trivy%%", 1, env_var("BASH_FUNC_trivy%%", "() { :; }")
        )
        caso("G17 LD_PRELOAD", 1, env_var("LD_PRELOAD", "/opt/x/x.so"))
    out(f"controles de la guardia: {n}; fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
