"""TKT-051 (QA TKT-023 OBS-BE-01): requisitos de publicación sobre el estado RESULTANTE.

Antes, el PUT de un contenido PUBLICADO (`_actualizar_publicacion`) aplicaba las colecciones hijas
`replace-all` (checklist del tipo, días del itinerario, elementos de la colección) DESPUÉS de
validar los requisitos, de modo que la regla leía las GUARDADAS y no las enviadas:

- reducir el checklist de un tipo publicado de 10 a 7 respondía 200 (quedaba publicado
  incumpliendo RULE-025 Should "≥ 8") y
- a partir de ahí cualquier corrección (6, 8 o 10) respondía 422 `checklist_insuficiente`: el
  contenido quedaba bloqueado. Lo mismo con los días de un itinerario y los elementos de una
  colección.

Además `analisis-publicacion` de un contenido PUBLICADO (no destino) validaba el estado GUARDADO,
que la operación de escritura sustituye, y declaraba "no confirmable" la corrección de un contenido
ya inconsistente. Contrato: PUT → 422 `ReglaNegocioPublicacion` (`publicacion_invalida` con
`errores_por_entidad`); `panelAnalizarPublicacion` → en ACTUALIZAR_PUBLICACION `entidad` solo trae
las reglas multi-entidad.

Las colecciones que ya se aplicaban antes de validar (fuentes, relaciones, galería, tipos M2M) se
cubren como regresión.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.test import Client

from apps.contenido import services
from apps.contenido.models import (
    ChecklistItem,
    Contenido,
    DiaItinerario,
    ElementoColeccion,
    Fuente,
    TipoContenido,
)
from apps.contenido.tests import publicos

T = TipoContenido
BASE = "/api/v1/panel/contenidos"

pytestmark = pytest.mark.django_db


def _json(cliente: Client, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
    return getattr(cliente, metodo)(ruta, cuerpo, content_type="application/json")


def _ruta(tipo: str, contenido_id: int) -> str:
    return f"{BASE}/{services.TIPO_A_RUTA[tipo]}/{contenido_id}"


def _version(contenido_id: int) -> int:
    return Contenido.objects.get(pk=contenido_id).version


def _put(cliente: Client, tipo: str, contenido_id: int, cambios: dict[str, Any]) -> Any:
    """PUT como el formulario del panel: el cuerpo completo `{Tipo}Actualizacion` (lo editable que
    devuelve el GET) con `cambios` aplicados. Las colecciones omitidas se REEMPLAZAN por vacías."""
    actual = cliente.get(_ruta(tipo, contenido_id)).json()
    cuerpo = {c: actual[c] for c in services.CAMPOS_EDITABLES[tipo]}
    return _json(
        cliente,
        "put",
        _ruta(tipo, contenido_id),
        cuerpo | cambios | {"version": actual["version"]},
    )


def _codigos_principal(respuesta: Any) -> set[str]:
    cuerpo = respuesta.json()
    principal = [e for e in cuerpo["errores_por_entidad"] if e["rol"] == "PRINCIPAL"]
    return {err["code"] for entidad in principal for err in entidad["errores"]}


def _assert_rechazado(
    respuesta: Any, code: str, conforme: Callable[[str, Any], None], version_previa: int, pk: int
) -> None:
    assert respuesta.status_code == 422, respuesta.content
    assert respuesta["Content-Type"].startswith("application/problem+json")
    cuerpo = respuesta.json()
    conforme("ProblemaPublicacion", cuerpo)
    assert cuerpo["code"] == "publicacion_invalida"
    assert code in _codigos_principal(respuesta)
    # Sin persistir: la versión no avanza (rollback de la transacción).
    assert _version(pk) == version_previa


def _checklist(n: int) -> list[dict[str, Any]]:
    return [
        {"texto": f"Elemento {i}", "grupo": "Equipo", "esencial": i == 0, "orden": i}
        for i in range(n)
    ]


def _dias(n: int) -> list[dict[str, Any]]:
    return [
        {"numero_dia": i, "titulo": f"Día {i}", "actividades": "<p>Caminar</p>"}
        for i in range(1, n + 1)
    ]


@pytest.fixture
def fondo() -> dict[str, Any]:
    """Tipo y destino publicados más contenido publicado suficiente para RULE-006 (≥ 3
    relacionados publicados) de cualquier entidad del módulo."""
    tipo = publicos.tipo("Senderismo TKT051")
    destinos = [publicos.destino(f"Destino {i} TKT051", tipos=[tipo]) for i in range(3)]
    return {"tipo": tipo, "destinos": destinos}


# --------------------------------------------------------------------- Tipo (checklist)
@pytest.fixture
def tipo_publicado(fondo: dict[str, Any]) -> int:
    """Tipo PUBLICADO que cumple todo con 10 elementos de checklist."""
    tipo = fondo["tipo"]
    ChecklistItem.objects.filter(tipo_aventura=tipo).delete()
    for item in _checklist(10):
        ChecklistItem.objects.create(tipo_aventura=tipo, **item)
    return int(tipo.pk)


def _n_checklist(tipo_id: int) -> int:
    return ChecklistItem.objects.filter(tipo_aventura_id=tipo_id).count()


def test_TKT051_01_tipo_reducir_checklist_bajo_el_minimo_rechaza_sin_persistir(
    tipo_publicado: int, cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    previa = _version(tipo_publicado)
    respuesta = _put(cliente_editora, T.TIPO, tipo_publicado, {"checklist": _checklist(7)})
    _assert_rechazado(respuesta, "checklist_insuficiente", conforme, previa, tipo_publicado)
    assert respuesta.json()["errors"]["checklist"]
    assert _n_checklist(tipo_publicado) == 10


@pytest.mark.parametrize("n", [8, 10])
def test_TKT051_02_tipo_inconsistente_con_7_se_corrige_con_un_put_valido(
    n: int, tipo_publicado: int, cliente_editora: Client
) -> None:
    # Estado inconsistente heredado del defecto: PUBLICADO con 7 elementos.
    ChecklistItem.objects.filter(tipo_aventura_id=tipo_publicado, orden__gte=7).delete()
    assert _n_checklist(tipo_publicado) == 7

    respuesta = _put(cliente_editora, T.TIPO, tipo_publicado, {"checklist": _checklist(n)})
    assert respuesta.status_code == 200, respuesta.content
    assert _n_checklist(tipo_publicado) == n
    assert len(respuesta.json()["checklist"]) == n


def test_TKT051_03_tipo_inconsistente_no_admite_otra_lista_insuficiente(
    tipo_publicado: int, cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    ChecklistItem.objects.filter(tipo_aventura_id=tipo_publicado, orden__gte=7).delete()
    previa = _version(tipo_publicado)
    respuesta = _put(cliente_editora, T.TIPO, tipo_publicado, {"checklist": _checklist(6)})
    _assert_rechazado(respuesta, "checklist_insuficiente", conforme, previa, tipo_publicado)
    assert _n_checklist(tipo_publicado) == 7


def test_TKT051_04_tipo_secuencia_de_la_qa(tipo_publicado: int, cliente_editora: Client) -> None:
    """Reproducción literal de OBS-BE-01: 8 → 200, 7 → 422, después 6 → 422 y 8/10 → 200."""
    resultados = [
        _put(cliente_editora, T.TIPO, tipo_publicado, {"checklist": _checklist(n)}).status_code
        for n in (8, 7, 6, 8, 10)
    ]
    assert resultados == [200, 422, 422, 200, 200]
    assert _n_checklist(tipo_publicado) == 10


def test_TKT051_05_tipo_checklist_vacio_sigue_admitido(
    tipo_publicado: int, cliente_editora: Client
) -> None:
    """RULE-025 Should: sin checklist (0) es válido; solo 1..7 es insuficiente. Sin cambios."""
    respuesta = _put(cliente_editora, T.TIPO, tipo_publicado, {"checklist": []})
    assert respuesta.status_code == 200, respuesta.content
    assert _n_checklist(tipo_publicado) == 0


def test_TKT051_06_tipo_inconsistente_sin_corregir_la_lista_sigue_rechazado(
    tipo_publicado: int, cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    """Editar otro campo reenviando la lista guardada de 7: el estado resultante sigue incumpliendo
    y se rechaza (no se "blanquea" la inconsistencia)."""
    ChecklistItem.objects.filter(tipo_aventura_id=tipo_publicado, orden__gte=7).delete()
    previa = _version(tipo_publicado)
    respuesta = _put(cliente_editora, T.TIPO, tipo_publicado, {"resumen": "Otro resumen"})
    _assert_rechazado(respuesta, "checklist_insuficiente", conforme, previa, tipo_publicado)
    assert _n_checklist(tipo_publicado) == 7


# --------------------------------------------------------------- Itinerario (días)
@pytest.fixture
def itinerario_publicado(fondo: dict[str, Any]) -> int:
    itinerario = publicos.itinerario(
        "Itinerario TKT051", fondo["destinos"][0], dias=3, tipos=[fondo["tipo"]]
    )
    return int(itinerario.pk)


def _n_dias(itinerario_id: int) -> int:
    return DiaItinerario.objects.filter(itinerario_id=itinerario_id).count()


def test_TKT051_07_itinerario_quitar_un_dia_rechaza_sin_persistir(
    itinerario_publicado: int, cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    previa = _version(itinerario_publicado)
    respuesta = _put(cliente_editora, T.ITINERARIO, itinerario_publicado, {"dias": _dias(2)})
    _assert_rechazado(respuesta, "dias_no_coinciden", conforme, previa, itinerario_publicado)
    assert _n_dias(itinerario_publicado) == 3


def test_TKT051_08_itinerario_inconsistente_se_corrige(
    itinerario_publicado: int, cliente_editora: Client
) -> None:
    DiaItinerario.objects.filter(itinerario_id=itinerario_publicado, numero_dia=3).delete()
    respuesta = _put(cliente_editora, T.ITINERARIO, itinerario_publicado, {"dias": _dias(3)})
    assert respuesta.status_code == 200, respuesta.content
    assert _n_dias(itinerario_publicado) == 3


def test_TKT051_09_itinerario_cambiar_duracion_y_dias_a_la_vez(
    itinerario_publicado: int, cliente_editora: Client
) -> None:
    """Duración y días se evalúan juntos sobre el resultado (antes: duración nueva contra los días
    guardados → 422 dias_no_coinciden)."""
    respuesta = _put(
        cliente_editora,
        T.ITINERARIO,
        itinerario_publicado,
        {"duracion_dias": 4, "dias": _dias(4)},
    )
    assert respuesta.status_code == 200, respuesta.content
    assert _n_dias(itinerario_publicado) == 4


# ------------------------------------------------------------ Colección (elementos)
@pytest.fixture
def coleccion_publicada(fondo: dict[str, Any]) -> tuple[int, list[Contenido]]:
    itinerario = publicos.itinerario("Itinerario col TKT051", fondo["destinos"][0])
    elementos = [d.contenido for d in fondo["destinos"]] + [itinerario.contenido]
    coleccion = publicos.coleccion("Colección TKT051", elementos)
    return int(coleccion.pk), elementos


def _elementos(contenidos: list[Contenido]) -> list[dict[str, Any]]:
    return [
        {"tipo_contenido": c.tipo, "contenido_id": c.pk, "orden": i, "nota_editorial": None}
        for i, c in enumerate(contenidos)
    ]


def _n_elementos(coleccion_id: int) -> int:
    return ElementoColeccion.objects.filter(coleccion_id=coleccion_id).count()


def test_TKT051_10_coleccion_bajo_el_minimo_rechaza_sin_persistir(
    coleccion_publicada: tuple[int, list[Contenido]],
    cliente_editora: Client,
    conforme: Callable[[str, Any], None],
) -> None:
    pk, elementos = coleccion_publicada
    previa = _version(pk)
    respuesta = _put(cliente_editora, T.COLECCION, pk, {"elementos": _elementos(elementos[:3])})
    _assert_rechazado(respuesta, "elementos_insuficientes", conforme, previa, pk)
    assert _n_elementos(pk) == 4


def test_TKT051_11_coleccion_inconsistente_se_corrige(
    coleccion_publicada: tuple[int, list[Contenido]], cliente_editora: Client
) -> None:
    pk, elementos = coleccion_publicada
    ElementoColeccion.objects.filter(coleccion_id=pk, contenido=elementos[3]).delete()
    assert _n_elementos(pk) == 3
    respuesta = _put(cliente_editora, T.COLECCION, pk, {"elementos": _elementos(elementos)})
    assert respuesta.status_code == 200, respuesta.content
    assert _n_elementos(pk) == 4


# ------------------------------------- Regresión: colecciones ya aplicadas antes de validar
def test_TKT051_12_guia_quitar_fuentes_rechaza_sin_persistir(
    fondo: dict[str, Any], cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    guia = publicos.guia("Guía TKT051")
    Fuente.objects.create(contenido=guia.contenido, titulo="Fuente", url="https://example.org")
    guia.remite_a_metodologia = False
    guia.save(update_fields=["remite_a_metodologia"])
    previa = _version(guia.pk)
    respuesta = _put(cliente_editora, T.GUIA, guia.pk, {"fuentes": []})
    _assert_rechazado(respuesta, "requerido", conforme, previa, guia.pk)
    assert Fuente.objects.filter(contenido_id=guia.pk).count() == 1


def test_TKT051_13_destino_galeria_insuficiente_rechaza_sin_persistir(
    fondo: dict[str, Any], cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    destino = fondo["destinos"][0]
    respuesta_get = cliente_editora.get(_ruta(T.DESTINO, destino.pk)).json()
    galeria = respuesta_get["galeria_ids"]
    assert len(galeria) == 3
    previa = _version(destino.pk)
    respuesta = _put(cliente_editora, T.DESTINO, destino.pk, {"galeria_ids": galeria[:2]})
    _assert_rechazado(respuesta, "minimo_medios", conforme, previa, destino.pk)
    assert cliente_editora.get(_ruta(T.DESTINO, destino.pk)).json()["galeria_ids"] == galeria


# ---------------------------------------------------------------- analisis-publicacion
def _analizar(cliente: Client, tipo: str, pk: int) -> Any:
    return _json(
        cliente, "post", f"{_ruta(tipo, pk)}/analisis-publicacion", {"version": _version(pk)}
    )


def test_TKT051_14_analisis_de_un_publicado_no_bloquea_la_correccion(
    tipo_publicado: int, cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    """Tipo PUBLICADO inconsistente (7): el análisis de ACTUALIZAR_PUBLICACION no puede ver el
    checklist del formulario, así que no lo declara "no confirmable" por el guardado; el PUT con 8
    lo acepta y el PUT con 7 lo rechaza."""
    ChecklistItem.objects.filter(tipo_aventura_id=tipo_publicado, orden__gte=7).delete()
    respuesta = _analizar(cliente_editora, T.TIPO, tipo_publicado)
    assert respuesta.status_code == 200, respuesta.content
    cuerpo = respuesta.json()
    conforme("AnalisisPublicacion", cuerpo)
    assert cuerpo["operacion"] == "ACTUALIZAR_PUBLICACION"
    assert cuerpo["confirmable"] is True
    assert cuerpo["entidad"]["pendientes"] == []
    assert (
        _put(cliente_editora, T.TIPO, tipo_publicado, {"checklist": _checklist(7)}).status_code
        == 422
    )
    assert (
        _put(cliente_editora, T.TIPO, tipo_publicado, {"checklist": _checklist(8)}).status_code
        == 200
    )


def test_TKT051_15_analisis_de_un_borrador_sigue_validando_el_guardado(
    fondo: dict[str, Any], cliente_editora: Client
) -> None:
    """PUBLICAR no recibe datos: el estado resultante ES el guardado, que se sigue validando."""
    borrador = publicos.tipo("Borrador TKT051", estado="BORRADOR")
    respuesta = _analizar(cliente_editora, T.TIPO, borrador.pk)
    assert respuesta.status_code == 200, respuesta.content
    cuerpo = respuesta.json()
    assert cuerpo["operacion"] == "PUBLICAR"
    assert cuerpo["confirmable"] is False
    assert "checklist_insuficiente" in {e["code"] for e in cuerpo["entidad"]["pendientes"]}
