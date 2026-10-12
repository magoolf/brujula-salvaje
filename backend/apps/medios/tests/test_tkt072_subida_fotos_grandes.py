"""TKT-072 (OBS-QA071-01): subida de fotos de cámara grandes dentro de los límites (≤ 40 MP).

Causa raíz: `_resanear` copiaba los píxeles con `putdata(get_flattened_data())`, que crea una tupla
de Python por píxel (17 M tuplas con 17 MP, varios GiB); con el límite de 1 GiB del contenedor del
backend tardaba ~400 s y gunicorn (timeout 120 s) mataba el worker. Además los derivados incluían
siempre el ancho original en los tres formatos (el 65-85 % de la codificación con una foto de
cámara). Ahora la copia sin metadatos se hace en C (`paste`) y el derivado mayor se acota a
`ANCHO_MAXIMO_DERIVADO` (DEC-AUTO-1320/1321, ADR-medios-002), sin perder el saneo de EXIF/GPS/XMP.
"""

from __future__ import annotations

import io
import os
import time
from pathlib import Path
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.medios import services
from apps.medios.models import FormatoDerivado

AVIF, WEBP, JPEG = FormatoDerivado.AVIF, FormatoDerivado.WEBP, FormatoDerivado.JPEG
# Rastros de metadatos que no pueden aparecer en ningún archivo generado (THREAT-007): bloque
# EXIF (JPEG APP1 / ítem Exif de AVIF), XMP y los valores inyectados; el chunk EXIF de WebP
# lo cubre `getexif()` (4 bytes podrían aparecer por azar en los datos comprimidos).
MARCADORES = (b"Exif\x00\x00", b"<x:xmpmeta", b"http://ns.adobe.com", b"CamaraTKT072")


def _exif_con_gps() -> bytes:
    exif = Image.Exif()
    exif[0x010F] = "CamaraTKT072"  # Make
    exif[0x0110] = "ModeloTKT072"  # Model
    exif[0x8825] = {1: "N", 2: (40.0, 25.0, 0.0), 3: "W", 4: (3.0, 42.0, 0.0)}  # GPSInfo
    return exif.tobytes()


XMP = (
    b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
    b'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description '
    b'xmlns:exif="http://ns.adobe.com/exif/1.0/" exif:GPSLatitude="40,25.0N"/></rdf:RDF>'
    b"</x:xmpmeta>"
)
ICC_FALSO = bytes(128)


def _foto_con_metadatos(ancho: int, alto: int) -> bytes:
    """JPEG con detalle (degradado + ruido), EXIF con GPS, XMP e ICC."""
    degradado = Image.linear_gradient("L").resize((ancho, alto))
    ruido = Image.effect_noise((ancho, alto), 48)
    imagen = Image.merge("RGB", (degradado, ruido, Image.blend(degradado, ruido, 0.5)))
    buffer = io.BytesIO()
    imagen.save(
        buffer, format="JPEG", quality=85, exif=_exif_con_gps(), xmp=XMP, icc_profile=ICC_FALSO
    )
    return buffer.getvalue()


def _copia_previa(imagen: Image.Image) -> Image.Image:
    """La copia de antes de TKT-072 (`putdata`), como referencia píxel a píxel."""
    modo = "RGB" if imagen.mode not in ("RGB", "RGBA") else imagen.mode
    limpia = Image.new(modo, imagen.size)
    limpia.putdata(imagen.convert(modo).get_flattened_data())
    return limpia


def _imagen_de_modo(modo: str) -> Image.Image:
    degradado = Image.linear_gradient("L").resize((64, 48))
    ruido = Image.effect_noise((64, 48), 60)
    base = Image.merge("RGB", (degradado, ruido, degradado.rotate(180)))
    if modo == "RGBA":
        return Image.merge("RGBA", (*base.split(), ruido.rotate(180)))
    if modo == "LA":
        return Image.merge("LA", (ruido, degradado))
    if modo == "P":
        return base.convert("P", palette=Image.Palette.ADAPTIVE)
    if modo == "I;16":
        return degradado.convert("I;16")
    return base.convert(modo)


