"""TKT-045 (2)-(4).

(2) RULE-009 en servidor con el criterio de DEC-AUTO-977: `fecha_ultima_revision` es válida si es
    <= la fecha actual en UTC+14 (no es futura en ninguna zona horaria). Se aplica al guardar
    (400 `validacion`, Problem Details) y al publicar (422, `ErrorRegla.code` `fecha_futura`), y no
    depende de la zona horaria del proceso.
(3) OBS-02 de la QA de TKT-023: el análisis de publicación de un destino con un tipo RETIRADO
    devuelve `confirmable: false` con el mismo error `tipo_retirado` que daría publicar.
(4) OBS-03: el saneado descarta `href` relativos al protocolo ("//host") y elimina el contenido de
    <script>/<style>.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

import pytest
from django.test import Client

from apps.contenido import reglas, services
from apps.contenido.models import Contenido, EstadoEditorial, TipoContenido
from apps.contenido.saneado import sanear_html
from apps.contenido.tests import publicos

T = TipoContenido
E = EstadoEditorial
BASE = "/api/v1/panel/contenidos"
BOGOTA = timezone(timedelta(hours=-5))


def _json(cliente: Client, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
    return getattr(cliente, metodo)(ruta, cuerpo, content_type="application/json")


# ---------------------------------------------------------------------------
# (2) RULE-009 — DEC-AUTO-977
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("instante", "maxima"),
    [
        # 09:59 UTC → 23:59 en UTC+14: el último día admitido sigue siendo el de UTC.
        (datetime(2026, 10, 8, 9, 59, tzinfo=UTC), date(2026, 10, 8)),
        # 10:00 UTC → ya es el 9 en UTC+14 (Kiritimati): el 9 deja de ser "futuro".
        (datetime(2026, 10, 8, 10, 0, tzinfo=UTC), date(2026, 10, 9)),
        # Editor en Bogotá (UTC-5) a las 20:00 del 8: en UTC es el 9 a la 01:00, en UTC+14 el 9.
        (datetime(2026, 10, 8, 20, 0, tzinfo=BOGOTA), date(2026, 10, 9)),
        # Bogotá a las 04:00 del 8: UTC 09:00 del 8, UTC+14 23:00 del 8.
        (datetime(2026, 10, 8, 4, 0, tzinfo=BOGOTA), date(2026, 10, 8)),
    ],
)
def test_AC_TKT045_07_fecha_maxima_es_hoy_en_utc_mas_14(instante: datetime, maxima: date) -> None:
    assert reglas.fecha_maxima_revision(instante) == maxima
    assert not reglas.es_fecha_futura(maxima, instante)
    assert reglas.es_fecha_futura(maxima + timedelta(days=1), instante)
    assert not reglas.es_fecha_futura(None, instante)


def test_AC_TKT045_08_hoy_local_de_un_editor_por_detras_de_utc_nunca_es_futuro(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A las 21:00 en Bogotá (02:00 UTC del día siguiente) la fecha local del editor es "ayer" en
    UTC y "hoy" en Bogotá: ninguna de las dos es futura. Antes, con `date.today()` del proceso, un
    servidor por delante del editor no le afectaba, pero uno por detrás (o un cliente con su fecha
    local) sí discrepaba; con UTC+14 el resultado no depende de la zona del proceso."""
    instante = datetime(2026, 10, 9, 2, 0, tzinfo=UTC)
    monkeypatch.setattr(reglas, "_ahora_utc", lambda: instante)
    hoy_bogota = instante.astimezone(BOGOTA).date()
    assert hoy_bogota == date(2026, 10, 8)
    datos = _destino_valido(fecha_ultima_revision=hoy_bogota)
    assert not [e for e in reglas.validar_destino(datos) if e["campo"] == "fecha_ultima_revision"]
    # Mañana en UTC (10) sigue siendo futuro a las 02:00 UTC (en UTC+14 son las 16:00 del 9).
    futuro = reglas.validar_destino(_destino_valido(fecha_ultima_revision=date(2026, 10, 10)))
    assert any(e["code"] == "fecha_futura" for e in futuro)


