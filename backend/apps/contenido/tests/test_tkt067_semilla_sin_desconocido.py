"""TKT-067 (AC-030, ADR-DB-004 §1.5, residual de TKT-060): la semilla completa no deja eventos de
auditoría 'desconocido'.

Antes, los ~342 eventos que registraban los servicios del panel (crear_borrador, publicar,
crear_pais, catalogar, actualizar_config_inicio) con `actor_id=None` y sin etiqueta quedaban como
'desconocido'; `cargar_semilla` los envuelve ahora en `auditar_como_sistema()`.

Carga el dataset UNA vez para el módulo dentro de una transacción que se revierte al terminar
(mismo patrón y motivo que `test_ac_tkt007_semilla.py`).
"""

from __future__ import annotations

from collections.abc import Iterator
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.db import transaction

from apps.auditoria.contexto import etiqueta_de_proceso
from apps.auditoria.models import AccionAuditoria, EventoAuditoria
from apps.auditoria.services import ETIQUETA_DESCONOCIDO, ETIQUETA_SISTEMA, registrar_evento


@pytest.fixture(scope="module")
def eventos_semilla(django_db_setup: None, django_db_blocker: Any) -> Iterator[dict[str, Any]]:
    with django_db_blocker.unblock(), transaction.atomic():
        call_command("cargar_semilla", stdout=StringIO())
        primera = list(EventoAuditoria.objects.values_list("actor_id", "actor_etiqueta", "accion"))
        # Fuera del comando el contexto ya no está activo.
        tras_comando = registrar_evento(accion=AccionAuditoria.TAXONOMIA).actor_etiqueta
        antes_segunda = EventoAuditoria.objects.count()
        call_command("cargar_semilla", stdout=StringIO())
        segunda = EventoAuditoria.objects.count() - antes_segunda
        yield {
            "primera": primera,
            "tras_comando": tras_comando,
            "segunda": segunda,
            "proceso_tras_comando": etiqueta_de_proceso(),
        }
        transaction.set_rollback(True)


@pytest.mark.django_db
def test_TKT067_AC_030_semilla_completa_sin_eventos_desconocido(
    eventos_semilla: dict[str, Any],
) -> None:
    eventos = eventos_semilla["primera"]
    assert len(eventos) > 300  # crear_borrador, publicar, crear_pais, catalogar, inicio...
    etiquetas = {etiqueta for _, etiqueta, _ in eventos}
    assert ETIQUETA_DESCONOCIDO not in etiquetas
    assert {(actor, etiqueta) for actor, etiqueta, _ in eventos} == {(None, ETIQUETA_SISTEMA)}


@pytest.mark.django_db
def test_TKT067_semilla_cubre_los_servicios_del_panel(eventos_semilla: dict[str, Any]) -> None:
    """Las acciones que antes quedaban 'desconocido' (servicios sin etiqueta) están presentes."""
    acciones = {accion for _, _, accion in eventos_semilla["primera"]}
    assert {
        AccionAuditoria.CREAR,
        AccionAuditoria.PUBLICAR,
        AccionAuditoria.TAXONOMIA,
        AccionAuditoria.EDITAR_MEDIO,
        AccionAuditoria.CONFIG_INICIO,
    } <= acciones


@pytest.mark.django_db
def test_TKT067_el_contexto_termina_con_el_comando(eventos_semilla: dict[str, Any]) -> None:
    assert eventos_semilla["proceso_tras_comando"] is None
    assert eventos_semilla["tras_comando"] == ETIQUETA_DESCONOCIDO


@pytest.mark.django_db
def test_TKT067_segunda_ejecucion_no_repite_auditoria(eventos_semilla: dict[str, Any]) -> None:
    assert eventos_semilla["segunda"] == 0
