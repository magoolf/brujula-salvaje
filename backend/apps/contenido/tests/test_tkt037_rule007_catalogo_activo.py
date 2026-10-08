"""TKT-037 (RULE-007, hallazgo del Developer de TKT-035 y OBS-02 de su QA): el contenido no puede
quedar publicado apuntando a un catálogo retirado (`activo=false`), ni asignarse uno retirado.

- AC_TKT037_01: retirar el país (o su región, o la categoría de la guía) con el contenido en
  BORRADOR y publicarlo después → 422 `publicacion_invalida` con el requisito por campo
  (`pais_retirado` / `region_retirada` / `categoria_retirada`); antes se publicaba. El análisis de
  publicación y la vista previa lo muestran como pendiente.
- AC_TKT037_02: asignar un catálogo retirado (alta, o PUT que lo cambia) → 400 `validacion` en el
  campo. Conservar el que ya tenía un borrador no impide guardarlo (la publicación lo rechaza).
- AC_TKT037_03: la lectura del catálogo toma `FOR SHARE` (choca con el `FOR NO KEY UPDATE` del PUT
  de retirada); la edición bloquea su fila y las referenciadas en orden ascendente de id (OBS-1).
- AC_TKT037_04 (deuda): sin `services._transaccion`, la espera de bloqueo agotada o el
  interbloqueo siguen siendo 409 `conflicto_version` (manejador global de TKT-035) y los demás
  errores operacionales siguen siendo 500.

Las carreras con transacciones reales están en `test_tkt037_carreras.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from apps.catalogos.models import CategoriaGuia, Continente, Pais, Region
from apps.contenido import reglas, services
from apps.contenido.models import (
    Contenido,
    Destino,
    EstadoEditorial,
    Guia,
    TipoAventura,
    TipoContenido,
)
from apps.contenido.tests import publicos

T = TipoContenido
E = EstadoEditorial
BASE = "/api/v1/panel/contenidos"
TAX = "/api/v1/panel/taxonomias"
AYER = date.today() - timedelta(days=1)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _json(cliente: Client, metodo: str, ruta: str, cuerpo: Any) -> Any:
    return getattr(cliente, metodo)(ruta, cuerpo, content_type="application/json")


def _problema(respuesta: Any, estado: int, codigo: str) -> dict[str, Any]:
    assert respuesta.status_code == estado, respuesta.content
    assert respuesta["Content-Type"] == "application/problem+json"
    cuerpo: dict[str, Any] = respuesta.json()
    assert cuerpo["code"] == codigo, cuerpo
    assert len(cuerpo["trace_id"]) == 32
    return cuerpo


def _region(sufijo: str) -> Region:
    return Region.objects.create(
        nombre=f"Región {sufijo}", slug=f"region-{sufijo}", continente=Continente.EUROPA
    )


def _categoria(sufijo: str) -> CategoriaGuia:
    return CategoriaGuia.objects.create(
        nombre=f"Categoría {sufijo}", slug=f"categoria-{sufijo}", descripcion="Para pruebas"
    )


def _retirar_pais(cliente: Client, pais: Pais) -> Any:
    return _json(
        cliente,
        "put",
        f"{TAX}/paises/{pais.pk}",
        {
            "nombre": pais.nombre,
            "slug": pais.slug,
            "codigo_iso2": pais.codigo_iso2,
            "region_id": pais.region_id,
            "activo": False,
        },
    )


def _relleno() -> TipoAventura:
    """Tipo publicado y 3 destinos publicados que lo usan: RULE-006 (≥3 relacionados) por
    afinidad y RULE-002 (tipo del destino ya publicado) sin co-publicación."""
    tipo = publicos.tipo("Tipo publicado TKT-037")
    for i in range(3):
        publicos.destino(f"Relleno TKT-037 {i}", tipos=[tipo])
    return tipo


def datos_destino_publicable(
    tipo: TipoAventura, pais: Pais, sufijo: str = "", **cambios: Any
) -> dict[str, Any]:
    return {
        "titulo": f"Destino TKT-037 {sufijo}",
        "pais_id": pais.pk,
        "tipos_ids": [tipo.pk],
        "tipo_principal_id": tipo.pk,
        "resumen": "Resumen corto",
        "descripcion_experta": "palabra " * 600,
        "dificultad": 3,
        "meses_mejor_epoca": [1, 2],
        "duracion_min_dias": 2,
        "duracion_max_dias": 5,
        "nivel_presupuesto": 2,
        "clima": "Templado",
        "como_llegar": "En bus",
        "seguridad_riesgos": "Ninguno relevante",
        "sostenibilidad": "Lleva tu basura",
        "latitud": 6.5,
        "longitud": -72.3,
        "fecha_ultima_revision": AYER,
        "seo_descripcion": f"SEO única del destino TKT-037 {sufijo}",
        "portada_id": publicos.medio().pk,
        "galeria_ids": [publicos.medio().pk for _ in range(3)],
    } | cambios


def _datos_guia_publicable(categoria: CategoriaGuia, relacionados: list[Contenido]) -> dict:
    return {
        "titulo": "Guía TKT-037",
        "categoria_id": categoria.pk,
        "resumen": "Resumen de la guía",
        "cuerpo": "<p>Cuerpo de la guía</p>",
        "remite_a_metodologia": True,
        "fecha_ultima_revision": AYER,
        "seo_descripcion": "SEO única de la guía TKT-037",
        "portada_id": publicos.medio().pk,
        "relaciones": [{"tipo": c.tipo, "id": c.pk} for c in relacionados],
    }


def _publicar(cliente: Client, ruta: str, contenido: Contenido) -> Any:
    contenido.refresh_from_db()
    return _json(
        cliente, "post", f"{BASE}/{ruta}/{contenido.pk}/publicar", {"version": contenido.version}
    )


def _codigos_principal(cuerpo: dict[str, Any]) -> list[tuple[str, str]]:
    principal = next(e for e in cuerpo["errores_por_entidad"] if e["rol"] == "PRINCIPAL")
    return [(err["campo"], err["code"]) for err in principal["errores"]]


@pytest.fixture
def actor(editora: Any) -> int:
    return int(editora.cuenta.pk)


# ---------------------------------------------------------------------------
# AC_TKT037_01 — publicar con un catálogo retirado
# ---------------------------------------------------------------------------
def test_AC_TKT037_01_retirar_pais_con_destino_en_borrador_y_publicar_es_422(
    cliente_editora: Client, actor: int, conforme: Callable[[str, Any], None]
) -> None:
    tipo = _relleno()
    pais = publicos.pais()
    destino = services.crear_borrador(T.DESTINO, actor, datos_destino_publicable(tipo, pais))
    # El catálogo permite retirarlo: el destino está en borrador (RULE-007, lado de catálogos).
    assert _retirar_pais(cliente_editora, pais).status_code == 200

    cuerpo = _problema(_publicar(cliente_editora, "destinos", destino), 422, "publicacion_invalida")
    conforme("ProblemaPublicacion", cuerpo)
    assert ("pais_id", "pais_retirado") in _codigos_principal(cuerpo)
    assert cuerpo["errors"]["pais_id"] == [reglas.MENSAJE_PAIS_RETIRADO]
    destino.refresh_from_db()
    assert destino.estado_editorial == E.BORRADOR

    # Control positivo: con el país reactivado se publica.
    Pais.objects.filter(pk=pais.pk).update(activo=True)
    assert _publicar(cliente_editora, "destinos", destino).status_code == 200


def test_AC_TKT037_01_pais_de_region_retirada_no_se_publica(
    cliente_editora: Client, actor: int
) -> None:
    tipo = _relleno()
    region = _region("retirada")
    pais = publicos.pais(region=region)
    destino = services.crear_borrador(T.DESTINO, actor, datos_destino_publicable(tipo, pais))
    respuesta = _json(
        cliente_editora,
        "put",
        f"{TAX}/regiones/{region.pk}",
        {
            "nombre": region.nombre,
            "slug": region.slug,
            "continente": region.continente,
            "orden": region.orden,
            "activo": False,
        },
    )
    assert respuesta.status_code == 200, respuesta.content

    cuerpo = _problema(_publicar(cliente_editora, "destinos", destino), 422, "publicacion_invalida")
    assert ("pais_id", "region_retirada") in _codigos_principal(cuerpo)


def test_AC_TKT037_01_retirar_categoria_con_guia_en_borrador_y_publicar_es_422(
    cliente_editora: Client, actor: int, conforme: Callable[[str, Any], None]
) -> None:
    tipo = _relleno()
    relacionados = [d.contenido for d in Destino.objects.filter(tipo_principal=tipo)]
    categoria = _categoria("guia")
    guia = services.crear_borrador(T.GUIA, actor, _datos_guia_publicable(categoria, relacionados))
    respuesta = _json(
        cliente_editora,
        "put",
        f"{TAX}/categorias-guia/{categoria.pk}",
        {
            "nombre": categoria.nombre,
            "slug": categoria.slug,
            "descripcion": categoria.descripcion,
            "orden": categoria.orden,
            "activo": False,
        },
    )
    assert respuesta.status_code == 200, respuesta.content

    cuerpo = _problema(_publicar(cliente_editora, "guias", guia), 422, "publicacion_invalida")
    conforme("ProblemaPublicacion", cuerpo)
    assert _codigos_principal(cuerpo) == [("categoria_id", "categoria_retirada")]

    CategoriaGuia.objects.filter(pk=categoria.pk).update(activo=True)
    assert _publicar(cliente_editora, "guias", guia).status_code == 200


def test_AC_TKT037_01_analisis_y_vista_previa_muestran_el_pais_retirado(
    cliente_editora: Client, actor: int, conforme: Callable[[str, Any], None]
) -> None:
    tipo = _relleno()
    pais = publicos.pais()
    datos = datos_destino_publicable(tipo, pais)
    destino = services.crear_borrador(T.DESTINO, actor, dict(datos))
    Pais.objects.filter(pk=pais.pk).update(activo=False)

    analisis = _json(
        cliente_editora,
        "post",
        f"{BASE}/destinos/{destino.pk}/analisis-publicacion",
        {"version": destino.version},
    )
    assert analisis.status_code == 200, analisis.content
    assert '"pais_retirado"' in analisis.content.decode()

    previa = _json(
        cliente_editora,
        "post",
        f"{BASE}/destinos/vista-previa",
        {**datos, "fecha_ultima_revision": AYER.isoformat()},
    )
    assert previa.status_code == 200, previa.content
    pendientes = previa.json()["requisitos_publicacion"]["pendientes"]
    assert {"campo": "pais_id", "code": "pais_retirado"}.items() <= next(
        p for p in pendientes if p["campo"] == "pais_id"
    ).items()


def test_AC_TKT037_01_actualizar_publicacion_con_pais_retirado_es_422(
    cliente_editora: Client,
) -> None:
    """Defensa: un destino PUBLICADO cuyo país quedó retirado (p. ej. por un cambio fuera de la
    API) no puede "Actualizar publicación" sin elegir un país activo."""
    tipo = _relleno()
    destino = Destino.objects.filter(tipo_principal=tipo).select_related("contenido").first()
    assert destino is not None
    Pais.objects.filter(pk=destino.pais_id).update(activo=False)
    respuesta = _json(
        cliente_editora,
        "put",
        f"{BASE}/destinos/{destino.pk}",
        {
            "version": destino.contenido.version,
            "titulo": destino.contenido.titulo,
            "pais_id": destino.pais_id,
            "tipos_ids": [tipo.pk],
            "tipo_principal_id": tipo.pk,
            "resumen": "Resumen nuevo",
        },
    )
    cuerpo = _problema(respuesta, 422, "publicacion_invalida")
    assert ("pais_id", "pais_retirado") in _codigos_principal(cuerpo)


@pytest.mark.parametrize(
    ("pais_activo", "region_activa", "esperado"),
    [
        (True, True, None),
        (False, True, "pais_retirado"),
        (True, False, "region_retirada"),
        (False, False, "pais_retirado"),
    ],
)
def test_AC_TKT037_01_regla_pura_del_pais(
    pais_activo: bool, region_activa: bool, esperado: str | None
) -> None:
    base = reglas.DatosDestino(
        resumen=None,
        descripcion_experta=None,
        tipos_ids=(),
        tipo_principal_id=None,
        dificultad=None,
        meses_mejor_epoca=(),
        duracion_min_dias=None,
        duracion_max_dias=None,
        nivel_presupuesto=None,
        clima=None,
        como_llegar=None,
        seguridad_riesgos=None,
        sostenibilidad=None,
        latitud=None,
        longitud=None,
        portada_id=None,
        galeria_ids=(),
        fecha_ultima_revision=None,
        seo_descripcion=None,
        pais_id=7,
        pais_activo=pais_activo,
        region_activa=region_activa,
    )
    codigos = {e["code"] for e in reglas.validar_destino(base) if e["campo"] == "pais_id"}
    assert codigos == ({esperado} if esperado else set())


def test_AC_TKT037_01_sin_pais_no_hay_requisito_de_catalogo() -> None:
    assert reglas.mensaje_pais_no_activo(True, True) is None
    assert services._estado_pais(None) == services.EstadoCatalogo(True, True)
    assert services._categoria_activa(None) is True


# ---------------------------------------------------------------------------
# AC_TKT037_02 — asignar un catálogo retirado
# ---------------------------------------------------------------------------
def test_AC_TKT037_02_alta_con_pais_retirado_es_400(
    cliente_editora: Client, conforme: Callable[[str, Any], None]
) -> None:
    pais = publicos.pais()
    Pais.objects.filter(pk=pais.pk).update(activo=False)
    respuesta = _json(
        cliente_editora, "post", f"{BASE}/destinos", {"titulo": "Nuevo", "pais_id": pais.pk}
    )
    cuerpo = _problema(respuesta, 400, "validacion")
    conforme("ProblemaValidacion", cuerpo)
    assert cuerpo["errors"] == {"pais_id": [reglas.MENSAJE_PAIS_RETIRADO]}
    assert not Contenido.objects.filter(titulo="Nuevo").exists()


def test_AC_TKT037_02_alta_con_pais_de_region_retirada_es_400(cliente_editora: Client) -> None:
    region = _region("inactiva")
    pais = publicos.pais(region=region)
    Region.objects.filter(pk=region.pk).update(activo=False)
    respuesta = _json(
        cliente_editora, "post", f"{BASE}/destinos", {"titulo": "Nuevo", "pais_id": pais.pk}
    )
    cuerpo = _problema(respuesta, 400, "validacion")
    assert cuerpo["errors"] == {"pais_id": [reglas.MENSAJE_REGION_RETIRADA]}


def test_AC_TKT037_02_alta_con_pais_inexistente_sigue_siendo_400(cliente_editora: Client) -> None:
    respuesta = _json(
        cliente_editora, "post", f"{BASE}/destinos", {"titulo": "Nuevo", "pais_id": 987654321}
    )
    cuerpo = _problema(respuesta, 400, "validacion")
    assert cuerpo["errors"] == {"pais_id": [services.MENSAJE_INEXISTENTE]}


def test_AC_TKT037_02_alta_de_guia_con_categoria_retirada_es_400(cliente_editora: Client) -> None:
    categoria = _categoria("retirada")
    CategoriaGuia.objects.filter(pk=categoria.pk).update(activo=False)
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/guias",
        {"titulo": "Guía nueva", "categoria_id": categoria.pk},
    )
    cuerpo = _problema(respuesta, 400, "validacion")
    assert cuerpo["errors"] == {"categoria_id": [reglas.MENSAJE_CATEGORIA_RETIRADA]}
    respuesta = _json(
        cliente_editora,
        "post",
        f"{BASE}/guias",
        {"titulo": "Guía nueva", "categoria_id": 987654321},
    )
    assert _problema(respuesta, 400, "validacion")["errors"] == {
        "categoria_id": [services.MENSAJE_INEXISTENTE]
    }


def test_AC_TKT037_02_put_de_borrador_conserva_o_cambia_el_pais(
    cliente_editora: Client, actor: int
) -> None:
    retirado = publicos.pais()
    otro_retirado = publicos.pais()
    activo = publicos.pais()
    destino = services.crear_borrador(
        T.DESTINO, actor, {"titulo": "Borrador", "pais_id": retirado.pk}
    )
    Pais.objects.filter(pk__in=[retirado.pk, otro_retirado.pk]).update(activo=False)

    def put(pais_id: int, version: int) -> Any:
        return _json(
            cliente_editora,
            "put",
            f"{BASE}/destinos/{destino.pk}",
            {"version": version, "titulo": "Borrador", "pais_id": pais_id, "resumen": "Otro"},
        )

    # Conservar el país que se retiró con el destino en borrador no impide guardar el borrador.
    assert put(retirado.pk, 1).status_code == 200
    # Cambiarlo a otro retirado sí: es una asignación.
    cuerpo = _problema(put(otro_retirado.pk, 2), 400, "validacion")
    assert cuerpo["errors"] == {"pais_id": [reglas.MENSAJE_PAIS_RETIRADO]}
    assert Destino.objects.get(pk=destino.pk).pais_id == retirado.pk
    # Y a uno activo, también.
    assert put(activo.pk, 2).status_code == 200
    assert Destino.objects.get(pk=destino.pk).pais_id == activo.pk


def test_AC_TKT037_02_put_de_guia_que_cambia_a_categoria_retirada_es_400(
    cliente_editora: Client, actor: int
) -> None:
    activa = _categoria("activa")
    retirada = _categoria("fuera")
    guia = services.crear_borrador(T.GUIA, actor, {"titulo": "Guía", "categoria_id": activa.pk})
    CategoriaGuia.objects.filter(pk=retirada.pk).update(activo=False)
    respuesta = _json(
        cliente_editora,
        "put",
        f"{BASE}/guias/{guia.pk}",
        {"version": 1, "titulo": "Guía", "categoria_id": retirada.pk},
    )
    assert _problema(respuesta, 400, "validacion")["errors"] == {
        "categoria_id": [reglas.MENSAJE_CATEGORIA_RETIRADA]
    }
    assert Guia.objects.get(pk=guia.pk).categoria_id == activa.pk


# ---------------------------------------------------------------------------
# AC_TKT037_03 — modos y orden de bloqueo
# ---------------------------------------------------------------------------
def _sql(contexto: CaptureQueriesContext) -> list[str]:
    return [q["sql"] for q in contexto.captured_queries]


def _existencia_y_luego_for_share(consultas: list[str]) -> bool:
    """La existencia se lee sin bloquear (un borrado concurrente lo arbitra la FK, TKT-035) y el
    estado `activo` con `FOR SHARE` (una retirada concurrente espera o se espera)."""
    modos = [q.rstrip().endswith("FOR SHARE") for q in consultas]
    return modos == [False, True]


def test_AC_TKT037_03_el_catalogo_se_lee_for_share_dentro_de_la_transaccion(actor: int) -> None:
    pais = publicos.pais()
    with CaptureQueriesContext(connection) as contexto:
        services.crear_borrador(T.DESTINO, actor, {"titulo": "Con país", "pais_id": pais.pk})
    consultas = [q for q in _sql(contexto) if "FROM pais p JOIN region r" in q]
    assert _existencia_y_luego_for_share(consultas), consultas

    categoria = _categoria("bloqueo")
    with CaptureQueriesContext(connection) as contexto:
        services.crear_borrador(T.GUIA, actor, {"titulo": "Con cat", "categoria_id": categoria.pk})
    consultas = [q for q in _sql(contexto) if "FROM categoria_guia" in q]
    assert _existencia_y_luego_for_share(consultas), consultas


@pytest.mark.django_db(transaction=True)
def test_AC_TKT037_03_fuera_de_transaccion_el_catalogo_se_lee_sin_bloquear() -> None:
    """Análisis y vista previa (sin transacción): nada que proteger, lectura sin bloqueo."""
    pais = publicos.pais(region=_region("sin-bloqueo"))
    with CaptureQueriesContext(connection) as contexto:
        assert services._estado_pais(pais.pk) == services.EstadoCatalogo(True, True)
    assert not any("FOR SHARE" in q for q in _sql(contexto))


def _orden_de_bloqueos(sql: list[str], propio: int) -> list[str]:
    """Secuencia de bloqueos de `contenido`: 'ref' (FOR KEY SHARE de referencias) y 'propio'."""
    secuencia = []
    for q in sql:
        if "FOR KEY SHARE" in q and "FROM contenido" in q:
            secuencia.append("ref")
        elif ("FOR UPDATE" in q or "FOR NO KEY UPDATE" in q) and '"contenido"' in q:
            secuencia.append(
                f"propio:{'UPDATE' if 'FOR UPDATE' in q and 'NO KEY' not in q else 'NO KEY'}"
            )
    return secuencia


def test_AC_TKT037_03_la_edicion_bloquea_en_orden_ascendente_de_id(actor: int) -> None:
    menor = services.crear_borrador(T.DESTINO, actor, {"titulo": "Menor"})
    editado = services.crear_borrador(T.DESTINO, actor, {"titulo": "Editado"})
    mayor = services.crear_borrador(T.DESTINO, actor, {"titulo": "Mayor"})
    assert menor.pk < editado.pk < mayor.pk
    relaciones = [{"tipo": T.DESTINO, "id": mayor.pk}, {"tipo": T.DESTINO, "id": menor.pk}]

    # Sin cambio de título: la fila propia con FOR NO KEY UPDATE, tras la referencia menor.
    with CaptureQueriesContext(connection) as contexto:
        services.actualizar(
            T.DESTINO, editado.pk, actor, {"titulo": "Editado", "relaciones": relaciones}, 1
        )
    assert _orden_de_bloqueos(_sql(contexto), editado.pk)[:3] == ["ref", "propio:NO KEY", "ref"]

    # Con cambio de título (UPDATE de clave): la fila propia ya con FOR UPDATE, sin ascenso.
    with CaptureQueriesContext(connection) as contexto:
        services.actualizar(
            T.DESTINO, editado.pk, actor, {"titulo": "Renombrado", "relaciones": relaciones}, 2
        )
    assert _orden_de_bloqueos(_sql(contexto), editado.pk)[:3] == ["ref", "propio:UPDATE", "ref"]


def test_AC_TKT037_03_cambia_clave(actor: int) -> None:
    contenido = services.crear_borrador(T.DESTINO, actor, {"titulo": "Clave", "slug": "clave"})
    assert not services._cambia_clave(T.DESTINO, contenido.pk, {})
    assert not services._cambia_clave(T.DESTINO, contenido.pk, {"titulo": "Clave", "slug": None})
    assert not services._cambia_clave(T.DESTINO, contenido.pk, {"slug": "clave"})
    assert services._cambia_clave(T.DESTINO, contenido.pk, {"titulo": "Otra"})
    assert services._cambia_clave(T.DESTINO, contenido.pk, {"slug": "otra"})
    assert not services._cambia_clave(T.DESTINO, 987654321, {"titulo": "Otra"})


# ---------------------------------------------------------------------------
# AC_TKT037_04 — deuda: traducción de errores de bloqueo solo en core
# ---------------------------------------------------------------------------
def test_AC_TKT037_04_services_ya_no_traduce_errores_de_bd() -> None:
    assert not hasattr(services, "_transaccion")
    assert not hasattr(services, "_SQLSTATE_CONCURRENCIA")
