"""TKT-033 (hallazgos de TKT-032 y de su QA): conflictos del panel editorial con el código
documentado en el contrato en lugar de 500.

AC_TKT033_01 (F-032-02): DELETE de un borrador que otro contenido referencia por una FK PROTECT
(itinerario → destino; destino/itinerario → tipo de aventura) → 409 `dependencia_bloqueante` con
`usos` en forma `ReferenciaUso`; nada se borra. Las referencias CASCADE (guías, colecciones,
relaciones, términos) no bloquean, como antes.

AC_TKT033_04 (DEC-AUTO-945): retirar (y "Actualizar publicación" de un destino) con un
`cascada_confirmada` que difiere de la cascada calculada → 409 `impacto_modificado` también
cuando la calculada está vacía (antes 200).

AC_TKT033_05 (INFO): `AnalisisPublicacion.copublicar_tipos[].id` sin `maximum` en el esquema
generado; mensaje del 400 en `tipo_principal_id` cuando el PUT no envía `tipos_ids` (F-032-04).

La carrera alta/DELETE (AC_TKT033_02) está en `test_tkt033_carrera_alta_borrado.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.test import Client

from apps.auditoria.models import MotivoRevision, RevisionContenido
from apps.contenido import services
from apps.contenido.models import (
    Contenido,
    Destino,
    DestinoTipoAventura,
    EstadoEditorial,
    Guia,
    Itinerario,
    TipoAventura,
    TipoContenido,
)
from apps.contenido.tests import publicos
from apps.contenido.tests.fabricas import forzar_diferidas
from apps.core.esquema import GeneradorContrato

T = TipoContenido
E = EstadoEditorial
BASE = "/api/v1/panel/contenidos"

pytestmark = pytest.mark.django_db


def _json(cliente: Client, metodo: str, ruta: str, cuerpo: Any) -> Any:
    return getattr(cliente, metodo)(ruta, cuerpo, content_type="application/json")


def _problema(respuesta: Any, estado: int, codigo: str) -> dict[str, Any]:
    assert respuesta.status_code == estado, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
    cuerpo: dict[str, Any] = respuesta.json()
    assert cuerpo["code"] == codigo, cuerpo
    assert cuerpo["status"] == estado
    assert len(cuerpo["trace_id"]) == 32
    return cuerpo


def _sin_excepciones(logs: Callable[[], list[dict[str, Any]]]) -> None:
    forzar_diferidas("ALL")
    eventos = [linea for linea in logs() if linea.get("event") == "excepcion_no_controlada"]
    assert eventos == []


def _borrar(cliente: Client, ruta: str, contenido: Contenido) -> Any:
    return cliente.delete(f"{BASE}/{ruta}/{contenido.pk}?version={contenido.version}")


def _uso(contenido: Contenido) -> dict[str, Any]:
    return {
        "tipo_entidad": contenido.tipo,
        "id": contenido.pk,
        "titulo": contenido.titulo,
        "estado_editorial": contenido.estado_editorial,
    }


# ---------------------------------------------------------------------------
# AC_TKT033_01 — DELETE de un borrador referenciado por FK PROTECT
# ---------------------------------------------------------------------------
def test_AC_TKT033_01_borrar_destino_referenciado_por_itinerario_es_409(
    cliente_editora: Client,
    logs_json: Callable[[], list[dict[str, Any]]],
    conforme: Callable[[str, Any], None],
) -> None:
    destino = publicos.destino("Destino borrador", tipos=[], estado=E.BORRADOR)
    itinerario = publicos.itinerario("Itinerario que lo usa", destino, estado=E.BORRADOR)

    cuerpo = _problema(
        _borrar(cliente_editora, "destinos", destino.contenido), 409, "dependencia_bloqueante"
    )

    conforme("ProblemaConUsos", cuerpo)
    assert cuerpo["usos"] == [_uso(itinerario.contenido)]
    assert cuerpo["total_usos"] == 1
    assert Destino.objects.filter(pk=destino.pk).exists()  # nada se borra
    _sin_excepciones(logs_json)


def test_AC_TKT033_01_borrar_tipo_referenciado_es_409_con_todos_los_usos(
    cliente_editora: Client,
    logs_json: Callable[[], list[dict[str, Any]]],
    conforme: Callable[[str, Any], None],
) -> None:
    """Tipo de aventura en BORRADOR usado como principal y en `tipos_ids` de un destino y en los
    tipos de un itinerario: cada contenido aparece una sola vez."""
    tipo = publicos.tipo("Tipo borrador", estado=E.BORRADOR)
    destino = publicos.destino("Destino con el tipo", tipos=[tipo], estado=E.BORRADOR)
    itinerario = publicos.itinerario("Itinerario con el tipo", destino, estado=E.BORRADOR)
    itinerario.tipos_aventura.set([tipo])

    cuerpo = _problema(
        _borrar(cliente_editora, "tipos-aventura", tipo.contenido), 409, "dependencia_bloqueante"
    )

    conforme("ProblemaConUsos", cuerpo)
    assert cuerpo["usos"] == [_uso(destino.contenido), _uso(itinerario.contenido)]
    assert cuerpo["total_usos"] == 2
    assert TipoAventura.objects.filter(pk=tipo.pk).exists()
    _sin_excepciones(logs_json)


def test_AC_TKT033_01_borrar_tipo_solo_secundario_de_un_destino_es_409(
    cliente_editora: Client, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    principal = publicos.tipo("Principal", estado=E.BORRADOR)
    secundario = publicos.tipo("Secundario", estado=E.BORRADOR)
    destino = publicos.destino(
        "Destino dos tipos", tipos=[principal, secundario], estado=E.BORRADOR
    )

    cuerpo = _problema(
        _borrar(cliente_editora, "tipos-aventura", secundario.contenido),
        409,
        "dependencia_bloqueante",
    )
    assert cuerpo["usos"] == [_uso(destino.contenido)]
    _sin_excepciones(logs_json)


def test_AC_TKT033_01_sin_referencias_protect_el_borrado_sigue_siendo_204(
    cliente_editora: Client, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """Regresión: quitar la referencia desbloquea el borrado, y las referencias CASCADE (guía →
    destinos) no bloquean: se borran con el destino."""
    destino = publicos.destino("Destino libre", tipos=[], estado=E.BORRADOR)
    itinerario = publicos.itinerario("Itinerario", destino, estado=E.BORRADOR)
    guia = publicos.guia("Guía", estado=E.BORRADOR, destinos=[destino])
    _problema(
        _borrar(cliente_editora, "destinos", destino.contenido), 409, "dependencia_bloqueante"
    )

    Itinerario.objects.filter(pk=itinerario.pk).update(destino=None)
    destino.contenido.refresh_from_db()
    respuesta = _borrar(cliente_editora, "destinos", destino.contenido)

    assert respuesta.status_code == 204, respuesta.content
    assert not Contenido.objects.filter(pk=destino.pk).exists()
    assert list(guia.destinos.all()) == []
    _sin_excepciones(logs_json)


def test_AC_TKT033_01_fk_protect_no_prevista_es_409_y_no_500(
    cliente_editora: Client,
    logs_json: Callable[[], list[dict[str, Any]]],
    conforme: Callable[[str, Any], None],
) -> None:
    """Defensa en profundidad: cualquier otra FK PROTECT hacia el borrador (aquí una revisión,
    que un borrador nunca publicado no debería tener) también es 409, no `ProtectedError`."""
    guia = publicos.guia("Guía con revisión", estado=E.BORRADOR)
    revision = RevisionContenido.objects.create(
        contenido=guia.contenido,
        tipo_contenido=T.GUIA,
        numero_revision=1,
        motivo=MotivoRevision.PUBLICACION,
        instantanea={},
    )

    cuerpo = _problema(
        _borrar(cliente_editora, "guias", guia.contenido), 409, "dependencia_bloqueante"
    )

    conforme("ProblemaConUsos", cuerpo)
    assert cuerpo["total_usos"] == 1
    assert cuerpo["usos"][0]["tipo_entidad"] == "REVISIONCONTENIDO"
    assert cuerpo["usos"][0]["id"] == revision.pk
    assert cuerpo["usos"][0]["estado_editorial"] is None
    assert Guia.objects.filter(pk=guia.pk).exists()
    _sin_excepciones(logs_json)


def test_AC_TKT033_01_usos_de_un_subtipo_en_la_excepcion() -> None:
    """`_usos_de_objetos` traduce un subtipo protegido a la ReferenciaUso de su contenido."""
    destino = publicos.destino("Destino", tipos=[], estado=E.BORRADOR)
    itinerario = publicos.itinerario("Itinerario", destino, estado=E.BORRADOR)
    from django.db.models import ProtectedError

    usos = services._usos_de_objetos(ProtectedError("protegido", {itinerario}))
    assert usos == [_uso(itinerario.contenido)]


def test_AC_TKT033_01_los_usos_se_recortan_al_maximo_del_contrato(
    cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    """`ProblemaConUsos.usos.maxItems: 100`; `total_usos` lleva el total real."""
    destino = publicos.destino("Destino muy usado", tipos=[], estado=E.BORRADOR)
    contenidos = Contenido.objects.bulk_create(
        [
            Contenido(tipo=T.ITINERARIO, slug=f"it-masivo-{n}", titulo=f"Itinerario masivo {n}")
            for n in range(services.MAX_USOS + 3)
        ]
    )
    Itinerario.objects.bulk_create([Itinerario(contenido=c, destino=destino) for c in contenidos])

    cuerpo = _problema(
        _borrar(cliente_editora, "destinos", destino.contenido), 409, "dependencia_bloqueante"
    )

    conforme("ProblemaConUsos", cuerpo)
    assert len(cuerpo["usos"]) == services.MAX_USOS
    assert cuerpo["total_usos"] == services.MAX_USOS + 3


def test_AC_TKT033_01_orden_conflicto_version_antes_que_dependencia(
    cliente_editora: Client,
) -> None:
    destino = publicos.destino("Destino", tipos=[], estado=E.BORRADOR)
    publicos.itinerario("Itinerario", destino, estado=E.BORRADOR)
    respuesta = cliente_editora.delete(
        f"{BASE}/destinos/{destino.pk}?version={destino.contenido.version + 1}"
    )
    _problema(respuesta, 409, "conflicto_version")


# ---------------------------------------------------------------------------
# AC_TKT033_02 (parte determinista) — referencia borrada antes de leerla
# ---------------------------------------------------------------------------
def test_AC_TKT033_02_regla_de_itinerario_con_destino_ya_inexistente() -> None:
    """`_datos_regla_itinerario` no lanza `DoesNotExist` si el destino ya no existe (defensa en
    profundidad del caso visto por la QA al serializar la respuesta del alta)."""
    destino = publicos.destino("Destino", tipos=[], estado=E.BORRADOR)
    itinerario = publicos.itinerario("Itinerario", destino, estado=E.BORRADOR)
    itinerario = Itinerario.objects.get(pk=itinerario.pk)
    itinerario.destino_id = 99_999_999  # solo en memoria

    datos = services._datos_regla_itinerario(itinerario, itinerario.contenido)

    assert datos.destino_estado is None


def test_AC_TKT033_02_alta_bloquea_las_referencias_con_for_key_share(
    cliente_editora: Client,
) -> None:
    """El alta toma `FOR KEY SHARE` sobre los contenidos referenciados, en orden de id."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    tipo = publicos.tipo("Tipo", estado=E.BORRADOR)
    destino = publicos.destino("Destino", tipos=[tipo], estado=E.BORRADOR)
    with CaptureQueriesContext(connection) as consultas:
        respuesta = _json(
            cliente_editora,
            "post",
            f"{BASE}/itinerarios",
            {"titulo": "Con referencias", "destino_id": destino.pk, "tipos_ids": [tipo.pk]},
        )
    assert respuesta.status_code == 201, respuesta.content
    bloqueos = [q["sql"] for q in consultas.captured_queries if "FOR KEY SHARE" in q["sql"]]
    assert len(bloqueos) == 1
    assert "ORDER BY id" in bloqueos[0]


