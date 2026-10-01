"""TKT-012 (deuda de cobertura, Skill_Backend §8: services > 90 %): ramas de `apps.medios.services`
y del panel de medios que ninguna prueba ejercía (hallazgo de QA en TKT-006 y TKT-017).

- Rechazos de subida por contenido real: formato no permitido (incluido el archivo disfrazado:
  un GIF con extensión y Content-Type de JPEG), tamaño excedido, archivo corrupto (cabecera
  válida con datos truncados), megapíxeles excedidos (límite propio y "bomba de descompresión"
  que Pillow rechaza ya en `open`, antes un 500) y duplicado por huella vía HTTP.
- Carrera de subida duplicada: el INSERT choca con la UNIQUE de `huella_sha256` (otra petición
  insertó la misma huella entre la comprobación previa y el INSERT) -> DUPLICADO, no 500.
- NoEncontrado (404) en obtener/catalogar/usos/retirar/reactivar.
- Catalogar con licencia incompatible un medio en uso por contenido publicado -> 422.
- `usos()`: filas PORTADA, GALERIA y HERO, y su conteo de consultas (N+1).
- Autenticación: sin sesión de panel -> 401/403 (los medios son recursos editoriales
  compartidos, sin propietario: no hay acceso horizontal entre editores que probar).
"""

from __future__ import annotations

import io
import struct
import zlib
from collections.abc import Callable
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from PIL import Image

from apps.catalogos.models import Licencia
from apps.contenido.models import ContenidoMedio, TipoContenido
from apps.contenido.tests import publicos
from apps.contenido.tests.fabricas import crear_cuenta, crear_medio
from apps.inicio.models import ID_SINGLETON, ConfigInicio
from apps.medios import services
from apps.medios.models import EstadoMedio, Medio

pytestmark = pytest.mark.django_db

BASE = "/api/v1/panel/medios"
NO_EXISTE = 987_654_321


def _imagen(formato: str, ancho: int = 1600, alto: int = 1200, modo: str = "RGB") -> bytes:
    buffer = io.BytesIO()
    Image.new(modo, (ancho, alto)).save(buffer, format=formato)
    return buffer.getvalue()


def _png_con_cabecera(ancho: int, alto: int) -> bytes:
    """PNG cuya cabecera (IHDR) declara `ancho`x`alto` sin los datos de esos píxeles: Pillow lee
    el tamaño de la cabecera en `open` (perezoso), igual que haría con un archivo malicioso."""

    def bloque(tipo: bytes, datos: bytes) -> bytes:
        crc = zlib.crc32(tipo + datos) & 0xFFFFFFFF
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00" * 16)
    return (
        b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", ihdr) + bloque(b"IDAT", idat) + bloque(b"IEND", b"")
    )


@pytest.fixture
def actor() -> int:
    return crear_cuenta("editora.tkt012.medios").pk


def _subir(actor: int, nombre: str, contenido: bytes, tipo: str = "image/jpeg") -> Any:
    return services.subir_medios(actor, [SimpleUploadedFile(nombre, contenido, tipo)])[0]


def _codigo_rechazo(resultado: Any) -> str:
    assert resultado.resultado == "RECHAZADO", resultado
    assert resultado.motivo is not None
    return str(resultado.motivo["code"])


# ---------------------------------------------------------------------------
# Rechazos de subida (servicio)
# ---------------------------------------------------------------------------
def test_TKT012_archivo_disfrazado_gif_como_jpeg_es_formato_no_permitido(actor: int) -> None:
    """THREAT-006: el tipo se decide por el contenido, nunca por el nombre ni el Content-Type."""
    gif = _imagen("GIF", modo="P")
    assert _codigo_rechazo(_subir(actor, "foto.jpg", gif, "image/jpeg")) == "formato_no_permitido"
    assert not Medio.objects.exists()


def test_TKT012_bmp_es_formato_no_permitido(actor: int) -> None:
    assert _codigo_rechazo(_subir(actor, "a.bmp", _imagen("BMP"))) == "formato_no_permitido"


def test_TKT012_archivo_vacio_es_tamano_excedido(actor: int) -> None:
    assert _codigo_rechazo(_subir(actor, "vacio.jpg", b"")) == "tamano_excedido"


def test_TKT012_cabecera_valida_con_datos_truncados_es_archivo_corrupto(actor: int) -> None:
    """La cabecera pasa `open` (perezoso) pero `load()` falla al decodificar."""
    truncado = _imagen("JPEG")[:2_000]
    assert _codigo_rechazo(_subir(actor, "truncada.jpg", truncado)) == "archivo_corrupto"


