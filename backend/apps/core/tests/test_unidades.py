"""Pruebas unitarias de la infraestructura de core."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, override_settings
from rest_framework import exceptions as drf

from apps.core import trazas
from apps.core.exceptions import ErrorApi, manejador_excepciones, normalizar_errores
from apps.core.middleware import seudonimo_usuario
from apps.core.problemas import CATALOGO, cuerpo_problema
from apps.core.throttling import LimitePorAmbito, huella_hmac, truncar_ip
from config.settings import _env

# ---------------------------------------------------------------------------
# Variables de entorno
# ---------------------------------------------------------------------------


def test_env_texto_obligatorio_y_defecto(monkeypatch):
    monkeypatch.delenv("VAR_PRUEBA", raising=False)
    with pytest.raises(ImproperlyConfigured):
        _env.texto("VAR_PRUEBA")
    assert _env.texto("VAR_PRUEBA", "d") == "d"
    monkeypatch.setenv("VAR_PRUEBA", "  valor ")
    assert _env.texto("VAR_PRUEBA") == "valor"


@pytest.mark.parametrize(("valor", "esperado"), [("true", True), ("OFF", False), ("", True)])
def test_env_booleano(monkeypatch, valor, esperado):
    monkeypatch.setenv("VAR_PRUEBA", valor)
    assert _env.booleano("VAR_PRUEBA", True) is esperado


def test_env_booleano_invalido(monkeypatch):
    monkeypatch.setenv("VAR_PRUEBA", "quizas")
    with pytest.raises(ImproperlyConfigured):
        _env.booleano("VAR_PRUEBA", False)


def test_env_entero_y_lista(monkeypatch):
    monkeypatch.setenv("VAR_PRUEBA", "42")
    assert _env.entero("VAR_PRUEBA", 1) == 42
    monkeypatch.setenv("VAR_PRUEBA", "x")
    with pytest.raises(ImproperlyConfigured):
        _env.entero("VAR_PRUEBA", 1)
    monkeypatch.delenv("VAR_PRUEBA")
    assert _env.entero("VAR_PRUEBA", 7) == 7
    monkeypatch.setenv("VAR_PRUEBA", " a, ,b ")
    assert _env.lista("VAR_PRUEBA") == ["a", "b"]


# ---------------------------------------------------------------------------
# Trazas
# ---------------------------------------------------------------------------


def test_trace_id_actual_fuera_de_peticion_genera_uno():
    assert len(trazas.trace_id_actual()) == 32


def test_trace_id_otel_sin_span_es_none():
    assert trazas.trace_id_otel() is None


def test_nuevo_trace_id_nunca_nulo(monkeypatch):
    valores = iter(["0" * 32, "a" * 32])
    monkeypatch.setattr(trazas.secrets, "token_hex", lambda _n: next(valores))
    assert trazas.nuevo_trace_id() == "a" * 32


# ---------------------------------------------------------------------------
# Problemas y excepciones
# ---------------------------------------------------------------------------


def test_catalogo_codes_validos_y_status_coherente():
    import re

    for codigo, (estado, titulo, detalle) in CATALOGO.items():
        assert re.fullmatch(r"^[a-z][a-z0-9_]{2,63}$", codigo)
        assert 400 <= estado <= 599
        assert titulo and len(titulo) <= 200 and detalle


@override_settings(PROBLEM_TYPE_BASE_URL="https://ejemplo.test/")
def test_cuerpo_problema_base_configurable():
    cuerpo = cuerpo_problema("no_encontrado", detalle="x", extra={"status": 1, "alternativas": []})
    assert cuerpo["type"] == "https://ejemplo.test/errors/no_encontrado"
    assert cuerpo["status"] == 404 and cuerpo["alternativas"] == []


def test_error_api_rechaza_code_fuera_de_catalogo():
    with pytest.raises(ValueError, match="catálogo"):
        ErrorApi(codigo="inventado")


def test_normalizar_errores_anidados():
    detalle = {
        "non_field_errors": ["general"],
        "dias": [{"titulo": ["largo"]}, {}],
        "fuentes": {"non_field_errors": ["mal"], "url": ["http"]},
        "etiquetas": ["uno", {"x": ["y"]}],
    }
    assert normalizar_errores(detalle) == {
        "_general": ["general"],
        "dias.0.titulo": ["largo"],
        "fuentes": ["mal"],
        "fuentes.url": ["http"],
        "etiquetas": ["uno"],
        "etiquetas.1.x": ["y"],
    }
    assert normalizar_errores("solo texto") == {"_general": ["solo texto"]}


@pytest.mark.parametrize(
    ("excepcion", "codigo"),
    [
        (drf.NotAuthenticated(), "no_autenticado"),
        (drf.AuthenticationFailed(), "no_autenticado"),
        (drf.NotFound(), "no_encontrado"),
        (drf.NotAcceptable(), "error_interno"),
        (drf.Throttled(wait=None), "limite_tasa"),
    ],
)
def test_manejador_traduce_excepciones_drf(excepcion, codigo):
    respuesta = manejador_excepciones(excepcion, {})
    assert respuesta.data["code"] == codigo
    assert "Retry-After" not in respuesta


def test_manejador_status_desconocido_cae_en_error_interno():
    class Rara(drf.APIException):
        status_code = 418

    assert manejador_excepciones(Rara(), {}).data["code"] == "error_interno"


# ---------------------------------------------------------------------------
# Limitación de tasa y seudónimos
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ip", "red"),
    [
        ("203.0.113.77", "203.0.113.0/24"),
        ("2001:db8:abcd:12::1", "2001:db8:abcd::/48"),
        ("no-es-ip", "desconocida"),
        (None, "desconocida"),
    ],
)
def test_truncar_ip(ip, red):
    assert truncar_ip(ip) == red


def test_clave_de_limite_sin_ip_en_claro_y_agrupada_por_red():
    limite = LimitePorAmbito()
    limite.scope = "publico-lectura"
    vista = SimpleNamespace()

    def peticion(ip):
        return RequestFactory().get("/", HTTP_X_FORWARDED_FOR=ip, REMOTE_ADDR="10.0.0.2")

    clave = limite.get_cache_key(peticion("203.0.113.77"), vista)
    # NUM_PROXIES=1: se usa la última IP de X-Forwarded-For (la que fija el proxy).
    assert clave == limite.get_cache_key(peticion("6.6.6.6, 203.0.113.9"), vista)
    assert "203.0.113" not in clave and clave.startswith("limite:publico-lectura:")
    assert clave == limite.get_cache_key(peticion("203.0.113.5"), vista)
    assert clave != limite.get_cache_key(peticion("203.0.114.5"), vista)


def test_clave_de_limite_por_cuenta_autenticada():
    limite = LimitePorAmbito()
    limite.scope = "panel-escritura"
    usuario = SimpleNamespace(is_authenticated=True, pk=7)
    clave = limite.get_cache_key(SimpleNamespace(user=usuario, META={}), SimpleNamespace())
    assert clave == f"limite:panel-escritura:{huella_hmac('panel-escritura|cuenta:7')}"


def test_seudonimo_usuario():
    assert seudonimo_usuario(SimpleNamespace()) is None
    usuario = SimpleNamespace(is_authenticated=True, pk=7)
    seudonimo = seudonimo_usuario(SimpleNamespace(user=usuario))
    assert seudonimo and len(seudonimo) == 16 and "7" != seudonimo


# ---------------------------------------------------------------------------
# Cabeceras, paginación y permisos por defecto
# ---------------------------------------------------------------------------


def test_cabeceras_de_seguridad_en_respuestas_api(cliente):
    respuesta = cliente.get("/health/live")
    assert "frame-ancestors 'none'" in respuesta["Content-Security-Policy"]
    assert respuesta["X-Content-Type-Options"] == "nosniff"
    assert respuesta["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert respuesta["X-Frame-Options"] == "DENY"
    assert "camera=()" in respuesta["Permissions-Policy"]


def test_cabeceras_del_panel_no_store_y_noindex(cliente):
    respuesta = cliente.get("/api/v1/panel/cualquier-cosa")
    assert respuesta.status_code == 404
    assert respuesta["Cache-Control"] == "no-store"
    assert respuesta["X-Robots-Tag"] == "noindex, nofollow"


@pytest.mark.urls("apps.core.tests.urls_prueba")
def test_paginacion_envoltorio_y_enlaces_relativos(cliente):
    primera = cliente.get("/prueba/paginada?orden=a").json()
    assert primera["total"] == 30 and primera["total_paginas"] == 2
    assert primera["tamano_pagina"] == 24 and len(primera["resultados"]) == 24
    assert primera["anterior"] is None
    assert primera["siguiente"] == "/prueba/paginada?orden=a&pagina=2"
    segunda = cliente.get(primera["siguiente"]).json()
    assert segunda["resultados"] == list(range(24, 30))
    assert segunda["siguiente"] is None
    assert segunda["anterior"] == "/prueba/paginada?orden=a&pagina=1"


@pytest.mark.urls("apps.core.tests.urls_prueba")
@pytest.mark.parametrize(
    ("pagina", "status", "code"),
    [
        ("3", 404, "pagina_fuera_de_rango"),
        ("0", 400, "parametro_invalido"),
        ("x", 400, "parametro_invalido"),
    ],
)
def test_paginacion_errores(cliente, pagina, status, code):
    respuesta = cliente.get(f"/prueba/paginada?pagina={pagina}")
    assert respuesta.status_code == status
    assert respuesta.json()["code"] == code


def test_paginacion_sin_ejecutar_falla():
    from apps.core.paginacion import PaginacionNumerada

    paginacion = PaginacionNumerada()
    with pytest.raises(RuntimeError):
        paginacion.get_paginated_response([])
    with pytest.raises(RuntimeError):
        paginacion._enlace(1)
    assert "resultados" in paginacion.get_paginated_response_schema({"type": "array"})["properties"]


# ---------------------------------------------------------------------------
# OpenTelemetry (desactivable)
# ---------------------------------------------------------------------------


def test_otel_desactivado_no_instrumenta():
    from apps.core.observabilidad import configurar_otel

    assert configurar_otel() is False


def test_otel_activo_propaga_traza_y_no_guarda_query(monkeypatch):
    # OBS-QA004-07: el propio SDK de OpenTelemetry lee OTEL_SDK_DISABLED del entorno (con "true"
    # crea un proveedor no-op); la prueba no debe depender del entorno en que se ejecuta.
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    from django.test import Client
    from opentelemetry import trace
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from apps.core.observabilidad import configurar_otel

    exportador = InMemorySpanExporter()
    with override_settings(OTEL_SDK_DISABLED=False, OTEL_EXPORTER_OTLP_ENDPOINT=""):
        try:
            assert configurar_otel() is True
            trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exportador))
            respuesta = Client().get(
                "/health/live?q=secreto",
                HTTP_TRACEPARENT="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            )
        finally:
            DjangoInstrumentor().uninstrument()
            PsycopgInstrumentor().uninstrument()
    assert respuesta["X-Trace-Id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    spans = exportador.get_finished_spans()
    assert spans
    for span in spans:
        assert "secreto" not in str(dict(span.attributes or {}))