# ---------------------------------------------------------------------------
# AC_TKT033_04 — cascada_confirmada distinta de una cascada calculada vacía
# ---------------------------------------------------------------------------
def _retirar(cliente: Client, ruta: str, contenido: Contenido, **extra: Any) -> Any:
    return _json(
        cliente,
        "post",
        f"{BASE}/{ruta}/{contenido.pk}/retirar",
        {"version": contenido.version, "motivo": "Prueba", **extra},
    )


def test_AC_TKT033_04_retirar_destino_sin_cascada_con_confirmada_distinta_es_409(
    cliente_editora: Client,
    logs_json: Callable[[], list[dict[str, Any]]],
    conforme: Callable[[str, Any], None],
) -> None:
    tipo = publicos.tipo("Tipo compartido")
    destino = publicos.destino("Destino sin cascada", tipos=[tipo])
    publicos.destino("Otro destino del tipo", tipos=[tipo])  # el tipo no queda con 0 destinos
    ajeno = publicos.itinerario("Itinerario ajeno", publicos.destino("Tercero", tipos=[tipo]))

    respuesta = _retirar(
        cliente_editora,
        "destinos",
        destino.contenido,
        confirmar_cascada=True,
        cascada_confirmada=[{"tipo": "ITINERARIO", "id": ajeno.pk}],
    )

    cuerpo = _problema(respuesta, 409, "impacto_modificado")
    conforme("ProblemaConUsos", cuerpo)
    assert cuerpo["impacto_cascada"] == {
        "itinerarios_en_cascada": [],
        "tipos_en_cascada": [],
        "bloqueos_cascada": [],
    }
    destino.contenido.refresh_from_db()
    assert destino.contenido.estado_editorial == E.PUBLICADO  # nada cambia
    _sin_excepciones(logs_json)


