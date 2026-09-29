"""AC-TKT006: destacados de inicio, configuración del sitio y tablero (FEAT-043/047/049)."""

from __future__ import annotations

import pytest

from apps.contenido.models import TipoContenido
from apps.contenido.tests import publicos
from apps.contenido.tests.fabricas import crear_cuenta
from apps.inicio import services
from apps.inicio.models import ConfigSitio

T = TipoContenido
pytestmark = pytest.mark.django_db


@pytest.fixture
def actor() -> int:
    return crear_cuenta("editora.inicio").pk


def _mundo_minimo() -> dict[str, list[int]]:
    tipo = publicos.tipo("Tipo de inicio")
    destinos = [
        publicos.destino(f"Destino inicio {i}", tipos=[tipo]).contenido_id for i in range(6)
    ]
    itinerarios = [
        publicos.itinerario(
            f"Itinerario inicio {i}", publicos.destino(f"Base {i}", tipos=[tipo])
        ).contenido_id
        for i in range(3)
    ]
    guias = [publicos.guia(f"Guía inicio {i}").contenido_id for i in range(3)]
    return {"destinos": destinos, "itinerarios": itinerarios, "guias": guias}


def test_AC_TKT006_05_actualizar_config_inicio_valido(actor: int) -> None:
    publicos.config_inicio()
    mundo = _mundo_minimo()
    hero = publicos.medio()

    config = services.actualizar_config_inicio(
        actor,
        {
            "hero_titular": "Explora",
            "hero_subtitulo": "Aventuras",
            "hero_medio_id": hero.pk,
            "destinos_ids": mundo["destinos"],
            "itinerarios_ids": mundo["itinerarios"],
            "guias_ids": mundo["guias"],
        },
    )
    assert config.hero_titular == "Explora"
    assert set(services.SECCION_TIPO) == {"DESTINOS", "ITINERARIOS", "GUIAS"}


def test_AC_TKT006_05_config_inicio_rechaza_contenido_no_publicado(actor: int) -> None:
    publicos.config_inicio()
    mundo = _mundo_minimo()
    hero = publicos.medio()
    borrador = publicos.destino("Destino borrador", tipos=[], estado="BORRADOR")

    with pytest.raises(services.ReglaNegocio):
        services.actualizar_config_inicio(
            actor,
            {
                "hero_titular": "Explora",
                "hero_subtitulo": "Aventuras",
                "hero_medio_id": hero.pk,
                "destinos_ids": [*mundo["destinos"][:5], borrador.contenido_id],
                "itinerarios_ids": mundo["itinerarios"],
                "guias_ids": mundo["guias"],
            },
        )


def test_AC_TKT006_05_config_inicio_exige_minimos(actor: int) -> None:
    publicos.config_inicio()
    mundo = _mundo_minimo()
    hero = publicos.medio()
    with pytest.raises(services.ReglaNegocio):
        services.actualizar_config_inicio(
            actor,
            {
                "hero_titular": "Explora",
                "hero_subtitulo": "Aventuras",
                "hero_medio_id": hero.pk,
                "destinos_ids": mundo["destinos"][:3],
                "itinerarios_ids": mundo["itinerarios"],
                "guias_ids": mundo["guias"],
            },
        )


def test_AC_TKT006_05_actualizar_configuracion_sitio(actor: int) -> None:
    # `ConfigSitio` (id=1) ya viene sembrada por la migración 0001 (singleton, DB_HANDOFF).
    config = services.actualizar_config_sitio(
        actor,
        {
            "nombre_marca": "Brújula Salvaje",
            "texto_descargo": "Nuevo descargo",
            "responsable_nombre": "Responsable de prueba",
        },
    )
    assert config.texto_descargo == "Nuevo descargo"
    assert config.responsable_nombre == "Responsable de prueba"


def test_AC_TKT006_05_tablero_cuenta_por_tipo_y_estado() -> None:
    tipo = publicos.tipo("Tipo tablero")
    publicos.destino("Destino publicado tablero", tipos=[tipo])
    publicos.destino("Destino borrador tablero", tipos=[], estado="BORRADOR")

    resultado = services.tablero(es_administrador=False)
    conteos = {c["tipo"]: c for c in resultado["conteos"]}
    assert conteos[T.DESTINO]["publicado"] >= 1
    assert conteos[T.DESTINO]["borrador"] >= 1
    assert resultado["salud_editorial"] is None
    assert not any(a["code"] == "responsable_sin_definir" for a in resultado["alertas"])


def test_AC_TKT006_05_tablero_alerta_responsable_solo_para_administrador() -> None:
    # `ConfigSitio` (id=1) ya viene sembrada por la migración 0001 con `responsable_nombre`
    # vacío (GAP-004), así que no hace falta crearla aquí.
    assert ConfigSitio.objects.get(pk=1).responsable_nombre is None
    resultado_admin = services.tablero(es_administrador=True)
    resultado_editor = services.tablero(es_administrador=False)
    assert any(a["code"] == "responsable_sin_definir" for a in resultado_admin["alertas"])
    assert not any(a["code"] == "responsable_sin_definir" for a in resultado_editor["alertas"])


def test_AC_TKT006_05_tablero_alerta_coleccion_bajo_minimo() -> None:
    tipo = publicos.tipo("Tipo colección")
    destino_ = publicos.destino("Destino colección", tipos=[tipo])
    coleccion = publicos.coleccion("Colección incompleta", [destino_.contenido])
    resultado = services.tablero(es_administrador=False)
    assert any(
        a["code"] == "coleccion_bajo_minimo" and coleccion.contenido.titulo in a["mensaje"]
        for a in resultado["alertas"]
    )
