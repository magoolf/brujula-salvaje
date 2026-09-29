"""Reglas de publicación del panel editorial (RULE-002..006, 009, 023..027, ADR-DB-004).

Funciones puras (sin acceso a BD ni a HTTP, Skill_Backend §4.2/§4.3): reciben los datos ya
resueltos por `apps.contenido.services` (valores del borrador o del formulario en edición, más los
datos de apoyo obtenidos por selectors: medios disponibles, estado de los tipos, etc.) y devuelven
una lista de errores con la forma de `ErrorRegla` del contrato (`campo`, `code`, `mensaje`,
`referencias` opcional). Lista vacía = la entidad cumple los requisitos de publicación.

Los `CheckConstraint` del DB_HANDOFF (p. ej. `ck_contenido_publicado_portada`,
`ck_contenido_publicado_seo`, `ck_contenido_publicado_fechas`) son la defensa de último nivel; estas
funciones existen para devolver 422 `publicacion_invalida` con mensajes útiles en vez de dejar que
una violación de constraint llegue como 500.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

MINIMO_RELACIONADOS = 3
MINIMO_PALABRAS_DESCRIPCION_DESTINO = 600
MINIMO_ELEMENTOS_COLECCION = 4
MINIMO_CHECKLIST = 8

_TAG_RE = re.compile(r"<[^>]+>")


def _palabras(html: str | None) -> int:
    texto = _TAG_RE.sub(" ", html or "")
    return len(texto.split())


def _err(
    campo: str, code: str, mensaje: str, referencias: list[dict[str, object]] | None = None
) -> dict[str, object]:
    error: dict[str, object] = {"campo": campo, "code": code, "mensaje": mensaje}
    if referencias:
        error["referencias"] = referencias
    return error


def _requerido(valor: object, campo: str, mensaje: str) -> dict[str, object] | None:
    if valor in (None, "", []):
        return _err(campo, "requerido", mensaje)
    return None


def _fecha_no_futura(
    valor: date | None, campo: str = "fecha_ultima_revision"
) -> dict[str, object] | None:
    if valor is None:
        return _err(campo, "requerido", "La fecha de última revisión es obligatoria.")
    if valor > date.today():
        return _err(campo, "fecha_futura", "La fecha de última revisión no puede ser futura.")
    return None


# ---------------------------------------------------------------------------
# Datos de entrada (resueltos por services.py a partir del borrador/formulario)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DatosDestino:
    resumen: str | None
    descripcion_experta: str | None
    tipos_ids: tuple[int, ...]
    tipo_principal_id: int | None
    dificultad: int | None
    meses_mejor_epoca: tuple[int, ...]
    duracion_min_dias: int | None
    duracion_max_dias: int | None
    nivel_presupuesto: int | None
    clima: str | None
    como_llegar: str | None
    seguridad_riesgos: str | None
    sostenibilidad: str | None
    latitud: float | None
    longitud: float | None
    portada_id: int | None
    galeria_ids: tuple[int, ...]
    fecha_ultima_revision: date | None
    seo_descripcion: str | None
    medios_disponibles_en_galeria: int = 0
    relacionados_publicados: int = 0
    seo_descripcion_en_uso: bool = False


def validar_destino(d: DatosDestino) -> list[dict[str, object]]:
    """RULE-002, RULE-006, RULE-023, RULE-027. No valida el estado de los tipos (RULE-025/RULE-002
    v1.1): eso lo evalúa el orquestador multi-entidad de `services.py`, que conoce el resultado de
    la operación completa (co-publicación incluida)."""
    errores = [
        e
        for e in (
            _requerido(d.resumen, "resumen", "El resumen es obligatorio."),
            _requerido(
                d.descripcion_experta,
                "descripcion_experta",
                "La descripción experta es obligatoria.",
            ),
            _requerido(d.dificultad, "dificultad", "La dificultad es obligatoria."),
            _requerido(d.nivel_presupuesto, "nivel_presupuesto", "El presupuesto es obligatorio."),
            _requerido(d.clima, "clima", "El clima es obligatorio."),
            _requerido(d.como_llegar, "como_llegar", "Cómo llegar es obligatorio."),
            _requerido(d.seguridad_riesgos, "seguridad_riesgos", "La seguridad es obligatoria."),
            _requerido(d.sostenibilidad, "sostenibilidad", "La sostenibilidad es obligatoria."),
            _requerido(d.portada_id, "portada_id", "La portada es obligatoria."),
            _fecha_no_futura(d.fecha_ultima_revision),
            _requerido(d.seo_descripcion, "seo_descripcion", "La descripción SEO es obligatoria."),
        )
        if e is not None
    ]
    if d.resumen and len(d.resumen) > 300:
        errores.append(_err("resumen", "longitud_excedida", "Máximo 300 caracteres."))
    if (
        d.descripcion_experta
        and _palabras(d.descripcion_experta) < MINIMO_PALABRAS_DESCRIPCION_DESTINO
    ):
        errores.append(
            _err(
                "descripcion_experta",
                "minimo_palabras",
                f"Mínimo {MINIMO_PALABRAS_DESCRIPCION_DESTINO} palabras.",
            )
        )
    if not d.tipos_ids:
        errores.append(_err("tipos_ids", "requerido", "Selecciona al menos un tipo de aventura."))
    elif d.tipo_principal_id is None:
        errores.append(_err("tipo_principal_id", "requerido", "Selecciona el tipo principal."))
    elif d.tipo_principal_id not in d.tipos_ids:
        errores.append(
            _err(
                "tipo_principal_id",
                "no_pertenece",
                "El tipo principal debe estar entre los tipos del destino.",
            )
        )
    if not d.meses_mejor_epoca:
        errores.append(_err("meses_mejor_epoca", "requerido", "Selecciona al menos un mes."))
    if d.duracion_min_dias is None or d.duracion_max_dias is None:
        errores.append(
            _err("duracion_min_dias", "requerido", "La duración mínima y máxima son obligatorias.")
        )
    elif d.duracion_min_dias > d.duracion_max_dias:
        errores.append(
            _err(
                "duracion_min_dias",
                "rango_invalido",
                "La duración mínima no puede superar la máxima.",
            )
        )
    if d.latitud is None or d.longitud is None:
        errores.append(_err("latitud", "requerido", "Las coordenadas son obligatorias."))
    if d.medios_disponibles_en_galeria < 3:
        errores.append(
            _err(
                "galeria_ids",
                "minimo_medios",
                "Se necesitan al menos 3 medios DISPONIBLES en la galería.",
            )
        )
    if d.relacionados_publicados < MINIMO_RELACIONADOS:
        errores.append(
            _err(
                "_general",
                "relacionados_insuficientes",
                f"Se necesitan al menos {MINIMO_RELACIONADOS} contenidos relacionados publicados.",
            )
        )
    if d.seo_descripcion_en_uso:
        errores.append(
            _err(
                "seo_descripcion",
                "seo_duplicado",
                "Ya hay otro contenido publicado con esta descripción SEO.",
            )
        )
    return errores


@dataclass(frozen=True)
class DatosItinerario:
    destino_id: int | None
    destino_estado: str | None
    resumen: str | None
    duracion_dias: int | None
    dificultad: int | None
    tipos_ids: tuple[int, ...]
    tipos_estados: tuple[str, ...]
    riesgos_seguridad: str | None
    portada_id: int | None
    fecha_ultima_revision: date | None
    seo_descripcion: str | None
    numeros_dia: tuple[int, ...]
    dias_completos: bool
    relacionados_publicados: int = 0
    seo_descripcion_en_uso: bool = False


def validar_itinerario(d: DatosItinerario) -> list[dict[str, object]]:
    """RULE-003, RULE-006, RULE-027."""
    errores = [
        e
        for e in (
            _requerido(d.destino_id, "destino_id", "El destino es obligatorio."),
            _requerido(d.resumen, "resumen", "El resumen es obligatorio."),
            _requerido(d.duracion_dias, "duracion_dias", "La duración es obligatoria."),
            _requerido(d.dificultad, "dificultad", "La dificultad es obligatoria."),
            _requerido(
                d.riesgos_seguridad, "riesgos_seguridad", "Riesgos y seguridad son obligatorios."
            ),
            _requerido(d.portada_id, "portada_id", "La portada es obligatoria."),
            _fecha_no_futura(d.fecha_ultima_revision),
            _requerido(d.seo_descripcion, "seo_descripcion", "La descripción SEO es obligatoria."),
        )
        if e is not None
    ]
    if d.destino_id is not None and d.destino_estado != "PUBLICADO":
        errores.append(
            _err("destino_id", "destino_no_publicado", "El destino debe estar publicado.")
        )
    if not d.tipos_ids:
        errores.append(_err("tipos_ids", "requerido", "Selecciona al menos un tipo de aventura."))
    no_publicados = [
        t for t, estado in zip(d.tipos_ids, d.tipos_estados, strict=False) if estado != "PUBLICADO"
    ]
    if no_publicados:
        errores.append(
            _err(
                "tipos_ids",
                "itinerario_tipo_no_publicado",
                "Todos los tipos del itinerario deben estar publicados.",
            )
        )
    if d.duracion_dias is not None:
        if not d.dias_completos:
            errores.append(
                _err("dias", "dias_incompletos", "Cada día necesita título y actividades.")
            )
        elif len(d.numeros_dia) != d.duracion_dias or set(d.numeros_dia) != set(
            range(1, d.duracion_dias + 1)
        ):
            errores.append(
                _err(
                    "dias", "dias_no_coinciden", "El número de días debe coincidir con la duración."
                )
            )
    if d.relacionados_publicados < MINIMO_RELACIONADOS:
        errores.append(
            _err(
                "_general",
                "relacionados_insuficientes",
                f"Se necesitan al menos {MINIMO_RELACIONADOS} contenidos relacionados publicados.",
            )
        )
    if d.seo_descripcion_en_uso:
        errores.append(
            _err(
                "seo_descripcion",
                "seo_duplicado",
                "Ya hay otro contenido publicado con esta descripción SEO.",
            )
        )
    return errores


@dataclass(frozen=True)
class DatosGuia:
    categoria_id: int | None
    resumen: str | None
    cuerpo: str | None
    portada_id: int | None
    fecha_ultima_revision: date | None
    seo_descripcion: str | None
    remite_a_metodologia: bool
    numero_fuentes: int
    relacionados_publicados: int = 0
    seo_descripcion_en_uso: bool = False


def validar_guia(d: DatosGuia) -> list[dict[str, object]]:
    """RULE-004, RULE-006, RULE-027."""
    errores = [
        e
        for e in (
            _requerido(d.categoria_id, "categoria_id", "La categoría es obligatoria."),
            _requerido(d.resumen, "resumen", "El resumen es obligatorio."),
            _requerido(d.cuerpo, "cuerpo", "El cuerpo es obligatorio."),
            _requerido(d.portada_id, "portada_id", "La portada es obligatoria."),
            _fecha_no_futura(d.fecha_ultima_revision),
            _requerido(d.seo_descripcion, "seo_descripcion", "La descripción SEO es obligatoria."),
        )
        if e is not None
    ]
    if not d.remite_a_metodologia and d.numero_fuentes < 1:
        errores.append(
            _err(
                "fuentes", "requerido", "Añade al menos una fuente o marca «remite a metodología»."
            )
        )
    if d.relacionados_publicados < MINIMO_RELACIONADOS:
        errores.append(
            _err(
                "_general",
                "relacionados_insuficientes",
                f"Se necesitan al menos {MINIMO_RELACIONADOS} contenidos relacionados publicados.",
            )
        )
    if d.seo_descripcion_en_uso:
        errores.append(
            _err(
                "seo_descripcion",
                "seo_duplicado",
                "Ya hay otro contenido publicado con esta descripción SEO.",
            )
        )
    return errores


@dataclass(frozen=True)
class DatosTipoAventura:
    resumen: str | None
    descripcion: str | None
    portada_id: int | None
    fecha_ultima_revision: date | None
    seo_descripcion: str | None
    numero_checklist: int
    destinos_publicados: int
    relacionados_publicados: int = 0
    seo_descripcion_en_uso: bool = False


def validar_tipo_aventura(
    d: DatosTipoAventura, *, exigir_destino_publicado: bool = True
) -> list[dict[str, object]]:
    """Campos propios + RULE-025 checklist Should + RULE-006. RULE-025 (≥1 destino publicado) se
    reporta aquí con `tipo_sin_destino_publicado` cuando `exigir_destino_publicado` (el llamante
    decide: en co-publicación el destino se publica en la misma operación)."""
    errores = [
        e
        for e in (
            _requerido(d.resumen, "resumen", "El resumen es obligatorio."),
            _requerido(d.descripcion, "descripcion", "La descripción es obligatoria."),
            _requerido(d.portada_id, "portada_id", "La portada es obligatoria."),
            _fecha_no_futura(d.fecha_ultima_revision),
            _requerido(d.seo_descripcion, "seo_descripcion", "La descripción SEO es obligatoria."),
        )
        if e is not None
    ]
    if 0 < d.numero_checklist < MINIMO_CHECKLIST:
        errores.append(
            _err(
                "checklist",
                "checklist_insuficiente",
                "La lista de comprobación necesita al menos 8 elementos.",
            )
        )
    if d.relacionados_publicados < MINIMO_RELACIONADOS:
        errores.append(
            _err(
                "_general",
                "relacionados_insuficientes",
                f"Se necesitan al menos {MINIMO_RELACIONADOS} contenidos relacionados publicados.",
            )
        )
    if exigir_destino_publicado and d.destinos_publicados < 1:
        errores.append(
            _err(
                "_general",
                "tipo_sin_destino_publicado",
                "Este tipo no tiene destinos publicados. Publícalo desde uno de sus destinos "
                "en borrador.",
            )
        )
    if d.seo_descripcion_en_uso:
        errores.append(
            _err(
                "seo_descripcion",
                "seo_duplicado",
                "Ya hay otro contenido publicado con esta descripción SEO.",
            )
        )
    return errores


@dataclass(frozen=True)
class DatosColeccion:
    portada_id: int | None
    fecha_ultima_revision: date | None
    seo_descripcion: str | None
    elementos_publicados: int
    seo_descripcion_en_uso: bool = False


def validar_coleccion(d: DatosColeccion) -> list[dict[str, object]]:
    """RULE-024, RULE-027 (+ portada/fecha/seo por `ck_contenido_publicado_*`)."""
    errores = [
        e
        for e in (
            _requerido(d.portada_id, "portada_id", "La portada es obligatoria."),
            _fecha_no_futura(d.fecha_ultima_revision),
            _requerido(d.seo_descripcion, "seo_descripcion", "La descripción SEO es obligatoria."),
        )
        if e is not None
    ]
    if d.elementos_publicados < MINIMO_ELEMENTOS_COLECCION:
        errores.append(
            _err(
                "elementos",
                "elementos_insuficientes",
                f"Se necesitan al menos {MINIMO_ELEMENTOS_COLECCION} elementos publicados.",
            )
        )
    if d.seo_descripcion_en_uso:
        errores.append(
            _err(
                "seo_descripcion",
                "seo_duplicado",
                "Ya hay otro contenido publicado con esta descripción SEO.",
            )
        )
    return errores


@dataclass(frozen=True)
class DatosTermino:
    fecha_ultima_revision: date | None
    vinculado_a_publicado: bool


def validar_termino(d: DatosTermino) -> list[dict[str, object]]:
    """RULE-026 + `ck_contenido_publicado_fechas` (TERMINO no exige portada ni SEO)."""
    errores = [e for e in (_fecha_no_futura(d.fecha_ultima_revision),) if e is not None]
    if not d.vinculado_a_publicado:
        errores.append(
            _err(
                "_general",
                "sin_vinculo_publicado",
                "El término debe estar vinculado a al menos un contenido publicado.",
            )
        )
    return errores


@dataclass(frozen=True)
class DatosPaginaInstitucional:
    cuerpo: str | None
    version_documento: str | None
    vigente_desde: date | None
    fecha_ultima_revision: date | None
    seo_descripcion: str | None


def validar_pagina_institucional(d: DatosPaginaInstitucional) -> list[dict[str, object]]:
    """`ck_contenido_publicado_fechas`/`_seo`: una página siempre está PUBLICADA."""
    return [
        e
        for e in (
            _requerido(d.cuerpo, "cuerpo", "El cuerpo es obligatorio."),
            _requerido(
                d.version_documento, "version_documento", "La versión del documento es obligatoria."
            ),
            _requerido(d.vigente_desde, "vigente_desde", "La fecha de vigencia es obligatoria."),
            _fecha_no_futura(d.fecha_ultima_revision),
            _requerido(d.seo_descripcion, "seo_descripcion", "La descripción SEO es obligatoria."),
        )
        if e is not None
    ]
