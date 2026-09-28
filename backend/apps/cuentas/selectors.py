"""Consultas de lectura de cuentas y de la política de tratamiento (Skill_Backend §4.3).

La política vigente (FEAT-032, DEC-AUTO-038) es la página institucional POLITICA_DATOS del
dominio `contenido`. Ese dominio aún no expone selectores (TKT-005), así que aquí se hace una
lectura directa y de solo lectura de su modelo (sin mutarlo, Skill_Backend §5).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from django.conf import settings
from django.db.models import QuerySet

from apps.contenido.models import ClavePagina, PaginaInstitucional
from apps.core.exceptions import NoEncontrado
from apps.cuentas.models import CuentaStaff, EstadoCuenta, RolCuenta

URL_POLITICA = "/politica-de-tratamiento-de-datos"
RESUMEN_FINALIDAD = (
    "Brújula Salvaje trata tu usuario, tu nombre visible, tu rol y el registro de tus acciones "
    "en el panel con estas finalidades: gestionar tu acceso y tus credenciales, proteger la "
    "seguridad del panel y dejar constancia de las acciones editoriales (auditoría durante 365 "
    "días). No se comparten con terceros. Puedes consultar, actualizar o pedir la supresión de "
    "tus datos al Administrador, conforme a la Ley 1581 de 2012."
)

# Estados con los que una sesión del panel sigue siendo válida (STATE-003/004).
ESTADOS_CON_SESION = frozenset(
    {EstadoCuenta.PENDIENTE_ACTIVACION, EstadoCuenta.ACTIVA, EstadoCuenta.BLOQUEADA_TEMPORAL}
)


@dataclass(frozen=True)
class PoliticaVigente:
    version: str
    vigente_desde: date
    resumen_finalidad: str
    url: str = URL_POLITICA


def politica_vigente() -> PoliticaVigente:
    pagina = (
        PaginaInstitucional.objects.filter(clave=ClavePagina.POLITICA_DATOS)
        .only("version_documento", "vigente_desde")
        .first()
    )
    if pagina is not None:
        return PoliticaVigente(
            version=pagina.version_documento,
            vigente_desde=pagina.vigente_desde,
            resumen_finalidad=RESUMEN_FINALIDAD,
        )
    return PoliticaVigente(
        version=settings.POLITICA_TRATAMIENTO_VERSION_RESPALDO,
        vigente_desde=date.fromisoformat(settings.POLITICA_TRATAMIENTO_VIGENTE_DESDE_RESPALDO),
        resumen_finalidad=RESUMEN_FINALIDAD,
    )


def cuenta_por_usuario(usuario: str) -> CuentaStaff | None:
    return CuentaStaff.objects.filter(usuario=usuario).first()


def cuenta_con_sesion(cuenta_id: int) -> CuentaStaff | None:
    """Cuenta de una sesión, solo si su estado admite sesión (si no, la sesión no vale)."""
    return CuentaStaff.objects.filter(pk=cuenta_id, estado__in=ESTADOS_CON_SESION).first()


def obtener_cuenta(cuenta_id: int) -> CuentaStaff:
    cuenta = CuentaStaff.objects.filter(pk=cuenta_id).first()
    if cuenta is None:
        raise NoEncontrado()
    return cuenta


def listar_cuentas(*, estado: str | None = None, rol: str | None = None) -> QuerySet[CuentaStaff]:
    cuentas = CuentaStaff.objects.all()
    if estado:
        cuentas = cuentas.filter(estado=estado)
    if rol:
        cuentas = cuentas.filter(rol=rol)
    return cuentas.order_by("creado_en", "id")


def hay_otro_administrador_activo(excluida_id: int) -> bool:
    """RULE-015: ¿queda al menos un Administrador ACTIVO distinto de `excluida_id`?"""
    return (
        CuentaStaff.objects.filter(rol=RolCuenta.ADMINISTRADOR, estado=EstadoCuenta.ACTIVA)
        .exclude(pk=excluida_id)
        .exists()
    )


def ids_cuentas_por_anonimizar(limite: datetime) -> list[int]:
    """Cuentas DESACTIVADAS antes de `limite` (plazo de anonimización, ADR-DB-004 §2)."""
    return list(
        CuentaStaff.objects.filter(estado=EstadoCuenta.DESACTIVADA, desactivado_en__lt=limite)
        .order_by("id")
        .values_list("id", flat=True)
    )
