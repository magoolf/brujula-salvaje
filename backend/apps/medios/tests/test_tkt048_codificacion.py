"""TKT-048 (QA TKT-041 F-02): codificación explícita de los derivados y su regeneración.

Causa raíz del LCP > 2,5 s en Inicio y fichas: los derivados se guardaban con los valores por
defecto de Pillow (sin `quality`/`speed`), y el AVIF de 800 px -- el que elige un móvil a DPR 1,75
y el primero que prueba el `<picture>` -- pesaba 94-174 KB, a menudo MÁS que el WebP y el JPEG.

Se prueba con fotografías reales de la semilla (`seed/fotos`, las mismas que sirve el sitio) y con
imágenes sintéticas extremas (planas y ruido) para la garantía de orden de pesos.
"""

from __future__ import annotations

import io
import secrets
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image

from apps.catalogos.models import Licencia
from apps.contenido.tests.fabricas import crear_cuenta
from apps.medios import services
from apps.medios.models import EstadoMedio, FormatoDerivado, Medio, MedioDerivado
from seed import fotografias

AVIF, WEBP, JPEG = FormatoDerivado.AVIF, FormatoDerivado.WEBP, FormatoDerivado.JPEG
# Fotos de la semilla que son imagen LCP en las rutas medidas (Inicio y fichas de destino).
CLAVES_LCP = ("inicio:hero", "destino:dolomitas:0", "destino:bahia-de-ha-long:0")
# PERFORMANCE_SPEC (HANDOFF_UI_UX): imagen LCP ≤ 200 KB en móvil; tarjeta ≤ 60 KB. Con los nuevos
# parámetros el AVIF de 800 px (LCP en móvil) queda muy por debajo; el umbral deja margen a fotos
# con mucho detalle sin permitir volver a los valores por defecto (94-174 KB en la semilla).
MAX_AVIF_800 = 90 * 1024
MAX_AVIF_400 = 30 * 1024


def _foto(clave: str) -> Image.Image:
    imagen = Image.open(io.BytesIO(fotografias.foto_para(clave).leer()))
    imagen.load()
    return imagen


def _por_ancho(
    derivados: list[services.DerivadoCodificado],
) -> dict[int, dict[str, services.DerivadoCodificado]]:
    tabla: dict[int, dict[str, services.DerivadoCodificado]] = {}
    for d in derivados:
        tabla.setdefault(d.ancho, {})[d.formato] = d
    return tabla


def _comprobar_orden(formatos: dict[str, Any], peso: Any) -> None:
    """AVIF ≤ WebP ≤ JPEG entre los formatos presentes."""
    presentes = [f for f in (AVIF, WEBP, JPEG) if f in formatos]
    pesos = [peso(formatos[f]) for f in presentes]
    assert pesos == sorted(pesos), dict(zip(presentes, pesos, strict=True))


# ---------------------------------------------------------------------------
# Parámetros de codificación
# ---------------------------------------------------------------------------
def test_AC_TKT048_01_parametros_de_codificacion_explicitos() -> None:
    avif = services.PARAMETROS_CODIFICACION[AVIF]
    webp = services.PARAMETROS_CODIFICACION[WEBP]
    jpeg = services.PARAMETROS_CODIFICACION[JPEG]
    assert 50 <= avif["quality"] <= 60 and 0 <= avif["speed"] <= 10
    assert 75 <= webp["quality"] <= 80
    assert jpeg["quality"] == 80 and jpeg["progressive"] is True
    # Los reintentos solo bajan la calidad.
    assert all(q < avif["quality"] for q in services.CALIDADES_REINTENTO[AVIF])
    assert all(q < webp["quality"] for q in services.CALIDADES_REINTENTO[WEBP])


@pytest.mark.parametrize("clave", CLAVES_LCP)
def test_AC_TKT048_02_fotos_reales_orden_de_pesos_y_presupuesto(clave: str) -> None:
    codificacion = services._codificar_derivados(_foto(clave))
    tabla = _por_ancho(codificacion.derivados)
    assert codificacion.no_soportados == frozenset()  # la imagen del backend escribe AVIF
    for ancho, formatos in tabla.items():
        # Con una fotografía real los tres formatos caben en el orden (no se descarta ninguno).
        assert set(formatos) == {AVIF, WEBP, JPEG}, ancho
        _comprobar_orden(formatos, lambda d: len(d.contenido))
    assert len(tabla[800][AVIF].contenido) <= MAX_AVIF_800
    assert len(tabla[400][AVIF].contenido) <= MAX_AVIF_400


