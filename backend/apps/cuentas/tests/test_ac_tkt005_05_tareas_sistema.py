"""AC-TKT005-05 y QA-TKT005-03: tareas del sistema sobre cuentas y auditoría con el libro v2.

Fuente: ADR-DB-004 §2 y §4.1-§4.5, DB_HANDOFF v1.3 pruebas_obligatorias "Libro v2" (CHG-DB-003,
DEC-AUTO-260..264). "Restaurar una copia" se simula devolviendo la fila de la cuenta al estado que
tenía en la copia; el libro (volumen vivo) conserva todos los eventos.
"""

from __future__ import annotations

import io
import multiprocessing
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from django.core.management import call_command, get_commands
from django.core.management.base import CommandError
from django.db import connection
from django.test import override_settings
from django.utils import timezone

from apps.auditoria.models import AccionAuditoria, EventoAuditoria
from apps.auditoria.services import purgar_eventos_caducados
from apps.core.exceptions import ErrorApi
from apps.cuentas import libro, services
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

REGEX_LINEA = re.compile(
    r"^[1-9][0-9]{0,18};(DESACTIVADA|REACTIVADA|ANONIMIZADA);"
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
solo_posix = pytest.mark.skipif(os.name != "posix", reason="flock/O_NOFOLLOW/permisos POSIX")
T0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)


@pytest.fixture
def admin():
    return crear_staff("admin.libro", rol=RolCuenta.ADMINISTRADOR).cuenta


def _lineas(ruta: Path) -> list[str]:
    return ruta.read_text(encoding="utf-8").splitlines() if ruta.exists() else []


def _escribir(ruta: Path, *lineas: str, final: str = "\n") -> None:
    ruta.write_bytes(("\n".join(lineas) + final).encode("utf-8"))
    if os.name == "posix":
        ruta.chmod(0o640)


def _f(momento: datetime) -> str:
    return momento.strftime("%Y-%m-%dT%H:%M:%SZ")


def _restaurar(cuenta: CuentaStaff, **estado) -> None:
    """Devuelve la fila al estado de la copia (la restauración no toca el libro)."""
    CuentaStaff.objects.filter(pk=cuenta.pk).update(**estado)
    cuenta.refresh_from_db()


def _desactivada(usuario: str, desactivado_en: datetime) -> CuentaStaff:
    cuenta = crear_staff(usuario, estado=EstadoCuenta.DESACTIVADA).cuenta
    _restaurar(cuenta, desactivado_en=desactivado_en)
    CuentaCodigoRecuperacion.objects.create(cuenta=cuenta, hash_codigo="h" * 64)
    sesion = SessionStore()
    sesion.create()
    SesionPanel.objects.filter(session_key=sesion.session_key).update(cuenta=cuenta)
    return cuenta


def _eventos(accion: str, cuenta: CuentaStaff) -> list[EventoAuditoria]:
    return list(EventoAuditoria.objects.filter(accion=accion, entidad_id=cuenta.pk))


def _comando(nombre: str, *args: str) -> str:
    salida = io.StringIO()
    call_command(nombre, *args, stdout=salida)
    return salida.getvalue()


def _registro(tarea: str) -> OpsEjecucionTarea:
    return OpsEjecucionTarea.objects.filter(tarea=tarea).order_by("-id").first()


# ---------------------------------------------------------------------------
# Escenario de QA-TKT005-03 (obligatorio)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("estado_copia", [EstadoCuenta.ACTIVA, EstadoCuenta.PENDIENTE_ACTIVACION])
def test_QA_TKT005_03_desactivar_reactivar_copia_restaurar_31_dias_sigue_igual(
    admin, libro_anonimizaciones, estado_copia
):
    editor = crear_staff("editor.qa", estado=estado_copia).cuenta
    services.desactivar_cuenta(admin, editor.pk)
    services.reactivar_cuenta(admin, editor.pk)
    assert [linea.split(";")[1] for linea in _lineas(libro_anonimizaciones)] == [
        "DESACTIVADA",
        "REACTIVADA",
    ]
    tamano = libro_anonimizaciones.stat().st_size
    _restaurar(editor, estado=estado_copia, desactivado_en=None)

    reaplicado = services.reaplicar_libro_anonimizaciones()
    anonimizado = services.anonimizar_cuentas_vencidas(timezone.now() + timedelta(days=31))

    assert (reaplicado.desactivadas, reaplicado.anonimizadas) == ([], [])
    assert anonimizado.anonimizadas == []
    editor.refresh_from_db()
    assert (editor.estado, editor.usuario, editor.desactivado_en) == (
        estado_copia,
        "editor.qa",
        None,
    )
    assert editor.nombre_visible == "Nombre de editor.qa"
    assert _eventos(AccionAuditoria.CUENTA_ANONIMIZAR, editor) == []
    assert libro_anonimizaciones.stat().st_size == tamano


