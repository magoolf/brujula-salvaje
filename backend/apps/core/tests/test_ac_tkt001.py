"""Pruebas de aceptación de TKT-001 (AC-TKT001-01..08)."""

from __future__ import annotations

import base64
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from django.conf import settings
from django.core.management import call_command
from django.db import connection

from apps.core import selectors

BACKEND = Path(settings.BASE_DIR)
PATRON_TRACE = re.compile(r"^[0-9a-f]{32}$")
PROBLEMA = "application/problem+json"
CAMPOS_PROBLEMA = {"type", "title", "status", "detail", "code", "errors", "trace_id"}
TRACEPARENT_VALIDO = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


# Clave Fernet bien formada (32 bytes) pero ficticia: prod.py valida su formato.
_FERNET_FICTICIA = base64.urlsafe_b64encode(b"ficticia-fernet-no-real-" + b"0" * 8).decode()


def _entorno_prod(**extra: str) -> dict[str, str]:
    """Variables ficticias de producción (nunca reales) para arrancar config.settings (prod)."""
    entorno = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "DB_"))}
    entorno.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJANGO_SECRET_KEY": "ficticia-" + "a1b2c3d4" * 8,
            "THROTTLE_HMAC_KEY": "ficticia-" + "e5f6a7b8" * 8,
            "MFA_FERNET_KEY": _FERNET_FICTICIA,
            "DB_PASSWORD": "ficticia",
            "DJANGO_SECURE_SSL_REDIRECT": "true",
            "DJANGO_SECURE_HSTS_SECONDS": "31536000",
        }
    )
    entorno.pop("DJANGO_ENV", None)
    entorno.update(extra)
    return entorno


