"""TKT-040 con transacciones REALES de PostgreSQL (`django_db(transaction=True)`): cada petición y
cada bloqueador corren en su hilo, con su conexión y su transacción.

- AC_TKT040_09: renovar la sesión mientras otra transacción tiene su fila bloqueada más que
  `lock_timeout` → 409 `conflicto_version` (antes 400 `validacion` desde SessionMiddleware); al
  liberarse, el reintento funciona.
- AC_TKT040_10: renovar mientras otra transacción borra la sesión (invalidación concurrente) y
  confirma → 401 `sesion_expirada` (antes 400 `validacion`).
- AC_TKT040_11 (NV-01, CWE-204): con un login en curso sobre el mismo usuario retenido más que
  `lock_timeout`, la respuesta es la MISMA para una cuenta existente y para un usuario
  inexistente: 401 `credenciales_invalidas`, mismo cuerpo salvo `trace_id` y el mismo tiempo de
  espera; se audita LOGIN_FALLIDO y no se suma un fallo sin comprobar la contraseña.
- AC_TKT040_12 (NV-01): con la fila de la cuenta bloqueada por otra transacción, el login ya no
  responde 409 (que delataba que la cuenta existe) sino 401 `credenciales_invalidas`.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import pytest
from django.core.cache import cache
from django.db import connection, connections, transaction
from django.test import Client

from apps.auditoria.models import AccionAuditoria, EventoAuditoria
from apps.core.throttling import huella_hmac
from apps.cuentas.models import SesionPanel
from apps.cuentas.tests.conftest import IP, crear_staff, entrar, post, problema

pytestmark = pytest.mark.django_db(transaction=True)

PLAZO_S = 60
LOCK_TIMEOUT_S = 5  # ALTER ROLE app_migrator SET lock_timeout = '5s' (infra/db/init)


@pytest.fixture(autouse=True)
def _limites_limpios() -> None:
    """cache_limites (límite de tasa por IP y fallos por usuario) no la vacía el flush de las
    pruebas transaccionales: otras pruebas con COMMIT pueden haber agotado el límite de la IP."""
    cache.clear()


class _Bloqueador(threading.Thread):
    """Otra transacción (conexión propia) que ejecuta `sql` y la mantiene abierta hasta `soltar`.

    Con `esperar_a_otro` no suelta hasta que otra sesión de la BD espere un bloqueo, y entonces
    confirma (COMMIT) al instante."""

    def __init__(self, sql: list[tuple[str, list[Any]]], *, esperar_a_otro: bool = False):
        super().__init__()
        self.sql = sql
        self.esperar_a_otro = esperar_a_otro
        self.listo = threading.Event()
        self.soltar = threading.Event()
        self.error: BaseException | None = None

    def run(self) -> None:
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                for sentencia, parametros in self.sql:
                    cursor.execute(sentencia, parametros)
                self.listo.set()
                if self.esperar_a_otro:
                    _esperar_a_que_otro_espere(cursor)
                else:
                    self.soltar.wait(PLAZO_S)
        except BaseException as exc:  # pragma: no cover - solo si la prueba falla
            self.error = exc
            self.listo.set()
        finally:
            connections.close_all()


def _esperar_a_que_otro_espere(cursor: Any) -> None:
    limite = time.monotonic() + PLAZO_S
    while time.monotonic() < limite:
        cursor.execute("SELECT pg_stat_clear_snapshot()")
        cursor.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
            "AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()"
        )
        if cursor.fetchone()[0]:
            return
        time.sleep(0.05)
    raise AssertionError("ninguna sesión llegó a esperar el bloqueo")  # pragma: no cover


def _con_bloqueo(
    sql: list[tuple[str, list[Any]]], accion: Callable[[], Any], *, esperar_a_otro: bool = False
) -> tuple[Any, float]:
    bloqueador = _Bloqueador(sql, esperar_a_otro=esperar_a_otro)
    bloqueador.start()
    try:
        assert bloqueador.listo.wait(PLAZO_S)
        inicio = time.monotonic()
        resultado = accion()
        transcurrido = time.monotonic() - inicio
    finally:
        bloqueador.soltar.set()
        bloqueador.join(PLAZO_S)
    assert bloqueador.error is None, bloqueador.error
    return resultado, transcurrido


def _clave_sesion(cliente: Client) -> str:
    return cliente.cookies["sessionid"].value


def _sin_cuerpo_variable(cuerpo: dict[str, Any]) -> dict[str, Any]:
    return {clave: valor for clave, valor in cuerpo.items() if clave != "trace_id"}


def _bloqueo_login(usuario: str) -> tuple[str, list[Any]]:
    """El mismo bloqueo consultivo que toma un login en curso sobre `usuario` (servicio)."""
    return (
        "SELECT pg_advisory_xact_lock(hashtext('login'), hashtext(%s))",
        [huella_hmac(f"login|{usuario}")],
    )


def _login(usuario: str, contrasena: str) -> Any:
    cliente = Client(raise_request_exception=False)
    return post(
        cliente, "/auth/login", {"usuario": usuario, "contrasena": contrasena}, REMOTE_ADDR=IP
    )


def _fallidos(actor_id: int | None) -> int:
    eventos = EventoAuditoria.objects.filter(accion=AccionAuditoria.LOGIN_FALLIDO)
    if actor_id is None:
        return eventos.filter(actor_id__isnull=True).count()
    return eventos.filter(actor_id=actor_id).count()


# ---------------------------------------------------------------------------
# AC_TKT040_09 / 10: sesión
# ---------------------------------------------------------------------------
def test_AC_TKT040_09_renovar_con_la_fila_de_sesion_bloqueada_es_409_y_reintentable(
    logs_json: Callable[[], list[dict[str, Any]]],
) -> None:
    cliente = Client(raise_request_exception=False)
    entrar(cliente, crear_staff("editora.renovar"))
    clave = _clave_sesion(cliente)
    respuesta, esperado = _con_bloqueo(
        [("SELECT 1 FROM sesion_panel WHERE session_key = %s FOR UPDATE", [clave])],
        lambda: post(cliente, "/auth/sesion/renovar"),
    )
    problema(respuesta, 409, "conflicto_version")
    assert esperado >= LOCK_TIMEOUT_S - 0.5  # esperó el lock_timeout del rol
    assert [linea for linea in logs_json() if linea.get("event") == "excepcion_no_controlada"] == []
    reintento = post(cliente, "/auth/sesion/renovar")
    assert reintento.status_code == 200, reintento.content


def test_AC_TKT040_10_renovar_durante_una_invalidacion_concurrente_es_401_sesion_expirada() -> None:
    staff = crear_staff("editora.invalidada")
    cliente = Client(raise_request_exception=False)
    entrar(cliente, staff)
    respuesta, _ = _con_bloqueo(
        [("DELETE FROM sesion_panel WHERE cuenta_id = %s", [staff.cuenta.pk])],
        lambda: post(cliente, "/auth/sesion/renovar"),
        esperar_a_otro=True,
    )
    problema(respuesta, 401, "sesion_expirada")
    assert respuesta.cookies["sessionid"].value == ""
    assert SesionPanel.objects.filter(cuenta_id=staff.cuenta.pk).count() == 0


# ---------------------------------------------------------------------------
# AC_TKT040_11 / 12: NV-01 (CWE-204)
# ---------------------------------------------------------------------------
def test_AC_TKT040_11_login_retenido_responde_igual_exista_o_no_la_cuenta() -> None:
    staff = crear_staff("editora.existe")
    resultados = {}
    for usuario in ("editora.existe", "nadie.existe"):
        resultados[usuario] = _con_bloqueo(
            [_bloqueo_login(usuario)], lambda u=usuario: _login(u, "frase-incorrecta-larga-2026")
        )
    (existe, t_existe), (no_existe, t_no_existe) = resultados.values()
    cuerpo_existe = problema(existe, 401, "credenciales_invalidas")
    cuerpo_no_existe = problema(no_existe, 401, "credenciales_invalidas")
    assert _sin_cuerpo_variable(cuerpo_existe) == _sin_cuerpo_variable(cuerpo_no_existe)
    assert set(existe.headers) == set(no_existe.headers)
    # Mismo tiempo: ambos esperan el lock_timeout (antes, el inexistente respondía al instante).
    assert t_existe >= LOCK_TIMEOUT_S - 0.5
    assert t_no_existe >= LOCK_TIMEOUT_S - 0.5
    assert abs(t_existe - t_no_existe) < 1.5
    # Auditoría: LOGIN_FALLIDO en ambos casos y sin actor (la FK del actor pediría bloquear la
    # fila de la cuenta); sin sumar fallos sin comprobar la contraseña.
    assert _fallidos(None) == 2
    assert _fallidos(staff.cuenta.pk) == 0
    staff.cuenta.refresh_from_db()
    assert staff.cuenta.intentos_fallidos == 0


def test_AC_TKT040_11_login_correcto_no_retenido_sigue_funcionando_y_cuenta_fallos() -> None:
    """El bloqueo consultivo no cambia el camino normal: fallos contados y login correcto."""
    staff = crear_staff("editora.normal")
    problema(_login("editora.normal", "frase-incorrecta-larga-2026"), 401, "credenciales_invalidas")
    staff.cuenta.refresh_from_db()
    assert staff.cuenta.intentos_fallidos == 1
    assert _login("editora.normal", staff.contrasena).status_code == 200


def test_AC_TKT040_11_logins_simultaneos_sobre_un_usuario_retenido_nunca_dan_409() -> None:
    """Varios intentos a la vez (existente e inexistente) mientras un login retiene el usuario:
    todos 401 credenciales_invalidas; ningún 409 ni 5xx que distinga la cuenta."""
    crear_staff("editora.rafaga")
    usuarios = ["editora.rafaga"] * 3 + ["nadie.rafaga"] * 3
    resultados: list[Any] = [None] * len(usuarios)

    def rafaga() -> None:
        barrera = threading.Barrier(len(usuarios))

        def trabajar(indice: int, usuario: str) -> None:
            try:
                barrera.wait(PLAZO_S)
                resultados[indice] = _login(usuario, "frase-incorrecta-larga-2026")
            finally:
                connections.close_all()

        hilos = [threading.Thread(target=trabajar, args=(i, u)) for i, u in enumerate(usuarios)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(PLAZO_S)

    _con_bloqueo([_bloqueo_login("editora.rafaga"), _bloqueo_login("nadie.rafaga")], rafaga)
    assert all(r is not None for r in resultados)
    codigos = [(r.status_code, r.json()["code"]) for r in resultados]
    assert codigos == [(401, "credenciales_invalidas")] * len(usuarios)


def test_AC_TKT040_12_login_con_la_fila_de_la_cuenta_bloqueada_no_delata_la_cuenta() -> None:
    staff = crear_staff("editora.fila")
    respuesta, _ = _con_bloqueo(
        [("SELECT 1 FROM cuenta_staff WHERE id = %s FOR UPDATE", [staff.cuenta.pk])],
        lambda: _login("editora.fila", staff.contrasena),
    )
    problema(respuesta, 401, "credenciales_invalidas")
    assert _fallidos(None) == 1
    # Liberada la fila, la misma contraseña entra.
    assert _login("editora.fila", staff.contrasena).status_code == 200
