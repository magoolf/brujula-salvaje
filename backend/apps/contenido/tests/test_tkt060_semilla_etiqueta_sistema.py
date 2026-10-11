"""TKT-060 (ADR-DB-004 §1.5, DB_HANDOFF): los eventos de auditoría que `cargar_semilla` registra
directamente llevan `actor_etiqueta = 'sistema'` (actor_id NULL = carga semilla), no 'desconocido'.

Se prueban los dos pasos del comando que auditan sin pasar por un servicio (páginas
institucionales y primer alta de la configuración de inicio) sin ejecutar la semilla completa,
que sube ~130 fotografías (ver `test_ac_tkt007_semilla.py`).
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from apps.auditoria.models import AccionAuditoria, EventoAuditoria
from apps.auditoria.services import ETIQUETA_SISTEMA
from apps.contenido.management.commands.cargar_semilla import Command
from apps.contenido.models import TipoContenido
from apps.contenido.tests import publicos
from apps.inicio.models import ID_SINGLETON, ConfigInicio
from seed import destinos as seed_destinos
from seed import guias as seed_guias
from seed import itinerarios as seed_itinerarios
from seed import paginas as seed_paginas

T = TipoContenido
pytestmark = pytest.mark.django_db


def _comando() -> Command:
    comando = Command()
    comando._contador = {"creados": 0, "reutilizados": 0, "publicados": 0}
    comando.fecha_revision = date.today()
    return comando


def _pares(entidades: list[str], ids: list[int]) -> dict[str, SimpleNamespace]:
    return {slug: SimpleNamespace(pk=pk) for slug, pk in zip(entidades, ids, strict=True)}


def test_TKT060_paginas_institucionales_auditadas_como_sistema() -> None:
    paginas = _comando()._cargar_paginas()

    eventos = list(
        EventoAuditoria.objects.filter(accion=AccionAuditoria.CREAR, tipo_entidad=T.PAGINA)
    )
    assert len(eventos) == len(seed_paginas.PAGINAS) == len(paginas)
    assert {(e.actor_id, e.actor_etiqueta) for e in eventos} == {(None, ETIQUETA_SISTEMA)}


def test_TKT060_paginas_reutilizadas_no_repiten_auditoria() -> None:
    _comando()._cargar_paginas()
    _comando()._cargar_paginas()

    assert EventoAuditoria.objects.filter(tipo_entidad=T.PAGINA).count() == len(
        seed_paginas.PAGINAS
    )


def test_TKT060_primera_configuracion_de_inicio_auditada_como_sistema() -> None:
    tipo = publicos.tipo("Tipo TKT-060")
    destinos = [publicos.destino(f"Destino TKT-060 {i}", tipos=[tipo]) for i in range(6)]
    itinerarios = [
        publicos.itinerario(f"Itinerario TKT-060 {i}", destinos[i]).contenido_id for i in range(3)
    ]
    guias = [publicos.guia(f"Guía TKT-060 {i}").contenido_id for i in range(3)]
    hero = publicos.medio()
    comando = _comando()
    comando._destinos = _pares(
        [d.slug for d in seed_destinos.DESTINOS[:6]], [d.contenido_id for d in destinos]
    )
    comando._itinerarios = _pares([i.slug for i in seed_itinerarios.ITINERARIOS[:3]], itinerarios)
    comando._guias = _pares([g.slug for g in seed_guias.GUIAS[:3]], guias)
    comando._subir_imagen = lambda _asignacion: hero.pk  # type: ignore[method-assign]

    comando._configurar_inicio()

    assert ConfigInicio.objects.filter(pk=ID_SINGLETON, actualizado_por__isnull=True).exists()
    evento = EventoAuditoria.objects.get(accion=AccionAuditoria.CONFIG_INICIO)
    assert (evento.actor_id, evento.actor_etiqueta, evento.entidad_id) == (
        None,
        ETIQUETA_SISTEMA,
        ID_SINGLETON,
    )
