"""Ciclo editorial del panel: CRUD, vista previa, publicar/retirar/reactivar, revisiones.

Fuente: BLUEPRINT STATE-001, RULE-002..009, 023..027, CHG-BP-001/CHG-API-005 (co-publicación
Destino+Tipos, retiro en cascada Destino→Itinerarios+Tipos), ADR-DB-004 (revisiones/auditoría),
contracts/openapi.yaml (`panel-ciclo-editorial`). Es la única capa que muta contenido editorial
(Skill_Backend §4.2): la API (apps.contenido.api.panel_views) solo transporta.

Bloqueo optimista: cada mutación exige `version` y la compara con `Contenido.version` bajo
`select_for_update()`; una discrepancia es 409 `conflicto_version` (AC-110). Cada operación
multi-entidad bloquea TODAS las filas implicadas (destino + sus tipos, o destino + sus itinerarios
y tipos publicados) en orden ascendente de id ANTES de validar nada (DEC-AUTO-269), de modo que dos
operaciones concurrentes nunca dejen el invariante de RULE-025 roto.
"""

from __future__ import annotations

import decimal
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import QuerySet, Value
from django.utils import timezone

from apps.auditoria import services as auditoria
from apps.auditoria.models import AccionAuditoria, MotivoRevision, RevisionContenido
from apps.busqueda import services as busqueda
from apps.contenido import reglas
from apps.contenido.models import (
    ChecklistItem,
    Coleccion,
    Contenido,
    ContenidoMedio,
    ContenidoTermino,
    Destino,
    DiaItinerario,
    ElementoColeccion,
    EstadoEditorial,
    Fuente,
    Guia,
    Itinerario,
    PaginaInstitucional,
    RelacionContenido,
    TerminoGlosario,
    TipoAventura,
    TipoContenido,
    normalizar,
)
from apps.contenido.saneado import sanear_html
from apps.core.exceptions import ErrorApi, NoEncontrado
from apps.medios.models import EstadoMedio, Medio

T = TipoContenido
E = EstadoEditorial

LIMITE_CASCADA = 200

RUTA_A_TIPO: dict[str, str] = {
    "destinos": T.DESTINO,
    "itinerarios": T.ITINERARIO,
    "guias": T.GUIA,
    "tipos-aventura": T.TIPO,
    "colecciones": T.COLECCION,
    "glosario": T.TERMINO,
    "paginas": T.PAGINA,
}
TIPO_A_RUTA = {v: k for k, v in RUTA_A_TIPO.items()}
# Tipos con el ciclo BORRADOR/PUBLICADO/RETIRADO completo (PAGINA queda fuera: AC-033).
TIPOS_CICLO_COMPLETO = frozenset({T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO, T.COLECCION, T.TERMINO})
# Tipos que usan ContenidoComunCampos (titulo/slug/fecha/seo/relaciones/terminos/fuentes).
TIPOS_CON_COMUNES = frozenset({T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO, T.COLECCION})
RELACION_NOMBRE: dict[str, str] = {
    T.DESTINO: "destino",
    T.ITINERARIO: "itinerario",
    T.GUIA: "guia",
    T.TIPO: "tipo_aventura",
    T.COLECCION: "coleccion",
    T.TERMINO: "termino_glosario",
    T.PAGINA: "pagina",
}


class TransicionInvalida(ErrorApi):
    codigo = "transicion_invalida"


class ConflictoVersion(ErrorApi):
    codigo = "conflicto_version"


class SlugInmutable(ErrorApi):
    codigo = "slug_inmutable"


class SlugEnUso(ErrorApi):
    codigo = "slug_en_uso"


class Duplicado(ErrorApi):
    codigo = "duplicado"


class PublicacionInvalida(ErrorApi):
    codigo = "publicacion_invalida"


class ReglaNegocio(ErrorApi):
    codigo = "regla_negocio"


class CascadaBloqueada(ErrorApi):
    codigo = "cascada_bloqueada"


class CascadaSinConfirmar(ErrorApi):
    codigo = "cascada_sin_confirmar"


class ImpactoModificado(ErrorApi):
    codigo = "impacto_modificado"


class DependenciaBloqueante(ErrorApi):
    codigo = "dependencia_bloqueante"


