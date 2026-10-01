"""Alta y edición de taxonomías del panel (FEAT-044, RULE-007, RULE-012, RULE-014).

"Retirar" un elemento es un PUT con `activo=false`; si está en uso por contenido publicado, la
operación se rechaza con 409 `dependencia_bloqueante` y la lista de usos (RULE-007). Toda
escritura audita `TAXONOMIA`. Las escalas (`NivelEscala`) son una colección fija de 9 filas
sembradas (RULE-012): no se crean ni se eliminan, solo se edita `etiqueta`/`descripcion`.
"""

from __future__ import annotations

from typing import Any, TypeVar

from django.db import IntegrityError, transaction

from apps.auditoria import services as auditoria
from apps.auditoria.models import AccionAuditoria
from apps.catalogos.models import CategoriaGuia, Licencia, NivelEscala, Pais, Region
from apps.contenido.models import EstadoEditorial
from apps.core.exceptions import ErrorApi, NoEncontrado


class DependenciaBloqueante(ErrorApi):
    codigo = "dependencia_bloqueante"


class Duplicado(ErrorApi):
    codigo = "duplicado"


MENSAJE_INEXISTENTE = "No existe."


def _auditar(actor_id: int, tipo_entidad: str, entidad_id: int) -> None:
    auditoria.registrar_evento(
        accion=AccionAuditoria.TAXONOMIA,
        actor_id=actor_id,
        tipo_entidad=tipo_entidad,
        entidad_id=entidad_id,
    )


# TypeVar de restricción (no de cota): PEP 695 no tiene equivalente para "uno de estos tipos
# exactos" (solo cotas/unions, que no bastan aquí: ver el fallo de tipos al usar `[M: Union]`).
_M = TypeVar("_M", Region, Pais, CategoriaGuia, Licencia, NivelEscala)


def _obtener_o_404(modelo: type[_M], pk: int) -> _M:  # noqa: UP047
    obj = modelo.objects.filter(pk=pk).first()
    if obj is None:
        raise NoEncontrado()
    return obj


def _guardar(obj: _M) -> _M:  # noqa: UP047
    try:
        obj.save()
    except IntegrityError as exc:
        raise Duplicado() from exc
    return obj


# ---------------------------------------------------------------------------
# Región
# ---------------------------------------------------------------------------
def _usos_pais(pais_id: int) -> list[dict[str, Any]]:
    from apps.contenido.models import Destino

    return [
        {
            "tipo_entidad": "DESTINO",
            "id": d.contenido_id,
            "titulo": d.contenido.titulo,
            "estado_editorial": d.contenido.estado_editorial,
        }
        for d in Destino.objects.filter(
            pais_id=pais_id, contenido__estado_editorial=EstadoEditorial.PUBLICADO
        ).select_related("contenido")
    ]


def crear_region(actor_id: int, datos: dict[str, Any]) -> Region:
    with transaction.atomic():
        region = _guardar(Region(**datos))
        _auditar(actor_id, "REGION", region.pk)
        return region


def actualizar_region(region_id: int, actor_id: int, datos: dict[str, Any]) -> Region:
    with transaction.atomic():
        region = _obtener_o_404(Region, region_id)
        if datos.get("activo") is False and region.activo:
            paises = Pais.objects.filter(region=region)
            usos = [u for pais in paises for u in _usos_pais(pais.pk)]
            if usos:
                raise DependenciaBloqueante(extra={"usos": usos, "total_usos": len(usos)})
        for campo, valor in datos.items():
            setattr(region, campo, valor)
        _guardar(region)
        _auditar(actor_id, "REGION", region.pk)
        return region


# ---------------------------------------------------------------------------
# País
# ---------------------------------------------------------------------------
def _validar_region(datos: dict[str, Any]) -> None:
    """La región referenciada debe existir ANTES de escribir (TKT-032): la FK `pais.region_id`
    de Django es DEFERRABLE INITIALLY DEFERRED, así que una región inexistente no fallaba en el
    INSERT/UPDATE sino en el COMMIT, fuera de `_guardar`, y se respondía 500 en vez de 400."""
    if not Region.objects.filter(pk=datos["region_id"]).exists():
        raise ErrorApi(codigo="validacion", errors={"region_id": [MENSAJE_INEXISTENTE]})


