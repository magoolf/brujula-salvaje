"""TKT-012 (deuda de cobertura, Skill_Backend §8: services > 90 %): ramas de
`apps.catalogos.services` que ninguna prueba ejercía.

- RULE-007: desactivar (PUT `activo=false`) una región, un país, una categoría de guía o una
  licencia en uso por contenido PUBLICADO se rechaza con `dependencia_bloqueante` y la lista de
  usos; sin uso publicado (o con el contenido en borrador) se desactiva y se audita.
- `NoEncontrado` al actualizar un id inexistente y `Duplicado` al chocar con una UNIQUE.
"""

from __future__ import annotations

import pytest

from apps.auditoria.models import AccionAuditoria, EventoAuditoria
from apps.catalogos import services
from apps.catalogos.models import CategoriaGuia, Continente, Licencia, Pais, Region
from apps.contenido.models import EstadoEditorial
from apps.contenido.tests import publicos
from apps.contenido.tests.fabricas import crear_cuenta
from apps.core.exceptions import NoEncontrado

pytestmark = pytest.mark.django_db

NO_EXISTE = 987_654_321


@pytest.fixture
def actor() -> int:
    return crear_cuenta("editora.tkt012.catalogos").pk


def _region(slug: str) -> Region:
    return Region.objects.create(
        nombre=f"Región {slug}", slug=slug, continente=Continente.AMERICA, orden=99
    )


def _licencia(codigo: str) -> Licencia:
    return Licencia.objects.create(
        codigo=codigo,
        nombre=f"Licencia {codigo}",
        requiere_atribucion=False,
        compatible_publicacion=True,
        activo=True,
    )


def _auditorias(tipo_entidad: str, entidad_id: int) -> int:
    return EventoAuditoria.objects.filter(
        accion=AccionAuditoria.TAXONOMIA, tipo_entidad=tipo_entidad, entidad_id=entidad_id
    ).count()


# ---------------------------------------------------------------------------
# RULE-007: desactivar con uso publicado -> dependencia_bloqueante
# ---------------------------------------------------------------------------
def test_TKT012_region_con_pais_en_uso_publicado_no_se_desactiva(actor: int) -> None:
    region = _region("tkt012-region-en-uso")
    pais = publicos.pais(region=region)
    destino = publicos.destino("Destino de la región", tipos=[], pais_=pais)

    with pytest.raises(services.DependenciaBloqueante) as error:
        services.actualizar_region(region.pk, actor, {"activo": False})

    assert error.value.extra["total_usos"] == 1
    assert error.value.extra["usos"] == [
        {
            "tipo_entidad": "DESTINO",
            "id": destino.contenido_id,
            "titulo": "Destino de la región",
            "estado_editorial": EstadoEditorial.PUBLICADO,
        }
    ]
    region.refresh_from_db()
    assert region.activo is True


def test_TKT012_region_sin_uso_publicado_se_desactiva_y_audita(actor: int) -> None:
    region = _region("tkt012-region-libre")
    pais = publicos.pais(region=region)
    publicos.destino("Destino en borrador", tipos=[], pais_=pais, estado=EstadoEditorial.BORRADOR)

    guardada = services.actualizar_region(region.pk, actor, {"activo": False})

    assert guardada.activo is False
    assert _auditorias("REGION", region.pk) == 1


def test_TKT012_pais_en_uso_publicado_no_se_desactiva(actor: int) -> None:
    pais = publicos.pais()
    publicos.destino("Destino del país", tipos=[], pais_=pais)

    with pytest.raises(services.DependenciaBloqueante) as error:
        services.actualizar_pais(pais.pk, actor, {"activo": False})

    assert error.value.extra["total_usos"] == 1
    assert Pais.objects.get(pk=pais.pk).activo is True


def test_TKT012_categoria_en_uso_publicado_no_se_desactiva(actor: int) -> None:
    categoria = CategoriaGuia.objects.create(
        nombre="Categoría TKT-012", slug="categoria-tkt012", descripcion="Descripción", orden=99
    )
    guia = publicos.guia("Guía de la categoría", categoria_=categoria)

    with pytest.raises(services.DependenciaBloqueante) as error:
        services.actualizar_categoria(categoria.pk, actor, {"activo": False})

    assert error.value.extra["usos"][0]["tipo_entidad"] == "GUIA"
    assert error.value.extra["usos"][0]["id"] == guia.contenido_id
    assert CategoriaGuia.objects.get(pk=categoria.pk).activo is True


def test_TKT012_categoria_sin_uso_se_desactiva(actor: int) -> None:
    categoria = CategoriaGuia.objects.create(
        nombre="Categoría libre", slug="categoria-libre-tkt012", descripcion="Sin uso", orden=98
    )
    guardada = services.actualizar_categoria(categoria.pk, actor, {"activo": False})
    assert guardada.activo is False
    assert _auditorias("CATEGORIA_GUIA", categoria.pk) == 1


def test_TKT012_licencia_de_medio_en_uso_publicado_no_se_desactiva(actor: int) -> None:
    licencia = _licencia("TKT012-EN-USO")
    portada = publicos.medio(licencia=licencia)
    publicos.destino("Destino con portada licenciada", tipos=[], portada=portada)

    with pytest.raises(services.DependenciaBloqueante) as error:
        services.actualizar_licencia(licencia.pk, actor, {"activo": False})

    assert error.value.extra["usos"] == [
        {
            "tipo_entidad": "MEDIO",
            "id": portada.pk,
            "titulo": f"Medio #{portada.pk}",
            "estado_editorial": None,
        }
    ]
    assert Licencia.objects.get(pk=licencia.pk).activo is True


def test_TKT012_licencia_de_medio_sin_uso_publicado_se_desactiva(actor: int) -> None:
    licencia = _licencia("TKT012-SIN-USO")
    publicos.medio(licencia=licencia)  # medio con la licencia, pero sin uso publicado

    guardada = services.actualizar_licencia(licencia.pk, actor, {"activo": False})

    assert guardada.activo is False
    assert _auditorias("LICENCIA", licencia.pk) == 1


# ---------------------------------------------------------------------------
# NoEncontrado / Duplicado
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "actualizar",
    [
        services.actualizar_region,
        services.actualizar_pais,
        services.actualizar_categoria,
        services.actualizar_licencia,
    ],
)
def test_TKT012_actualizar_inexistente_es_no_encontrado(actor: int, actualizar: object) -> None:
    with pytest.raises(NoEncontrado):
        actualizar(NO_EXISTE, actor, {"activo": True})  # type: ignore[operator]


def test_TKT012_crear_region_con_slug_repetido_es_duplicado(actor: int) -> None:
    existente = _region("tkt012-region-repetida")
    with pytest.raises(services.Duplicado):
        services.crear_region(
            actor,
            {
                "nombre": "Otro nombre",
                "slug": existente.slug,
                "continente": Continente.EUROPA,
                "orden": 1,
            },
        )
    assert Region.objects.filter(slug=existente.slug).count() == 1
