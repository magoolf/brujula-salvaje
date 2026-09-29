"""AC-TKT006 (QA ciclo 1/3, BUG-2): prueba HTTP real (Django test `Client`, sesión de panel real
vía `cliente_editora`, encoding multipart real -- no `content_type="application/json"`) de
`POST /api/v1/panel/medios`.

Motivo de este archivo: `test_ac_tkt006_03_medios.py` (mismo directorio) prueba
`services.subir_medios` llamándolo directamente en Python, nunca a través de la vista HTTP real
-- por eso nunca atrapó que `REST_FRAMEWORK["DEFAULT_PARSER_CLASSES"]` (config/settings/base.py)
solo declara `JSONParser` a nivel global y `ListaMedios` (apps/medios/api/views.py) no tenía
`parser_classes` propio: DRF rechazaba CUALQUIER `multipart/form-data` con 415 antes de ejecutar
`post()`, dejando la subida de imágenes (FEAT-041) 100% inalcanzable pese a que
`services.subir_medios` en sí funcionaba perfectamente. QA lo confirmó contra el servidor real;
este archivo deja la reproducción HTTP en el repo."""

from __future__ import annotations

import io

import pytest
from django.test import Client
from PIL import Image

pytestmark = pytest.mark.django_db

BASE = "/api/v1/panel/medios"


def _jpeg_bytes(ancho: int = 1600, alto: int = 1200) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (ancho, alto), color=(10, 20, 30)).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def test_AC_TKT006_04_subir_medio_via_multipart_real(cliente_editora: Client) -> None:
    """BUG-2: antes de la corrección, esta petición devolvía 415 `Unsupported Media Type` sin
    llegar a ejecutar `ListaMedios.post` -- ni siquiera `request.FILES` se poblaba. El `Client`
    de Django usa `multipart/form-data` de forma automática al recibir un archivo en el dict de
    datos (no se fuerza `content_type`, a diferencia del resto de las pruebas HTTP del panel, que
    sí son JSON): es la misma forma en la que un navegador/cliente real sube un archivo."""
    archivo = io.BytesIO(_jpeg_bytes())
    archivo.name = "foto.jpg"

    respuesta = cliente_editora.post(BASE, {"archivos": archivo})

    assert respuesta.status_code == 200, respuesta.content
    cuerpo = respuesta.json()
    assert len(cuerpo["resultados"]) == 1
    resultado = cuerpo["resultados"][0]
    assert resultado["resultado"] == "ACEPTADO"
    assert resultado["medio"]["estado"] == "PENDIENTE_METADATOS"
    assert resultado["medio"]["ancho_px"] == 1600
    assert resultado["medio"]["alto_px"] == 1200


def test_AC_TKT006_04_subir_medio_json_se_rechaza_sin_500(cliente_editora: Client) -> None:
    """`POST /panel/medios` es EXCLUSIVAMENTE multipart (contrato: `multipart/form-data`, sin
    variante JSON) -- el fix de BUG-2 fue deliberadamente scoped a
    `parser_classes = [MultiPartParser, FormParser]` en `ListaMedios`, sin `JSONParser` (a
    diferencia del resto del panel, que sigue siendo JSON-only por diseño y NO debe aceptar
    multipart). Un `Content-Type: application/json` contra esta vista debe rechazarse con un 415
    bien formado (`application/problem+json`, DRF `UnsupportedMediaType` vía
    `apps.core.exceptions.manejador_excepciones`) y NO con un 500: confirma que el scoping del
    parser no dejó la vista en un estado ambiguo para el único otro Content-Type real que podría
    llegarle."""
    respuesta = cliente_editora.post(BASE, {"archivos": []}, content_type="application/json")
    assert respuesta.status_code == 415, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"


def test_AC_TKT006_04_listar_medios_sigue_siendo_json(cliente_editora: Client) -> None:
    """`GET` (sin body) de la misma vista no debe verse afectado por el `parser_classes` scoped a
    la subida: sigue devolviendo JSON con normalidad."""
    respuesta = cliente_editora.get(BASE)
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["resultados"] == []
