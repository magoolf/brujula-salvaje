"""TKT-012 (deuda de cobertura, Skill_Backend §8: endpoints críticos > 95 %): pruebas HTTP reales
(sesión de panel real, Postgres real) del panel editorial que ninguna prueba ejercía
(hallazgo de QA en TKT-006: `panel_selectors.listar_por_tipo` con 0 % real y `panel_views.py` al
55 %).

- Listar/filtrar por tipo (FEAT-033): estado, texto, parámetros inválidos y sin N+1.
- Crear con `Idempotency-Key`, obtener, eliminar borrador (validación de `version`).
- Ciclo editorial completo por HTTP: publicar, análisis, impacto de retiro, retirar, reactivar,
  revisiones (listar, detalle, restaurar).
- Páginas institucionales: listado, detalle, actualización y autorización por rol (vertical:
  solo ACERCA_DE la edita un EDITOR, AC-033).
- Vista previa, ids fuera de rango (404) y acceso sin sesión.

Acceso horizontal: los contenidos del panel son recursos editoriales compartidos (sin
propietario en el contrato ni en el modelo), así que no hay "usuario A sobre recurso de B" que
probar; la autorización por objeto que sí existe es la vertical de las páginas institucionales.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from apps.contenido.api import panel_selectors
from apps.contenido.models import ContenidoTermino, EstadoEditorial, TipoContenido
from apps.contenido.tests import publicos

T = TipoContenido
E = EstadoEditorial
BASE = "/api/v1/panel/contenidos"
AYER = (date.today() - timedelta(days=1)).isoformat()

pytestmark = pytest.mark.django_db


def _json(cliente: Client, metodo: str, ruta: str, cuerpo: Any = None, **extra: Any) -> Any:
    return getattr(cliente, metodo)(ruta, cuerpo, content_type="application/json", **extra)


def _termino_publicable(cliente: Client, titulo: str) -> tuple[int, int]:
    """Crea por HTTP un término en BORRADOR vinculado a un destino publicado (requisito para
    publicarlo, RULE-026). Devuelve (id, version)."""
    creado = _json(
        cliente,
        "post",
        f"{BASE}/glosario",
        {"titulo": titulo, "definicion": "Definición", "fecha_ultima_revision": AYER},
    )
    assert creado.status_code == 201, creado.content
    cuerpo = creado.json()
    destino = publicos.destino(f"Destino que usa {titulo}", tipos=[])
    ContenidoTermino.objects.create(
        contenido=destino.contenido, tipo_contenido=T.DESTINO, termino_id=cuerpo["id"]
    )
    return int(cuerpo["id"]), int(cuerpo["version"])


# ---------------------------------------------------------------------------
# Listar / filtrar (FEAT-033) — panel_selectors.listar_por_tipo
# ---------------------------------------------------------------------------
def test_TKT012_listar_por_tipo_filtra_por_estado_y_texto(cliente_editora: Client) -> None:
    publicos.termino("Escalada en roca", [], estado=E.PUBLICADO)
    publicos.termino("Escalada en hielo", [], estado=E.BORRADOR)
    publicos.termino("Barranco", [], estado=E.PUBLICADO)

    todos = cliente_editora.get(f"{BASE}/glosario")
    assert todos.status_code == 200, todos.content
    assert todos.json()["total"] == 3

    publicados = cliente_editora.get(f"{BASE}/glosario", {"estado": "PUBLICADO"})
    titulos = {r["titulo"] for r in publicados.json()["resultados"]}
    assert titulos == {"Escalada en roca", "Barranco"}
    assert all(r["publicado"] and r["url_publica"] for r in publicados.json()["resultados"])

    por_texto = cliente_editora.get(f"{BASE}/glosario", {"q": "escalada", "estado": "BORRADOR"})
    resultados = por_texto.json()["resultados"]
    assert [r["titulo"] for r in resultados] == ["Escalada en hielo"]
    assert resultados[0]["url_publica"] is None


@pytest.mark.parametrize("consulta", [{"estado": "ARCHIVADO"}, {"orden": "titulo"}])
def test_TKT012_listar_por_tipo_parametro_invalido_es_400(
    cliente_editora: Client, consulta: dict[str, str]
) -> None:
    respuesta = cliente_editora.get(f"{BASE}/destinos", consulta)
    assert respuesta.status_code == 400, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"


def test_TKT012_listar_por_tipo_selector_ordena_y_no_hace_n_mas_1() -> None:
    for i in range(5):
        publicos.termino(f"Término {i}", [], estado=E.PUBLICADO)
    with CaptureQueriesContext(connection) as consultas:
        filas = list(panel_selectors.listar_por_tipo(T.TERMINO))
        _ = [f.actualizado_por for f in filas]
    assert len(consultas) == 1  # select_related(actualizado_por): una sola consulta
    fechas = [f.actualizado_en for f in filas]
    assert fechas == sorted(fechas, reverse=True)
    assert list(panel_selectors.listar_por_tipo(T.TERMINO, estado=E.RETIRADO)) == []


def test_TKT012_listado_http_consultas_constantes(cliente_editora: Client) -> None:
    """El listado paginado no crece en consultas con el número de filas (sin N+1)."""
    publicos.termino("Uno", [], estado=E.PUBLICADO)
    with CaptureQueriesContext(connection) as pocas:
        assert cliente_editora.get(f"{BASE}/glosario").status_code == 200
    for i in range(6):
        publicos.termino(f"Más {i}", [], estado=E.PUBLICADO)
    with CaptureQueriesContext(connection) as muchas:
        assert cliente_editora.get(f"{BASE}/glosario").status_code == 200
    assert len(muchas) == len(pocas)


def test_TKT012_listar_paginas_institucionales(cliente_editora: Client) -> None:
    publicos.pagina("ACERCA_DE", "Acerca de")
    publicos.pagina("AVISO_LEGAL", "Aviso legal")
    respuesta = cliente_editora.get(f"{BASE}/paginas")
    assert respuesta.status_code == 200, respuesta.content
    assert {r["titulo"] for r in respuesta.json()["resultados"]} == {"Acerca de", "Aviso legal"}


# ---------------------------------------------------------------------------
# Crear (idempotente) / obtener / eliminar
# ---------------------------------------------------------------------------
def test_TKT012_crear_con_idempotency_key_repite_la_misma_respuesta(
    cliente_editora: Client,
) -> None:
    cabecera = {"HTTP_IDEMPOTENCY_KEY": str(uuid4())}
    cuerpo = {"titulo": "Vivac", "definicion": "Noche al raso"}
    primera = _json(cliente_editora, "post", f"{BASE}/glosario", cuerpo, **cabecera)
    segunda = _json(cliente_editora, "post", f"{BASE}/glosario", cuerpo, **cabecera)
    assert primera.status_code == segunda.status_code == 201, segunda.content
    assert primera.json()["id"] == segunda.json()["id"]


def test_TKT012_eliminar_borrador_valida_version(cliente_editora: Client) -> None:
    creado = _json(cliente_editora, "post", f"{BASE}/glosario", {"titulo": "Rapel"}).json()
    ruta = f"{BASE}/glosario/{creado['id']}"
    assert cliente_editora.delete(ruta).status_code == 400
    assert cliente_editora.delete(f"{ruta}?version=abc").status_code == 400
    assert cliente_editora.delete(f"{ruta}?version=1").status_code == 204
    assert cliente_editora.get(ruta).status_code == 404


@pytest.mark.parametrize(
    "ruta",
    [
        f"{BASE}/destinos/9223372036854775808",
        f"{BASE}/glosario/0",
        f"{BASE}/glosario/9223372036854775808/revisiones",
        f"{BASE}/glosario/123456789/impacto-retiro",
    ],
)
def test_TKT012_id_fuera_de_rango_o_inexistente_es_404(cliente_editora: Client, ruta: str) -> None:
    respuesta = cliente_editora.get(ruta)
    assert respuesta.status_code == 404, respuesta.content
    assert respuesta.json()["code"] == "no_encontrado"


# ---------------------------------------------------------------------------
# Ciclo editorial completo por HTTP
# ---------------------------------------------------------------------------
def test_TKT012_ciclo_http_publicar_retirar_reactivar_y_revisiones(
    cliente_editora: Client,
) -> None:
    termino_id, version = _termino_publicable(cliente_editora, "Chimenea")
    base = f"{BASE}/glosario/{termino_id}"

    analisis = _json(cliente_editora, "post", f"{base}/analisis-publicacion", {"version": version})
    assert analisis.status_code == 200, analisis.content
    assert analisis.json()["confirmable"] is True

    publicado = _json(cliente_editora, "post", f"{base}/publicar", {"version": version})
    assert publicado.status_code == 200, publicado.content
    cuerpo = publicado.json()
    assert cuerpo["estado_editorial"] == "PUBLICADO"
    assert cuerpo["url_publica"] == "/glosario/chimenea"
    assert cuerpo["entidades"][0]["origen"] == "PRINCIPAL"
    assert cuerpo["afectados"] == []
    version = cuerpo["version"]

    impacto = cliente_editora.get(f"{base}/impacto-retiro")
    assert impacto.status_code == 200, impacto.content
    assert impacto.json()["retirable"] is True

    retirado = _json(
        cliente_editora,
        "post",
        f"{base}/retirar",
        {"version": version, "motivo": "Término en revisión"},
    )
    assert retirado.status_code == 200, retirado.content
    assert retirado.json()["estado_editorial"] == "RETIRADO"
    assert retirado.json()["url_publica"] is None
    version = retirado.json()["version"]

    reactivado = _json(cliente_editora, "post", f"{base}/reactivar", {"version": version})
    assert reactivado.status_code == 200, reactivado.content
    assert reactivado.json()["estado_editorial"] == "BORRADOR"
    assert reactivado.json()["entidades"][0]["origen"] == "PRINCIPAL"

    revisiones = cliente_editora.get(f"{base}/revisiones")
    assert revisiones.status_code == 200, revisiones.content
    motivos = [r["motivo"] for r in revisiones.json()["resultados"]]
    assert "PUBLICACION" in motivos and "RETIRO" in motivos
    numero = next(
        r["numero_revision"]
        for r in revisiones.json()["resultados"]
        if r["motivo"] == "PUBLICACION"
    )

    detalle = cliente_editora.get(f"{base}/revisiones/{numero}")
    assert detalle.status_code == 200, detalle.content
    assert detalle.json()["instantanea"]["titulo"] == "Chimenea"
    assert detalle.json()["creado_por"]["id"] is not None

    restaurada = _json(cliente_editora, "post", f"{base}/revisiones/{numero}/restaurar")
    assert restaurada.status_code == 200, restaurada.content
    assert restaurada.json()["numero_revision"] == numero
    assert "estado_editorial" not in restaurada.json()["datos"]


def test_TKT012_publicar_sin_requisitos_es_422_y_revision_inexistente_404(
    cliente_editora: Client,
) -> None:
    creado = _json(cliente_editora, "post", f"{BASE}/glosario", {"titulo": "Cornisa"}).json()
    base = f"{BASE}/glosario/{creado['id']}"
    respuesta = _json(cliente_editora, "post", f"{base}/publicar", {"version": 1})
    assert respuesta.status_code == 422, respuesta.content
    assert respuesta.json()["code"] == "publicacion_invalida"
    assert cliente_editora.get(f"{base}/revisiones/99").status_code == 404


def test_TKT012_retirar_con_motivo_con_nul_es_400(cliente_editora: Client) -> None:
    termino_id, _version = _termino_publicable(cliente_editora, "Sendero")
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/glosario/{termino_id}/retirar",
        {"version": 1, "motivo": "con\x00nul"},
    )
    assert respuesta.status_code == 400, respuesta.content


# ---------------------------------------------------------------------------
# Páginas institucionales: detalle, actualización y rol (AC-033)
# ---------------------------------------------------------------------------
def _datos_pagina(version: int) -> dict[str, Any]:
    return {
        "titulo": "Política de datos",
        "cuerpo": "<p>Tratamos tus datos con cuidado.</p>",
        "version_documento": "1.1",
        "vigente_desde": AYER,
        "version": version,
    }


def test_TKT012_pagina_no_acerca_de_solo_la_edita_un_administrador(
    cliente_editora: Client, cliente_admin: Client
) -> None:
    pagina = publicos.pagina("POLITICA_DATOS", "Política de datos")
    ruta = f"{BASE}/paginas/{pagina.contenido_id}"

    obtenida = cliente_editora.get(ruta)
    assert obtenida.status_code == 200, obtenida.content
    assert obtenida.json()["solo_administrador"] is True
    version = obtenida.json()["version"]

    denegada = _json(cliente_editora, "put", ruta, _datos_pagina(version))
    assert denegada.status_code == 403, denegada.content
    assert denegada.json()["code"] == "permiso_denegado"

    permitida = _json(cliente_admin, "put", ruta, _datos_pagina(version))
    assert permitida.status_code == 200, permitida.content
    assert permitida.json()["version_documento"] == "1.1"


def test_TKT012_pagina_acerca_de_la_edita_un_editor(cliente_editora: Client) -> None:
    pagina = publicos.pagina("ACERCA_DE", "Acerca de")
    ruta = f"{BASE}/paginas/{pagina.contenido_id}"
    version = cliente_editora.get(ruta).json()["version"]
    datos = _datos_pagina(version) | {"titulo": "Quiénes somos"}
    respuesta = _json(cliente_editora, "put", ruta, datos)
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["titulo"] == "Quiénes somos"


# ---------------------------------------------------------------------------
# Vista previa y validación de forma del contrato
# ---------------------------------------------------------------------------
def test_TKT012_vista_previa_termino_no_existe_y_pagina_si(cliente_editora: Client) -> None:
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/paginas/vista-previa",
        {"titulo": "Borrador de página", "cuerpo": "<p>Hola</p>"},
    )
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["forma"] == "PaginaInstitucionalPublica"
    assert respuesta.json()["marca"] == "VISTA PREVIA – NO PUBLICADO"


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("terminos_ids", [1, 1]),
        ("galeria_ids", [5, 5]),
        ("meses_mejor_epoca", [3, 3]),
        ("fuentes", [{"titulo": "Fuente", "url": "ftp://ejemplo.org/x"}]),
        ("titulo", "con\x00nul"),
    ],
)
def test_TKT012_restricciones_del_contrato_se_aplican_en_la_entrada(
    cliente_editora: Client, campo: str, valor: Any
) -> None:
    """El contrato manda (TKT-012): uniqueItems, URL http(s) en fuentes y texto sin NUL se
    VALIDAN (400), no solo se documentan en el esquema generado."""
    cuerpo = {"titulo": "Destino de validación", campo: valor}
    respuesta = _json(cliente_editora, "post", f"{BASE}/destinos", cuerpo)
    assert respuesta.status_code == 400, respuesta.content
    assert any(clave.startswith(campo) for clave in respuesta.json()["errors"])


def test_TKT012_fuente_con_url_https_se_acepta(cliente_editora: Client) -> None:
    cuerpo = {
        "titulo": "Destino con fuente",
        "fuentes": [{"titulo": "Parques Nacionales", "url": "https://example.org/parque"}],
    }
    respuesta = _json(cliente_editora, "post", f"{BASE}/destinos", cuerpo)
    assert respuesta.status_code == 201, respuesta.content
    assert respuesta.json()["fuentes"][0]["url"] == "https://example.org/parque"


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("get", f"{BASE}/destinos"),
        ("post", f"{BASE}/glosario/1/publicar"),
        ("post", f"{BASE}/glosario/1/retirar"),
        ("get", f"{BASE}/glosario/1/revisiones"),
        ("post", f"{BASE}/glosario/1/revisiones/1/restaurar"),
    ],
)
def test_TKT012_sin_sesion_de_panel_no_autoriza(metodo: str, ruta: str) -> None:
    respuesta = _json(Client(raise_request_exception=False), metodo, ruta, {})
    assert respuesta.status_code in {401, 403}, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