def test_AC_TKT033_04_retirar_guia_con_confirmada_no_vacia_es_409(
    cliente_editora: Client,
) -> None:
    """Un tipo sin cascada posible (guía): cualquier `cascada_confirmada` no vacía difiere."""
    tipo = publicos.tipo("Tipo")
    guia = publicos.guia("Guía publicada", tipos=[tipo])
    respuesta = _retirar(
        cliente_editora,
        "guias",
        guia.contenido,
        confirmar_cascada=True,
        cascada_confirmada=[{"tipo": "TIPO", "id": tipo.pk}],
    )
    _problema(respuesta, 409, "impacto_modificado")
    guia.contenido.refresh_from_db()
    assert guia.contenido.estado_editorial == E.PUBLICADO


def test_AC_TKT033_04_retirar_sin_cascada_y_sin_confirmada_sigue_siendo_200(
    cliente_editora: Client,
) -> None:
    tipo = publicos.tipo("Tipo")
    destino = publicos.destino("Destino", tipos=[tipo])
    publicos.destino("Otro", tipos=[tipo])
    respuesta = _retirar(cliente_editora, "destinos", destino.contenido)
    assert respuesta.status_code == 200, respuesta.content


def test_AC_TKT033_04_actualizar_publicacion_sin_cascada_con_confirmada_distinta_es_409(
    cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    tipo = publicos.tipo("Tipo")
    destino = publicos.destino("Destino", tipos=[tipo])
    respuesta = _json(
        cliente_editora,
        "put",
        f"{BASE}/destinos/{destino.pk}",
        {
            "version": destino.contenido.version,
            "titulo": destino.contenido.titulo,
            "tipos_ids": [tipo.pk],
            "tipo_principal_id": tipo.pk,
            "resumen": "Resumen nuevo",
            "cascada_confirmada": [{"tipo": "TIPO", "id": tipo.pk}],
        },
    )
    cuerpo = _problema(respuesta, 409, "impacto_modificado")
    conforme("ProblemaConUsos", cuerpo)
    assert cuerpo["impacto_cascada"]["tipos_en_cascada"] == []


# ---------------------------------------------------------------------------
# AC_TKT033_05 — INFO
# ---------------------------------------------------------------------------
def test_AC_TKT033_05_tipo_versionado_de_respuesta_sin_maximum() -> None:
    esquema = GeneradorContrato().get_schema(request=None, public=True)
    propiedad = esquema["components"]["schemas"]["TipoVersionado"]["properties"]["id"]
    assert "maximum" not in propiedad
    assert propiedad["minimum"] == 1
    assert propiedad["format"] == "int64"


def test_AC_TKT033_05_mensaje_del_principal_cuando_el_put_omite_tipos_ids(
    cliente_editora: Client,
) -> None:
    """F-032-04: un PUT sin `tipos_ids` (opcional, vacío por defecto) sobre un destino con tipo
    principal guardado da 400 en `tipo_principal_id`; el mensaje explica por qué."""
    guardado = publicos.tipo("Guardado", estado=E.BORRADOR)
    destino = publicos.destino("Destino", tipos=[guardado], estado=E.BORRADOR)
    respuesta = _json(
        cliente_editora,
        "put",
        f"{BASE}/destinos/{destino.pk}",
        {"version": destino.contenido.version, "titulo": "Destino"},
    )
    errores = _problema(respuesta, 400, "validacion")["errors"]
    mensaje = errores["tipo_principal_id"][0]
    assert "vacío" in mensaje
    assert "si se omite" in mensaje
    assert "tipo_principal_id: null" in mensaje
    assert DestinoTipoAventura.objects.filter(destino=destino).count() == 1  # nada cambia


def test_AC_TKT033_05_mensaje_del_principal_cuando_el_alta_no_trae_tipos(
    cliente_editora: Client,
) -> None:
    tipo = publicos.tipo("Tipo", estado=E.BORRADOR)
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/destinos",
        {"titulo": "Nuevo", "tipo_principal_id": tipo.pk},
    )
    errores = _problema(respuesta, 400, "validacion")["errors"]
    assert "si se omite, se guarda vacío" in errores["tipo_principal_id"][0]


def test_AC_TKT033_05_principal_fuera_de_tipos_no_vacios_mantiene_el_mensaje(
    cliente_editora: Client,
) -> None:
    """Con `tipos_ids` no vacío y el principal guardado fuera de ellos, el mensaje corto."""
    guardado = publicos.tipo("Guardado", estado=E.BORRADOR)
    otro = publicos.tipo("Otro", estado=E.BORRADOR)
    destino = publicos.destino("Destino", tipos=[guardado], estado=E.BORRADOR)
    respuesta = _json(
        cliente_editora,
        "put",
        f"{BASE}/destinos/{destino.pk}",
        {"version": destino.contenido.version, "titulo": "Destino", "tipos_ids": [otro.pk]},
    )
    errores = _problema(respuesta, 400, "validacion")["errors"]
    assert errores["tipo_principal_id"] == ["Debe pertenecer a tipos_ids."]
