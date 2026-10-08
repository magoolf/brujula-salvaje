"""TKT-033 AC_TKT033_03 (F-032-03): el 409 `medio_en_uso` de POST /panel/medios/{id}/retirar
lista los usos con la forma `ReferenciaUso` del contrato ({tipo_entidad, id, titulo,
estado_editorial}), no con la de `UsoMedio` (GET .../usos, que no cambia)."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from apps.contenido.models import ContenidoMedio, TipoContenido
from apps.contenido.tests import publicos
from apps.contenido.tests.conftest import validar_contra
from apps.inicio.models import ID_SINGLETON, ConfigInicio
from apps.medios import services
from apps.medios.models import EstadoMedio, Medio

BASE = "/api/v1/panel/medios"

pytestmark = pytest.mark.django_db


def _retirar_409(cliente: Client, medio_id: int) -> dict[str, Any]:
    respuesta = cliente.post(f"{BASE}/{medio_id}/retirar")
    assert respuesta.status_code == 409, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
    cuerpo: dict[str, Any] = respuesta.json()
    assert cuerpo["code"] == "medio_en_uso"
    assert validar_contra("ProblemaConUsos", cuerpo) == []
    return cuerpo


def test_AC_TKT033_03_usos_del_409_con_forma_referencia_uso(cliente_editora: Client) -> None:
    destino = publicos.destino("Destino con portada", tipos=[])
    medio_id = destino.contenido.portada_id
    galeria = publicos.destino("Destino con galería", tipos=[])
    ContenidoMedio.objects.create(
        contenido=galeria.contenido,
        tipo_contenido=TipoContenido.DESTINO,
        medio_id=medio_id,
        orden=9,
    )
    # El mismo contenido como portada y en la galería: una sola referencia.
    ContenidoMedio.objects.create(
        contenido=destino.contenido,
        tipo_contenido=TipoContenido.DESTINO,
        medio_id=medio_id,
        orden=9,
    )
    ConfigInicio.objects.update_or_create(
        pk=ID_SINGLETON,
        defaults={"hero_titular": "Hero", "hero_subtitulo": "Sub", "hero_medio_id": medio_id},
    )

    cuerpo = _retirar_409(cliente_editora, medio_id)

    assert cuerpo["usos"] == [
        {
            "tipo_entidad": "DESTINO",
            "id": destino.contenido_id,
            "titulo": "Destino con portada",
            "estado_editorial": "PUBLICADO",
        },
        {
            "tipo_entidad": "DESTINO",
            "id": galeria.contenido_id,
            "titulo": "Destino con galería",
            "estado_editorial": "PUBLICADO",
        },
        {
            "tipo_entidad": "CONFIG_INICIO",
            "id": ID_SINGLETON,
            "titulo": "Portada de inicio",
            "estado_editorial": None,
        },
    ]
    assert cuerpo["total_usos"] == 3
    assert Medio.objects.get(pk=medio_id).estado == EstadoMedio.DISPONIBLE


def test_AC_TKT033_03_usos_del_409_se_recortan_al_maximo(cliente_editora: Client) -> None:
    destino = publicos.destino("Destino", tipos=[])
    medio_id = destino.contenido.portada_id
    extra = services.MAX_USOS + 1
    for n in range(extra):
        otro = publicos._contenido("GUIA", f"Guía {n}", "BORRADOR", publicos.BASE)
        ContenidoMedio.objects.create(
            contenido=otro, tipo_contenido=TipoContenido.GUIA, medio_id=medio_id, orden=0
        )

    cuerpo = _retirar_409(cliente_editora, medio_id)

    assert len(cuerpo["usos"]) == services.MAX_USOS
    assert cuerpo["total_usos"] == extra + 1


def test_AC_TKT033_03_get_usos_conserva_la_forma_uso_medio(cliente_editora: Client) -> None:
    """Regresión: el listado de usos (UsoMedio, consumido por el panel) no cambia."""
    destino = publicos.destino("Destino", tipos=[])
    respuesta = cliente_editora.get(f"{BASE}/{destino.contenido.portada_id}/usos")
    assert respuesta.status_code == 200, respuesta.content
    assert set(respuesta.json()["resultados"][0]) == {
        "tipo_contenido",
        "contenido_id",
        "titulo",
        "estado_editorial",
        "rol",
    }
