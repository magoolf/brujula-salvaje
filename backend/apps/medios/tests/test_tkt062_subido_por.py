"""TKT-062: `MedioPanel.subido_por` cumple `components.schemas.ActorRef` ("Usuario o seudónimo si
la cuenta está anonimizada; 'sistema' para procesos"); antes era `#<id>`. Sin N+1: el listado
carga las cuentas de toda la página en una consulta.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.contenido.tests import publicos
from apps.contenido.tests.conftest import validar_contra
from apps.contenido.tests.fabricas import crear_cuenta
from apps.cuentas.models import CuentaStaff, EstadoCuenta
from apps.medios.models import Medio

pytestmark = pytest.mark.django_db

RUTA = "/api/v1/panel/medios"


def _anonimizar(cuenta: CuentaStaff) -> None:
    ahora = timezone.now()
    CuentaStaff.objects.filter(pk=cuenta.pk).update(
        usuario=None,
        nombre_visible=None,
        estado=EstadoCuenta.ANONIMIZADA,
        password="!inutilizable",  # nosec B106 (hash inutilizable, no es un secreto)
        desactivado_en=ahora,
        anonimizado_en=ahora,
    )


def test_TKT062_detalle_de_medio_lleva_el_usuario(cliente_editora: Client) -> None:
    autora = crear_cuenta("fotografa.062")
    medio = publicos.medio(subido_por=autora)
    datos = cliente_editora.get(f"{RUTA}/{medio.pk}").json()
    assert validar_contra("MedioPanel", datos) == []
    assert datos["subido_por"] == {"id": autora.pk, "etiqueta": "fotografa.062"}


def test_TKT062_seudonimo_y_sistema(cliente_editora: Client) -> None:
    autora = crear_cuenta("fotografa.anonimizable")
    anonimo = publicos.medio(subido_por=autora)
    semilla = publicos.medio()  # carga semilla: subido_por NULL (DEC-AUTO-095)
    _anonimizar(autora)
    datos = cliente_editora.get(f"{RUTA}/{anonimo.pk}").json()
    assert datos["subido_por"] == {"id": autora.pk, "etiqueta": f"Cuenta anonimizada #{autora.pk}"}
    assert "fotografa" not in str(datos)
    datos = cliente_editora.get(f"{RUTA}/{semilla.pk}").json()
    assert datos["subido_por"] == {"id": None, "etiqueta": "sistema"}


def test_TKT062_listado_lleva_el_usuario(cliente_editora: Client) -> None:
    autora = crear_cuenta("fotografa.lista")
    ids = {publicos.medio(subido_por=autora).pk for _ in range(3)}
    datos = cliente_editora.get(RUTA).json()
    assert validar_contra("PaginaMedioPanel", datos) == []
    filas = [r for r in datos["resultados"] if r["id"] in ids]
    assert len(filas) == 3
    assert {r["subido_por"]["etiqueta"] for r in filas} == {"fotografa.lista"}


def test_TKT062_listado_sin_n_mas_1_por_autor(cliente_editora: Client) -> None:
    """Mismas consultas con 4 medios de 1 autora que con 4 medios de 4 autoras distintas."""
    unica = crear_cuenta("fotografa.unica")
    medios = [publicos.medio(subido_por=unica) for _ in range(4)]
    with CaptureQueriesContext(connection) as una:
        assert cliente_editora.get(RUTA).status_code == 200

    for i, medio in enumerate(medios):
        Medio.objects.filter(pk=medio.pk).update(subido_por=crear_cuenta(f"fotografa.{i}"))
    with CaptureQueriesContext(connection) as varias:
        respuesta = cliente_editora.get(RUTA)
    etiquetas = {r["subido_por"]["etiqueta"] for r in respuesta.json()["resultados"]}
    assert etiquetas == {f"fotografa.{i}" for i in range(4)}
    assert len(varias.captured_queries) == len(una.captured_queries)


def test_TKT062_detalle_carga_la_cuenta_en_una_consulta(cliente_editora: Client) -> None:
    from apps.medios.api.serializers import MedioPanelSerializer

    medio = publicos.medio(subido_por=crear_cuenta("fotografa.una"))
    fresco = Medio.objects.select_related("licencia").get(pk=medio.pk)
    with CaptureQueriesContext(connection) as con_cuenta:
        datos: Any = MedioPanelSerializer(fresco).data
    assert datos["subido_por"]["etiqueta"] == "fotografa.una"
    Medio.objects.filter(pk=medio.pk).update(subido_por=None)
    fresco = Medio.objects.select_related("licencia").get(pk=medio.pk)
    with CaptureQueriesContext(connection) as sin_cuenta:
        MedioPanelSerializer(fresco).data  # noqa: B018 (serializa)
    # La cuenta cuesta exactamente 1 consulta; sin actor, ninguna.
    assert len(con_cuenta.captured_queries) == len(sin_cuenta.captured_queries) + 1
