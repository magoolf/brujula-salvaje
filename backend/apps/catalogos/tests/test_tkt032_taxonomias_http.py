"""TKT-032: taxonomías del panel por HTTP real.

- F1 (AC_TKT032_01): crear o editar un país con una región inexistente era un 500 (la FK
  `pais.region_id` es DEFERRABLE y fallaba en el COMMIT); ahora 400 `validacion` con el campo, sin
  `excepcion_no_controlada` en el log y sin nada pendiente para el COMMIT.
- F4 (AC_TKT032_04): listado, detalle y edición de regiones y países (y las ramas de error de
  categorías y licencias que faltaban) para que `apps/catalogos/api/views.py` supere el 95 %.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.test import Client

from apps.catalogos.models import Continente, Licencia, Pais, Region
from apps.contenido.tests import publicos
from apps.contenido.tests.fabricas import forzar_diferidas

pytestmark = pytest.mark.django_db

BASE = "/api/v1/panel/taxonomias"
NX = 99_999_999
FUERA_DE_RANGO = 2**63


def _json(cliente: Client, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
    return getattr(cliente, metodo)(ruta, cuerpo, content_type="application/json")


def _problema(respuesta: Any, estado: int, codigo: str) -> dict[str, Any]:
    assert respuesta.status_code == estado, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
    cuerpo: dict[str, Any] = respuesta.json()
    assert cuerpo["code"] == codigo
    assert len(cuerpo["trace_id"]) == 32
    return cuerpo


def _region(**cambios: Any) -> dict[str, Any]:
    return {
        "nombre": "Región TKT-032",
        "slug": "region-tkt032",
        "continente": Continente.OCEANIA,
        "orden": 7,
        "activo": True,
    } | cambios


def _pais(region_id: int, **cambios: Any) -> dict[str, Any]:
    return {
        "nombre": "País TKT-032",
        "slug": "pais-tkt032",
        "codigo_iso2": "QX",
        "region_id": region_id,
        "activo": True,
    } | cambios


# ---------------------------------------------------------------------------
# F1 — región inexistente en POST/PUT de país
# ---------------------------------------------------------------------------
def test_AC_TKT032_01_crear_pais_con_region_inexistente_es_400(
    cliente_editora: Client, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    antes = Pais.objects.count()
    respuesta = _json(cliente_editora, "post", f"{BASE}/paises", _pais(NX))
    assert _problema(respuesta, 400, "validacion")["errors"] == {"region_id": ["No existe."]}
    assert Pais.objects.count() == antes
    forzar_diferidas("ALL")  # nada pendiente para el COMMIT (antes: violación de la FK → 500)
    assert not [r for r in logs_json() if r.get("event") == "excepcion_no_controlada"]


def test_AC_TKT032_01_editar_pais_con_region_inexistente_es_400(
    cliente_editora: Client, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    pais = publicos.pais()
    region_original = pais.region_id
    respuesta = _json(
        cliente_editora,
        "put",
        f"{BASE}/paises/{pais.pk}",
        _pais(NX, nombre=pais.nombre, slug=pais.slug, codigo_iso2=pais.codigo_iso2),
    )
    assert _problema(respuesta, 400, "validacion")["errors"] == {"region_id": ["No existe."]}
    pais.refresh_from_db()
    assert pais.region_id == region_original
    forzar_diferidas("ALL")
    assert not [r for r in logs_json() if r.get("event") == "excepcion_no_controlada"]


# ---------------------------------------------------------------------------
# F4 — regiones
# ---------------------------------------------------------------------------
def test_AC_TKT032_04_regiones_listar_obtener_y_actualizar(cliente_editora: Client) -> None:
    lista = cliente_editora.get(f"{BASE}/regiones")
    assert lista.status_code == 200, lista.content
    cuerpo = lista.json()
    assert cuerpo["total"] == Region.objects.count() > 0
    ordenadas = [(r["orden"], r["nombre"]) for r in cuerpo["resultados"]]
    assert ordenadas == sorted(ordenadas)

    creada = _json(cliente_editora, "post", f"{BASE}/regiones", _region())
    assert creada.status_code == 201, creada.content
    ruta = f"{BASE}/regiones/{creada.json()['id']}"

    obtenida = cliente_editora.get(ruta)
    assert obtenida.status_code == 200
    assert obtenida.json() == creada.json()

    actualizada = _json(cliente_editora, "put", ruta, _region(nombre="Región renombrada", orden=9))
    assert actualizada.status_code == 200, actualizada.content
    assert actualizada.json()["nombre"] == "Región renombrada"
    assert Region.objects.get(pk=creada.json()["id"]).orden == 9


def test_AC_TKT032_04_regiones_errores(cliente_editora: Client) -> None:
    _problema(cliente_editora.get(f"{BASE}/regiones", {"orden": "x"}), 400, "parametro_invalido")
    _problema(cliente_editora.get(f"{BASE}/regiones/{NX}"), 404, "no_encontrado")
    _problema(cliente_editora.get(f"{BASE}/regiones/{FUERA_DE_RANGO}"), 404, "no_encontrado")
    _problema(
        _json(cliente_editora, "put", f"{BASE}/regiones/{NX}", _region()), 404, "no_encontrado"
    )
    existente = Region.objects.order_by("id").first()
    assert existente is not None
    duplicada = _json(cliente_editora, "post", f"{BASE}/regiones", _region(nombre=existente.nombre))
    _problema(duplicada, 409, "duplicado")
    invalida = _json(
        cliente_editora,
        "put",
        f"{BASE}/regiones/{existente.pk}",
        _region(continente="MARTE", orden=-1),
    )
    assert {"continente", "orden"} <= set(_problema(invalida, 400, "validacion")["errors"])


# ---------------------------------------------------------------------------
# F4 — países
# ---------------------------------------------------------------------------
def test_AC_TKT032_04_paises_listar_filtrar_obtener_y_actualizar(cliente_editora: Client) -> None:
    region_a, region_b = Region.objects.order_by("id")[:2]
    pais_a = publicos.pais("Aaa país", region=region_a)
    pais_b = publicos.pais("Bbb país", region=region_b)

    todos = cliente_editora.get(f"{BASE}/paises")
    assert todos.status_code == 200, todos.content
    nombres = [p["nombre"] for p in todos.json()["resultados"]]
    assert nombres == sorted(nombres)
    assert {pais_a.pk, pais_b.pk} <= {p["id"] for p in todos.json()["resultados"]}

    filtrados = cliente_editora.get(f"{BASE}/paises", {"region_id": region_b.pk})
    assert filtrados.status_code == 200
    ids = {p["id"] for p in filtrados.json()["resultados"]}
    assert pais_b.pk in ids and pais_a.pk not in ids
    assert all(p["region_id"] == region_b.pk for p in filtrados.json()["resultados"])

    ruta = f"{BASE}/paises/{pais_a.pk}"
    obtenido = cliente_editora.get(ruta)
    assert obtenido.status_code == 200
    assert obtenido.json() == {
        "id": pais_a.pk,
        "nombre": "Aaa país",
        "slug": pais_a.slug,
        "codigo_iso2": pais_a.codigo_iso2,
        "region_id": region_a.pk,
        "activo": True,
    }

    actualizado = _json(
        cliente_editora,
        "put",
        ruta,
        _pais(region_b.pk, nombre="Aaa movido", slug=pais_a.slug, codigo_iso2=pais_a.codigo_iso2),
    )
    assert actualizado.status_code == 200, actualizado.content
    assert actualizado.json()["region_id"] == region_b.pk
    pais_a.refresh_from_db()
    assert (pais_a.nombre, pais_a.region_id) == ("Aaa movido", region_b.pk)


@pytest.mark.parametrize("region_id", ["abc", "-1", "1.5"])
def test_AC_TKT032_04_paises_filtro_region_no_entero_es_400(
    cliente_editora: Client, region_id: str
) -> None:
    respuesta = cliente_editora.get(f"{BASE}/paises", {"region_id": region_id})
    assert "region_id" in _problema(respuesta, 400, "parametro_invalido")["errors"]


def test_AC_TKT032_04_paises_errores(cliente_editora: Client) -> None:
    _problema(cliente_editora.get(f"{BASE}/paises", {"orden": "x"}), 400, "parametro_invalido")
    _problema(cliente_editora.get(f"{BASE}/paises/{NX}"), 404, "no_encontrado")
    region = Region.objects.order_by("id").first()
    assert region is not None
    _problema(
        _json(cliente_editora, "put", f"{BASE}/paises/{NX}", _pais(region.pk)), 404, "no_encontrado"
    )
    existente = publicos.pais()
    duplicado = _json(
        cliente_editora,
        "post",
        f"{BASE}/paises",
        _pais(region.pk, codigo_iso2=existente.codigo_iso2),
    )
    _problema(duplicado, 409, "duplicado")


# ---------------------------------------------------------------------------
# F4 — ramas de error de categorías y licencias que no se ejercían
# ---------------------------------------------------------------------------
def test_AC_TKT032_04_categorias_listar_y_errores(cliente_editora: Client) -> None:
    lista = cliente_editora.get(f"{BASE}/categorias-guia")
    assert lista.status_code == 200
    assert lista.json()["total"] > 0
    _problema(cliente_editora.get(f"{BASE}/categorias-guia/{NX}"), 404, "no_encontrado")
    categoria = lista.json()["resultados"][0]
    actualizada = _json(
        cliente_editora,
        "put",
        f"{BASE}/categorias-guia/{categoria['id']}",
        {**{k: v for k, v in categoria.items() if k != "id"}, "orden": 42},
    )
    assert actualizada.status_code == 200, actualizada.content
    assert actualizada.json()["orden"] == 42


def test_AC_TKT032_04_licencias_solo_administrador_escribe(cliente_editora: Client) -> None:
    licencia = Licencia.objects.order_by("id").first()
    assert licencia is not None
    cuerpo = {
        "codigo": "CC-TKT-032",
        "nombre": "Licencia",
        "url_texto_legal": None,
        "requiere_atribucion": True,
        "compatible_publicacion": True,
        "activo": True,
    }
    _problema(_json(cliente_editora, "post", f"{BASE}/licencias", cuerpo), 403, "permiso_denegado")
    _problema(
        _json(cliente_editora, "put", f"{BASE}/licencias/{licencia.pk}", cuerpo),
        403,
        "permiso_denegado",
    )
    _problema(cliente_editora.get(f"{BASE}/licencias/{NX}"), 404, "no_encontrado")
    assert cliente_editora.get(f"{BASE}/licencias/{licencia.pk}").status_code == 200
