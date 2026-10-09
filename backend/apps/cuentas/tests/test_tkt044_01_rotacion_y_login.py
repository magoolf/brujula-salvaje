"""TKT-044 (QA de TKT-040: F-01 MEDIUM THREAT-002, F-02, F-03/F-04 CWE-204) con transacciones
REALES de PostgreSQL (`django_db(transaction=True)`): la petición y cada bloqueador corren en su
hilo, con su conexión y su transacción. Ningún fallo de la BD se simula.

- AC_TKT044_01: tras cambiar la contraseña o verificar el MFA, la sesión ANTERIOR deja de valer
  aunque otra transacción tenga su fila bloqueada (antes: el borrado chocaba, se ignoraba y la
  clave anterior seguía válida y renovable hasta el máximo absoluto de 12 h). Sin esperar.
- AC_TKT044_02: si la INSERT de la clave nueva falla de verdad (la FK de la cuenta espera un
  bloqueo de su fila más que `lock_timeout`), la respuesta es 401 `sesion_expirada`, la cookie se
  borra y la clave anterior queda invalidada igualmente (antes seguía válida).
- AC_TKT044_03 (F-02): ese fallo se detecta como tal: log `sesion_no_rotada` (antes la rama era
  inalcanzable porque `cycle_key` asigna la clave nueva antes de guardarla, y el log decía
  `sesion_anterior_no_borrada`). La sesión conserva su clave anterior y solo se intenta una INSERT;
  el alta de una sesión cuya cuenta ya no existe no reintenta para siempre (Django sí).
- AC_TKT044_04: `invalidar_clave` no espera bloqueos: con la fila bloqueada deja una marca de
  revocación que la carga de sesiones respeta; la marca no es una sesión y la purga la retira.
- AC_TKT044_05 (F-04, CWE-204): con la fila de la cuenta bloqueada, el login de una cuenta
  existente responde lo mismo que el de un usuario inexistente y SIN esperar `lock_timeout`
  (antes 5 s frente a 0,2 s).
- AC_TKT044_06 (F-03, CWE-204): sin contención, una contraseña incorrecta de una cuenta existente
  hace el mismo trabajo de BD que un usuario inexistente (misma consulta de la cuenta, mismo
  contador por usuario en caché, una auditoría); solo añade el UPDATE de su contador.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from django.core.cache import cache
from django.core.exceptions import SuspiciousOperation
from django.db import IntegrityError, connection, connections, transaction
from django.db.models import Max
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.auditoria.models import AccionAuditoria, EventoAuditoria
from apps.cuentas import services
from apps.cuentas.models import CuentaStaff, RolCuenta, SesionPanel
from apps.cuentas.sesiones import (
    CLAVE_AUTENTICADO_EN,
    CLAVE_CUENTA,
    SessionStore,
    clave_revocacion,
    fallo_por_contencion,
    invalidar_clave,
)
from apps.cuentas.tests.conftest import IP, Staff, crear_staff, entrar, post, problema

pytestmark = pytest.mark.django_db(transaction=True)

PLAZO_S = 60
LOCK_TIMEOUT_S = 5  # ALTER ROLE app_migrator SET lock_timeout = '5s' (infra/db/init)
NUEVA = "otra-frase-de-prueba-bastante-larga-2026"
INCORRECTA = "frase-incorrecta-bastante-larga-2026"


@pytest.fixture(autouse=True)
def _limites_limpios() -> None:
    """cache_limites no la vacía el flush de las pruebas transaccionales."""
    cache.clear()


class _Bloqueador(threading.Thread):
    """Otra transacción (conexión propia) que ejecuta `sql` y la mantiene hasta `soltar`."""

    def __init__(self, sql: list[tuple[str, list[Any]]]):
        super().__init__()
        self.sql = sql
        self.listo = threading.Event()
        self.soltar = threading.Event()
        self.error: BaseException | None = None

    def run(self) -> None:
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                for sentencia, parametros in self.sql:
                    cursor.execute(sentencia, parametros)
                self.listo.set()
                self.soltar.wait(PLAZO_S)
        except BaseException as exc:  # pragma: no cover - solo si la prueba falla
            self.error = exc
            self.listo.set()
        finally:
            connections.close_all()

    def iniciar(self) -> _Bloqueador:
        self.start()
        assert self.listo.wait(PLAZO_S)
        return self

    def terminar(self) -> None:
        self.soltar.set()
        self.join(PLAZO_S)
        assert self.error is None, self.error


@contextmanager
def _bloqueo(sql: list[tuple[str, list[Any]]]) -> Iterator[None]:
    bloqueador = _Bloqueador(sql).iniciar()
    try:
        yield
    finally:
        bloqueador.terminar()


def _fila_sesion(clave: str) -> list[tuple[str, list[Any]]]:
    return [("SELECT 1 FROM sesion_panel WHERE session_key = %s FOR UPDATE", [clave])]


def _fila_cuenta(cuenta: CuentaStaff) -> list[tuple[str, list[Any]]]:
    return [("SELECT 1 FROM cuenta_staff WHERE id = %s FOR UPDATE", [cuenta.pk])]


@contextmanager
def _bloqueo_tras(
    monkeypatch: pytest.MonkeyPatch, servicio: str, sql: list[tuple[str, list[Any]]]
) -> Iterator[None]:
    """Otra transacción toma el bloqueo `sql` justo DESPUÉS del efecto del servicio (cuando la
    vista va a rotar la sesión) y lo mantiene hasta que termina la petición."""
    original = getattr(services, servicio)
    bloqueadores: list[_Bloqueador] = []

    def envuelto(*args: Any, **kwargs: Any) -> Any:
        resultado = original(*args, **kwargs)
        bloqueadores.append(_Bloqueador(sql).iniciar())
        return resultado

    monkeypatch.setattr(services, servicio, envuelto)
    try:
        yield
    finally:
        monkeypatch.setattr(services, servicio, original)
        for bloqueador in bloqueadores:
            bloqueador.terminar()
    assert len(bloqueadores) == 1


def _clave(cliente: Client) -> str:
    return cliente.cookies["sessionid"].value


def _cookie_borrada(respuesta: Any) -> bool:
    cookie = respuesta.cookies.get("sessionid")
    return cookie is not None and cookie.value == "" and str(cookie["max-age"]) == "0"


def _assert_clave_invalida(clave: str) -> None:
    """Quien conserve la clave anterior (p. ej. robada) ya no entra: ni la consulta ni la
    renovación de la sesión la aceptan."""
    atacante = Client(raise_request_exception=False)
    atacante.cookies["sessionid"] = clave
    assert atacante.get("/api/v1/panel/auth/sesion").status_code == 401
    assert post(atacante, "/auth/sesion/renovar").status_code == 401
    assert SessionStore(clave).load() == {}


def _eventos_log(logs: Callable[[], list[dict[str, Any]]], nombre: str) -> list[dict[str, Any]]:
    return [linea for linea in logs() if linea.get("event") == nombre]


def _admin_tras_contrasena() -> tuple[Staff, Client]:
    admin = crear_staff("admin.rotacion", rol=RolCuenta.ADMINISTRADOR)
    cliente = Client(raise_request_exception=False)
    respuesta = post(
        cliente,
        "/auth/login",
        {"usuario": admin.cuenta.usuario, "contrasena": admin.contrasena},
        REMOTE_ADDR=IP,
    )
    assert respuesta.json()["paso_pendiente"] == "MFA"
    return admin, cliente


# ---------------------------------------------------------------------------
# AC_TKT044_01: la sesión anterior deja de valer aunque su fila esté bloqueada
# ---------------------------------------------------------------------------
def test_AC_TKT044_01_cambio_de_contrasena_con_la_fila_anterior_bloqueada_la_invalida(
    monkeypatch: pytest.MonkeyPatch, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    staff = crear_staff("editora.rotacion")
    cliente = Client(raise_request_exception=False)
    entrar(cliente, staff)
    anterior = _clave(cliente)
    inicio = time.monotonic()
    with _bloqueo_tras(monkeypatch, "cambiar_contrasena", _fila_sesion(anterior)):
        respuesta = post(
            cliente,
            "/auth/contrasena",
            {"contrasena_actual": staff.contrasena, "contrasena_nueva": NUEVA},
        )
        transcurrido = time.monotonic() - inicio
    assert respuesta.status_code == 200, respuesta.content
    assert transcurrido < LOCK_TIMEOUT_S  # NOWAIT: no espera al bloqueo
    nueva = _clave(cliente)
    assert nueva not in ("", anterior)
    assert SesionPanel.objects.filter(session_key=anterior).exists()  # la fila sobrevivió...
    _assert_clave_invalida(anterior)  # ...pero ya no vale (marca de revocación)
    assert cliente.get("/api/v1/panel/auth/sesion").status_code == 200
    assert _eventos_log(logs_json, "sesion_anterior_revocada")[-1]["momento"] == "rotacion"


def test_AC_TKT044_01_mfa_con_la_fila_anterior_bloqueada_la_invalida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin, cliente = _admin_tras_contrasena()
    anterior = _clave(cliente)
    with _bloqueo_tras(monkeypatch, "verificar_mfa", _fila_sesion(anterior)):
        respuesta = post(cliente, "/auth/mfa/verificar", {"codigo": admin.codigo()}, REMOTE_ADDR=IP)
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["paso_pendiente"] == "NINGUNO"
    assert _clave(cliente) not in ("", anterior)
    _assert_clave_invalida(anterior)
    assert cliente.get("/api/v1/panel/auth/sesion").status_code == 200


def test_AC_TKT044_01_rotacion_sin_contencion_borra_la_fila_anterior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staff = crear_staff("editora.limpia")
    cliente = Client(raise_request_exception=False)
    entrar(cliente, staff)
    anterior = _clave(cliente)
    respuesta = post(
        cliente,
        "/auth/contrasena",
        {"contrasena_actual": staff.contrasena, "contrasena_nueva": NUEVA},
    )
    assert respuesta.status_code == 200, respuesta.content
    assert not SesionPanel.objects.filter(session_key=anterior).exists()
    assert not SesionPanel.objects.filter(session_key=clave_revocacion(anterior)).exists()
    assert SesionPanel.objects.filter(cuenta_id=staff.cuenta.pk).count() == 1


# ---------------------------------------------------------------------------
# AC_TKT044_02 / 03: la INSERT de la clave nueva falla de verdad
# ---------------------------------------------------------------------------
def test_AC_TKT044_02_cambio_de_contrasena_sin_poder_dar_de_alta_la_clave_nueva(
    monkeypatch: pytest.MonkeyPatch, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """La FK de la clave nueva pide FOR KEY SHARE sobre la fila de la cuenta, que otra
    transacción tiene con FOR UPDATE: la INSERT falla con 55P03 tras `lock_timeout`."""
    staff = crear_staff("editora.sinalta")
    cliente = Client(raise_request_exception=False)
    entrar(cliente, staff)
    anterior = _clave(cliente)
    with _bloqueo_tras(monkeypatch, "cambiar_contrasena", _fila_cuenta(staff.cuenta)):
        respuesta = post(
            cliente,
            "/auth/contrasena",
            {"contrasena_actual": staff.contrasena, "contrasena_nueva": NUEVA},
        )
    problema(respuesta, 401, "sesion_expirada")
    assert _cookie_borrada(respuesta)
    staff.cuenta.refresh_from_db()
    assert staff.cuenta.check_password(NUEVA)  # el efecto quedó confirmado
    _assert_clave_invalida(anterior)
    assert not SesionPanel.objects.filter(cuenta_id=staff.cuenta.pk).exists()
    # AC_TKT044_03 (F-02): el fallo de la INSERT se detecta y se registra como tal.
    rotacion = _eventos_log(logs_json, "sesion_no_rotada")
    assert [evento["contencion"] for evento in rotacion] == [True]
    assert _eventos_log(logs_json, "sesion_anterior_no_borrada") == []


def test_AC_TKT044_02_mfa_sin_poder_dar_de_alta_la_clave_nueva(
    monkeypatch: pytest.MonkeyPatch, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    admin, cliente = _admin_tras_contrasena()
    anterior = _clave(cliente)
    with _bloqueo_tras(monkeypatch, "verificar_mfa", _fila_cuenta(admin.cuenta)):
        respuesta = post(cliente, "/auth/mfa/verificar", {"codigo": admin.codigo()}, REMOTE_ADDR=IP)
    problema(respuesta, 401, "sesion_expirada")
    assert _cookie_borrada(respuesta)
    _assert_clave_invalida(anterior)
    assert _eventos_log(logs_json, "sesion_no_rotada")


def _cuenta_inexistente() -> int:
    return int(CuentaStaff.objects.aggregate(maximo=Max("id"))["maximo"] or 0) + 1000


@contextmanager
def _altas_contadas(maximo: int = 20) -> Iterator[list[int]]:
    """Cuenta las claves nuevas generadas; corta (AssertionError) un reintento sin fin."""
    original = SessionStore._get_new_session_key
    contadas = [0]

    def contar(self: SessionStore) -> str:
        contadas[0] += 1
        if contadas[0] > maximo:
            raise AssertionError("alta de sesión reintentada sin fin")
        return str(original(self))

    with pytest.MonkeyPatch.context() as parche:
        parche.setattr(SessionStore, "_get_new_session_key", contar)
        yield contadas


def test_AC_TKT044_03_crear_con_clave_nueva_que_falla_conserva_la_clave_anterior(
    editora_con_sesion: tuple[Staff, str],
) -> None:
    """INSERT real que falla (FK a una cuenta inexistente, detectada en el COMMIT): el error se
    propaga, la sesión conserva su clave anterior y no se reintenta con otras claves."""
    _, anterior = editora_con_sesion
    tienda = SessionStore(anterior)
    tienda[CLAVE_CUENTA] = _cuenta_inexistente()
    with _altas_contadas() as altas, pytest.raises(IntegrityError):
        tienda.crear_con_clave_nueva()
    assert altas[0] == 1
    assert tienda.session_key == anterior
    assert SesionPanel.objects.filter(session_key=anterior).exists()


def test_AC_TKT044_03_crear_con_clave_nueva_devuelve_la_anterior_sin_borrarla(
    editora_con_sesion: tuple[Staff, str],
) -> None:
    _, anterior = editora_con_sesion
    tienda = SessionStore(anterior)
    tienda["dato"] = "conservado"
    assert tienda.crear_con_clave_nueva() == anterior
    assert tienda.session_key != anterior
    assert SessionStore(tienda.session_key).load()["dato"] == "conservado"
    assert SesionPanel.objects.filter(session_key=anterior).exists()  # la invalida quien llama


def test_AC_TKT044_03_alta_de_sesion_de_cuenta_inexistente_no_reintenta_sin_fin() -> None:
    tienda = SessionStore()
    tienda[CLAVE_CUENTA] = _cuenta_inexistente()
    tienda[CLAVE_AUTENTICADO_EN] = timezone.now().isoformat()
    with _altas_contadas() as altas, pytest.raises(IntegrityError):
        tienda.save()
    assert altas[0] == 1
    assert tienda.session_key is None


def test_AC_TKT044_03_clave_repetida_se_reintenta_con_otra(
    editora_con_sesion: tuple[Staff, str],
) -> None:
    """Una clave que ya existe (23505) sí se reintenta: la segunda clave generada entra."""
    _, existente = editora_con_sesion
    original = SessionStore._get_new_session_key
    claves = iter([existente])

    def repetir_primero(self: SessionStore) -> str:
        return next(claves, None) or str(original(self))

    tienda = SessionStore()
    tienda["dato"] = 1
    with pytest.MonkeyPatch.context() as parche:
        parche.setattr(SessionStore, "_get_new_session_key", repetir_primero)
        tienda.save()
    assert tienda.session_key not in (None, existente)
    assert SessionStore(tienda.session_key).load()["dato"] == 1


@pytest.fixture
def editora_con_sesion() -> tuple[Staff, str]:
    staff = crear_staff("editora.tienda")
    cliente = Client(raise_request_exception=False)
    entrar(cliente, staff)
    return staff, _clave(cliente)


# ---------------------------------------------------------------------------
# AC_TKT044_04: invalidar_clave
# ---------------------------------------------------------------------------
def test_AC_TKT044_04_invalidar_con_la_fila_bloqueada_revoca_sin_esperar(
    editora_con_sesion: tuple[Staff, str],
) -> None:
    _, clave = editora_con_sesion
    with _bloqueo(_fila_sesion(clave)):
        inicio = time.monotonic()
        assert invalidar_clave(clave) is False
        assert time.monotonic() - inicio < 1
        assert invalidar_clave(clave) is False  # una segunda invalidación no falla
    marca = SesionPanel.objects.get(session_key=clave_revocacion(clave))
    assert marca.cuenta_id is None
    assert marca.session_data == ""
    assert marca.expire_date > timezone.now() + timedelta(hours=11)
    assert SesionPanel.objects.filter(session_key=clave).exists()
    assert SessionStore(clave).load() == {}
    # La marca nunca es una sesión: su clave no es válida y no carga.
    assert len(marca.session_key) == 40 and marca.session_key.startswith("~")
    assert SessionStore(marca.session_key).load() == {}
    assert SessionStore(marca.session_key).session_key is None
    # La purga de caducadas la retira.
    SesionPanel.objects.filter(pk=marca.pk).update(expire_date=timezone.now() - timedelta(1))
    SessionStore.clear_expired()
    assert not SesionPanel.objects.filter(pk=marca.pk).exists()


def test_AC_TKT044_04_invalidar_sin_contencion_borra_la_fila(
    editora_con_sesion: tuple[Staff, str],
) -> None:
    _, clave = editora_con_sesion
    assert invalidar_clave(clave) is True
    assert not SesionPanel.objects.filter(session_key=clave).exists()
    assert not SesionPanel.objects.filter(session_key=clave_revocacion(clave)).exists()
    assert invalidar_clave(clave) is True  # ya no existía


def test_AC_TKT044_04_sesion_expirada_con_la_fila_bloqueada_queda_revocada(
    editora_con_sesion: tuple[Staff, str],
) -> None:
    """Descarte de una sesión que expiró (autenticación) con su fila bloqueada: 401 y revocada."""
    staff, clave = editora_con_sesion
    tienda = SessionStore(clave)
    tienda["panel_ultima_actividad"] = "2000-01-01T00:00:00+00:00"
    tienda.save()
    cliente = Client(raise_request_exception=False)
    cliente.cookies["sessionid"] = clave
    with _bloqueo(_fila_sesion(clave)):
        respuesta = cliente.get("/api/v1/panel/tablero")
    problema(respuesta, 401, "sesion_expirada")
    assert SesionPanel.objects.filter(session_key=clave_revocacion(clave)).exists()
    assert SessionStore(clave).load() == {}
    assert staff.cuenta.pk  # la cuenta no se toca


# ---------------------------------------------------------------------------
# AC_TKT044_05 / 06: login sin diferencias entre cuenta existente e inexistente (CWE-204)
# ---------------------------------------------------------------------------
def _login(usuario: str, contrasena: str) -> tuple[Any, float]:
    cliente = Client(raise_request_exception=False)
    inicio = time.monotonic()
    respuesta = post(
        cliente, "/auth/login", {"usuario": usuario, "contrasena": contrasena}, REMOTE_ADDR=IP
    )
    return respuesta, time.monotonic() - inicio


def _cuerpo(respuesta: Any) -> dict[str, Any]:
    return {k: v for k, v in respuesta.json().items() if k != "trace_id"}


@pytest.mark.parametrize("contrasena", [INCORRECTA, None])
def test_AC_TKT044_05_login_con_la_fila_de_la_cuenta_bloqueada_no_espera_ni_delata(
    contrasena: str | None,
) -> None:
    staff = crear_staff("editora.oraculo")
    clave_real = contrasena or staff.contrasena
    with _bloqueo(_fila_cuenta(staff.cuenta)):
        existente, t_existente = _login("editora.oraculo", clave_real)
        inexistente, t_inexistente = _login("nadie.oraculo", clave_real)
    problema(existente, 401, "credenciales_invalidas")
    problema(inexistente, 401, "credenciales_invalidas")
    assert _cuerpo(existente) == _cuerpo(inexistente)
    assert t_existente < LOCK_TIMEOUT_S / 2  # antes esperaba lock_timeout (5 s)
    assert abs(t_existente - t_inexistente) < 1
    # Auditado sin actor (la FK no toca la fila bloqueada); el contador de la fila no cambia.
    fallidos = EventoAuditoria.objects.filter(accion=AccionAuditoria.LOGIN_FALLIDO)
    assert fallidos.filter(actor_id__isnull=True).count() == 2
    staff.cuenta.refresh_from_db()
    assert staff.cuenta.intentos_fallidos == 0
    # Liberada la fila, la contraseña correcta entra.
    assert _login("editora.oraculo", staff.contrasena)[0].status_code == 200


def _consultas_de_login(usuario: str) -> list[str]:
    cache.clear()
    with CaptureQueriesContext(connection) as capturadas:
        respuesta, _ = _login(usuario, INCORRECTA)
    problema(respuesta, 401, "credenciales_invalidas")
    return [consulta["sql"] for consulta in capturadas.captured_queries]


def _contar(consultas: list[str], fragmento: str) -> int:
    return sum(1 for sql in consultas if fragmento in sql)


def test_AC_TKT044_06_contrasena_incorrecta_hace_el_mismo_trabajo_exista_o_no() -> None:
    crear_staff("editora.trabajo")
    existente = _consultas_de_login("editora.trabajo")
    inexistente = _consultas_de_login("nadie.trabajo")
    for fragmento in ('FROM "cuenta_staff"', '"cache_limites"', 'INTO "evento_auditoria"'):
        assert _contar(existente, fragmento) == _contar(inexistente, fragmento), fragmento
    assert _contar(existente, 'FROM "cuenta_staff"') == 1
    assert _contar(existente, '"cache_limites"') >= 2  # lectura y escritura del contador
    # La cuenta existente solo añade el UPDATE de su contador (y nada más).
    assert len(existente) - len(inexistente) == _contar(existente, 'UPDATE "cuenta_staff"') == 1


def test_AC_TKT044_06_acceso_completo_reinicia_el_contador_en_cache() -> None:
    staff = crear_staff("editora.contador")
    _login("editora.contador", INCORRECTA)
    assert services._leer_fallos("editora.contador")["intentos"] == 1
    assert _login("editora.contador", staff.contrasena)[0].status_code == 200
    assert services._leer_fallos("editora.contador")["intentos"] == 0


def test_AC_TKT044_04_carga_con_operacion_sospechosa_no_carga_y_se_registra(
    editora_con_sesion: tuple[Staff, str], caplog: pytest.LogCaptureFixture
) -> None:
    """Como la de Django: una SuspiciousOperation al cargar deja la sesión vacía y se registra."""
    _, clave = editora_con_sesion
    tienda = SessionStore(clave)
    with mock.patch.object(
        SesionPanel.objects, "filter", side_effect=SuspiciousOperation("manipulada")
    ):
        assert tienda.load() == {}
    assert tienda.session_key is None
    assert "manipulada" in caplog.text


# ---------------------------------------------------------------------------
# AC_TKT044_07 (QA TKT-044 ciclo 1, F-A): alta con FK violada por HTTP, con plazo acotado
# ---------------------------------------------------------------------------
PLAZO_PETICION_S = 30


def _con_plazo(accion: Callable[[], Any]) -> Any:
    """Ejecuta `accion` en un hilo y falla si no termina en PLAZO_PETICION_S (antes, una cadena
    de __cause__ cíclica colgaba la petición en un bucle de CPU)."""
    resultado: list[Any] = []
    errores: list[BaseException] = []

    def correr() -> None:
        try:
            resultado.append(accion())
        except BaseException as exc:  # pragma: no cover - solo si la prueba falla
            errores.append(exc)
        finally:
            connections.close_all()

    hilo = threading.Thread(target=correr, daemon=True)
    hilo.start()
    hilo.join(PLAZO_PETICION_S)
    assert not hilo.is_alive(), "la petición no terminó: posible bucle infinito"
    assert not errores, errores
    return resultado[0]


def test_AC_TKT044_07_rotacion_con_fk_violada_es_401_sin_colgarse(
    monkeypatch: pytest.MonkeyPatch, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """La INSERT de la clave nueva falla de verdad por FK (23503, cuenta inexistente en el COMMIT):
    401 sesion_expirada, cookie borrada y clave anterior inválida, en tiempo acotado."""
    staff = crear_staff("editora.fk")
    cliente = Client(raise_request_exception=False)
    entrar(cliente, staff)
    anterior = _clave(cliente)
    original = SessionStore.crear_con_clave_nueva

    def con_cuenta_inexistente(self: SessionStore) -> str | None:
        self[CLAVE_CUENTA] = _cuenta_inexistente()
        return original(self)

    monkeypatch.setattr(SessionStore, "crear_con_clave_nueva", con_cuenta_inexistente)
    respuesta = _con_plazo(
        lambda: post(
            cliente,
            "/auth/contrasena",
            {"contrasena_actual": staff.contrasena, "contrasena_nueva": NUEVA},
        )
    )
    monkeypatch.undo()
    problema(respuesta, 401, "sesion_expirada")
    assert _cookie_borrada(respuesta)
    _assert_clave_invalida(anterior)
    assert [e["contencion"] for e in _eventos_log(logs_json, "sesion_no_rotada")] == [False]


def test_AC_TKT044_07_login_con_fk_violada_es_401_sin_colgarse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Login correcto cuya sesión nueva no puede darse de alta (la cuenta ya no existe al
    confirmar la INSERT): 401 sesion_expirada, cookie borrada y la sesión previa invalidada."""
    staff = crear_staff("editora.fklogin")
    cliente = Client(raise_request_exception=False)
    entrar(cliente, staff)
    anterior = _clave(cliente)
    original = services.iniciar_sesion

    def sin_cuenta(*args: Any, **kwargs: Any) -> services.ResultadoLogin:
        resultado = original(*args, **kwargs)
        fantasma = CuentaStaff(pk=_cuenta_inexistente(), usuario="fantasma")
        return services.ResultadoLogin(cuenta=fantasma, requiere_mfa=resultado.requiere_mfa)

    monkeypatch.setattr(services, "iniciar_sesion", sin_cuenta)
    respuesta = _con_plazo(
        lambda: post(
            cliente,
            "/auth/login",
            {"usuario": staff.cuenta.usuario, "contrasena": staff.contrasena},
            REMOTE_ADDR=IP,
        )
    )
    monkeypatch.undo()
    problema(respuesta, 401, "sesion_expirada")
    assert _cookie_borrada(respuesta)
    _assert_clave_invalida(anterior)


def test_AC_TKT044_07_error_de_alta_sin_ciclos_y_clasificacion_segura() -> None:
    """El error que propaga el alta no forma ciclos en __cause__, y fallo_por_contencion termina
    aunque reciba una cadena cíclica."""
    tienda = SessionStore()
    tienda[CLAVE_CUENTA] = _cuenta_inexistente()
    with pytest.raises(IntegrityError) as info:
        tienda.save()
    vistos: list[BaseException] = []
    actual: BaseException | None = info.value
    while actual is not None:
        assert all(actual is not visto for visto in vistos), "ciclo en __cause__"
        vistos.append(actual)
        actual = actual.__cause__
    assert len(vistos) == 2  # IntegrityError de Django -> error de psycopg
    assert fallo_por_contencion(info.value) is False
    a, b = IntegrityError("a"), IntegrityError("b")
    a.__cause__, b.__cause__ = b, a
    assert fallo_por_contencion(a) is False
