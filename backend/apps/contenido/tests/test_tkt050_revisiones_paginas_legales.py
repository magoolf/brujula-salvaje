"""TKT-050 (QA TKT-045 F-QA045-01): control de acceso por objeto en las revisiones de páginas.

Las páginas institucionales legales (AVISO_LEGAL, POLITICA_COOKIES, POLITICA_DATOS) solo las edita
un Administrador: su PUT ya respondía 403 `permiso_denegado` a un Editor (AC-033), pero la lista y
el detalle de revisiones y `POST .../revisiones/{n}/restaurar` respondían 200 (y el restaurar dejaba
un evento de auditoría RESTAURAR_REVISION). Ahora las tres operaciones aplican la misma
autorización que el PUT. Sin cambios para el Administrador, para ACERCA_DE ni para los demás tipos.

Contrato: `panelListarRevisiones`, `panelObtenerRevision` y `panelRestaurarRevision` declaran
`'403': PermisoDenegado` (Problem Details RFC 9457, Skill_Backend §12.1).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.test import Client

from apps.auditoria.models import (
    AccionAuditoria,
    EventoAuditoria,
    MotivoRevision,
)
from apps.contenido import services
from apps.contenido.models import Contenido, TipoContenido
from apps.contenido.tests import publicos

Respuesta = Any  # respuesta del cliente de pruebas de Django

T = TipoContenido
BASE = "/api/v1/panel/contenidos"
LEGALES = ["AVISO_LEGAL", "POLITICA_COOKIES", "POLITICA_DATOS"]
TITULOS = {
    "AVISO_LEGAL": "Aviso legal",
    "POLITICA_COOKIES": "Política de cookies",
    "POLITICA_DATOS": "Política de datos",
    "ACERCA_DE": "Acerca de",
}
OPERACIONES = ["lista", "detalle", "restaurar"]

pytestmark = pytest.mark.django_db


def _con_revision(contenido: Contenido) -> int:
    """Revisión real (mismo punto de creación que publicar/actualizar/retirar)."""
    return services._crear_revision(contenido, MotivoRevision.ACTUALIZACION, None).numero_revision


def _pagina(clave: str) -> tuple[int, int]:
    pagina = publicos.pagina(clave, TITULOS[clave])
    return pagina.contenido_id, _con_revision(pagina.contenido)


def _operar(cliente: Client, operacion: str, ruta: str, numero: int) -> Respuesta:
    if operacion == "lista":
        return cliente.get(f"{ruta}/revisiones")
    if operacion == "detalle":
        return cliente.get(f"{ruta}/revisiones/{numero}")
    return cliente.post(f"{ruta}/revisiones/{numero}/restaurar", content_type="application/json")


def _restauraciones(contenido_id: int) -> int:
    return EventoAuditoria.objects.filter(
        accion=AccionAuditoria.RESTAURAR_REVISION, entidad_id=contenido_id
    ).count()


def _comprobar_exito(respuesta: Respuesta, operacion: str, numero: int) -> None:
    assert respuesta.status_code == 200, respuesta.content
    cuerpo = respuesta.json()
    if operacion == "lista":
        assert [r["numero_revision"] for r in cuerpo["resultados"]] == [numero]
    else:
        assert cuerpo["numero_revision"] == numero


def _comprobar_403(respuesta: Respuesta, conforme: Callable[[str, Any], None]) -> None:
    assert respuesta.status_code == 403, respuesta.content
    assert respuesta["Content-Type"].startswith("application/problem+json")
    cuerpo = respuesta.json()
    conforme("Problem", cuerpo)
    assert cuerpo["code"] == "permiso_denegado"
    assert cuerpo["status"] == 403
    assert cuerpo["trace_id"]
    assert respuesta["X-Trace-Id"] == cuerpo["trace_id"]


# ---------------------------------------------------------------------------
# Editor: páginas legales → 403 en las tres operaciones, sin auditoría de restauración
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("operacion", OPERACIONES)
@pytest.mark.parametrize("clave", LEGALES)
def test_AC_TKT050_01_editor_pagina_legal_es_403(
    cliente_editora: Client, conforme: Callable[[str, Any], None], clave: str, operacion: str
) -> None:
    contenido_id, numero = _pagina(clave)
    ruta = f"{BASE}/paginas/{contenido_id}"

    respuesta = _operar(cliente_editora, operacion, ruta, numero)

    _comprobar_403(respuesta, conforme)
    assert _restauraciones(contenido_id) == 0


@pytest.mark.parametrize("clave", LEGALES)
def test_AC_TKT050_02_editor_restaurar_legal_no_audita_ni_altera(
    cliente_editora: Client, clave: str
) -> None:
    contenido_id, numero = _pagina(clave)
    ruta = f"{BASE}/paginas/{contenido_id}"
    eventos_antes = EventoAuditoria.objects.count()
    version_antes = Contenido.objects.get(pk=contenido_id).version

    for _ in range(3):
        respuesta = _operar(cliente_editora, "restaurar", ruta, numero)
        assert respuesta.status_code == 403, respuesta.content

    assert _restauraciones(contenido_id) == 0
    assert not EventoAuditoria.objects.filter(accion=AccionAuditoria.RESTAURAR_REVISION).exists()
    assert EventoAuditoria.objects.count() == eventos_antes
    assert Contenido.objects.get(pk=contenido_id).version == version_antes


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_AC_TKT050_03_editor_legal_revision_inexistente_es_403_sin_enumerar(
    cliente_editora: Client, conforme: Callable[[str, Any], None], operacion: str
) -> None:
    """El 403 precede a la búsqueda de la revisión: el Editor no distingue revisiones existentes
    de inexistentes en una página que no puede consultar."""
    contenido_id, _numero = _pagina("POLITICA_DATOS")
    ruta = f"{BASE}/paginas/{contenido_id}"
    _comprobar_403(_operar(cliente_editora, operacion, ruta, 999), conforme)
    assert _restauraciones(contenido_id) == 0


@pytest.mark.parametrize("operacion", OPERACIONES)
@pytest.mark.parametrize("cliente", ["cliente_editora", "cliente_admin"])
def test_AC_TKT050_04_pagina_inexistente_sigue_siendo_404(
    request: pytest.FixtureRequest, cliente: str, operacion: str
) -> None:
    """Igual que el PUT: el 404 del contenido inexistente se mantiene antes que el 403."""
    respuesta = _operar(request.getfixturevalue(cliente), operacion, f"{BASE}/paginas/999999", 1)
    assert respuesta.status_code == 404, respuesta.content
    assert respuesta.json()["code"] == "no_encontrado"


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_AC_TKT050_05_id_de_otro_tipo_bajo_paginas_es_404(
    cliente_editora: Client, operacion: str
) -> None:
    """Un id que existe pero no es una página no se autoriza como página: 404 como antes."""
    termino = publicos.termino("Vivac TKT050", []).contenido
    numero = _con_revision(termino)
    respuesta = _operar(cliente_editora, operacion, f"{BASE}/paginas/{termino.pk}", numero)
    assert respuesta.status_code == 404, respuesta.content


# ---------------------------------------------------------------------------
# Sin cambios: Administrador (todas las páginas), Editor en ACERCA_DE y en otros tipos
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("operacion", OPERACIONES)
@pytest.mark.parametrize("clave", [*LEGALES, "ACERCA_DE"])
def test_AC_TKT050_06_administrador_conserva_acceso(
    cliente_admin: Client, clave: str, operacion: str
) -> None:
    contenido_id, numero = _pagina(clave)
    ruta = f"{BASE}/paginas/{contenido_id}"

    _comprobar_exito(_operar(cliente_admin, operacion, ruta, numero), operacion, numero)
    assert _restauraciones(contenido_id) == (1 if operacion == "restaurar" else 0)


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_AC_TKT050_07_editor_conserva_acceso_a_acerca_de(
    cliente_editora: Client, operacion: str
) -> None:
    contenido_id, numero = _pagina("ACERCA_DE")
    ruta = f"{BASE}/paginas/{contenido_id}"

    _comprobar_exito(_operar(cliente_editora, operacion, ruta, numero), operacion, numero)
    assert _restauraciones(contenido_id) == (1 if operacion == "restaurar" else 0)


@pytest.mark.parametrize("operacion", OPERACIONES)
@pytest.mark.parametrize("cliente", ["cliente_editora", "cliente_admin"])
def test_AC_TKT050_08_otros_tipos_sin_cambios(
    request: pytest.FixtureRequest, cliente: str, operacion: str
) -> None:
    destino = publicos.destino("Destino TKT050", tipos=[publicos.tipo("Senderismo TKT050")])
    termino = publicos.termino("Cordada TKT050", []).contenido
    for contenido, ruta_tipo in ((destino.contenido, "destinos"), (termino, "glosario")):
        numero = _con_revision(contenido)
        ruta = f"{BASE}/{ruta_tipo}/{contenido.pk}"
        respuesta = _operar(request.getfixturevalue(cliente), operacion, ruta, numero)
        _comprobar_exito(respuesta, operacion, numero)
        assert _restauraciones(contenido.pk) == (1 if operacion == "restaurar" else 0)


def test_AC_TKT050_09_put_y_revisiones_coinciden_por_rol_y_pagina(
    cliente_editora: Client, cliente_admin: Client
) -> None:
    """Matriz de coherencia: para cada página y rol, las tres operaciones de revisiones devuelven
    el mismo resultado de autorización que el PUT de la página (403 ⇔ 403)."""
    for clave in [*LEGALES, "ACERCA_DE"]:
        contenido_id, numero = _pagina(clave)
        ruta = f"{BASE}/paginas/{contenido_id}"
        for cliente in (cliente_editora, cliente_admin):
            version = cliente.get(ruta).json()["version"]
            put = cliente.put(
                ruta,
                {
                    "titulo": TITULOS[clave],
                    "cuerpo": f"<p>{clave}</p>",
                    "version_documento": "1.0",
                    "vigente_desde": "2026-01-01",
                    "version": version + 100,  # versión obsoleta: 409 si autoriza, sin escribir
                },
                content_type="application/json",
            )
            denegado = put.status_code == 403
            for operacion in OPERACIONES:
                respuesta = _operar(cliente, operacion, ruta, numero)
                contexto = (clave, operacion, put.status_code)
                assert (respuesta.status_code == 403) is denegado, contexto
