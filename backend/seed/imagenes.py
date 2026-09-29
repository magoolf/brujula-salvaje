"""Generador de ilustraciones propias (RSK-002, DEC-AUTO-014, REQ-043).

No se descargan fotografías ni bancos de imágenes de terceros: cada medio de la semilla es una
ilustración geométrica abstracta generada por este módulo con Pillow (ya es dependencia del
backend, `apps.medios.services`), determinista por "semilla" (slug + índice) para que el comando
sea idempotente (la misma entrada produce siempre los mismos bytes -> el `huella_sha256` de
`apps.medios.services.subir_medios` deduplica en reintentos).

Deliberadamente NO intenta imitar una fotografía real (sin degradados fotorrealistas, sin
texturas): paleta plana + formas geométricas simples (franjas, círculo, triángulos), en el
espíritu de un cartel/icono editorial. `LADO_MAYOR_MINIMO_PX` (apps.medios.models) exige >=1200px
de lado mayor: se genera a 1600x1200.
"""

from __future__ import annotations

import hashlib
import io
import math

from PIL import Image, ImageDraw

ANCHO = 1600
ALTO = 1200


def _entero_estable(semilla: str, sal: str, modulo: int) -> int:
    digest = hashlib.sha256(f"{semilla}:{sal}".encode()).hexdigest()
    return int(digest[:8], 16) % modulo


def _color_hsl_a_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:  # noqa: E741
    """HSL -> RGB (0..1) sin dependencias extra: fórmula estándar."""
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if h < 60:
        r, g, b = c, x, 0.0
    elif h < 120:
        r, g, b = x, c, 0.0
    elif h < 180:
        r, g, b = 0.0, c, x
    elif h < 240:
        r, g, b = 0.0, x, c
    elif h < 300:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x
    return (round((r + m) * 255), round((g + m) * 255), round((b + m) * 255))


def _paleta(
    semilla: str,
) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    """3 colores armónicos (mismo matiz base, distinta luminosidad) derivados de la semilla."""
    matiz = _entero_estable(semilla, "matiz", 360)
    fondo = _color_hsl_a_rgb(matiz, 0.45, 0.28)
    medio = _color_hsl_a_rgb((matiz + 24) % 360, 0.55, 0.46)
    acento = _color_hsl_a_rgb((matiz + 190) % 360, 0.60, 0.72)
    return fondo, medio, acento


def generar_ilustracion(semilla: str, *, variante: int = 0) -> bytes:
    """PNG determinista (mismo `semilla`+`variante` -> mismos bytes) de una escena abstracta.

    Compone franjas horizontales (cielo/tierra), un círculo (sol/luna) y una silueta de
    triángulos (montañas/olas esquemáticas): un icono editorial, no una fotografía.
    """
    clave = f"{semilla}#{variante}"
    fondo, medio, acento = _paleta(clave)
    imagen = Image.new("RGB", (ANCHO, ALTO), color=fondo)
    dibujo = ImageDraw.Draw(imagen)

    horizonte = ALTO - _entero_estable(clave, "horizonte", ALTO // 3) - ALTO // 4
    dibujo.rectangle([0, horizonte, ANCHO, ALTO], fill=medio)

    radio_sol = 90 + _entero_estable(clave, "radio", 120)
    cx = _entero_estable(clave, "cx", ANCHO)
    cy = max(radio_sol + 20, horizonte - _entero_estable(clave, "cy", horizonte // 2))
    dibujo.ellipse([cx - radio_sol, cy - radio_sol, cx + radio_sol, cy + radio_sol], fill=acento)

    n_picos = 4 + _entero_estable(clave, "picos", 4)
    ancho_pico = ANCHO / n_picos
    for i in range(n_picos):
        altura_pico = horizonte - (
            40 + _entero_estable(f"{clave}:{i}", "altura", int(horizonte * 0.6))
        )
        x0 = i * ancho_pico
        xm = x0 + ancho_pico / 2
        x1 = x0 + ancho_pico
        dibujo.polygon([(x0, horizonte), (xm, max(0, altura_pico)), (x1, horizonte)], fill=fondo)

    n_franjas = 3 + _entero_estable(clave, "franjas", 3)
    for i in range(n_franjas):
        y = ALTO - (i + 1) * (ALTO - horizonte) / (n_franjas + 2)
        amplitud = 12 + _entero_estable(f"{clave}:onda:{i}", "amp", 18)
        puntos = []
        pasos = 40
        for p in range(pasos + 1):
            x = ANCHO * p / pasos
            y_onda = y + amplitud * math.sin((p / pasos) * 2 * math.pi + i)
            puntos.append((x, y_onda))
        dibujo.line(puntos, fill=acento, width=3)

    salida = io.BytesIO()
    imagen.save(salida, format="PNG")
    return salida.getvalue()