# ---------------------------------------------------------------------------
# Utilidades comunes
# ---------------------------------------------------------------------------
def _slugify(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    minusculas = re.sub(r"[^a-z0-9]+", "-", normalizado.lower()).strip("-")
    minusculas = re.sub(r"-{2,}", "-", minusculas)
    return (minusculas or "item")[:120]


def _slug_disponible(tipo: str, slug: str, excluir_id: int | None = None) -> bool:
    qs = Contenido.objects.filter(tipo=tipo, slug=slug)
    if excluir_id is not None:
        qs = qs.exclude(pk=excluir_id)
    return not qs.exists()


def _proponer_slug(tipo: str, titulo: str, excluir_id: int | None = None) -> str:
    base = _slugify(titulo)
    candidato = base
    sufijo = 2
    while not _slug_disponible(tipo, candidato, excluir_id):
        candidato = f"{base}-{sufijo}"[:120]
        sufijo += 1
    return candidato


def _referencia(contenido: Contenido) -> dict[str, Any]:
    return {
        "tipo": contenido.tipo,
        "id": contenido.pk,
        "titulo": contenido.titulo,
        "slug": contenido.slug,
        "estado_editorial": contenido.estado_editorial,
    }


def obtener_para_editar(tipo: str, contenido_id: int, *, bloquear: bool = False) -> Contenido:
    qs: QuerySet[Contenido] = Contenido.objects.filter(pk=contenido_id, tipo=tipo)
    if bloquear:
        qs = qs.select_for_update()
    contenido = qs.first()
    if contenido is None:
        raise NoEncontrado()
    return contenido


def subtipo_de(contenido: Contenido) -> Any:
    return getattr(contenido, RELACION_NOMBRE[contenido.tipo])


def _verificar_version(contenido: Contenido, version: int) -> None:
    if contenido.version != version:
        raise ConflictoVersion(
            errors={"version": ["El recurso cambió. Recarga y vuelve a intentarlo."]}
        )


def _siguiente_numero_revision(contenido_id: int) -> int:
    ultimo = (
        RevisionContenido.objects.filter(contenido_id=contenido_id)
        .order_by("-numero_revision")
        .values_list("numero_revision", flat=True)
        .first()
    )
    return (ultimo or 0) + 1


def _json_seguro(valor: Any) -> Any:
    """Convierte tipos de Python que `JSONField` no serializa (`Decimal`, `date`) a JSON."""
    if isinstance(valor, decimal.Decimal):
        return float(valor)
    if isinstance(valor, date | datetime):
        return valor.isoformat()
    if isinstance(valor, list):
        return [_json_seguro(v) for v in valor]
    return valor


def _instantanea(contenido: Contenido) -> dict[str, Any]:
    """Documento JSON de la revisión (DATA-026): todos los campos y relaciones, solo ids."""
    subtipo = subtipo_de(contenido)
    datos: dict[str, Any] = {
        "titulo": contenido.titulo,
        "slug": contenido.slug,
        "estado_editorial": contenido.estado_editorial,
        "fecha_ultima_revision": contenido.fecha_ultima_revision.isoformat()
        if contenido.fecha_ultima_revision
        else None,
        "seo_titulo": contenido.seo_titulo,
        "seo_descripcion": contenido.seo_descripcion,
        "portada_id": contenido.portada_id,
    }
    for campo in subtipo._meta.fields:
        nombre = campo.name
        if nombre in ("contenido", "tipo_contenido"):
            continue
        valor = (
            getattr(subtipo, f"{nombre}_id", None)
            if campo.is_relation
            else getattr(subtipo, nombre)
        )
        datos[nombre] = _json_seguro(valor)
    return datos


def _crear_revision(contenido: Contenido, motivo: str, actor_id: int | None) -> RevisionContenido:
    return RevisionContenido.objects.create(
        contenido=contenido,
        tipo_contenido=contenido.tipo,
        numero_revision=_siguiente_numero_revision(contenido.pk),
        motivo=motivo,
        instantanea=_instantanea(contenido),
        creado_por_id=actor_id,
    )


def _auditar(
    *,
    accion: str,
    actor_id: int | None,
    contenido: Contenido,
    campos: list[str] | None = None,
    ip: str | None = None,
) -> None:
    auditoria.registrar_evento(
        accion=accion,
        actor_id=actor_id,
        tipo_entidad=contenido.tipo,
        entidad_id=contenido.pk,
        entidad_titulo=contenido.titulo,
        campos_cambiados=campos,
        ip=ip,
    )


def _reindexar(contenido_id: int) -> None:
    busqueda.indexar(contenido_id)


# ---------------------------------------------------------------------------
# Aplicación de campos comunes y por tipo (BORRADOR: sin validar completitud)
# ---------------------------------------------------------------------------
def _aplicar_comunes(contenido: Contenido, datos: dict[str, Any]) -> list[str]:
    cambiados: list[str] = []
    if "titulo" in datos:
        contenido.titulo = datos["titulo"]
        cambiados.append("titulo")
    if "slug" in datos:
        nuevo = datos["slug"] or _proponer_slug(contenido.tipo, contenido.titulo, contenido.pk)
        if contenido.primera_publicacion_en is not None and nuevo != contenido.slug:
            raise SlugInmutable()
        if nuevo != contenido.slug and not _slug_disponible(contenido.tipo, nuevo, contenido.pk):
            raise SlugEnUso(errors={"slug": ["El slug ya está en uso."]})
        contenido.slug = nuevo
        cambiados.append("slug")
    elif contenido.pk is None:
        contenido.slug = _proponer_slug(contenido.tipo, contenido.titulo)
    if "fecha_ultima_revision" in datos:
        contenido.fecha_ultima_revision = datos["fecha_ultima_revision"]
        cambiados.append("fecha_ultima_revision")
    if "seo_titulo" in datos:
        contenido.seo_titulo = datos["seo_titulo"]
        cambiados.append("seo_titulo")
    if "seo_descripcion" in datos:
        contenido.seo_descripcion = datos["seo_descripcion"]
        cambiados.append("seo_descripcion")
    return cambiados


def _guardar_relaciones(contenido: Contenido, relaciones: list[dict[str, Any]]) -> None:
    RelacionContenido.objects.filter(origen=contenido).delete()
    filas = [
        RelacionContenido(
            origen=contenido,
            origen_tipo=contenido.tipo,
            relacionado_id=r["id"],
            relacionado_tipo=r["tipo"],
            orden=indice,
        )
        for indice, r in enumerate(relaciones)
    ]
    RelacionContenido.objects.bulk_create(filas)


def _guardar_terminos(contenido: Contenido, terminos_ids: list[int]) -> None:
    ContenidoTermino.objects.filter(contenido=contenido).delete()
    filas = [
        ContenidoTermino(contenido=contenido, tipo_contenido=contenido.tipo, termino_id=tid)
        for tid in terminos_ids
    ]
    ContenidoTermino.objects.bulk_create(filas)


def _guardar_fuentes(contenido: Contenido, fuentes: list[dict[str, Any]]) -> None:
    Fuente.objects.filter(contenido=contenido).delete()
    filas = [
        Fuente(
            contenido=contenido,
            titulo=f["titulo"],
            entidad_editora=f.get("entidad_editora"),
            url=f.get("url"),
            fecha_consulta=f.get("fecha_consulta"),
            orden=indice,
        )
        for indice, f in enumerate(fuentes)
    ]
    Fuente.objects.bulk_create(filas)


def _guardar_galeria(contenido: Contenido, medios_ids: list[int]) -> None:
    ContenidoMedio.objects.filter(contenido=contenido).delete()
    filas = [
        ContenidoMedio(
            contenido=contenido, tipo_contenido=contenido.tipo, medio_id=mid, orden=indice
        )
        for indice, mid in enumerate(medios_ids)
    ]
    ContenidoMedio.objects.bulk_create(filas)


def _aplicar_comunes_relacionales(contenido: Contenido, datos: dict[str, Any]) -> None:
    if "relaciones" in datos:
        _guardar_relaciones(contenido, datos["relaciones"])
    if "terminos_ids" in datos:
        _guardar_terminos(contenido, datos["terminos_ids"])
    if "fuentes" in datos:
        _guardar_fuentes(contenido, datos["fuentes"])


def _texto_enriquecido(valor: Any) -> Any:
    return sanear_html(valor) if isinstance(valor, str) else valor


# --------------------------------------------------------------------- Destino
def _aplicar_destino(destino: Destino, contenido: Contenido, datos: dict[str, Any]) -> None:
    for campo in (
        "resumen",
        "dificultad",
        "duracion_min_dias",
        "duracion_max_dias",
        "nivel_presupuesto",
        "altitud_max_m",
        "latitud",
        "longitud",
    ):
        if campo in datos:
            setattr(destino, campo, datos[campo])
    for campo in (
        "descripcion_experta",
        "clima",
        "como_llegar",
        "seguridad_riesgos",
        "sostenibilidad",
    ):
        if campo in datos:
            setattr(destino, campo, _texto_enriquecido(datos[campo]))
    if "pais_id" in datos:
        destino.pais_id = datos["pais_id"]
    if "meses_mejor_epoca" in datos:
        destino.meses_mejor_epoca = sorted(set(datos["meses_mejor_epoca"]))
    if "portada_id" in datos:
        contenido.portada_id = datos["portada_id"]
    if "galeria_ids" in datos:
        _guardar_galeria(contenido, datos["galeria_ids"])
    if "tipo_principal_id" in datos:
        destino.tipo_principal_id = datos["tipo_principal_id"]
    if "tipos_ids" in datos:
        # Aplicado tras el guardado (M2M, necesita PK): ver _confirmar_pendientes_m2m.
        destino._tipos_ids_pendientes = list(datos["tipos_ids"])  # type: ignore[attr-defined]


def _datos_regla_destino(destino: Destino, contenido: Contenido) -> reglas.DatosDestino:
    tipos_ids = tuple(destino.tipos_aventura.values_list("contenido_id", flat=True))
    galeria_disponibles = ContenidoMedio.objects.filter(
        contenido=contenido, medio__estado=EstadoMedio.DISPONIBLE
    ).count()
    relacionados = len(_relacionados_publicados(contenido))
    seo_en_uso = _seo_en_uso(contenido)
    return reglas.DatosDestino(
        resumen=destino.resumen,
        descripcion_experta=destino.descripcion_experta,
        tipos_ids=tipos_ids,
        tipo_principal_id=destino.tipo_principal_id,
        dificultad=destino.dificultad,
        meses_mejor_epoca=tuple(destino.meses_mejor_epoca or []),
        duracion_min_dias=destino.duracion_min_dias,
        duracion_max_dias=destino.duracion_max_dias,
        nivel_presupuesto=destino.nivel_presupuesto,
        clima=destino.clima,
        como_llegar=destino.como_llegar,
        seguridad_riesgos=destino.seguridad_riesgos,
        sostenibilidad=destino.sostenibilidad,
        latitud=float(destino.latitud) if destino.latitud is not None else None,
        longitud=float(destino.longitud) if destino.longitud is not None else None,
        portada_id=contenido.portada_id,
        galeria_ids=tuple(
            ContenidoMedio.objects.filter(contenido=contenido).values_list("medio_id", flat=True)
        ),
        fecha_ultima_revision=contenido.fecha_ultima_revision,
        seo_descripcion=contenido.seo_descripcion,
        medios_disponibles_en_galeria=galeria_disponibles,
        relacionados_publicados=relacionados,
        seo_descripcion_en_uso=seo_en_uso,
    )


# ------------------------------------------------------------------ Itinerario
def _aplicar_itinerario(
    itinerario: Itinerario, contenido: Contenido, datos: dict[str, Any]
) -> None:
    for campo in (
        "resumen",
        "duracion_dias",
        "dificultad",
        "distancia_total_km",
        "desnivel_acumulado_m",
    ):
        if campo in datos:
            setattr(itinerario, campo, datos[campo])
    if "riesgos_seguridad" in datos:
        itinerario.riesgos_seguridad = _texto_enriquecido(datos["riesgos_seguridad"])
    if "destino_id" in datos:
        itinerario.destino_id = datos["destino_id"]
    if "portada_id" in datos:
        contenido.portada_id = datos["portada_id"]
    if "galeria_ids" in datos:
        _guardar_galeria(contenido, datos["galeria_ids"])
    if "tipos_ids" in datos:
        itinerario._tipos_ids_pendientes = list(datos["tipos_ids"])  # type: ignore[attr-defined]
    if "dias" in datos:
        itinerario._dias_pendientes = datos["dias"]  # type: ignore[attr-defined]


def _datos_regla_itinerario(itinerario: Itinerario, contenido: Contenido) -> reglas.DatosItinerario:
    tipos = list(
        TipoAventura.objects.filter(itinerarios=itinerario).values_list(
            "contenido_id", "contenido__estado_editorial"
        )
    )
    dias = list(itinerario.dias.order_by("numero_dia"))
    dias_completos = all(d.titulo and d.actividades for d in dias)
    destino_estado = (
        itinerario.destino.contenido.estado_editorial if itinerario.destino is not None else None
    )
    return reglas.DatosItinerario(
        destino_id=itinerario.destino_id,
        destino_estado=destino_estado,
        resumen=itinerario.resumen,
        duracion_dias=itinerario.duracion_dias,
        dificultad=itinerario.dificultad,
        tipos_ids=tuple(t[0] for t in tipos),
        tipos_estados=tuple(t[1] for t in tipos),
        riesgos_seguridad=itinerario.riesgos_seguridad,
        portada_id=contenido.portada_id,
        fecha_ultima_revision=contenido.fecha_ultima_revision,
        seo_descripcion=contenido.seo_descripcion,
        numeros_dia=tuple(d.numero_dia for d in dias),
        dias_completos=dias_completos,
        relacionados_publicados=len(_relacionados_publicados(contenido)),
        seo_descripcion_en_uso=_seo_en_uso(contenido),
    )


# ----------------------------------------------------------------------- Guía
def _aplicar_guia(guia: Guia, contenido: Contenido, datos: dict[str, Any]) -> None:
    if "categoria_id" in datos:
        guia.categoria_id = datos["categoria_id"]
    if "resumen" in datos:
        guia.resumen = datos["resumen"]
    if "cuerpo" in datos:
        guia.cuerpo = _texto_enriquecido(datos["cuerpo"])
        guia.palabras = reglas._palabras(guia.cuerpo)
    if "remite_a_metodologia" in datos:
        guia.remite_a_metodologia = datos["remite_a_metodologia"]
    if "portada_id" in datos:
        contenido.portada_id = datos["portada_id"]
    if "destinos_ids" in datos:
        guia._destinos_ids_pendientes = list(datos["destinos_ids"])  # type: ignore[attr-defined]
    if "tipos_ids" in datos:
        guia._tipos_ids_pendientes = list(datos["tipos_ids"])  # type: ignore[attr-defined]


def _datos_regla_guia(guia: Guia, contenido: Contenido) -> reglas.DatosGuia:
    return reglas.DatosGuia(
        categoria_id=guia.categoria_id,
        resumen=guia.resumen,
        cuerpo=guia.cuerpo,
        portada_id=contenido.portada_id,
        fecha_ultima_revision=contenido.fecha_ultima_revision,
        seo_descripcion=contenido.seo_descripcion,
        remite_a_metodologia=guia.remite_a_metodologia,
        numero_fuentes=Fuente.objects.filter(contenido=contenido).count(),
        relacionados_publicados=len(_relacionados_publicados(contenido)),
        seo_descripcion_en_uso=_seo_en_uso(contenido),
    )


# ------------------------------------------------------------- Tipo de aventura
def _aplicar_tipo_aventura(tipo: TipoAventura, contenido: Contenido, datos: dict[str, Any]) -> None:
    if "resumen" in datos:
        tipo.resumen = datos["resumen"]
    if "descripcion" in datos:
        tipo.descripcion = _texto_enriquecido(datos["descripcion"])
    if "nivel_exigencia" in datos:
        tipo.nivel_exigencia = datos["nivel_exigencia"]
    if "orden" in datos:
        tipo.orden = datos["orden"]
    if "portada_id" in datos:
        contenido.portada_id = datos["portada_id"]
    if "checklist" in datos:
        tipo._checklist_pendiente = datos["checklist"]  # type: ignore[attr-defined]


def _destinos_publicados_de_tipo(tipo_id: int, *, excluir_destino_id: int | None = None) -> int:
    qs = Destino.objects.filter(tipos_aventura=tipo_id, contenido__estado_editorial=E.PUBLICADO)
    if excluir_destino_id is not None:
        qs = qs.exclude(pk=excluir_destino_id)
    return qs.count()


def _datos_regla_tipo(
    tipo: TipoAventura, contenido: Contenido, *, exigir_destino_publicado: bool = True
) -> reglas.DatosTipoAventura:
    return reglas.DatosTipoAventura(
        resumen=tipo.resumen,
        descripcion=tipo.descripcion,
        portada_id=contenido.portada_id,
        fecha_ultima_revision=contenido.fecha_ultima_revision,
        seo_descripcion=contenido.seo_descripcion,
        numero_checklist=ChecklistItem.objects.filter(tipo_aventura=tipo).count(),
        destinos_publicados=_destinos_publicados_de_tipo(tipo.pk)
        if exigir_destino_publicado
        else 1,
        relacionados_publicados=len(_relacionados_publicados(contenido)),
        seo_descripcion_en_uso=_seo_en_uso(contenido),
    )


# ------------------------------------------------------------------- Colección
def _aplicar_coleccion(coleccion: Coleccion, contenido: Contenido, datos: dict[str, Any]) -> None:
    if "resumen" in datos:
        coleccion.resumen = datos["resumen"]
    if "descripcion" in datos:
        coleccion.descripcion = _texto_enriquecido(datos["descripcion"])
    if "portada_id" in datos:
        contenido.portada_id = datos["portada_id"]
    if "elementos" in datos:
        coleccion._elementos_pendientes = datos["elementos"]  # type: ignore[attr-defined]


def _elementos_publicados(coleccion: Coleccion) -> int:
    return ElementoColeccion.objects.filter(
        coleccion=coleccion, contenido__estado_editorial=E.PUBLICADO
    ).count()


def _datos_regla_coleccion(coleccion: Coleccion, contenido: Contenido) -> reglas.DatosColeccion:
    return reglas.DatosColeccion(
        portada_id=contenido.portada_id,
        fecha_ultima_revision=contenido.fecha_ultima_revision,
        seo_descripcion=contenido.seo_descripcion,
        elementos_publicados=_elementos_publicados(coleccion),
        seo_descripcion_en_uso=_seo_en_uso(contenido),
    )


# --------------------------------------------------------------------- Término
def _aplicar_termino(termino: TerminoGlosario, contenido: Contenido, datos: dict[str, Any]) -> None:
    if "titulo" in datos:
        contenido.titulo = datos["titulo"]
    if "slug" in datos:
        nuevo = datos["slug"] or _proponer_slug(T.TERMINO, contenido.titulo, contenido.pk)
        if contenido.primera_publicacion_en is not None and nuevo != contenido.slug:
            raise SlugInmutable()
        contenido.slug = nuevo
    elif contenido.pk is None:
        contenido.slug = _proponer_slug(T.TERMINO, contenido.titulo)
    if "definicion" in datos:
        termino.definicion = datos["definicion"]
    if "fecha_ultima_revision" in datos:
        contenido.fecha_ultima_revision = datos["fecha_ultima_revision"]


def _titulo_normalizado(texto: str) -> str:
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        .lower()
    )


