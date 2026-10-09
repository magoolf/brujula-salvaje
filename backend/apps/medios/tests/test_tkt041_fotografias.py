"""TKT-041 (REQ-043, REQ-071, DEC-AUTO-967): integridad del manifiesto de fotografías de la semilla.

Sin base de datos: comprueba que `seed/fotos/MANIFIESTO.json` y los archivos que describe son
coherentes (huella, dimensiones, sin metadatos, tamaño acotado), que solo hay licencias libres
admitidas con autor, página de Commons y alt en español, y que cubre exactamente cada imagen que
pide la carga semilla (portadas, galerías de destino, colecciones y portada de inicio).
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image

from seed import colecciones, destinos, fotografias, guias, itinerarios, tipos_aventura

COMMONS = "https://commons.wikimedia.org/wiki/File:"
LIMITE_REPO_BYTES = 25 * 1024 * 1024  # tamaño acotado en el repositorio (ticket TKT-041)
LADO_MAYOR_MAX = 1920
URL_LICENCIA = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "PDM-1.0": "https://creativecommons.org/publicdomain/mark/1.0/",
    "CC-BY-2.0": "https://creativecommons.org/licenses/by/2.0/",
    "CC-BY-2.5": "https://creativecommons.org/licenses/by/2.5/",
    "CC-BY-3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC-BY-SA-2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
    "CC-BY-SA-2.5": "https://creativecommons.org/licenses/by-sa/2.5/",
    "CC-BY-SA-3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
}


def _asignaciones_requeridas() -> set[str]:
    claves = {f"tipo:{t.slug}" for t in tipos_aventura.TIPOS}
    claves |= {f"destino:{d.slug}:{i}" for d in destinos.DESTINOS for i in range(4)}
    claves |= {f"itinerario:{it.slug}" for it in itinerarios.ITINERARIOS}
    claves |= {f"guia:{g.slug}" for g in guias.GUIAS}
    claves |= {f"coleccion:{c.slug}" for c in colecciones.COLECCIONES}
    claves.add("inicio:hero")
    return claves


def test_TKT041_manifiesto_cubre_exactamente_las_imagenes_de_la_semilla() -> None:
    asignadas = [clave for foto in fotografias.fotos() for clave in foto.asignado_a]
    assert len(asignadas) == len(set(asignadas)), "asignación duplicada"
    assert set(asignadas) == _asignaciones_requeridas()
    for clave in _asignaciones_requeridas():
        assert fotografias.foto_para(clave).archivo


def test_TKT041_archivos_integros_sin_metadatos_y_tamano_acotado() -> None:
    fotos = fotografias.fotos()
    archivos = {f.archivo for f in fotos}
    assert len(archivos) == len(fotos)
    assert len({f.sha256 for f in fotos}) == len(fotos)  # sin fotos repetidas
    en_disco = {p.name for p in fotografias.CARPETA.glob("*.jpg")}
    assert en_disco == archivos  # ni huérfanos ni ausentes
    total = 0
    entradas = {
        e["archivo"]: e
        for e in json.loads(fotografias.MANIFIESTO.read_text(encoding="utf-8"))["fotos"]
    }
    for foto in fotos:
        datos = foto.leer()  # verifica la huella
        total += len(datos)
        assert entradas[foto.archivo]["bytes"] == len(datos)
        # CC BY/BY-SA exigen indicar los cambios: cada entrada declara sus modificaciones.
        assert "respecto al original" in entradas[foto.archivo]["modificaciones"]
        with Image.open(io.BytesIO(datos)) as imagen:
            assert imagen.format == "JPEG"
            assert imagen.mode == "RGB"
            assert (imagen.width, imagen.height) == (
                entradas[foto.archivo]["ancho"],
                entradas[foto.archivo]["alto"],
            )
            assert max(imagen.size) <= LADO_MAYOR_MAX
            # Apaisadas (portadas y tarjetas recortan con object-fit), panorámicas hasta ~3:1.
            assert 1.0 <= imagen.width / imagen.height <= 3.2
            assert min(imagen.size) >= 380
            assert not imagen.getexif(), f"{foto.archivo} conserva EXIF"
            assert "icc_profile" not in imagen.info or imagen.info["icc_profile"] is None
    total += fotografias.MANIFIESTO.stat().st_size
    assert total <= LIMITE_REPO_BYTES


def test_TKT041_licencias_libres_con_autor_fuente_y_alt_en_espanol() -> None:
    for foto in fotografias.fotos():
        assert foto.licencia in fotografias.LICENCIAS_ADMITIDAS
        assert foto.url_licencia == URL_LICENCIA[foto.licencia]
        assert foto.autor.strip() and "<" not in foto.autor and len(foto.autor) <= 150
        assert foto.pagina.startswith(COMMONS)
        assert foto.titulo_commons.startswith("File:")
        alt = foto.alt.strip()
        assert 20 <= len(alt) <= 250
        assert "ilustración" not in alt.lower() and "imagen de" not in alt.lower()
    # Nada con cláusulas NC/ND ni licencias ajenas a la lista cerrada.
    assert not any("NC" in lic or "ND" in lic for lic in fotografias.LICENCIAS_ADMITIDAS)


def test_TKT041_error_explicito_si_falta_asignacion_archivo_o_huella(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(fotografias.FotoNoDisponibleError, match="no tiene foto"):
        fotografias.foto_para("destino:inexistente:0")

    foto = fotografias.foto_para("inicio:hero")
    monkeypatch.setattr(fotografias, "CARPETA", tmp_path)
    with pytest.raises(fotografias.FotoNoDisponibleError, match="Falta el archivo"):
        foto.leer()
    (tmp_path / foto.archivo).write_bytes(b"alterado")
    with pytest.raises(fotografias.FotoNoDisponibleError, match="huella"):
        foto.leer()


def test_TKT041_asignacion_duplicada_en_el_manifiesto_se_rechaza(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = fotografias.fotos()
    duplicada = (*original, original[0])
    fotografias._por_asignacion.cache_clear()
    monkeypatch.setattr(fotografias, "fotos", lambda: duplicada)
    try:
        with pytest.raises(fotografias.FotoNoDisponibleError, match="duplicada"):
            fotografias.foto_para("inicio:hero")
    finally:
        fotografias._por_asignacion.cache_clear()


# ---------------------------------------------------------------------------
# QA TKT-041 F-01 (WCAG 1.4.3): la portada de inicio debe dejar legible el texto del hero.
# Geometría medida en Chromium (cajas del bloque principal y de cada texto, en fracciones del
# hero) con el CSS actual de `pagina-inicio.css`: `object-fit: cover` centrado y velo
# `linear-gradient(to top, 0.78, 0.2 al 60 %, transparente)`. Es una guardia de regresión de la
# FOTO (percentil 99 de luminancia bajo cada caja de texto); la medición por píxel de glifo al
# 100 % se hace en navegador (evidencia del ticket). El CSS del hero es de TKT-047.
# ---------------------------------------------------------------------------
_HERO_VISTAS = {
    # vista: (ancho_px, alto_px, {texto: (x, y, ancho, alto) en fracción del hero})
    "d1280": (1265, 560, {"overline": (0.234, 0.253, 0.531, 0.030),
                          "titular": (0.234, 0.311, 0.531, 0.220),
                          "subtitulo": (0.234, 0.560, 0.481, 0.054)}),
    "d1366": (1351, 630, {"overline": (0.251, 0.336, 0.497, 0.027),
                          "titular": (0.251, 0.388, 0.497, 0.196),
                          "subtitulo": (0.251, 0.609, 0.450, 0.048)}),
    "m390": (375, 591, {"overline": (0.043, 0.330, 0.915, 0.029),
                        "titular": (0.043, 0.385, 0.915, 0.119),
                        "subtitulo": (0.043, 0.532, 0.915, 0.103)}),
}  # fmt: skip
# Color del texto (tokens ink-300 y sand-50) y contraste mínimo WCAG por texto.
_HERO_TEXTO = {"overline": ((184, 194, 188), 4.5), "titular": ((251, 248, 243), 3.0),
               "subtitulo": ((251, 248, 243), 4.5)}  # fmt: skip


def _luminancia(rgb: tuple[int, int, int]) -> float:
    def canal(c: int) -> float:
        v = c / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def _velo(fraccion_desde_abajo: float) -> float:
    f = fraccion_desde_abajo
    return 0.78 + (0.2 - 0.78) * f / 0.6 if f <= 0.6 else 0.2 * (1 - (f - 0.6) / 0.4)


def test_TKT041_portada_de_inicio_deja_el_texto_del_hero_con_contraste_wcag() -> None:
    foto = fotografias.foto_para("inicio:hero")
    with Image.open(io.BytesIO(foto.leer())) as original:
        imagen = original.convert("RGB")
    ancho0, alto0 = imagen.size
    pixeles = imagen.load()
    assert pixeles is not None
    for vista, (ancho, alto, cajas) in _HERO_VISTAS.items():
        escala = max(ancho / ancho0, alto / alto0)
        ox, oy = (ancho0 * escala - ancho) / 2, (alto0 * escala - alto) / 2
        for texto, (fx, fy, fw, fh) in cajas.items():
            color, minimo = _HERO_TEXTO[texto]
            fondo = []
            for y in range(int(fy * alto), int((fy + fh) * alto), 2):
                velo = _velo(1 - y / alto)
                for x in range(int(fx * ancho), int((fx + fw) * ancho), 2):
                    sx = min(ancho0 - 1, int((x + ox) / escala))
                    sy = min(alto0 - 1, int((y + oy) / escala))
                    fondo.append(_luminancia(pixeles[sx, sy]) * (1 - velo))  # type: ignore[arg-type]
            fondo.sort()
            p99 = fondo[int(0.99 * (len(fondo) - 1))]
            contraste = (_luminancia(color) + 0.05) / (p99 + 0.05)
            assert contraste >= minimo, f"{vista} {texto}: {contraste:.2f} < {minimo}"
