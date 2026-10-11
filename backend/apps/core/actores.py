"""Referencia al actor de un cambio (components.schemas.ActorRef) para las respuestas del panel.

Criterio único (TKT-057/058/062, AC-030, DEC-AUTO-1028):

- cuenta con usuario: su nombre de usuario (identificador laboral interno, visible solo para el
  personal del panel; nunca en respuestas públicas ni en logs);
- cuenta ANONIMIZADA (usuario NULL): el seudónimo "Cuenta anonimizada #<id>", el mismo que pone
  app.fn_auditoria_seudonimizar (ADR-DB-004 §1, THREAT-013);
- sin actor (carga semilla, tareas): "sistema".

Infraestructura (Skill_Backend Regla 10): no importa nada de `apps/`; la cuenta es el modelo de
usuario configurado (`get_user_model()`) y se trata por su `USERNAME_FIELD`.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Model

ETIQUETA_SISTEMA = "sistema"
PREFIJO_SEUDONIMO = "Cuenta anonimizada #"


def etiqueta_de_cuenta(cuenta_id: int, usuario: str | None) -> str:
    """Usuario de la cuenta o, si está anonimizada (sin usuario), su seudónimo."""
    return str(usuario) if usuario else f"{PREFIJO_SEUDONIMO}{cuenta_id}"


def actor_ref(cuenta: Any | None) -> dict[str, Any]:
    """components.schemas.ActorRef de una cuenta YA cargada (o None = "sistema").

    No consulta la BD: el llamante carga la cuenta con `select_related` o `precargar_actores`."""
    if cuenta is None:
        return {"id": None, "etiqueta": ETIQUETA_SISTEMA}
    return {"id": cuenta.pk, "etiqueta": etiqueta_de_cuenta(cuenta.pk, cuenta.get_username())}


def precargar_actores(instancias: Iterable[Model], *campos: str) -> None:
    """Carga en UNA consulta las cuentas de las FK `campos` de `instancias` que aún no estén en
    caché (sin N+1, Skill_Backend §8): las ya traídas con `select_related` no cuestan nada y una FK
    NULL se cachea como None. Tras llamarla, `getattr(instancia, campo)` no consulta la BD."""
    pendientes: list[tuple[Model, Any, int]] = []
    for instancia in instancias:
        for campo in campos:
            fk: Any = instancia._meta.get_field(campo)
            if fk.is_cached(instancia):
                continue
            cuenta_id = getattr(instancia, fk.attname)
            if cuenta_id is None:
                fk.set_cached_value(instancia, None)
            else:
                pendientes.append((instancia, fk, cuenta_id))
    if not pendientes:
        return
    modelo: Any = get_user_model()
    ids = {cuenta_id for _, _, cuenta_id in pendientes}
    cuentas = modelo._default_manager.filter(pk__in=ids).only("pk", modelo.USERNAME_FIELD)
    por_id = {cuenta.pk: cuenta for cuenta in cuentas}
    for instancia, fk, cuenta_id in pendientes:
        if cuenta_id in por_id:
            fk.set_cached_value(instancia, por_id[cuenta_id])
