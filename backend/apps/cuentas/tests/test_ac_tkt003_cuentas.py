"""Cuentas del staff y sesiones (DB_HANDOFF cuenta_staff, cuenta_codigo_recuperacion,
sesion_panel) y NV-02 de QA TKT-001 (AC-TKT003-04 y AC-TKT003-07)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.contenido.tests.fabricas import crear_cuenta, forzar_diferidas
from apps.cuentas.models import (
    CuentaCodigoRecuperacion,
    CuentaStaff,
    EstadoCuenta,
    RolCuenta,
    SesionPanel,
)
from apps.cuentas.sesiones import SessionStore
from apps.cuentas.tests.urls_prueba import USUARIO_PII

pytestmark = pytest.mark.django_db


@contextmanager
def _falla(excepcion=IntegrityError):
    with pytest.raises(excepcion), transaction.atomic():
        yield


def _activar(cuenta: CuentaStaff) -> None:
    cuenta.estado = EstadoCuenta.ACTIVA
    cuenta.autorizacion_otorgada_en = timezone.now()
    cuenta.autorizacion_version_politica = "1.0"
    cuenta.save()


# ---------------------------------------------------------------------------
# AUTH_USER_MODEL y modelo
# ---------------------------------------------------------------------------
def test_AC_TKT003_02_auth_user_model_es_cuenta_staff_sin_apps_auth():
    assert settings.AUTH_USER_MODEL == "cuentas.CuentaStaff"
    assert get_user_model() is CuentaStaff
    assert CuentaStaff._meta.db_table == "cuenta_staff"
    # El DB_HANDOFF no define tablas auth_*, django_content_type ni django_session.
    for app in ("django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions"):
        assert app not in settings.INSTALLED_APPS
    # last_login de Django se guarda en la columna ultimo_acceso_en.
    assert CuentaStaff._meta.get_field("last_login").column == "ultimo_acceso_en"


def test_AC_TKT003_04_is_active_se_deriva_del_estado():
    cuenta = crear_cuenta("editora.uno")
    assert cuenta.is_active is False
    assert cuenta.es_administrador is False
    _activar(cuenta)
    assert cuenta.is_active is True
    assert CuentaStaff.objects.get_by_natural_key("editora.uno") == cuenta
    assert str(cuenta) == f"Cuenta #{cuenta.pk}"
    assert "editora" not in str(cuenta)  # __str__ sin PII


def test_AC_TKT003_04_hash_de_credencial_nunca_en_claro():
    cuenta = crear_cuenta("editora.dos")
    cuenta.set_password("Frase-de-prueba-larga-2026")
    cuenta.save()
    cuenta.refresh_from_db()
    assert "Frase-de-prueba" not in cuenta.password
    assert cuenta.check_password("Frase-de-prueba-larga-2026")


# ---------------------------------------------------------------------------
# CHECK de cuenta_staff
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "campos",
    [
        {"usuario": "Mayusculas"},
        {"usuario": "con espacio"},
        {"rol": "SUPERUSUARIO"},
        {"estado": "BORRADA"},
        {"intentos_fallidos": -1},
        {"bloqueos_consecutivos": -1},
        {"nombre_visible": None},
        {"estado": EstadoCuenta.ACTIVA},  # ACTIVA sin autorización (REQ-070)
        {"estado": EstadoCuenta.DESACTIVADA},  # sin desactivado_en
        {"mfa_activo": True},  # sin secreto
    ],
)
def test_AC_TKT003_04_cuenta_staff_rechaza_estados_incoherentes(campos):
    with _falla():
        datos = dict(campos)
        crear_cuenta(datos.pop("usuario", "cuenta.invalida"), **datos)


def test_AC_TKT003_04_usuario_unico_y_anonimizacion_coherente():
    crear_cuenta("editora.tres")
    with _falla():
        crear_cuenta("editora.tres")
    ahora = timezone.now()
    anonimizada = crear_cuenta(
        None,
        nombre_visible=None,
        estado=EstadoCuenta.ANONIMIZADA,
        desactivado_en=ahora,
        anonimizado_en=ahora,
        password="!inutilizable",
    )
    assert anonimizada.usuario is None
    # Anonimizada que conserva PII o una credencial utilizable -> rechazo.
    with _falla():
        crear_cuenta(
            "sigue.identificable",
            estado=EstadoCuenta.ANONIMIZADA,
            desactivado_en=ahora,
            anonimizado_en=ahora,
            password="!inutilizable",
        )
    with _falla():
        crear_cuenta(
            None,
            nombre_visible=None,
            estado=EstadoCuenta.ANONIMIZADA,
            desactivado_en=ahora,
            anonimizado_en=ahora,
            password="pbkdf2_sha256$1$sal$hash",
        )


def test_AC_TKT003_04_trigger_admin_minimo_impide_quedarse_sin_administrador():
    admin = crear_cuenta("admin.unica", rol=RolCuenta.ADMINISTRADOR)
    _activar(admin)
    forzar_diferidas("trg_cuenta_admin_minimo")
    with _falla():
        admin.rol = RolCuenta.EDITOR
        admin.save()
        forzar_diferidas("trg_cuenta_admin_minimo")
    # Con otra administradora operativa, sí se puede degradar a la primera.
    crear_cuenta("admin.dos", rol=RolCuenta.ADMINISTRADOR)
    admin.refresh_from_db()
    admin.estado = EstadoCuenta.DESACTIVADA
    admin.desactivado_en = timezone.now()
    admin.save()
    forzar_diferidas("trg_cuenta_admin_minimo")


def test_AC_TKT003_04_codigos_de_recuperacion_unicos_por_cuenta():
    cuenta = crear_cuenta("editora.cuatro")
    codigo = CuentaCodigoRecuperacion.objects.create(cuenta=cuenta, hash_codigo="hash-1")
    assert str(codigo) == f"Código de recuperación #{codigo.pk}"
    with _falla():
        CuentaCodigoRecuperacion.objects.create(cuenta=cuenta, hash_codigo="hash-1")


# ---------------------------------------------------------------------------
# sesion_panel (DEC-AUTO-089): almacén de sesiones de Django sobre la tabla propia
# ---------------------------------------------------------------------------
def test_AC_TKT003_04_sesiones_en_sesion_panel_e_invalidacion_por_cuenta():
    cuenta = crear_cuenta("editora.cinco")
    tienda = SessionStore()
    tienda["dato"] = "valor"
    tienda.create()
    sesion = SesionPanel.objects.get(session_key=tienda.session_key)
    assert SesionPanel.get_session_store_class() is SessionStore
    assert "expira" in str(sesion)
    sesion.cuenta = cuenta
    sesion.autenticado_en = timezone.now()
    sesion.save()
    assert SessionStore(session_key=tienda.session_key)["dato"] == "valor"
    # THREAT-002/025: invalidar todas las sesiones de una cuenta.
    assert cuenta.sesiones.filter(expire_date__gt=timezone.now() - timedelta(days=1)).count() == 1
    cuenta.sesiones.all().delete()
    assert not SesionPanel.objects.filter(session_key=tienda.session_key).exists()


# ---------------------------------------------------------------------------
# AC-TKT003-07 (NV-02 de QA TKT-001): un IntegrityError con PII no llega al log
# ---------------------------------------------------------------------------
@pytest.mark.urls("apps.cuentas.tests.urls_prueba")
@pytest.mark.xfail(
    strict=True,
    reason=(
        "NV-02 abierto -> TKT-004: el manejador de apps/core registra exc_info y la traza "
        "incluye el DETAIL de PostgreSQL con el valor PII (usuario). apps/core queda fuera de "
        "los archivos permitidos de TKT-003. Al corregirlo, esta prueba pasa y el marcador "
        "strict obliga a retirarlo."
    ),
)
def test_AC_TKT003_07_integrity_error_no_registra_pii(cliente, logs_json):
    respuesta = cliente.post(
        "/prueba/cuenta-duplicada", data="{}", content_type="application/json"
    )
    assert respuesta.status_code == 500
    texto_log = logs_json.texto()
    assert "excepcion_no_controlada" in texto_log
    assert USUARIO_PII not in texto_log


@pytest.mark.urls("apps.cuentas.tests.urls_prueba")
def test_AC_TKT003_07_respuesta_http_no_expone_pii(cliente):
    respuesta = cliente.post(
        "/prueba/cuenta-duplicada", data="{}", content_type="application/json"
    )
    assert respuesta.status_code == 500
    assert USUARIO_PII not in respuesta.content.decode()
