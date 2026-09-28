"""AC-TKT005-05 (BP-1, DEC-AUTO-909): tareas del sistema sobre cuentas y auditoría.

- cuentas.services.anonimizar_cuentas_vencidas(): DESACTIVADAS hace > 30 días, actor "sistema",
  la fila persiste (CHG-DB-002), idempotente.
- cuentas.services.reaplicar_libro_anonimizaciones(): libro solo con ids, idempotente, sin PII.
- auditoria.services.purgar_eventos_caducados(): app.fn_auditoria_purgar() (365 días).
- Comandos anonimizar_cuentas, reaplicar_anonimizaciones y purgar_auditoria con lock y registro.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta

import pytest
from django.core.management import call_command, get_commands
from django.db import connection
from django.test import override_settings
from django.utils import timezone

from apps.auditoria.models import AccionAuditoria, EventoAuditoria
from apps.auditoria.services import purgar_eventos_caducados
from apps.cuentas import services
from apps.cuentas.models import (
    CuentaCodigoRecuperacion,
    CuentaStaff,
    EstadoCuenta,
    RolCuenta,
    SesionPanel,
)
from apps.cuentas.sesiones import SessionStore
from apps.cuentas.tests.conftest import crear_staff
from apps.ops.models import OpsEjecucionTarea, ResultadoTarea, TareaProgramada

pytestmark = pytest.mark.django_db


@pytest.fixture
def libro(tmp_path):
    ruta = tmp_path / "libro_anonimizaciones.log"
    with override_settings(LIBRO_ANONIMIZACIONES_PATH=str(ruta)):
        yield ruta


def _desactivada(usuario: str, hace_dias: int) -> CuentaStaff:
    cuenta = crear_staff(usuario, estado=EstadoCuenta.DESACTIVADA).cuenta
    CuentaStaff.objects.filter(pk=cuenta.pk).update(
        desactivado_en=timezone.now() - timedelta(days=hace_dias)
    )
    CuentaCodigoRecuperacion.objects.create(cuenta=cuenta, hash_codigo="h" * 64)
    sesion = SessionStore()
    sesion.create()
    SesionPanel.objects.filter(session_key=sesion.session_key).update(cuenta=cuenta)
    return cuenta


def _eventos(accion: str, cuenta: CuentaStaff) -> list[EventoAuditoria]:
    return list(EventoAuditoria.objects.filter(accion=accion, entidad_id=cuenta.pk))


# ---------------------------------------------------------------------------
# anonimizar_cuentas_vencidas
# ---------------------------------------------------------------------------
def test_AC_TKT005_05_anonimiza_solo_las_vencidas_con_actor_sistema(
    libro, django_capture_on_commit_callbacks
):
    vencida = _desactivada("vencida.uno", 31)
    reciente = _desactivada("reciente.dos", 10)
    activa = crear_staff("activa.tres").cuenta
    with django_capture_on_commit_callbacks(execute=True):
        assert services.anonimizar_cuentas_vencidas() == 1
    vencida.refresh_from_db()
    assert vencida.estado == EstadoCuenta.ANONIMIZADA
    assert (vencida.usuario, vencida.nombre_visible, vencida.secreto_mfa) == (None, None, None)
    assert not vencida.has_usable_password()
    assert not CuentaCodigoRecuperacion.objects.filter(cuenta=vencida).exists()
    assert not SesionPanel.objects.filter(cuenta=vencida).exists()
    evento = _eventos(AccionAuditoria.CUENTA_ANONIMIZAR, vencida)[0]
    assert (evento.actor_id, evento.actor_etiqueta) == (None, "sistema")
    for cuenta, estado in ((reciente, EstadoCuenta.DESACTIVADA), (activa, EstadoCuenta.ACTIVA)):
        cuenta.refresh_from_db()
        assert cuenta.estado == estado
    assert libro.read_text(encoding="utf-8").startswith(f"{vencida.pk};ANONIMIZADA;")
    # Idempotente y sin borrar la fila (CHG-DB-002).
    assert services.anonimizar_cuentas_vencidas() == 0
    assert CuentaStaff.objects.filter(pk=vencida.pk).exists()


def test_AC_TKT005_05_anonimizar_ahora_del_admin_sigue_igual(libro):
    admin = crear_staff("admin.panel", rol=RolCuenta.ADMINISTRADOR).cuenta
    objetivo = _desactivada("objetivo.cuatro", 1)
    services.anonimizar_cuenta(admin, objetivo.pk)
    evento = _eventos(AccionAuditoria.CUENTA_ANONIMIZAR, objetivo)[0]
    assert (evento.actor_id, evento.actor_etiqueta) == (admin.pk, "admin.panel")


# ---------------------------------------------------------------------------
# reaplicar_libro_anonimizaciones
# ---------------------------------------------------------------------------
def test_AC_TKT005_05_reaplica_el_libro_de_forma_idempotente(libro, logs_json):
    solo_desactivada = crear_staff("restaurada.activa").cuenta
    anonimizada = crear_staff("restaurada.anonimizable").cuenta
    ya_anonimizada = _desactivada("ya.anonimizada", 40)
    services.anonimizar_cuentas_vencidas()
    libro.write_text(
        f"{solo_desactivada.pk};DESACTIVADA;2026-09-01T10:00:00Z\n"
        f"{anonimizada.pk};DESACTIVADA;2026-08-01T10:00:00Z\n"
        f"{anonimizada.pk};ANONIMIZADA;2026-09-02T10:00:00Z\n"
        f"{ya_anonimizada.pk};ANONIMIZADA;2026-09-03T10:00:00Z\n"
        "999999999;ANONIMIZADA;2026-09-03T10:00:00Z\n"
        "linea con usuario@correo.example no valida\n"
        "\n",
        encoding="utf-8",
    )
    resultado = services.reaplicar_libro_anonimizaciones()
    assert resultado == services.ResultadoLibro(
        desactivadas=2, anonimizadas=1, lineas_invalidas=1, cuentas_inexistentes=1
    )
    solo_desactivada.refresh_from_db()
    assert solo_desactivada.estado == EstadoCuenta.DESACTIVADA
    assert solo_desactivada.desactivado_en == datetime(2026, 9, 1, 10, tzinfo=UTC)
    assert not solo_desactivada.has_usable_password()
    anonimizada.refresh_from_db()
    assert anonimizada.estado == EstadoCuenta.ANONIMIZADA
    assert anonimizada.usuario is None
    desactivar = _eventos(AccionAuditoria.CUENTA_DESACTIVAR, solo_desactivada)[0]
    assert (desactivar.actor_id, desactivar.actor_etiqueta) == (None, "sistema")
    # Segunda pasada: nada que hacer.
    segunda = services.reaplicar_libro_anonimizaciones()
    assert (segunda.desactivadas, segunda.anonimizadas) == (0, 0)
    texto = logs_json.texto()
    assert "restaurada" not in texto
    assert "usuario@correo" not in texto


def test_AC_TKT005_05_libro_inexistente_no_hace_nada(libro):
    assert not libro.exists()
    assert services.reaplicar_libro_anonimizaciones() == services.ResultadoLibro(0, 0, 0, 0)


# ---------------------------------------------------------------------------
# purgar_eventos_caducados
# ---------------------------------------------------------------------------
def test_AC_TKT005_05_purga_auditoria_mayor_de_365_dias():
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO app.evento_auditoria (ocurrido_en, actor_etiqueta, accion, resultado) "
            "VALUES (%s, 'sistema', 'CREAR', 'EXITO'), (%s, 'sistema', 'CREAR', 'EXITO') "
            "RETURNING id",
            [timezone.now() - timedelta(days=366), timezone.now() - timedelta(days=300)],
        )
        antiguo, reciente = (fila[0] for fila in cursor.fetchall())
    assert purgar_eventos_caducados() == 1
    assert not EventoAuditoria.objects.filter(pk=antiguo).exists()
    assert EventoAuditoria.objects.filter(pk=reciente).exists()
    assert purgar_eventos_caducados() == 0


# ---------------------------------------------------------------------------
# Comandos del planificador y de la restauración
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("nombre", "tarea"),
    [
        ("anonimizar_cuentas", TareaProgramada.ANONIMIZACION_CUENTAS),
        ("reaplicar_anonimizaciones", TareaProgramada.REAPLICAR_ANONIMIZACIONES),
        ("purgar_auditoria", TareaProgramada.PURGA_AUDITORIA),
    ],
)
def test_AC_TKT005_05_comandos_de_sistema_con_registro(libro, nombre, tarea):
    _desactivada("vencida.cmd", 45)
    for _ in range(2):
        call_command(nombre, stdout=io.StringIO())
    registros = list(OpsEjecucionTarea.objects.filter(tarea=tarea).order_by("id"))
    assert [r.resultado for r in registros] == [ResultadoTarea.EXITO] * 2
    if nombre == "anonimizar_cuentas":
        assert [r.detalle for r in registros] == ["cuentas=1", "cuentas=0"]


def test_AC_TKT005_05_post_restore_encuentra_los_comandos():
    # scripts/ops/post-restore-local.sh los busca en `manage.py help --commands`.
    disponibles = set(get_commands())
    assert {
        "reaplicar_anonimizaciones",
        "anonimizar_cuentas",
        "purgar_auditoria",
        "purgar_sesiones",
        "reindexar_busqueda",
        "verificar_busqueda",
        "purgar_ops",
    } <= disponibles


# ---------------------------------------------------------------------------
# QA-TKT005-03 (DEC-AUTO-913): REACTIVADA en el libro, último evento gana, último Administrador
# ---------------------------------------------------------------------------
def test_QA_TKT005_03_desactivar_reactivar_reaplicar_y_31_dias_sigue_activa(
    libro, django_capture_on_commit_callbacks
):
    admin = crear_staff("admin.qa", rol=RolCuenta.ADMINISTRADOR).cuenta
    editor = crear_staff("editor.qa").cuenta
    with django_capture_on_commit_callbacks(execute=True):
        services.desactivar_cuenta(admin, editor.pk)
    with django_capture_on_commit_callbacks(execute=True):
        services.reactivar_cuenta(admin, editor.pk)
    eventos = [linea.split(";")[1] for linea in libro.read_text(encoding="utf-8").splitlines()]
    assert eventos == ["DESACTIVADA", "REACTIVADA"]
    resultado = services.reaplicar_libro_anonimizaciones()
    assert (resultado.desactivadas, resultado.anonimizadas) == (0, 0)
    assert services.anonimizar_cuentas_vencidas(timezone.now() + timedelta(days=31)) == 0
    editor.refresh_from_db()
    assert editor.estado in (EstadoCuenta.PENDIENTE_ACTIVACION, EstadoCuenta.ACTIVA)
    assert editor.usuario == "editor.qa"


def test_QA_TKT005_03_ultimo_evento_gana(libro):
    reactivada = crear_staff("vuelve.a.desactivar").cuenta
    libro.write_text(
        f"{reactivada.pk};DESACTIVADA;2026-08-01T10:00:00Z\n"
        f"{reactivada.pk};REACTIVADA;2026-08-05T10:00:00Z\n"
        f"{reactivada.pk};DESACTIVADA;2026-09-10T10:00:00Z\n",
        encoding="utf-8",
    )
    assert services.reaplicar_libro_anonimizaciones().desactivadas == 1
    reactivada.refresh_from_db()
    assert reactivada.estado == EstadoCuenta.DESACTIVADA
    assert reactivada.desactivado_en == datetime(2026, 9, 10, 10, tzinfo=UTC)


def test_QA_TKT005_03_copia_desactivada_con_reactivacion_posterior_no_se_anonimiza(libro):
    # Copia restaurada anterior a la reactivación: en la BD sigue DESACTIVADA hace > 30 días.
    cuenta = _desactivada("restaurada.reactivada", 45)
    libro.write_text(
        f"{cuenta.pk};DESACTIVADA;2026-08-01T10:00:00Z\n"
        f"{cuenta.pk};REACTIVADA;2026-08-20T10:00:00Z\n",
        encoding="utf-8",
    )
    assert services.anonimizar_cuentas_vencidas() == 0
    cuenta.refresh_from_db()
    assert cuenta.estado == EstadoCuenta.DESACTIVADA
    assert cuenta.usuario == "restaurada.reactivada"


def test_QA_TKT005_03_nunca_desactiva_al_ultimo_administrador_activo(libro, logs_json):
    unico = crear_staff("admin.unico", rol=RolCuenta.ADMINISTRADOR).cuenta
    libro.write_text(
        f"{unico.pk};DESACTIVADA;2026-09-01T10:00:00Z\n"
        f"{unico.pk};ANONIMIZADA;2026-09-02T10:00:00Z\n",
        encoding="utf-8",
    )
    resultado = services.reaplicar_libro_anonimizaciones()
    assert (resultado.desactivadas, resultado.anonimizadas, resultado.omitidas) == (0, 0, 1)
    unico.refresh_from_db()
    assert unico.estado == EstadoCuenta.ACTIVA
    assert "admin.unico" not in logs_json.texto()
    # Con otro Administrador activo, sí se reaplica.
    crear_staff("admin.otro", rol=RolCuenta.ADMINISTRADOR)
    assert services.reaplicar_libro_anonimizaciones().anonimizadas == 1
