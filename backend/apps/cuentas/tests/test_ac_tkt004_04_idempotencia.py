"""AC-TKT004-04: servicio común de idempotencia (ADR-API-002 §5, DB_HANDOFF idempotencia_peticion,
DEC-AUTO-123..129) y su uso en panelCrearCuenta.

- misma clave + misma huella → misma respuesta, un solo efecto;
- otra huella u otra operación → 422 idempotencia_conflicto;
- duplicado concurrente sin confirmar → 409 idempotencia_en_curso con Retry-After;
- panelCrearCuenta repetido → 409 idempotencia_respuesta_no_reproducible con Location.
"""

from __future__ import annotations

import threading
import uuid

import pytest
from django.db import connection, connections, transaction
from django.test import override_settings

from apps.auditoria.models import EventoAuditoria
from apps.core import idempotencia
from apps.core.exceptions import ParametroInvalido
from apps.cuentas.models import CuentaStaff
from apps.cuentas.tests.conftest import crear_staff, post, problema

ALTA = {"usuario": "alta.idempotente", "nombre_visible": "Alta", "rol": "EDITOR"}


def _filas(cuenta_id: int) -> list[tuple]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT operacion, codigo_http, recurso_id, cuerpo_respuesta IS NULL, cuerpo_omitido "
            "FROM app.idempotencia_peticion WHERE cuenta_id = %s",
            [cuenta_id],
        )
        return cursor.fetchall()


# ---------------------------------------------------------------------------
# panelCrearCuenta (DEC-AUTO-125/129)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_AC_TKT004_04_crear_cuenta_repetida_no_reproducible_con_location(cliente_admin, admin):
    clave = str(uuid.uuid4())
    primera = post(cliente_admin, "/cuentas", ALTA, HTTP_IDEMPOTENCY_KEY=clave)
    assert primera.status_code == 201
    cuenta_id = primera.json()["cuenta"]["id"]
    segunda = post(cliente_admin, "/cuentas", ALTA, HTTP_IDEMPOTENCY_KEY=clave)
    problema(segunda, 409, "idempotencia_respuesta_no_reproducible")
    assert segunda["Location"] == f"/api/v1/panel/cuentas/{cuenta_id}"
    assert CuentaStaff.objects.filter(usuario="alta.idempotente").count() == 1
    assert EventoAuditoria.objects.filter(accion="CUENTA_CREAR").count() == 1
    # La respuesta con la contraseña temporal nunca se guarda (AC-106).
    assert _filas(admin.cuenta.pk) == [("panelCrearCuenta", 201, cuenta_id, True, True)]


@pytest.mark.django_db
def test_AC_TKT004_04_misma_clave_otra_huella_es_422(cliente_admin):
    clave = str(uuid.uuid4())
    assert post(cliente_admin, "/cuentas", ALTA, HTTP_IDEMPOTENCY_KEY=clave).status_code == 201
    otra = post(
        cliente_admin, "/cuentas", {**ALTA, "usuario": "otra.alta"}, HTTP_IDEMPOTENCY_KEY=clave
    )
    assert "Idempotency-Key" in problema(otra, 422, "idempotencia_conflicto")["errors"]
    assert not CuentaStaff.objects.filter(usuario="otra.alta").exists()


@pytest.mark.django_db
def test_AC_TKT004_04_error_no_guarda_la_clave_y_el_reintento_se_ejecuta(cliente_admin, admin):
    crear_staff("ya.existe")
    clave = str(uuid.uuid4())
    problema(
        post(
            cliente_admin, "/cuentas", {**ALTA, "usuario": "ya.existe"}, HTTP_IDEMPOTENCY_KEY=clave
        ),
        409,
        "duplicado",
    )
    assert _filas(admin.cuenta.pk) == []
    # Sin clave también funciona (la cabecera es opcional).
    assert post(cliente_admin, "/cuentas", ALTA).status_code == 201


@pytest.mark.django_db
def test_AC_TKT004_04_clave_invalida_es_400(cliente_admin):
    respuesta = post(cliente_admin, "/cuentas", ALTA, HTTP_IDEMPOTENCY_KEY="no-es-un-uuid")
    assert "Idempotency-Key" in problema(respuesta, 400, "parametro_invalido")["errors"]


# ---------------------------------------------------------------------------
# Servicio común (reutilizable por TKT-005/006)
# ---------------------------------------------------------------------------
@pytest.fixture
def cuenta_id(db) -> int:
    return crear_staff("servicio.idem").cuenta.pk


def _efecto(contador: list[int], cuerpo=None, codigo: int = 201):
    def efecto() -> idempotencia.Resultado:
        contador.append(1)
        return idempotencia.Resultado(codigo_http=codigo, cuerpo=cuerpo or {"id": 7}, recurso_id=7)

    return efecto


def _ejecutar(cuenta_id, clave, efecto, operacion="panelCrearDestino", huella=None, **extra):
    return idempotencia.ejecutar(
        cuenta_id=cuenta_id,
        clave=clave,
        operacion=operacion,
        huella=huella or idempotencia.huella_peticion(operacion, {}, {"titulo": "x"}),
        efecto=efecto,
        **extra,
    )


