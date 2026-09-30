"""TKT-017: regresión de la causa raíz de los 404 en `/media/publico/**` con la semilla real.

Causa raíz (confirmada contra el stack Docker real antes de corregir, ver HANDOFF del ticket):
`apps.medios.services` escribía TODOS los archivos bajo `MEDIA_ROOT/medios/**`, una ruta que
nginx (`infra/proxy/nginx.conf`) nunca expone -- solo sirve `MEDIA_ROOT/publico/**` (documentado
en `docs/05_operacion/DEVOPS_HANDOFF.md` §6 y DEC-AUTO-147, nunca implementado por TKT-006). La
URL pública que construye `apps.contenido.api.serializers` (`MEDIA_PUBLIC_URL + derivado.ruta`,
fuera de `archivos_permitidos` de este ticket) era correcta; el archivo físico, no.

Las pruebas existentes (`apps/contenido/tests/publicos.py`) nunca detectaron esto porque crean el
`Medio`/`MedioDerivado` directamente por ORM, sin pasar por `services.py` ni tocar el sistema de
archivos -- por eso ya asumían la convención correcta (`ruta="derivados/..."`, sin prefijo
`medios/`) sin que nada la verificara contra un archivo real. Estas pruebas sí ejercitan
`services.py` de punta a punta (subida real -> Pillow -> disco) y comprueban el archivo físico."""

from __future__ import annotations

import io
import os
import secrets
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from apps.catalogos.models import Licencia
from apps.contenido.tests.fabricas import crear_cuenta
from apps.medios import services
from apps.medios.models import EstadoMedio, Medio

pytestmark = pytest.mark.django_db

BASE = "/api/v1/panel/medios"


def _jpeg() -> bytes:
    """Color aleatorio por llamada (no un color fijo como `test_ac_tkt006_03_medios.py`): el
    nombre del archivo derivado es `huella_sha256(contenido)-ancho.ext`, así que dos pruebas con
    la MISMA imagen (incluso en archivos distintos) comparten huella y, si una ya la cataloga a
    DISPONIBLE en una ejecución anterior de la suite, el archivo puede quedar movido a `publico/`
    de forma persistente en disco (MEDIA_ROOT no se limpia entre ejecuciones de pytest, a
    diferencia de la BD, que sí se revierte por prueba) y contaminar una aserción "no debe
    existir en publico/" de una ejecución posterior. Un color aleatorio por invocación hace cada
    huella prácticamente única entre ejecuciones."""
    color = tuple(secrets.randbelow(256) for _ in range(3))
    buffer = io.BytesIO()
    Image.new("RGB", (1600, 1200), color=color).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


@pytest.fixture
def actor() -> int:
    return crear_cuenta("editora.tkt017").pk


@pytest.fixture
def licencia_propia() -> Licencia:
    licencia = Licencia.objects.filter(compatible_publicacion=True, activo=True).first()
    assert licencia is not None
    return licencia


def _existe_en(medio: Medio, area: str, ancho: int = 800, formato: str = "WEBP") -> bool:
    derivado = medio.derivados.get(ancho_px=ancho, formato=formato)
    return (Path(settings.MEDIA_ROOT) / area / derivado.ruta).is_file()


def test_TKT017_derivado_recien_subido_vive_en_privado_no_en_publico(actor: int) -> None:
    """Un medio recién subido está PENDIENTE_METADATOS (nunca nace DISPONIBLE, DEC-AUTO-110): sus
    derivados deben quedar en `privado/`, nunca en `publico/` (que es lo único que nginx sirve)."""
    archivo = SimpleUploadedFile("a.jpg", _jpeg(), content_type="image/jpeg")
    medio = services.subir_medios(actor, [archivo])[0].medio
    assert medio is not None
    assert medio.derivados.exists()

    assert _existe_en(medio, services.RAIZ_PRIVADA) is True
    assert _existe_en(medio, services.RAIZ_PUBLICA) is False

    # El original saneado tampoco se sirve nunca (THREAT-023): siempre en privado/.
    ruta_original = Path(settings.MEDIA_ROOT) / services.RAIZ_PRIVADA / medio.archivo_saneado_ruta
    assert ruta_original.is_file()


