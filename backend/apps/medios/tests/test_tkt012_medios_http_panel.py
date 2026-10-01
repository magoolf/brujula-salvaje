"""TKT-012 (deuda de cobertura, Skill_Backend §8): listado/filtros, detalle, catalogación,
archivo, retiro y reactivación del panel de medios por HTTP real, y el selector
`apps.medios.selectors_panel.listar_panel` con su conteo de consultas (N+1).

Los medios son recursos editoriales compartidos (sin propietario): no hay acceso horizontal
entre editores que probar; la autenticación está cubierta en `test_tkt012_medios_ramas.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from apps.catalogos.models import Licencia
from apps.contenido.tests import publicos
from apps.medios import selectors_panel, services
from apps.medios.models import EstadoMedio, Medio

pytestmark = pytest.mark.django_db

BASE = "/api/v1/panel/medios"


def _ids(respuesta: Any) -> set[int]:
    assert respuesta.status_code == 200, respuesta.content
    return {m["id"] for m in respuesta.json()["resultados"]}


@pytest.fixture
def medios() -> dict[str, Medio]:
    licencia = Licencia.objects.create(
        codigo="TKT012-FILTRO",
        nombre="Licencia de filtro",
        requiere_atribucion=False,
        compatible_publicacion=True,
        activo=True,
    )
    en_uso = publicos.medio(texto_alternativo="Cascada helada al amanecer", licencia=licencia)
    publicos.destino("Destino con portada filtrada", tipos=[], portada=en_uso)
    return {
        "en_uso": en_uso,
        "libre": publicos.medio(autor_credito="Fotógrafa Nómada"),
        "pendiente": publicos.medio(estado=EstadoMedio.PENDIENTE_METADATOS),
        "retirado": publicos.medio(estado=EstadoMedio.RETIRADO),
    }


# ---------------------------------------------------------------------------
# Listado con filtros (HTTP) y selector
# ---------------------------------------------------------------------------
def test_TKT012_listar_medios_filtra_por_estado_licencia_texto_y_uso(
    cliente_editora: Client, medios: dict[str, Medio]
) -> None:
    pendientes = _ids(cliente_editora.get(BASE, {"estado": EstadoMedio.PENDIENTE_METADATOS}))
    assert medios["pendiente"].pk in pendientes
    assert medios["libre"].pk not in pendientes

    assert _ids(cliente_editora.get(BASE, {"licencia": "TKT012-FILTRO"})) == {medios["en_uso"].pk}
    assert _ids(cliente_editora.get(BASE, {"q": "cascada helada"})) == {medios["en_uso"].pk}
    assert medios["libre"].pk in _ids(cliente_editora.get(BASE, {"q": "nómada"}))

    usados = _ids(cliente_editora.get(BASE, {"en_uso": "true"}))
    sin_uso = _ids(cliente_editora.get(BASE, {"en_uso": "false"}))
    assert medios["en_uso"].pk in usados
    assert medios["en_uso"].pk not in sin_uso
    assert medios["libre"].pk in sin_uso


@pytest.mark.parametrize(
    ("parametros", "campo"),
    [({"estado": "BORRADO"}, "estado"), ({"en_uso": "quizas"}, "en_uso")],
)
def test_TKT012_listar_medios_parametro_invalido_es_400(
    cliente_editora: Client, parametros: dict[str, str], campo: str
) -> None:
    respuesta = cliente_editora.get(BASE, parametros)
    assert respuesta.status_code == 400, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
    assert campo in respuesta.json()["errors"]


def test_TKT012_selector_listar_panel_consultas_constantes(medios: dict[str, Medio]) -> None:
    """select_related(licencia) + prefetch_related(derivados): 2 consultas sin importar el número
    de medios ni el filtro aplicado."""
    for filtros in (
        {},
        {"estado": EstadoMedio.DISPONIBLE, "en_uso": True},
        {"licencia": "TKT012-FILTRO", "texto": "cascada"},
    ):
        with CaptureQueriesContext(connection) as consultas:
            filas = list(selectors_panel.listar_panel(**filtros))  # type: ignore[arg-type]
            for medio in filas:
                _ = medio.licencia
                _ = list(medio.derivados.all())
        assert filas
        assert len(consultas) == 2, [c["sql"] for c in consultas]


# ---------------------------------------------------------------------------
# Detalle y catalogación
# ---------------------------------------------------------------------------
def test_TKT012_obtener_y_catalogar_medio(
    cliente_editora: Client, medios: dict[str, Medio]
) -> None:
    medio = medios["libre"]
    respuesta = cliente_editora.get(f"{BASE}/{medio.pk}")
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["id"] == medio.pk

    respuesta = cliente_editora.put(
        f"{BASE}/{medio.pk}",
        {"texto_alternativo": "Lago glaciar entre montañas", "fuente_url": "https://example.org"},
        content_type="application/json",
    )
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["texto_alternativo"] == "Lago glaciar entre montañas"
    medio.refresh_from_db()
    assert medio.texto_alternativo == "Lago glaciar entre montañas"


def test_TKT012_catalogar_con_fuente_no_http_es_400(
    cliente_editora: Client, medios: dict[str, Medio]
) -> None:
    respuesta = cliente_editora.put(
        f"{BASE}/{medios['libre'].pk}",
        {"fuente_url": "javascript:alert(1)"},
        content_type="application/json",
    )
    assert respuesta.status_code == 400, respuesta.content
    assert "fuente_url" in respuesta.json()["errors"]


def test_TKT012_id_fuera_del_rango_bigint_es_404(cliente_editora: Client) -> None:
    respuesta = cliente_editora.get(f"{BASE}/{2**63}")
    assert respuesta.status_code == 404, respuesta.content
    assert respuesta.json()["code"] == "no_encontrado"


# ---------------------------------------------------------------------------
# Archivo de un derivado
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "parametros",
    [{"formato": "JPEG"}, {"ancho": "abc", "formato": "JPEG"}, {"ancho": "800", "formato": "GIF"}],
)
def test_TKT012_archivo_con_parametros_invalidos_es_400(
    cliente_editora: Client, medios: dict[str, Medio], parametros: dict[str, str]
) -> None:
    respuesta = cliente_editora.get(f"{BASE}/{medios['libre'].pk}/archivo", parametros)
    assert respuesta.status_code == 400, respuesta.content


def test_TKT012_archivo_sin_derivado_o_sin_fichero_es_404(
    cliente_editora: Client, medios: dict[str, Medio]
) -> None:
    medio = medios["libre"]
    sin_derivado = cliente_editora.get(
        f"{BASE}/{medio.pk}/archivo", {"ancho": "333", "formato": "JPEG"}
    )
    assert sin_derivado.status_code == 404, sin_derivado.content

    # El derivado existe en BD, pero su fichero no está en disco: 404, nunca 500.
    derivado = medio.derivados.get(formato="AVIF")
    assert not (Path(settings.MEDIA_ROOT) / services.RAIZ_PUBLICA / derivado.ruta).exists()
    sin_fichero = cliente_editora.get(
        f"{BASE}/{medio.pk}/archivo", {"ancho": str(derivado.ancho_px), "formato": "AVIF"}
    )
    assert sin_fichero.status_code == 404, sin_fichero.content


def test_TKT012_archivo_existente_se_sirve_sin_cache(
    cliente_editora: Client, medios: dict[str, Medio], tmp_path: Path, settings: Any
) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    medio = medios["pendiente"]  # no DISPONIBLE: su derivado vive en privado/
    derivado = medio.derivados.get(formato="WEBP")
    ruta = tmp_path / services.RAIZ_PRIVADA / derivado.ruta
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(b"RIFF-webp-de-prueba")

    respuesta = cliente_editora.get(
        f"{BASE}/{medio.pk}/archivo", {"ancho": str(derivado.ancho_px), "formato": "WEBP"}
    )

    assert respuesta.status_code == 200
    assert respuesta.content == b"RIFF-webp-de-prueba"
    assert respuesta["Content-Type"] == "image/webp"
    assert respuesta["Cache-Control"] == "no-store"
    assert respuesta["X-Content-Type-Options"] == "nosniff"


# ---------------------------------------------------------------------------
# Retiro y reactivación
# ---------------------------------------------------------------------------
def test_TKT012_retirar_y_reactivar_medio_sin_uso(
    cliente_editora: Client, medios: dict[str, Medio], tmp_path: Path, settings: Any
) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    medio = medios["libre"]

    retirado = cliente_editora.post(f"{BASE}/{medio.pk}/retirar")
    assert retirado.status_code == 200, retirado.content
    assert retirado.json()["estado"] == EstadoMedio.RETIRADO

    reactivado = cliente_editora.post(f"{BASE}/{medio.pk}/reactivar")
    assert reactivado.status_code == 200, reactivado.content
    assert reactivado.json()["estado"] == EstadoMedio.PENDIENTE_METADATOS


def test_TKT012_retirar_medio_en_uso_publicado_es_409(
    cliente_editora: Client, medios: dict[str, Medio]
) -> None:
    respuesta = cliente_editora.post(f"{BASE}/{medios['en_uso'].pk}/retirar")
    assert respuesta.status_code == 409, respuesta.content
    assert respuesta.json()["total_usos"] == 1
    assert Medio.objects.get(pk=medios["en_uso"].pk).estado == EstadoMedio.DISPONIBLE


def test_TKT012_reactivar_medio_no_retirado_es_transicion_invalida(
    cliente_editora: Client, medios: dict[str, Medio]
) -> None:
    respuesta = cliente_editora.post(f"{BASE}/{medios['libre'].pk}/reactivar")
    assert respuesta.status_code == 409, respuesta.content
    assert respuesta.json()["code"] == "transicion_invalida"
