"""AC-TKT004-06 (NV-02) y AC-TKT004-07 (REQ-OPS002-01, OBS-01, RSK-OPS-012) en apps/core.

- NV-02: ningún error de BD lleva su mensaje (DETAIL con valores de filas) al log.
- OBS-01: la línea de django.request de un 5xx no se emite sin trace_id (la registra
  RegistroPeticionMiddleware con trace_id).
- REQ-OPS002-01: SECURE_PROXY_SSL_HEADER = None; X-Forwarded-Proto de un emisor cualquiera no
  convierte la petición en HTTPS (con SSL_REDIRECT → 301).
- RSK-OPS-012: X-Forwarded-For solo cuenta si REMOTE_ADDR es un proxy de confianza.
"""

from __future__ import annotations

import io
import json
import logging

import psycopg
import pytest
from django.conf import settings
from django.db import IntegrityError
from django.test import Client, RequestFactory, override_settings
from rest_framework import serializers

from apps.core.api.serializers import EntradaEstricta
from apps.core.exceptions import ErrorApi, ParametroInvalido
from apps.core.observabilidad import (
    formateador_json,
    sanear_excepciones_bd,
    traza_sin_datos_bd,
)
from apps.core.parametros import validar_parametros
from apps.core.throttling import LimitePorAmbito, ip_cliente

PII = "persona.secreta-nv02"


def _error_bd_encadenado() -> IntegrityError:
    try:
        try:
            raise psycopg.errors.UniqueViolation(f'duplicate key\nDETAIL:  Key (usuario)=({PII}) already exists.')
        except psycopg.Error as origen:
            raise IntegrityError(str(origen)) from origen
    except IntegrityError as error:
        return error


# ---------------------------------------------------------------------------
# AC-TKT004-06: NV-02
# ---------------------------------------------------------------------------
def test_AC_TKT004_06_traza_de_error_bd_sin_valores():
    traza = traza_sin_datos_bd(_error_bd_encadenado())
    assert PII not in traza
    assert "psycopg.errors.UniqueViolation: [detalle omitido: sqlstate" in traza
    assert "django.db.utils.IntegrityError: [detalle omitido" in traza
    assert "Traceback (most recent call last)" in traza


@pytest.mark.parametrize("forma", ["excepcion", "tupla"])
def test_AC_TKT004_06_procesador_sanea_exc_info_de_bd(forma):
    error = _error_bd_encadenado()
    exc_info = error if forma == "excepcion" else (type(error), error, error.__traceback__)
    evento = sanear_excepciones_bd(None, "error", {"event": "x", "exc_info": exc_info})
    assert "exc_info" not in evento
    assert PII not in evento["exception"]


def test_AC_TKT004_06_procesador_no_toca_otras_excepciones():
    evento = {"event": "x", "exc_info": ValueError("mensaje normal")}
    assert sanear_excepciones_bd(None, "error", dict(evento)) == evento
    assert sanear_excepciones_bd(None, "info", {"event": "sin excepción"}) == {"event": "sin excepción"}


def test_AC_TKT004_06_exc_info_true_dentro_de_un_except(logs_json):
    registro = logging.getLogger("brujula.pruebas")
    try:
        raise _error_bd_encadenado()
    except IntegrityError:
        registro.exception("fallo_con_bd")
    texto = logs_json.texto()
    assert "fallo_con_bd" in texto
    assert PII not in texto


# ---------------------------------------------------------------------------
# AC-TKT004-07: OBS-01
# ---------------------------------------------------------------------------
@pytest.mark.urls("apps.core.tests.urls_prueba")
@pytest.mark.parametrize("ruta", ["/prueba/fallo-drf", "/prueba/django-falla"])
def test_AC_TKT004_07_obs01_toda_linea_de_un_5xx_lleva_trace_id(cliente, logs_json, ruta):
    # django.request no propaga a "django" (propagate=False): se captura aparte.
    flujo = io.StringIO()
    manejador = logging.StreamHandler(flujo)
    manejador.setFormatter(formateador_json())
    registro_django = logging.getLogger("django.request")
    registro_django.addHandler(manejador)
    try:
        respuesta = cliente.get(ruta)
    finally:
        registro_django.removeHandler(manejador)
    assert respuesta.status_code == 500
    lineas_django = [json.loads(linea) for linea in flujo.getvalue().splitlines() if linea.strip()]
    assert all(linea.get("trace_id") == respuesta["X-Trace-Id"] for linea in lineas_django)
    if ruta == "/prueba/fallo-drf":
        # DRF ya respondió 500 y el middleware lo registró: django.request no duplica la línea.
        assert lineas_django == []
    lineas = logs_json() + lineas_django
    assert lineas
    assert all(linea.get("trace_id") == respuesta["X-Trace-Id"] for linea in lineas), lineas
    # No hay una segunda línea de django.request duplicando la del middleware.
    assert sum(1 for linea in lineas if linea.get("event") == "peticion") == 1


