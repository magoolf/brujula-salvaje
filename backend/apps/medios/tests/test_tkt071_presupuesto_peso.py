"""TKT-071 (REQ-052): presupuesto de peso por píxel del AVIF de los derivados.

Causa raíz del LCP móvil de /colecciones (2984 ms > 2,5 s tras TKT-021): la imagen LCP, la portada
de la primera colección por título («Deportes de adrenalina y expediciones», la foto del puente de
Kawarau), es una foto 4:3 con mucho detalle fino (follaje, roca) y con calidad fija su AVIF de
800 px pesaba 85-87 KB (0,18 B/px) frente a 50-56 KB de las imágenes LCP del resto de listados.
Con el presupuesto, el AVIF de una foto así se recodifica a menor calidad (con suelo) y las fotos
de detalle normal no cambian.
"""

from __future__ import annotations

import io
import secrets
from pathlib import Path
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from PIL import Image

from apps.contenido.tests.fabricas import crear_cuenta
from apps.medios import services
from apps.medios.models import FormatoDerivado, Medio
from seed import fotografias

AVIF, WEBP, JPEG = FormatoDerivado.AVIF, FormatoDerivado.WEBP, FormatoDerivado.JPEG
# Imagen LCP de /colecciones (primera colección por título, selectors.colecciones_publicas).
CLAVE_LCP_COLECCIONES = "coleccion:deportes-de-adrenalina-y-expediciones"
CLAVES_COLECCIONES = (
    CLAVE_LCP_COLECCIONES,
    "coleccion:grandes-travesias-de-trekking",
    "coleccion:mundos-de-agua-buceo-cenotes-y-fiordos",
    "coleccion:techos-y-volcanes-de-alta-montana",
)
# Foto de detalle normal (por debajo del presupuesto): no debe cambiar.
CLAVE_DETALLE_NORMAL = "destino:kilimanjaro:0"
# PERFORMANCE_SPEC (HANDOFF_UI_UX): imagen de tarjeta ≤ 60 KB. El AVIF de 800 px es el que elige un
# móvil (412 px a DPR 1,75) para la tarjeta de ancho completo de los listados.
MAX_AVIF_TARJETA_800 = 60 * 1024


def _foto(clave: str) -> Image.Image:
    imagen = Image.open(io.BytesIO(fotografias.foto_para(clave).leer()))
    imagen.load()
    return imagen


def _a_800(imagen: Image.Image) -> Image.Image:
    base = imagen.convert("RGB")
    base.info = {}
    alto = round(imagen.height * 800 / imagen.width)
    redimensionada = base.resize((800, alto), Image.Resampling.LANCZOS)
    redimensionada.info = {}
    return redimensionada


def _avif_800(clave: str) -> bytes:
    for derivado in services._codificar_derivados(_foto(clave)).derivados:
        if derivado.formato == AVIF and derivado.ancho == 800:
            return derivado.contenido
    raise AssertionError(f"sin AVIF de 800 px para {clave}")


def test_AC_TKT071_01_parametros_del_presupuesto() -> None:
    base = services.PARAMETROS_CODIFICACION[AVIF]["quality"]
    calidades = services.CALIDADES_PRESUPUESTO[AVIF]
    # Solo baja la calidad, en orden decreciente, y el suelo no es inferior al primer reintento
    # por orden de pesos de TKT-048 (no se pierde más nitidez de la que ya se aceptaba allí).
    assert list(calidades) == sorted(calidades, reverse=True)
    assert all(q < base for q in calidades)
    assert calidades[-1] >= services.CALIDADES_REINTENTO[AVIF][0]
    assert 0 < services.PRESUPUESTO_BYTES_POR_PIXEL[AVIF] < 0.2
    # El WebP (respaldo sin AVIF) y el JPEG (respaldo universal) no llevan presupuesto.
    assert set(services.PRESUPUESTO_BYTES_POR_PIXEL) == {AVIF}


def test_AC_TKT071_02_imagen_lcp_de_colecciones_dentro_del_presupuesto_de_tarjeta() -> None:
    sin_presupuesto = services._codificar(_a_800(_foto(CLAVE_LCP_COLECCIONES)), AVIF)
    con_presupuesto = _avif_800(CLAVE_LCP_COLECCIONES)
    # Antes superaba el presupuesto de tarjeta; ahora cabe y es claramente más ligera.
    assert len(sin_presupuesto) > MAX_AVIF_TARJETA_800
    assert len(con_presupuesto) <= MAX_AVIF_TARJETA_800
    assert len(con_presupuesto) <= 0.75 * len(sin_presupuesto)
    with Image.open(io.BytesIO(con_presupuesto)) as leida:
        assert leida.format == "AVIF"
        assert leida.size == (800, 600)


