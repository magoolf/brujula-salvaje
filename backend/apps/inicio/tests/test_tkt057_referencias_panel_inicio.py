"""TKT-057: `GET/PUT /api/v1/panel/inicio` cumplen `components.schemas.ConfigInicioPanel`.

- `referencias.medios` = miniatura del medio del hero (`MedioMiniatura`, maxItems 1) y
  `referencias.contenidos` = los contenidos destacados (`ContenidoRefPanel`, maxItems 24), en el
  orden de sus secciones; antes se devolvían siempre vacías.
- `actualizado_por.etiqueta` = usuario de la cuenta (`ActorRef`: "Usuario o seudónimo si la cuenta
  está anonimizada; 'sistema' para procesos"); antes era `#<id>`.
- Sin N+1: número de consultas fijo, independiente del número de destacados.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.contenido.models import Contenido
from apps.contenido.tests import publicos
from apps.contenido.tests.fabricas import crear_cuenta
from apps.cuentas.models import CuentaStaff, EstadoCuenta
from apps.inicio import services
from apps.inicio.api.serializers import ConfigInicioPanelSerializer
from apps.inicio.models import ConfigInicio
from apps.inicio.tests.test_ac_tkt006_05_inicio_configuracion_tablero import _mundo_minimo
from apps.medios.models import Medio, MedioDerivado

pytestmark = pytest.mark.django_db

RUTA = "/api/v1/panel/inicio"


def _cuerpo(mundo: dict[str, list[int]], hero: Medio) -> dict[str, Any]:
    return {
        "hero_titular": "Explora",
        "hero_subtitulo": "Aventura con criterio",
        "hero_medio_id": hero.pk,
        "destinos_ids": mundo["destinos"],
        "itinerarios_ids": mundo["itinerarios"],
        "guias_ids": mundo["guias"],
    }


def _contenidos_esperados(mundo: dict[str, list[int]]) -> list[dict[str, Any]]:
    ids = [*mundo["destinos"], *mundo["itinerarios"], *mundo["guias"]]
    por_id = {c.pk: c for c in Contenido.objects.filter(pk__in=ids)}
    return [
        {
            "tipo": por_id[i].tipo,
            "id": i,
            "titulo": por_id[i].titulo,
            "slug": por_id[i].slug,
            "estado_editorial": por_id[i].estado_editorial,
        }
        for i in ids
    ]


def _medio_esperado(hero: Medio) -> dict[str, Any]:
    # `publicos.medio()` crea AVIF 800, WEBP 800 y JPEG 1600: el más estrecho, WebP a igual ancho.
    return {
        "id": hero.pk,
        "estado": hero.estado,
        "texto_alternativo": hero.texto_alternativo,
        "licencia_codigo": hero.licencia.codigo,
        "url_miniatura": f"/api/v1/panel/medios/{hero.pk}/archivo?ancho=800&formato=WEBP",
    }


def test_TKT057_put_y_get_devuelven_referencias_y_etiqueta_reales(
    cliente_editora: Client, editora: Any
) -> None:
    publicos.config_inicio()
    mundo = _mundo_minimo()
    hero = publicos.medio()
    respuesta = cliente_editora.put(RUTA, _cuerpo(mundo, hero), content_type="application/json")
    assert respuesta.status_code == 200, respuesta.content
    esperado_ref = {"medios": [_medio_esperado(hero)], "contenidos": _contenidos_esperados(mundo)}
    esperado_actor = {"id": editora.cuenta.pk, "etiqueta": editora.cuenta.usuario}

    for datos in (respuesta.json(), cliente_editora.get(RUTA).json()):
        assert datos["referencias"] == esperado_ref
        assert datos["actualizado_por"] == esperado_actor
        assert datos["destinos_ids"] == mundo["destinos"]
        assert datos["itinerarios_ids"] == mundo["itinerarios"]
        assert datos["guias_ids"] == mundo["guias"]


def test_TKT057_referencias_incluyen_destacados_no_publicados(cliente_editora: Client) -> None:
    """El panel ve el estado real de cada destacado (p. ej. uno retirado tras destacarlo), igual
    que lo cuentan `*_ids`; el filtro PUBLICADO es del sitio público, no del panel."""
    publicos.config_inicio()
    mundo = _mundo_minimo()
    actor = crear_cuenta("editora.ref")
    services.actualizar_config_inicio(actor.pk, _cuerpo(mundo, publicos.medio()))
    Contenido.objects.filter(pk=mundo["guias"][0]).update(
        estado_editorial="RETIRADO", retirado_en=timezone.now(), motivo_retiro="Desactualizada"
    )

    datos = cliente_editora.get(RUTA).json()
    retirado = next(c for c in datos["referencias"]["contenidos"] if c["id"] == mundo["guias"][0])
    assert retirado["estado_editorial"] == "RETIRADO"
    assert len(datos["referencias"]["contenidos"]) == 12


def test_TKT057_etiqueta_de_cuenta_anonimizada_es_el_seudonimo(cliente_editora: Client) -> None:
    publicos.config_inicio()
    mundo = _mundo_minimo()
    autora = crear_cuenta("autora.anonimizable")
    services.actualizar_config_inicio(autora.pk, _cuerpo(mundo, publicos.medio()))
    ahora = timezone.now()
    CuentaStaff.objects.filter(pk=autora.pk).update(
        usuario=None,
        nombre_visible=None,
        estado=EstadoCuenta.ANONIMIZADA,
        password="!inutilizable",  # noqa: S106  # nosec B106 (hash inutilizable, no es un secreto)
        desactivado_en=ahora,
        anonimizado_en=ahora,
    )

    datos = cliente_editora.get(RUTA).json()
    assert datos["actualizado_por"] == {
        "id": autora.pk,
        "etiqueta": f"Cuenta anonimizada #{autora.pk}",
    }


def test_TKT057_sin_actor_la_etiqueta_es_sistema(cliente_editora: Client) -> None:
    publicos.config_inicio()  # carga semilla: actualizado_por NULL (DEC-AUTO-095)
    datos = cliente_editora.get(RUTA).json()
    assert datos["actualizado_por"] == {"id": None, "etiqueta": "sistema"}
    assert datos["referencias"]["contenidos"] == []
    assert len(datos["referencias"]["medios"]) == 1


def test_TKT057_hero_sin_derivados_se_omite_de_referencias(cliente_editora: Client) -> None:
    """DEC-AUTO-1081: sin derivado no hay `url_miniatura` que enlazar (campo obligatorio)."""
    config = publicos.config_inicio()
    MedioDerivado.objects.filter(medio_id=config.hero_medio_id).delete()
    datos = cliente_editora.get(RUTA).json()
    assert datos["referencias"]["medios"] == []
    assert datos["hero_medio_id"] == config.hero_medio_id


def _serializar() -> dict[str, Any]:
    return dict(ConfigInicioPanelSerializer(services.obtener_config_inicio()).data)


def test_TKT057_sin_n_mas_1(django_assert_num_queries: Any) -> None:
    """3 consultas fijas (config + autor + medio/licencia por JOIN; derivados del hero; destacados
    con su contenido por JOIN), con 12 destacados igual que con ninguno."""
    publicos.config_inicio()
    with django_assert_num_queries(3):
        vacio = _serializar()
    assert vacio["referencias"]["contenidos"] == []

    mundo = _mundo_minimo()
    services.actualizar_config_inicio(
        crear_cuenta("editora.n1").pk, _cuerpo(mundo, publicos.medio())
    )
    with django_assert_num_queries(3):
        lleno = _serializar()
    assert len(lleno["referencias"]["contenidos"]) == 12
    assert lleno["actualizado_por"]["etiqueta"] == "editora.n1"


def test_TKT057_put_no_hace_consultas_por_destacado(cliente_editora: Client) -> None:
    """La respuesta del PUT relee el singleton con sus relaciones: el número de consultas no
    crece con el número de destacados (6+3+3 frente a 12+6+6)."""
    publicos.config_inicio()
    mundo = _mundo_minimo()
    hero = publicos.medio()
    with CaptureQueriesContext(connection) as minimo:
        r = cliente_editora.put(RUTA, _cuerpo(mundo, hero), content_type="application/json")
    assert r.status_code == 200, r.content

    tipo = publicos.tipo("Tipo de inicio extra")
    mundo["destinos"] += [
        publicos.destino(f"Destino extra {i}", tipos=[tipo]).contenido_id for i in range(6)
    ]
    mundo["itinerarios"] += [
        publicos.itinerario(
            f"Itinerario extra {i}", publicos.destino(f"Base extra {i}", tipos=[tipo])
        ).contenido_id
        for i in range(3)
    ]
    mundo["guias"] += [publicos.guia(f"Guía extra {i}").contenido_id for i in range(3)]
    with CaptureQueriesContext(connection) as maximo:
        r = cliente_editora.put(RUTA, _cuerpo(mundo, hero), content_type="application/json")
    assert r.status_code == 200, r.content
    assert len(r.json()["referencias"]["contenidos"]) == 24
    assert len(maximo.captured_queries) == len(minimo.captured_queries)
    assert ConfigInicio.objects.get().actualizado_por_id is not None