def test_TKT012_dimensiones_cero_en_cabecera_es_archivo_corrupto(actor: int) -> None:
    assert _codigo_rechazo(_subir(actor, "cero.png", _png_con_cabecera(0, 0))) in {
        "archivo_corrupto"
    }


def test_TKT012_megapixeles_excedidos_por_limite_propio(actor: int) -> None:
    """7000 x 6000 = 42 MP > 40 MP (`PIXELES_MAXIMOS`), sin llegar al umbral de Pillow."""
    resultado = _subir(actor, "grande.png", _png_con_cabecera(7000, 6000), "image/png")
    assert _codigo_rechazo(resultado) == "megapixeles_excedidos"


def test_TKT012_bomba_de_descompresion_es_megapixeles_excedidos_no_500(actor: int) -> None:
    """30000 x 30000 = 900 MP: Pillow lanza `DecompressionBombError` (no OSError) ya en `open`.
    Antes escapaba sin capturar (500); ahora es el mismo rechazo de negocio."""
    resultado = _subir(actor, "bomba.png", _png_con_cabecera(30_000, 30_000), "image/png")
    assert _codigo_rechazo(resultado) == "megapixeles_excedidos"


def test_TKT012_carrera_de_subida_duplicada_responde_duplicado(
    actor: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Otra petición insertó la misma huella entre la comprobación previa y el INSERT: el
    IntegrityError REAL de la UNIQUE solo deshace el savepoint del INSERT y la respuesta es
    DUPLICADO con el id existente (antes la transacción quedaba rota -> 500)."""
    contenido = _imagen("JPEG")
    primero = _subir(actor, "a.jpg", contenido)
    assert primero.resultado == "ACEPTADO"

    llamadas: list[str] = []
    original = services._medio_por_huella

    def comprobacion_previa_sin_ver_al_otro(huella: str) -> Medio | None:
        llamadas.append(huella)
        return None if len(llamadas) == 1 else original(huella)

    monkeypatch.setattr(services, "_medio_por_huella", comprobacion_previa_sin_ver_al_otro)
    segundo = _subir(actor, "b.jpg", contenido)

    assert segundo.resultado == "DUPLICADO"
    assert segundo.medio_existente_id == primero.medio.pk
    assert len(llamadas) == 2
    assert Medio.objects.count() == 1


# ---------------------------------------------------------------------------
# Catalogación con licencia incompatible en uso publicado
# ---------------------------------------------------------------------------
def test_TKT012_licencia_incompatible_en_medio_publicado_se_rechaza(actor: int) -> None:
    destino = publicos.destino("Destino con portada catalogada", tipos=[])
    medio_id = destino.contenido.portada_id
    incompatible = Licencia.objects.create(
        codigo="TKT012-INCOMP",
        nombre="Licencia incompatible de prueba",
        requiere_atribucion=False,
        compatible_publicacion=False,
        activo=True,
    )
    with pytest.raises(services.ErrorApi) as error:
        services.catalogar(medio_id, actor, {"licencia_id": incompatible.pk})
    assert error.value.codigo == "regla_negocio"
    assert Medio.objects.get(pk=medio_id).licencia_id != incompatible.pk


def test_TKT012_licencia_incompatible_en_medio_sin_uso_queda_disponible(actor: int) -> None:
    """Sin uso publicado no hay bloqueo: se guarda (el medio ya DISPONIBLE no cambia de estado)."""
    medio = crear_medio(
        estado=EstadoMedio.DISPONIBLE,
        texto_alternativo="Alt",
        autor_credito="Autor",
        licencia=Licencia.objects.filter(compatible_publicacion=True).first(),
    )
    incompatible = Licencia.objects.create(
        codigo="TKT012-INCOMP2",
        nombre="Otra licencia incompatible",
        requiere_atribucion=False,
        compatible_publicacion=False,
        activo=True,
    )
    guardado = services.catalogar(medio.pk, actor, {"licencia_id": incompatible.pk})
    assert guardado.licencia_id == incompatible.pk
    assert guardado.estado == EstadoMedio.DISPONIBLE


# ---------------------------------------------------------------------------
# usos(): PORTADA + GALERIA + HERO, sin N+1
# ---------------------------------------------------------------------------
def test_TKT012_usos_incluye_portada_galeria_y_hero_sin_n_mas_1() -> None:
    destino = publicos.destino("Destino de usos completos", tipos=[])
    medio_id = destino.contenido.portada_id
    otros = [publicos.destino(f"Galería {i}", tipos=[]) for i in range(3)]
    for orden, otro in enumerate(otros):
        ContenidoMedio.objects.create(
            contenido=otro.contenido,
            tipo_contenido=TipoContenido.DESTINO,
            medio_id=medio_id,
            orden=orden,
        )
    ConfigInicio.objects.update_or_create(
        pk=ID_SINGLETON,
        defaults={"hero_titular": "Hero", "hero_subtitulo": "Sub", "hero_medio_id": medio_id},
    )

    with CaptureQueriesContext(connection) as consultas:
        filas = services.usos(medio_id)
    # 1 portada + 1 galería (select_related) + 1 hero: constante, no crece con las filas.
    assert len(consultas) == 3

    roles = sorted(f["rol"] for f in filas)
    assert roles == ["GALERIA", "GALERIA", "GALERIA", "HERO", "PORTADA"]
    hero = next(f for f in filas if f["rol"] == "HERO")
    assert hero["tipo_contenido"] == "CONFIG_INICIO"
    assert hero["estado_editorial"] is None


# ---------------------------------------------------------------------------
# HTTP: 404, duplicado, usos, autenticación
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("get", f"{BASE}/{NO_EXISTE}", None),
        ("put", f"{BASE}/{NO_EXISTE}", {"texto_alternativo": "Alt"}),
        ("get", f"{BASE}/{NO_EXISTE}/usos", None),
        ("post", f"{BASE}/{NO_EXISTE}/retirar", None),
        ("post", f"{BASE}/{NO_EXISTE}/reactivar", None),
    ],
)
def test_TKT012_http_medio_inexistente_es_404_problem(
    cliente_editora: Client, metodo: str, ruta: str, cuerpo: dict[str, Any] | None
) -> None:
    llamada: Callable[..., Any] = getattr(cliente_editora, metodo)
    respuesta = llamada(ruta, cuerpo, content_type="application/json")
    assert respuesta.status_code == 404, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
    assert respuesta.json()["code"] == "no_encontrado"
    assert respuesta.json()["trace_id"]


def test_TKT012_http_subida_duplicada_y_rechazo_por_archivo(cliente_editora: Client) -> None:
    jpeg = _imagen("JPEG")
    primero = io.BytesIO(jpeg)
    primero.name = "uno.jpg"
    disfrazado = io.BytesIO(_imagen("GIF", modo="P"))
    disfrazado.name = "foto.jpg"
    respuesta = cliente_editora.post(BASE, {"archivos": [primero, disfrazado]})
    assert respuesta.status_code == 200, respuesta.content
    resultados = respuesta.json()["resultados"]
    assert [r["resultado"] for r in resultados] == ["ACEPTADO", "RECHAZADO"]
    assert resultados[1]["motivo"]["code"] == "formato_no_permitido"

    repetido = io.BytesIO(jpeg)
    repetido.name = "otro-nombre.jpg"
    respuesta = cliente_editora.post(BASE, {"archivos": repetido})
    assert respuesta.status_code == 200, respuesta.content
    resultado = respuesta.json()["resultados"][0]
    assert resultado["resultado"] == "DUPLICADO"
    assert resultado["medio_existente_id"] == resultados[0]["medio"]["id"]


def test_TKT012_http_subida_sin_archivos_o_mas_de_diez_es_400(cliente_editora: Client) -> None:
    respuesta = cliente_editora.post(BASE, {})
    assert respuesta.status_code == 400, respuesta.content
    assert "archivos" in respuesta.json()["errors"]

    archivos = []
    for i in range(11):
        archivo = io.BytesIO(b"x")
        archivo.name = f"{i}.jpg"
        archivos.append(archivo)
    respuesta = cliente_editora.post(BASE, {"archivos": archivos})
    assert respuesta.status_code == 400, respuesta.content


def test_TKT012_http_usos_lista_portada(cliente_editora: Client) -> None:
    destino = publicos.destino("Destino usos HTTP", tipos=[])
    respuesta = cliente_editora.get(f"{BASE}/{destino.contenido.portada_id}/usos")
    assert respuesta.status_code == 200, respuesta.content
    filas = respuesta.json()["resultados"]
    assert filas == [
        {
            "tipo_contenido": "DESTINO",
            "contenido_id": destino.contenido_id,
            "titulo": "Destino usos HTTP",
            "estado_editorial": "PUBLICADO",
            "rol": "PORTADA",
        }
    ]


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("get", BASE),
        ("get", f"{BASE}/1"),
        ("get", f"{BASE}/1/usos"),
        ("post", f"{BASE}/1/retirar"),
        ("post", f"{BASE}/1/reactivar"),
    ],
)
def test_TKT012_http_sin_sesion_no_autoriza(metodo: str, ruta: str) -> None:
    respuesta = getattr(Client(raise_request_exception=False), metodo)(ruta)
    assert respuesta.status_code in {401, 403}, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
