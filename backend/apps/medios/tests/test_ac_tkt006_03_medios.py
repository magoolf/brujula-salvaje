"""AC-TKT006: subida, catalogación y ciclo de vida de medios (STATE-002, RULE-005, DEC-AUTO-044).

Genera imágenes JPEG válidas/ inválidas en memoria con Pillow para probar la validación de
formato, tamaño y dimensiones sin depender de archivos de prueba externos.
"""

from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.catalogos.models import Licencia
from apps.contenido.tests.fabricas import crear_cuenta
from apps.medios import services
from apps.medios.models import EstadoMedio

pytestmark = pytest.mark.django_db


def _jpeg(ancho: int = 1600, alto: int = 1200, color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (ancho, alto), color=color).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


@pytest.fixture
def actor() -> int:
    return crear_cuenta("editora.medios").pk


def test_AC_TKT006_03_subir_medio_valido_queda_pendiente_de_metadatos(actor: int) -> None:
    archivo = SimpleUploadedFile("foto.jpg", _jpeg(), content_type="image/jpeg")
    resultados = services.subir_medios(actor, [archivo])
    assert len(resultados) == 1
    resultado = resultados[0]
    assert resultado.resultado == "ACEPTADO"
    assert resultado.medio is not None
    assert resultado.medio.estado == EstadoMedio.PENDIENTE_METADATOS
    assert resultado.medio.ancho_px == 1600
    assert resultado.medio.alto_px == 1200
    assert len(resultado.medio.huella_sha256) == 64


def test_AC_TKT006_03_subir_medio_duplicado_por_huella(actor: int) -> None:
    contenido = _jpeg()
    services.subir_medios(
        actor, [SimpleUploadedFile("a.jpg", contenido, content_type="image/jpeg")]
    )
    resultados = services.subir_medios(
        actor, [SimpleUploadedFile("b.jpg", contenido, content_type="image/jpeg")]
    )
    assert resultados[0].resultado == "DUPLICADO"
    assert resultados[0].medio_existente_id is not None


def test_AC_TKT006_03_subir_medio_dimensiones_insuficientes(actor: int) -> None:
    archivo = SimpleUploadedFile("pequena.jpg", _jpeg(800, 600), content_type="image/jpeg")
    resultados = services.subir_medios(actor, [archivo])
    assert resultados[0].resultado == "RECHAZADO"
    assert resultados[0].motivo is not None
    assert resultados[0].motivo["code"] == "dimensiones_insuficientes"


def test_AC_TKT006_03_subir_medio_no_imagen_es_archivo_corrupto(actor: int) -> None:
    archivo = SimpleUploadedFile(
        "no-es-imagen.jpg", b"esto no es una imagen", content_type="image/jpeg"
    )
    resultados = services.subir_medios(actor, [archivo])
    assert resultados[0].resultado == "RECHAZADO"
    assert resultados[0].motivo["code"] == "archivo_corrupto"


def test_AC_TKT006_03_subir_medio_demasiado_pesado_se_rechaza(actor: int) -> None:
    grande = b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024 + 1)
    archivo = SimpleUploadedFile("grande.jpg", grande, content_type="image/jpeg")
    resultados = services.subir_medios(actor, [archivo])
    assert resultados[0].resultado == "RECHAZADO"
    assert resultados[0].motivo["code"] == "tamano_excedido"


def test_AC_TKT006_03_catalogar_medio_lo_deja_disponible(actor: int) -> None:
    archivo = SimpleUploadedFile("foto.jpg", _jpeg(), content_type="image/jpeg")
    resultado = services.subir_medios(actor, [archivo])[0]
    licencia = Licencia.objects.filter(compatible_publicacion=True, activo=True).first()
    assert licencia is not None

    catalogado = services.catalogar(
        resultado.medio.pk,
        actor,
        {
            "texto_alternativo": "Vista del paisaje",
            "autor_credito": "Fotógrafo de prueba",
            "licencia_id": licencia.pk,
        },
    )
    assert catalogado.estado == EstadoMedio.DISPONIBLE
    assert services._pendientes_catalogacion(catalogado, licencia_compatible=True) == []


def test_AC_TKT006_03_catalogar_sin_licencia_queda_pendiente(actor: int) -> None:
    archivo = SimpleUploadedFile("foto.jpg", _jpeg(), content_type="image/jpeg")
    resultado = services.subir_medios(actor, [archivo])[0]
    catalogado = services.catalogar(
        resultado.medio.pk, actor, {"texto_alternativo": "Alt", "autor_credito": "Autor"}
    )
    assert catalogado.estado == EstadoMedio.PENDIENTE_METADATOS


def test_AC_TKT006_03_retirar_medio_no_usado_y_reactivar(actor: int) -> None:
    archivo = SimpleUploadedFile("foto.jpg", _jpeg(), content_type="image/jpeg")
    medio = services.subir_medios(actor, [archivo])[0].medio

    retirado = services.retirar(medio.pk, actor)
    assert retirado.estado == EstadoMedio.RETIRADO

    reactivado = services.reactivar(medio.pk, actor)
    assert reactivado.estado == EstadoMedio.PENDIENTE_METADATOS


def test_AC_TKT006_03_retirar_medio_en_uso_publicado_falla(actor: int) -> None:
    from apps.contenido.tests import publicos

    destino_ = publicos.destino("Destino con medio", tipos=[])
    portada_id = destino_.contenido.portada_id

    with pytest.raises(services.MedioEnUso):
        services.retirar(portada_id, actor)


def test_AC_TKT006_03_reactivar_medio_no_retirado_falla(actor: int) -> None:
    archivo = SimpleUploadedFile("foto.jpg", _jpeg(), content_type="image/jpeg")
    medio = services.subir_medios(actor, [archivo])[0].medio
    with pytest.raises(services.TransicionInvalida):
        services.reactivar(medio.pk, actor)


def test_AC_TKT006_03_usos_de_medio(actor: int) -> None:
    from apps.contenido.tests import publicos

    destino_ = publicos.destino("Destino con usos", tipos=[])
    usos = services.usos(destino_.contenido.portada_id)
    assert any(u["rol"] == "PORTADA" for u in usos)