def _termino_duplicado(titulo: str, excluir_id: int | None = None) -> bool:
    objetivo = _titulo_normalizado(titulo)
    qs = Contenido.objects.filter(tipo=T.TERMINO)
    if excluir_id is not None:
        qs = qs.exclude(pk=excluir_id)
    return any(_titulo_normalizado(t) == objetivo for t in qs.values_list("titulo", flat=True))


def _datos_regla_termino(contenido: Contenido) -> reglas.DatosTermino:
    vinculado = ContenidoTermino.objects.filter(
        termino_id=contenido.pk, contenido__estado_editorial=E.PUBLICADO
    ).exists()
    return reglas.DatosTermino(
        fecha_ultima_revision=contenido.fecha_ultima_revision, vinculado_a_publicado=vinculado
    )


# ---------------------------------------------------------------------------
# Apoyo de reglas transversal
# ---------------------------------------------------------------------------
def _relacionados_publicados(contenido: Contenido) -> list[int]:
    if contenido.pk is None or contenido.tipo not in {T.DESTINO, T.ITINERARIO, T.GUIA, T.TIPO}:
        return []
    from apps.contenido import selectors as contenido_selectors

    return [r.contenido.pk for r in contenido_selectors.relacionados(contenido, limite=3)]


def _seo_en_uso(contenido: Contenido) -> bool:
    if not contenido.seo_descripcion:
        return False
    qs = Contenido.objects.filter(
        estado_editorial=E.PUBLICADO, seo_descripcion__iexact=contenido.seo_descripcion.strip()
    )
    if contenido.pk is not None:
        qs = qs.exclude(pk=contenido.pk)
    return qs.exists()


# ---------------------------------------------------------------------------
# Validación de la entrada contra la BD ANTES de escribir (TKT-032)
# ---------------------------------------------------------------------------
# Las FK de Django son DEFERRABLE INITIALLY DEFERRED (fallan en el COMMIT, fuera de cualquier
# `try`), las FK compuestas (id, tipo) de 0002_integridad_sql fallan en el INSERT y los CHECK que
# combinan campos (coordenadas, duración) o que dependen del saneado (longitud del HTML) no los
# puede ver el serializer. Antes cada uno de esos caminos acababa en 500 `error_interno`; ahora se
# comprueban aquí con los valores EFECTIVOS (entrada + estado guardado) y se responde 400
# `validacion` con el campo, como documenta el contrato para estas operaciones.
MENSAJE_INEXISTENTE = "No existe."
MENSAJE_HTML_LARGO = "El texto, una vez saneado, supera la longitud máxima permitida."
CAMPOS_HTML: dict[str, tuple[str, ...]] = {
    T.DESTINO: ("descripcion_experta", "como_llegar", "seguridad_riesgos", "sostenibilidad"),
    T.ITINERARIO: ("riesgos_seguridad",),
    T.GUIA: ("cuerpo",),
    T.TIPO: ("descripcion",),
    T.COLECCION: ("descripcion",),
    T.PAGINA: ("cuerpo",),
}


def _ids_existentes(modelo: Any, ids: list[int]) -> set[int]:
    if not ids:
        return set()
    return set(modelo.objects.filter(pk__in=ids).values_list("pk", flat=True))


def _referencia_unica(
    errores: dict[str, list[str]], datos: dict[str, Any], campo: str, modelo: Any
) -> None:
    valor = datos.get(campo)
    if valor is not None and not modelo.objects.filter(pk=valor).exists():
        errores[campo] = [MENSAJE_INEXISTENTE]


def _referencias_lista(
    errores: dict[str, list[str]], datos: dict[str, Any], campo: str, modelo: Any
) -> None:
    ids = list(datos.get(campo) or [])
    existentes = _ids_existentes(modelo, ids)
    for indice, valor in enumerate(ids):
        if valor not in existentes:
            errores[f"{campo}.{indice}"] = [MENSAJE_INEXISTENTE]


def _pares_existentes(pares: list[tuple[str, int]]) -> set[tuple[str, int]]:
    if not pares:
        return set()
    filas = Contenido.objects.filter(pk__in=[i for _t, i in pares]).values_list("tipo", "pk")
    return {(tipo, pk) for tipo, pk in filas}


def _validar_polimorficas(
    errores: dict[str, list[str]], datos: dict[str, Any], contenido_id: int | None
) -> None:
    """`relaciones` y `elementos` apuntan a contenido(id, tipo) por FK compuesta: el id debe
    existir CON ese tipo (ADR-DB-002), y una relación nunca apunta al propio contenido
    (`ck_relacion_contenido_distintos`)."""
    relaciones = list(datos.get("relaciones") or [])
    existentes = _pares_existentes([(r["tipo"], r["id"]) for r in relaciones])
    for indice, r in enumerate(relaciones):
        if contenido_id is not None and r["id"] == contenido_id:
            errores[f"relaciones.{indice}.id"] = [
                "Un contenido no puede relacionarse consigo mismo."
            ]
        elif (r["tipo"], r["id"]) not in existentes:
            errores[f"relaciones.{indice}.id"] = [MENSAJE_INEXISTENTE]
    elementos = list(datos.get("elementos") or [])
    existentes = _pares_existentes([(e["tipo_contenido"], e["contenido_id"]) for e in elementos])
    for indice, e in enumerate(elementos):
        if (e["tipo_contenido"], e["contenido_id"]) not in existentes:
            errores[f"elementos.{indice}.contenido_id"] = [MENSAJE_INEXISTENTE]


def _efectivo(datos: dict[str, Any], campo: str, subtipo: Any) -> Any:
    """Valor tras aplicar la entrada: el enviado o, si no viaja, el guardado (None al crear)."""
    if campo in datos:
        return datos[campo]
    return getattr(subtipo, campo, None) if subtipo is not None else None


def _validar_coherencia_destino(
    errores: dict[str, list[str]], datos: dict[str, Any], destino: Destino | None
) -> None:
    latitud = _efectivo(datos, "latitud", destino)
    longitud = _efectivo(datos, "longitud", destino)
    if (latitud is None) != (longitud is None):  # RULE-023, ck_destino_coordenadas
        campo = "latitud" if latitud is None else "longitud"
        errores[campo] = [
            "Las coordenadas se indican completas (latitud y longitud) o no se indican."
        ]
    minimo = _efectivo(datos, "duracion_min_dias", destino)
    maximo = _efectivo(datos, "duracion_max_dias", destino)
    if minimo is not None and maximo is not None and minimo > maximo:  # ck_destino_duracion
        errores["duracion_max_dias"] = ["Debe ser mayor o igual que duracion_min_dias."]
    # fk_destino_tipo_principal_en_tipos (DEFERRABLE): el principal pertenece a los tipos.
    if "tipos_ids" in datos:
        tipos = set(datos["tipos_ids"])
    elif destino is not None:
        tipos = set(destino.tipos_aventura.values_list("contenido_id", flat=True))
    else:
        tipos = set()
    principal = _efectivo(datos, "tipo_principal_id", destino)
    if principal is not None and principal not in tipos:
        errores["tipo_principal_id"] = ["Debe pertenecer a tipos_ids."]


def _validar_html_saneado(errores: dict[str, list[str]], tipo: str, datos: dict[str, Any]) -> None:
    """El saneado escapa `&`, `<` y `>` y completa etiquetas: un texto dentro del `maxLength` de
    la entrada puede superar el CHECK `ck_*_longitud` (LONGITUD_MAXIMA_TEXTO) al guardarse."""
    from apps.contenido.models import LONGITUD_MAXIMA_TEXTO

    for campo in CAMPOS_HTML.get(tipo, ()):
        valor = datos.get(campo)
        if isinstance(valor, str) and len(sanear_html(valor) or "") > LONGITUD_MAXIMA_TEXTO:
            errores[campo] = [MENSAJE_HTML_LARGO]
    for indice, dia in enumerate(datos.get("dias") or []):
        # `actividades`/`consejos` ya llegan saneados del serializer (DiaEntradaSerializer).
        for campo in ("actividades", "consejos"):
            valor = dia.get(campo)
            if isinstance(valor, str) and len(valor) > LONGITUD_MAXIMA_TEXTO:
                errores[f"dias.{indice}.{campo}"] = [MENSAJE_HTML_LARGO]


def _titulo_en_uso(tipo: str, titulo: str, excluir_id: int | None) -> bool:
    """uq_contenido_tipo_titulo_norm con la MISMA normalización de la BD (app.f_normalizar)."""
    qs = Contenido.objects.filter(tipo=tipo, titulo_norm=normalizar(Value(titulo)))
    if excluir_id is not None:
        qs = qs.exclude(pk=excluir_id)
    return qs.exists()


def _validar_entrada(tipo: str, datos: dict[str, Any], contenido: Contenido | None = None) -> None:
    """Comprueba contra la BD, sin escribir nada, lo que de otro modo violaría una FK, un CHECK o
    una UNIQUE al guardar `datos` (alta si `contenido` es None; si no, edición). 400
    `validacion` con todos los campos afectados; 409 `duplicado` si el título ya existe."""
    from apps.catalogos.models import CategoriaGuia, Pais

    subtipo = subtipo_de(contenido) if contenido is not None else None
    errores: dict[str, list[str]] = {}
    _referencia_unica(errores, datos, "portada_id", Medio)
    _referencias_lista(errores, datos, "galeria_ids", Medio)
    _referencias_lista(errores, datos, "terminos_ids", TerminoGlosario)
    _referencias_lista(errores, datos, "tipos_ids", TipoAventura)
    _validar_polimorficas(errores, datos, contenido.pk if contenido is not None else None)
    if tipo == T.DESTINO:
        _referencia_unica(errores, datos, "pais_id", Pais)
        _validar_coherencia_destino(errores, datos, subtipo)
    elif tipo == T.ITINERARIO:
        _referencia_unica(errores, datos, "destino_id", Destino)
    elif tipo == T.GUIA:
        _referencia_unica(errores, datos, "categoria_id", CategoriaGuia)
        _referencias_lista(errores, datos, "destinos_ids", Destino)
    _validar_html_saneado(errores, tipo, datos)
    if errores:
        raise ErrorApi(codigo="validacion", errors=errores)
    titulo = datos.get("titulo")
    if (
        tipo != T.TERMINO  # el término usa su propia comprobación (`_termino_duplicado`)
        and titulo is not None
        and _titulo_en_uso(tipo, titulo, contenido.pk if contenido is not None else None)
    ):
        raise Duplicado(errors={"titulo": ["Ya existe un contenido de este tipo con ese título."]})


