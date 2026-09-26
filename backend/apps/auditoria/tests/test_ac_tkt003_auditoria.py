"""Auditoría inmutable y revisiones (ADR-DB-004 §1; AC-TKT003-03 y AC-TKT003-04)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta

import pytest
from django.db import DataError, IntegrityError, ProgrammingError, connection, transaction
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria, RevisionContenido
from apps.contenido.tests.fabricas import como_rol, crear_contenido, crear_cuenta, forzar_diferidas
from apps.cuentas.models import EstadoCuenta

pytestmark = pytest.mark.django_db


@contextmanager
def _falla(excepcion=IntegrityError):
    with pytest.raises(excepcion), transaction.atomic():
        yield


def _evento(**campos) -> EventoAuditoria:
    datos = {"actor_etiqueta": "sistema", "accion": "CREAR", "resultado": "EXITO"}
    datos.update(campos)
    return EventoAuditoria.objects.create(**datos)


def _envejecer(evento: EventoAuditoria, dias: int) -> None:
    """Fecha un evento en el pasado sin UPDATE (el trigger lo impediría): INSERT con fecha."""
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO app.evento_auditoria (ocurrido_en, actor_etiqueta, accion, resultado) "
            "VALUES (%s, 'sistema', 'CREAR', 'EXITO') RETURNING id",
            [timezone.now() - timedelta(days=dias)],
        )
        evento.pk = cursor.fetchone()[0]


# ---------------------------------------------------------------------------
# CHECK e IP truncada (REQ-057, DEC-AUTO-092)
# ---------------------------------------------------------------------------
def test_AC_TKT003_04_ip_truncada_solo_redes_24_o_48_y_en_autenticacion():
    evento = _evento(accion="LOGIN_OK", ip_truncada="203.0.113.0/24")
    evento.refresh_from_db()
    assert evento.ip_truncada == "203.0.113.0/24"
    _evento(accion="LOGIN_FALLIDO", ip_truncada="2001:db8:abcd::/48")
    with _falla():  # IP completa (/32)
        _evento(accion="LOGIN_OK", ip_truncada="203.0.113.7/32")
    with _falla(DataError):  # bits de host: cidr la rechaza
        _evento(accion="LOGIN_OK", ip_truncada="203.0.113.7/24")
    with _falla():  # solo en eventos de autenticación
        _evento(accion="CREAR", ip_truncada="203.0.113.0/24")
    with _falla():
        _evento(accion="ACCION_INVENTADA")
    with _falla():
        _evento(resultado="QUIZA")
    assert str(evento) == f"LOGIN_OK #{evento.pk}"


# ---------------------------------------------------------------------------
# Trigger trg_auditoria_inmutable (también frente al propietario)
# ---------------------------------------------------------------------------
def test_AC_TKT003_04_evento_inmutable_salvo_seudonimizacion():
    evento = _evento(accion="LOGIN_OK", ip_truncada="198.51.100.0/24", actor_etiqueta="ana")
    with _falla():
        EventoAuditoria.objects.filter(pk=evento.pk).update(accion="LOGOUT")
    with _falla():
        EventoAuditoria.objects.filter(pk=evento.pk).update(actor_etiqueta="otra persona")
    with _falla():
        EventoAuditoria.objects.filter(pk=evento.pk).update(ip_truncada="192.0.2.0/24")
    # La seudonimización sí está permitida.
    EventoAuditoria.objects.filter(pk=evento.pk).update(
        actor_etiqueta="Cuenta anonimizada #7", ip_truncada=None
    )


def test_AC_TKT003_04_evento_no_se_borra_antes_de_365_dias_ni_se_trunca():
    reciente = _evento()
    with _falla():
        EventoAuditoria.objects.filter(pk=reciente.pk).delete()
    forzar_diferidas("ALL")  # TRUNCATE exige no tener eventos de trigger pendientes
    with _falla(), connection.cursor() as cursor:
        cursor.execute("TRUNCATE app.evento_auditoria")
    antiguo = EventoAuditoria()
    _envejecer(antiguo, 400)
    EventoAuditoria.objects.filter(pk=antiguo.pk).delete()
    assert not EventoAuditoria.objects.filter(pk=antiguo.pk).exists()


def test_AC_TKT003_04_funciones_security_definer_de_purga_y_seudonimizacion():
    antiguo = EventoAuditoria()
    _envejecer(antiguo, 366)
    reciente = _evento()
    cuenta = crear_cuenta("persona.auditada")
    evento_cuenta = _evento(
        actor=cuenta, actor_etiqueta="persona.auditada", accion="LOGIN_OK",
        ip_truncada="198.51.100.0/24",
    )
    with como_rol("app_rw") as cursor:
        cursor.execute("SELECT app.fn_auditoria_purgar()")
        assert cursor.fetchone()[0] >= 1
        # La cuenta no está anonimizada: la función se niega.
        with _falla():
            cursor.execute("SELECT app.fn_auditoria_seudonimizar(%s)", [cuenta.pk])
    ahora = timezone.now()
    cuenta.usuario = None
    cuenta.nombre_visible = None
    cuenta.estado = EstadoCuenta.ANONIMIZADA
    cuenta.desactivado_en = ahora
    cuenta.anonimizado_en = ahora
    cuenta.password = "!inutilizable"
    cuenta.save()
    with como_rol("app_rw") as cursor:
        cursor.execute("SELECT app.fn_auditoria_purgar()")
        cursor.execute("SELECT app.fn_auditoria_seudonimizar(%s)", [cuenta.pk])
        assert cursor.fetchone()[0] == 1
        cursor.execute(
            "SELECT actor_etiqueta, ip_truncada FROM app.evento_auditoria WHERE id = %s",
            [evento_cuenta.pk],
        )
        assert cursor.fetchone() == (f"Cuenta anonimizada #{cuenta.pk}", None)
        cursor.execute("SELECT count(*) FROM app.evento_auditoria WHERE id = %s", [antiguo.pk])
        assert cursor.fetchone()[0] == 0
        cursor.execute("SELECT count(*) FROM app.evento_auditoria WHERE id = %s", [reciente.pk])
        assert cursor.fetchone()[0] == 1


# ---------------------------------------------------------------------------
# AC-TKT003-03: privilegios de app_rw (solo SELECT e INSERT)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "sentencia",
    [
        "UPDATE app.evento_auditoria SET resultado = 'FALLO'",
        "DELETE FROM app.evento_auditoria",
        "TRUNCATE app.evento_auditoria",
        "UPDATE app.revision_contenido SET motivo = 'RETIRO'",
        "DELETE FROM app.revision_contenido",
    ],
)
def test_AC_TKT003_03_app_rw_no_modifica_ni_borra_auditoria_ni_revisiones(sentencia):
    with como_rol("app_rw") as cursor, pytest.raises(ProgrammingError, match="permission denied"):
        cursor.execute(sentencia)


def test_AC_TKT003_03_app_rw_inserta_y_lee_auditoria_y_revisiones():
    contenido = crear_contenido("GUIA")
    with como_rol("app_rw") as cursor:
        cursor.execute(
            "INSERT INTO app.evento_auditoria (actor_etiqueta, accion, resultado) "
            "VALUES ('sistema', 'CREAR', 'EXITO')"
        )
        cursor.execute(
            "INSERT INTO app.revision_contenido "
            "(contenido_id, tipo_contenido, numero_revision, motivo, instantanea) "
            "VALUES (%s, 'GUIA', 1, 'PUBLICACION', '{}')",
            [contenido.pk],
        )
        cursor.execute("SELECT count(*) FROM app.revision_contenido")
        assert cursor.fetchone()[0] >= 1


def test_AC_TKT003_04_revision_numero_unico_y_str():
    contenido = crear_contenido("GUIA")
    revision = RevisionContenido.objects.create(
        contenido=contenido,
        tipo_contenido="GUIA",
        numero_revision=1,
        motivo="PUBLICACION",
        instantanea={"titulo": contenido.titulo},
    )
    assert str(revision) == f"Revisión 1 del contenido #{contenido.pk}"
    with _falla():
        RevisionContenido.objects.create(
            contenido=contenido,
            tipo_contenido="GUIA",
            numero_revision=1,
            motivo="ACTUALIZACION",
            instantanea={},
        )
    with _falla():
        RevisionContenido.objects.create(
            contenido=contenido,
            tipo_contenido="GUIA",
            numero_revision=0,
            motivo="ACTUALIZACION",
            instantanea={},
        )