# ---------------------------------------------------------------------------
# AC-TKT004-07: REQ-OPS002-01
# ---------------------------------------------------------------------------
def test_AC_TKT004_07_django_no_confia_en_x_forwarded_proto():
    assert settings.SECURE_PROXY_SSL_HEADER is None


@pytest.mark.django_db
def test_AC_TKT004_07_x_forwarded_proto_directo_no_evita_la_redireccion():
    with override_settings(SECURE_SSL_REDIRECT=True):
        cliente = Client(raise_request_exception=False)
        respuesta = cliente.get("/api/v1/panel/auth/csrf", HTTP_X_FORWARDED_PROTO="https")
        assert respuesta.status_code == 301
        assert respuesta["Location"].startswith("https://")
        # Las sondas internas no se redirigen.
        assert cliente.get("/health/live", HTTP_X_FORWARDED_PROTO="https").status_code == 200
        # El esquema https real (fijado por gunicorn en wsgi.url_scheme) sí se respeta.
        assert cliente.get("/api/v1/panel/auth/csrf", secure=True).status_code == 204


# ---------------------------------------------------------------------------
# AC-TKT004-07: RSK-OPS-012 (IP del cliente)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("remota", "reenviada", "proxies", "esperada"),
    [
        ("10.231.45.10", "198.51.100.7", ["10.231.45.10/32"], "198.51.100.7"),
        ("203.0.113.66", "198.51.100.7", ["10.231.45.10/32"], "203.0.113.66"),
        ("no-es-ip", "198.51.100.7", ["10.231.45.0/24"], "no-es-ip"),
        ("10.0.0.2", "6.6.6.6, 198.51.100.7", [], "198.51.100.7"),
        ("10.0.0.2", "", [], "10.0.0.2"),
        ("10.0.0.2", " , ", [], "10.0.0.2"),
    ],
)
def test_AC_TKT004_07_ip_cliente_solo_desde_proxy_de_confianza(remota, reenviada, proxies, esperada):
    with override_settings(PROXIES_CONFIANZA=proxies):
        assert ip_cliente({"REMOTE_ADDR": remota, "HTTP_X_FORWARDED_FOR": reenviada}) == esperada


def test_AC_TKT004_07_sin_proxies_configurados_num_proxies_cero():
    with override_settings(NUM_PROXIES=0, PROXIES_CONFIANZA=[]):
        assert ip_cliente({"REMOTE_ADDR": "10.0.0.2", "HTTP_X_FORWARDED_FOR": "1.2.3.4"}) == "10.0.0.2"


def test_AC_TKT004_07_throttle_usa_la_ip_de_confianza():
    peticion = RequestFactory().get("/", REMOTE_ADDR="203.0.113.66", HTTP_X_FORWARDED_FOR="1.2.3.4")
    with override_settings(PROXIES_CONFIANZA=["10.231.45.10/32"]):
        assert LimitePorAmbito().get_ident(peticion) == "203.0.113.66"


# ---------------------------------------------------------------------------
# Utilidades de entrada comunes (DEC-AUTO-105/108)
# ---------------------------------------------------------------------------
class _Entrada(EntradaEstricta):
    nombre = serializers.CharField()


def test_entrada_estricta_rechaza_campos_desconocidos():
    with pytest.raises(ErrorApi) as error:
        _Entrada(data={"nombre": "x", "rol": "ADMINISTRADOR"}).is_valid()
    assert error.value.codigo == "campo_no_permitido"
    assert error.value.errors == {"rol": ["Campo no permitido."]}
    assert _Entrada(data={"nombre": "x"}).is_valid()


def test_validar_parametros():
    validar_parametros({"pagina": "1"}, {"pagina"})
    with pytest.raises(ParametroInvalido) as error:
        validar_parametros({"otro": "1"}, {"pagina"})
    assert "otro" in error.value.errors