APLICAR_CAMPOS: dict[str, Any] = {
    T.DESTINO: _aplicar_destino,
    T.ITINERARIO: _aplicar_itinerario,
    T.GUIA: _aplicar_guia,
    T.TIPO: _aplicar_tipo_aventura,
    T.COLECCION: _aplicar_coleccion,
}


def _confirmar_pendientes_m2m(subtipo: Any) -> None:
    """Aplica los M2M/`replace-all` marcados por `_aplicar_*` tras guardar el subtipo (piden PK)."""
    if isinstance(subtipo, Destino) and hasattr(subtipo, "_tipos_ids_pendientes"):
        subtipo.tipos_aventura.set(subtipo._tipos_ids_pendientes)
    if isinstance(subtipo, Itinerario):
        if hasattr(subtipo, "_tipos_ids_pendientes"):
            subtipo.tipos_aventura.set(subtipo._tipos_ids_pendientes)
        if hasattr(subtipo, "_dias_pendientes"):
            subtipo.dias.all().delete()
            DiaItinerario.objects.bulk_create(
                [DiaItinerario(itinerario=subtipo, **dia) for dia in subtipo._dias_pendientes]
            )
    if isinstance(subtipo, Guia):
        if hasattr(subtipo, "_destinos_ids_pendientes"):
            subtipo.destinos.set(subtipo._destinos_ids_pendientes)
        if hasattr(subtipo, "_tipos_ids_pendientes"):
            subtipo.tipos_aventura.set(subtipo._tipos_ids_pendientes)
    if isinstance(subtipo, TipoAventura) and hasattr(subtipo, "_checklist_pendiente"):
        subtipo.checklist.all().delete()
        ChecklistItem.objects.bulk_create(
            [ChecklistItem(tipo_aventura=subtipo, **item) for item in subtipo._checklist_pendiente]
        )
    if isinstance(subtipo, Coleccion) and hasattr(subtipo, "_elementos_pendientes"):
        subtipo.elementos.all().delete()
        ElementoColeccion.objects.bulk_create(
            [ElementoColeccion(coleccion=subtipo, **elem) for elem in subtipo._elementos_pendientes]
        )


# ---------------------------------------------------------------------------
# Crear (POST .../{tipo}) — siempre BORRADOR
# ---------------------------------------------------------------------------
def crear_borrador(
    tipo: str, actor_id: int, datos: dict[str, Any], ip: str | None = None
) -> Contenido:
    with transaction.atomic():
        _validar_entrada(tipo, datos)
        contenido = Contenido(tipo=tipo, creado_por_id=actor_id, actualizado_por_id=actor_id)
        _aplicar_comunes(contenido, datos)
        try:
            contenido.save()
        except IntegrityError as exc:
            raise Duplicado() from exc
        _aplicar_comunes_relacionales(contenido, datos)
        modelo_subtipo: dict[str, Any] = {
            T.DESTINO: Destino,
            T.ITINERARIO: Itinerario,
            T.GUIA: Guia,
            T.TIPO: TipoAventura,
            T.COLECCION: Coleccion,
            T.TERMINO: TerminoGlosario,
        }
        subtipo: Any = modelo_subtipo[tipo](contenido=contenido)
        if tipo == T.TERMINO:
            if _termino_duplicado(contenido.titulo, contenido.pk):
                raise Duplicado(errors={"titulo": ["Ya existe un término con este nombre."]})
            _aplicar_termino(subtipo, contenido, datos)
            contenido.save(update_fields=["titulo", "slug", "fecha_ultima_revision"])
        else:
            APLICAR_CAMPOS[tipo](subtipo, contenido, datos)
            # `APLICAR_CAMPOS` puede cambiar `contenido.portada_id` (Destino/Itinerario/...): sin
            # este guardado, la portada quedaba solo en memoria y nunca se persistía (AC-104).
            contenido.save(update_fields=["portada"])
        subtipo.save()
        _confirmar_pendientes_m2m(subtipo)
        _auditar(accion=AccionAuditoria.CREAR, actor_id=actor_id, contenido=contenido, ip=ip)
        return contenido


# ---------------------------------------------------------------------------
# Guardar borrador / Actualizar publicación (PUT .../{tipo}/{id})
# ---------------------------------------------------------------------------
@dataclass
class ResultadoGuardado:
    contenido: Contenido
    entidades_afectadas: list[dict[str, Any]] = field(default_factory=list)


_CAMPOS_OPERACION = {"copublicar_tipos", "confirmar_cascada", "cascada_confirmada"}


def actualizar(
    tipo: str,
    contenido_id: int,
    actor_id: int,
    datos: dict[str, Any],
    version: int,
    ip: str | None = None,
) -> ResultadoGuardado:
    with transaction.atomic():
        contenido = obtener_para_editar(tipo, contenido_id, bloquear=True)
        _verificar_version(contenido, version)
        if contenido.estado_editorial == E.RETIRADO:
            raise TransicionInvalida(detalle="Reactiva el contenido antes de editarlo.")

        operacion = {k: datos.pop(k) for k in list(datos) if k in _CAMPOS_OPERACION}
        _validar_entrada(tipo, datos, contenido)
        if tipo == T.PAGINA:
            return _actualizar_pagina(contenido, actor_id, datos, ip)

        if contenido.estado_editorial == E.BORRADOR:
            if tipo != T.DESTINO and any(
                operacion.get(k) for k in ("copublicar_tipos", "cascada_confirmada")
            ):
                raise ErrorApi(
                    codigo="campo_no_permitido",
                    errors={"copublicar_tipos": ["No permitido en borrador."]},
                )
            if (
                operacion.get("copublicar_tipos")
                or operacion.get("confirmar_cascada")
                or operacion.get("cascada_confirmada")
            ):
                raise ErrorApi(
                    codigo="campo_no_permitido",
                    errors={"copublicar_tipos": ["Solo se admite al actualizar una publicación."]},
                )
            return _guardar_borrador(contenido, actor_id, datos, ip)
        return _actualizar_publicacion(contenido, actor_id, datos, operacion, ip)


def _guardar_borrador(
    contenido: Contenido, actor_id: int, datos: dict[str, Any], ip: str | None
) -> ResultadoGuardado:
    cambiados = _aplicar_comunes(contenido, datos)
    _aplicar_comunes_relacionales(contenido, datos)
    subtipo = subtipo_de(contenido)
    if contenido.tipo == T.TERMINO:
        if "titulo" in datos and _termino_duplicado(datos["titulo"], contenido.pk):
            raise Duplicado(errors={"titulo": ["Ya existe un término con este nombre."]})
        _aplicar_termino(subtipo, contenido, datos)
    else:
        APLICAR_CAMPOS[contenido.tipo](subtipo, contenido, datos)
    contenido.actualizado_por_id = actor_id
    contenido.version += 1
    try:
        contenido.save()
        subtipo.save()
    except IntegrityError as exc:
        raise Duplicado() from exc
    _confirmar_pendientes_m2m(subtipo)
    _auditar(
        accion=AccionAuditoria.EDITAR,
        actor_id=actor_id,
        contenido=contenido,
        campos=cambiados,
        ip=ip,
    )
    return ResultadoGuardado(contenido=contenido)


def _validar_entidad_para_publicar(
    tipo: str, contenido: Contenido, subtipo: Any, *, exigir_destino_publicado: bool = True
) -> list[dict[str, Any]]:
    if tipo == T.DESTINO:
        return reglas.validar_destino(_datos_regla_destino(subtipo, contenido))
    if tipo == T.ITINERARIO:
        return reglas.validar_itinerario(_datos_regla_itinerario(subtipo, contenido))
    if tipo == T.GUIA:
        return reglas.validar_guia(_datos_regla_guia(subtipo, contenido))
    if tipo == T.TIPO:
        return reglas.validar_tipo_aventura(
            _datos_regla_tipo(
                subtipo, contenido, exigir_destino_publicado=exigir_destino_publicado
            ),
            exigir_destino_publicado=exigir_destino_publicado,
        )
    if tipo == T.COLECCION:
        return reglas.validar_coleccion(_datos_regla_coleccion(subtipo, contenido))
    if tipo == T.TERMINO:
        return reglas.validar_termino(_datos_regla_termino(contenido))
    return []


def _levantar_publicacion_invalida(errores_por_entidad: list[dict[str, Any]]) -> None:
    errors: dict[str, list[str]] = {}
    for entidad in errores_por_entidad:
        prefijo = "" if entidad["rol"] == "PRINCIPAL" else f"copublicar_tipos.{entidad['id']}."
        for err in entidad["errores"]:
            clave = (
                f"{prefijo}{err['campo']}"
                if err["campo"] != "_general"
                else (prefijo.rstrip(".") or "_general")
            )
            errors.setdefault(clave, []).append(err["mensaje"])
    raise PublicacionInvalida(
        detalle=f"Faltan requisitos de publicación en {len(errores_por_entidad)} entidad(es)."
        if len(errores_por_entidad) > 1
        else "Faltan requisitos de publicación.",
        errors=errors,
        extra={"errores_por_entidad": errores_por_entidad},
    )