# ---------------------------------------------------------------------------
# Escritura (§4.2)
# ---------------------------------------------------------------------------
def test_libro_v2_escritura_una_linea_por_transicion(admin, libro_anonimizaciones):
    editor = crear_staff("editor.lineas").cuenta
    services.desactivar_cuenta(admin, editor.pk)
    editor.refresh_from_db()
    services.reactivar_cuenta(admin, editor.pk)
    services.desactivar_cuenta(admin, editor.pk)
    services.anonimizar_cuenta(admin, editor.pk)
    vencida = _desactivada("vencida.lineas", timezone.now() - timedelta(days=40))
    services.anonimizar_cuentas_vencidas()
    lineas = _lineas(libro_anonimizaciones)
    assert all(REGEX_LINEA.match(linea) for linea in lineas), lineas
    assert [linea.split(";")[:2] for linea in lineas] == [
        [str(editor.pk), "DESACTIVADA"],
        [str(editor.pk), "REACTIVADA"],
        [str(editor.pk), "DESACTIVADA"],
        [str(editor.pk), "ANONIMIZADA"],
        [str(vencida.pk), "ANONIMIZADA"],
    ]
    # En DESACTIVADA, la fecha es desactivado_en truncado a segundos.
    assert lineas[0].split(";")[2] == libro.fecha_libro(editor.desactivado_en)


def test_libro_v2_sin_libro_escribible_la_operacion_se_deshace(admin, tmp_path, logs_json):
    ocupado = tmp_path / "es-un-fichero"
    ocupado.write_text("x", encoding="utf-8")
    editor = crear_staff("editor.sin.libro").cuenta
    sesion = SessionStore()
    sesion.create()
    SesionPanel.objects.filter(session_key=sesion.session_key).update(cuenta=editor)
    with override_settings(LIBRO_ANONIMIZACIONES_PATH=str(ocupado / "libro.log")):
        with pytest.raises(libro.LibroNoEscrito):
            services.desactivar_cuenta(admin, editor.pk)
        editor.refresh_from_db()
        assert editor.estado == EstadoCuenta.ACTIVA
        assert SesionPanel.objects.filter(cuenta=editor).exists()
        assert _eventos(AccionAuditoria.CUENTA_DESACTIVAR, editor) == []
        desactivada = _desactivada("ya.desactivada", timezone.now() - timedelta(days=1))
        for operacion in (services.reactivar_cuenta, services.anonimizar_cuenta):
            with pytest.raises(libro.LibroNoEscrito):
                operacion(admin, desactivada.pk)
            desactivada.refresh_from_db()
            assert desactivada.estado == EstadoCuenta.DESACTIVADA
    assert "libro_anonimizaciones_no_escrito" in logs_json.texto()
    assert "editor.sin.libro" not in logs_json.texto()


def test_libro_v2_si_falla_rule_015_no_se_escribe_linea(admin, libro_anonimizaciones):
    otro = crear_staff("admin.otro", rol=RolCuenta.ADMINISTRADOR, estado=EstadoCuenta.DESACTIVADA)
    with pytest.raises(ErrorApi) as error:
        services.desactivar_cuenta(otro.cuenta, admin.pk)
    assert error.value.codigo == "ultimo_administrador"
    assert _lineas(libro_anonimizaciones) == []