@pytest.mark.parametrize("clave", CLAVES_COLECCIONES)
def test_AC_TKT071_02_portadas_de_coleccion_caben_en_el_presupuesto_de_tarjeta(clave: str) -> None:
    assert len(_avif_800(clave)) <= MAX_AVIF_TARJETA_800


def test_AC_TKT071_03_foto_de_detalle_normal_no_cambia() -> None:
    redimensionada = _a_800(_foto(CLAVE_DETALLE_NORMAL))
    calidad_base = services._codificar(redimensionada, AVIF)
    assert len(calidad_base) <= (
        services.PRESUPUESTO_BYTES_POR_PIXEL[AVIF] * redimensionada.width * redimensionada.height
    )
    assert _avif_800(CLAVE_DETALLE_NORMAL) == calidad_base


def _registrar_calidades(
    monkeypatch: pytest.MonkeyPatch, inflar_avif: bool = False
) -> list[tuple[str, int | None]]:
    reales = services._codificar
    llamadas: list[tuple[str, int | None]] = []

    def codificar(imagen: Image.Image, formato: str, calidad: int | None = None) -> bytes:
        llamadas.append((str(formato), calidad))
        contenido = reales(imagen, formato, calidad)
        return contenido * 50 if inflar_avif and formato == AVIF else contenido

    monkeypatch.setattr(services, "_codificar", codificar)
    return llamadas