@pytest.mark.parametrize("clave", CLAVES_LCP[:1])
def test_AC_TKT048_03_formato_real_jpeg_progresivo_y_sin_metadatos(clave: str) -> None:
    origen = _foto(clave)
    # Se le inyectan metadatos para comprobar que ninguno llega a los derivados (THREAT-007).
    exif = Image.Exif()
    exif[0x010F] = "Fabricante"  # Make
    exif[0x0110] = "Modelo"  # Model
    buffer = io.BytesIO()
    origen.save(buffer, format="JPEG", exif=exif.tobytes(), icc_profile=b"\0" * 128)
    con_metadatos = Image.open(io.BytesIO(buffer.getvalue()))
    con_metadatos.load()
    assert "exif" in con_metadatos.info

    for derivado in services._codificar_derivados(con_metadatos).derivados:
        with Image.open(io.BytesIO(derivado.contenido)) as leida:
            assert leida.format == str(derivado.formato)
            assert leida.size == (derivado.ancho, derivado.alto)
            for clave_meta in ("exif", "xmp", "icc_profile", "XML:com.adobe.xmp"):
                assert not leida.info.get(clave_meta), (derivado.formato, clave_meta)
            if derivado.formato == JPEG:
                assert leida.info.get("progressive") or leida.info.get("progression")


# ---------------------------------------------------------------------------
# Garantía de orden con imágenes sintéticas extremas
# ---------------------------------------------------------------------------
def _plana(ancho: int = 800, alto: int = 600) -> Image.Image:
    return Image.new("RGB", (ancho, alto), color=(40, 90, 160))


def _ruido(ancho: int = 800, alto: int = 600) -> Image.Image:
    return Image.frombytes("RGB", (ancho, alto), secrets.token_bytes(ancho * alto * 3))


@pytest.mark.parametrize("fabrica", [_plana, _ruido], ids=["plana", "ruido"])
def test_AC_TKT048_02_nunca_se_sirve_un_formato_mayor_que_el_menos_eficiente(fabrica: Any) -> None:
    formatos = services._codificar_ancho(fabrica(), set())
    assert JPEG in formatos  # el respaldo universal siempre existe
    _comprobar_orden(formatos, len)