def test_libro_v2_reparacion_de_cola_sin_salto_de_linea(admin, libro_anonimizaciones):
    editor = crear_staff("editor.reparacion").cuenta
    _escribir(libro_anonimizaciones, "12;DESACTIVADA;2026-0", final="")
    services.desactivar_cuenta(admin, editor.pk)
    lineas = _lineas(libro_anonimizaciones)
    assert lineas[0] == "12;DESACTIVADA;2026-0"
    assert lineas[1].startswith("#REPARACION;")
    assert lineas[2].startswith(f"{editor.pk};DESACTIVADA;")
    lectura = libro.leer()
    assert lectura.avisos == ["LINEA_REPARADA:1"]
    assert lectura.cuentas[editor.pk].ultimo == libro.DESACTIVADA


@solo_posix
def test_libro_v2_modo_0640_y_enlace_simbolico_rechazado(admin, libro_anonimizaciones, tmp_path):
    editor = crear_staff("editor.modo").cuenta
    services.desactivar_cuenta(admin, editor.pk)
    assert libro_anonimizaciones.stat().st_mode & 0o777 == 0o640
    destino = tmp_path / "otro.log"
    destino.write_text("", encoding="utf-8")
    enlace = tmp_path / "enlace.log"
    enlace.symlink_to(destino)
    with override_settings(LIBRO_ANONIMIZACIONES_PATH=str(enlace)):
        with pytest.raises(libro.LibroNoEscrito):
            services.reactivar_cuenta(admin, editor.pk)
        with pytest.raises(libro.ErrorLibro) as error:
            libro.leer()
        assert error.value.codigo == libro.LIBRO_ILEGIBLE
    assert destino.read_text(encoding="utf-8") == ""


def _escribir_muchas(ruta: str, cuenta_id: int, cantidad: int) -> None:
    for _ in range(cantidad):
        momento = datetime.now(UTC)
        libro.anadir_linea(Path(ruta), f"{cuenta_id};DESACTIVADA;{_f(momento)}\n", momento)


@solo_posix
def test_libro_v2_dos_procesos_concurrentes_400_lineas_validas(libro_anonimizaciones):
    contexto = multiprocessing.get_context("fork")
    procesos = [
        contexto.Process(target=_escribir_muchas, args=(str(libro_anonimizaciones), n, 200))
        for n in (1, 2)
    ]
    for proceso in procesos:
        proceso.start()
    for proceso in procesos:
        proceso.join(60)
        assert proceso.exitcode == 0
    lineas = _lineas(libro_anonimizaciones)
    assert len(lineas) == 400
    assert all(REGEX_LINEA.match(linea) for linea in lineas)


def test_libro_v2_la_relectura_no_escribe(admin, libro_anonimizaciones):
    editor = crear_staff("editor.relectura").cuenta
    services.desactivar_cuenta(admin, editor.pk)
    _restaurar(editor, estado=EstadoCuenta.ACTIVA, desactivado_en=None)
    tamano = libro_anonimizaciones.stat().st_size
    assert services.reaplicar_libro_anonimizaciones().desactivadas == [editor.pk]
    assert libro_anonimizaciones.stat().st_size == tamano


# ---------------------------------------------------------------------------
# Relectura (a)-(i) (§4.3)
# ---------------------------------------------------------------------------
def test_libro_v2_a_desactivada_tras_la_copia_plazo_desde_la_fecha_del_libro(
    admin, libro_anonimizaciones
):
    editor = crear_staff("rel.a").cuenta
    _escribir(libro_anonimizaciones, f"{editor.pk};DESACTIVADA;{_f(T0)}")
    assert services.reaplicar_libro_anonimizaciones().desactivadas == [editor.pk]
    editor.refresh_from_db()
    assert (editor.estado, editor.desactivado_en) == (EstadoCuenta.DESACTIVADA, T0)
    desactivar = _eventos(AccionAuditoria.CUENTA_DESACTIVAR, editor)[0]
    assert (desactivar.actor_id, desactivar.actor_etiqueta) == (None, "sistema")
    assert services.anonimizar_cuentas_vencidas(T0 + timedelta(days=29)).anonimizadas == []
    assert services.anonimizar_cuentas_vencidas(T0 + timedelta(days=31)).anonimizadas == [editor.pk]


