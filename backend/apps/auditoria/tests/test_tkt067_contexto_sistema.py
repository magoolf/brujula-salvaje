"""TKT-067 (AC-030, ADR-DB-004 §1.5, DEC-AUTO-1034): contexto de proceso `auditar_como_sistema()`.

Los eventos sin actor ni etiqueta registrados dentro del bloque llevan 'sistema'; fuera de él,
el comportamiento previo no cambia ('desconocido' sin actor). El contexto nunca se impone a una
etiqueta explícita ni a un actor real (ni a su seudónimo), no alcanza a otros hilos ni a las
peticiones HTTP y se restaura aunque el bloque lance una excepción.

La semilla completa (0 eventos 'desconocido') se prueba en
`apps/contenido/tests/test_tkt067_semilla_sin_desconocido.py`.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest
from django.db import connections
from django.test import Client

from apps.auditoria.contexto import etiqueta_de_proceso
from apps.auditoria.models import AccionAuditoria, EventoAuditoria
from apps.auditoria.services import (
    ETIQUETA_DESCONOCIDO,
    ETIQUETA_SISTEMA,
    PREFIJO_SEUDONIMO,
    auditar_como_sistema,
    etiqueta_de_actor,
    registrar_evento,
)
from apps.auditoria.tests.test_ac_tkt058_etiqueta_actor import _anonimizar_en_bd
from apps.cuentas.tests.conftest import IP, post

PLAZO_S = 60


class _FalloError(Exception):
    pass


def _sin_actor() -> EventoAuditoria:
    return registrar_evento(accion=AccionAuditoria.TAXONOMIA, tipo_entidad="REGION", entidad_id=1)


def _login_usuario_inexistente(cliente: Client) -> Any:
    return post(
        cliente,
        "/auth/login",
        {"usuario": "nadie.tkt067", "contrasena": "frase-equivocada-tkt-067"},
        REMOTE_ADDR=IP,
    )


# ---------------------------------------------------------------------------
# Precedencia de la etiqueta (sin hilos)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestPrecedencia:
    def test_TKT067_AC_030_sin_actor_dentro_del_contexto_es_sistema(self) -> None:
        with auditar_como_sistema():
            evento = _sin_actor()
        evento.refresh_from_db()
        assert (evento.actor_id, evento.actor_etiqueta) == (None, ETIQUETA_SISTEMA)

    def test_TKT067_fuera_del_contexto_no_cambia_sigue_desconocido(self) -> None:
        assert etiqueta_de_proceso() is None
        assert _sin_actor().actor_etiqueta == ETIQUETA_DESCONOCIDO
        with auditar_como_sistema():
            pass
        assert _sin_actor().actor_etiqueta == ETIQUETA_DESCONOCIDO

    def test_TKT067_etiqueta_explicita_prevalece_sobre_el_contexto(self) -> None:
        with auditar_como_sistema():
            evento = registrar_evento(
                accion=AccionAuditoria.LOGIN_FALLIDO, resultado="FALLO", actor_etiqueta="otra"
            )
        assert evento.actor_etiqueta == "otra"

    def test_TKT067_actor_real_prevalece_sobre_el_contexto(self, editora: Any) -> None:
        with auditar_como_sistema():
            evento = registrar_evento(accion=AccionAuditoria.EDITAR, actor_id=editora.cuenta.pk)
        evento.refresh_from_db()
        assert (evento.actor_id, evento.actor_etiqueta) == (editora.cuenta.pk, "editora.uno")

    def test_TKT067_THREAT_013_actor_anonimizado_conserva_el_seudonimo(self, editora: Any) -> None:
        cuenta = editora.cuenta
        _anonimizar_en_bd(cuenta)
        with auditar_como_sistema():
            evento = registrar_evento(accion=AccionAuditoria.EDITAR, actor_id=cuenta.pk)
        assert evento.actor_etiqueta == f"{PREFIJO_SEUDONIMO}{cuenta.pk}"

    def test_TKT067_actor_inexistente_sigue_desconocido_en_el_contexto(self) -> None:
        """El contexto solo cubre la AUSENCIA de actor: un id sin cuenta no es 'sistema' (la FK
        impide insertarlo, así que se comprueba la resolución de la etiqueta)."""
        with auditar_como_sistema():
            assert etiqueta_de_actor(987654321) == ETIQUETA_DESCONOCIDO
            assert etiqueta_de_actor(None) == ETIQUETA_DESCONOCIDO

    def test_TKT067_se_restaura_aunque_haya_excepcion(self) -> None:
        dentro: list[str] = []

        def bloque_que_falla() -> None:
            with auditar_como_sistema():
                dentro.append(_sin_actor().actor_etiqueta)
                raise _FalloError

        with pytest.raises(_FalloError):
            bloque_que_falla()
        assert dentro == [ETIQUETA_SISTEMA]
        assert etiqueta_de_proceso() is None
        assert _sin_actor().actor_etiqueta == ETIQUETA_DESCONOCIDO

    def test_TKT067_bloques_anidados_restauran_el_valor_exterior(self) -> None:
        with auditar_como_sistema():
            with pytest.raises(_FalloError), auditar_como_sistema():
                raise _FalloError
            assert etiqueta_de_proceso() == ETIQUETA_SISTEMA
        assert etiqueta_de_proceso() is None


# ---------------------------------------------------------------------------
# Aislamiento: peticiones HTTP en el MISMO hilo que un bloque activo
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestPeticionEnElMismoHilo:
    def test_TKT067_peticion_sin_actor_durante_el_contexto_es_desconocido(self) -> None:
        with auditar_como_sistema():
            respuesta = _login_usuario_inexistente(Client(raise_request_exception=False))
            assert respuesta.status_code == 401, respuesta.content
            # Al terminar la petición, el bloque recupera su etiqueta.
            assert etiqueta_de_proceso() == ETIQUETA_SISTEMA
            despues = _sin_actor()
        fallo = EventoAuditoria.objects.get(accion=AccionAuditoria.LOGIN_FALLIDO)
        assert (fallo.actor_id, fallo.actor_etiqueta) == (None, ETIQUETA_DESCONOCIDO)
        assert despues.actor_etiqueta == ETIQUETA_SISTEMA

    def test_TKT067_peticion_del_panel_durante_el_contexto_lleva_su_usuario(
        self, cliente_editora: Client, editora: Any
    ) -> None:
        with auditar_como_sistema():
            respuesta = post(cliente_editora, "/auth/logout")
            assert respuesta.status_code == 204, respuesta.content
        salida = EventoAuditoria.objects.get(accion=AccionAuditoria.LOGOUT)
        assert (salida.actor_id, salida.actor_etiqueta) == (editora.cuenta.pk, "editora.uno")
        assert etiqueta_de_proceso() is None


# ---------------------------------------------------------------------------
# Aislamiento entre hilos (transacciones reales: cada hilo con su conexión)
# ---------------------------------------------------------------------------
class _Hilo(threading.Thread):
    """Ejecuta `objetivo` en otro hilo y guarda su resultado o su error."""

    def __init__(self, objetivo: Any) -> None:
        super().__init__()
        self.objetivo = objetivo
        self.resultado: Any = None
        self.error: BaseException | None = None

    def run(self) -> None:
        try:
            self.resultado = self.objetivo()
        except BaseException as exc:  # pragma: no cover - solo si la prueba falla
            self.error = exc
        finally:
            connections.close_all()

    def esperar(self) -> Any:
        self.join(PLAZO_S)
        assert not self.is_alive(), "el hilo no terminó a tiempo"
        if self.error is not None:
            raise self.error
        return self.resultado


@pytest.mark.django_db(transaction=True)
class TestOtrosHilos:
    def test_TKT067_otro_hilo_no_hereda_el_contexto(self) -> None:
        def en_otro_hilo() -> tuple[str | None, int]:
            return etiqueta_de_proceso(), _sin_actor().pk

        with auditar_como_sistema():
            hilo = _Hilo(en_otro_hilo)
            hilo.start()
            etiqueta_hilo, evento_hilo = hilo.esperar()
            propio = _sin_actor()

        assert etiqueta_hilo is None
        assert EventoAuditoria.objects.get(pk=evento_hilo).actor_etiqueta == ETIQUETA_DESCONOCIDO
        assert EventoAuditoria.objects.get(pk=propio.pk).actor_etiqueta == ETIQUETA_SISTEMA

    def test_TKT067_contexto_de_otro_hilo_no_alcanza_a_este(self) -> None:
        """Un proceso de sistema en curso en otro hilo no etiqueta los eventos de este."""
        dentro = threading.Event()
        soltar = threading.Event()

        def proceso_de_sistema() -> int:
            with auditar_como_sistema():
                dentro.set()
                assert soltar.wait(PLAZO_S)
                return _sin_actor().pk

        hilo = _Hilo(proceso_de_sistema)
        hilo.start()
        assert dentro.wait(PLAZO_S)
        try:
            assert etiqueta_de_proceso() is None
            propio = _sin_actor()
        finally:
            soltar.set()
        del_sistema = hilo.esperar()

        assert EventoAuditoria.objects.get(pk=propio.pk).actor_etiqueta == ETIQUETA_DESCONOCIDO
        assert EventoAuditoria.objects.get(pk=del_sistema).actor_etiqueta == ETIQUETA_SISTEMA

    def test_TKT067_peticion_http_concurrente_no_hereda_el_contexto(self) -> None:
        """Mientras un proceso de sistema está dentro del bloque, una petición atendida en otro
        hilo (como en el servidor) audita su fallo de login sin actor como 'desconocido'."""
        from django.core.cache import cache

        cache.clear()  # límites de tasa de otras pruebas transaccionales

        def peticion() -> int:
            respuesta = _login_usuario_inexistente(Client(raise_request_exception=False))
            return int(respuesta.status_code)

        with auditar_como_sistema():
            hilo = _Hilo(peticion)
            hilo.start()
            estado = hilo.esperar()
            propio = _sin_actor()

        assert estado == 401
        fallo = EventoAuditoria.objects.get(accion=AccionAuditoria.LOGIN_FALLIDO)
        assert (fallo.actor_id, fallo.actor_etiqueta) == (None, ETIQUETA_DESCONOCIDO)
        assert EventoAuditoria.objects.get(pk=propio.pk).actor_etiqueta == ETIQUETA_SISTEMA
