"""AC-TKT006: alta y edición de taxonomías (FEAT-044, RULE-007, RULE-012, RULE-014)."""

from __future__ import annotations

import pytest

from apps.catalogos import services
from apps.catalogos.models import CategoriaGuia, Continente, Licencia, NivelEscala, Pais, Region
from apps.contenido.tests.fabricas import crear_cuenta

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor() -> int:
    return crear_cuenta("editora.catalogos").pk


def test_AC_TKT006_04_crear_y_actualizar_region(actor: int) -> None:
    region = services.crear_region(
        actor,
        {
            "nombre": "Región de prueba",
            "slug": "region-de-prueba",
            "continente": Continente.AMERICA,
            "orden": 1,
            "activo": True,
        },
    )
    assert region.pk is not None
    actualizada = services.actualizar_region(
        region.pk,
        actor,
        {
            "nombre": "Región renombrada",
            "slug": "region-de-prueba",
            "continente": Continente.AMERICA,
            "orden": 2,
            "activo": True,
        },
    )
    assert actualizada.nombre == "Región renombrada"
    assert actualizada.orden == 2


def test_AC_TKT006_04_region_duplicada(actor: int) -> None:
    services.crear_region(
        actor,
        {
            "nombre": "Única",
            "slug": "unica-region",
            "continente": Continente.EUROPA,
            "orden": 1,
            "activo": True,
        },
    )
    with pytest.raises(services.Duplicado):
        services.crear_region(
            actor,
            {
                "nombre": "Otra",
                "slug": "unica-region",
                "continente": Continente.EUROPA,
                "orden": 2,
                "activo": True,
            },
        )


def test_AC_TKT006_04_desactivar_pais_en_uso_bloqueado(actor: int) -> None:
    from apps.contenido.tests import publicos

    region = Region.objects.first()
    pais = Pais.objects.create(
        nombre="País en uso", slug="pais-en-uso", codigo_iso2="ZZ", region=region
    )
    publicos.destino("Destino con país en uso", tipos=[], pais_=pais)

    with pytest.raises(services.DependenciaBloqueante) as exc:
        services.actualizar_pais(
            pais.pk,
            actor,
            {
                "nombre": pais.nombre,
                "slug": pais.slug,
                "codigo_iso2": pais.codigo_iso2,
                "region_id": region.pk,
                "activo": False,
            },
        )
    assert exc.value.extra["usos"]
    pais.refresh_from_db()
    assert pais.activo is True


def test_AC_TKT006_04_desactivar_pais_sin_uso_funciona(actor: int) -> None:
    region = Region.objects.first()
    pais = Pais.objects.create(
        nombre="País libre", slug="pais-libre", codigo_iso2="YY", region=region
    )
    actualizado = services.actualizar_pais(
        pais.pk,
        actor,
        {
            "nombre": pais.nombre,
            "slug": pais.slug,
            "codigo_iso2": pais.codigo_iso2,
            "region_id": region.pk,
            "activo": False,
        },
    )
    assert actualizado.activo is False


def test_AC_TKT006_04_categoria_guia_en_uso_bloqueada(actor: int) -> None:
    from apps.contenido.tests import publicos

    categoria = CategoriaGuia.objects.create(
        nombre="Categoría en uso", slug="categoria-en-uso", descripcion="Descripción", orden=1
    )
    publicos.guia("Guía que usa la categoría", categoria_=categoria)

    with pytest.raises(services.DependenciaBloqueante):
        services.actualizar_categoria(
            categoria.pk,
            actor,
            {
                "nombre": categoria.nombre,
                "slug": categoria.slug,
                "descripcion": categoria.descripcion,
                "orden": categoria.orden,
                "activo": False,
            },
        )


def test_AC_TKT006_04_crear_licencia(actor: int) -> None:
    licencia = services.crear_licencia(
        actor,
        {
            "codigo": "CC-TEST",
            "nombre": "Licencia de prueba",
            "requiere_atribucion": True,
            "compatible_publicacion": True,
            "activo": True,
        },
    )
    assert Licencia.objects.filter(pk=licencia.pk).exists()


def test_AC_TKT006_04_actualizar_nivel_escala(actor: int) -> None:
    nivel = NivelEscala.objects.first()
    assert nivel is not None
    actualizado = services.actualizar_nivel_escala(
        nivel.pk, actor, {"etiqueta": "Etiqueta nueva", "descripcion": "Descripción nueva"}
    )
    assert actualizado.etiqueta == "Etiqueta nueva"
