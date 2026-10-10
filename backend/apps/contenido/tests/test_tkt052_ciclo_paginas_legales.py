"""TKT-052 (QA TKT-050 OBS-QA050-02): control de acceso por objeto en el ciclo de las páginas.

Las páginas institucionales legales (AVISO_LEGAL, POLITICA_COOKIES, POLITICA_DATOS) solo las
gestiona un Administrador (AC-033): su PUT y, desde TKT-050, sus revisiones responden 403
`permiso_denegado` a un Editor. Las operaciones de ciclo con `tipo=paginas` no aplicaban esa
autorización: un Editor obtenía en una página legal `GET impacto-retiro` 200 con `retirable: true`
(las páginas no se retiran), `publicar`/`reactivar` 409 y `retirar` 400/409, y podía publicar una
página legal en BORRADOR. Ahora `publicar`, `analisis-publicacion`, `impacto-retiro`, `retirar` y
`reactivar` aplican la misma autorización que el PUT, con el mismo orden que TKT-050: 400 de formato
del cuerpo → 404 del contenido inexistente → 403, y el 403 precede a la idempotencia y a cualquier
efecto o auditoría. `impacto-retiro` de una PAGINA devuelve `retirable: false` para todos los roles.
Sin cambios para el Administrador, para ACERCA_DE ni para los demás tipos.

Contrato: las cinco operaciones declaran `'403': PermisoDenegado` (Problem Details RFC 9457,
Skill_Backend §12.1); el cuerpo 200 de impacto-retiro cumple `ImpactoRetiro`.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection
from django.test import Client

from apps.auditoria.models import EventoAuditoria, RevisionContenido
from apps.contenido.models import Contenido, EstadoEditorial, TipoContenido
from apps.contenido.tests import publicos

Respuesta = Any  # respuesta del cliente de pruebas de Django

T = TipoContenido
E = EstadoEditorial
BASE = "/api/v1/panel/contenidos"
LEGALES = ["AVISO_LEGAL", "POLITICA_COOKIES", "POLITICA_DATOS"]
TITULOS = {
    "AVISO_LEGAL": "Aviso legal",
    "POLITICA_COOKIES": "Política de cookies",
    "POLITICA_DATOS": "Política de datos",
    "ACERCA_DE": "Acerca de",
}
OPERACIONES = ["publicar", "analisis", "impacto", "retirar", "reactivar"]
OPERACIONES_IDEMPOTENTES = ["publicar", "retirar", "reactivar"]
# Estado de partida más exigente por operación. Una PAGINA nunca está RETIRADA (constraint de BD,
# AC-033), así que `reactivar` parte de PUBLICADO.
ESTADO_FAVORABLE = {
    "publicar": E.BORRADOR,
    "analisis": E.BORRADOR,
    "impacto": E.PUBLICADO,
    "retirar": E.PUBLICADO,
    "reactivar": E.PUBLICADO,
}

pytestmark = pytest.mark.django_db


def _pagina(clave: str, estado: str = E.PUBLICADO) -> Contenido:
    return publicos.pagina(clave, TITULOS[clave], estado).contenido


def _operar(
    cliente: Client,
    operacion: str,
    ruta: str,
    version: int,
    *,
    clave_idempotencia: str | None = None,
    cuerpo: dict[str, Any] | None = None,
) -> Respuesta:
    if operacion == "impacto":
        return cliente.get(f"{ruta}/impacto-retiro")
    extra: dict[str, str] = {}
    if clave_idempotencia is not None:
        extra["HTTP_IDEMPOTENCY_KEY"] = clave_idempotencia
    if cuerpo is None:
        cuerpo = {"version": version}
        if operacion == "retirar":
            cuerpo["motivo"] = "Retiro TKT-052"
    sufijo = "analisis-publicacion" if operacion == "analisis" else operacion
    return cliente.post(f"{ruta}/{sufijo}", cuerpo, content_type="application/json", **extra)


def _idempotencias() -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM idempotencia_peticion")
        fila = cursor.fetchone()
    assert fila is not None
    return int(fila[0])


def _huella(contenido_id: int) -> tuple[Any, ...]:
    """Estado observable de la página y efectos globales que una operación podría dejar."""
    c = Contenido.objects.get(pk=contenido_id)
    return (
        c.estado_editorial,
        c.version,
        c.slug,
        c.retirado_en,
        c.motivo_retiro,
        EventoAuditoria.objects.count(),
        RevisionContenido.objects.filter(contenido_id=contenido_id).count(),
        _idempotencias(),
    )


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
# Editor: páginas legales → 403 en las cinco operaciones, sin efectos ni auditoría
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("operacion", OPERACIONES)
@pytest.mark.parametrize("clave", LEGALES)
def test_AC_TKT052_01_editor_pagina_legal_es_403_sin_efectos(
    cliente_editora: Client, conforme: Callable[[str, Any], None], clave: str, operacion: str
) -> None:
    contenido = _pagina(clave, ESTADO_FAVORABLE[operacion])
    ruta = f"{BASE}/paginas/{contenido.pk}"
    antes = _huella(contenido.pk)

    respuesta = _operar(cliente_editora, operacion, ruta, contenido.version)

    _comprobar_403(respuesta, conforme)
    assert _huella(contenido.pk) == antes


@pytest.mark.parametrize("operacion", OPERACIONES)
@pytest.mark.parametrize("estado", [E.BORRADOR, E.PUBLICADO])
def test_AC_TKT052_02_editor_legal_403_en_cualquier_estado(
    cliente_editora: Client, conforme: Callable[[str, Any], None], estado: str, operacion: str
) -> None:
    """La autorización no depende del estado editorial (sin oráculo por 409 transicion_invalida)."""
    contenido = _pagina("POLITICA_DATOS", estado)
    ruta = f"{BASE}/paginas/{contenido.pk}"
    antes = _huella(contenido.pk)

    _comprobar_403(_operar(cliente_editora, operacion, ruta, contenido.version), conforme)
    assert _huella(contenido.pk) == antes


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_AC_TKT052_03_editor_legal_version_obsoleta_es_403_no_409(
    cliente_editora: Client, conforme: Callable[[str, Any], None], operacion: str
) -> None:
    """El 403 precede a la comprobación de versión: el Editor no averigua la versión vigente."""
    contenido = _pagina("AVISO_LEGAL", ESTADO_FAVORABLE[operacion])
    ruta = f"{BASE}/paginas/{contenido.pk}"
    _comprobar_403(_operar(cliente_editora, operacion, ruta, contenido.version + 50), conforme)


@pytest.mark.parametrize("operacion", OPERACIONES_IDEMPOTENTES)
def test_AC_TKT052_04_editor_legal_con_idempotency_key_no_reserva_ni_reproduce(
    cliente_editora: Client, conforme: Callable[[str, Any], None], operacion: str
) -> None:
    """El 403 precede a la idempotencia: repetir la misma clave sigue dando 403 y no deja fila."""
    contenido = _pagina("POLITICA_COOKIES", ESTADO_FAVORABLE[operacion])
    ruta = f"{BASE}/paginas/{contenido.pk}"
    antes = _huella(contenido.pk)
    clave = str(uuid.uuid4())

    for _ in range(3):
        respuesta = _operar(
            cliente_editora, operacion, ruta, contenido.version, clave_idempotencia=clave
        )
        _comprobar_403(respuesta, conforme)

    assert _huella(contenido.pk) == antes
    assert _idempotencias() == 0


def test_AC_TKT052_05_editor_no_publica_pagina_legal_en_borrador(
    cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    """Caso con efecto real antes del arreglo: un borrador legal no pasa a PUBLICADO ni audita."""
    contenido = _pagina("AVISO_LEGAL", E.BORRADOR)
    ruta = f"{BASE}/paginas/{contenido.pk}"

    _comprobar_403(_operar(cliente_editora, "publicar", ruta, contenido.version), conforme)

    contenido.refresh_from_db()
    assert contenido.estado_editorial == E.BORRADOR
    assert not EventoAuditoria.objects.filter(entidad_id=contenido.pk).exists()
    assert not RevisionContenido.objects.filter(contenido_id=contenido.pk).exists()


@pytest.mark.parametrize("operacion", ["publicar", "analisis", "retirar", "reactivar"])
def test_AC_TKT052_06_formato_invalido_sigue_siendo_400(
    cliente_editora: Client, operacion: str
) -> None:
    """Orden de evaluación (DEC-AUTO-269, igual que el PUT de TKT-050): 400 de formato primero."""
    contenido = _pagina("AVISO_LEGAL")
    ruta = f"{BASE}/paginas/{contenido.pk}"
    respuesta = _operar(cliente_editora, operacion, ruta, 1, cuerpo={"version": 0})
    assert respuesta.status_code == 400, respuesta.content


# ---------------------------------------------------------------------------
# 404 antes que 403 (igual que el PUT y las revisiones de TKT-050)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("operacion", OPERACIONES)
@pytest.mark.parametrize("cliente", ["cliente_editora", "cliente_admin"])
def test_AC_TKT052_07_pagina_inexistente_es_404(
    request: pytest.FixtureRequest, cliente: str, operacion: str
) -> None:
    respuesta = _operar(request.getfixturevalue(cliente), operacion, f"{BASE}/paginas/999999", 1)
    assert respuesta.status_code == 404, respuesta.content
    assert respuesta.json()["code"] == "no_encontrado"
    assert _idempotencias() == 0


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_AC_TKT052_08_id_de_otro_tipo_bajo_paginas_es_404(
    cliente_editora: Client, operacion: str
) -> None:
    """Un id que existe pero no es una página no se autoriza como página: 404."""
    termino = publicos.termino("Vivac TKT052", []).contenido
    antes = _huella(termino.pk)
    respuesta = _operar(cliente_editora, operacion, f"{BASE}/paginas/{termino.pk}", 1)
    assert respuesta.status_code == 404, respuesta.content
    assert _huella(termino.pk) == antes


# ---------------------------------------------------------------------------
# Autorizados: Administrador (todas) y Editor en ACERCA_DE → las páginas no se retiran (AC-033)
# ---------------------------------------------------------------------------
def _autorizados() -> list[tuple[str, str]]:
    return [("cliente_admin", c) for c in [*LEGALES, "ACERCA_DE"]] + [
        ("cliente_editora", "ACERCA_DE")
    ]


@pytest.mark.parametrize(("cliente", "clave"), _autorizados())
def test_AC_TKT052_09_impacto_retiro_de_pagina_no_es_retirable(
    request: pytest.FixtureRequest, conforme: Callable[[str, Any], None], cliente: str, clave: str
) -> None:
    contenido = _pagina(clave)
    respuesta = request.getfixturevalue(cliente).get(
        f"{BASE}/paginas/{contenido.pk}/impacto-retiro"
    )
    assert respuesta.status_code == 200, respuesta.content
    cuerpo = respuesta.json()
    conforme("ImpactoRetiro", cuerpo)
    assert cuerpo["retirable"] is False


@pytest.mark.parametrize("operacion", ["retirar", "reactivar"])
@pytest.mark.parametrize(("cliente", "clave"), _autorizados())
def test_AC_TKT052_10_autorizado_retirar_reactivar_pagina_es_409_transicion_invalida(
    request: pytest.FixtureRequest, cliente: str, clave: str, operacion: str
) -> None:
    http = request.getfixturevalue(cliente)  # el login audita LOGIN_OK: antes de la huella
    contenido = _pagina(clave, ESTADO_FAVORABLE[operacion])
    ruta = f"{BASE}/paginas/{contenido.pk}"
    antes = _huella(contenido.pk)

    respuesta = _operar(http, operacion, ruta, contenido.version)

    assert respuesta.status_code == 409, respuesta.content
    assert respuesta.json()["code"] == "transicion_invalida"
    assert _huella(contenido.pk) == antes


@pytest.mark.parametrize(("cliente", "clave"), _autorizados())
def test_AC_TKT052_11_autorizado_publicar_y_analizar_sin_403(
    request: pytest.FixtureRequest, cliente: str, clave: str
) -> None:
    """Publicar una página ya publicada sigue siendo 409 transicion_invalida y el análisis 200."""
    contenido = _pagina(clave)
    ruta = f"{BASE}/paginas/{contenido.pk}"
    http = request.getfixturevalue(cliente)

    publicar = _operar(http, "publicar", ruta, contenido.version)
    assert publicar.status_code == 409, publicar.content
    assert publicar.json()["code"] == "transicion_invalida"

    analisis = _operar(http, "analisis", ruta, contenido.version)
    assert analisis.status_code == 200, analisis.content


# ---------------------------------------------------------------------------
# Sin cambios en los demás tipos
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cliente", ["cliente_editora", "cliente_admin"])
def test_AC_TKT052_12_otros_tipos_siguen_siendo_retirables(
    request: pytest.FixtureRequest, conforme: Callable[[str, Any], None], cliente: str
) -> None:
    termino = publicos.termino("Cordada TKT052", []).contenido
    http = request.getfixturevalue(cliente)
    ruta = f"{BASE}/glosario/{termino.pk}"

    impacto = http.get(f"{ruta}/impacto-retiro")
    assert impacto.status_code == 200, impacto.content
    conforme("ImpactoRetiro", impacto.json())
    assert impacto.json()["retirable"] is True

    retirar = _operar(http, "retirar", ruta, termino.version)
    assert retirar.status_code == 200, retirar.content
    assert retirar.json()["estado_editorial"] == E.RETIRADO

    version = Contenido.objects.get(pk=termino.pk).version
    reactivar = _operar(http, "reactivar", ruta, version)
    assert reactivar.status_code == 200, reactivar.content
    assert reactivar.json()["estado_editorial"] == E.BORRADOR


# ---------------------------------------------------------------------------
# Coherencia con el PUT de la página por rol y página
# ---------------------------------------------------------------------------
def test_AC_TKT052_13_put_y_ciclo_coinciden_por_rol_y_pagina(
    cliente_editora: Client, cliente_admin: Client
) -> None:
    """Para cada página y rol, las cinco operaciones de ciclo devuelven el mismo resultado de
    autorización que el PUT de la página (403 ⇔ 403)."""
    for clave in [*LEGALES, "ACERCA_DE"]:
        contenido = _pagina(clave)
        ruta = f"{BASE}/paginas/{contenido.pk}"
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
                respuesta = _operar(cliente, operacion, ruta, version)
                contexto = (clave, operacion, put.status_code, respuesta.status_code)
                assert (respuesta.status_code == 403) is denegado, contexto