def _actualizar_publicacion(
    contenido: Contenido,
    actor_id: int,
    datos: dict[str, Any],
    operacion: dict[str, Any],
    ip: str | None,
) -> ResultadoGuardado:
    if datos.get("slug") is not None and datos["slug"] != contenido.slug:
        raise SlugInmutable()
    datos.pop("slug", None)
    cambiados = _aplicar_comunes(contenido, datos)
    _aplicar_comunes_relacionales(contenido, datos)
    subtipo = subtipo_de(contenido)
    tipos_ids_previos = (
        set(subtipo.tipos_aventura.values_list("contenido_id", flat=True))
        if contenido.tipo == T.DESTINO
        else set()
    )
    if contenido.tipo == T.TERMINO:
        # TKT-012: el término no está en APLICAR_CAMPOS (igual que en `_guardar_borrador`); antes
        # actualizar un término PUBLICADO acababa en KeyError (500) en vez de guardarse.
        if "titulo" in datos and _termino_duplicado(datos["titulo"], contenido.pk):
            raise Duplicado(errors={"titulo": ["Ya existe un término con este nombre."]})
        _aplicar_termino(subtipo, contenido, datos)
    else:
        APLICAR_CAMPOS[contenido.tipo](subtipo, contenido, datos)
    tipos_quitados: set[int] = set()
    if hasattr(subtipo, "_tipos_ids_pendientes"):
        tipos_quitados = tipos_ids_previos - set(subtipo._tipos_ids_pendientes)
        subtipo.tipos_aventura.set(subtipo._tipos_ids_pendientes)
        del subtipo._tipos_ids_pendientes

    entidades_afectadas: list[dict[str, Any]] = []
    errores_por_entidad: list[dict[str, Any]] = []
    entidad_errores = _validar_entidad_para_publicar(contenido.tipo, contenido, subtipo)
    if entidad_errores:
        errores_por_entidad.append(
            {
                "tipo": contenido.tipo,
                "id": contenido.pk,
                "titulo": contenido.titulo,
                "estado_editorial": contenido.estado_editorial,
                "rol": "PRINCIPAL",
                "errores": entidad_errores,
            }
        )

    copublicados: list[TipoAventura] = []
    en_cascada: list[Contenido] = []
    if contenido.tipo == T.DESTINO:
        copublicados, errores_copub = _resolver_copublicacion(
            subtipo, operacion.get("copublicar_tipos") or []
        )
        errores_por_entidad.extend(errores_copub)
        en_cascada, bloqueos = _resolver_cascada_actualizacion(subtipo, operacion, tipos_quitados)
        if bloqueos:
            raise CascadaBloqueada(
                detalle="La retirada en cascada la bloquea contenido publicado.",
                extra={
                    "bloqueos_cascada": bloqueos,
                    "usos": _usos_de_bloqueos(bloqueos),
                    "total_usos": sum(b["total_itinerarios"] for b in bloqueos),
                },
            )

    if errores_por_entidad:
        _levantar_publicacion_invalida(errores_por_entidad)

    ahora = timezone.now()
    contenido.actualizado_por_id = actor_id
    contenido.publicado_actualizado_en = ahora
    contenido.version += 1
    contenido.save()
    subtipo.save()
    _confirmar_pendientes_m2m(subtipo)
    _crear_revision(contenido, MotivoRevision.ACTUALIZACION, actor_id)
    _auditar(
        accion=AccionAuditoria.ACTUALIZAR_PUBLICACION,
        actor_id=actor_id,
        contenido=contenido,
        campos=cambiados,
        ip=ip,
    )

    for tipo_co in copublicados:
        _confirmar_publicacion_entidad(tipo_co.contenido, actor_id, ip)
        entidades_afectadas.append(_entidad_transitada(tipo_co.contenido, origen="COPUBLICACION"))
    for entidad in en_cascada:
        _confirmar_retiro_entidad(
            entidad, actor_id, "Cascada: sin destinos publicados (RULE-025)", ip
        )
        entidades_afectadas.append(_entidad_transitada(entidad, origen="CASCADA"))

    # Reindexar DESPUÉS de confirmar TODAS las entidades de la operación (TKT-013, mismo patrón
    # que publicar()): el destino podía cambiar de tipo_principal a un tipo recién co-publicado en
    # la misma llamada; reindexarlo antes de confirmar ese tipo lo dejaba fuera del índice de
    # forma permanente (AC-129).
    _reindexar(contenido.pk)
    for tipo_co in copublicados:
        _reindexar(tipo_co.contenido.pk)

    return ResultadoGuardado(contenido=contenido, entidades_afectadas=entidades_afectadas)


def _actualizar_pagina(
    contenido: Contenido, actor_id: int, datos: dict[str, Any], ip: str | None
) -> ResultadoGuardado:
    subtipo: PaginaInstitucional = contenido.pagina
    if "titulo" in datos:
        contenido.titulo = datos["titulo"]
    if "fecha_ultima_revision" in datos:
        contenido.fecha_ultima_revision = datos["fecha_ultima_revision"]
    if "seo_titulo" in datos:
        contenido.seo_titulo = datos["seo_titulo"]
    if "seo_descripcion" in datos:
        contenido.seo_descripcion = datos["seo_descripcion"]
    if "cuerpo" in datos:
        subtipo.cuerpo = sanear_html(datos["cuerpo"]) or ""
    if "version_documento" in datos:
        subtipo.version_documento = datos["version_documento"]
    if "vigente_desde" in datos:
        subtipo.vigente_desde = datos["vigente_desde"]

    errores = reglas.validar_pagina_institucional(
        reglas.DatosPaginaInstitucional(
            cuerpo=subtipo.cuerpo,
            version_documento=subtipo.version_documento,
            vigente_desde=subtipo.vigente_desde,
            fecha_ultima_revision=contenido.fecha_ultima_revision,
            seo_descripcion=contenido.seo_descripcion,
        )
    )
    if errores:
        _levantar_publicacion_invalida(
            [
                {
                    "tipo": T.PAGINA,
                    "id": contenido.pk,
                    "titulo": contenido.titulo,
                    "estado_editorial": contenido.estado_editorial,
                    "rol": "PRINCIPAL",
                    "errores": errores,
                }
            ]
        )

    contenido.actualizado_por_id = actor_id
    contenido.publicado_actualizado_en = timezone.now()
    contenido.version += 1
    contenido.save()
    subtipo.save()
    _crear_revision(contenido, MotivoRevision.ACTUALIZACION, actor_id)
    _auditar(
        accion=AccionAuditoria.ACTUALIZAR_PUBLICACION, actor_id=actor_id, contenido=contenido, ip=ip
    )
    _reindexar(contenido.pk)
    return ResultadoGuardado(contenido=contenido)


# ---------------------------------------------------------------------------
# Eliminar borrador (DELETE)
# ---------------------------------------------------------------------------
def eliminar_borrador(
    tipo: str, contenido_id: int, actor_id: int, version: int, ip: str | None = None
) -> None:
    with transaction.atomic():
        contenido = obtener_para_editar(tipo, contenido_id, bloquear=True)
        _verificar_version(contenido, version)
        if contenido.estado_editorial != E.BORRADOR or contenido.primera_publicacion_en is not None:
            raise TransicionInvalida(detalle="Solo se puede eliminar un borrador nunca publicado.")
        _auditar(
            accion=AccionAuditoria.ELIMINAR_BORRADOR, actor_id=actor_id, contenido=contenido, ip=ip
        )
        contenido.delete()


# ---------------------------------------------------------------------------
# Publicar (POST .../publicar)
# ---------------------------------------------------------------------------
def _entidad_transitada(contenido: Contenido, *, origen: str) -> dict[str, Any]:
    ultima = (
        RevisionContenido.objects.filter(contenido_id=contenido.pk)
        .order_by("-numero_revision")
        .values_list("numero_revision", flat=True)
        .first()
    )
    return {
        "tipo": contenido.tipo,
        "id": contenido.pk,
        "titulo": contenido.titulo,
        "slug": contenido.slug,
        "estado_editorial": contenido.estado_editorial,
        "version": contenido.version,
        "numero_revision": ultima,
        "url_publica": _url_publica(contenido),
        "origen": origen,
    }


def _url_publica(contenido: Contenido) -> str | None:
    if contenido.estado_editorial != E.PUBLICADO:
        return None
    prefijos: dict[str, str] = {
        T.DESTINO: "destinos",
        T.ITINERARIO: "itinerarios",
        T.GUIA: "guias",
        T.TIPO: "tipos-aventura",
        T.COLECCION: "colecciones",
        T.TERMINO: "glosario",
        T.PAGINA: "paginas",
    }
    return f"/{prefijos[contenido.tipo]}/{contenido.slug}"


def _confirmar_publicacion_entidad(contenido: Contenido, actor_id: int, ip: str | None) -> None:
    """Confirma el estado PUBLICADO de UNA entidad. No reindexa (TKT-013): cuando una operación
    co-publica varias entidades relacionadas (p. ej. Destino + tipo_principal), reindexar aquí
    reindexaría cada una con las demás todavía en BORRADOR, y la visibilidad del Destino exige que
    su tipo_principal ya esté PUBLICADO (AC-129) -- el índice quedaría incoherente de forma
    permanente. El llamador reindexa explícitamente TODAS las entidades afectadas, una vez cada
    una, después de confirmar el estado de TODAS ellas."""
    ahora = timezone.now()
    if contenido.primera_publicacion_en is None:
        contenido.primera_publicacion_en = ahora
    contenido.publicado_actualizado_en = ahora
    contenido.estado_editorial = E.PUBLICADO
    contenido.actualizado_por_id = actor_id
    contenido.version += 1
    contenido.save()
    _crear_revision(contenido, MotivoRevision.PUBLICACION, actor_id)
    _auditar(accion=AccionAuditoria.PUBLICAR, actor_id=actor_id, contenido=contenido, ip=ip)


def _resolver_copublicacion(
    destino: Destino, copublicar_tipos: list[dict[str, Any]]
) -> tuple[list[TipoAventura], list[dict[str, Any]]]:
    tipos_actuales = list(
        TipoAventura.objects.select_for_update()
        .filter(destinos=destino)
        .select_related("contenido")
        .order_by("contenido_id")
    )
    pedidos = {t["id"]: t["version"] for t in copublicar_tipos}
    ids_actuales = {t.pk for t in tipos_actuales}
    errores_principal: list[dict[str, Any]] = []
    errores_por_tipo: list[dict[str, Any]] = []
    en_conflicto: list[dict[str, Any]] = []
    a_copublicar: list[TipoAventura] = []

    for tid in pedidos:
        if tid not in ids_actuales:
            errores_principal.append(
                reglas._err(
                    "tipos_ids",
                    "copublicacion_tipo_no_asociado",
                    "El tipo no pertenece a este destino.",
                )
            )

    for tipo in tipos_actuales:
        c = tipo.contenido
        if c.estado_editorial == E.RETIRADO:
            errores_principal.append(
                reglas._err(
                    "tipos_ids",
                    "tipo_retirado",
                    f"Reactiva primero el tipo {c.titulo}.",
                    [_referencia(c)],
                )
            )
        elif c.estado_editorial == E.BORRADOR:
            if tipo.pk in pedidos:
                if c.version != pedidos[tipo.pk]:
                    en_conflicto.append(_referencia(c))
                else:
                    a_copublicar.append(tipo)
            else:
                errores_principal.append(
                    reglas._err(
                        "tipos_ids",
                        "tipo_no_publicado",
                        f"El tipo {c.titulo} debe publicarse junto con el destino.",
                        [_referencia(c)],
                    )
                )
    for tipo in a_copublicar:
        errores_tipo = _validar_entidad_para_publicar(
            T.TIPO, tipo.contenido, tipo, exigir_destino_publicado=False
        )
        if errores_tipo:
            errores_por_tipo.append(
                {
                    "tipo": T.TIPO,
                    "id": tipo.pk,
                    "titulo": tipo.contenido.titulo,
                    "estado_editorial": tipo.contenido.estado_editorial,
                    "rol": "COPUBLICACION",
                    "errores": errores_tipo,
                }
            )
    if en_conflicto:
        raise ConflictoVersion(extra={"entidades_en_conflicto": en_conflicto})
    resultado_errores: list[dict[str, Any]] = list(errores_por_tipo)
    if errores_principal:
        resultado_errores.insert(
            0,
            {
                "tipo": T.DESTINO,
                "id": destino.pk,
                "titulo": destino.contenido.titulo,
                "estado_editorial": destino.contenido.estado_editorial,
                "rol": "PRINCIPAL",
                "errores": errores_principal,
            },
        )
    return a_copublicar, resultado_errores