def test_libro_v2_b_desactivacion_vigente_tras_reactivar_y_desactivar(admin, libro_anonimizaciones):
    editor = _desactivada("rel.b", T0)  # copia: DESACTIVADA en t0
    t1 = T0 + timedelta(days=10)
    _escribir(
        libro_anonimizaciones,
        f"{editor.pk};DESACTIVADA;{_f(T0)}",
        f"{editor.pk};REACTIVADA;{_f(T0 + timedelta(days=2))}",
        f"{editor.pk};DESACTIVADA;{_f(t1)}",
    )
    assert services.reaplicar_libro_anonimizaciones().alineadas == [editor.pk]
    editor.refresh_from_db()
    assert editor.desactivado_en == t1
    assert services.anonimizar_cuentas_vencidas(T0 + timedelta(days=31)).anonimizadas == []
    assert services.anonimizar_cuentas_vencidas(t1 + timedelta(days=31)).anonimizadas == [editor.pk]


def test_libro_v2_c_reactivada_tras_la_copia_no_se_reproduce_ni_se_anonimiza(
    admin, libro_anonimizaciones
):
    editor = _desactivada("rel.c", T0)
    _escribir(
        libro_anonimizaciones,
        f"{editor.pk};DESACTIVADA;{_f(T0)}",
        f"{editor.pk};REACTIVADA;{_f(T0 + timedelta(days=3))}",
    )
    reaplicado = services.reaplicar_libro_anonimizaciones()
    assert reaplicado.avisos() == {"REACTIVADA_NO_REPRODUCIDA": [editor.pk]}
    editor.refresh_from_db()
    assert editor.estado == EstadoCuenta.DESACTIVADA
    resultado = services.anonimizar_cuentas_vencidas(T0 + timedelta(days=31))
    assert (resultado.anonimizadas, resultado.omitidas_reactivada) == ([], [editor.pk])
    _comando("anonimizar_cuentas")
    assert "OMITIDA_REACTIVADA=1" in _registro(TareaProgramada.ANONIMIZACION_CUENTAS).detalle


def test_libro_v2_d_anonimizada_tras_la_copia(admin, libro_anonimizaciones):
    editor = crear_staff("rel.d").cuenta
    EventoAuditoria.objects.create(
        actor=editor, actor_etiqueta="rel.d", accion="LOGIN_OK", resultado="EXITO"
    )
    _escribir(
        libro_anonimizaciones,
        f"{editor.pk};DESACTIVADA;{_f(T0)}",
        f"{editor.pk};ANONIMIZADA;{_f(T0 + timedelta(days=1))}",
    )
    assert services.reaplicar_libro_anonimizaciones().anonimizadas == [editor.pk]
    editor.refresh_from_db()
    assert (editor.estado, editor.usuario, editor.desactivado_en) == (
        EstadoCuenta.ANONIMIZADA,
        None,
        T0,
    )
    assert not EventoAuditoria.objects.filter(actor_etiqueta="rel.d").exists()


def test_libro_v2_e_f_ultimo_administrador_nunca_se_toca(libro_anonimizaciones, logs_json):
    unico = crear_staff("admin.unico", rol=RolCuenta.ADMINISTRADOR).cuenta
    for evento in ("DESACTIVADA", "ANONIMIZADA"):
        _escribir(libro_anonimizaciones, f"{unico.pk};{evento};{_f(T0)}")
        salida = _comando("reaplicar_anonimizaciones")
        assert f"OMITIDA_ULTIMO_ADMIN=1[{unico.pk}]" in salida
        unico.refresh_from_db()
        assert unico.estado == EstadoCuenta.ACTIVA
    assert "admin.unico" not in logs_json.texto()
    crear_staff("admin.nuevo", rol=RolCuenta.ADMINISTRADOR)
    _escribir(libro_anonimizaciones, f"{unico.pk};DESACTIVADA;{_f(T0)}")
    assert services.reaplicar_libro_anonimizaciones().desactivadas == [unico.pk]