def _manage(*args: str, **extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 (argumentos fijos, sin shell)
        [sys.executable, "manage.py", *args],
        cwd=BACKEND,
        env=_entorno_prod(**extra),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _assert_problema(respuesta, status: int, code: str) -> dict:
    assert respuesta.status_code == status
    assert respuesta["Content-Type"] == PROBLEMA
    cuerpo = respuesta.json()
    assert CAMPOS_PROBLEMA <= set(cuerpo)
    assert cuerpo["status"] == status
    assert cuerpo["code"] == code
    assert cuerpo["type"] == f"https://brujulasalvaje.example/errors/{code}"
    assert PATRON_TRACE.fullmatch(cuerpo["trace_id"])
    assert cuerpo["trace_id"] == respuesta["X-Trace-Id"]
    return cuerpo


def _trace_en_log(logs: list[dict], trace_id: str) -> bool:
    return any(
        linea.get("event") == "peticion" and linea.get("trace_id") == trace_id for linea in logs
    )


# ---------------------------------------------------------------------------
# AC-TKT001-01: check y check --deploy (prod con variables ficticias)
# ---------------------------------------------------------------------------
def test_AC_TKT001_01_check_sin_errores():
    call_command("check", fail_level="WARNING")


def test_AC_TKT001_01_check_deploy_prod_sin_avisos():
    resultado = _manage("check", "--deploy", "--fail-level", "WARNING")
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "no issues" in resultado.stdout


def test_AC_TKT001_01_prod_rechaza_secretos_de_plantilla():
    resultado = _manage("check", DJANGO_SECRET_KEY="CHANGE_ME")
    assert resultado.returncode != 0
    assert "DJANGO_SECRET_KEY" in resultado.stderr


def test_AC_TKT001_01_prod_exige_variables_obligatorias():
    entorno = _entorno_prod()
    entorno.pop("THROTTLE_HMAC_KEY")
    resultado = subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert resultado.returncode != 0
    assert "THROTTLE_HMAC_KEY" in resultado.stderr


def test_AC_TKT001_01_django_env_dev_selecciona_settings_de_desarrollo():
    resultado = _manage(
        "shell", "-c", "from django.conf import settings; print(settings.DEBUG)", DJANGO_ENV="dev"
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip().splitlines()[-1] == "True"


def test_AC_TKT001_01_django_env_invalido_falla():
    resultado = _manage("check", DJANGO_ENV="staging")
    assert resultado.returncode != 0
    assert "DJANGO_ENV" in resultado.stderr


# ---------------------------------------------------------------------------
# AC-TKT001-02: /health/live sin BD; /health/ready 200 con BD y 503 sin BD
# ---------------------------------------------------------------------------
def test_AC_TKT001_02_live_200_sin_tocar_bd(cliente):
    # Sin marca django_db: cualquier acceso a la BD haría fallar la prueba.
    respuesta = cliente.get("/health/live")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}
    assert respuesta["Cache-Control"] == "no-store"
    assert PATRON_TRACE.fullmatch(respuesta["X-Trace-Id"])
    assert "Set-Cookie" not in respuesta


@pytest.mark.django_db
def test_AC_TKT001_02_ready_200_con_bd(cliente):
    respuesta = cliente.get("/health/ready")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


@pytest.mark.django_db(transaction=True)
def test_AC_TKT001_02_ready_503_si_la_bd_no_responde(cliente, logs_json):
    puerto_original = connection.settings_dict["PORT"]
    connection.close()
    connection.settings_dict["PORT"] = "1"  # nadie escucha: conexión rechazada
    try:
        respuesta = cliente.get("/health/ready")
    finally:
        connection.close()
        connection.settings_dict["PORT"] = puerto_original
    cuerpo = _assert_problema(respuesta, 503, "servicio_no_disponible")
    # Sin topología ni versiones (THREAT-028).
    assert "5432" not in respuesta.content.decode() and "postgres" not in respuesta.content.decode()
    assert _trace_en_log(logs_json(), cuerpo["trace_id"])


@pytest.mark.django_db
def test_AC_TKT001_02_ready_503_si_select_no_devuelve_1(cliente, monkeypatch):
    monkeypatch.setattr(selectors, "base_datos_disponible", lambda: False)
    _assert_problema(cliente.get("/health/ready"), 503, "servicio_no_disponible")


@pytest.mark.django_db
def test_AC_TKT001_02_ready_aplica_statement_timeout():
    from django.db import transaction

    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT set_config('statement_timeout', %s, true)", ["1000ms"])
        cursor.execute("SHOW statement_timeout")
        assert cursor.fetchone()[0] == "1s"
    assert selectors.base_datos_disponible() is True


# ---------------------------------------------------------------------------
# AC-TKT001-03: errores en problem+json con trace_id = X-Trace-Id = log
# ---------------------------------------------------------------------------
@pytest.mark.urls("apps.core.tests.urls_prueba")
@pytest.mark.parametrize(
    ("metodo", "ruta", "status", "code"),
    [
        ("get", "/ruta/que/no/existe", 404, "no_encontrado"),
        ("post", "/prueba/solo-get", 405, "metodo_no_permitido"),
        ("get", "/prueba/fallo-drf", 500, "error_interno"),
        ("get", "/prueba/django-falla", 500, "error_interno"),
        ("get", "/prueba/no-encontrado", 404, "no_encontrado"),
        ("get", "/prueba/permiso", 403, "permiso_denegado"),
        ("get", "/prueba/denegada", 403, "permiso_denegado"),
        ("get", "/prueba/carga-grande", 413, "carga_demasiado_grande"),
        ("get", "/prueba/django-prohibida", 403, "permiso_denegado"),
        ("get", "/prueba/django-sospechosa", 400, "validacion"),
        ("get", "/prueba/django-grande", 413, "carga_demasiado_grande"),
        ("get", "/prueba/error-api", 409, "conflicto_version"),
    ],
)
def test_AC_TKT001_03_errores_problem_json_con_trace_id(
    cliente, logs_json, metodo, ruta, status, code
):
    respuesta = getattr(cliente, metodo)(ruta)
    cuerpo = _assert_problema(respuesta, status, code)
    assert _trace_en_log(logs_json(), cuerpo["trace_id"])
    # Sin trazas ni mensajes técnicos en la respuesta (ALT-025).
    assert "Traceback" not in respuesta.content.decode()
    assert "dato-sensible" not in respuesta.content.decode()


@pytest.mark.urls("apps.core.tests.urls_prueba")
def test_AC_TKT001_03_405_incluye_allow(cliente):
    respuesta = cliente.post("/prueba/solo-get")
    assert "GET" in respuesta["Allow"]


@pytest.mark.urls("apps.core.tests.urls_prueba")
def test_AC_TKT001_03_validacion_drf_con_errores_por_campo(cliente, logs_json):
    respuesta = cliente.post(
        "/prueba/validacion",
        {"dias": [{"titulo": "demasiado largo"}, {}]},
        content_type="application/json",
    )
    cuerpo = _assert_problema(respuesta, 400, "validacion")
    assert set(cuerpo["errors"]) == {"nombre", "dias.0.titulo", "dias.1.titulo"}
    assert _trace_en_log(logs_json(), cuerpo["trace_id"])


@pytest.mark.urls("apps.core.tests.urls_prueba")
def test_AC_TKT001_03_validacion_general_en_general(cliente):
    respuesta = cliente.post(
        "/prueba/validacion",
        {"nombre": "prohibido", "dias": []},
        content_type="application/json",
    )
    cuerpo = _assert_problema(respuesta, 400, "validacion")
    assert cuerpo["errors"] == {"_general": ["Nombre no permitido."]}


@pytest.mark.urls("apps.core.tests.urls_prueba")
def test_AC_TKT001_03_json_malformado_y_tipo_no_soportado(cliente):
    _assert_problema(
        cliente.post("/prueba/validacion", "{no-json", content_type="application/json"),
        400,
        "validacion",
    )
    _assert_problema(
        cliente.post("/prueba/validacion", "a=1", content_type="text/plain"),
        415,
        "tipo_medio_no_soportado",
    )


@pytest.mark.urls("apps.core.tests.urls_prueba")
def test_AC_TKT001_03_error_api_conserva_cabeceras_y_campos_propios(cliente):
    respuesta = cliente.get("/prueba/error-api")
    cuerpo = _assert_problema(respuesta, 409, "conflicto_version")
    assert respuesta["X-Prueba"] == "1"
    assert cuerpo["usos"] == []


@pytest.mark.urls("apps.core.tests.urls_prueba")
def test_AC_TKT001_03_csrf_invalido_problem_json():
    from django.test import Client

    cliente_csrf = Client(enforce_csrf_checks=True, raise_request_exception=False)
    _assert_problema(cliente_csrf.post("/prueba/django-csrf"), 403, "csrf_invalido")


@pytest.mark.django_db
@pytest.mark.urls("apps.core.tests.urls_prueba")
def test_AC_TKT001_03_limite_de_tasa_429_con_retry_after(cliente):
    for _ in range(2):
        assert cliente.get("/prueba/limitada", REMOTE_ADDR="198.51.100.7").status_code == 200
    respuesta = cliente.get("/prueba/limitada", REMOTE_ADDR="198.51.100.7")
    _assert_problema(respuesta, 429, "limite_tasa")
    assert int(respuesta["Retry-After"]) >= 1
    # Otra red /24 conserva su propia cuota.
    assert cliente.get("/prueba/limitada", REMOTE_ADDR="198.51.101.7").status_code == 200


# ---------------------------------------------------------------------------
# AC-TKT001-04: traceparent válido se propaga; inválido se regenera
# ---------------------------------------------------------------------------
def test_AC_TKT001_04_traceparent_valido_se_propaga(cliente):
    respuesta = cliente.get("/health/live", HTTP_TRACEPARENT=TRACEPARENT_VALIDO)
    assert respuesta["X-Trace-Id"] == "4bf92f3577b34da6a3ce929d0e0e4736"


@pytest.mark.parametrize(
    "traceparent",
    [
        "basura",
        "00-4BF92F3577B34DA6A3CE929D0E0E4736-00f067aa0ba902b7-01",
        "00-00000000000000000000000000000000-00f067aa0ba902b7-01",
        "00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01",
        "ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01-extra",
    ],
)
def test_AC_TKT001_04_traceparent_invalido_se_regenera(cliente, traceparent):
    respuesta = cliente.get("/health/live", HTTP_TRACEPARENT=traceparent)
    trace_id = respuesta["X-Trace-Id"]
    assert PATRON_TRACE.fullmatch(trace_id)
    assert trace_id != "4bf92f3577b34da6a3ce929d0e0e4736"


def test_AC_TKT001_04_sin_traceparent_cada_peticion_tiene_traza_nueva(cliente):
    primera = cliente.get("/health/live")["X-Trace-Id"]
    segunda = cliente.get("/health/live")["X-Trace-Id"]
    assert primera != segunda


def test_AC_TKT001_04_traza_propagada_llega_a_errores_y_logs(cliente, logs_json):
    respuesta = cliente.get("/no/existe", HTTP_TRACEPARENT=TRACEPARENT_VALIDO)
    cuerpo = _assert_problema(respuesta, 404, "no_encontrado")
    assert cuerpo["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert _trace_en_log(logs_json(), "4bf92f3577b34da6a3ce929d0e0e4736")


# ---------------------------------------------------------------------------
# AC-TKT001-05: logs JSON, sin IP completa ni query strings de búsqueda
# ---------------------------------------------------------------------------
@pytest.mark.urls("apps.core.tests.urls_prueba")
def test_AC_TKT001_05_logs_json_sin_ip_ni_query(cliente, logs_json):
    ip = "203.0.113.77"
    cliente.get(
        "/api/v1/publico/buscar?q=texto-secreto-del-visitante",
        REMOTE_ADDR=ip,
        HTTP_X_FORWARDED_FOR=ip,
    )
    cliente.get("/prueba/fallo-drf?q=otro-secreto", REMOTE_ADDR=ip, HTTP_X_FORWARDED_FOR=ip)
    cliente.get("/prueba/django-falla?q=tercer-secreto", REMOTE_ADDR=ip, HTTP_X_FORWARDED_FOR=ip)
    texto = logs_json.texto()
    lineas = logs_json()  # cada línea es JSON válido (json.loads)
    assert len(lineas) >= 3
    for secreto in (ip, "texto-secreto", "otro-secreto", "tercer-secreto", "q="):
        assert secreto not in texto
    peticiones = [linea for linea in lineas if linea.get("event") == "peticion"]
    assert {"trace_id", "metodo", "endpoint", "status", "duration_ms", "timestamp", "level"} <= set(
        peticiones[0]
    )
    assert peticiones[0]["endpoint"] == "<no_resuelta>"
    assert any(linea.get("endpoint") == "/prueba/fallo-drf" for linea in peticiones)
    errores = [linea for linea in lineas if linea.get("event") == "excepcion_no_controlada"]
    assert errores and "RuntimeError" in errores[0]["exception"]


def test_AC_TKT001_05_filtro_elimina_claves_sensibles():
    from apps.core.observabilidad import eliminar_claves_sensibles

    evento = {"event": "x", "ip": "1.2.3.4", "Password": "p", "q": "busqueda", "status": 200}
    assert eliminar_claves_sensibles(None, "info", evento) == {"event": "x", "status": 200}


# ---------------------------------------------------------------------------
# AC-TKT001-06: manage.py spectacular funciona
# ---------------------------------------------------------------------------
def test_AC_TKT001_06_spectacular_genera_esquema_valido(tmp_path):
    destino = tmp_path / "generado.yaml"
    call_command("spectacular", "--validate", "--file", str(destino))
    esquema = yaml.safe_load(destino.read_text(encoding="utf-8"))
    assert esquema["openapi"].startswith("3.1")
    operaciones = {
        esquema["paths"][ruta]["get"]["operationId"] for ruta in ("/health/live", "/health/ready")
    }
    assert operaciones == {"saludLive", "saludReady"}
    problema_503 = esquema["paths"]["/health/ready"]["get"]["responses"]["503"]["content"]
    assert PROBLEMA in problema_503


# ---------------------------------------------------------------------------
# AC-TKT001-07: pytest con cobertura >= 80 % sobre PostgreSQL real (test_brujula)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_AC_TKT001_07_pytest_en_postgresql_con_umbral_de_cobertura():
    config = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    opciones = config["tool"]["pytest"]["ini_options"]["addopts"]
    umbral = next(o for o in opciones if o.startswith("--cov-fail-under="))
    assert int(umbral.split("=")[1]) >= 80
    assert connection.vendor == "postgresql"
    assert connection.settings_dict["NAME"] == "test_brujula"


# ---------------------------------------------------------------------------
# AC-TKT001-08: contrato con infra/docker/backend.Dockerfile y compose
# ---------------------------------------------------------------------------
def test_AC_TKT001_08_contrato_de_la_imagen():
    config = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["tool"]["uv"]["package"] is False
    assert config["project"]["requires-python"] == "==3.13.*"
    dependencias = config["project"]["dependencies"]
    assert all("==" in dep for dep in dependencias)
    assert any(dep.startswith("gunicorn==") for dep in dependencias)
    assert (BACKEND / "uv.lock").is_file()
    assert (BACKEND / "manage.py").is_file()
    # gunicorn config.wsgi:application con DJANGO_SETTINGS_MODULE=config.settings (prod).
    resultado = subprocess.run(
        [
            sys.executable,
            "-c",
            "from config.wsgi import application; from django.conf import settings; "
            "print(type(application).__name__, settings.DEBUG, settings.OTEL_SDK_DISABLED)",
        ],
        cwd=BACKEND,
        env=_entorno_prod(OTEL_SDK_DISABLED="true"),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.split() == ["WSGIHandler", "False", "True"]
