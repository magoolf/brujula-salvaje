"""Inventario de vistas REALES a partir del URLconf de Django (TKT-OPS-022, F-QA021-01).

Uso (desde backend/, con el entorno del proyecto y DJANGO_SETTINGS_MODULE definido):
      uv run --frozen python ../infra/ci/vistas_urlconf.py SALIDA_JSON
Sale 0 si escribe el inventario; 1 si Django no carga o el URLconf no sirve ninguna ruta (falla
CERRADO). Sin dependencias nuevas: solo Django (ya en el lockfile del backend) y la biblioteca
estándar.

Recorre get_resolver() entero (include() anidados) y los manejadores de error (handler400/403/404/
500) y resuelve cada callback a su MÓDULO real: view_class (vistas de clase de Django/DRF), cls
(ViewSets/@api_view de DRF, que copian el __module__ de la función decorada) o el propio callback.
El módulo se traduce al ARCHIVO (ruta relativa a backend/, separador "/") para que el gate de
cobertura (gate_cobertura.py --vistas-urlconf) exija que toda vista servida esté clasificada como
crítica o no crítica, se llame como se llame el archivo (vistas_mfa.py, endpoints.py, ...).
Los módulos fuera de backend/ (Django, DRF, terceros) se listan aparte en "externos".
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Any


def modulo_de(callback: Any) -> str:
    for attr in ("view_class", "cls"):
        clase = getattr(callback, attr, None)
        if clase is not None and getattr(clase, "__module__", None):
            return str(clase.__module__)
    return str(getattr(callback, "__module__", "") or "")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("uso: " + __doc__.splitlines()[3].strip() + "\n")
        return 2
    raiz = pathlib.Path.cwd().resolve()
    sys.path.insert(0, str(raiz))
    try:
        import django

        django.setup()
        from django.urls import URLPattern, URLResolver, get_resolver
    except Exception as exc:  # falla cerrado con el motivo, sea cual sea
        sys.stdout.write(
            f"::error::vistas_urlconf: Django no carga ({type(exc).__name__}: {exc})\n"
        )
        return 1

    rutas: list[tuple[str, str]] = []

    def recorrer(patrones: list[Any], prefijo: str) -> None:
        for p in patrones:
            if isinstance(p, URLResolver):
                recorrer(p.url_patterns, prefijo + str(p.pattern))
            elif isinstance(p, URLPattern):
                rutas.append((prefijo + str(p.pattern), modulo_de(p.callback)))

    resolver = get_resolver()
    recorrer(resolver.url_patterns, "/")
    for codigo in (400, 403, 404, 500):
        rutas.append((f"handler{codigo}", modulo_de(resolver.resolve_error_handler(codigo))))

    archivos: dict[str, list[str]] = {}
    externos: dict[str, list[str]] = {}
    for ruta, mod in rutas:
        fichero = getattr(sys.modules.get(mod), "__file__", None)
        rel = None
        if fichero:
            try:
                rel = pathlib.Path(fichero).resolve().relative_to(raiz).as_posix()
            except ValueError:
                rel = None
        if rel is not None and not rel.startswith((".venv/", "venv/")):
            archivos.setdefault(rel, []).append(ruta)
        else:
            externos.setdefault(mod or "<desconocido>", []).append(ruta)

    if not archivos:
        sys.stdout.write("::error::vistas_urlconf: el URLconf no sirve ninguna vista del backend\n")
        return 1
    salida = {"archivos": archivos, "externos": externos}
    pathlib.Path(argv[1]).write_text(
        json.dumps(salida, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    total = sum(len(v) for v in archivos.values())
    sys.stdout.write(
        f"vistas del URLconf: {total} rutas en {len(archivos)} archivos del backend, "
        f"{sum(len(v) for v in externos.values())} en {len(externos)} módulos externos "
        f"(DJANGO_SETTINGS_MODULE={os.environ.get('DJANGO_SETTINGS_MODULE', '')})\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