def test_libro_v2_g_h_id_desconocido_e_idempotencia(admin, libro_anonimizaciones):
    editor = crear_staff("rel.h").cuenta
    _escribir(
        libro_anonimizaciones,
        "999999999;ANONIMIZADA;2026-08-01T10:00:00Z",
        f"{editor.pk};DESACTIVADA;{_f(T0)}",
    )
    primera = services.reaplicar_libro_anonimizaciones()
    assert (primera.inexistentes, primera.desactivadas) == ([999999999], [editor.pk])
    segunda = services.reaplicar_libro_anonimizaciones()
    assert (segunda.desactivadas, segunda.anonimizadas, segunda.alineadas) == ([], [], [])


def test_libro_v2_i_bd_mas_reciente_que_el_libro_inconsistente(admin, libro_anonimizaciones):
    editor = _desactivada("rel.i", T0 + timedelta(days=5))
    _escribir(libro_anonimizaciones, f"{editor.pk};DESACTIVADA;{_f(T0)}")
    assert services.reaplicar_libro_anonimizaciones().avisos() == {"INCONSISTENTE": [editor.pk]}
    editor.refresh_from_db()
    assert editor.desactivado_en == T0 + timedelta(days=5)


# ---------------------------------------------------------------------------
# Casos límite (§4.4)
# ---------------------------------------------------------------------------
def test_libro_v2_ausente(admin, libro_anonimizaciones, logs_json):
    editor = crear_staff("limite.ausente").cuenta
    with pytest.raises(CommandError, match="LIBRO_AUSENTE"):
        _comando("reaplicar_anonimizaciones")
    assert _registro(TareaProgramada.REAPLICAR_ANONIMIZACIONES).resultado == ResultadoTarea.FALLO
    assert "EXITO" in _comando("reaplicar_anonimizaciones", "--libro-vacio-confirmado")
    vencida = _desactivada("limite.vencida", timezone.now() - timedelta(days=40))
    salida = _comando("anonimizar_cuentas")
    assert "LIBRO_AUSENTE_SOLO_BD" in salida
    vencida.refresh_from_db()
    editor.refresh_from_db()
    assert (vencida.estado, editor.estado) == (EstadoCuenta.ANONIMIZADA, EstadoCuenta.ACTIVA)
    assert "libro_ausente" in logs_json.texto()


def test_libro_v2_corrupto_falla_sin_cambios_en_ambos_comandos(admin, libro_anonimizaciones):
    editor = crear_staff("limite.corrupto").cuenta
    vencida = _desactivada("limite.corrupto.vencida", timezone.now() - timedelta(days=40))
    _escribir(
        libro_anonimizaciones,
        f"{editor.pk};DESACTIVADA;{_f(T0)}",
        "linea basura",
        f"{editor.pk};REACTIVADA;{_f(T0)}",
    )
    for nombre, tarea in (
        ("reaplicar_anonimizaciones", TareaProgramada.REAPLICAR_ANONIMIZACIONES),
        ("anonimizar_cuentas", TareaProgramada.ANONIMIZACION_CUENTAS),
    ):
        with pytest.raises(CommandError, match="LIBRO_CORRUPTO lineas=2"):
            _comando(nombre)
        assert _registro(tarea).resultado == ResultadoTarea.FALLO
    for cuenta, estado in ((editor, EstadoCuenta.ACTIVA), (vencida, EstadoCuenta.DESACTIVADA)):
        cuenta.refresh_from_db()
        assert cuenta.estado == estado


def test_libro_v2_cola_truncada_y_duplicados_se_toleran(admin, libro_anonimizaciones):
    uno = crear_staff("limite.uno").cuenta
    dos = crear_staff("limite.dos").cuenta
    _escribir(
        libro_anonimizaciones,
        f"{uno.pk};DESACTIVADA;{_f(T0)}",
        f"{uno.pk};DESACTIVADA;{_f(T0)}",
        f"{dos.pk};DESACTIVADA;2026-08-0",
        final="",
    )
    lectura = libro.leer()
    assert lectura.avisos == ["COLA_INCOMPLETA:3"]
    resultado = services.reaplicar_libro_anonimizaciones()
    assert resultado.desactivadas == [uno.pk]
    dos.refresh_from_db()
    assert dos.estado == EstadoCuenta.ACTIVA