def crear_pais(actor_id: int, datos: dict[str, Any]) -> Pais:
    with transaction.atomic():
        _validar_region(datos)
        pais = _guardar(Pais(**datos))
        _auditar(actor_id, "PAIS", pais.pk)
        return pais


def actualizar_pais(pais_id: int, actor_id: int, datos: dict[str, Any]) -> Pais:
    with transaction.atomic():
        pais = _obtener_o_404(Pais, pais_id)
        _validar_region(datos)
        if datos.get("activo") is False and pais.activo:
            usos = _usos_pais(pais.pk)
            if usos:
                raise DependenciaBloqueante(extra={"usos": usos, "total_usos": len(usos)})
        for campo, valor in datos.items():
            setattr(pais, campo, valor)
        _guardar(pais)
        _auditar(actor_id, "PAIS", pais.pk)
        return pais


# ---------------------------------------------------------------------------
# Categoría de guía
# ---------------------------------------------------------------------------
def _usos_categoria(categoria_id: int) -> list[dict[str, Any]]:
    from apps.contenido.models import Guia

    return [
        {
            "tipo_entidad": "GUIA",
            "id": g.contenido_id,
            "titulo": g.contenido.titulo,
            "estado_editorial": g.contenido.estado_editorial,
        }
        for g in Guia.objects.filter(
            categoria_id=categoria_id, contenido__estado_editorial=EstadoEditorial.PUBLICADO
        ).select_related("contenido")
    ]


def crear_categoria(actor_id: int, datos: dict[str, Any]) -> CategoriaGuia:
    with transaction.atomic():
        categoria = _guardar(CategoriaGuia(**datos))
        _auditar(actor_id, "CATEGORIA_GUIA", categoria.pk)
        return categoria


def actualizar_categoria(categoria_id: int, actor_id: int, datos: dict[str, Any]) -> CategoriaGuia:
    with transaction.atomic():
        categoria = _obtener_o_404(CategoriaGuia, categoria_id)
        if datos.get("activo") is False and categoria.activo:
            usos = _usos_categoria(categoria.pk)
            if usos:
                raise DependenciaBloqueante(extra={"usos": usos, "total_usos": len(usos)})
        for campo, valor in datos.items():
            setattr(categoria, campo, valor)
        _guardar(categoria)
        _auditar(actor_id, "CATEGORIA_GUIA", categoria.pk)
        return categoria


# ---------------------------------------------------------------------------
# Licencia (solo Administrador)
# ---------------------------------------------------------------------------
def _usos_licencia(licencia_id: int) -> list[dict[str, Any]]:
    from apps.medios import services as medios_services
    from apps.medios.models import Medio

    usos: list[dict[str, Any]] = []
    for medio in Medio.objects.filter(licencia_id=licencia_id):
        if medios_services._en_uso_publicado(medio.pk):
            usos.append(
                {
                    "tipo_entidad": "MEDIO",
                    "id": medio.pk,
                    "titulo": f"Medio #{medio.pk}",
                    "estado_editorial": None,
                }
            )
    return usos


def crear_licencia(actor_id: int, datos: dict[str, Any]) -> Licencia:
    with transaction.atomic():
        licencia = _guardar(Licencia(**datos))
        _auditar(actor_id, "LICENCIA", licencia.pk)
        return licencia


def actualizar_licencia(licencia_id: int, actor_id: int, datos: dict[str, Any]) -> Licencia:
    with transaction.atomic():
        licencia = _obtener_o_404(Licencia, licencia_id)
        if datos.get("activo") is False and licencia.activo:
            usos = _usos_licencia(licencia.pk)
            if usos:
                raise DependenciaBloqueante(extra={"usos": usos, "total_usos": len(usos)})
        for campo, valor in datos.items():
            setattr(licencia, campo, valor)
        _guardar(licencia)
        _auditar(actor_id, "LICENCIA", licencia.pk)
        return licencia


# ---------------------------------------------------------------------------
# Escalas (solo Administrador; colección fija de 9)
# ---------------------------------------------------------------------------
def actualizar_nivel_escala(nivel_id: int, actor_id: int, datos: dict[str, Any]) -> NivelEscala:
    with transaction.atomic():
        nivel = _obtener_o_404(NivelEscala, nivel_id)
        nivel.etiqueta = datos["etiqueta"]
        nivel.descripcion = datos["descripcion"]
        _guardar(nivel)
        _auditar(actor_id, "NIVEL_ESCALA", nivel.pk)
        return nivel