def test_AC_TKT045_09_no_depende_de_la_fecha_local_del_proceso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La regla ya no consulta `date.today()` (zona horaria del proceso): aunque el reloj local
    del proceso diga otra cosa, manda el instante UTC."""

    class FechaLocalFalsa(date):
        @classmethod
        def today(cls) -> date:  # pragma: no cover - debe no llamarse
            raise AssertionError("RULE-009 no debe usar date.today()")

    monkeypatch.setattr(reglas, "date", FechaLocalFalsa)
    monkeypatch.setattr(reglas, "_ahora_utc", lambda: datetime(2026, 10, 8, 12, 0, tzinfo=UTC))
    assert reglas._fecha_no_futura(date(2026, 10, 9)) is None
    error = reglas._fecha_no_futura(date(2026, 10, 10))
    assert error is not None
    assert error["code"] == "fecha_futura"


def _destino_valido(**overrides: Any) -> reglas.DatosDestino:
    datos: dict[str, Any] = {
        "resumen": "Resumen",
        "descripcion_experta": "<p>" + "palabra " * 700 + "</p>",
        "tipos_ids": (1,),
        "tipo_principal_id": 1,
        "dificultad": 3,
        "meses_mejor_epoca": (1,),
        "duracion_min_dias": 2,
        "duracion_max_dias": 4,
        "nivel_presupuesto": 2,
        "clima": "Templado",
        "como_llegar": "<p>Bus</p>",
        "seguridad_riesgos": "<p>Riesgos</p>",
        "sostenibilidad": "<p>Sostenible</p>",
        "latitud": 4.5,
        "longitud": -74.1,
        "portada_id": 1,
        "galeria_ids": (1, 2, 3),
        "fecha_ultima_revision": date(2026, 9, 1),
        "seo_descripcion": "SEO",
        "medios_disponibles_en_galeria": 3,
        "relacionados_publicados": 3,
        "seo_descripcion_en_uso": False,
        "pais_id": 1,
        "pais_activo": True,
        "region_activa": True,
    }
    datos.update(overrides)
    return reglas.DatosDestino(**datos)


@pytest.mark.django_db
def test_AC_TKT045_10_guardar_con_fecha_futura_es_400_problem_details(
    cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    manana_en_todas_partes = (reglas.fecha_maxima_revision() + timedelta(days=1)).isoformat()
    creado = _json(
        cliente_editora,
        "post",
        f"{BASE}/guias",
        {"titulo": "Guía futura", "fecha_ultima_revision": manana_en_todas_partes},
    )
    assert creado.status_code == 400, creado.content
    assert creado["Content-Type"] == "application/problem+json"
    cuerpo = creado.json()
    conforme("ProblemaValidacion", cuerpo)
    assert cuerpo["code"] == "validacion"
    assert cuerpo["errors"] == {"fecha_ultima_revision": [reglas.MENSAJE_FECHA_FUTURA]}
    assert not Contenido.objects.filter(titulo="Guía futura").exists()

    # El último día admitido (hoy en UTC+14, que puede ser "mañana" en UTC) sí se guarda.
    valido = _json(
        cliente_editora,
        "post",
        f"{BASE}/guias",
        {
            "titulo": "Guía límite",
            "fecha_ultima_revision": reglas.fecha_maxima_revision().isoformat(),
        },
    )
    assert valido.status_code == 201, valido.content

    # También al actualizar (PUT), en todos los tipos con fecha (aquí un término).
    termino = _json(cliente_editora, "post", f"{BASE}/glosario", {"titulo": "Bivac TKT045"})
    assert termino.status_code == 201, termino.content
    actualizado = _json(
        cliente_editora,
        "put",
        f"{BASE}/glosario/{termino.json()['id']}",
        {
            "titulo": "Bivac TKT045",
            "fecha_ultima_revision": manana_en_todas_partes,
            "version": termino.json()["version"],
        },
    )
    assert actualizado.status_code == 400, actualizado.content
    conforme("ProblemaValidacion", actualizado.json())
    assert "fecha_ultima_revision" in actualizado.json()["errors"]


@pytest.mark.django_db
def test_AC_TKT045_11_pagina_con_fecha_futura_es_400(
    cliente_admin: Client, conforme: Callable[[str, Any], None]
) -> None:
    pagina = publicos.pagina("POLITICA_COOKIES", "Cookies")
    ruta = f"{BASE}/paginas/{pagina.contenido_id}"
    version = cliente_admin.get(ruta).json()["version"]
    respuesta = _json(
        cliente_admin,
        "put",
        ruta,
        {
            "titulo": "Cookies",
            "cuerpo": "<p>Cookies</p>",
            "version_documento": "1.1",
            "vigente_desde": "2026-09-01",
            "fecha_ultima_revision": (
                reglas.fecha_maxima_revision() + timedelta(days=1)
            ).isoformat(),
            "version": version,
        },
    )
    assert respuesta.status_code == 400, respuesta.content
    conforme("ProblemaValidacion", respuesta.json())
    assert "fecha_ultima_revision" in respuesta.json()["errors"]


# ---------------------------------------------------------------------------
# (3) Análisis de publicación con un tipo RETIRADO (OBS-02)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_AC_TKT045_12_analisis_borrador_con_tipo_retirado_no_es_confirmable(
    cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    activo = publicos.tipo("Kayak TKT045")
    retirado = publicos.tipo("Parapente TKT045", estado=E.RETIRADO)
    destino = publicos.destino("Destino con retirado", tipos=[activo, retirado], estado=E.BORRADOR)
    contenido = destino.contenido

    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/destinos/{contenido.pk}/analisis-publicacion",
        {"version": contenido.version},
    )
    assert respuesta.status_code == 200, respuesta.content
    analisis = respuesta.json()
    conforme("AnalisisPublicacion", analisis)
    assert analisis["confirmable"] is False
    assert analisis["entidad"]["cumple"] is False
    error = next(e for e in analisis["entidad"]["pendientes"] if e["code"] == "tipo_retirado")
    assert error["campo"] == "tipos_ids"
    assert [r["id"] for r in error["referencias"]] == [retirado.pk]
    # El tipo retirado no "se publicará también".
    assert retirado.pk not in [c["id"] for c in analisis["copublicacion"]]

    # Coherente con publicar: 422 con el mismo código por entidad.
    publicar = _json(
        cliente_editora,
        "post",
        f"{BASE}/destinos/{contenido.pk}/publicar",
        {"version": contenido.version, "copublicar_tipos": []},
    )
    assert publicar.status_code == 422, publicar.content
    codigos = {e["code"] for ent in publicar.json()["errores_por_entidad"] for e in ent["errores"]}
    assert "tipo_retirado" in codigos


@pytest.mark.django_db
def test_AC_TKT045_13_analisis_actualizacion_con_tipo_retirado_propuesto(editora: Any) -> None:
    activo = publicos.tipo("Rafting TKT045")
    nuevo_borrador = publicos.tipo("Canopy TKT045", estado=E.BORRADOR)
    publicado_extra = publicos.tipo("Ciclismo TKT045")
    retirado = publicos.tipo("Espeleología TKT045", estado=E.RETIRADO)
    destino = publicos.destino("Destino publicado TKT045", tipos=[activo])
    contenido = destino.contenido

    sin_retirado = services.analizar_publicacion(
        T.DESTINO,
        contenido.pk,
        contenido.version,
        [activo.pk, nuevo_borrador.pk, publicado_extra.pk],
        activo.pk,
    )
    assert sin_retirado["operacion"] == "ACTUALIZAR_PUBLICACION"
    assert sin_retirado["entidad"]["pendientes"] == []
    # Solo los tipos en BORRADOR "se publicarán también" (el PUBLICADO no cambia de estado).
    assert [c["id"] for c in sin_retirado["copublicacion"]] == [nuevo_borrador.pk]
    assert sin_retirado["copublicar_tipos"] == [
        {"id": nuevo_borrador.pk, "version": nuevo_borrador.contenido.version}
    ]

    con_retirado = services.analizar_publicacion(
        T.DESTINO, contenido.pk, contenido.version, [activo.pk, retirado.pk], activo.pk
    )
    assert con_retirado["confirmable"] is False
    assert [e["code"] for e in con_retirado["entidad"]["pendientes"]] == ["tipo_retirado"]
    assert con_retirado["copublicacion"] == []


@pytest.mark.django_db
def test_AC_TKT045_14_analisis_actualizacion_sin_propuesta_con_tipo_ya_retirado() -> None:
    """Un destino publicado que conserva un tipo que se retiró (p. ej. por una carrera) tampoco es
    confirmable: actualizarlo daría 422 tipo_retirado."""
    activo = publicos.tipo("Buceo TKT045")
    retirado = publicos.tipo("Surf TKT045", estado=E.RETIRADO)
    destino = publicos.destino("Destino con tipo retirado TKT045", tipos=[activo, retirado])
    analisis = services.analizar_publicacion(
        T.DESTINO, destino.contenido.pk, destino.contenido.version
    )
    assert analisis["confirmable"] is False
    assert [e["code"] for e in analisis["entidad"]["pendientes"]] == ["tipo_retirado"]


# ---------------------------------------------------------------------------
# (4) Saneado (OBS-03)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "href",
    [
        "//evil.example/x",
        "/\\evil.example/x",
        "/\t/evil.example/x",
        "/\n/evil.example",
        "javascript:alert(1)",
        " //evil.example",
        "data:text/html,hola",
    ],
)
def test_AC_TKT045_15_href_fuera_del_sitio_se_descarta(href: str) -> None:
    assert sanear_html(f'<p><a href="{href}">enlace</a></p>') == "<p>enlace</p>"


@pytest.mark.parametrize(
    ("href", "esperado"),
    [
        ("/destinos/sierra", "/destinos/sierra"),
        ("https://example.org/a?b=1", "https://example.org/a?b=1"),
        ("http://example.org", "http://example.org"),
        ("/gu\tias/x", "/guias/x"),
    ],
)
def test_AC_TKT045_16_href_permitidos_se_conservan(href: str, esperado: str) -> None:
    assert (
        sanear_html(f'<a href="{href}">ir</a>')
        == f'<a href="{esperado.replace("&", "&amp;")}" rel="nofollow">ir</a>'
    )


@pytest.mark.parametrize(
    ("entrada", "salida"),
    [
        ("<p>a<script>alert(1)</script>b</p>", "<p>ab</p>"),
        ("<p>a<SCRIPT type='x'>alert('<p>')</SCRIPT>b</p>", "<p>ab</p>"),
        ("<style>p{color:red}</style><p>texto</p>", "<p>texto</p>"),
        ("<p>inicio</p><script>sin cerrar", "<p>inicio</p>"),
        ("<script/><p>tras autocierre</p>", "<p>tras autocierre</p>"),
        ("</style><p>cierre huérfano</p>", "<p>cierre huérfano</p>"),
        ("<div>texto de div</div>", "texto de div"),
    ],
)
def test_AC_TKT045_17_script_y_style_se_eliminan_con_su_contenido(
    entrada: str, salida: str
) -> None:
    assert sanear_html(entrada) == salida


@pytest.mark.django_db
def test_AC_TKT045_18_guardar_html_con_script_y_enlace_externo(cliente_editora: Client) -> None:
    creado = _json(
        cliente_editora,
        "post",
        f"{BASE}/guias",
        {
            "titulo": "Guía saneada TKT045",
            "cuerpo": '<p>Hola<script>robar()</script> <a href="//evil.example">aquí</a></p>',
        },
    )
    assert creado.status_code == 201, creado.content
    cuerpo = creado.json()["cuerpo"]
    assert cuerpo == "<p>Hola aquí</p>"
