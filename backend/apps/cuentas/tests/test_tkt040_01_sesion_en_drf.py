"""TKT-040 (QA CHG-API-006 F-01): el guardado de la sesión del panel ya no ocurre fuera de DRF.

Antes, la renovación de la inactividad se guardaba en SessionMiddleware.process_response: un
UPDATE de `sesion_panel` que chocaba con un bloqueo (55P03/40P01/40001) o encontraba la fila
borrada lanzaba UpdateError → SessionInterrupted → 400 `validacion` (no declarado) y, en una
escritura, con el efecto ya confirmado. Ahora (ADR-API-002 §22):
- AC_TKT040_01: contención al renovar en un método no seguro → 409 `conflicto_version` (Problem
  Details, mismo cuerpo que el manejador global), sin efectos, y la sesión sigue válida.
- AC_TKT040_02: fila borrada por una invalidación concurrente → 401 `sesion_expirada` y la cookie
  se borra.
- AC_TKT040_03: GET que renueva la inactividad y vistas previas (no declaran 409) → 401.
- AC_TKT040_04: fallo al guardar la sesión DESPUÉS del efecto (rotación tras cambiar la contraseña
  o verificar el MFA, apertura tras el login): nunca 409 (el contrato lo define sin efectos y
  reintentable). Contención → la respuesta de éxito (no se aplica la renovación; log); fila ya
  borrada → 401 `sesion_expirada` (OBS-01 de la QA de CHG-API-006).
- AC_TKT040_05: logout: el borrado de la sesión va antes de la auditoría (409 sin efectos).
- AC_TKT040_06: red de seguridad del middleware: fila borrada → 401 problem+json; contención →
  la respuesta de la vista.
- AC_TKT040_07: SessionStore no repite un UPDATE de datos ya guardados en la petición.
- AC_TKT040_08: el esquema generado declara 409 en las 8 operaciones de CHG-API-006.
Los errores de BD se simulan como en la reproducción de la QA (OperationalError con SQLSTATE);
las carreras reales están en test_tkt040_02_carreras.py.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any
from unittest import mock

import pytest
from django.contrib.sessions.backends.base import UpdateError
from django.db import OperationalError
from django.db.backends.utils import CursorWrapper
from django.http import HttpResponse
from django.test import Client, RequestFactory

from apps.auditoria.models import AccionAuditoria, EventoAuditoria
from apps.cuentas import selectors
from apps.cuentas.middleware import SesionPanelMiddleware
from apps.cuentas.models import CuentaStaff, SesionPanel
from apps.cuentas.sesiones import (
    CLAVE_CUENTA,
    SessionStore,
    descartar_en_memoria,
    fallo_por_contencion,
    marcar_guardada,
)
from apps.cuentas.tests.conftest import (
    CONTRASENA,
    IP,
    Staff,
    entrar,
    post,
    problema,
)

pytestmark = pytest.mark.django_db

NUEVA = "otra-frase-de-prueba-bastante-larga-2026"


class _CausaError(Exception):
    """Error de psycopg simulado (lo que Django guarda en __cause__)."""

    diag = None

    def __init__(self, sqlstate: str) -> None:
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


def _error_bd(sqlstate: str = "55P03") -> OperationalError:
    error = OperationalError(f"simulado {sqlstate}")
    error.__cause__ = _CausaError(sqlstate)
    return error


_GUARDAR = SesionPanel.save


@contextmanager
def _actualizacion_de_sesion_falla(sqlstate: str = "55P03", *, en: int = 1) -> Iterator[list[int]]:
    """El UPDATE número `en` de una fila de sesion_panel (force_update) falla con `sqlstate`.
    Las altas (INSERT) y el resto de UPDATE se ejecutan de verdad."""
    cuenta = [0]

    def lado(self: SesionPanel, *args: Any, **kwargs: Any) -> None:
        if kwargs.get("force_update"):
            cuenta[0] += 1
            if cuenta[0] == en:
                raise _error_bd(sqlstate)
        _GUARDAR(self, *args, **kwargs)

    with mock.patch.object(SesionPanel, "save", autospec=True, side_effect=lado):
        yield cuenta


@contextmanager
def _alta_de_sesion_falla(sqlstate: str = "55P03") -> Iterator[list[int]]:
    """Toda alta (INSERT, force_insert) de una fila de sesion_panel falla con `sqlstate`
    (TKT-044: `SessionStore.create` y `crear_con_clave_nueva` se ejecutan de verdad)."""
    altas = [0]

    def lado(self: SesionPanel, *args: Any, **kwargs: Any) -> None:
        if kwargs.get("force_insert"):
            altas[0] += 1
            raise _error_bd(sqlstate)
        _GUARDAR(self, *args, **kwargs)

    with mock.patch.object(SesionPanel, "save", autospec=True, side_effect=lado):
        yield altas


_EJECUTAR = CursorWrapper.execute


@contextmanager
def _borrado_de_sesion_falla(sqlstate: str = "55P03") -> Iterator[None]:
    """El borrado sin espera de una sesión (`invalidar_clave`, TKT-044) falla con `sqlstate`
    (55P03: su fila la tiene bloqueada otra transacción). El resto de SQL se ejecuta de verdad."""

    def lado(self: CursorWrapper, sql: str, params: Any = None) -> Any:
        if sql.startswith("DELETE FROM") and "FOR UPDATE NOWAIT" in sql:
            raise _error_bd(sqlstate)
        return _EJECUTAR(self, sql, params)

    with mock.patch.object(CursorWrapper, "execute", autospec=True, side_effect=lado):
        yield


def _revocada(clave: str) -> bool:
    """La clave ya no carga como sesión aunque su fila siga (marca de revocación, TKT-044)."""
    return SessionStore(clave).load() == {}


@contextmanager
def _sesion_invalidada_en_curso(cuenta: CuentaStaff) -> Iterator[None]:
    """Otra petición borra las sesiones de la cuenta entre la lectura de la sesión y su guardado
    (la autenticación ya cargó la fila; el UPDATE encuentra 0 filas)."""
    original = selectors.cuenta_con_sesion

    def lado(cuenta_id: int) -> CuentaStaff | None:
        SesionPanel.objects.filter(cuenta_id=cuenta.pk).delete()
        return original(cuenta_id)

    with mock.patch.object(selectors, "cuenta_con_sesion", side_effect=lado):
        yield


def _cookie_borrada(respuesta: Any) -> bool:
    cookie = respuesta.cookies.get("sessionid")
    return cookie is not None and cookie.value == "" and str(cookie["max-age"]) == "0"


def _cliente(staff: Staff) -> Client:
    cliente = Client(raise_request_exception=False)
    entrar(cliente, staff)
    return cliente


def _sesiones(cuenta: CuentaStaff) -> int:
    return SesionPanel.objects.filter(cuenta_id=cuenta.pk).count()


def _eventos(accion: str, cuenta: CuentaStaff) -> int:
    return EventoAuditoria.objects.filter(accion=accion, actor_id=cuenta.pk).count()


def _sin_400(logs: Callable[[], list[dict[str, Any]]]) -> None:
    assert [linea for linea in logs() if linea.get("event") == "excepcion_no_controlada"] == []


# ---------------------------------------------------------------------------
# AC_TKT040_01: contención al renovar (método no seguro) → 409, sin efectos
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("sqlstate", ["55P03", "40P01", "40001"])
def test_AC_TKT040_01_renovar_con_la_fila_bloqueada_es_409_conflicto_version(
    editora: Staff, sqlstate: str, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    cliente = _cliente(editora)
    with _actualizacion_de_sesion_falla(sqlstate):
        respuesta = post(cliente, "/auth/sesion/renovar")
    cuerpo = problema(respuesta, 409, "conflicto_version")
    assert set(cuerpo) >= {"type", "title", "status", "detail", "code", "errors", "trace_id"}
    assert cuerpo["type"].endswith("/errors/conflicto_version")
    # La sesión sigue siendo válida (no se borra la cookie) y el reintento funciona.
    assert "sessionid" not in respuesta.cookies
    reintento = post(cliente, "/auth/sesion/renovar")
    assert reintento.status_code == 200, reintento.content
    _sin_400(logs_json)


def test_AC_TKT040_01_el_409_es_el_mismo_cuerpo_que_el_manejador_global(editora: Staff) -> None:
    """Mismo Problem Details que core.exceptions para 55P03 en una vista (TKT-035)."""
    cliente = _cliente(editora)
    with _actualizacion_de_sesion_falla("55P03"):
        cuerpo = problema(post(cliente, "/auth/sesion/renovar"), 409, "conflicto_version")
    assert cuerpo["title"] == "Conflicto de versión"
    assert cuerpo["status"] == 409
    assert cuerpo["errors"] == {}
    assert "usos" not in cuerpo
    assert "entidades_en_conflicto" not in cuerpo


def test_AC_TKT040_01_escritura_con_contencion_al_renovar_no_tiene_efectos(
    editora: Staff,
) -> None:
    """La renovación se guarda ANTES de la vista: el 409 es veraz (no se cambió la contraseña)
    y reintentar es seguro (antes: 400 validacion con la contraseña ya cambiada)."""
    cliente = _cliente(editora)
    datos = {"contrasena_actual": CONTRASENA, "contrasena_nueva": NUEVA}
    with _actualizacion_de_sesion_falla("55P03"):
        problema(post(cliente, "/auth/contrasena", datos), 409, "conflicto_version")
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.check_password(CONTRASENA)
    assert _eventos(AccionAuditoria.CAMBIO_CREDENCIAL, editora.cuenta) == 0
    respuesta = post(cliente, "/auth/contrasena", datos)
    assert respuesta.status_code == 200, respuesta.content
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.check_password(NUEVA)


def test_AC_TKT040_01_login_con_sesion_previa_bloqueada_es_409_sin_efectos(editora: Staff) -> None:
    """Login con una sesión anterior aún vigente cuya fila está bloqueada: 409 antes de evaluar
    las credenciales (no depende del usuario enviado) y sin LOGIN_OK."""
    cliente = _cliente(editora)
    antes = _eventos(AccionAuditoria.LOGIN_OK, editora.cuenta)
    with _actualizacion_de_sesion_falla("55P03"):
        respuesta = post(
            cliente,
            "/auth/login",
            {"usuario": "editora.uno", "contrasena": CONTRASENA},
            REMOTE_ADDR=IP,
        )
    problema(respuesta, 409, "conflicto_version")
    assert _eventos(AccionAuditoria.LOGIN_OK, editora.cuenta) == antes


# ---------------------------------------------------------------------------
# AC_TKT040_02: fila borrada por una invalidación concurrente → 401 sesion_expirada
# ---------------------------------------------------------------------------
def test_AC_TKT040_02_renovar_con_la_sesion_invalidada_en_curso_es_401_sesion_expirada(
    editora: Staff, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    cliente = _cliente(editora)
    with _sesion_invalidada_en_curso(editora.cuenta):
        respuesta = post(cliente, "/auth/sesion/renovar")
    problema(respuesta, 401, "sesion_expirada")
    assert _cookie_borrada(respuesta)
    assert _sesiones(editora.cuenta) == 0
    # La cookie antigua ya no sirve.
    problema(cliente.get("/api/v1/panel/auth/sesion"), 401, "no_autenticado")
    _sin_400(logs_json)


def test_AC_TKT040_02_escritura_con_la_sesion_invalidada_en_curso_no_tiene_efectos(
    editora: Staff,
) -> None:
    cliente = _cliente(editora)
    datos = {"contrasena_actual": CONTRASENA, "contrasena_nueva": NUEVA}
    with _sesion_invalidada_en_curso(editora.cuenta):
        problema(post(cliente, "/auth/contrasena", datos), 401, "sesion_expirada")
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.check_password(CONTRASENA)


def test_AC_TKT040_02_login_con_la_sesion_previa_invalidada_en_curso_entra(
    editora: Staff,
) -> None:
    """En el login (AllowAny) la sesión previa invalidada se trata como anónima: entra."""
    cliente = _cliente(editora)
    with _sesion_invalidada_en_curso(editora.cuenta):
        respuesta = post(
            cliente,
            "/auth/login",
            {"usuario": "editora.uno", "contrasena": CONTRASENA},
            REMOTE_ADDR=IP,
        )
    assert respuesta.status_code == 200, respuesta.content
    assert _sesiones(editora.cuenta) == 1
    assert cliente.get("/api/v1/panel/auth/sesion").status_code == 200


# ---------------------------------------------------------------------------
# AC_TKT040_03: lecturas y vistas previas (no declaran 409) → 401
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("ruta", ["/auth/autorizacion", "/tablero", "/cuentas"])
def test_AC_TKT040_03_get_que_renueva_con_contencion_es_401_sesion_expirada(
    admin: Staff, ruta: str
) -> None:
    cliente = _cliente(admin)
    with _actualizacion_de_sesion_falla("55P03"):
        respuesta = cliente.get(f"/api/v1/panel{ruta}")
    problema(respuesta, 401, "sesion_expirada")
    # No se descarta la sesión (puede seguir viva): el siguiente GET funciona.
    assert cliente.get(f"/api/v1/panel{ruta}").status_code == 200


def test_AC_TKT040_03_get_con_la_sesion_invalidada_en_curso_es_401(editora: Staff) -> None:
    cliente = _cliente(editora)
    with _sesion_invalidada_en_curso(editora.cuenta):
        respuesta = cliente.get("/api/v1/panel/tablero")
    problema(respuesta, 401, "sesion_expirada")
    assert _cookie_borrada(respuesta)


def test_AC_TKT040_03_vista_previa_con_contencion_es_401_no_409(editora: Staff) -> None:
    """Las vistas previas (POST sin efectos) no declaran 409 en el contrato."""
    cliente = _cliente(editora)
    with _actualizacion_de_sesion_falla("55P03"):
        respuesta = post(cliente, "/contenidos/destinos/vista-previa", {})
    problema(respuesta, 401, "sesion_expirada")


def test_AC_TKT040_03_obtener_sesion_no_renueva_ni_guarda(editora: Staff) -> None:
    """GET /auth/sesion no renueva la inactividad (AC-109): ningún UPDATE que pueda fallar."""
    cliente = _cliente(editora)
    with _actualizacion_de_sesion_falla("55P03") as actualizaciones:
        assert cliente.get("/api/v1/panel/auth/sesion").status_code == 200
    assert actualizaciones[0] == 0


def test_AC_TKT040_03_sesion_expirada_que_no_puede_borrarse_es_401(editora: Staff) -> None:
    """Sesión vencida cuyo borrado choca con un bloqueo: 401 sesion_expirada (no 409) y cookie
    borrada; la fila la retira quien la bloquea o la limpieza de caducadas."""
    cliente = _cliente(editora)
    SesionPanel.objects.filter(cuenta_id=editora.cuenta.pk).update(
        session_data=SessionStore().encode(
            {
                **SesionPanel.objects.get(cuenta_id=editora.cuenta.pk).get_decoded(),
                "panel_ultima_actividad": "2000-01-01T00:00:00+00:00",
            }
        )
    )
    clave = cliente.cookies["sessionid"].value
    with _borrado_de_sesion_falla("55P03"):
        respuesta = cliente.get("/api/v1/panel/tablero")
    problema(respuesta, 401, "sesion_expirada")
    assert _cookie_borrada(respuesta)
    assert SesionPanel.objects.filter(session_key=clave).exists()
    assert _revocada(clave)  # TKT-044: la fila sobrevive, pero revocada


def test_AC_TKT040_03_otro_error_al_borrar_la_sesion_expirada_no_se_oculta(
    editora: Staff,
) -> None:
    cliente = _cliente(editora)
    with (
        mock.patch.object(selectors, "cuenta_con_sesion", return_value=None),
        _borrado_de_sesion_falla("XX000"),
    ):
        respuesta = cliente.get("/api/v1/panel/tablero")
    problema(respuesta, 500, "error_interno")


# ---------------------------------------------------------------------------
# AC_TKT040_04: fallo tras el efecto → 401 sesion_expirada, nunca 409
# ---------------------------------------------------------------------------
def _eventos_log(logs: Callable[[], list[dict[str, Any]]], nombre: str) -> list[dict[str, Any]]:
    return [linea for linea in logs() if linea.get("event") == nombre]


@pytest.mark.parametrize("sqlstate", ["55P03", "40P01"])
def test_AC_TKT040_04_cambio_de_contrasena_con_borrado_de_la_sesion_anterior_bloqueado_es_200(
    editora: Staff, sqlstate: str, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """La rotación crea la clave nueva y el borrado de la anterior choca con un bloqueo: la
    contraseña YA cambió, así que la respuesta es la de éxito con la sesión nueva (nunca 409)."""
    cliente = _cliente(editora)
    anterior = cliente.cookies["sessionid"].value
    datos = {"contrasena_actual": CONTRASENA, "contrasena_nueva": NUEVA}
    with _borrado_de_sesion_falla(sqlstate):
        respuesta = post(cliente, "/auth/contrasena", datos)
    assert respuesta.status_code == 200, respuesta.content
    nueva = respuesta.cookies["sessionid"].value
    assert nueva not in ("", anterior)
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.check_password(NUEVA)
    assert _eventos(AccionAuditoria.CAMBIO_CREDENCIAL, editora.cuenta) == 1
    evento = _eventos_log(logs_json, "sesion_anterior_revocada")[-1]
    assert evento["momento"] == "rotacion"
    assert _revocada(anterior)  # TKT-044: la anterior no sigue valiendo
    assert cliente.get("/api/v1/panel/auth/sesion").status_code == 200


def test_AC_TKT040_04_update_tras_el_efecto_con_contencion_es_200_sin_reintento(
    editora: Staff, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """El UPDATE de la sesión tras el efecto choca con un bloqueo: éxito de la operación, la
    renovación no se aplica, queda en el log y el middleware no lo vuelve a intentar."""
    cliente = _cliente(editora)
    datos = {"contrasena_actual": CONTRASENA, "contrasena_nueva": NUEVA}
    original = SessionStore.crear_con_clave_nueva

    def rotar_y_cambiar(self: SessionStore) -> str | None:
        anterior = original(self)
        self["cambio"] = True  # fuerza un UPDATE tras la rotación
        return anterior

    with (
        mock.patch.object(
            SessionStore, "crear_con_clave_nueva", autospec=True, side_effect=rotar_y_cambiar
        ),
        _actualizacion_de_sesion_falla("55P03", en=2) as actualizaciones,
    ):
        respuesta = post(cliente, "/auth/contrasena", datos)
    assert respuesta.status_code == 200, respuesta.content
    assert actualizaciones[0] == 2  # renovación temprana + el que falló; ninguno más
    assert respuesta.cookies["sessionid"].value != ""
    evento = _eventos_log(logs_json, "sesion_no_guardada")[-1]
    assert (evento["momento"], evento["contencion"]) == ("tras_efecto", True)
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.check_password(NUEVA)


def test_AC_TKT040_04_rotacion_con_la_fila_nueva_ya_borrada_es_401(
    editora: Staff, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """El UPDATE posterior a la rotación encuentra la fila borrada (invalidación concurrente):
    401 sesion_expirada y cookie borrada; el efecto (contraseña cambiada) queda confirmado."""
    cliente = _cliente(editora)
    datos = {"contrasena_actual": CONTRASENA, "contrasena_nueva": NUEVA}
    original = SessionStore.crear_con_clave_nueva

    def rotar_y_perder(self: SessionStore) -> str | None:
        anterior = original(self)
        SesionPanel.objects.filter(session_key=self.session_key).delete()
        self["cambio"] = True  # fuerza un UPDATE posterior, que encuentra 0 filas
        return anterior

    with mock.patch.object(
        SessionStore, "crear_con_clave_nueva", autospec=True, side_effect=rotar_y_perder
    ):
        respuesta = post(cliente, "/auth/contrasena", datos)
    problema(respuesta, 401, "sesion_expirada")
    assert _cookie_borrada(respuesta)
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.check_password(NUEVA)
    evento = _eventos_log(logs_json, "sesion_no_guardada")[-1]
    assert (evento["momento"], evento["contencion"]) == ("tras_efecto", False)


def test_AC_TKT040_04_rotacion_que_no_llega_a_crear_la_clave_nueva_es_401(
    editora: Staff,
) -> None:
    """Sin clave nueva y con el efecto confirmado: ni 409 ni seguir con el identificador
    anterior (THREAT-002): 401 sesion_expirada, cookie borrada y la anterior invalidada (TKT-044:
    la INSERT de la rotación falla de verdad, sin simular `create`)."""
    cliente = _cliente(editora)
    anterior = cliente.cookies["sessionid"].value
    datos = {"contrasena_actual": CONTRASENA, "contrasena_nueva": NUEVA}
    with _alta_de_sesion_falla("55P03") as altas:
        respuesta = post(cliente, "/auth/contrasena", datos)
    problema(respuesta, 401, "sesion_expirada")
    assert altas[0] == 1
    assert _cookie_borrada(respuesta)
    editora.cuenta.refresh_from_db()
    assert editora.cuenta.check_password(NUEVA)
    assert not SesionPanel.objects.filter(session_key=anterior).exists()


def test_AC_TKT040_04_rotacion_con_otro_error_al_crear_no_se_oculta(editora: Staff) -> None:
    cliente = _cliente(editora)
    datos = {"contrasena_actual": CONTRASENA, "contrasena_nueva": NUEVA}
    anterior = cliente.cookies["sessionid"].value
    with _alta_de_sesion_falla("XX000"):
        respuesta = post(cliente, "/auth/contrasena", datos)
    problema(respuesta, 500, "error_interno")
    assert not SesionPanel.objects.filter(session_key=anterior).exists()  # TKT-044


def test_AC_TKT040_04_mfa_verificado_con_borrado_de_la_sesion_anterior_bloqueado_es_200(
    admin: Staff,
) -> None:
    cliente = Client(raise_request_exception=False)
    respuesta = post(
        cliente,
        "/auth/login",
        {"usuario": admin.cuenta.usuario, "contrasena": admin.contrasena},
        REMOTE_ADDR=IP,
    )
    assert respuesta.json()["paso_pendiente"] == "MFA"
    anterior = cliente.cookies["sessionid"].value
    with _borrado_de_sesion_falla("40P01"):
        respuesta = post(cliente, "/auth/mfa/verificar", {"codigo": admin.codigo()}, REMOTE_ADDR=IP)
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["paso_pendiente"] == "NINGUNO"
    assert _eventos(AccionAuditoria.LOGIN_OK, admin.cuenta) == 1
    assert _revocada(anterior)  # TKT-044


@pytest.mark.parametrize(
    ("sqlstate", "estado", "codigo"),
    [("55P03", 401, "sesion_expirada"), ("XX000", 500, "error_interno")],
)
def test_AC_TKT040_04_login_cuya_sesion_nueva_no_puede_crearse(
    editora: Staff, sqlstate: str, estado: int, codigo: str
) -> None:
    """Credenciales correctas (sin enumeración) y alta de la sesión bloqueada: 401, no 409."""
    cliente = Client(raise_request_exception=False)
    with mock.patch.object(SessionStore, "create", side_effect=_error_bd(sqlstate)):
        respuesta = post(
            cliente,
            "/auth/login",
            {"usuario": "editora.uno", "contrasena": CONTRASENA},
            REMOTE_ADDR=IP,
        )
    problema(respuesta, estado, codigo)


def test_AC_TKT040_04_login_con_borrado_de_la_sesion_anterior_bloqueado_entra(
    editora: Staff,
) -> None:
    cliente = _cliente(editora)
    anterior = cliente.cookies["sessionid"].value
    with _borrado_de_sesion_falla("55P03"):
        respuesta = post(
            cliente,
            "/auth/login",
            {"usuario": "editora.uno", "contrasena": CONTRASENA},
            REMOTE_ADDR=IP,
        )
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.cookies["sessionid"].value not in ("", anterior)
    assert _revocada(anterior)  # TKT-044


def test_AC_TKT040_04_otro_error_tras_el_efecto_no_se_oculta(editora: Staff) -> None:
    cliente = _cliente(editora)
    datos = {"contrasena_actual": CONTRASENA, "contrasena_nueva": NUEVA}
    with _borrado_de_sesion_falla("XX000"):
        respuesta = post(cliente, "/auth/contrasena", datos)
    problema(respuesta, 500, "error_interno")


def test_AC_TKT040_04_marcar_guardada_sin_clave_no_hace_nada() -> None:
    tienda = SessionStore()
    marcar_guardada(tienda)
    assert tienda._guardado is None


def test_AC_TKT040_04_bloqueo_de_mfa_con_borrado_de_sesion_bloqueado_sigue_429(
    admin: Staff,
) -> None:
    """El 5.º fallo de MFA bloquea la cuenta (efecto confirmado); si la sesión no se puede borrar
    por un bloqueo, se descarta igualmente y la respuesta sigue siendo la 429 del contrato."""
    cliente = Client(raise_request_exception=False)
    post(
        cliente,
        "/auth/login",
        {"usuario": admin.cuenta.usuario, "contrasena": admin.contrasena},
        REMOTE_ADDR=IP,
    )
    for _ in range(4):
        problema(post(cliente, "/auth/mfa/verificar", {"codigo": "000000"}), 401, "mfa_invalido")
    anterior = cliente.cookies["sessionid"].value
    with _borrado_de_sesion_falla("55P03"):
        respuesta = post(cliente, "/auth/mfa/verificar", {"codigo": "000000"})
    problema(respuesta, 429, "acceso_bloqueado_temporalmente")
    assert _cookie_borrada(respuesta)
    assert _revocada(anterior)  # TKT-044


# ---------------------------------------------------------------------------
# AC_TKT040_05: logout y "No autorizo": borrado antes de auditar
# ---------------------------------------------------------------------------
def test_AC_TKT040_05_logout_con_borrado_bloqueado_es_409_sin_auditar_y_reintentable(
    editora: Staff,
) -> None:
    cliente = _cliente(editora)
    with mock.patch.object(SessionStore, "delete", side_effect=_error_bd("55P03")):
        respuesta = post(cliente, "/auth/logout")
    problema(respuesta, 409, "conflicto_version")
    assert _eventos(AccionAuditoria.LOGOUT, editora.cuenta) == 0
    assert _sesiones(editora.cuenta) == 1
    reintento = post(cliente, "/auth/logout")
    assert reintento.status_code == 204
    assert _eventos(AccionAuditoria.LOGOUT, editora.cuenta) == 1
    assert _sesiones(editora.cuenta) == 0


def test_AC_TKT040_05_no_autorizo_con_borrado_bloqueado_es_409_sin_auditar(
    editora: Staff,
) -> None:
    cliente = _cliente(editora)
    datos = {"decision": "NO_AUTORIZO", "version_politica": "1.0"}
    with mock.patch.object(SessionStore, "delete", side_effect=_error_bd("55P03")):
        respuesta = post(cliente, "/auth/autorizacion", datos)
    problema(respuesta, 409, "conflicto_version")
    assert _eventos(AccionAuditoria.LOGOUT, editora.cuenta) == 0
    assert post(cliente, "/auth/autorizacion", datos).status_code == 204
    assert _eventos(AccionAuditoria.LOGOUT, editora.cuenta) == 1


# ---------------------------------------------------------------------------
# AC_TKT040_06: red de seguridad del middleware
# ---------------------------------------------------------------------------
def _peticion_con_sesion(editora: Staff) -> tuple[Any, str]:
    tienda = SessionStore()
    tienda[CLAVE_CUENTA] = editora.cuenta.pk
    tienda.save()
    clave = str(tienda.session_key)
    peticion = RequestFactory().post("/api/v1/panel/auth/sesion/renovar")
    peticion.COOKIES["sessionid"] = clave
    peticion.session = SessionStore(session_key=clave)
    peticion.session["panel_ultima_actividad"] = "2026-01-01T00:00:00+00:00"
    return peticion, clave


def test_AC_TKT040_06_middleware_con_la_fila_borrada_responde_401_problem_json_no_400(
    editora: Staff, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """Reproducción de la QA (renovar_middleware.py) con el middleware del proyecto."""
    peticion, clave = _peticion_con_sesion(editora)
    SesionPanel.objects.filter(session_key=clave).delete()
    middleware = SesionPanelMiddleware(lambda _r: HttpResponse(status=200))
    respuesta = middleware.process_response(peticion, HttpResponse(status=200))
    assert respuesta.status_code == 401
    assert respuesta["Content-Type"] == "application/problem+json"
    cuerpo = json.loads(respuesta.content)
    assert cuerpo["code"] == "sesion_expirada"
    assert len(cuerpo["trace_id"]) == 32
    assert _cookie_borrada(respuesta)
    assert "Cookie" in respuesta["Vary"]
    evento = _eventos_log(logs_json, "sesion_no_guardada")[-1]
    assert (evento["momento"], evento["contencion"]) == ("middleware", False)


@pytest.mark.parametrize("sqlstate", ["55P03", "40P01", "40001"])
def test_AC_TKT040_06_middleware_con_contencion_entrega_la_respuesta_de_la_vista(
    editora: Staff, sqlstate: str, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """Contención tras la vista (efecto posiblemente confirmado): ni 400 ni 409; la respuesta de
    la vista se entrega y la renovación no se aplica (queda en el log)."""
    peticion, _ = _peticion_con_sesion(editora)
    middleware = SesionPanelMiddleware(lambda _r: HttpResponse(status=200))
    original = HttpResponse(b"ok", status=200)
    with _actualizacion_de_sesion_falla(sqlstate):
        respuesta = middleware.process_response(peticion, original)
    assert respuesta is original
    assert respuesta.status_code == 200
    evento = _eventos_log(logs_json, "sesion_no_guardada")[-1]
    assert (evento["momento"], evento["contencion"]) == ("middleware", True)


def test_AC_TKT040_06_middleware_sin_fallos_se_comporta_como_el_de_django(
    editora: Staff,
) -> None:
    peticion = RequestFactory().get("/api/v1/publico")
    middleware = SesionPanelMiddleware(lambda _r: HttpResponse(status=200))
    middleware.process_request(peticion)
    respuesta = middleware.process_response(peticion, HttpResponse(status=200))
    assert respuesta.status_code == 200
    assert "sessionid" not in respuesta.cookies


# ---------------------------------------------------------------------------
# AC_TKT040_07: SessionStore no repite un UPDATE ya hecho
# ---------------------------------------------------------------------------
def test_AC_TKT040_07_guardar_dos_veces_lo_mismo_hace_un_solo_update(
    editora: Staff, django_assert_num_queries: Any
) -> None:
    tienda = SessionStore()
    tienda[CLAVE_CUENTA] = editora.cuenta.pk
    tienda.save()
    clave = tienda.session_key
    tienda["x"] = 1
    with django_assert_num_queries(3):  # SAVEPOINT + UPDATE + RELEASE
        tienda.save()
    with django_assert_num_queries(0):
        tienda.save()
    tienda["x"] = 2
    with django_assert_num_queries(3):
        tienda.save()
    assert SessionStore(clave).load()["x"] == 2


def test_AC_TKT040_07_tras_rotar_la_clave_nueva_se_guarda(editora: Staff) -> None:
    tienda = SessionStore()
    tienda[CLAVE_CUENTA] = editora.cuenta.pk
    tienda.save()
    tienda.cycle_key()
    tienda["y"] = "z"
    tienda.save()
    assert SessionStore(tienda.session_key).load()["y"] == "z"


def test_AC_TKT040_07_peticion_autenticada_hace_un_solo_update_de_sesion(
    editora: Staff,
) -> None:
    """El guardado temprano sustituye al del middleware: un único UPDATE por petición."""
    cliente = _cliente(editora)
    with _actualizacion_de_sesion_falla("55P03", en=99) as actualizaciones:
        assert post(cliente, "/auth/sesion/renovar").status_code == 200
        assert cliente.get("/api/v1/panel/tablero").status_code == 200
    assert actualizaciones[0] == 2


def test_AC_TKT040_07_clasificacion_de_fallos() -> None:
    assert fallo_por_contencion(_error_bd("55P03"))
    assert fallo_por_contencion(_error_bd("40001"))
    envuelto = UpdateError()
    envuelto.__cause__ = _error_bd("40P01")
    assert fallo_por_contencion(envuelto)
    assert not fallo_por_contencion(UpdateError())
    assert not fallo_por_contencion(_error_bd("23505"))
    tienda = SessionStore("x" * 32)
    tienda["a"] = 1
    descartar_en_memoria(tienda)
    assert tienda.is_empty()
    assert tienda.modified


# ---------------------------------------------------------------------------
# AC_TKT040_08: el esquema generado declara 409 en las 8 operaciones de CHG-API-006
# ---------------------------------------------------------------------------
OPERACIONES_CHG_API_006 = {
    "panelIniciarSesion",
    "panelVerificarMfa",
    "panelCambiarContrasena",
    "panelActualizarConfigInicio",
    "panelActualizarConfiguracionSitio",
    "panelActualizarNivelEscala",
    "panelCerrarSesion",
    "panelRenovarSesion",
}


def test_AC_TKT040_08_esquema_generado_declara_409_problem_json_en_las_8_operaciones() -> None:
    from drf_spectacular.generators import SchemaGenerator

    esquema = SchemaGenerator().get_schema(request=None, public=True)
    vistas = {
        op["operationId"]: op
        for item in esquema["paths"].values()
        for metodo, op in item.items()
        if isinstance(op, dict) and "operationId" in op
    }
    assert OPERACIONES_CHG_API_006 <= set(vistas)
    for operacion in OPERACIONES_CHG_API_006:
        respuesta = vistas[operacion]["responses"].get("409")
        assert respuesta is not None, operacion
        assert set(respuesta["content"]) == {"application/problem+json"}, operacion
