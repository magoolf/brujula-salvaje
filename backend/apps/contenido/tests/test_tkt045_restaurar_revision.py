"""TKT-045 (1): restaurar una revisión no pierde datos (F-01 HIGH de la QA de TKT-023).

Antes, `services._instantanea` recorría solo `subtipo._meta.fields`: la revisión no guardaba M2M
(tipos, destinos), hijos (días, checklist, elementos), comunes relacionales (relaciones, términos,
fuentes) ni la galería, y guardaba las FK sin `_id` (`pais`, `destino`...). `restaurar_revision`
devolvía esa instantánea, que no es un cuerpo `{Tipo}Actualizacion` válido y, cargada en el
formulario y guardada, vaciaba esas colecciones.

Pruebas por tipo (los 7) de ida y vuelta por HTTP real: estado A → revisión → estado B →
restaurar → `datos` conforme a `{Tipo}Actualizacion` del contrato e igual a A → PUT → el contenido
vuelve a A. Además, las revisiones antiguas (formato anterior, incompletas) se restauran sin
inventar datos y sin borrar por omisión (DEC-DEV-045-01).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pytest
from django.test import Client

from apps.auditoria.models import (
    AccionAuditoria,
    EventoAuditoria,
    MotivoRevision,
    RevisionContenido,
)
from apps.contenido import services
from apps.contenido.api import panel_serializers as ps
from apps.contenido.models import Contenido, EstadoEditorial, TipoContenido
from apps.contenido.tests import publicos

T = TipoContenido
E = EstadoEditorial
BASE = "/api/v1/panel/contenidos"
AYER = (date.today() - timedelta(days=1)).isoformat()
HACE_UN_MES = (date.today() - timedelta(days=30)).isoformat()

pytestmark = pytest.mark.django_db

ESQUEMA_ACTUALIZACION = {
    T.DESTINO: "DestinoActualizacion",
    T.ITINERARIO: "ItinerarioActualizacion",
    T.GUIA: "GuiaActualizacion",
    T.TIPO: "TipoAventuraActualizacion",
    T.COLECCION: "ColeccionActualizacion",
    T.TERMINO: "TerminoGlosarioActualizacion",
    T.PAGINA: "PaginaInstitucionalActualizacion",
}
SERIALIZER_ACTUALIZACION = {
    T.DESTINO: ps.DestinoActualizacionSerializer,
    T.ITINERARIO: ps.ItinerarioActualizacionSerializer,
    T.GUIA: ps.GuiaActualizacionSerializer,
    T.TIPO: ps.TipoAventuraActualizacionSerializer,
    T.COLECCION: ps.ColeccionActualizacionSerializer,
    T.TERMINO: ps.TerminoGlosarioActualizacionSerializer,
    T.PAGINA: ps.PaginaInstitucionalActualizacionSerializer,
}
CONTROL_OPERACION = {"version", "copublicar_tipos", "confirmar_cascada", "cascada_confirmada"}


def _json(cliente: Client, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
    return getattr(cliente, metodo)(ruta, cuerpo, content_type="application/json")


def _ruta(tipo: str, contenido_id: int) -> str:
    return f"{BASE}/{services.TIPO_A_RUTA[tipo]}/{contenido_id}"


def _editables(cuerpo: dict[str, Any], tipo: str) -> dict[str, Any]:
    return {c: cuerpo[c] for c in services.CAMPOS_EDITABLES[tipo]}


@pytest.fixture
def refs() -> dict[str, Any]:
    """Referencias reales (catálogos, medios, contenidos publicados) para rellenar cada tipo."""
    t1 = publicos.tipo("Senderismo TKT045")
    t2 = publicos.tipo("Escalada TKT045")
    d1 = publicos.destino("Destino ref TKT045", tipos=[t1])
    i1 = publicos.itinerario("Itinerario ref TKT045", d1, tipos=[t1])
    return {
        "pais": publicos.pais().pk,
        "categoria": publicos.categoria().pk,
        "medios": [publicos.medio().pk for _ in range(3)],
        "t1": t1.pk,
        "t2": t2.pk,
        "d1": d1.pk,
        "i1": i1.pk,
        "te1": publicos.termino("Vivac TKT045", []).pk,
        "te2": publicos.termino("Cordada TKT045", []).pk,
    }


def _comunes_a(refs: dict[str, Any], titulo: str) -> dict[str, Any]:
    return {
        "titulo": titulo,
        "fecha_ultima_revision": HACE_UN_MES,
        "seo_titulo": f"SEO {titulo}",
        "seo_descripcion": f"Descripción SEO de {titulo}",
        "relaciones": [{"tipo": "DESTINO", "id": refs["d1"]}, {"tipo": "TIPO", "id": refs["t2"]}],
        "terminos_ids": [refs["te2"], refs["te1"]],
        "fuentes": [
            {
                "titulo": "Fuente uno",
                "entidad_editora": "Instituto",
                "url": "https://example.org/fuente",
                "fecha_consulta": "2026-09-01",
            },
            {"titulo": "Fuente dos", "entidad_editora": None, "url": None, "fecha_consulta": None},
        ],
    }


def _estado_a(tipo: str, refs: dict[str, Any]) -> dict[str, Any]:
    m1, m2, m3 = refs["medios"]
    if tipo == T.DESTINO:
        return _comunes_a(refs, "Destino A") | {
            "pais_id": refs["pais"],
            "resumen": "Resumen A",
            "descripcion_experta": '<p>Experta <a href="https://example.org">enlace</a></p>',
            "tipos_ids": [refs["t1"], refs["t2"]],
            "tipo_principal_id": refs["t2"],
            "dificultad": 4,
            "meses_mejor_epoca": [3, 1],
            "duracion_min_dias": 2,
            "duracion_max_dias": 5,
            "nivel_presupuesto": 3,
            "clima": "Frío",
            "altitud_max_m": 3000,
            "como_llegar": "<p>Bus</p>",
            "seguridad_riesgos": "<p>Riesgos</p>",
            "sostenibilidad": "<p>Sin rastro</p>",
            "latitud": 4.123456,
            "longitud": -74.5,
            "portada_id": m1,
            "galeria_ids": [m3, m2],
        }
    if tipo == T.ITINERARIO:
        return _comunes_a(refs, "Itinerario A") | {
            "destino_id": refs["d1"],
            "resumen": "Resumen A",
            "duracion_dias": 2,
            "dificultad": 3,
            "tipos_ids": [refs["t1"]],
            "distancia_total_km": 12.5,
            "desnivel_acumulado_m": 800,
            "riesgos_seguridad": "<p>Agua</p>",
            "portada_id": m1,
            "galeria_ids": [m2],
            "dias": [
                {
                    "numero_dia": 1,
                    "titulo": "Día uno",
                    "actividades": "<p>Subir</p>",
                    "distancia_km": 5.5,
                    "desnivel_positivo_m": 100,
                    "desnivel_negativo_m": 50,
                    "alojamiento_orientativo": "Refugio",
                    "consejos": "<p>Madrugar</p>",
                },
                {"numero_dia": 2, "titulo": "Día dos", "actividades": "<p>Bajar</p>"},
            ],
        }
    if tipo == T.GUIA:
        return _comunes_a(refs, "Guía A") | {
            "categoria_id": refs["categoria"],
            "resumen": "Resumen A",
            "cuerpo": "<p>Cuerpo A</p>",
            "destinos_ids": [refs["d1"]],
            "tipos_ids": [refs["t1"], refs["t2"]],
            "remite_a_metodologia": True,
            "portada_id": m1,
        }
    if tipo == T.TIPO:
        return _comunes_a(refs, "Tipo A") | {
            "resumen": "Resumen A",
            "descripcion": "<p>Descripción A</p>",
            "nivel_exigencia": 2,
            "portada_id": m1,
            "orden": 5,
            "checklist": [
                {"texto": "Casco", "grupo": "Equipo", "esencial": True, "orden": 0},
                {"texto": "Agua", "grupo": None, "esencial": False, "orden": 1},
            ],
        }
    if tipo == T.COLECCION:
        # Las colecciones no enlazan términos (`ck_contenido_termino_tipo_contenido`).
        return _comunes_a(refs, "Colección A") | {
            "terminos_ids": [],
            "resumen": "Resumen A",
            "descripcion": "<p>Descripción A</p>",
            "portada_id": m1,
            "elementos": [
                {
                    "tipo_contenido": "DESTINO",
                    "contenido_id": refs["d1"],
                    "orden": 0,
                    "nota_editorial": "Imprescindible",
                },
                {
                    "tipo_contenido": "ITINERARIO",
                    "contenido_id": refs["i1"],
                    "orden": 1,
                    "nota_editorial": None,
                },
            ],
        }
    if tipo == T.TERMINO:
        return {
            "titulo": "Término A",
            "slug": "termino-a-tkt045",
            "definicion": "Definición A",
            "fecha_ultima_revision": HACE_UN_MES,
        }
    return {
        "titulo": "Aviso legal A",
        "cuerpo": "<p>Texto legal A</p>",
        "version_documento": "2.0",
        "vigente_desde": "2026-09-15",
        "fecha_ultima_revision": HACE_UN_MES,
        "seo_titulo": "Aviso A",
        "seo_descripcion": "Aviso legal versión A",
    }


def _estado_b(tipo: str, version: int) -> dict[str, Any]:
    """Cambio posterior que vacía colecciones y anula referencias (lo que se debe recuperar)."""
    if tipo == T.TERMINO:
        return {"titulo": "Término B", "definicion": None, "version": version}
    if tipo == T.PAGINA:
        return {
            "titulo": "Aviso legal B",
            "cuerpo": "<p>Texto legal B</p>",
            "version_documento": "3.0",
            "vigente_desde": "2026-10-01",
            "fecha_ultima_revision": AYER,
            "version": version,
        }
    cambio: dict[str, Any] = {"titulo": f"{tipo} B", "resumen": "Resumen B", "version": version}
    if tipo == T.DESTINO:
        cambio |= {"pais_id": None, "tipo_principal_id": None}
    if tipo == T.ITINERARIO:
        cambio |= {"destino_id": None}
    if tipo == T.GUIA:
        cambio |= {"categoria_id": None, "remite_a_metodologia": False}
    return cambio


def _preparar(
    tipo: str, refs: dict[str, Any], editora: Client, admin: Client
) -> tuple[Client, int, int, dict[str, Any]]:
    """Deja el contenido en el estado A con una revisión que lo registra. Devuelve (cliente, id,
    número de la revisión, campos editables de A tal como los devuelve el panel)."""
    if tipo == T.PAGINA:
        # Flujo real: actualizar una página publicada crea la revisión (motivo ACTUALIZACION).
        pagina = publicos.pagina("AVISO_LEGAL", "Aviso legal")
        ruta = _ruta(T.PAGINA, pagina.contenido_id)
        version = admin.get(ruta).json()["version"]
        guardado = _json(admin, "put", ruta, _estado_a(tipo, refs) | {"version": version})
        assert guardado.status_code == 200, guardado.content
        numero = RevisionContenido.objects.filter(contenido_id=pagina.contenido_id).latest(
            "numero_revision"
        )
        return admin, pagina.contenido_id, numero.numero_revision, _editables(guardado.json(), tipo)
    creado = _json(editora, "post", f"{BASE}/{services.TIPO_A_RUTA[tipo]}", _estado_a(tipo, refs))
    assert creado.status_code == 201, creado.content
    contenido = Contenido.objects.get(pk=creado.json()["id"])
    # Mismo punto de creación que usan publicar/actualizar publicación/retirar.
    revision = services._crear_revision(contenido, MotivoRevision.ACTUALIZACION, None)
    return editora, contenido.pk, revision.numero_revision, _editables(creado.json(), tipo)


@pytest.mark.parametrize("tipo", list(ESQUEMA_ACTUALIZACION))
def test_AC_TKT045_01_restaurar_ida_y_vuelta_por_tipo(
    tipo: str,
    refs: dict[str, Any],
    cliente_editora: Client,
    cliente_admin: Client,
    conforme: Callable[[str, Any], None],
) -> None:
    cliente, contenido_id, numero, estado_a = _preparar(tipo, refs, cliente_editora, cliente_admin)
    ruta = _ruta(tipo, contenido_id)

    # La instantánea registra TODO (colecciones, hijos, M2M y FK con `_id`).
    instantanea = RevisionContenido.objects.get(
        contenido_id=contenido_id, numero_revision=numero
    ).instantanea
    assert {k: v for k, v in instantanea.items() if k != "estado_editorial"} == estado_a

    # Estado B: colecciones vaciadas, referencias anuladas.
    version = cliente.get(ruta).json()["version"]
    cambiado = _json(cliente, "put", ruta, _estado_b(tipo, version))
    assert cambiado.status_code == 200, cambiado.content
    assert _editables(cambiado.json(), tipo) != estado_a

    restaurada = _json(cliente, "post", f"{ruta}/revisiones/{numero}/restaurar")
    assert restaurada.status_code == 200, restaurada.content
    cuerpo = restaurada.json()
    conforme("RestauracionRevision", cuerpo)
    assert cuerpo["version_actual"] == cambiado.json()["version"]
    datos = cuerpo["datos"]
    # Cuerpo `{Tipo}Actualizacion` del contrato (sin `version`): mismas claves y válido.
    assert set(datos) == set(services.CAMPOS_EDITABLES[tipo])
    conforme(ESQUEMA_ACTUALIZACION[tipo], datos | {"version": cuerpo["version_actual"]})
    assert datos == estado_a

    # Guardar lo restaurado devuelve el contenido exactamente al estado A.
    guardado = _json(cliente, "put", ruta, datos | {"version": cuerpo["version_actual"]})
    assert guardado.status_code == 200, guardado.content
    assert _editables(guardado.json(), tipo) == estado_a
    assert _editables(cliente.get(ruta).json(), tipo) == estado_a


@pytest.mark.parametrize("tipo", list(ESQUEMA_ACTUALIZACION))
def test_AC_TKT045_02_campos_editables_coinciden_con_el_cuerpo_de_actualizacion(
    tipo: str,
) -> None:
    """La lista de campos de la instantánea/restauración es exactamente la del serializer de
    actualización (que el gate de contrato compara con `{Tipo}Actualizacion`), sin `version` ni
    los campos de control de la operación."""
    campos_serializer = set(SERIALIZER_ACTUALIZACION[tipo]().fields) - CONTROL_OPERACION
    assert set(services.CAMPOS_EDITABLES[tipo]) == campos_serializer


def test_AC_TKT045_03_revision_antigua_incompleta_no_inventa_ni_borra(
    refs: dict[str, Any], cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    """Instantánea con el formato anterior a TKT-045 (FK sin `_id`, sin colecciones): se traducen
    las claves heredadas, se descartan las no editables y los campos que la revisión no registró
    conservan su valor actual (el PUT es sustitución completa: omitirlos los vaciaría)."""
    creado = _json(cliente_editora, "post", f"{BASE}/destinos", _estado_a(T.DESTINO, refs))
    assert creado.status_code == 201, creado.content
    actual = _editables(creado.json(), T.DESTINO)
    contenido = Contenido.objects.get(pk=creado.json()["id"])
    otro_pais = publicos.pais().pk
    RevisionContenido.objects.create(
        contenido=contenido,
        tipo_contenido=T.DESTINO,
        numero_revision=1,
        motivo=MotivoRevision.PUBLICACION,
        instantanea={
            "titulo": "Destino antiguo",
            "slug": contenido.slug,
            "estado_editorial": "PUBLICADO",
            "fecha_ultima_revision": "2026-08-01",
            "seo_titulo": None,
            "seo_descripcion": "Descripción antigua",
            "portada_id": refs["medios"][1],
            "pais": otro_pais,
            "resumen": "Resumen antiguo",
            "descripcion_experta": "<p>Antigua</p>",
            "tipo_principal": refs["t1"],
            "dificultad": 2,
            "meses_mejor_epoca": [6, 7],
            "duracion_min_dias": 1,
            "duracion_max_dias": 3,
            "nivel_presupuesto": 1,
            "clima": "Seco",
            "altitud_max_m": 100,
            "como_llegar": None,
            "seguridad_riesgos": None,
            "sostenibilidad": None,
            "latitud": 1.5,
            "longitud": 2.5,
        },
    )
    ruta = _ruta(T.DESTINO, contenido.pk)
    restaurada = _json(cliente_editora, "post", f"{ruta}/revisiones/1/restaurar")
    assert restaurada.status_code == 200, restaurada.content
    datos = restaurada.json()["datos"]
    version = restaurada.json()["version_actual"]

    conforme("DestinoActualizacion", datos | {"version": version})
    assert "pais" not in datos
    assert "tipo_principal" not in datos
    assert "estado_editorial" not in datos
    # Lo registrado se restaura (también las FK heredadas, con su nombre de la API)...
    assert datos["titulo"] == "Destino antiguo"
    assert datos["pais_id"] == otro_pais
    assert datos["tipo_principal_id"] == refs["t1"]
    assert datos["meses_mejor_epoca"] == [6, 7]
    assert datos["latitud"] == 1.5
    # ...y lo no registrado conserva el valor actual (nada se vacía por omisión).
    for campo in ("relaciones", "terminos_ids", "fuentes", "tipos_ids", "galeria_ids"):
        assert datos[campo] == actual[campo], campo

    guardado = _json(cliente_editora, "put", ruta, datos | {"version": version})
    assert guardado.status_code == 200, guardado.content
    final = _editables(guardado.json(), T.DESTINO)
    assert final["galeria_ids"] == actual["galeria_ids"]
    assert final["relaciones"] == actual["relaciones"]
    assert final["pais_id"] == otro_pais


@pytest.mark.parametrize(
    ("tipo", "heredada", "valor_clave", "descartadas"),
    [
        (T.ITINERARIO, "destino", "d1", {"palabras"}),
        (T.GUIA, "categoria", "categoria", {"palabras"}),
    ],
)
def test_AC_TKT045_03b_claves_heredadas_de_itinerario_y_guia(
    tipo: str,
    heredada: str,
    valor_clave: str,
    descartadas: set[str],
    refs: dict[str, Any],
    cliente_editora: Client,
    conforme: Callable[[str, Any], None],
) -> None:
    creado = _json(
        cliente_editora, "post", f"{BASE}/{services.TIPO_A_RUTA[tipo]}", _estado_a(tipo, refs)
    )
    assert creado.status_code == 201, creado.content
    contenido = Contenido.objects.get(pk=creado.json()["id"])
    antigua = {"titulo": "Antiguo", "estado_editorial": "BORRADOR", heredada: refs[valor_clave]}
    antigua |= dict.fromkeys(descartadas, 123)
    RevisionContenido.objects.create(
        contenido=contenido,
        tipo_contenido=tipo,
        numero_revision=1,
        motivo=MotivoRevision.PUBLICACION,
        instantanea=antigua,
    )
    restaurada = _json(
        cliente_editora, "post", f"{_ruta(tipo, contenido.pk)}/revisiones/1/restaurar"
    )
    assert restaurada.status_code == 200, restaurada.content
    datos = restaurada.json()["datos"]
    conforme(ESQUEMA_ACTUALIZACION[tipo], datos | {"version": 1})
    assert datos[f"{heredada}_id"] == refs[valor_clave]
    assert not (descartadas | {heredada}) & set(datos)
    assert datos["titulo"] == "Antiguo"


def test_AC_TKT045_03c_pagina_antigua_descarta_claves_no_editables(
    cliente_admin: Client, conforme: Callable[[str, Any], None]
) -> None:
    pagina = publicos.pagina("POLITICA_DATOS", "Política de datos")
    RevisionContenido.objects.create(
        contenido=pagina.contenido,
        tipo_contenido=T.PAGINA,
        numero_revision=1,
        motivo=MotivoRevision.ACTUALIZACION,
        instantanea={
            "titulo": "Política antigua",
            "slug": pagina.contenido.slug,
            "estado_editorial": "PUBLICADO",
            "fecha_ultima_revision": "2026-08-01",
            "seo_titulo": None,
            "seo_descripcion": None,
            "portada_id": None,
            "clave": "POLITICA_DATOS",
            "cuerpo": "<p>Antigua</p>",
            "version_documento": "0.9",
            "vigente_desde": "2026-01-01",
        },
    )
    ruta = _ruta(T.PAGINA, pagina.contenido_id)
    restaurada = _json(cliente_admin, "post", f"{ruta}/revisiones/1/restaurar")
    assert restaurada.status_code == 200, restaurada.content
    datos = restaurada.json()["datos"]
    conforme("PaginaInstitucionalActualizacion", datos | {"version": 1})
    assert not {"slug", "portada_id", "clave", "estado_editorial"} & set(datos)
    assert datos["version_documento"] == "0.9"


def test_AC_TKT045_04_restaurar_no_persiste_y_audita(
    refs: dict[str, Any], cliente_editora: Client, cliente_admin: Client
) -> None:
    """Restaurar solo carga los datos (AC-121): no cambia el contenido ni su versión y deja el
    evento RESTAURAR_REVISION."""
    cliente, contenido_id, numero, _ = _preparar(T.TIPO, refs, cliente_editora, cliente_admin)
    ruta = _ruta(T.TIPO, contenido_id)
    version = cliente.get(ruta).json()["version"]
    _json(cliente, "put", ruta, _estado_b(T.TIPO, version))
    antes = cliente.get(ruta).json()

    restaurada = _json(cliente, "post", f"{ruta}/revisiones/{numero}/restaurar")
    assert restaurada.status_code == 200, restaurada.content

    despues = cliente.get(ruta).json()
    assert _editables(despues, T.TIPO) == _editables(antes, T.TIPO)
    assert despues["version"] == antes["version"]
    assert EventoAuditoria.objects.filter(
        accion=AccionAuditoria.RESTAURAR_REVISION, entidad_id=contenido_id
    ).exists()


def test_AC_TKT045_05_instantanea_de_publicacion_real_registra_la_forma_editable(
    editora: Any,
) -> None:
    """Flujo real de publicación (sin `_crear_revision` directo): la revisión que crea publicar
    un término guarda su forma editable completa."""
    destino = publicos.destino("Destino del término TKT045", tipos=[])
    termino = publicos.termino("Rapel TKT045", [destino.contenido], estado=E.BORRADOR)
    contenido = termino.contenido
    contenido.fecha_ultima_revision = publicos.BASE
    contenido.save(update_fields=["fecha_ultima_revision"])
    services.publicar(T.TERMINO, contenido.pk, editora.cuenta.pk, contenido.version, None)
    revision = RevisionContenido.objects.get(contenido=contenido)
    assert revision.instantanea == {
        "estado_editorial": "PUBLICADO",
        "titulo": "Rapel TKT045",
        "slug": contenido.slug,
        "definicion": "Definición de Rapel TKT045",
        "fecha_ultima_revision": publicos.BASE.isoformat(),
    }


def test_AC_TKT045_06_coleccion_con_terminos_es_400_no_500(
    cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    """Hallazgo colateral: una colección con `terminos_ids` violaba
    `ck_contenido_termino_tipo_contenido` en el INSERT y respondía 500. Ahora 400 `validacion`."""
    termino = publicos.termino("Glaciar TKT045", [])
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/colecciones",
        {"titulo": "Colección con términos", "terminos_ids": [termino.pk]},
    )
    assert respuesta.status_code == 400, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
    cuerpo = respuesta.json()
    conforme("ProblemaValidacion", cuerpo)
    assert cuerpo["code"] == "validacion"
    assert "terminos_ids" in cuerpo["errors"]
    assert not Contenido.objects.filter(titulo="Colección con términos").exists()