@pytest.mark.parametrize("modo", ["RGB", "RGBA", "L", "LA", "P", "CMYK", "I;16"])
def test_AC_TKT072_01_copia_sin_metadatos_identica_a_la_previa(modo: str) -> None:
    origen = _imagen_de_modo(modo)
    origen.info = {
        "exif": _exif_con_gps(),
        "xmp": XMP,
        "icc_profile": ICC_FALSO,
        "dpi": (300, 300),
    }

    limpia = services._imagen_sin_metadatos(origen)

    referencia = _copia_previa(origen)
    assert limpia.mode == referencia.mode
    assert limpia.size == origen.size
    assert limpia.tobytes() == referencia.tobytes()
    assert limpia.info == {}
    assert not limpia.getexif()
    assert origen.info.get("exif")  # la entrada no se modifica


def test_AC_TKT072_02_la_copia_no_crea_objetos_por_pixel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regresión de la causa raíz: ni `putdata` ni `get_flattened_data`/`getdata`."""

    def prohibido(*_: Any, **__: Any) -> None:
        raise AssertionError("copia píxel a píxel en Python (OBS-QA071-01)")

    for metodo in ("putdata", "getdata", "get_flattened_data"):
        if hasattr(Image.Image, metodo):
            monkeypatch.setattr(Image.Image, metodo, prohibido)
    origen = Image.effect_noise((4800, 3600), 64).convert("RGB")  # 17 MP, como la de QA
    inicio = time.perf_counter()
    limpia = services._imagen_sin_metadatos(origen)
    duracion = time.perf_counter() - inicio
    assert limpia.size == (4800, 3600)
    # Antes ~400 s en el contenedor; en C es del orden de 0,1 s. Margen amplio para la CI.
    assert duracion < 10, duracion


@pytest.mark.parametrize(
    ("ancho", "esperados"),
    [
        (1200, [400, 800, 1200]),
        (1300, [400, 800, 1200, 1300]),
        (1920, [400, 800, 1200, 1600, 1920]),
        (2000, [400, 800, 1200, 1600, 2000]),
        (2560, [400, 800, 1200, 1600, 2000, 2560]),
        (4000, [400, 800, 1200, 1600, 2000, 2560]),
        (7302, [400, 800, 1200, 1600, 2000, 2560]),
    ],
)
def test_AC_TKT072_03_anchos_derivados_acotados(ancho: int, esperados: list[int]) -> None:
    assert services.anchos_derivados(ancho) == esperados
    # Hasta el máximo, el derivado mayor sigue siendo el ancho original (las fotos de la semilla,
    # ≤ 1920 px, no cambian).
    assert services.anchos_derivados(ancho)[-1] == min(ancho, services.ANCHO_MAXIMO_DERIVADO)


def test_AC_TKT072_04_preparar_subida_sanea_gps_exif_xmp_y_acota_derivados(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Original saneado y derivados sin ningún marcador de metadatos; el derivado mayor acotado.
    El máximo se baja a 1200 para ejercitar la cota con una imagen pequeña (prueba ligera)."""
    monkeypatch.setattr(services, "ANCHO_MAXIMO_DERIVADO", 1200)
    contenido = _foto_con_metadatos(1500, 1000)
    with Image.open(io.BytesIO(contenido)) as origen:
        assert origen.getexif().get_ifd(0x8825)  # la entrada SÍ lleva GPS
        assert "xmp" in origen.info
    assert all(m in contenido for m in (b"Exif\x00\x00", b"<x:xmpmeta", b"CamaraTKT072"))

    archivo = SimpleUploadedFile("camara.jpg", contenido, content_type="image/jpeg")
    monkeypatch.setattr(services, "_medio_por_huella", lambda _huella: None)  # sin BD
    (preparada,) = services.preparar_subida([archivo])

    assert preparada.resultado is None
    assert (preparada.ancho_px, preparada.alto_px) == (1500, 1000)
    assert preparada.extension == "jpg"
    assert preparada.codificacion is not None
    generados = [preparada.saneado] + [d.contenido for d in preparada.codificacion.derivados]
    for datos in generados:
        for marcador in MARCADORES:
            assert marcador not in datos, marcador
        with Image.open(io.BytesIO(datos)) as leida:
            assert not leida.getexif()
            for clave in ("exif", "xmp", "icc_profile", "XML:com.adobe.xmp"):
                assert not leida.info.get(clave), clave
    with Image.open(io.BytesIO(preparada.saneado)) as saneada:
        assert saneada.size == (1500, 1000)
    anchos = sorted({d.ancho for d in preparada.codificacion.derivados})
    assert anchos == [400, 800, 1200]
    assert {d.formato for d in preparada.codificacion.derivados if d.ancho == 1200} >= {JPEG}