def publicar(
    tipo: str,
    contenido_id: int,
    actor_id: int,
    version: int,
    copublicar_tipos: list[dict[str, Any]] | None,
    ip: str | None = None,
) -> tuple[Contenido, list[dict[str, Any]]]:
    copublicar_tipos = copublicar_tipos or []
    if tipo != T.DESTINO and copublicar_tipos:
        raise ErrorApi(
            codigo="campo_no_permitido",
            errors={"copublicar_tipos": ["Solo se admite en destinos."]},
        )
    with transaction.atomic():
        contenido = obtener_para_editar(tipo, contenido_id, bloquear=True)
        if contenido.estado_editorial != E.BORRADOR:
            raise TransicionInvalida()
        if contenido.version != version:
            raise ConflictoVersion(extra={"entidades_en_conflicto": [_referencia(contenido)]})
        subtipo = subtipo_de(contenido)

        copublicados: list[TipoAventura] = []
        errores_por_entidad: list[dict[str, Any]] = []
        if tipo == T.DESTINO:
            copublicados, errores_por_entidad = _resolver_copublicacion(subtipo, copublicar_tipos)
        errores_principal = _validar_entidad_para_publicar(
            tipo, contenido, subtipo, exigir_destino_publicado=(tipo != T.TIPO or False)
        )
        if tipo == T.TIPO:
            # Publicar un tipo por sí solo (sin pasar por un destino) exige que ya tenga un
            # destino PUBLICADO (RULE-025): no hay co-publicación desde el propio tipo.
            errores_principal = _validar_entidad_para_publicar(
                tipo, contenido, subtipo, exigir_destino_publicado=True
            )
        if errores_principal and not any(e.get("rol") == "PRINCIPAL" for e in errores_por_entidad):
            errores_por_entidad = [
                {
                    "tipo": tipo,
                    "id": contenido.pk,
                    "titulo": contenido.titulo,
                    "estado_editorial": contenido.estado_editorial,
                    "rol": "PRINCIPAL",
                    "errores": errores_principal,
                },
                *errores_por_entidad,
            ]
        if errores_por_entidad:
            _levantar_publicacion_invalida(errores_por_entidad)

        _confirmar_publicacion_entidad(contenido, actor_id, ip)
        afectadas = [_entidad_transitada(contenido, origen="PRINCIPAL")]
        for tipo_co in copublicados:
            _confirmar_publicacion_entidad(tipo_co.contenido, actor_id, ip)
            afectadas.append(_entidad_transitada(tipo_co.contenido, origen="COPUBLICACION"))

        # Reindexar DESPUÉS de confirmar TODAS las entidades de la operación (TKT-013): si el
        # destino se reindexara justo tras su propia confirmación (antes de este punto), su
        # tipo_principal co-publicado seguiría en BORRADOR y el destino quedaría marcado como no
        # visible en el índice de forma permanente (AC-129), pese a estar PUBLICADO en BD.
        _reindexar(contenido.pk)
        for tipo_co in copublicados:
            _reindexar(tipo_co.contenido.pk)
        return contenido, afectadas


# ---------------------------------------------------------------------------
# Retirar (POST .../retirar) e impacto de retiro
# ---------------------------------------------------------------------------
def _itinerarios_en_cascada(destino: Destino) -> list[Contenido]:
    return list(
        Contenido.objects.filter(
            itinerario__destino=destino, estado_editorial=E.PUBLICADO
        ).order_by("id")
    )


def _tipos_en_cascada(
    destino: Destino, *, excluir_destino_id: int | None = None
) -> list[TipoAventura]:
    candidatos = TipoAventura.objects.filter(
        destinos=destino, contenido__estado_editorial=E.PUBLICADO
    )
    return [
        t
        for t in candidatos
        if _destinos_publicados_de_tipo(t.pk, excluir_destino_id=excluir_destino_id) == 0
    ]


def _bloqueos_de_cascada(
    tipos: list[TipoAventura], *, itinerarios_ya_en_cascada: set[int]
) -> list[dict[str, Any]]:
    bloqueos = []
    for tipo in tipos:
        usos = list(
            Contenido.objects.filter(itinerario__tipos_aventura=tipo, estado_editorial=E.PUBLICADO)
            .exclude(pk__in=itinerarios_ya_en_cascada)
            .order_by("id")
        )
        if usos:
            bloqueos.append(
                {
                    "tipo_aventura": _referencia(tipo.contenido),
                    "itinerarios": [_referencia(i) for i in usos],
                    "total_itinerarios": len(usos),
                }
            )
    return bloqueos