def test_AC_TKT004_04_repeticion_devuelve_la_respuesta_original(cuenta_id):
    llamadas: list[int] = []
    clave = uuid.uuid4()
    primera = _ejecutar(cuenta_id, clave, _efecto(llamadas, {"id": 7, "titulo": "Río"}))
    segunda = _ejecutar(cuenta_id, clave, _efecto(llamadas))
    assert len(llamadas) == 1
    assert (segunda.codigo_http, segunda.cuerpo, segunda.recurso_id) == (
        201,
        {"id": 7, "titulo": "Río"},
        7,
    )
    assert segunda.repetida is True and primera.repetida is False


def test_AC_TKT004_04_otra_operacion_con_la_misma_clave_es_422(cuenta_id):
    clave = uuid.uuid4()
    _ejecutar(cuenta_id, clave, _efecto([]))
    with pytest.raises(idempotencia.IdempotenciaConflicto):
        _ejecutar(cuenta_id, clave, _efecto([]), operacion="panelCrearGuia")


def test_AC_TKT004_04_huella_canonica(cuenta_id):
    uno = idempotencia.huella_peticion("panelCrearDestino", {"id": 1}, {"b": 1, "a": [1, 2]})
    dos = idempotencia.huella_peticion("panelCrearDestino", {"id": 1}, {"a": [1, 2], "b": 1})
    assert uno == dos and len(uno) == 64
    assert uno != idempotencia.huella_peticion(
        "panelCrearDestino", {"id": 2}, {"a": [1, 2], "b": 1}
    )


def test_AC_TKT004_04_clave_vencida_se_reutiliza_como_nueva(cuenta_id):
    llamadas: list[int] = []
    clave = uuid.uuid4()
    _ejecutar(cuenta_id, clave, _efecto(llamadas))
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE app.idempotencia_peticion SET creado_en = now() - interval '25 hours', "
            "expira_en = now() - interval '1 hour' WHERE clave = %s",
            [clave],
        )
    _ejecutar(cuenta_id, clave, _efecto(llamadas))
    assert len(llamadas) == 2


def test_AC_TKT004_04_respuesta_mayor_de_64_kb_no_se_reproduce(cuenta_id):
    clave = uuid.uuid4()
    _ejecutar(cuenta_id, clave, _efecto([], {"texto": "x" * 70_000}))
    with pytest.raises(idempotencia.RespuestaNoReproducible):
        _ejecutar(cuenta_id, clave, _efecto([]))


def test_AC_TKT004_04_sin_clave_se_ejecuta_siempre(cuenta_id):
    llamadas: list[int] = []
    _ejecutar(cuenta_id, None, _efecto(llamadas))
    _ejecutar(cuenta_id, None, _efecto(llamadas))
    assert len(llamadas) == 2


def test_AC_TKT004_04_validaciones_del_servicio(cuenta_id):
    with pytest.raises(ValueError, match="Operación sin idempotencia"):
        _ejecutar(cuenta_id, uuid.uuid4(), _efecto([]), operacion="panelBorrarTodo")
    with pytest.raises(ValueError, match="2xx"):
        _ejecutar(cuenta_id, uuid.uuid4(), _efecto([], codigo=400))
    with pytest.raises(ParametroInvalido):
        idempotencia.leer_clave("{12345678-1234-1234-1234-123456789012}")
    assert idempotencia.leer_clave(None) is None


def test_AC_TKT004_04_borrar_claves_de_una_cuenta(cuenta_id):
    _ejecutar(cuenta_id, uuid.uuid4(), _efecto([]))
    _ejecutar(cuenta_id, uuid.uuid4(), _efecto([]))
    assert idempotencia.borrar_claves_de_cuenta(cuenta_id) == 2


# ---------------------------------------------------------------------------
# Concurrencia: la segunda petición espera al índice único y, si vence lock_timeout, 409
# ---------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
@override_settings(IDEMPOTENCIA_LOCK_TIMEOUT_MS=500)
def test_AC_TKT004_04_duplicado_concurrente_responde_409_en_curso():
    cuenta_id = crear_staff("concurrente.idem").cuenta.pk
    clave = uuid.uuid4()
    reservada = threading.Event()
    liberar = threading.Event()
    errores: list[BaseException] = []

    def primera() -> None:
        def efecto_lento() -> idempotencia.Resultado:
            reservada.set()
            liberar.wait(10)
            return idempotencia.Resultado(codigo_http=201, cuerpo={"id": 1}, recurso_id=1)

        try:
            _ejecutar(cuenta_id, clave, efecto_lento)
        except BaseException as exc:  # pragma: no cover - solo si la prueba falla
            errores.append(exc)
        finally:
            connections.close_all()

    hilo = threading.Thread(target=primera)
    hilo.start()
    assert reservada.wait(10)
    try:
        with pytest.raises(idempotencia.IdempotenciaEnCurso) as error:
            _ejecutar(cuenta_id, clave, _efecto([]))
        assert error.value.cabeceras["Retry-After"] == "1"
    finally:
        liberar.set()
        hilo.join(10)
    assert not errores
    # Confirmada la primera, la repetición devuelve su respuesta.
    repetida = _ejecutar(cuenta_id, clave, _efecto([]))
    assert repetida.repetida and repetida.cuerpo == {"id": 1}
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM app.idempotencia_peticion WHERE clave = %s", [clave])
        assert cursor.fetchone()[0] == 1
