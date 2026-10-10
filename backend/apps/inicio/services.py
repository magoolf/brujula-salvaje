"""Configuración del inicio, del sitio y tablero del panel (FEAT-043, FEAT-047, FEAT-049,
RULE-016, DATA-021/022/023).

`ConfigInicio` y `ConfigSitio` son singletons (`id = 1`, DB_HANDOFF); se actualizan siempre por
UPDATE, nunca se crean ni se borran filas nuevas. Toda escritura audita `CONFIG_INICIO` o
`CONFIG_SITIO` en la misma transacción (ADR-DB-004 §1).
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.auditoria import services as auditoria
from apps.auditoria.models import AccionAuditoria
from apps.contenido.models import (
    Coleccion,
    Contenido,
    ElementoColeccion,
    EstadoEditorial,
    TipoContenido,
)
from apps.core.exceptions import ErrorApi, NoEncontrado
from apps.inicio import selectors
from apps.inicio.models import (
    ID_SINGLETON,
    ConfigInicio,
    ConfigSitio,
    DestacadoInicio,
    SeccionInicio,
)
from apps.medios.models import EstadoMedio, Medio

T = TipoContenido
E = EstadoEditorial

SECCION_TIPO: dict[str, str] = {
    SeccionInicio.DESTINOS: T.DESTINO,
    SeccionInicio.ITINERARIOS: T.ITINERARIO,
    SeccionInicio.GUIAS: T.GUIA,
}
MINIMOS_SECCION: dict[str, int] = {
    SeccionInicio.DESTINOS: 6,
    SeccionInicio.ITINERARIOS: 3,
    SeccionInicio.GUIAS: 3,
}


class ReglaNegocio(ErrorApi):
    codigo = "regla_negocio"


def obtener_config_inicio() -> ConfigInicio:
    """Singleton con autor y medio del hero cargados (`selectors.config_inicio_panel`, TKT-057)."""
    config = selectors.config_inicio_panel()
    if config is None:
        raise NoEncontrado()
    return config


def _validar_seccion(seccion: str, ids: list[int]) -> None:
    tipo = SECCION_TIPO[seccion]
    minimo = MINIMOS_SECCION[seccion]
    if len(ids) < minimo:
        raise ReglaNegocio(
            errors={f"{seccion.lower()}_ids": [f"Se necesitan al menos {minimo} elementos."]}
        )
    publicados = set(
        Contenido.objects.filter(pk__in=ids, tipo=tipo, estado_editorial=E.PUBLICADO).values_list(
            "pk", flat=True
        )
    )
    if publicados != set(ids):
        raise ReglaNegocio(
            errors={
                f"{seccion.lower()}_ids": [
                    "Todos los elementos deben estar publicados y ser del tipo correcto."
                ]
            }
        )


def actualizar_config_inicio(actor_id: int, datos: dict[str, Any]) -> ConfigInicio:
    with transaction.atomic():
        config = ConfigInicio.objects.select_for_update().filter(pk=ID_SINGLETON).first()
        if config is None:
            raise NoEncontrado()
        medio = Medio.objects.filter(
            pk=datos["hero_medio_id"], estado=EstadoMedio.DISPONIBLE
        ).first()
        if medio is None:
            raise ReglaNegocio(errors={"hero_medio_id": ["El medio debe estar DISPONIBLE."]})
        secciones = {
            SeccionInicio.DESTINOS: datos["destinos_ids"],
            SeccionInicio.ITINERARIOS: datos["itinerarios_ids"],
            SeccionInicio.GUIAS: datos["guias_ids"],
        }
        for seccion, ids in secciones.items():
            _validar_seccion(seccion, ids)

        config.hero_titular = datos["hero_titular"]
        config.hero_subtitulo = datos["hero_subtitulo"]
        config.hero_medio_id = datos["hero_medio_id"]
        config.actualizado_por_id = actor_id
        config.actualizado_en = timezone.now()
        config.save()

        DestacadoInicio.objects.all().delete()
        filas = [
            DestacadoInicio(
                seccion=seccion,
                contenido_id=cid,
                tipo_contenido=SECCION_TIPO[seccion],
                orden=indice,
            )
            for seccion, ids in secciones.items()
            for indice, cid in enumerate(ids)
        ]
        DestacadoInicio.objects.bulk_create(filas)
        auditoria.registrar_evento(
            accion=AccionAuditoria.CONFIG_INICIO,
            actor_id=actor_id,
            tipo_entidad="CONFIG_INICIO",
            entidad_id=ID_SINGLETON,
        )
    # Relectura con las relaciones que pinta la respuesta (TKT-057): la fila bloqueada no las
    # trae y serializarla dispararía una consulta por relación.
    return obtener_config_inicio()


def obtener_config_sitio() -> ConfigSitio:
    config = ConfigSitio.objects.filter(pk=ID_SINGLETON).first()
    if config is None:
        raise NoEncontrado()
    return config


def actualizar_config_sitio(actor_id: int, datos: dict[str, Any]) -> ConfigSitio:
    with transaction.atomic():
        config = ConfigSitio.objects.select_for_update().filter(pk=ID_SINGLETON).first()
        if config is None:
            raise NoEncontrado()
        for campo, valor in datos.items():
            setattr(config, campo, valor)
        config.actualizado_por_id = actor_id
        config.actualizado_en = timezone.now()
        config.save()
        auditoria.registrar_evento(
            accion=AccionAuditoria.CONFIG_SITIO,
            actor_id=actor_id,
            tipo_entidad="CONFIG_SITIO",
            entidad_id=ID_SINGLETON,
        )
        return config


# ---------------------------------------------------------------------------
# Tablero (FEAT-049)
# ---------------------------------------------------------------------------
def _conteos() -> list[dict[str, Any]]:
    conteos = []
    for tipo in (T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO, T.COLECCION, T.TERMINO, T.PAGINA):
        qs = Contenido.objects.filter(tipo=tipo)
        conteos.append(
            {
                "tipo": tipo,
                "borrador": qs.filter(estado_editorial=E.BORRADOR).count(),
                "publicado": qs.filter(estado_editorial=E.PUBLICADO).count(),
                "retirado": qs.filter(estado_editorial=E.RETIRADO).count(),
            }
        )
    return conteos


def _recientes() -> list[Contenido]:
    return list(
        Contenido.objects.select_related("actualizado_por").order_by("-actualizado_en", "-id")[:10]
    )


def _alertas(*, es_administrador: bool) -> list[dict[str, Any]]:
    alertas: list[dict[str, Any]] = []
    if es_administrador:
        config = ConfigSitio.objects.filter(pk=ID_SINGLETON).first()
        if config is None or not config.responsable_nombre:
            alertas.append(
                {
                    "code": "responsable_sin_definir",
                    "mensaje": "Falta definir el Responsable en la configuración del sitio.",
                    "enlace": "/panel/configuracion",
                }
            )
    for destacado in DestacadoInicio.objects.select_related("contenido").exclude(
        contenido__estado_editorial=E.PUBLICADO
    ):
        alertas.append(
            {
                "code": "destacado_retirado",
                "mensaje": f"El destacado «{destacado.contenido.titulo}» ya no está publicado.",
                "enlace": "/panel/inicio",
            }
        )
    for coleccion in Coleccion.objects.filter(
        contenido__estado_editorial=E.PUBLICADO
    ).select_related("contenido"):
        publicados = ElementoColeccion.objects.filter(
            coleccion=coleccion, contenido__estado_editorial=E.PUBLICADO
        ).count()
        if publicados < 4:
            alertas.append(
                {
                    "code": "coleccion_bajo_minimo",
                    "mensaje": (
                        f"La colección «{coleccion.contenido.titulo}» tiene menos de 4 "
                        "elementos publicados."
                    ),
                    "enlace": f"/panel/contenidos/colecciones/{coleccion.pk}",
                }
            )
    return alertas[:20]


def tablero(*, es_administrador: bool) -> dict[str, Any]:
    return {
        "conteos": _conteos(),
        "recientes": _recientes(),
        "alertas": _alertas(es_administrador=es_administrador),
        "salud_editorial": None,
    }
