"""AC-TKT006 (QA ciclo 1/3, BUG-1): pruebas HTTP reales (Django test `Client`, sesión de panel
real vía `cliente_editora`) de crear/obtener/actualizar/publicar Destino, Itinerario y Guía CON
al menos un tipo de aventura asociado.

Motivo de este archivo (no solo cobertura por cobertura): las 5 rondas de corrección del gate de
contrato de este ticket nunca ejecutaron una petición HTTP real contra Postgres (sin Docker en el
entorno de esas rondas), así que ninguna prueba anterior habría atrapado que
`DestinoPanelSerializer`/`ItinerarioPanelSerializer`/`GuiaPanelSerializer.to_representation`
(apps/contenido/api/panel_serializers.py) leían `tipos_aventura.values_list("id", flat=True)` --
`TipoAventura` es un supertipo 1:1 (patrón ADR-DB-002) cuya PK real es `contenido`, no `id`; el
campo simplemente no existe en ese modelo. Sin capturar, eso producía un 500 en CUALQUIER
crear/obtener/actualizar/publicar de estos 3 tipos que tuviera un tipo de aventura asociado --
prácticamente todos los casos reales. QA lo reprodujo con Postgres real; este archivo deja la
reproducción en el repo para que no vuelva a pasar inadvertida.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db

BASE = "/api/v1/panel/contenidos"


def _crear_tipo_aventura(cliente: Client, titulo: str) -> int:
    respuesta = cliente.post(
        f"{BASE}/tipos-aventura", {"titulo": titulo}, content_type="application/json"
    )
    assert respuesta.status_code == 201, respuesta.content
    return int(respuesta.json()["id"])


@pytest.mark.parametrize(
    ("ruta", "titulo"),
    [
        ("destinos", "Cocuy con tipo de aventura"),
        ("itinerarios", "Itinerario con tipo de aventura"),
        ("guias", "Guía con tipo de aventura"),
    ],
)
def test_AC_TKT006_08_crear_y_obtener_con_tipo_aventura_no_revienta(
    cliente_editora: Client, ruta: str, titulo: str
) -> None:
    """BUG-1: reproducción exacta de QA -- crear un tipo-aventura (201), luego crear el contenido
    con `tipos_ids: [<ese id>]` (antes: 500 `error_interno`), y por último obtenerlo (GET, antes
    también 500)."""
    tipo_id = _crear_tipo_aventura(cliente_editora, f"Tipo para {ruta}")

    creado = cliente_editora.post(
        f"{BASE}/{ruta}",
        {"titulo": titulo, "tipos_ids": [tipo_id]},
        content_type="application/json",
    )
    assert creado.status_code == 201, creado.content
    cuerpo_creado: dict[str, Any] = creado.json()
    assert cuerpo_creado["tipos_ids"] == [tipo_id]
    id_contenido = cuerpo_creado["id"]

    obtenido = cliente_editora.get(f"{BASE}/{ruta}/{id_contenido}")
    assert obtenido.status_code == 200, obtenido.content
    assert obtenido.json()["tipos_ids"] == [tipo_id]


def test_AC_TKT006_08_ciclo_completo_destino_con_tipo_aventura(cliente_editora: Client) -> None:
    """BUG-1, ciclo completo pedido explícitamente por QA: crear -> obtener -> actualizar ->
    publicar un Destino con un tipo de aventura asociado. `actualizar` (PUT) pasa por
    `DestinoGuardadoSerializer` (envuelve `DestinoPanelSerializer`), la misma línea que crear/
    obtener; `publicar` no serializa el subtipo completo (usa un dict ligero en
    `services._entidad_transitada`), pero se incluye para probar el flujo de punta a punta que
    pidió QA, no solo la línea exacta del bug."""
    tipo_id = _crear_tipo_aventura(cliente_editora, "Tipo para ciclo completo")

    creado = cliente_editora.post(
        f"{BASE}/destinos",
        {"titulo": "Destino ciclo completo", "tipos_ids": [tipo_id]},
        content_type="application/json",
    )
    assert creado.status_code == 201, creado.content
    cuerpo = creado.json()
    destino_id = cuerpo["id"]
    version = cuerpo["version"]
    assert cuerpo["tipos_ids"] == [tipo_id]

    obtenido = cliente_editora.get(f"{BASE}/destinos/{destino_id}")
    assert obtenido.status_code == 200, obtenido.content
    assert obtenido.json()["tipos_ids"] == [tipo_id]

    actualizado = cliente_editora.put(
        f"{BASE}/destinos/{destino_id}",
        {
            "titulo": "Destino ciclo completo (editado)",
            "tipos_ids": [tipo_id],
            "version": version,
        },
        content_type="application/json",
    )
    assert actualizado.status_code == 200, actualizado.content
    cuerpo_actualizado = actualizado.json()
    # PUT de Destino responde `DestinoGuardadoSerializer(DestinoPanelSerializer)`: mismo esquema
    # plano de `DestinoPanelSerializer` (incluido `tipos_ids`) más `entidades_afectadas`.
    assert cuerpo_actualizado["tipos_ids"] == [tipo_id]
    version_tras_editar = cuerpo_actualizado["version"]

    # `publicar` exige muchos requisitos no relacionados con BUG-1 (RULE-002: resumen,
    # descripcion_experta >= 600 palabras, portada_id con un medio real, clima, etc. --
    # reglas.validar_destino) que este destino mínimo no cumple a propósito: no son parte de este
    # bug ni de este ticket, y satisfacerlos aquí solo añadiría fragilidad sin probar nada nuevo
    # de BUG-1. Lo que SÍ es relevante para BUG-1 es que el endpoint responda con normalidad (422
    # `publicacion_invalida`, la respuesta correcta cuando faltan requisitos) y NO con un 500: eso
    # confirma que el propio manejo de `tipos_aventura` en el camino de publicar (co-publicación,
    # `_validar_entidad_para_publicar`) tampoco revienta con un tipo de aventura asociado.
    publicado = cliente_editora.post(
        f"{BASE}/destinos/{destino_id}/publicar",
        {"version": version_tras_editar},
        content_type="application/json",
    )
    assert publicado.status_code == 422, publicado.content
    assert publicado.json()["code"] == "publicacion_invalida"