def test_TKT017_catalogar_a_disponible_mueve_los_derivados_a_publico(
    actor: int, licencia_propia: Licencia
) -> None:
    """Causa raíz exacta del 404 con la semilla real: `cargar_semilla` sube y cataloga cada
    imagen en la misma operación (TKT-007), dejando el medio DISPONIBLE de inmediato. Antes de
    esta corrección, el archivo nunca se movía a `publico/`: la URL pública devuelta por la API
    apuntaba a una ruta vacía. `MEDIA_PUBLIC_URL + derivado.ruta` (misma fórmula que
    `apps.contenido.api.serializers.DerivadoImagenSerializer`, fuera de archivos_permitidos) debe
    resolver a un archivo real tras catalogar."""
    archivo = SimpleUploadedFile("b.jpg", _jpeg(), content_type="image/jpeg")
    medio = services.subir_medios(actor, [archivo])[0].medio
    assert medio is not None

    catalogado = services.catalogar(
        medio.pk,
        actor,
        {
            "texto_alternativo": "Vista de prueba",
            "autor_credito": "Autor de prueba",
            "licencia_id": licencia_propia.pk,
        },
    )
    assert catalogado.estado == EstadoMedio.DISPONIBLE

    assert _existe_en(catalogado, services.RAIZ_PUBLICA) is True
    assert _existe_en(catalogado, services.RAIZ_PRIVADA) is False

    # Reproduce exactamente la fórmula de la URL pública real y comprueba el archivo físico.
    for derivado in catalogado.derivados.all():
        url_publica = f"{str(settings.MEDIA_PUBLIC_URL).rstrip('/')}/{derivado.ruta.lstrip('/')}"
        assert url_publica.startswith("/media/publico/")
        assert not url_publica.startswith("/media/publico/medios/"), (
            "regresión: la ruta guardada vuelve a incluir el prefijo 'medios/' que producía "
            "el 404 original"
        )
        ruta_fisica = Path(settings.MEDIA_ROOT) / services.RAIZ_PUBLICA / derivado.ruta
        assert ruta_fisica.is_file(), f"404 real: {url_publica} no tiene archivo físico"

    # Catalogar de nuevo (idempotencia: cargar_semilla puede reejecutarse) no debe fallar ni
    # volver a mover nada (ya está en publico/).
    services.catalogar(catalogado.pk, actor, {"texto_alternativo": "Vista de prueba (editada)"})
    assert _existe_en(catalogado, services.RAIZ_PUBLICA) is True


def test_TKT017_retirar_mueve_los_derivados_de_vuelta_a_privado(
    actor: int, licencia_propia: Licencia
) -> None:
    """DEC-AUTO-147: al retirar un medio DISPONIBLE, sus derivados dejan de ser públicos y deben
    volver a `privado/` (ya no accesibles por nginx, solo por el panel con sesión)."""
    archivo = SimpleUploadedFile("c.jpg", _jpeg(), content_type="image/jpeg")
    medio = services.subir_medios(actor, [archivo])[0].medio
    assert medio is not None
    services.catalogar(
        medio.pk,
        actor,
        {
            "texto_alternativo": "Vista",
            "autor_credito": "Autor",
            "licencia_id": licencia_propia.pk,
        },
    )
    assert _existe_en(medio, services.RAIZ_PUBLICA) is True

    retirado = services.retirar(medio.pk, actor)
    assert retirado.estado == EstadoMedio.RETIRADO
    assert _existe_en(retirado, services.RAIZ_PRIVADA) is True
    assert _existe_en(retirado, services.RAIZ_PUBLICA) is False

    # reactivar() no mueve nada: RETIRADO -> PENDIENTE_METADATOS son ambos "no público".
    reactivado = services.reactivar(retirado.pk, actor)
    assert reactivado.estado == EstadoMedio.PENDIENTE_METADATOS
    assert _existe_en(reactivado, services.RAIZ_PRIVADA) is True
    assert _existe_en(reactivado, services.RAIZ_PUBLICA) is False


def test_TKT017_panel_archivo_sirve_bytes_reales_disponible_y_pendiente(
    cliente_editora: Client, licencia_propia: Licencia
) -> None:
    """`GET /panel/medios/{id}/archivo` debe seguir sirviendo el derivado sea cual sea su estado
    (DEC-AUTO-110: los no DISPONIBLES solo se ven por aquí, con sesión) -- prueba HTTP real, no
    solo la función de servicio, porque el bug original era justo de resolución de ruta física."""
    archivo = io.BytesIO(_jpeg())
    archivo.name = "g.jpg"
    respuesta = cliente_editora.post(BASE, {"archivos": archivo})
    assert respuesta.status_code == 200, respuesta.content
    medio_id = respuesta.json()["resultados"][0]["medio"]["id"]
    medio = Medio.objects.get(pk=medio_id)
    derivado = medio.derivados.filter(ancho_px=800, formato="WEBP").first()
    assert derivado is not None

    # PENDIENTE_METADATOS: el archivo vive en privado/, el panel debe poder leerlo igual.
    resp_pendiente = cliente_editora.get(f"{BASE}/{medio_id}/archivo?ancho=800&formato=WEBP")
    assert resp_pendiente.status_code == 200, resp_pendiente.content
    assert resp_pendiente["Content-Type"] == "image/webp"
    assert len(resp_pendiente.content) == derivado.peso_bytes

    # Catalogar -> DISPONIBLE -> el archivo se mueve a publico/; el panel sigue sirviéndolo.
    services.catalogar(
        medio_id,
        crear_cuenta("editora.tkt017.b").pk,
        {
            "texto_alternativo": "Vista",
            "autor_credito": "Autor",
            "licencia_id": licencia_propia.pk,
        },
    )
    resp_disponible = cliente_editora.get(f"{BASE}/{medio_id}/archivo?ancho=800&formato=WEBP")
    assert resp_disponible.status_code == 200, resp_disponible.content
    assert resp_disponible.content == resp_pendiente.content