def test_AC_TKT072_05_png_con_alfa_conserva_alfa_sin_metadatos() -> None:
    rgba = Image.merge(
        "RGBA",
        (
            Image.linear_gradient("L").resize((1300, 900)),
            Image.effect_noise((1300, 900), 40),
            Image.linear_gradient("L").rotate(90).resize((1300, 900)),
            Image.linear_gradient("L").resize((1300, 900)),
        ),
    )
    buffer = io.BytesIO()
    rgba.save(buffer, format="PNG", exif=_exif_con_gps())
    _, imagen = services._validar_formato_y_tamano(buffer.getvalue())
    limpia = services._imagen_sin_metadatos(imagen)
    contenido, _sha, extension = services._resanear(limpia)
    assert extension == "png"
    for marcador in MARCADORES:
        assert marcador not in contenido
    with Image.open(io.BytesIO(contenido)) as leida:
        assert leida.mode == "RGBA"
        assert leida.tobytes() == rgba.tobytes()
        assert not leida.getexif()


def _cpu_del_proceso() -> int:
    if hasattr(os, "sched_getaffinity"):
        return len(os.sched_getaffinity(0))
    return os.cpu_count() or 1


@pytest.mark.parametrize(
    ("contenido", "cuota"),
    [
        ("150000 100000\n", 2),  # cuota de 1,5 CPU (compose.yaml del backend) -> techo 2
        ("100000 100000\n", 1),
        ("50000 100000\n", 1),
        ("max 100000\n", None),  # sin cuota: las CPU del proceso
        ("basura\n", None),
    ],
)
def test_AC_TKT072_06_hilos_del_codificador_segun_la_cuota_de_cpu(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contenido: str, cuota: int | None
) -> None:
    """DEC-AUTO-1323: con los hilos por omisión de Pillow (las CPU del host) bajo una cuota de
    1,5 CPU cada AVIF tardaba el doble."""
    cpu_max = tmp_path / "cpu.max"
    cpu_max.write_text(contenido)
    monkeypatch.setattr(services, "RUTA_CPU_MAX_CGROUP", cpu_max)
    services.hilos_codificador.cache_clear()
    try:
        hilos = services.hilos_codificador()
    finally:
        services.hilos_codificador.cache_clear()
    disponibles = _cpu_del_proceso()
    assert hilos == (disponibles if cuota is None else min(cuota, disponibles))


def test_AC_TKT072_06_sin_cgroup_usa_las_cpu_del_proceso(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(services, "RUTA_CPU_MAX_CGROUP", tmp_path / "no-existe")
    services.hilos_codificador.cache_clear()
    try:
        assert services.hilos_codificador() == _cpu_del_proceso()
    finally:
        services.hilos_codificador.cache_clear()


def test_AC_TKT072_06_el_avif_se_codifica_con_esos_hilos(monkeypatch: pytest.MonkeyPatch) -> None:
    recibidos: dict[str, dict[str, Any]] = {}
    original = Image.Image.save

    def espia(self: Image.Image, fp: Any, format: str | None = None, **params: Any) -> None:
        recibidos[str(format)] = params
        original(self, fp, format=format, **params)

    monkeypatch.setattr(Image.Image, "save", espia)
    monkeypatch.setattr(services, "hilos_codificador", lambda: 2)
    imagen = Image.effect_noise((64, 48), 40).convert("RGB")
    for formato in (AVIF, WEBP, JPEG):
        services._codificar(imagen, formato)
    assert recibidos["AVIF"]["max_threads"] == 2
    assert "max_threads" not in recibidos["WEBP"]
    assert "max_threads" not in recibidos["JPEG"]
