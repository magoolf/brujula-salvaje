"""AC-TKT003-06: semilla de catálogos idempotente y reversible (migración catalogos.0002)."""

from __future__ import annotations

import importlib
from contextlib import contextmanager

import pytest
from django.apps import apps
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.catalogos.models import CategoriaGuia, Licencia, NivelEscala, Pais, Region

pytestmark = pytest.mark.django_db

semilla = importlib.import_module("apps.catalogos.migrations.0002_semilla")


@contextmanager
def _falla(excepcion=IntegrityError):
    with pytest.raises(excepcion), transaction.atomic():
        yield


def _recuentos() -> dict[str, int]:
    return {
        "regiones": Region.objects.count(),
        "categorias": CategoriaGuia.objects.count(),
        "licencias": Licencia.objects.count(),
        "niveles": NivelEscala.objects.count(),
    }


def test_AC_TKT003_06_la_migracion_siembra_los_catalogos():
    assert _recuentos() == {"regiones": 7, "categorias": 8, "licencias": 5, "niveles": 9}
    assert set(Region.objects.values_list("continente", flat=True)) == {
        "AMERICA",
        "EUROPA",
        "AFRICA",
        "ASIA",
        "OCEANIA",
    }
    assert NivelEscala.objects.filter(escala="DIFICULTAD").count() == 5
    assert NivelEscala.objects.filter(escala="PRESUPUESTO").count() == 4
    assert Licencia.objects.filter(compatible_publicacion=True).count() == 5
    assert Pais.objects.count() == 0  # los países llegan con la carga semilla (TKT-007)


def test_AC_TKT003_06_semilla_idempotente():
    antes = _recuentos()
    semilla.sembrar(apps, None)
    semilla.sembrar(apps, None)
    assert _recuentos() == antes


def test_AC_TKT003_06_semilla_no_pisa_ediciones_del_administrador():
    Region.objects.filter(slug="europa").update(orden=99)
    semilla.sembrar(apps, None)
    assert Region.objects.get(slug="europa").orden == 99


def test_AC_TKT003_06_semilla_reversible_por_clave_natural():
    extra = Licencia.objects.create(
        codigo="OTRA-1.0", nombre="Otra", requiere_atribucion=False, compatible_publicacion=False
    )
    semilla.retirar_semilla(apps, None)
    assert _recuentos() == {"regiones": 0, "categorias": 0, "licencias": 1, "niveles": 0}
    assert Licencia.objects.get() == extra  # solo borra lo que sembró
    semilla.sembrar(apps, None)
    assert _recuentos() == {"regiones": 7, "categorias": 8, "licencias": 6, "niveles": 9}


def test_AC_TKT003_04_catalogos_rechazan_valores_fuera_de_dominio():
    region = Region.objects.get(slug="asia")
    pais = Pais.objects.create(nombre="Nepal", slug="nepal", codigo_iso2="NP", region=region)
    assert str(pais) == "Nepal" and str(region) == "Asia"
    assert str(Licencia.objects.get(codigo="CC0-1.0")) == "CC0-1.0"
    assert str(CategoriaGuia.objects.get(orden=1)) == "Preparación física"
    assert str(NivelEscala.objects.get(escala="DIFICULTAD", nivel=3)) == "DIFICULTAD 3"
    with _falla():
        Pais.objects.create(nombre="X", slug="x", codigo_iso2="np", region=region)
    with _falla():
        Region.objects.create(nombre="Luna", slug="luna", continente="LUNA")
    with _falla():
        NivelEscala.objects.create(escala="PRESUPUESTO", nivel=5, etiqueta="x", descripcion="x")
    with _falla():
        NivelEscala.objects.create(escala="DIFICULTAD", nivel=1, etiqueta="x", descripcion="x")
    with _falla():
        Licencia.objects.create(
            codigo="cc minúscula", nombre="x", requiere_atribucion=True,
            compatible_publicacion=True,
        )
    with _falla():
        Licencia.objects.create(
            codigo="URL-MALA", nombre="x", url_texto_legal="ftp://x", requiere_atribucion=True,
            compatible_publicacion=True,
        )
    with _falla():
        CategoriaGuia.objects.create(nombre="Otra", slug="Otra Categoria", descripcion="x")
    with _falla(ProtectedError):  # PROTECT: una región con países no se borra
        Region.objects.filter(pk=region.pk).delete()
