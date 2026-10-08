"""TKT-034: almacén de sesiones del panel sobre `sesion_panel` (apps.cuentas.sesiones).

Comportamiento del SessionStore propio (ADR-DB-005 §2, DEC-AUTO-089) más allá del flujo HTTP de
TKT-004: columnas cuenta/autenticado_en, alta y actualización, rotación del identificador,
colisión de claves, invalidación concurrente (logout o desactivación entre peticiones), errores
de la BD y limpieza de sesiones caducadas.
Trazabilidad: TKT-OPS-022 (módulo crítico > 95 %), Skill_Backend §8; STATE-004, THREAT-002/025,
AC-107.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest
from django.contrib.sessions.backends.base import CreateError, UpdateError
from django.db import IntegrityError, OperationalError, connection
from django.utils import timezone

from apps.cuentas.models import CuentaStaff, SesionPanel
from apps.cuentas.sesiones import CLAVE_AUTENTICADO_EN, CLAVE_CUENTA, SessionStore
from apps.cuentas.tests.conftest import Staff

pytestmark = pytest.mark.django_db


def _sesion_de(cuenta: CuentaStaff, autenticado_en: datetime | None = None) -> SessionStore:
    """Sesión autenticada guardada con save() sin clave previa (camino de alta)."""
    tienda = SessionStore()
    tienda[CLAVE_CUENTA] = cuenta.pk
    tienda[CLAVE_AUTENTICADO_EN] = (autenticado_en or timezone.now()).isoformat()
    tienda.save()
    return tienda


def _fila(tienda: SessionStore) -> SesionPanel:
    assert tienda.session_key is not None
    return SesionPanel.objects.get(session_key=tienda.session_key)


# ---------------------------------------------------------------------------
# Alta: columnas propias de sesion_panel
# ---------------------------------------------------------------------------
def test_TKT034_el_modelo_del_almacen_es_sesion_panel():
    assert SessionStore.get_model_class() is SesionPanel
    assert SesionPanel.get_session_store_class() is SessionStore


def test_TKT034_guardar_sin_clave_crea_la_fila_con_cuenta_y_autenticado_en(editora: Staff):
    autenticado_en = timezone.now() - timedelta(minutes=5)
    tienda = SessionStore()
    assert tienda.session_key is None
    tienda[CLAVE_CUENTA] = editora.cuenta.pk
    tienda[CLAVE_AUTENTICADO_EN] = autenticado_en.isoformat()

    tienda.save()

    assert tienda.session_key is not None
    fila = _fila(tienda)
    assert fila.cuenta_id == editora.cuenta.pk
    assert fila.autenticado_en == autenticado_en
    assert fila.creado_en is not None
    assert fila.expire_date > timezone.now()
    # El contenido va firmado en session_data y se recupera íntegro.
    assert fila.get_decoded()[CLAVE_CUENTA] == editora.cuenta.pk
    # La cuenta ve sus sesiones por la relación (invalidación por cuenta, AC-107).
    assert list(editora.cuenta.sesiones.values_list("session_key", flat=True)) == [
        tienda.session_key
    ]


def test_TKT034_sesion_anonima_guarda_cuenta_y_autenticado_en_nulos():
    tienda = SessionStore()
    tienda["csrf_previo"] = "x"
    tienda.save()

    fila = _fila(tienda)
    assert fila.cuenta_id is None
    assert fila.autenticado_en is None


@pytest.mark.parametrize("valor", ["7", 7.0, None, [7]], ids=["texto", "decimal", "nulo", "lista"])
def test_TKT034_un_id_de_cuenta_no_entero_no_asocia_la_sesion(editora: Staff, valor: Any):
    tienda = SessionStore()
    tienda[CLAVE_CUENTA] = valor
    tienda[CLAVE_AUTENTICADO_EN] = ""
    tienda.save()

    fila = _fila(tienda)
    assert fila.cuenta_id is None
    assert fila.autenticado_en is None  # cadena vacía = sin marca de autenticación


def test_TKT034_cargar_por_clave_recupera_los_datos(editora: Staff):
    tienda = _sesion_de(editora.cuenta)
    otra = SessionStore(session_key=tienda.session_key)
    assert otra[CLAVE_CUENTA] == editora.cuenta.pk
    assert otra.exists(tienda.session_key)


# ---------------------------------------------------------------------------
# Actualización
# ---------------------------------------------------------------------------
def test_TKT034_actualizar_refleja_cuenta_y_marca_y_conserva_creado_en(editora: Staff):
    tienda = SessionStore()
    tienda["csrf_previo"] = "x"
    tienda.save()
    antiguo = timezone.now() - timedelta(days=1)
    SesionPanel.objects.filter(session_key=tienda.session_key).update(creado_en=antiguo)

    autenticado_en = timezone.now()
    tienda[CLAVE_CUENTA] = editora.cuenta.pk
    tienda[CLAVE_AUTENTICADO_EN] = autenticado_en.isoformat()
    clave = tienda.session_key
    tienda.save()

    assert tienda.session_key == clave  # actualización, no alta
    fila = _fila(tienda)
    assert fila.cuenta_id == editora.cuenta.pk
    assert fila.autenticado_en == autenticado_en
    assert fila.creado_en == antiguo  # creado_en no está entre los campos actualizables
    assert SesionPanel.objects.count() == 1


def test_TKT034_quitar_la_cuenta_de_la_sesion_desasocia_la_fila(editora: Staff):
    tienda = _sesion_de(editora.cuenta)
    del tienda[CLAVE_CUENTA]
    del tienda[CLAVE_AUTENTICADO_EN]
    tienda.save()

    fila = _fila(tienda)
    assert fila.cuenta_id is None
    assert fila.autenticado_en is None


# ---------------------------------------------------------------------------
# Rotación del identificador (fijación de sesión, THREAT-002)
# ---------------------------------------------------------------------------
def test_TKT034_rotar_cambia_la_clave_borra_la_anterior_y_conserva_las_columnas(editora: Staff):
    autenticado_en = timezone.now() - timedelta(hours=1)
    tienda = _sesion_de(editora.cuenta, autenticado_en)
    anterior = tienda.session_key

    tienda.cycle_key()

    assert tienda.session_key != anterior
    assert not SesionPanel.objects.filter(session_key=anterior).exists()
    fila = _fila(tienda)
    assert fila.cuenta_id == editora.cuenta.pk
    # La rotación no reinicia la expiración absoluta de 12 h.
    assert fila.autenticado_en == autenticado_en
    assert SesionPanel.objects.count() == 1


def test_TKT034_una_colision_de_clave_reintenta_con_otra_sin_pisar_la_existente(
    editora: Staff, admin: Staff, monkeypatch: pytest.MonkeyPatch
):
    existente = _sesion_de(editora.cuenta)
    claves = iter([existente.session_key, "clave0nueva0tkt034sesionpanel0001"])
    monkeypatch.setattr(SessionStore, "_get_new_session_key", lambda self: next(claves))

    nueva = SessionStore()
    nueva[CLAVE_CUENTA] = admin.cuenta.pk
    nueva.create()

    assert nueva.session_key == "clave0nueva0tkt034sesionpanel0001"
    assert _fila(existente).cuenta_id == editora.cuenta.pk  # la original queda intacta
    assert _fila(existente).get_decoded()[CLAVE_CUENTA] == editora.cuenta.pk
    assert _fila(nueva).cuenta_id == admin.cuenta.pk


def test_TKT034_crear_con_una_clave_ya_usada_lanza_create_error(editora: Staff, admin: Staff):
    existente = _sesion_de(editora.cuenta)
    intrusa = SessionStore(session_key=existente.session_key)
    intrusa[CLAVE_CUENTA] = admin.cuenta.pk

    with pytest.raises(CreateError) as error:
        intrusa.save(must_create=True)

    assert isinstance(error.value.__cause__, IntegrityError)
    fila = _fila(existente)
    assert fila.cuenta_id == editora.cuenta.pk
    assert fila.get_decoded()[CLAVE_CUENTA] == editora.cuenta.pk


# ---------------------------------------------------------------------------
# Invalidación (logout, desactivación, restablecimiento) y errores de la BD
# ---------------------------------------------------------------------------
def test_TKT034_guardar_una_sesion_invalidada_lanza_update_error_y_no_la_resucita(
    editora: Staff,
):
    tienda = _sesion_de(editora.cuenta)
    clave = tienda.session_key
    # Otra petición cierra todas las sesiones de la cuenta mientras esta seguía en curso.
    editora.cuenta.sesiones.all().delete()
    tienda["panel_ultima_actividad"] = timezone.now().isoformat()

    with pytest.raises(UpdateError):
        tienda.save()

    assert not SesionPanel.objects.filter(session_key=clave).exists()


def test_TKT034_cerrar_la_sesion_la_borra_del_servidor(editora: Staff):
    tienda = _sesion_de(editora.cuenta)
    clave = tienda.session_key

    tienda.flush()

    assert tienda.session_key is None
    assert not SesionPanel.objects.filter(session_key=clave).exists()
    assert not SessionStore().exists(clave)


def test_TKT034_una_sesion_manipulada_en_la_bd_se_descarta(editora: Staff):
    tienda = _sesion_de(editora.cuenta)
    fila = _fila(tienda)
    datos, firma = fila.session_data.rsplit(":", 1)
    SesionPanel.objects.filter(pk=fila.pk).update(session_data=f"{datos}:{firma[::-1]}")

    recargada = SessionStore(session_key=tienda.session_key)
    # Firma inválida: la sesión se trata como vacía (no autentica a nadie).
    assert CLAVE_CUENTA not in recargada


def test_TKT034_actualizar_con_una_cuenta_inexistente_propaga_integrity_error(editora: Staff):
    tienda = SessionStore()
    tienda["csrf_previo"] = "x"
    tienda.save()
    with connection.cursor() as cursor:
        # La FK es diferible: se comprueba ya, como al confirmar la transacción de la petición.
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    tienda[CLAVE_CUENTA] = editora.cuenta.pk + 100_000

    with pytest.raises(IntegrityError):
        tienda.save()

    # La actualización se revierte (savepoint): la fila conserva su estado anterior.
    assert _fila(tienda).cuenta_id is None


def test_TKT034_un_error_de_bd_al_crear_se_propaga_sin_reintentos(
    editora: Staff, monkeypatch: pytest.MonkeyPatch
):
    intentos: list[bool] = []

    def caida(self: SesionPanel, *args: Any, **kwargs: Any) -> None:
        intentos.append(kwargs["force_insert"])
        raise OperationalError("conexión con la BD perdida")

    monkeypatch.setattr(SesionPanel, "save", caida)
    tienda = SessionStore()
    tienda[CLAVE_CUENTA] = editora.cuenta.pk

    with pytest.raises(OperationalError):
        tienda.create()

    # No se confunde con una colisión de clave (no se reintenta en bucle).
    assert intentos == [True]


def test_TKT034_un_error_de_bd_al_actualizar_se_informa_como_update_error(
    editora: Staff, monkeypatch: pytest.MonkeyPatch
):
    tienda = _sesion_de(editora.cuenta)

    def caida(self: SesionPanel, *args: Any, **kwargs: Any) -> None:
        raise OperationalError("conexión con la BD perdida")

    monkeypatch.setattr(SesionPanel, "save", caida)
    tienda["panel_ultima_actividad"] = timezone.now().isoformat()

    with pytest.raises(UpdateError) as error:
        tienda.save()
    assert isinstance(error.value.__cause__, OperationalError)


# ---------------------------------------------------------------------------
# Expiración
# ---------------------------------------------------------------------------
def test_TKT034_una_sesion_caducada_no_se_carga_y_se_limpia(editora: Staff, admin: Staff):
    caducada = _sesion_de(editora.cuenta)
    vigente = _sesion_de(admin.cuenta)
    SesionPanel.objects.filter(session_key=caducada.session_key).update(
        expire_date=timezone.now() - timedelta(seconds=1)
    )

    recargada = SessionStore(session_key=caducada.session_key)
    assert CLAVE_CUENTA not in recargada  # caducada: se trata como vacía
    assert recargada.session_key is None  # y no se reutiliza su identificador

    SessionStore.clear_expired()

    assert list(SesionPanel.objects.values_list("session_key", flat=True)) == [vigente.session_key]