def _usos_de_bloqueos(bloqueos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usos: list[dict[str, Any]] = []
    for b in bloqueos:
        for i in b["itinerarios"]:
            usos.append(
                {
                    "tipo_entidad": "ITINERARIO",
                    "id": i["id"],
                    "titulo": i["titulo"],
                    "estado_editorial": i["estado_editorial"],
                }
            )
    return usos


def impacto_retiro(tipo: str, contenido_id: int) -> dict[str, Any]:
    contenido = obtener_para_editar(tipo, contenido_id)
    itinerarios: list[Contenido] = []
    tipos_cascada: list[TipoAventura] = []
    bloqueos_cascada: list[dict[str, Any]] = []
    if tipo == T.DESTINO:
        destino = contenido.destino
        itinerarios = _itinerarios_en_cascada(destino)
        tipos_cascada = _tipos_en_cascada(destino, excluir_destino_id=destino.pk)
        bloqueos_cascada = _bloqueos_de_cascada(
            tipos_cascada, itinerarios_ya_en_cascada={i.pk for i in itinerarios}
        )
    colecciones = [
        _referencia(e.coleccion.contenido)
        for e in ElementoColeccion.objects.filter(contenido=contenido).select_related(
            "coleccion__contenido"
        )
    ]
    destacados = list({d.seccion for d in contenido.destacados.all()})
    enlaces_entrantes = RelacionContenido.objects.filter(relacionado=contenido).count()
    return {
        "retirable": not bloqueos_cascada,
        "itinerarios_en_cascada": [_referencia(i) for i in itinerarios],
        "tipos_en_cascada": [_referencia(t.contenido) for t in tipos_cascada],
        "bloqueos_cascada": bloqueos_cascada,
        "colecciones": colecciones,
        "destacados": destacados,
        "enlaces_entrantes": enlaces_entrantes,
        "bloqueos": [],
    }


def _resolver_cascada_actualizacion(
    destino: Destino, operacion: dict[str, Any], tipos_quitados: set[int]
) -> tuple[list[Contenido], list[dict[str, Any]]]:
    """Solo tipos que "Actualizar publicación" quita del destino (no incluye itinerarios: los
    itinerarios de un destino no se retiran al editarlo, solo al retirarlo, ADR-API-002 §21.6).

    `tipos_quitados` son los ids que estaban en `tipos_ids` antes de esta operación y ya no están
    (el M2M de `destino` ya se actualizó al nuevo conjunto cuando se llega aquí): se excluye este
    destino al contar sus destinos publicados restantes, precisamente porque ya no lo referencia.
    """
    if not tipos_quitados:
        return [], []
    tipos_cascada = [
        t
        for t in TipoAventura.objects.filter(
            pk__in=tipos_quitados, contenido__estado_editorial=E.PUBLICADO
        )
        if _destinos_publicados_de_tipo(t.pk, excluir_destino_id=destino.pk) == 0
    ]
    if not tipos_cascada:
        return [], []
    bloqueos = _bloqueos_de_cascada(tipos_cascada, itinerarios_ya_en_cascada=set())
    if bloqueos:
        return [], bloqueos
    confirmada = operacion.get("cascada_confirmada")
    calculado = {(T.TIPO, t.pk) for t in tipos_cascada}
    if confirmada is not None:
        enviado = {(e["tipo"], e["id"]) for e in confirmada}
        if enviado != calculado:
            raise ImpactoModificado(
                extra={
                    "impacto_cascada": {
                        "itinerarios_en_cascada": [],
                        "tipos_en_cascada": [_referencia(t.contenido) for t in tipos_cascada],
                        "bloqueos_cascada": [],
                    }
                }
            )
    elif not operacion.get("confirmar_cascada"):
        raise CascadaSinConfirmar(
            extra={
                "impacto_cascada": {
                    "itinerarios_en_cascada": [],
                    "tipos_en_cascada": [_referencia(t.contenido) for t in tipos_cascada],
                    "bloqueos_cascada": [],
                }
            }
        )
    return [t.contenido for t in tipos_cascada], []


def _confirmar_retiro_entidad(
    contenido: Contenido, actor_id: int, motivo: str, ip: str | None
) -> None:
    contenido.estado_editorial = E.RETIRADO
    contenido.retirado_en = timezone.now()
    contenido.motivo_retiro = motivo
    contenido.actualizado_por_id = actor_id
    contenido.version += 1
    contenido.save()
    _crear_revision(contenido, MotivoRevision.RETIRO, actor_id)
    _auditar(accion=AccionAuditoria.RETIRAR, actor_id=actor_id, contenido=contenido, ip=ip)
    _reindexar(contenido.pk)


def _reindexar_dependientes_de_tipo(tipo_aventura_id: int) -> None:
    """TKT-014 (criterio de "destino dependiente" corregido en TKT-015, ver `_usos_publicados_de_
    tipo`): al retirar un Tipo DIRECTAMENTE (fuera de la cascada RULE-025 de `retirar()` con
    tipo == T.DESTINO, que ya reindexa explícitamente cada entidad que ella misma retira), ese
    Tipo puede seguir estando en `tipos_aventura` (principal o secundario, RULE-002/AC-124) de un
    Destino PUBLICADO o estar entre los tipos de un Itinerario PUBLICADO. Ninguna de esas dos
    entidades cambia su propio estado_editorial, así que `_confirmar_retiro_entidad` (que solo
    reindexa la entidad que retira, es decir, el propio Tipo) nunca las toca. Pero su visibilidad
    o su contenido indexado público SÍ cambian: q_visible()/es_visible() exige tipo_principal
    PUBLICADO para un Destino (AC-129, 404 si falta) y al menos un tipo PUBLICADO para un
    Itinerario; y, aunque el tipo sea solo secundario, RULE-001 v1.1 exige que la relación deje de
    exponerse en el Destino igualmente. Ninguno de los dos casos lo refleja BusquedaDocumento por
    sí solo. Se reindexan explícitamente aquí, igual que TKT-013 reindexa explícitamente tras
    confirmar el estado de todas las entidades de una operación.

    En el camino normal, `_usos_publicados_de_tipo` ya bloquea (TKT-015, RULE-007) cualquier
    retiro directo mientras exista un destino o itinerario publicado dependiente, así que esta
    función solo se alcanza con 0 dependientes (no encuentra nada) salvo por una publicación
    concurrente entre esa comprobación y este commit (`select_for_update()` solo bloquea la fila
    del propio Tipo): se conserva como defensa en profundidad para esa ventana de carrera, con el
    mismo criterio amplio de "destino dependiente" que `_usos_publicados_de_tipo`."""
    destinos_afectados = Destino.objects.filter(
        tipos_aventura=tipo_aventura_id, contenido__estado_editorial=E.PUBLICADO
    ).values_list("pk", flat=True)
    for destino_id in destinos_afectados:
        _reindexar(destino_id)
    itinerarios_afectados = Itinerario.objects.filter(
        tipos_aventura=tipo_aventura_id, contenido__estado_editorial=E.PUBLICADO
    ).values_list("pk", flat=True)
    for itinerario_id in itinerarios_afectados:
        _reindexar(itinerario_id)


def _usos_publicados_de_tipo(tipo_aventura_id: int) -> list[dict[str, Any]]:
    """Usos de un Tipo por contenido PUBLICADO (RULE-007, FLOW-012): retirarlo DIRECTAMENTE (fuera
    de la cascada de `retirar()` con tipo == T.DESTINO, que verifica sus propios tipos en cascada
    con `_bloqueos_de_cascada` antes de llegar aquí y nunca pasa por esta función) se bloquea si
    está en `tipos_aventura` de algún Destino PUBLICADO (principal O secundario: RULE-002/AC-124
    exige que TODOS los tipos de un destino publicado estén publicados, no solo el principal;
    FLOW-012 solo tolera sin bloquear las relaciones de guías/colecciones/destacados/relacionados,
    nunca las de un destino) o de algún Itinerario PUBLICADO. Mismo criterio "destino ⇒ tipo en
    uso" que ya usan `_destinos_publicados_de_tipo` y `_tipos_en_cascada` (M2M `tipos_aventura`
    completo, no solo `tipo_principal`) y que `_reindexar_dependientes_de_tipo` (TKT-014) también
    adopta desde TKT-015, para que las tres funciones respondan igual a la misma pregunta de
    negocio. Formato ReferenciaUso (contracts/openapi.yaml) para el `extra` de
    `DependenciaBloqueante`."""
    destinos = Contenido.objects.filter(
        destino__tipos_aventura=tipo_aventura_id, estado_editorial=E.PUBLICADO
    ).order_by("id")
    itinerarios = Contenido.objects.filter(
        itinerario__tipos_aventura=tipo_aventura_id, estado_editorial=E.PUBLICADO
    ).order_by("id")
    return [
        {
            "tipo_entidad": c.tipo,
            "id": c.pk,
            "titulo": c.titulo,
            "estado_editorial": c.estado_editorial,
        }
        for c in list(destinos) + list(itinerarios)
    ]


def retirar(
    tipo: str,
    contenido_id: int,
    actor_id: int,
    version: int,
    motivo: str,
    confirmar_cascada: bool,
    cascada_confirmada: list[dict[str, Any]] | None,
    ip: str | None = None,
) -> tuple[Contenido, list[dict[str, Any]]]:
    if tipo == T.PAGINA:
        raise TransicionInvalida(detalle="Las páginas institucionales no se retiran.")
    with transaction.atomic():
        contenido = obtener_para_editar(tipo, contenido_id, bloquear=True)
        if contenido.estado_editorial != E.PUBLICADO:
            raise TransicionInvalida()
        if contenido.version != version:
            raise ConflictoVersion(extra={"entidades_en_conflicto": [_referencia(contenido)]})

        # RULE-007: un Tipo en uso por contenido publicado nunca se retira de forma DIRECTA (solo
        # mediante la cascada de retiro de su último Destino, rama T.DESTINO más abajo). Se evalúa
        # antes de tocar nada (DEC-AUTO-269: dependencia_bloqueante precede a cascada_bloqueada).
        if tipo == T.TIPO:
            usos = _usos_publicados_de_tipo(contenido.pk)
            if usos:
                raise DependenciaBloqueante(extra={"usos": usos, "total_usos": len(usos)})

        itinerarios: list[Contenido] = []
        tipos_cascada: list[TipoAventura] = []
        if tipo == T.DESTINO:
            destino = contenido.destino
            itinerarios = _itinerarios_en_cascada(destino)
            tipos_cascada = _tipos_en_cascada(destino, excluir_destino_id=destino.pk)
            bloqueos = _bloqueos_de_cascada(
                tipos_cascada, itinerarios_ya_en_cascada={i.pk for i in itinerarios}
            )
            if bloqueos:
                raise CascadaBloqueada(
                    extra={
                        "bloqueos_cascada": bloqueos,
                        "usos": _usos_de_bloqueos(bloqueos),
                        "total_usos": sum(b["total_itinerarios"] for b in bloqueos),
                    }
                )
            calculado = {("ITINERARIO", i.pk) for i in itinerarios} | {
                ("TIPO", t.pk) for t in tipos_cascada
            }
            if len(calculado) > LIMITE_CASCADA:
                raise ReglaNegocio(detalle="La cascada de retiro supera el límite permitido.")
            if calculado:
                if cascada_confirmada is not None:
                    enviado = {(e["tipo"], e["id"]) for e in cascada_confirmada}
                    if enviado != calculado:
                        raise ImpactoModificado(
                            extra={
                                "impacto_cascada": {
                                    "itinerarios_en_cascada": [_referencia(i) for i in itinerarios],
                                    "tipos_en_cascada": [
                                        _referencia(t.contenido) for t in tipos_cascada
                                    ],
                                    "bloqueos_cascada": [],
                                }
                            }
                        )
                elif not confirmar_cascada:
                    raise CascadaSinConfirmar(
                        extra={
                            "impacto_cascada": {
                                "itinerarios_en_cascada": [_referencia(i) for i in itinerarios],
                                "tipos_en_cascada": [
                                    _referencia(t.contenido) for t in tipos_cascada
                                ],
                                "bloqueos_cascada": [],
                            }
                        }
                    )

        _confirmar_retiro_entidad(contenido, actor_id, motivo, ip)
        afectadas = [_entidad_transitada(contenido, origen="PRINCIPAL")]
        for itinerario_contenido in itinerarios:
            _confirmar_retiro_entidad(itinerario_contenido, actor_id, motivo, ip)
            afectadas.append(_entidad_transitada(itinerario_contenido, origen="CASCADA"))
        for tipo_c in tipos_cascada:
            _confirmar_retiro_entidad(
                tipo_c.contenido, actor_id, "Cascada: sin destinos publicados (RULE-025)", ip
            )
            afectadas.append(_entidad_transitada(tipo_c.contenido, origen="CASCADA"))
        if tipo == T.TIPO:
            # TKT-014: retiro directo de un Tipo (no vía cascada RULE-025 desde un Destino, que
            # ya cubre sus propias entidades arriba). No transiciona estado en nadie más, pero
            # puede dejar sin visibilidad pública a Destinos (tipo_principal) e Itinerarios que lo
            # usan; ver _reindexar_dependientes_de_tipo.
            _reindexar_dependientes_de_tipo(contenido.pk)
        return contenido, afectadas


# ---------------------------------------------------------------------------
# Reactivar (POST .../reactivar)
# ---------------------------------------------------------------------------
def reactivar(
    tipo: str, contenido_id: int, actor_id: int, version: int, ip: str | None = None
) -> Contenido:
    if tipo == T.PAGINA:
        raise TransicionInvalida(detalle="Las páginas institucionales no se retiran ni reactivan.")
    with transaction.atomic():
        contenido = obtener_para_editar(tipo, contenido_id, bloquear=True)
        if contenido.estado_editorial != E.RETIRADO:
            raise TransicionInvalida()
        if contenido.version != version:
            raise ConflictoVersion()
        contenido.estado_editorial = E.BORRADOR
        contenido.retirado_en = None
        contenido.motivo_retiro = None
        contenido.actualizado_por_id = actor_id
        contenido.version += 1
        contenido.save()
        _auditar(accion=AccionAuditoria.REACTIVAR, actor_id=actor_id, contenido=contenido, ip=ip)
        return contenido


# ---------------------------------------------------------------------------
# Análisis de publicación (sin efectos)
# ---------------------------------------------------------------------------
def analizar_publicacion(
    tipo: str,
    contenido_id: int,
    version: int,
    tipos_ids_propuestos: list[int] | None = None,
    tipo_principal_propuesto: int | None = None,
) -> dict[str, Any]:
    contenido = obtener_para_editar(tipo, contenido_id)
    if contenido.version != version:
        raise ConflictoVersion()
    if tipo != T.DESTINO and (
        tipos_ids_propuestos is not None or tipo_principal_propuesto is not None
    ):
        raise ErrorApi(
            codigo="campo_no_permitido",
            errors={"tipos_ids": ["Solo se admite en un destino publicado."]},
        )

    subtipo = subtipo_de(contenido)
    if contenido.estado_editorial == E.BORRADOR:
        operacion = "PUBLICAR"
        errores = _validar_entidad_para_publicar(tipo, contenido, subtipo)
        entidad = {
            "tipo": tipo,
            "id": contenido.pk,
            "titulo": contenido.titulo,
            "slug": contenido.slug,
            "estado_editorial": contenido.estado_editorial,
            "version": contenido.version,
            "rol": "PRINCIPAL",
            "cumple": not errores,
            "pendientes": errores,
        }
        copublicacion: list[dict[str, Any]] = []
        copublicar_tipos: list[dict[str, Any]] = []
        if tipo == T.DESTINO:
            for t in TipoAventura.objects.filter(
                destinos=subtipo, contenido__estado_editorial=E.BORRADOR
            ).select_related("contenido"):
                errores_t = _validar_entidad_para_publicar(
                    T.TIPO, t.contenido, t, exigir_destino_publicado=False
                )
                copublicacion.append(
                    {
                        "tipo": T.TIPO,
                        "id": t.pk,
                        "titulo": t.contenido.titulo,
                        "slug": t.contenido.slug,
                        "estado_editorial": t.contenido.estado_editorial,
                        "version": t.contenido.version,
                        "rol": "COPUBLICACION",
                        "cumple": not errores_t,
                        "pendientes": errores_t,
                    }
                )
                copublicar_tipos.append({"id": t.pk, "version": t.contenido.version})
        confirmable = entidad["cumple"] and all(c["cumple"] for c in copublicacion)
        return {
            "operacion": operacion,
            "confirmable": confirmable,
            "entidad": entidad,
            "copublicacion": copublicacion,
            "copublicar_tipos": copublicar_tipos,
            "tipos_en_cascada": [],
            "bloqueos_cascada": [],
        }

    if contenido.estado_editorial != E.PUBLICADO:
        raise TransicionInvalida()
    operacion = "ACTUALIZAR_PUBLICACION"
    tipos_en_cascada: list[dict[str, Any]] = []
    bloqueos_cascada: list[dict[str, Any]] = []
    copublicacion = []
    copublicar_tipos = []
    if tipo == T.DESTINO and tipos_ids_propuestos is not None:
        actuales = set(subtipo.tipos_aventura.values_list("contenido_id", flat=True))
        nuevos = set(tipos_ids_propuestos) - actuales
        quitados = actuales - set(tipos_ids_propuestos)
        for tid in nuevos:
            tipo_nuevo = TipoAventura.objects.select_related("contenido").filter(pk=tid).first()
            if tipo_nuevo is None:
                continue
            errores_t = _validar_entidad_para_publicar(
                T.TIPO, tipo_nuevo.contenido, tipo_nuevo, exigir_destino_publicado=False
            )
            copublicacion.append(
                {
                    "tipo": T.TIPO,
                    "id": tipo_nuevo.pk,
                    "titulo": tipo_nuevo.contenido.titulo,
                    "slug": tipo_nuevo.contenido.slug,
                    "estado_editorial": tipo_nuevo.contenido.estado_editorial,
                    "version": tipo_nuevo.contenido.version,
                    "rol": "COPUBLICACION",
                    "cumple": not errores_t,
                    "pendientes": errores_t,
                }
            )
            copublicar_tipos.append({"id": tipo_nuevo.pk, "version": tipo_nuevo.contenido.version})
        for tid in quitados:
            if _destinos_publicados_de_tipo(tid, excluir_destino_id=subtipo.pk) == 0:
                tipo_quitado = TipoAventura.objects.select_related("contenido").get(pk=tid)
                tipos_en_cascada.append(_referencia(tipo_quitado.contenido))
        if tipos_en_cascada:
            bloqueos_cascada = _bloqueos_de_cascada(
                [TipoAventura.objects.get(pk=r["id"]) for r in tipos_en_cascada],
                itinerarios_ya_en_cascada=set(),
            )
    entidad_errores = (
        _validar_entidad_para_publicar(tipo, contenido, subtipo) if tipo != T.DESTINO else []
    )
    entidad = {
        "tipo": tipo,
        "id": contenido.pk,
        "titulo": contenido.titulo,
        "slug": contenido.slug,
        "estado_editorial": contenido.estado_editorial,
        "version": contenido.version,
        "rol": "PRINCIPAL",
        "cumple": not entidad_errores,
        "pendientes": entidad_errores,
    }
    confirmable = (
        entidad["cumple"] and all(c["cumple"] for c in copublicacion) and not bloqueos_cascada
    )
    return {
        "operacion": operacion,
        "confirmable": confirmable,
        "entidad": entidad,
        "copublicacion": copublicacion,
        "copublicar_tipos": copublicar_tipos,
        "tipos_en_cascada": tipos_en_cascada,
        "bloqueos_cascada": bloqueos_cascada,
    }


# ---------------------------------------------------------------------------
# Revisiones
# ---------------------------------------------------------------------------
def listar_revisiones(tipo: str, contenido_id: int) -> QuerySet[RevisionContenido]:
    obtener_para_editar(tipo, contenido_id)
    return (
        RevisionContenido.objects.filter(contenido_id=contenido_id)
        .select_related("creado_por")
        .order_by("-numero_revision")
    )


def obtener_revision(tipo: str, contenido_id: int, numero: int) -> RevisionContenido:
    obtener_para_editar(tipo, contenido_id)
    revision = (
        RevisionContenido.objects.filter(contenido_id=contenido_id, numero_revision=numero)
        .select_related("creado_por")
        .first()
    )
    if revision is None:
        raise NoEncontrado()
    return revision


def restaurar_revision(
    tipo: str, contenido_id: int, numero: int, actor_id: int, ip: str | None = None
) -> dict[str, Any]:
    with transaction.atomic():
        contenido = obtener_para_editar(tipo, contenido_id, bloquear=True)
        revision = RevisionContenido.objects.filter(
            contenido_id=contenido_id, numero_revision=numero
        ).first()
        if revision is None:
            raise NoEncontrado()
        _auditar(
            accion=AccionAuditoria.RESTAURAR_REVISION, actor_id=actor_id, contenido=contenido, ip=ip
        )
        datos = dict(revision.instantanea)
        datos.pop("estado_editorial", None)
        return {"numero_revision": numero, "version_actual": contenido.version, "datos": datos}


# ---------------------------------------------------------------------------
# Vista previa (sin persistir, DEC-AUTO-114)
# ---------------------------------------------------------------------------
def _seo_en_uso_valor(seo_descripcion: str | None, excluir_id: int | None) -> bool:
    if not seo_descripcion:
        return False
    qs = Contenido.objects.filter(
        estado_editorial=E.PUBLICADO, seo_descripcion__iexact=seo_descripcion.strip()
    )
    if excluir_id is not None:
        qs = qs.exclude(pk=excluir_id)
    return qs.exists()


def _relacionados_publicados_de_ids(relaciones: list[dict[str, Any]]) -> int:
    """Aproximación de RULE-006 para la vista previa (sin persistir): solo cuenta los curados que
    ya están publicados. No simula el complemento automático por afinidad (requiere un `pk`
    persistido); el resultado real se confirma al guardar y publicar (DEC-AUTO-114, orientativo)."""
    if not relaciones:
        return 0
    ids = [r["id"] for r in relaciones]
    return Contenido.objects.filter(pk__in=ids, estado_editorial=E.PUBLICADO).count()


def vista_previa(tipo: str, datos: dict[str, Any]) -> dict[str, Any]:
    """Requisitos de publicación sobre los datos del formulario, sin persistir nada (AC-111).

    Limitación documentada: `datos` en la respuesta es el propio cuerpo de entrada normalizado
    (no la forma exacta de `{Tipo}Detalle` público), suficiente para pintar el formulario en modo
    lectura; una réplica pixel-perfect del detalle público no es necesaria para AC-111.
    """
    excluir_id = datos.get("id")
    if tipo == T.PAGINA:
        errores = reglas.validar_pagina_institucional(
            reglas.DatosPaginaInstitucional(
                cuerpo=datos.get("cuerpo"),
                version_documento=datos.get("version_documento"),
                vigente_desde=datos.get("vigente_desde"),
                fecha_ultima_revision=datos.get("fecha_ultima_revision"),
                seo_descripcion=datos.get("seo_descripcion"),
            )
        )
        return {
            "requisitos_publicacion": {"cumple": not errores, "pendientes": errores},
            "datos": datos,
        }

    relacionados = _relacionados_publicados_de_ids(datos.get("relaciones") or [])
    seo_en_uso = _seo_en_uso_valor(datos.get("seo_descripcion"), excluir_id)

    if tipo == T.DESTINO:
        galeria_ids = datos.get("galeria_ids") or []
        errores = reglas.validar_destino(
            reglas.DatosDestino(
                resumen=datos.get("resumen"),
                descripcion_experta=datos.get("descripcion_experta"),
                tipos_ids=tuple(datos.get("tipos_ids") or []),
                tipo_principal_id=datos.get("tipo_principal_id"),
                dificultad=datos.get("dificultad"),
                meses_mejor_epoca=tuple(datos.get("meses_mejor_epoca") or []),
                duracion_min_dias=datos.get("duracion_min_dias"),
                duracion_max_dias=datos.get("duracion_max_dias"),
                nivel_presupuesto=datos.get("nivel_presupuesto"),
                clima=datos.get("clima"),
                como_llegar=datos.get("como_llegar"),
                seguridad_riesgos=datos.get("seguridad_riesgos"),
                sostenibilidad=datos.get("sostenibilidad"),
                latitud=datos.get("latitud"),
                longitud=datos.get("longitud"),
                portada_id=datos.get("portada_id"),
                galeria_ids=tuple(galeria_ids),
                fecha_ultima_revision=datos.get("fecha_ultima_revision"),
                seo_descripcion=datos.get("seo_descripcion"),
                medios_disponibles_en_galeria=Medio.objects.filter(
                    pk__in=galeria_ids, estado=EstadoMedio.DISPONIBLE
                ).count(),
                relacionados_publicados=relacionados,
                seo_descripcion_en_uso=seo_en_uso,
            )
        )
    elif tipo == T.ITINERARIO:
        tipos_ids = datos.get("tipos_ids") or []
        estados = dict(
            TipoAventura.objects.filter(pk__in=tipos_ids).values_list(
                "contenido_id", "contenido__estado_editorial"
            )
        )
        destino_estado = None
        if datos.get("destino_id"):
            destino_estado = (
                Contenido.objects.filter(pk=datos["destino_id"], tipo=T.DESTINO)
                .values_list("estado_editorial", flat=True)
                .first()
            )
        dias = datos.get("dias") or []
        errores = reglas.validar_itinerario(
            reglas.DatosItinerario(
                destino_id=datos.get("destino_id"),
                destino_estado=destino_estado,
                resumen=datos.get("resumen"),
                duracion_dias=datos.get("duracion_dias"),
                dificultad=datos.get("dificultad"),
                tipos_ids=tuple(tipos_ids),
                tipos_estados=tuple(estados.get(tid, "") for tid in tipos_ids),
                riesgos_seguridad=datos.get("riesgos_seguridad"),
                portada_id=datos.get("portada_id"),
                fecha_ultima_revision=datos.get("fecha_ultima_revision"),
                seo_descripcion=datos.get("seo_descripcion"),
                numeros_dia=tuple(d["numero_dia"] for d in dias),
                dias_completos=all(d.get("titulo") and d.get("actividades") for d in dias),
                relacionados_publicados=relacionados,
                seo_descripcion_en_uso=seo_en_uso,
            )
        )
    elif tipo == T.GUIA:
        errores = reglas.validar_guia(
            reglas.DatosGuia(
                categoria_id=datos.get("categoria_id"),
                resumen=datos.get("resumen"),
                cuerpo=datos.get("cuerpo"),
                portada_id=datos.get("portada_id"),
                fecha_ultima_revision=datos.get("fecha_ultima_revision"),
                seo_descripcion=datos.get("seo_descripcion"),
                remite_a_metodologia=bool(datos.get("remite_a_metodologia")),
                numero_fuentes=len(datos.get("fuentes") or []),
                relacionados_publicados=relacionados,
                seo_descripcion_en_uso=seo_en_uso,
            )
        )
    elif tipo == T.TIPO:
        checklist = datos.get("checklist") or []
        errores = reglas.validar_tipo_aventura(
            reglas.DatosTipoAventura(
                resumen=datos.get("resumen"),
                descripcion=datos.get("descripcion"),
                portada_id=datos.get("portada_id"),
                fecha_ultima_revision=datos.get("fecha_ultima_revision"),
                seo_descripcion=datos.get("seo_descripcion"),
                numero_checklist=len(checklist),
                destinos_publicados=_destinos_publicados_de_tipo(excluir_id) if excluir_id else 0,
                relacionados_publicados=relacionados,
                seo_descripcion_en_uso=seo_en_uso,
            ),
            exigir_destino_publicado=True,
        )
    elif tipo == T.COLECCION:
        elementos = datos.get("elementos") or []
        ids_publicados = set(
            Contenido.objects.filter(
                pk__in=[e["contenido_id"] for e in elementos], estado_editorial=E.PUBLICADO
            ).values_list("pk", flat=True)
        )
        errores = reglas.validar_coleccion(
            reglas.DatosColeccion(
                portada_id=datos.get("portada_id"),
                fecha_ultima_revision=datos.get("fecha_ultima_revision"),
                seo_descripcion=datos.get("seo_descripcion"),
                elementos_publicados=sum(
                    1 for e in elementos if e["contenido_id"] in ids_publicados
                ),
                seo_descripcion_en_uso=seo_en_uso,
            )
        )
    else:
        errores = []
    return {
        "requisitos_publicacion": {"cumple": not errores, "pendientes": errores},
        "datos": datos,
    }
