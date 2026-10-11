"""TKT-062 en inicio.

- `Tablero.recientes[].actualizado_por` (ContenidoResumenPanel) cumple ActorRef: usuario,
  seudónimo si la cuenta está anonimizada, "sistema" sin actor; antes era `#<id>`. Sin N+1.
- OBS-QA057-01: `actualizar_config_inicio` relee la configuración y sus destacados DENTRO de la
  transacción que los escribe, con la fila del singleton aún bloqueada; antes la relectura (y la
  de los destacados, en el serializer) se hacía tras el COMMIT y podía devolver la escritura de
  otro PUT confirmado justo después.
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
from apps.contenido.tests.conftest import validar_contra
from apps.contenido.tests.fabricas import crear_cuenta
from apps.cuentas.models import CuentaStaff, EstadoCuenta
from apps.inicio import selectors, services
from apps.inicio.api.serializers import ConfigInicioPanelSerializer
from apps.inicio.tests.test_ac_tkt006_05_inicio_configuracion_tablero import _mundo_minimo

pytestmark = pytest.mark.django_db

TABLERO = "/api/v1/panel/tablero"


def test_TKT062_tablero_recientes_llevan_el_usuario(cliente_editora: Client) -> None:
    tipo = publicos.tipo("Tipo tablero 062")
    autora = crear_cuenta("autora.tablero")
    anonima = crear_cuenta("autora.anonima")
    con_autora = publicos.destino("Reciente autora", tipos=[tipo], actualizado_por=autora)
    con_anonima = publicos.destino("Reciente anónima", tipos=[tipo], actualizado_por=anonima)
    ahora = timezone.now()
    CuentaStaff.objects.filter(pk=anonima.pk).update(
        usuario=None,
        nombre_visible=None,
        estado=EstadoCuenta.ANONIMIZADA,
        password="!inutilizable",  # nosec B106 (hash inutilizable, no es un secreto)
        desactivado_en=ahora,
        anonimizado_en=ahora,
    )

    datos = cliente_editora.get(TABLERO).json()
    assert validar_contra("Tablero", datos) == []
    por_id = {r["id"]: r["actualizado_por"] for r in datos["recientes"]}
    assert por_id[con_autora.contenido_id] == {"id": autora.pk, "etiqueta": "autora.tablero"}
    assert por_id[con_anonima.contenido_id] == {
        "id": anonima.pk,
        "etiqueta": f"Cuenta anonimizada #{anonima.pk}",
    }
    sin_actor = [r for r in datos["recientes"] if r["actualizado_por"]["id"] is None]
    assert sin_actor  # el tipo y la semilla de publicos no tienen actor
    assert all(r["actualizado_por"]["etiqueta"] == "sistema" for r in sin_actor)
    assert not any(r["etiqueta"].startswith("#") for r in por_id.values())


def test_TKT062_tablero_sin_n_mas_1_por_autor(cliente_editora: Client) -> None:
    tipo = publicos.tipo("Tipo tablero n1")
    destinos = [publicos.destino(f"Reciente {i}", tipos=[tipo]) for i in range(10)]
    with CaptureQueriesContext(connection) as sin_autores:
        assert cliente_editora.get(TABLERO).status_code == 200
    for i, d in enumerate(destinos):
        Contenido.objects.filter(pk=d.contenido_id).update(
            actualizado_por=crear_cuenta(f"autora.reciente{i}")
        )
    with CaptureQueriesContext(connection) as con_autores:
        respuesta = cliente_editora.get(TABLERO)
    etiquetas = {r["actualizado_por"]["etiqueta"] for r in respuesta.json()["recientes"]}
    assert etiquetas == {f"autora.reciente{i}" for i in range(10)}
    assert len(con_autores.captured_queries) == len(sin_autores.captured_queries)


def test_TKT062_OBS_QA057_01_relectura_dentro_de_la_transaccion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La configuración y los destacados que pinta la respuesta se leen con el bloque atómico del
    servicio aún abierto (un nivel más que fuera de él) y la fila del singleton bloqueada."""
    publicos.config_inicio()
    mundo = _mundo_minimo()
    hero = publicos.medio()
    actor = crear_cuenta("editora.relectura")
    profundidad_fuera = len(connection.atomic_blocks)
    lecturas: list[tuple[str, int]] = []

    def espiar(nombre: str, original: Any) -> Any:
        def envoltura() -> Any:
            lecturas.append((nombre, len(connection.atomic_blocks)))
            return original()

        return envoltura

    monkeypatch.setattr(
        selectors, "config_inicio_panel", espiar("config", selectors.config_inicio_panel)
    )
    monkeypatch.setattr(
        selectors, "destacados_panel", espiar("destacados", selectors.destacados_panel)
    )
    config = services.actualizar_config_inicio(
        actor.pk,
        {
            "hero_titular": "Explora",
            "hero_subtitulo": "Aventura con criterio",
            "hero_medio_id": hero.pk,
            "destinos_ids": mundo["destinos"],
            "itinerarios_ids": mundo["itinerarios"],
            "guias_ids": mundo["guias"],
        },
    )
    datos = dict(ConfigInicioPanelSerializer(config).data)

    # Ambas lecturas ocurrieron dentro del atomic del servicio y ninguna después (el serializer
    # usa los destacados ya leídos, no vuelve a consultarlos tras el COMMIT).
    assert lecturas == [("config", profundidad_fuera + 1), ("destacados", profundidad_fuera + 1)]
    assert datos["destinos_ids"] == mundo["destinos"]
    assert datos["actualizado_por"] == {"id": actor.pk, "etiqueta": "editora.relectura"}
