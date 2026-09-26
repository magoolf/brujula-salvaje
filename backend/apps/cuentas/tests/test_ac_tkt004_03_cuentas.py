"""AC-TKT004-03: cuentas del staff, solo Administrador (FEAT-045, FLOW-015, RULE-015).

Editor → 403 en cada operación (también sobre su propia cuenta: acceso horizontal y vertical),
regla del último Administrador, contraseña temporal devuelta una vez y nunca persistida ni
registrada. Trazabilidad: AC-105..108; THREAT-004, THREAT-024, THREAT-025, THREAT-027.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext

from apps.auditoria.models import EventoAuditoria
from apps.cuentas.models import (
    CuentaCodigoRecuperacion,
    CuentaStaff,
    EstadoCuenta,
    RolCuenta,
    SesionPanel,
)
from apps.cuentas.tests.conftest import (
    BASE,
    CONTRASENA,
    IP,
    crear_staff,
    entrar,
    post,
    problema,
)

pytestmark = pytest.mark.django_db

ACCIONES = ("restablecer-contrasena", "restablecer-mfa", "desactivar", "reactivar", "anonimizar")


def _operaciones(cuenta_id: int) -> list[tuple[str, str, dict | None]]:
    return [
        ("get", "/cuentas", None),
        ("post", "/cuentas", {"usuario": "x.y.z", "nombre_visible": "X", "rol": "EDITOR"}),
        ("get", f"/cuentas/{cuenta_id}", None),
        ("patch", f"/cuentas/{cuenta_id}", {"rol": "ADMINISTRADOR"}),
        *[("post", f"/cuentas/{cuenta_id}/{accion}", None) for accion in ACCIONES],
        ("get", "/auditoria", None),
    ]


def _llamar(cliente: Client, metodo: str, ruta: str, datos: dict | None):
    llamada = getattr(cliente, metodo)
    if metodo == "get":
        return llamada(f"{BASE}{ruta}")
    return llamada(f"{BASE}{ruta}", datos or {}, content_type="application/json")


# ---------------------------------------------------------------------------
# Autorización vertical y horizontal (THREAT-004, AC-105)
# ---------------------------------------------------------------------------
def test_AC_TKT004_03_editor_recibe_403_en_cuentas_y_auditoria(cliente_editora, editora, admin):
    antes = CuentaStaff.objects.count()
    for objetivo in (admin.cuenta.pk, editora.cuenta.pk):  # otra cuenta y la propia
        for metodo, ruta, datos in _operaciones(objetivo):
            problema(_llamar(cliente_editora, metodo, ruta, datos), 403, "permiso_denegado")
    assert CuentaStaff.objects.count() == antes
    admin.cuenta.refresh_from_db()
    assert admin.cuenta.estado == EstadoCuenta.ACTIVA


def test_AC_TKT004_03_anonimo_recibe_401(cliente, admin):
    for metodo, ruta, datos in _operaciones(admin.cuenta.pk):
        problema(_llamar(cliente, metodo, ruta, datos), 401, "no_autenticado")


def test_AC_TKT004_03_rol_se_lee_de_la_bd_no_de_la_peticion(cliente_editora):
    respuesta = cliente_editora.get(f"{BASE}/cuentas", HTTP_X_ROL="ADMINISTRADOR")
    problema(respuesta, 403, "permiso_denegado")


def test_AC_TKT004_03_id_inexistente_o_fuera_de_rango_es_404(cliente_admin):
    for ruta in ("/cuentas/999999", "/cuentas/99999999999999999999", "/cuentas/0"):
        problema(cliente_admin.get(f"{BASE}{ruta}"), 404, "no_encontrado")
    problema(post(cliente_admin, "/cuentas/999999/desactivar"), 404, "no_encontrado")


def test_AC_TKT004_03_metodos_no_definidos_405(cliente_admin, editora):
    problema(
        cliente_admin.delete(f"{BASE}/cuentas/{editora.cuenta.pk}"), 405, "metodo_no_permitido"
    )
    problema(
        cliente_admin.put(
            f"{BASE}/cuentas/{editora.cuenta.pk}", {}, content_type="application/json"
        ),
        405,
        "metodo_no_permitido",
    )


# ---------------------------------------------------------------------------
# Alta (AC-106, THREAT-027)
# ---------------------------------------------------------------------------
def test_AC_TKT004_03_alta_con_temporal_que_no_se_persiste_ni_registra(
    cliente_admin, admin, logs_json
):
    respuesta = post(
        cliente_admin,
        "/cuentas",
        {"usuario": "nueva.cuenta", "nombre_visible": "Nueva", "rol": "EDITOR"},
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    temporal = cuerpo["contrasena_temporal"]
    assert 16 <= len(temporal) <= 64
    assert cuerpo["cuenta"]["estado"] == "PENDIENTE_ACTIVACION"
    assert cuerpo["cuenta"]["etiqueta"] == "nueva.cuenta"
    assert cuerpo["cuenta"]["debe_cambiar_credencial"] is True
    cuenta = CuentaStaff.objects.get(usuario="nueva.cuenta")
    assert cuenta.check_password(temporal)
    assert temporal not in cuenta.password
    assert temporal not in logs_json.texto()
    evento = EventoAuditoria.objects.get(accion="CUENTA_CREAR")
    assert evento.actor_id == admin.cuenta.pk
    assert (evento.tipo_entidad, evento.entidad_id) == ("CUENTA", cuenta.pk)
    assert evento.entidad_titulo == f"Cuenta #{cuenta.pk}"  # sin PII
    assert evento.campos_cambiados == ["nombre_visible", "rol", "usuario"]
    # Ninguna tabla guarda la contraseña temporal en claro.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM app.evento_auditoria WHERE entidad_titulo LIKE %s",
            [f"%{temporal}%"],
        )
        assert cursor.fetchone()[0] == 0
        cursor.execute(
            "SELECT count(*) FROM app.idempotencia_peticion WHERE cuerpo_respuesta::text LIKE %s",
            [f"%{temporal}%"],
        )
        assert cursor.fetchone()[0] == 0


def test_AC_TKT004_03_alta_valida_la_entrada(cliente_admin, editora):
    problema(
        post(
            cliente_admin,
            "/cuentas",
            {"usuario": "editora.uno", "nombre_visible": "Dup", "rol": "EDITOR"},
        ),
        409,
        "duplicado",
    )
    problema(
        post(
            cliente_admin, "/cuentas", {"usuario": "Mayus", "nombre_visible": "X", "rol": "EDITOR"}
        ),
        400,
        "validacion",
    )
    problema(
        post(
            cliente_admin, "/cuentas", {"usuario": "ok.user", "nombre_visible": "X", "rol": "SUPER"}
        ),
        400,
        "validacion",
    )
    # THREAT-024: estado o credenciales no se pueden fijar en el alta.
    respuesta = post(
        cliente_admin,
        "/cuentas",
        {"usuario": "ok.user", "nombre_visible": "X", "rol": "EDITOR", "estado": "ACTIVA"},
    )
    assert "estado" in problema(respuesta, 400, "campo_no_permitido")["errors"]


# ---------------------------------------------------------------------------
# Listado, detalle y edición
# ---------------------------------------------------------------------------
def test_AC_TKT004_03_listado_paginado_y_filtrado(cliente_admin, admin, editora):
    crear_staff("editor.baja", estado=EstadoCuenta.DESACTIVADA)
    cuerpo = cliente_admin.get(f"{BASE}/cuentas").json()
    assert cuerpo["total"] == 3
    assert cuerpo["tamano_pagina"] == 50
    assert {c["usuario"] for c in cuerpo["resultados"]} == {
        "admin.principal",
        "editora.uno",
        "editor.baja",
    }
    assert "password" not in cuerpo["resultados"][0]
    assert "secreto_mfa" not in cuerpo["resultados"][0]
    solo = cliente_admin.get(f"{BASE}/cuentas?estado=DESACTIVADA&rol=EDITOR").json()
    assert [c["usuario"] for c in solo["resultados"]] == ["editor.baja"]
    problema(cliente_admin.get(f"{BASE}/cuentas?estado=BORRADA"), 400, "parametro_invalido")
    problema(cliente_admin.get(f"{BASE}/cuentas?orden=usuario"), 400, "parametro_invalido")
    problema(
        cliente_admin.get(f"{BASE}/cuentas?rol=EDITOR&rol=ADMINISTRADOR"), 400, "parametro_invalido"
    )
    problema(cliente_admin.get(f"{BASE}/cuentas?pagina=9"), 404, "pagina_fuera_de_rango")


def _consultas(cliente: Client, ruta: str) -> int:
    with CaptureQueriesContext(connection) as capturadas:
        assert cliente.get(ruta).status_code == 200
    return len(capturadas)


def test_AC_TKT004_03_listado_sin_n_mas_1(cliente_admin):
    # El número de consultas no depende del número de cuentas (sin N+1).
    con_una = _consultas(cliente_admin, f"{BASE}/cuentas")
    for indice in range(20):
        crear_staff(f"editor.{indice}")
    assert _consultas(cliente_admin, f"{BASE}/cuentas") == con_una


def test_AC_TKT004_03_detalle_y_edicion(cliente_admin, editora):
    detalle = cliente_admin.get(f"{BASE}/cuentas/{editora.cuenta.pk}").json()
    assert detalle["usuario"] == "editora.uno"
    respuesta = cliente_admin.patch(
        f"{BASE}/cuentas/{editora.cuenta.pk}",
        {"nombre_visible": "Nombre nuevo"},
        content_type="application/json",
    )
    assert respuesta.json()["nombre_visible"] == "Nombre nuevo"
    problema(
        cliente_admin.patch(
            f"{BASE}/cuentas/{editora.cuenta.pk}", {}, content_type="application/json"
        ),
        400,
        "validacion",
    )
    problema(
        cliente_admin.patch(
            f"{BASE}/cuentas/{editora.cuenta.pk}",
            {"estado": "ACTIVA"},
            content_type="application/json",
        ),
        400,
        "campo_no_permitido",
    )
    assert (
        EventoAuditoria.objects.filter(accion="CUENTA_ROL", entidad_id=editora.cuenta.pk).count()
        == 1
    )


def test_AC_TKT004_03_cambio_de_rol_invalida_sesiones(cliente_admin, editora):
    sesion_editora = Client(raise_request_exception=False)
    entrar(sesion_editora, editora)
    respuesta = cliente_admin.patch(
        f"{BASE}/cuentas/{editora.cuenta.pk}",
        {"rol": "ADMINISTRADOR"},
        content_type="application/json",
    )
    assert respuesta.json()["rol"] == "ADMINISTRADOR"
    assert not SesionPanel.objects.filter(cuenta=editora.cuenta).exists()
    problema(sesion_editora.get(f"{BASE}/auth/sesion"), 401, "no_autenticado")


# ---------------------------------------------------------------------------
# RULE-015 / AC-108: siempre >= 1 Administrador ACTIVO; nada sobre uno mismo
# ---------------------------------------------------------------------------
def test_AC_TKT004_03_no_se_actua_sobre_la_propia_cuenta(cliente_admin, admin):
    propio = admin.cuenta.pk
    problema(
        cliente_admin.patch(
            f"{BASE}/cuentas/{propio}", {"rol": "EDITOR"}, content_type="application/json"
        ),
        409,
        "operacion_sobre_si_mismo",
    )
    for accion in ACCIONES:
        problema(
            post(cliente_admin, f"/cuentas/{propio}/{accion}"), 409, "operacion_sobre_si_mismo"
        )
    # Cambiar el nombre propio sí está permitido.
    assert (
        cliente_admin.patch(
            f"{BASE}/cuentas/{propio}", {"nombre_visible": "Yo"}, content_type="application/json"
        ).status_code
        == 200
    )


def test_AC_TKT004_03_no_se_degrada_ni_desactiva_al_ultimo_admin_activo(cliente_admin, admin):
    otra = crear_staff("admin.dos", rol=RolCuenta.ADMINISTRADOR)
    # La administradora que actúa queda bloqueada temporalmente: "admin.dos" es la única ACTIVA.
    CuentaStaff.objects.filter(pk=admin.cuenta.pk).update(estado=EstadoCuenta.BLOQUEADA_TEMPORAL)
    ruta = f"{BASE}/cuentas/{otra.cuenta.pk}"
    problema(
        cliente_admin.patch(ruta, {"rol": "EDITOR"}, content_type="application/json"),
        409,
        "ultimo_administrador",
    )
    problema(
        post(cliente_admin, f"/cuentas/{otra.cuenta.pk}/desactivar"), 409, "ultimo_administrador"
    )
    problema(
        post(cliente_admin, f"/cuentas/{otra.cuenta.pk}/restablecer-contrasena"),
        409,
        "ultimo_administrador",
    )
    # Con otra administradora activa, sí.
    CuentaStaff.objects.filter(pk=admin.cuenta.pk).update(estado=EstadoCuenta.ACTIVA)
    assert (
        cliente_admin.patch(ruta, {"rol": "EDITOR"}, content_type="application/json").status_code
        == 200
    )


# ---------------------------------------------------------------------------
# Restablecer, desactivar, reactivar y anonimizar (FLOW-015, THREAT-025, AC-107)
# ---------------------------------------------------------------------------
def test_AC_TKT004_03_restablecer_contrasena(cliente_admin, editora):
    sesion = Client(raise_request_exception=False)
    entrar(sesion, editora)
    respuesta = post(cliente_admin, f"/cuentas/{editora.cuenta.pk}/restablecer-contrasena")
    assert respuesta.status_code == 200
    temporal = respuesta.json()["contrasena_temporal"]
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.estado == EstadoCuenta.PENDIENTE_ACTIVACION
    assert editora.cuenta.debe_cambiar_credencial is True
    assert editora.cuenta.check_password(temporal)
    assert not editora.cuenta.check_password(CONTRASENA)
    problema(sesion.get(f"{BASE}/auth/sesion"), 401, "no_autenticado")
    assert EventoAuditoria.objects.filter(
        accion="CUENTA_RESTABLECER", entidad_id=editora.cuenta.pk
    ).exists()
    # Con la temporal entra con el paso CAMBIO_CREDENCIAL (y conserva su autorización).
    nueva = post(
        Client(), "/auth/login", {"usuario": "editora.uno", "contrasena": temporal}, REMOTE_ADDR=IP
    )
    assert nueva.json()["paso_pendiente"] == "CAMBIO_CREDENCIAL"


def test_AC_TKT004_03_restablecer_mfa(cliente_admin):
    con_mfa = crear_staff("editor.mfa", con_mfa=True)
    CuentaCodigoRecuperacion.objects.create(cuenta=con_mfa.cuenta, hash_codigo="c" * 64)
    respuesta = post(cliente_admin, f"/cuentas/{con_mfa.cuenta.pk}/restablecer-mfa")
    assert respuesta.status_code == 200
    assert respuesta.json()["cuenta"]["mfa_activo"] is False
    con_mfa.cuenta.refresh_from_db()
    assert con_mfa.cuenta.secreto_mfa is None
    assert not CuentaCodigoRecuperacion.objects.filter(cuenta=con_mfa.cuenta).exists()


def test_AC_TKT004_03_desactivar_invalida_sesiones_y_credenciales(
    cliente_admin, editora, tmp_path, django_capture_on_commit_callbacks
):
    sesion = Client(raise_request_exception=False)
    entrar(sesion, editora)
    libro = tmp_path / "ops" / "libro.log"
    with (
        override_settings(LIBRO_ANONIMIZACIONES_PATH=str(libro)),
        django_capture_on_commit_callbacks(execute=True),
    ):
        respuesta = post(cliente_admin, f"/cuentas/{editora.cuenta.pk}/desactivar")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "DESACTIVADA"
    assert respuesta.json()["desactivado_en"] is not None
    problema(sesion.get(f"{BASE}/auth/sesion"), 401, "no_autenticado")
    problema(
        post(
            Client(),
            "/auth/login",
            {"usuario": "editora.uno", "contrasena": CONTRASENA},
            REMOTE_ADDR=IP,
        ),
        401,
        "credenciales_invalidas",
    )
    editora.cuenta.refresh_from_db()
    assert not editora.cuenta.has_usable_password()
    assert Path(libro).read_text(encoding="utf-8").startswith(f"{editora.cuenta.pk};DESACTIVADA;")
    problema(
        post(cliente_admin, f"/cuentas/{editora.cuenta.pk}/desactivar"), 409, "transicion_invalida"
    )
    problema(
        post(cliente_admin, f"/cuentas/{editora.cuenta.pk}/restablecer-contrasena"),
        409,
        "transicion_invalida",
    )


def test_AC_TKT004_03_reactivar(cliente_admin, editora):
    problema(
        post(cliente_admin, f"/cuentas/{editora.cuenta.pk}/reactivar"), 409, "transicion_invalida"
    )
    post(cliente_admin, f"/cuentas/{editora.cuenta.pk}/desactivar")
    respuesta = post(cliente_admin, f"/cuentas/{editora.cuenta.pk}/reactivar")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["cuenta"]["estado"] == "PENDIENTE_ACTIVACION"
    assert cuerpo["cuenta"]["desactivado_en"] is None
    assert EventoAuditoria.objects.filter(accion="CUENTA_REACTIVAR").count() == 1


def test_AC_TKT004_03_anonimizar(
    cliente_admin, editora, tmp_path, django_capture_on_commit_callbacks
):
    entrar(Client(), editora)  # genera eventos LOGIN_OK con IP
    problema(
        post(cliente_admin, f"/cuentas/{editora.cuenta.pk}/anonimizar"), 409, "transicion_invalida"
    )
    post(cliente_admin, f"/cuentas/{editora.cuenta.pk}/desactivar")
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO app.idempotencia_peticion (cuenta_id, clave, operacion, huella_peticion, "
            "codigo_http, cuerpo_omitido) VALUES "
            "(%s, gen_random_uuid(), 'panelCrearDestino', %s, 201, true)",
            [editora.cuenta.pk, "a" * 64],
        )
    libro = tmp_path / "libro.log"
    with (
        override_settings(LIBRO_ANONIMIZACIONES_PATH=str(libro)),
        django_capture_on_commit_callbacks(execute=True),
    ):
        respuesta = post(cliente_admin, f"/cuentas/{editora.cuenta.pk}/anonimizar")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ANONIMIZADA"
    assert (cuerpo["usuario"], cuerpo["nombre_visible"]) == (None, None)
    assert cuerpo["etiqueta"] == f"Cuenta anonimizada #{editora.cuenta.pk}"
    etiquetas = set(
        EventoAuditoria.objects.filter(actor=editora.cuenta).values_list(
            "actor_etiqueta", "ip_truncada"
        )
    )
    assert etiquetas == {(f"Cuenta anonimizada #{editora.cuenta.pk}", None)}
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM app.idempotencia_peticion WHERE cuenta_id = %s",
            [editora.cuenta.pk],
        )
        assert cursor.fetchone()[0] == 0
    assert "ANONIMIZADA" in libro.read_text(encoding="utf-8")
    problema(
        cliente_admin.patch(
            f"{BASE}/cuentas/{editora.cuenta.pk}",
            {"nombre_visible": "X"},
            content_type="application/json",
        ),
        409,
        "transicion_invalida",
    )


def test_AC_TKT004_03_libro_no_escrito_se_registra_sin_pii(
    cliente_admin, editora, tmp_path, django_capture_on_commit_callbacks, logs_json
):
    ocupado = tmp_path / "es-un-archivo"
    ocupado.write_text("x", encoding="utf-8")
    with (
        override_settings(LIBRO_ANONIMIZACIONES_PATH=str(ocupado / "libro.log")),
        django_capture_on_commit_callbacks(execute=True),
    ):
        assert post(cliente_admin, f"/cuentas/{editora.cuenta.pk}/desactivar").status_code == 200
    texto = logs_json.texto()
    assert "libro_anonimizaciones_no_escrito" in texto
    assert "editora.uno" not in texto
