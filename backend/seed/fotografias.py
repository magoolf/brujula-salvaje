"""Fotografías reales de la carga semilla (TKT-041, REQ-043, REQ-071, DEC-AUTO-967).

Sustituye a las ilustraciones geométricas de TKT-007 (DEC-AUTO-014). Las fotos viven en el
repositorio, en `seed/fotos/`, ya redimensionadas y recodificadas sin metadatos; su procedencia
está en `seed/fotos/MANIFIESTO.json`, una entrada por archivo con:

- `archivo` y `sha256` (integridad: se comprueba al leer, nunca se sube un archivo alterado);
- `titulo_commons`, `pagina` (URL de la página del archivo en Wikimedia Commons), `autor`;
- `licencia` (código del catálogo `apps.catalogos.Licencia`), `licencia_commons` y
  `url_licencia` (texto legal);
- `alt` (texto alternativo en español, redactado tras verificar visualmente cada imagen);
- `asignado_a`: claves `tipo:slug`, `destino:slug:n` (0 = portada, 1..3 = galería),
  `itinerario:slug`, `guia:slug`, `coleccion:slug` e `inicio:hero`.

Solo se aceptan CC0, dominio público, CC BY y CC BY-SA (`LICENCIAS_ADMITIDAS`): nada NC/ND.
Sin descargas en tiempo de ejecución: todo sale del repositorio. Este módulo es solo DATOS (no
toca el ORM); la subida y catalogación la hace `cargar_semilla` con los servicios de
`apps.medios`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "fotos"
MANIFIESTO = CARPETA / "MANIFIESTO.json"

LICENCIAS_ADMITIDAS = frozenset(
    {
        "CC0-1.0",
        "PDM-1.0",
        "CC-BY-2.0",
        "CC-BY-2.5",
        "CC-BY-3.0",
        "CC-BY-4.0",
        "CC-BY-SA-2.0",
        "CC-BY-SA-2.5",
        "CC-BY-SA-3.0",
        "CC-BY-SA-4.0",
    }
)


class FotoNoDisponibleError(LookupError):
    """No hay foto para una asignación o el archivo no coincide con su huella."""


@dataclass(frozen=True)
class Foto:
    archivo: str
    sha256: str
    titulo_commons: str
    pagina: str
    autor: str
    licencia: str
    url_licencia: str
    alt: str
    asignado_a: tuple[str, ...]

    def leer(self) -> bytes:
        """Bytes del archivo, verificados contra la huella del manifiesto."""
        ruta = CARPETA / self.archivo
        if not ruta.is_file():
            raise FotoNoDisponibleError(f"Falta el archivo {self.archivo}")
        datos = ruta.read_bytes()
        if hashlib.sha256(datos).hexdigest() != self.sha256:
            raise FotoNoDisponibleError(f"La huella de {self.archivo} no coincide con el manifiesto")
        return datos


@cache
def fotos() -> tuple[Foto, ...]:
    contenido = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    return tuple(
        Foto(
            archivo=f["archivo"],
            sha256=f["sha256"],
            titulo_commons=f["titulo_commons"],
            pagina=f["pagina"],
            autor=f["autor"],
            licencia=f["licencia"],
            url_licencia=f["url_licencia"],
            alt=f["alt"],
            asignado_a=tuple(f["asignado_a"]),
        )
        for f in contenido["fotos"]
    )


@cache
def _por_asignacion() -> dict[str, Foto]:
    indice: dict[str, Foto] = {}
    for foto in fotos():
        for clave in foto.asignado_a:
            if clave in indice:
                raise FotoNoDisponibleError(f"Asignación duplicada en el manifiesto: {clave}")
            indice[clave] = foto
    return indice


def foto_para(asignacion: str) -> Foto:
    """Foto asignada a `asignacion` (p. ej. `destino:dolomitas:0`); error si no existe."""
    foto = _por_asignacion().get(asignacion)
    if foto is None:
        raise FotoNoDisponibleError(f"El manifiesto no tiene foto para «{asignacion}»")
    return foto
