"""TKT-032 (hallazgos de la QA de TKT-012): el panel editorial no responde 500 ante entradas que
la BD rechaza; valida ANTES de escribir y responde el Problem Details que documenta el contrato.

F1. Referencias inexistentes (FK simples DEFERRABLE, que fallaban en el COMMIT; FK compuestas
(id, tipo), que fallaban en el INSERT), CHECK de varios campos (coordenadas, duración, tipo
principal dentro de los tipos), longitud del HTML ya saneado, relación consigo mismo y título
duplicado al actualizar una publicación o una página → 400 `validacion` (o 409 `duplicado`).
Cada prueba fuerza además las restricciones diferidas tras la petición (`forzar_diferidas`): con
el código anterior la petición devolvía 201/200 y la violación quedaba pendiente hasta el COMMIT
(500 `error_interno` en producción); ahora no queda nada pendiente. Y el log no registra ninguna
`excepcion_no_controlada`.

F2. `uniqueItems` del contrato aplicado en `copublicar_tipos` (publicar y actualizar
publicación), `cascada_confirmada` (retirar) y `tipos_ids` de `analisis-publicacion`, y
documentado en el esquema generado igual que en el contrato.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.test import Client

from apps.contenido.models import Contenido, Destino, EstadoEditorial, TipoContenido
from apps.contenido.tests import publicos
from apps.contenido.tests.fabricas import forzar_diferidas
from apps.core.esquema import GeneradorContrato

T = TipoContenido
E = EstadoEditorial
BASE = "/api/v1/panel/contenidos"
NX = 99_999_999
FUERA_DE_BIGINT = 2**63 + 5
HTML_QUE_CRECE = "&" * 100_000  # 100 000 caracteres → 500 000 tras escapar `&` (`&amp;`)

pytestmark = pytest.mark.django_db


def _json(cliente: Client, metodo: str, ruta: str, cuerpo: Any) -> Any:
    return getattr(cliente, metodo)(ruta, cuerpo, content_type="application/json")


def _problema(respuesta: Any, estado: int, codigo: str) -> dict[str, Any]:
    assert respuesta.status_code == estado, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
    cuerpo: dict[str, Any] = respuesta.json()
    assert cuerpo["code"] == codigo
    assert cuerpo["status"] == estado
    assert len(cuerpo["trace_id"]) == 32
    return cuerpo


def _sin_excepciones(logs: Callable[[], list[dict[str, Any]]]) -> None:
    forzar_diferidas("ALL")  # nada inválido queda pendiente para el COMMIT
    eventos = [linea for linea in logs() if linea.get("event") == "excepcion_no_controlada"]
    assert eventos == []


# ---------------------------------------------------------------------------
# F1 — alta (POST) con referencias inexistentes o datos que viola un CHECK
# ---------------------------------------------------------------------------
CASOS_ALTA: list[tuple[str, dict[str, Any], str]] = [
    # (ruta, campos además de `titulo`, clave de `errors` esperada)
    ("destinos", {"pais_id": NX}, "pais_id"),
    ("destinos", {"portada_id": NX}, "portada_id"),
    ("destinos", {"galeria_ids": [NX]}, "galeria_ids.0"),
    ("destinos", {"tipos_ids": [NX]}, "tipos_ids.0"),
    ("destinos", {"terminos_ids": [NX]}, "terminos_ids.0"),
    ("destinos", {"tipo_principal_id": NX}, "tipo_principal_id"),
    ("destinos", {"relaciones": [{"tipo": "TIPO", "id": NX}]}, "relaciones.0.id"),
    ("destinos", {"latitud": 4.5}, "longitud"),
    ("destinos", {"longitud": -74.1}, "latitud"),
    ("destinos", {"duracion_min_dias": 9, "duracion_max_dias": 3}, "duracion_max_dias"),
    ("destinos", {"descripcion_experta": HTML_QUE_CRECE}, "descripcion_experta"),
    ("destinos", {"como_llegar": HTML_QUE_CRECE}, "como_llegar"),
    ("destinos", {"seguridad_riesgos": HTML_QUE_CRECE}, "seguridad_riesgos"),
    ("destinos", {"sostenibilidad": HTML_QUE_CRECE}, "sostenibilidad"),
    ("itinerarios", {"destino_id": NX}, "destino_id"),
    ("itinerarios", {"tipos_ids": [NX]}, "tipos_ids.0"),
    ("itinerarios", {"galeria_ids": [NX]}, "galeria_ids.0"),
    ("itinerarios", {"riesgos_seguridad": HTML_QUE_CRECE}, "riesgos_seguridad"),
    (
        "itinerarios",
        {"dias": [{"numero_dia": 1, "titulo": "Día 1", "actividades": "&" * 50_000}]},
        "dias.0.actividades",
    ),
    (
        "itinerarios",
        {
            "dias": [
                {"numero_dia": 1, "titulo": "Día 1", "actividades": "a", "consejos": "&" * 50_000}
            ]
        },
        "dias.0.consejos",
    ),
    ("guias", {"categoria_id": NX}, "categoria_id"),
    ("guias", {"destinos_ids": [NX]}, "destinos_ids.0"),
    ("guias", {"tipos_ids": [NX]}, "tipos_ids.0"),
    ("guias", {"relaciones": [{"tipo": "TIPO", "id": NX}]}, "relaciones.0.id"),
    ("guias", {"cuerpo": HTML_QUE_CRECE}, "cuerpo"),
    ("tipos-aventura", {"portada_id": NX}, "portada_id"),
    ("tipos-aventura", {"descripcion": HTML_QUE_CRECE}, "descripcion"),
    (
        "colecciones",
        {"elementos": [{"tipo_contenido": "DESTINO", "contenido_id": NX, "orden": 0}]},
        "elementos.0.contenido_id",
    ),
    ("colecciones", {"relaciones": [{"tipo": "TIPO", "id": NX}]}, "relaciones.0.id"),
    ("colecciones", {"portada_id": NX}, "portada_id"),
    ("colecciones", {"descripcion": HTML_QUE_CRECE}, "descripcion"),
]


@pytest.mark.parametrize(("ruta", "campos", "clave"), CASOS_ALTA)
def test_AC_TKT032_01_alta_con_dato_que_la_bd_rechaza_es_400(
    cliente_editora: Client,
    logs_json: Callable[[], list[dict[str, Any]]],
    ruta: str,
    campos: dict[str, Any],
    clave: str,
) -> None:
    antes = Contenido.objects.count()
    respuesta = _json(cliente_editora, "post", f"{BASE}/{ruta}", {"titulo": "Nuevo", **campos})
    cuerpo = _problema(respuesta, 400, "validacion")
    assert clave in cuerpo["errors"], cuerpo["errors"]
    assert Contenido.objects.count() == antes  # no se escribe nada
    _sin_excepciones(logs_json)


@pytest.mark.parametrize(
    ("tipo_relacion", "apunta_a"),
    [("GUIA", "destino"), ("TIPO", "destino"), ("DESTINO", "tipo")],
)
def test_AC_TKT032_01_relacion_con_id_existente_de_otro_tipo_es_400(
    cliente_editora: Client,
    logs_json: Callable[[], list[dict[str, Any]]],
    tipo_relacion: str,
    apunta_a: str,
) -> None:
    """La FK compuesta exige (id, tipo): un id que existe con OTRO tipo tampoco vale."""
    tipo = publicos.tipo("Senderismo")
    destino = publicos.destino("Destino real", tipos=[tipo])
    existente_id = destino.pk if apunta_a == "destino" else tipo.pk
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/guias",
        {"titulo": "Guía", "relaciones": [{"tipo": tipo_relacion, "id": existente_id}]},
    )
    assert _problema(respuesta, 400, "validacion")["errors"] == {"relaciones.0.id": ["No existe."]}
    _sin_excepciones(logs_json)


def test_AC_TKT032_01_principal_sin_tipos_es_400(
    cliente_editora: Client, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """fk_destino_tipo_principal_en_tipos (DEFERRABLE): principal existente pero fuera de
    `tipos_ids` vacío (el serializer solo lo comprobaba con `tipos_ids` no vacío)."""
    tipo = publicos.tipo("Kayak")
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/destinos",
        {"titulo": "Sin tipos", "tipos_ids": [], "tipo_principal_id": tipo.pk},
    )
    assert "tipo_principal_id" in _problema(respuesta, 400, "validacion")["errors"]
    _sin_excepciones(logs_json)


def test_AC_TKT032_01_alta_valida_sigue_creando(
    cliente_editora: Client, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """Regresión: con todas las referencias existentes el alta sigue siendo 201."""
    tipo = publicos.tipo("Escalada")
    otro = publicos.destino("Otro destino", tipos=[tipo])
    pais = otro.pais
    medio = publicos.medio()
    termino = publicos.termino("Vivac", [])
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/destinos",
        {
            "titulo": "Destino completo",
            "pais_id": pais.pk,
            "portada_id": medio.pk,
            "galeria_ids": [medio.pk],
            "tipos_ids": [tipo.pk],
            "tipo_principal_id": tipo.pk,
            "terminos_ids": [termino.pk],
            "relaciones": [{"tipo": "DESTINO", "id": otro.pk}],
            "latitud": 4.5,
            "longitud": -74.1,
            "duracion_min_dias": 3,
            "duracion_max_dias": 3,
            "descripcion_experta": "<p>Texto &amp; más</p>",
        },
    )
    assert respuesta.status_code == 201, respuesta.content
    _sin_excepciones(logs_json)


# ---------------------------------------------------------------------------
# F1 — edición (PUT) de un borrador y de una publicación (valores efectivos)
# ---------------------------------------------------------------------------
def _borrador_destino(cliente: Client, tipo_id: int) -> dict[str, Any]:
    respuesta = _json(
        cliente,
        "post",
        f"{BASE}/destinos",
        {
            "titulo": "Borrador",
            "tipos_ids": [tipo_id],
            "tipo_principal_id": tipo_id,
            "latitud": 1.0,
            "longitud": 2.0,
            "duracion_min_dias": 2,
            "duracion_max_dias": 5,
        },
    )
    assert respuesta.status_code == 201, respuesta.content
    cuerpo: dict[str, Any] = respuesta.json()
    return cuerpo


@pytest.mark.parametrize(
    ("cambios", "clave"),
    [
        ({"latitud": None}, "latitud"),  # la longitud guardada sigue: coordenadas incompletas
        ({"longitud": None}, "longitud"),
        ({"duracion_min_dias": 9}, "duracion_max_dias"),  # el máximo guardado es 5
        ({"tipos_ids": []}, "tipo_principal_id"),  # el principal guardado queda fuera
        ({"tipo_principal_id": NX}, "tipo_principal_id"),
        ({"pais_id": NX}, "pais_id"),
        ({"descripcion_experta": HTML_QUE_CRECE}, "descripcion_experta"),
        ("a-si-mismo", "relaciones.0.id"),
    ],
)
def test_AC_TKT032_01_editar_borrador_con_valores_efectivos_invalidos_es_400(
    cliente_editora: Client,
    logs_json: Callable[[], list[dict[str, Any]]],
    cambios: Any,
    clave: str,
) -> None:
    tipo = publicos.tipo("Barranquismo")
    borrador = _borrador_destino(cliente_editora, tipo.pk)
    if cambios == "a-si-mismo":
        cambios = {"relaciones": [{"tipo": "DESTINO", "id": borrador["id"]}]}
    cuerpo_put = {
        "titulo": "Borrador",
        "version": borrador["version"],
        "tipos_ids": [tipo.pk],
        **cambios,
    }
    respuesta = _json(cliente_editora, "put", f"{BASE}/destinos/{borrador['id']}", cuerpo_put)
    assert clave in _problema(respuesta, 400, "validacion")["errors"]
    destino = Destino.objects.get(pk=borrador["id"])
    assert destino.contenido.version == borrador["version"]  # nada cambió
    assert destino.latitud is not None and destino.longitud is not None
    _sin_excepciones(logs_json)


def test_AC_TKT032_01_editar_borrador_solo_latitud_con_longitud_guardada_es_200(
    cliente_editora: Client, logs_json: Callable[[], list[dict[str, Any]]]
) -> None:
    """Valores efectivos: cambiar solo la latitud de un destino con coordenadas es válido."""
    tipo = publicos.tipo("Trekking")
    borrador = _borrador_destino(cliente_editora, tipo.pk)
    respuesta = _json(
        cliente_editora,
        "put",
        f"{BASE}/destinos/{borrador['id']}",
        {
            "titulo": "Borrador",
            "version": borrador["version"],
            "tipos_ids": [tipo.pk],
            "latitud": 7.25,
        },
    )
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["latitud"] == 7.25
    _sin_excepciones(logs_json)


def _cuerpo_destino_publicado(destino: Destino, **cambios: Any) -> dict[str, Any]:
    principal = destino.tipo_principal_id
    return {
        "titulo": destino.contenido.titulo,
        "version": destino.contenido.version,
        "tipos_ids": [principal],
        "tipo_principal_id": principal,
        **cambios,
    }


@pytest.mark.parametrize(
    ("cambios", "estado", "codigo", "clave"),
    [
        ({"latitud": None}, 400, "validacion", "latitud"),
        ({"pais_id": NX}, 400, "validacion", "pais_id"),
        ({"portada_id": NX}, 400, "validacion", "portada_id"),
        ({"descripcion_experta": HTML_QUE_CRECE}, 400, "validacion", "descripcion_experta"),
        ("a-si-mismo", 400, "validacion", "relaciones.0.id"),
        ({"titulo": "Otro destino publicado"}, 409, "duplicado", "titulo"),
    ],
)
def test_AC_TKT032_01_actualizar_publicacion_con_dato_invalido_no_es_500(
    cliente_editora: Client,
    logs_json: Callable[[], list[dict[str, Any]]],
    cambios: Any,
    estado: int,
    codigo: str,
    clave: str,
) -> None:
    tipo = publicos.tipo("Rafting")
    destino = publicos.destino("Destino publicado", tipos=[tipo])
    publicos.destino("Otro destino publicado", tipos=[tipo])
    if cambios == "a-si-mismo":
        cambios = {"relaciones": [{"tipo": "DESTINO", "id": destino.pk}]}
    respuesta = _json(
        cliente_editora,
        "put",
        f"{BASE}/destinos/{destino.pk}",
        _cuerpo_destino_publicado(destino, **cambios),
    )
    assert clave in _problema(respuesta, estado, codigo)["errors"]
    _sin_excepciones(logs_json)


@pytest.mark.parametrize(
    ("cambios", "estado", "codigo", "clave"),
    [
        ({"titulo": "Aviso legal"}, 409, "duplicado", "titulo"),
        ({"cuerpo": HTML_QUE_CRECE}, 400, "validacion", "cuerpo"),
    ],
)
def test_AC_TKT032_01_actualizar_pagina_institucional_no_es_500(
    cliente_admin: Client,
    logs_json: Callable[[], list[dict[str, Any]]],
    cambios: dict[str, Any],
    estado: int,
    codigo: str,
    clave: str,
) -> None:
    """uq_contenido_tipo_titulo_norm y ck_pagina_institucional_cuerpo_longitud: antes 500."""
    pagina = publicos.pagina("ACERCA_DE", "Acerca de")
    publicos.pagina("AVISO_LEGAL", "Aviso legal")
    respuesta = _json(
        cliente_admin,
        "put",
        f"{BASE}/paginas/{pagina.pk}",
        {
            "titulo": "Acerca de",
            "cuerpo": "<p>Quiénes somos</p>",
            "version_documento": "1.1",
            "vigente_desde": "2026-09-01",
            "version": pagina.contenido.version,
            **cambios,
        },
    )
    assert clave in _problema(respuesta, estado, codigo)["errors"]
    _sin_excepciones(logs_json)


# ---------------------------------------------------------------------------
# F2 — uniqueItems aplicado y documentado
# ---------------------------------------------------------------------------
def test_AC_TKT032_02_publicar_con_copublicar_tipos_repetidos_es_400(
    cliente_editora: Client,
) -> None:
    tipo = publicos.tipo("Ciclismo", estado=E.BORRADOR)
    destino = publicos.destino("Destino borrador", tipos=[tipo], estado=E.BORRADOR)
    version_tipo = tipo.contenido.version
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/destinos/{destino.pk}/publicar",
        {
            "version": destino.contenido.version,
            # mismo id con distinta versión: el contrato prohíbe ids repetidos
            "copublicar_tipos": [
                {"id": tipo.pk, "version": version_tipo},
                {"id": tipo.pk, "version": version_tipo + 1},
            ],
        },
    )
    assert "copublicar_tipos" in _problema(respuesta, 400, "validacion")["errors"]
    destino.contenido.refresh_from_db()
    assert destino.contenido.estado_editorial == E.BORRADOR


def test_AC_TKT032_02_actualizar_publicacion_con_listas_repetidas_es_400(
    cliente_editora: Client,
) -> None:
    tipo = publicos.tipo("Espeleología")
    destino = publicos.destino("Destino con cascada", tipos=[tipo])
    for campo, valor in (
        ("copublicar_tipos", [{"id": tipo.pk, "version": 1}] * 2),
        ("cascada_confirmada", [{"tipo": "TIPO", "id": tipo.pk}] * 2),
    ):
        respuesta = _json(
            cliente_editora,
            "put",
            f"{BASE}/destinos/{destino.pk}",
            _cuerpo_destino_publicado(destino, **{campo: valor}),
        )
        assert campo in _problema(respuesta, 400, "validacion")["errors"]


def test_AC_TKT032_02_retirar_con_cascada_confirmada_repetida_es_400(
    cliente_editora: Client,
) -> None:
    tipo = publicos.tipo("Alpinismo")
    destino = publicos.destino("Destino a retirar", tipos=[tipo])
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/destinos/{destino.pk}/retirar",
        {
            "version": destino.contenido.version,
            "motivo": "Cierre del parque",
            "confirmar_cascada": True,
            "cascada_confirmada": [{"tipo": "TIPO", "id": tipo.pk}] * 2,
        },
    )
    assert "cascada_confirmada" in _problema(respuesta, 400, "validacion")["errors"]
    destino.contenido.refresh_from_db()
    assert destino.contenido.estado_editorial == E.PUBLICADO


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"tipos_ids": [1, 1]},
        {"tipos_ids": [FUERA_DE_BIGINT]},
        {"tipos_ids": [1], "tipo_principal_id": FUERA_DE_BIGINT},
    ],
)
def test_AC_TKT032_02_analisis_publicacion_valida_tipos_ids(
    cliente_editora: Client, cuerpo: dict[str, Any]
) -> None:
    tipo = publicos.tipo("Surf")
    destino = publicos.destino("Destino analizado", tipos=[tipo])
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/destinos/{destino.pk}/analisis-publicacion",
        {"version": destino.contenido.version, **cuerpo},
    )
    _problema(respuesta, 400, "validacion")


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"copublicar_tipos": [{"id": FUERA_DE_BIGINT, "version": 1}]},
        {
            "confirmar_cascada": True,
            "cascada_confirmada": [{"tipo": "TIPO", "id": FUERA_DE_BIGINT}],
        },
    ],
)
def test_AC_TKT032_02_ids_de_operacion_fuera_de_bigint_son_400(
    cliente_editora: Client, cuerpo: dict[str, Any]
) -> None:
    tipo = publicos.tipo("Parapente")
    destino = publicos.destino("Destino con ids grandes", tipos=[tipo])
    respuesta = _json(
        cliente_editora,
        "put",
        f"{BASE}/destinos/{destino.pk}",
        _cuerpo_destino_publicado(destino, **cuerpo),
    )
    _problema(respuesta, 400, "validacion")


def _propiedad(esquemas: dict[str, Any], componente: str, campo: str) -> dict[str, Any]:
    esquema = esquemas[componente]
    for rama in esquema.get("allOf", [esquema]):
        if "$ref" in rama:
            encontrada = _propiedad(esquemas, rama["$ref"].rsplit("/", 1)[-1], campo)
            if encontrada:
                return encontrada
        elif campo in rama.get("properties", {}):
            propiedad: dict[str, Any] = rama["properties"][campo]
            return propiedad
    return {}


@pytest.mark.parametrize(
    ("componente", "campo", "max_items"),
    [
        ("PublicacionEntradaRequest", "copublicar_tipos", 12),
        ("CamposOperacionPublicada", "copublicar_tipos", 12),
        ("CamposOperacionPublicada", "cascada_confirmada", 12),
        ("RetiroEntradaRequest", "cascada_confirmada", 212),
        ("AnalisisPublicacionEntradaRequest", "tipos_ids", 12),
    ],
)
def test_AC_TKT032_02_esquema_generado_documenta_max_y_unique_items(
    componente: str, campo: str, max_items: int
) -> None:
    esquema = GeneradorContrato().get_schema(request=None, public=True)
    propiedad = _propiedad(esquema["components"]["schemas"], componente, campo)
    assert propiedad.get("type") == "array", propiedad
    assert propiedad.get("maxItems") == max_items
    assert propiedad.get("uniqueItems") is True
