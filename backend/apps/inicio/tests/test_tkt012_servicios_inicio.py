"""TKT-012 (deuda de cobertura, Skill_Backend §8: services > 90 %): ramas de
`apps.inicio.services` que ninguna prueba ejercía.

- Singletons ausentes (`ConfigInicio` antes de la carga semilla, `ConfigSitio` borrado):
  obtener y actualizar responden `NoEncontrado`, nunca un 500.
- Hero con un medio que no está DISPONIBLE: `regla_negocio` sobre `hero_medio_id`.
- Tablero: alerta `destacado_retirado` cuando un destacado de inicio deja de estar publicado.
"""

from __future__ import annotations

import pytest

from apps.contenido.models import EstadoEditorial
from apps.contenido.tests import publicos
from apps.contenido.tests.fabricas import crear_cuenta
from apps.core.exceptions import NoEncontrado
from apps.inicio import services
from apps.inicio.models import ConfigInicio, ConfigSitio, SeccionInicio
from apps.inicio.tests.test_ac_tkt006_05_inicio_configuracion_tablero import _mundo_minimo
from apps.medios.models import EstadoMedio

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor() -> int:
    return crear_cuenta("editora.tkt012.inicio").pk


def test_TKT012_config_inicio_ausente_es_no_encontrado(actor: int) -> None:
    assert not ConfigInicio.objects.exists()
    with pytest.raises(NoEncontrado):
        services.obtener_config_inicio()
    with pytest.raises(NoEncontrado):
        services.actualizar_config_inicio(actor, {"hero_medio_id": publicos.medio().pk})


def test_TKT012_config_sitio_ausente_es_no_encontrado(actor: int) -> None:
    ConfigSitio.objects.all().delete()
    with pytest.raises(NoEncontrado):
        services.obtener_config_sitio()
    with pytest.raises(NoEncontrado):
        services.actualizar_config_sitio(actor, {"nombre_marca": "Marca"})


def test_TKT012_hero_con_medio_no_disponible_es_regla_negocio(actor: int) -> None:
    config = publicos.config_inicio()
    mundo = _mundo_minimo()
    pendiente = publicos.medio(estado=EstadoMedio.PENDIENTE_METADATOS)

    with pytest.raises(services.ReglaNegocio) as error:
        services.actualizar_config_inicio(
            actor,
            {
                "hero_titular": "Explora",
                "hero_subtitulo": "Aventuras",
                "hero_medio_id": pendiente.pk,
                "destinos_ids": mundo["destinos"],
                "itinerarios_ids": mundo["itinerarios"],
                "guias_ids": mundo["guias"],
            },
        )

    assert "hero_medio_id" in error.value.errors
    config.refresh_from_db()
    assert config.hero_medio_id != pendiente.pk


def test_TKT012_tablero_alerta_destacado_que_ya_no_esta_publicado() -> None:
    publicos.config_inicio()
    retirado = publicos.destino(
        "Destino destacado retirado", tipos=[], estado=EstadoEditorial.RETIRADO
    )
    publicos.destacar(SeccionInicio.DESTINOS, retirado.contenido)

    alertas = services.tablero(es_administrador=False)["alertas"]

    codigos = [a["code"] for a in alertas]
    assert "destacado_retirado" in codigos
    # Sin rol de administrador no se evalúa la alerta del Responsable del sitio.
    assert "responsable_sin_definir" not in codigos
    alerta = next(a for a in alertas if a["code"] == "destacado_retirado")
    assert "Destino destacado retirado" in alerta["mensaje"]
    assert alerta["enlace"] == "/panel/inicio"