def test_libro_v2_manda_el_orden_del_fichero_no_la_fecha(admin, libro_anonimizaciones):
    editor = _desactivada("limite.orden", T0)
    _escribir(
        libro_anonimizaciones,
        f"{editor.pk};DESACTIVADA;{_f(T0 + timedelta(days=9))}",
        f"{editor.pk};REACTIVADA;{_f(T0)}",
    )
    lectura = libro.leer()
    assert lectura.cuentas[editor.pk].ultimo == libro.REACTIVADA
    assert f"FECHAS_NO_MONOTONAS:{editor.pk}" in lectura.avisos
    assert services.anonimizar_cuentas_vencidas(T0 + timedelta(days=60)).anonimizadas == []


def test_libro_v2_fecha_futura_retrasa_la_anonimizacion(admin, libro_anonimizaciones):
    ahora = timezone.now()
    futura = (ahora + timedelta(days=10)).replace(microsecond=0)
    editor = _desactivada("limite.futuro", ahora - timedelta(days=40))
    _escribir(libro_anonimizaciones, f"{editor.pk};DESACTIVADA;{_f(futura)}")
    assert f"FECHA_FUTURA:{editor.pk}" in libro.leer(ahora).avisos
    assert services.anonimizar_cuentas_vencidas(ahora).anonimizadas == []
    assert services.anonimizar_cuentas_vencidas(futura + timedelta(days=31)).anonimizadas == [
        editor.pk
    ]


@solo_posix
def test_libro_v2_escribible_por_otros_es_ilegible(admin, libro_anonimizaciones):
    _escribir(libro_anonimizaciones, f"{admin.pk};DESACTIVADA;{_f(T0)}")
    libro_anonimizaciones.chmod(0o666)
    for nombre in ("reaplicar_anonimizaciones", "anonimizar_cuentas"):
        with pytest.raises(CommandError, match="LIBRO_ILEGIBLE"):
            _comando(nombre)


# ---------------------------------------------------------------------------
# Auditoría, comandos y lock compartido
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
    _comando("purgar_auditoria")
    assert _registro(TareaProgramada.PURGA_AUDITORIA).resultado == ResultadoTarea.EXITO


def test_AC_TKT005_05_anonimizar_cuentas_registra_y_es_idempotente(libro_anonimizaciones):
    vencida = _desactivada("cmd.vencida", timezone.now() - timedelta(days=45))
    for _ in range(2):
        _comando("anonimizar_cuentas")
    registros = OpsEjecucionTarea.objects.filter(tarea=TareaProgramada.ANONIMIZACION_CUENTAS)
    detalles = list(registros.order_by("id").values_list("detalle", flat=True))
    assert detalles == [
        f"anonimizadas=1[{vencida.pk}] OMITIDA_REACTIVADA=0 LIBRO_AUSENTE_SOLO_BD",
        "anonimizadas=0 OMITIDA_REACTIVADA=0",
    ]
    evento = _eventos(AccionAuditoria.CUENTA_ANONIMIZAR, vencida)[0]
    assert (evento.actor_id, evento.actor_etiqueta) == (None, "sistema")
    assert CuentaStaff.objects.filter(pk=vencida.pk).exists()


def test_AC_TKT005_05_comandos_del_libro_comparten_lock(libro_anonimizaciones):
    datos = connection.settings_dict
    import psycopg

    with psycopg.connect(
        host=datos["HOST"],
        port=datos["PORT"],
        user=datos["USER"],
        password=datos["PASSWORD"],
        dbname=datos["NAME"],
        autocommit=True,
    ) as otra:
        otra.execute("SELECT pg_advisory_lock(hashtext('CUENTAS_LIBRO'))")
        for nombre in ("anonimizar_cuentas", "reaplicar_anonimizaciones"):
            assert "otro proceso tiene el lock" in _comando(nombre)


def test_AC_TKT005_05_post_restore_encuentra_los_comandos():
    # scripts/ops/post-restore-local.sh los busca en `manage.py help --commands`.
    assert {
        "reaplicar_anonimizaciones",
        "anonimizar_cuentas",
        "purgar_auditoria",
        "purgar_sesiones",
        "reindexar_busqueda",
        "verificar_busqueda",
        "purgar_ops",
    } <= set(get_commands())