@pytest.mark.skipif(os.name == "nt", reason="permisos POSIX no aplican en Windows")
def test_TKT017_permisos_de_archivo_publico_y_privado(
    actor: int, licencia_propia: Licencia
) -> None:
    """DEVOPS_HANDOFF §6: FILE_UPLOAD_PERMISSIONS 0o640 en privado y 0o644 en publico."""
    archivo = SimpleUploadedFile("d.jpg", _jpeg(), content_type="image/jpeg")
    medio = services.subir_medios(actor, [archivo])[0].medio
    assert medio is not None
    ruta_original = Path(settings.MEDIA_ROOT) / services.RAIZ_PRIVADA / medio.archivo_saneado_ruta
    assert (ruta_original.stat().st_mode & 0o777) == 0o640

    catalogado = services.catalogar(
        medio.pk,
        actor,
        {
            "texto_alternativo": "Vista",
            "autor_credito": "Autor",
            "licencia_id": licencia_propia.pk,
        },
    )
    derivado = catalogado.derivados.filter(ancho_px=800, formato="WEBP").first()
    assert derivado is not None
    ruta_publica = Path(settings.MEDIA_ROOT) / services.RAIZ_PUBLICA / derivado.ruta
    assert (ruta_publica.stat().st_mode & 0o777) == 0o644


def test_TKT017_mover_derivados_es_idempotente_si_el_destino_ya_existe(
    actor: int, licencia_propia: Licencia
) -> None:
    """Si el archivo de destino ya existe (p. ej. una segunda ejecución de `cargar_semilla` tras
    una interrupción a medias), `_mover_derivados` no debe fallar ni sobrescribir: se salta."""
    archivo = SimpleUploadedFile("e.jpg", _jpeg(), content_type="image/jpeg")
    medio = services.subir_medios(actor, [archivo])[0].medio
    assert medio is not None
    derivado = medio.derivados.filter(ancho_px=800, formato="WEBP").first()
    assert derivado is not None

    # Simula que el destino ya existe (movimiento previo interrumpido antes de confirmar en BD).
    destino = services._ruta_absoluta(services.RAIZ_PUBLICA, derivado.ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(b"contenido-preexistente")

    catalogado = services.catalogar(
        medio.pk,
        actor,
        {
            "texto_alternativo": "Vista",
            "autor_credito": "Autor",
            "licencia_id": licencia_propia.pk,
        },
    )
    assert catalogado.estado == EstadoMedio.DISPONIBLE
    # No lo sobrescribe (se salta por ser idempotente) y el origen en privado/ sigue intacto.
    assert destino.read_bytes() == b"contenido-preexistente"
    origen = services._ruta_absoluta(services.RAIZ_PRIVADA, derivado.ruta)
    assert origen.is_file()


def test_TKT017_mover_derivados_registra_advertencia_si_falta_el_archivo_de_origen(
    actor: int, licencia_propia: Licencia
) -> None:
    """Un archivo perdido (volumen dañado, borrado manual) no debe bloquear la transición de
    estado ya confirmada en BD -- se registra y se sigue (es un problema de infraestructura, no
    una razón de negocio para rechazar la catalogación)."""
    archivo = SimpleUploadedFile("f.jpg", _jpeg(), content_type="image/jpeg")
    medio = services.subir_medios(actor, [archivo])[0].medio
    assert medio is not None
    for derivado in medio.derivados.all():
        origen = services._ruta_absoluta(services.RAIZ_PRIVADA, derivado.ruta)
        origen.unlink()

    import structlog.testing

    with structlog.testing.capture_logs() as eventos:
        catalogado = services.catalogar(
            medio.pk,
            actor,
            {
                "texto_alternativo": "Vista",
                "autor_credito": "Autor",
                "licencia_id": licencia_propia.pk,
            },
        )
    assert catalogado.estado == EstadoMedio.DISPONIBLE
    assert any(e.get("event") == "derivado_no_encontrado_al_mover" for e in eventos)
