"""AC-TKT004-05: auditoría del panel (FEAT-046, FLOW-016, AC-030, AC-058, THREAT-013).

Cada acción del panel genera un evento; GET /api/v1/panel/auditoria filtra y pagina (solo
Administrador); nadie puede alterar los eventos (sin operación de edición; app_rw sin UPDATE/
DELETE) y la IP solo se guarda truncada en los eventos de autenticación.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import ProgrammingError, connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.contenido.tests.fabricas import como_rol
from apps.cuentas.tests.conftest import BASE, IP, post, problema

pytestmark = pytest.mark.django_db
RUTA = f"{BASE}/auditoria"


def test_AC_TKT004_05_cada_accion_del_panel_genera_un_evento(cliente_admin, admin):
    cliente = Client(raise_request_exception=False)
    post(cliente, "/auth/login", {"usuario": "nadie", "contrasena": "x"}, REMOTE_ADDR=IP)
    alta = post(
        cliente_admin, "/cuentas", {"usuario": "auditada", "nombre_visible": "A", "rol": "EDITOR"}
    )
    cuenta_id = alta.json()["cuenta"]["id"]
    cliente_admin.patch(
        f"{BASE}/cuentas/{cuenta_id}", {"rol": "ADMINISTRADOR"}, content_type="application/json"
    )
    post(cliente_admin, f"/cuentas/{cuenta_id}/restablecer-contrasena")
    post(cliente_admin, f"/cuentas/{cuenta_id}/restablecer-mfa")
    post(cliente_admin, f"/cuentas/{cuenta_id}/desactivar")
    post(cliente_admin, f"/cuentas/{cuenta_id}/reactivar")
    post(cliente_admin, f"/cuentas/{cuenta_id}/desactivar")
    post(cliente_admin, f"/cuentas/{cuenta_id}/anonimizar")
    post(cliente_admin, "/auth/logout", REMOTE_ADDR=IP)
    acciones = set(EventoAuditoria.objects.values_list("accion", flat=True))
    assert {
        "LOGIN_OK",
        "LOGIN_FALLIDO",
        "LOGOUT",
        "CUENTA_CREAR",
        "CUENTA_ROL",
        "CUENTA_RESTABLECER",
        "CUENTA_DESACTIVAR",
        "CUENTA_REACTIVAR",
        "CUENTA_ANONIMIZAR",
    } <= acciones
    # La IP solo en eventos de autenticación y siempre truncada (REQ-057, DEC-AUTO-092).
    for evento in EventoAuditoria.objects.all():
        if evento.accion in ("LOGIN_OK", "LOGIN_FALLIDO", "LOGOUT", "BLOQUEO"):
            assert evento.ip_truncada in (None, "203.0.113.0/24")
        else:
            assert evento.ip_truncada is None


def test_AC_TKT004_05_consulta_paginada_ordenada_y_filtrada(cliente_admin, admin, editora):
    ahora = timezone.now()
    for indice in range(55):
        registrar_evento(
            accion="CREAR",
            actor_id=editora.cuenta.pk,
            actor_etiqueta="editora.uno",
            tipo_entidad="DESTINO",
            entidad_id=indice + 1,
            entidad_titulo=f"Destino {indice}",
            campos_cambiados=["titulo"],
        )
    registrar_evento(accion="LOGIN_FALLIDO", resultado="FALLO", ip="198.51.100.9")
    pagina1 = cliente_admin.get(RUTA).json()
    total = EventoAuditoria.objects.count()
    assert pagina1["total"] == total and pagina1["tamano_pagina"] == 50
    assert pagina1["siguiente"].startswith("/api/v1/panel/auditoria?")
    fechas = [e["ocurrido_en"] for e in pagina1["resultados"]]
    assert fechas == sorted(fechas, reverse=True)
    primero = pagina1["resultados"][0]
    assert set(primero) >= {
        "id",
        "ocurrido_en",
        "actor",
        "accion",
        "resultado",
        "campos_cambiados",
        "ip_truncada",
    }
    assert set(primero["actor"]) == {"id", "etiqueta"}

    fallidos = cliente_admin.get(f"{RUTA}?accion=LOGIN_FALLIDO&resultado=FALLO").json()
    assert fallidos["total"] == 1
    assert fallidos["resultados"][0]["ip_truncada"] == "198.51.100.0/24"
    assert fallidos["resultados"][0]["actor"] == {"id": None, "etiqueta": "desconocido"}
    assert fallidos["resultados"][0]["campos_cambiados"] == []
    por_actor = cliente_admin.get(
        f"{RUTA}?actor_id={editora.cuenta.pk}&tipo_entidad=DESTINO"
    ).json()
    assert por_actor["total"] == 55
    desde = (ahora - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    hasta = (ahora + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    rango = cliente_admin.get(RUTA, {"desde": desde, "hasta": hasta, "pagina": 2}).json()
    assert rango["pagina"] == 2
    futuro = cliente_admin.get(RUTA, {"desde": (ahora + timedelta(days=1)).isoformat()}).json()
    assert futuro["total"] == 0


@pytest.mark.parametrize(
    "consulta",
    [
        "accion=BORRAR",
        "resultado=QUIZA",
        "actor_id=0",
        "actor_id=abc",
        "desde=ayer",
        "tipo_entidad=destino",
        "orden=asc",
        "pagina=0",
        "accion=CREAR&accion=EDITAR",
    ],
)
def test_AC_TKT004_05_filtros_invalidos_son_400(cliente_admin, consulta):
    problema(cliente_admin.get(f"{RUTA}?{consulta}"), 400, "parametro_invalido")


def test_AC_TKT004_05_pagina_fuera_de_rango_404(cliente_admin):
    problema(cliente_admin.get(f"{RUTA}?pagina=500"), 404, "pagina_fuera_de_rango")


def test_AC_TKT004_05_solo_administrador_y_solo_lectura(cliente_admin, cliente_editora):
    problema(cliente_editora.get(RUTA), 403, "permiso_denegado")
    problema(Client().get(RUTA), 401, "no_autenticado")
    for metodo in ("post", "put", "patch", "delete"):
        respuesta = getattr(cliente_admin, metodo)(RUTA, {}, content_type="application/json")
        problema(respuesta, 405, "metodo_no_permitido")


def test_AC_TKT004_05_app_rw_no_puede_alterar_eventos(admin):
    evento = registrar_evento(
        accion="CREAR", actor_id=admin.cuenta.pk, actor_etiqueta="admin.principal"
    )
    for sentencia in (
        "UPDATE app.evento_auditoria SET accion = 'EDITAR' WHERE id = %s",
        "DELETE FROM app.evento_auditoria WHERE id = %s",
    ):
        with (
            como_rol("app_rw") as cursor,
            pytest.raises(ProgrammingError, match="permission denied"),
        ):
            cursor.execute(sentencia, [evento.pk])
    assert EventoAuditoria.objects.get(pk=evento.pk).accion == "CREAR"


def test_AC_TKT004_05_ip_solo_en_eventos_de_autenticacion():
    creado = registrar_evento(accion="CREAR", ip="203.0.113.5")
    login = registrar_evento(accion="LOGIN_OK", ip="2001:db8:abcd:12::1")
    invalida = registrar_evento(accion="LOGIN_FALLIDO", ip="no-es-ip")
    creado.refresh_from_db()
    login.refresh_from_db()
    assert creado.ip_truncada is None
    assert login.ip_truncada == "2001:db8:abcd::/48"
    assert invalida.ip_truncada is None


def test_AC_TKT004_05_consulta_sin_n_mas_1(cliente_admin, editora):
    def contar() -> int:
        with CaptureQueriesContext(connection) as capturadas:
            assert cliente_admin.get(RUTA).status_code == 200
        return len(capturadas)

    base = contar()
    for _ in range(30):
        registrar_evento(accion="EDITAR", actor_id=editora.cuenta.pk, actor_etiqueta="editora.uno")
    assert contar() == base
