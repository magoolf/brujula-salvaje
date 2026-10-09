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
        with Image.open(io.BytesIO(datos)) as imagen:
            assert imagen.format == "JPEG"
            assert imagen.mode == "RGB"
            assert (imagen.width, imagen.height) == (
                entradas[foto.archivo]["ancho"],
                entradas[foto.archivo]["alto"],
            )
            assert max(imagen.size) <= LADO_MAYOR_MAX
            assert min(imagen.size) >= 480  # panorámicas incluidas
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