def test_AC_TKT071_04_por_encima_del_presupuesto_baja_hasta_caber(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llamadas = _registrar_calidades(monkeypatch)
    formatos = services._codificar_ancho(_a_800(_foto(CLAVE_LCP_COLECCIONES)), set())
    avif = [calidad for formato, calidad in llamadas if formato == str(AVIF)]
    # Primer intento a la calidad base y después las del presupuesto hasta caber.
    assert avif[0] is None
    assert avif[1:] == list(services.CALIDADES_PRESUPUESTO[AVIF][: len(avif) - 1])
    assert set(formatos) == {AVIF, WEBP, JPEG}
    assert len(formatos[AVIF]) <= len(formatos[WEBP]) <= len(formatos[JPEG])
    # WebP y JPEG se codifican una sola vez a su calidad base.
    assert [c for f, c in llamadas if f != str(AVIF)] == [None, None]


def test_AC_TKT071_04_el_suelo_se_conserva_aunque_no_quepa(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si ni con el suelo cabe en el presupuesto, se sirve el del suelo (no se baja más por
    presupuesto); el reintento por orden de pesos de TKT-048 solo prueba calidades inferiores al
    suelo y, si tampoco cabe bajo el WebP, se descarta como antes."""
    llamadas = _registrar_calidades(monkeypatch, inflar_avif=True)
    formatos = services._codificar_ancho(_a_800(_foto(CLAVE_DETALLE_NORMAL)), set())
    avif = [calidad for formato, calidad in llamadas if formato == str(AVIF)]
    suelo = services.CALIDADES_PRESUPUESTO[AVIF][-1]
    reintentos = [q for q in services.CALIDADES_REINTENTO[AVIF] if q < suelo]
    assert avif == [None, *services.CALIDADES_PRESUPUESTO[AVIF], *reintentos]
    assert set(formatos) == {WEBP, JPEG}


def test_AC_TKT071_04_ruido_respeta_orden_de_pesos_con_presupuesto() -> None:
    ruido = Image.frombytes("RGB", (800, 600), secrets.token_bytes(800 * 600 * 3))
    formatos = services._codificar_ancho(ruido, set())
    assert JPEG in formatos
    presentes = [f for f in (AVIF, WEBP, JPEG) if f in formatos]
    pesos = [len(formatos[f]) for f in presentes]
    assert pesos == sorted(pesos)


# ---------------------------------------------------------------------------
# Regeneración (mecanismo de TKT-048): los derivados ya publicados se versionan
# ---------------------------------------------------------------------------
@pytest.fixture
def media_temporal(settings: Any, tmp_path: Path) -> Path:
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.mark.django_db
def test_AC_TKT071_05_regenerar_aplica_el_presupuesto_con_ruta_versionada(
    media_temporal: Path, monkeypatch: pytest.MonkeyPatch, django_capture_on_commit_callbacks: Any
) -> None:
    actor = crear_cuenta("editora.tkt071").pk
    # Medio subido antes de TKT-071 (sin presupuesto).
    with monkeypatch.context() as m:
        m.setattr(services, "PRESUPUESTO_BYTES_POR_PIXEL", {})
        archivo = SimpleUploadedFile(
            "foto.jpg",
            fotografias.foto_para(CLAVE_LCP_COLECCIONES).leer(),
            content_type="image/jpeg",
        )
        medio = services.subir_medios(actor, [archivo])[0].medio
    assert isinstance(medio, Medio)
    antes = {(d.formato, d.ancho_px): (d.ruta, d.peso_bytes) for d in medio.derivados.all()}
    assert antes[(AVIF, 800)][1] > MAX_AVIF_TARJETA_800

    with django_capture_on_commit_callbacks(execute=True):
        resultado = services.regenerar_derivados(medio.pk)

    assert resultado.creados == resultado.eliminados == 0
    assert resultado.actualizados > 0
    avif_800 = medio.derivados.get(formato=AVIF, ancho_px=800)
    assert avif_800.peso_bytes <= MAX_AVIF_TARJETA_800
    # Contenido nuevo -> URL nueva (las de /media/publico son `immutable`) y el archivo antiguo se
    # borra al confirmar.
    assert avif_800.ruta != antes[(AVIF, 800)][0]
    assert avif_800.ruta.endswith(f"-800-{avif_800.sha256[:12]}.avif")
    assert not (media_temporal / services.RAIZ_PRIVADA / antes[(AVIF, 800)][0]).exists()
    assert (media_temporal / services.RAIZ_PRIVADA / avif_800.ruta).is_file()
    # Ningún AVIF pesa más que antes (WebP/JPEG pueden variar unos bytes: la regeneración parte del
    # original saneado y la subida del archivo subido, como ya documenta TKT-048).
    for derivado in medio.derivados.filter(formato=AVIF):
        assert derivado.peso_bytes <= antes[(AVIF, derivado.ancho_px)][1]

    salida = io.StringIO()
    call_command("regenerar_derivados", "--medio", str(medio.pk), stdout=salida)
    assert "creados: 0, actualizados: 0" in salida.getvalue()


# ---------------------------------------------------------------------------
# DEC-AUTO-1314: la codificación (segundos de CPU, más con el presupuesto) se hace FUERA de la
# transacción. Dentro, la conexión quedaba ociosa y el rol app_rw tiene
# `idle_in_transaction_session_timeout = 30s` (INFRA-DB-000): PostgreSQL cortaba la conexión a mitad
# de la subida de una foto grande con mucho detalle (reproducido con `cargar_semilla`).
# Con `transaction=True` no hay transacción envolvente de la prueba: `in_atomic_block` es la real.
# ---------------------------------------------------------------------------
def _vigilar_codificacion(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    reales = services._codificar_derivados
    dentro: list[bool] = []

    def codificar(imagen: Image.Image) -> services.Codificacion:
        dentro.append(connection.in_atomic_block)
        return reales(imagen)

    monkeypatch.setattr(services, "_codificar_derivados", codificar)
    return dentro


@pytest.mark.django_db(transaction=True)
def test_AC_TKT071_06_subida_y_regeneracion_codifican_fuera_de_la_transaccion(
    media_temporal: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    actor = crear_cuenta("editora.tkt071.tx").pk
    dentro = _vigilar_codificacion(monkeypatch)
    archivo = SimpleUploadedFile(
        "foto.jpg", fotografias.foto_para(CLAVE_DETALLE_NORMAL).leer(), content_type="image/jpeg"
    )
    medio = services.subir_medios(actor, [archivo])[0].medio
    assert isinstance(medio, Medio)
    assert medio.derivados.filter(formato=AVIF, ancho_px=800).exists()

    resultado = services.regenerar_derivados(medio.pk)

    assert dentro == [False, False]
    # (La regeneración parte del original saneado y la subida del archivo subido: los bytes pueden
    # variar, ya documentado en TKT-048; aquí solo importa dónde se codifica.)
    assert resultado.omitido is False
    assert medio.derivados.filter(formato=AVIF, ancho_px=800).exists()