def test_AC_TKT048_02_formato_que_no_cabe_ni_con_reintentos_se_descarta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si un formato eficiente pesa más que el anterior incluso con las calidades de reintento,
    no se genera (en vez de servir un AVIF/WebP mayor que el JPEG)."""
    reales = services._codificar

    def codificar(imagen: Image.Image, formato: str, calidad: int | None = None) -> bytes:
        contenido = reales(imagen, formato, calidad)
        return contenido * 50 if formato == AVIF else contenido

    monkeypatch.setattr(services, "_codificar", codificar)
    formatos = services._codificar_ancho(_foto(CLAVES_LCP[0]).resize((400, 225)), set())
    assert set(formatos) == {WEBP, JPEG}


def test_AC_TKT048_02_reintento_con_menor_calidad_cuando_el_primero_no_cabe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reales = services._codificar
    calidades: list[int | None] = []

    def codificar(imagen: Image.Image, formato: str, calidad: int | None = None) -> bytes:
        contenido = reales(imagen, formato, calidad)
        if formato == AVIF:
            calidades.append(calidad)
            if calidad is None:  # el primer intento «pesa» más que el WebP
                return contenido * 50
        return contenido

    monkeypatch.setattr(services, "_codificar", codificar)
    formatos = services._codificar_ancho(_foto(CLAVES_LCP[0]).resize((400, 225)), set())
    assert set(formatos) == {AVIF, WEBP, JPEG}
    assert calidades == [None, services.CALIDADES_REINTENTO[AVIF][0]]
    _comprobar_orden(formatos, len)


def test_AC_TKT048_02_formato_sin_codificador_se_omite_una_sola_vez(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reales = services._codificar
    intentos: list[str] = []

    def codificar(imagen: Image.Image, formato: str, calidad: int | None = None) -> bytes:
        if formato == AVIF:
            intentos.append(formato)
            raise OSError("sin libavif")
        return reales(imagen, formato, calidad)

    monkeypatch.setattr(services, "_codificar", codificar)
    codificacion = services._codificar_derivados(_foto(CLAVES_LCP[0]))
    assert codificacion.no_soportados == frozenset({AVIF})
    assert {d.formato for d in codificacion.derivados} == {WEBP, JPEG}
    assert intentos == [AVIF]  # no se reintenta en cada ancho


# ---------------------------------------------------------------------------
# Regeneración de derivados existentes (servicio y comando)
# ---------------------------------------------------------------------------
@pytest.fixture
def media_temporal(settings: Any, tmp_path: Path) -> Path:
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.fixture
def actor(db: None) -> int:
    return crear_cuenta("editora.tkt048").pk


def _subir(actor: int, clave: str = CLAVES_LCP[1]) -> Medio:
    archivo = SimpleUploadedFile(
        "foto.jpg", fotografias.foto_para(clave).leer(), content_type="image/jpeg"
    )
    medio = services.subir_medios(actor, [archivo])[0].medio
    assert medio is not None
    return medio


def _degradar_como_antes(medio: Medio, area: str) -> dict[int, bytes]:
    """Simula un derivado creado antes de TKT-048: reescribe cada AVIF con los valores por defecto
    de Pillow y guarda en BD su peso/huella. Devuelve los bytes antiguos por id de derivado."""
    antiguos: dict[int, bytes] = {}
    with Image.open(Path(settings.MEDIA_ROOT) / "privado" / medio.archivo_saneado_ruta) as o:
        base = o.convert("RGB")
    for derivado in medio.derivados.filter(formato=AVIF):
        buffer = io.BytesIO()
        base.resize((derivado.ancho_px, derivado.alto_px)).save(buffer, format="AVIF")
        contenido = buffer.getvalue()
        (Path(settings.MEDIA_ROOT) / area / derivado.ruta).write_bytes(contenido)
        derivado.peso_bytes = len(contenido)
        derivado.sha256 = services._sha256(contenido)
        derivado.save()
        antiguos[derivado.pk] = contenido
    return antiguos


def _archivo(area: str, derivado: MedioDerivado) -> Path:
    return Path(settings.MEDIA_ROOT) / area / derivado.ruta


@pytest.mark.django_db
def test_AC_TKT048_04_regenerar_actualiza_derivados_antiguos_y_es_idempotente(
    media_temporal: Path, actor: int, django_capture_on_commit_callbacks: Any
) -> None:
    medio = _subir(actor)
    antiguos = _degradar_como_antes(medio, services.RAIZ_PRIVADA)
    rutas_antes = dict(medio.derivados.values_list("pk", "ruta"))

    with django_capture_on_commit_callbacks(execute=True):
        primera = services.regenerar_derivados(medio.pk)

    # Todos cambian: los de la subida se codificaron desde el archivo subido y la regeneración
    # parte del original saneado; los «antiguos» además pesaban más.
    assert primera.actualizados == medio.derivados.count() > len(antiguos) > 0
    assert primera.creados == primera.eliminados == 0
    for derivado in medio.derivados.all():
        contenido = _archivo(services.RAIZ_PRIVADA, derivado).read_bytes()
        assert services._sha256(contenido) == derivado.sha256
        assert len(contenido) == derivado.peso_bytes
        assert not _archivo(services.RAIZ_PUBLICA, derivado).exists()  # sigue sin publicarse
        if derivado.pk in antiguos:
            assert len(contenido) < len(antiguos[derivado.pk])
        # Contenido nuevo -> URL nueva (las de /media/publico son `immutable`), y el archivo
        # antiguo se borra al confirmar.
        extension = str(derivado.formato).lower()
        assert derivado.ruta == (
            f"derivados/{medio.huella_sha256}-{derivado.ancho_px}-{derivado.sha256[:12]}.{extension}"
        )
        assert not (media_temporal / services.RAIZ_PRIVADA / rutas_antes[derivado.pk]).exists()

    with django_capture_on_commit_callbacks(execute=True):
        segunda = services.regenerar_derivados(medio.pk)
    assert (segunda.creados, segunda.actualizados, segunda.eliminados) == (0, 0, 0)
    assert segunda.sin_cambios == medio.derivados.count()
    # Ningún temporal de la escritura atómica queda en disco.
    assert not list(media_temporal.rglob("*.tmp"))


@pytest.mark.django_db
def test_AC_TKT048_04_regenerar_medio_disponible_escribe_en_publico(
    media_temporal: Path, actor: int, django_capture_on_commit_callbacks: Any
) -> None:
    medio = _subir(actor)
    licencia = Licencia.objects.filter(compatible_publicacion=True, activo=True).first()
    assert licencia is not None
    medio = services.catalogar(
        medio.pk,
        actor,
        {"texto_alternativo": "Prueba", "autor_credito": "Autor", "licencia_id": licencia.pk},
    )
    assert medio.estado == EstadoMedio.DISPONIBLE
    _degradar_como_antes(medio, services.RAIZ_PUBLICA)

    with django_capture_on_commit_callbacks(execute=True):
        resultado = services.regenerar_derivados(medio.pk)

    assert resultado.actualizados > 0
    for derivado in medio.derivados.all():
        assert _archivo(services.RAIZ_PUBLICA, derivado).is_file()
        assert not _archivo(services.RAIZ_PRIVADA, derivado).exists()
        assert services._sha256(_archivo(services.RAIZ_PUBLICA, derivado).read_bytes()) == (
            derivado.sha256
        )


@pytest.mark.django_db
def test_AC_TKT048_04_regenerar_crea_faltantes_y_elimina_descartados(
    media_temporal: Path,
    actor: int,
    django_capture_on_commit_callbacks: Any,
) -> None:
    medio = _subir(actor)
    faltante = medio.derivados.get(formato=WEBP, ancho_px=400)
    faltante.delete()
    # Un derivado que la codificación actual no produce (ancho inexistente): se elimina con su
    # archivo, que solo se borra al confirmar la transacción.
    sobrante = MedioDerivado.objects.create(
        medio=medio,
        formato=AVIF,
        ancho_px=333,
        alto_px=222,
        ruta=f"derivados/{medio.huella_sha256}-333.avif",
        peso_bytes=10,
        sha256=services._sha256(b"x"),
    )
    _archivo(services.RAIZ_PRIVADA, sobrante).write_bytes(b"x")

    with django_capture_on_commit_callbacks(execute=True):
        resultado = services.regenerar_derivados(medio.pk)

    assert (resultado.creados, resultado.eliminados) == (1, 1)
    assert medio.derivados.filter(formato=WEBP, ancho_px=400).exists()
    assert not MedioDerivado.objects.filter(pk=sobrante.pk).exists()
    assert not _archivo(services.RAIZ_PRIVADA, sobrante).exists()


@pytest.mark.django_db
def test_AC_TKT048_04_regenerar_conserva_formatos_sin_codificador(
    media_temporal: Path, actor: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    medio = _subir(actor)
    avif_antes = set(medio.derivados.filter(formato=AVIF).values_list("pk", "sha256"))
    reales = services._codificar

    def sin_avif(imagen: Image.Image, formato: str, calidad: int | None = None) -> bytes:
        if formato == AVIF:
            raise OSError("sin libavif")
        return reales(imagen, formato, calidad)

    monkeypatch.setattr(services, "_codificar", sin_avif)
    resultado = services.regenerar_derivados(medio.pk)

    assert resultado.eliminados == 0
    assert set(medio.derivados.filter(formato=AVIF).values_list("pk", "sha256")) == avif_antes


@pytest.mark.django_db
def test_AC_TKT048_04_regenerar_sin_original_se_omite(media_temporal: Path, actor: int) -> None:
    medio = _subir(actor)
    (media_temporal / services.RAIZ_PRIVADA / medio.archivo_saneado_ruta).unlink()
    assert services.regenerar_derivados(medio.pk).omitido is True


@pytest.mark.django_db
def test_AC_TKT048_04_regenerar_medio_inexistente_es_no_encontrado() -> None:
    with pytest.raises(services.NoEncontrado):
        services.regenerar_derivados(999_999_999)


@pytest.mark.django_db
def test_AC_TKT048_05_comando_regenerar_derivados_idempotente(
    media_temporal: Path, actor: int
) -> None:
    medio = _subir(actor)
    _degradar_como_antes(medio, services.RAIZ_PRIVADA)
    salida = io.StringIO()
    call_command("regenerar_derivados", "--medio", str(medio.pk), stdout=salida)
    assert "actualizados: 0" not in salida.getvalue()

    salida = io.StringIO()
    call_command("regenerar_derivados", stdout=salida)
    texto = salida.getvalue()
    assert "creados: 0, actualizados: 0" in texto
    assert "eliminados por peso: 0" in texto


@pytest.mark.django_db
def test_AC_TKT048_05_comando_medio_inexistente_falla() -> None:
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("regenerar_derivados", "--medio", "999999999", stdout=io.StringIO())
