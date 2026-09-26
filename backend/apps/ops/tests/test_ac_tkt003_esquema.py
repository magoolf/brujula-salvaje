"""Introspección del esquema, privilegios, búsqueda e idempotencia (TKT-003).

AC-TKT003-02 (objetos del DB_HANDOFF existen), AC-TKT003-03 (privilegios), AC-TKT003-04
(idempotencia), AC-TKT003-05 (búsqueda). Las constraints declaradas en los modelos se comparan
con pg_catalog para detectar deriva entre Django y la BD; los objetos RunSQL se listan aquí
explícitamente (RSK-DB-003).
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager

import pytest
from django.apps import apps
from django.core.cache import cache
from django.core.management import call_command
from django.db import IntegrityError, ProgrammingError, connection, models, transaction

from apps.contenido.tests.fabricas import (
    campos_publicado,
    como_rol,
    crear_contenido,
    crear_cuenta,
    crear_medio,
    forzar_diferidas,
    huella,
)
from apps.contenido.models import ContenidoMedio
from apps.inicio.models import ConfigInicio
from apps.ops.bd_pruebas.base import DatabaseOperations
from apps.ops.models import IdempotenciaPeticion, MedioUso, OpsEjecucionTarea

pytestmark = pytest.mark.django_db

TABLAS_DB_HANDOFF = {
    # Catálogos
    "region", "pais", "categoria_guia", "licencia", "nivel_escala",
    # Cuentas y sesiones
    "cuenta_staff", "cuenta_codigo_recuperacion", "sesion_panel",
    # Medios
    "medio", "medio_derivado",
    # Contenido: supertipo, subtipos y relaciones
    "contenido", "tipo_aventura", "checklist_item", "destino", "destino_tipo_aventura",
    "itinerario", "itinerario_tipo_aventura", "dia_itinerario", "guia", "guia_destino",
    "guia_tipo_aventura", "coleccion", "elemento_coleccion", "termino_glosario",
    "contenido_termino", "pagina_institucional", "contenido_medio", "fuente",
    "relacion_contenido", "destacado_inicio",
    # Configuración
    "config_inicio", "config_sitio",
    # Auditoría y revisiones
    "evento_auditoria", "revision_contenido",
    # Derivadas y operación
    "busqueda_documento", "ops_ejecucion_tarea", "cache_limites",
    # CHG-DB-001
    "idempotencia_peticion",
}  # fmt: skip

FK_COMPUESTAS = {
    # nombre: (tabla, destino)
    "fk_tipo_aventura_contenido_tipo": ("tipo_aventura", "contenido"),
    "fk_destino_contenido_tipo": ("destino", "contenido"),
    "fk_itinerario_contenido_tipo": ("itinerario", "contenido"),
    "fk_guia_contenido_tipo": ("guia", "contenido"),
    "fk_coleccion_contenido_tipo": ("coleccion", "contenido"),
    "fk_termino_glosario_contenido_tipo": ("termino_glosario", "contenido"),
    "fk_pagina_institucional_contenido_tipo": ("pagina_institucional", "contenido"),
    "fk_elemento_coleccion_contenido_tipo": ("elemento_coleccion", "contenido"),
    "fk_contenido_termino_contenido_tipo": ("contenido_termino", "contenido"),
    "fk_contenido_medio_contenido_tipo": ("contenido_medio", "contenido"),
    "fk_relacion_contenido_origen_tipo": ("relacion_contenido", "contenido"),
    "fk_relacion_contenido_relacionado_tipo": ("relacion_contenido", "contenido"),
    "fk_destacado_inicio_contenido_tipo": ("destacado_inicio", "contenido"),
    "fk_revision_contenido_contenido_tipo": ("revision_contenido", "contenido"),
    "fk_busqueda_documento_contenido_tipo": ("busqueda_documento", "contenido"),
    "fk_destino_tipo_principal_en_tipos": ("destino", "destino_tipo_aventura"),
}

TRIGGERS = {
    # nombre: (tabla, es_constraint_trigger_diferido)
    "trg_cuenta_admin_minimo": ("cuenta_staff", True),
    "trg_contenido_guardas": ("contenido", False),
    "trg_auditoria_inmutable": ("evento_auditoria", False),
    "trg_auditoria_inmutable_truncate": ("evento_auditoria", False),
    "trg_idempotencia_completa": ("idempotencia_peticion", True),
}

INDICES_CLAVE = {
    "ix_contenido_pub_titulo": "WHERE",
    "ix_contenido_pub_revision": "fecha_ultima_revision DESC",
    "uq_contenido_seo_publicado": "f_normalizar",
    "ix_medio_estado_subido": "subido_en DESC",
    "ix_evento_auditoria_ocurrido": "ocurrido_en DESC",
    "ix_evento_auditoria_actor": "actor_id, ocurrido_en DESC",
    "ix_busqueda_documento_fts": "USING gin (documento)",
    "ix_busqueda_titulo_trgm": "gin_trgm_ops",
    "ix_ops_tarea_iniciado": "iniciado_en DESC",
    "cache_limites_expires": "expires",
}


@contextmanager
def _falla(excepcion=IntegrityError):
    with pytest.raises(excepcion), transaction.atomic():
        yield


def _filas(sql: str, parametros: list | None = None) -> list[tuple]:
    with connection.cursor() as cursor:
        cursor.execute(sql, parametros or [])
        return cursor.fetchall()


def _valor(sql: str, parametros: list | None = None):
    return _filas(sql, parametros)[0][0]


# ---------------------------------------------------------------------------
# AC-TKT003-02: introspección
# ---------------------------------------------------------------------------
def test_AC_TKT003_02_existen_las_38_tablas_y_la_vista():
    relaciones = dict(
        _filas(
            "SELECT c.relname, c.relkind FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'app' AND c.relkind IN ('r', 'v', 'p')"
        )
    )
    tablas = {nombre for nombre, tipo in relaciones.items() if tipo == "r"}
    assert tablas - {"django_migrations"} == TABLAS_DB_HANDOFF
    assert len(TABLAS_DB_HANDOFF) == 38
    assert relaciones["v_medio_uso"] == "v"
    # Sin tablas de apps de Django que el DB_HANDOFF no define.
    assert not {"auth_user", "auth_group", "django_content_type", "django_session"} & tablas
    # public cerrado: nada de la aplicación fuera de app.
    assert _valor(
        "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'v')"
    ) == 0


def test_AC_TKT003_02_constraints_de_los_modelos_existen_en_la_bd():
    constraints_bd = {fila[0] for fila in _filas(
        "SELECT conname FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace "
        "WHERE n.nspname = 'app'"
    )}  # fmt: skip
    indices_bd = {fila[0] for fila in _filas("SELECT indexname FROM pg_indexes WHERE schemaname = 'app'")}
    esperadas = set()
    for modelo in apps.get_models():
        if modelo._meta.app_label == "core" or not modelo._meta.managed:
            continue
        for constraint in modelo._meta.constraints:
            esperadas.add(constraint.name)
        for indice in modelo._meta.indexes:
            assert indice.name in indices_bd, indice.name
    faltan = {n for n in esperadas if n not in constraints_bd and n not in indices_bd}
    assert not faltan
    assert len(esperadas) > 150


def test_AC_TKT003_02_fk_compuestas_por_introspeccion():
    filas = _filas(
        "SELECT c.conname, t.relname, r.relname, cardinality(c.conkey), c.condeferrable, "
        "       c.confdeltype "
        "FROM pg_constraint c "
        "JOIN pg_class t ON t.oid = c.conrelid JOIN pg_class r ON r.oid = c.confrelid "
        "WHERE c.contype = 'f' AND c.conname = ANY(%s)",
        [list(FK_COMPUESTAS)],
    )
    encontradas = {nombre: (tabla, destino) for nombre, tabla, destino, *_ in filas}
    assert encontradas == FK_COMPUESTAS
    for nombre, _tabla, _destino, columnas, diferible, borrado in filas:
        assert columnas == 2
        if nombre == "fk_destino_tipo_principal_en_tipos":
            assert diferible
        elif nombre == "fk_revision_contenido_contenido_tipo":
            assert borrado == "r"  # RESTRICT
        else:
            assert borrado == "c"  # CASCADE


def test_AC_TKT003_02_triggers_funciones_extensiones_y_configuracion():
    filas = _filas(
        "SELECT t.tgname, c.relname, t.tgconstraint <> 0, t.tgdeferrable, t.tgenabled "
        "FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
        "LEFT JOIN pg_constraint k ON k.oid = t.tgconstraint "
        "WHERE NOT t.tgisinternal AND t.tgname = ANY(%s) "
        "   OR (t.tgconstraint <> 0 AND t.tgname = ANY(%s))",
        [list(TRIGGERS), list(TRIGGERS)],
    )
    encontrados = {nombre: (tabla, es_constraint) for nombre, tabla, es_constraint, *_ in filas}
    assert encontrados == TRIGGERS
    for nombre, _tabla, es_constraint, diferible, habilitado in filas:
        assert habilitado == "O", nombre
        if es_constraint:
            assert diferible, nombre

    funciones = dict(
        _filas(
            "SELECT p.proname, p.prosecdef FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'app'"
        )
    )
    for nombre in ("f_normalizar", "f_sin_duplicados", "f_tsquery_prefijo"):
        assert funciones[nombre] is False
    assert funciones["fn_auditoria_purgar"] is True
    assert funciones["fn_auditoria_seudonimizar"] is True
    assert _valor("SELECT provolatile FROM pg_proc WHERE proname = 'f_normalizar'") == "i"

    extensiones = dict(
        _filas(
            "SELECT e.extname, n.nspname FROM pg_extension e "
            "JOIN pg_namespace n ON n.oid = e.extnamespace"
        )
    )
    assert extensiones["unaccent"] == "ext"
    assert extensiones["pg_trgm"] == "ext"
    assert _valor(
        "SELECT count(*) FROM pg_ts_config WHERE cfgname = 'es_unaccent' "
        "AND cfgnamespace = 'app'::regnamespace"
    ) == 1


def test_AC_TKT003_02_tipos_fisicos_collation_generada_e_indices_clave():
    columnas = {
        (tabla, columna): (tipo, collation, generada)
        for tabla, columna, tipo, collation, generada in _filas(
            "SELECT c.relname, a.attname, format_type(a.atttypid, a.atttypmod), "
            "       co.collname, a.attgenerated "
            "FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "LEFT JOIN pg_collation co ON co.oid = a.attcollation "
            "WHERE n.nspname = 'app' AND a.attnum > 0 AND NOT a.attisdropped"
        )
    }
    assert columnas[("contenido", "titulo")][1] == "es-x-icu"
    assert columnas[("contenido", "titulo_norm")][2] == "s"  # STORED
    assert columnas[("evento_auditoria", "ip_truncada")][0] == "cidr"
    assert columnas[("evento_auditoria", "campos_cambiados")][0] == "character varying(60)[]"
    assert columnas[("medio", "huella_sha256")][0] == "character(64)"
    assert columnas[("idempotencia_peticion", "huella_peticion")][0] == "character(64)"
    assert columnas[("idempotencia_peticion", "clave")][0] == "uuid"
    assert columnas[("idempotencia_peticion", "cuerpo_respuesta")][0] == "jsonb"
    assert columnas[("destino", "meses_mejor_epoca")][0] == "smallint[]"
    assert columnas[("destino", "latitud")][0] == "numeric(9,6)"
    assert columnas[("busqueda_documento", "documento")][0] == "tsvector"
    assert columnas[("cuenta_staff", "secreto_mfa")][0] == "bytea"
    assert ("cuenta_staff", "ultimo_acceso_en") in columnas
    assert ("sesion_panel", "cuenta_id") in columnas

    # PK bigint identity (DEC-AUTO-088) y singletons smallint.
    assert _valor(
        "SELECT attidentity FROM pg_attribute WHERE attrelid = 'app.contenido'::regclass "
        "AND attname = 'id'"
    ) == "d"
    assert columnas[("config_sitio", "id")][0] == "smallint"
    # cache_limites UNLOGGED (ADR-DB-005 §3).
    assert _valor("SELECT relpersistence FROM pg_class WHERE oid = 'app.cache_limites'::regclass") == "u"

    definiciones = dict(_filas("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'app'"))
    for indice, fragmento in INDICES_CLAVE.items():
        assert fragmento in definiciones[indice], indice
    assert "expire_date" in " ".join(
        d for n, d in definiciones.items() if n.startswith("sesion_panel_expire_date")
    )


# ---------------------------------------------------------------------------
# AC-TKT003-03: privilegios
# ---------------------------------------------------------------------------
def test_AC_TKT003_03_django_migrations_solo_lectura_para_app_rw():
    with como_rol("app_rw") as cursor:
        cursor.execute("SELECT count(*) FROM app.django_migrations")
        assert cursor.fetchone()[0] >= 12
    with como_rol("app_rw") as cursor, pytest.raises(ProgrammingError, match="permission denied"):
        cursor.execute(
            "INSERT INTO app.django_migrations (app, name, applied) VALUES ('x', 'y', now())"
        )
    with como_rol("app_rw") as cursor, pytest.raises(ProgrammingError, match="permission denied"):
        cursor.execute("DELETE FROM app.django_migrations")


def test_AC_TKT003_03_app_rw_sin_ddl():
    with como_rol("app_rw") as cursor, pytest.raises(ProgrammingError, match="permission denied"):
        cursor.execute("CREATE TABLE app.intrusa (id int)")
    with como_rol("app_rw") as cursor, pytest.raises(ProgrammingError, match="must be owner"):
        cursor.execute("ALTER TABLE app.contenido ADD COLUMN intrusa int")


def test_AC_TKT003_03_app_rw_opera_tablas_de_negocio_e_idempotencia():
    cuenta = crear_cuenta("editora.idem")
    with como_rol("app_rw") as cursor:
        cursor.execute("SELECT count(*) FROM app.contenido")
        cursor.execute(
            "INSERT INTO app.idempotencia_peticion "
            "(cuenta_id, clave, operacion, huella_peticion, codigo_http, cuerpo_respuesta) "
            "VALUES (%s, %s, 'panelCrearGuia', %s, 201, '{\"id\": 1}') RETURNING id",
            [cuenta.pk, uuid.uuid4(), huella("x")],
        )
        fila = cursor.fetchone()[0]
        cursor.execute("UPDATE app.idempotencia_peticion SET recurso_id = 1 WHERE id = %s", [fila])
        cursor.execute("DELETE FROM app.idempotencia_peticion WHERE id = %s", [fila])
        cursor.execute("SELECT count(*) FROM app.cache_limites")
        cursor.execute("SELECT count(*) FROM app.v_medio_uso")


@pytest.mark.parametrize(
    "consulta",
    [
        "SELECT usuario FROM app.cuenta_staff",
        "SELECT nombre_visible FROM app.cuenta_staff",
        "SELECT password FROM app.cuenta_staff",
        "SELECT * FROM app.cuenta_staff",
        "SELECT actor_etiqueta FROM app.evento_auditoria",
        "SELECT ip_truncada FROM app.evento_auditoria",
        "SELECT * FROM app.idempotencia_peticion",
        "SELECT * FROM app.sesion_panel",
        "SELECT * FROM app.cuenta_codigo_recuperacion",
        "SELECT * FROM app.cache_limites",
    ],
)
def test_AC_TKT003_03_readonly_no_ve_pii_ni_tablas_excluidas(consulta):
    with como_rol("readonly") as cursor, pytest.raises(ProgrammingError, match="permission denied"):
        cursor.execute(consulta)


def test_AC_TKT003_03_readonly_lee_columnas_permitidas_y_negocio():
    with como_rol("readonly") as cursor:
        cursor.execute(
            "SELECT id, rol, estado, mfa_activo, creado_en, desactivado_en, anonimizado_en "
            "FROM app.cuenta_staff"
        )
        cursor.execute(
            "SELECT id, ocurrido_en, actor_id, accion, resultado, entidad_titulo "
            "FROM app.evento_auditoria"
        )
        cursor.execute("SELECT count(*) FROM app.contenido")
        cursor.execute("SELECT count(*) FROM app.v_medio_uso")
    with como_rol("readonly") as cursor, pytest.raises(ProgrammingError, match="permission denied"):
        cursor.execute("DELETE FROM app.contenido")


# ---------------------------------------------------------------------------
# AC-TKT003-05: búsqueda en español insensible a tildes (ADR-DB-003)
# ---------------------------------------------------------------------------
def test_AC_TKT003_05_configuracion_es_unaccent_ignora_tildes_y_mayusculas():
    assert _valor(
        "SELECT to_tsvector('app.es_unaccent', 'Montaña Árbol') "
        "@@ to_tsquery('app.es_unaccent', 'montana & arbol')"
    )
    assert _valor(
        "SELECT to_tsvector('app.es_unaccent', 'PATAGONÍA') "
        "@@ plainto_tsquery('app.es_unaccent', 'patagonia')"
    )
    assert _valor("SELECT app.f_normalizar('  PATAGONÍA   Sur ')") == "patagonia sur"
    assert _valor("SELECT app.f_normalizar(NULL)") is None


def test_AC_TKT003_05_tsquery_por_prefijo_seguro():
    assert _valor(
        "SELECT to_tsvector('app.es_unaccent', 'Montañismo en los Andes') "
        "@@ app.f_tsquery_prefijo('mo')"
    )
    assert _valor(
        "SELECT to_tsvector('app.es_unaccent', 'Montañismo en los Andes') "
        "@@ app.f_tsquery_prefijo('ANDES monta')"
    )
    # Sintaxis tsquery del usuario descartada (THREAT-008).
    assert _valor("SELECT app.f_tsquery_prefijo('a & | ! :* ( )')::text") == "'a':*"
    assert _valor("SELECT app.f_tsquery_prefijo('!!! ¿? ')") is None
    tokens = " ".join(f"t{i}" for i in range(15))
    assert _valor("SELECT numnode(app.f_tsquery_prefijo(%s))", [tokens]) == 19  # 10 términos


def test_AC_TKT003_05_pg_trgm_disponible_y_gin_de_similitud():
    assert _valor("SELECT ext.similarity('patagonia', 'patagonai')") > 0.3
    assert _valor("SELECT 'patagonia' OPERATOR(ext.%%) 'patagonai'")
    assert _valor(
        "SELECT count(*) FROM pg_opclass WHERE opcname = 'gin_trgm_ops' "
        "AND opcnamespace = 'ext'::regnamespace"
    ) == 1


# ---------------------------------------------------------------------------
# AC-TKT003-04: idempotencia_peticion (CHG-DB-001)
# ---------------------------------------------------------------------------
def _clave(cuenta, **campos) -> IdempotenciaPeticion:
    datos = {
        "cuenta": cuenta,
        "clave": uuid.uuid4(),
        "operacion": "panelCrearGuia",
        "huella_peticion": huella("peticion"),
    }
    datos.update(campos)
    return IdempotenciaPeticion.objects.create(**datos)


def test_AC_TKT003_04_idempotencia_crear_cuenta_nunca_persiste_el_cuerpo():
    cuenta = crear_cuenta("admin.idem")
    _clave(cuenta, operacion="panelCrearCuenta", codigo_http=201, recurso_id=9, cuerpo_omitido=True)
    with _falla():
        _clave(
            cuenta,
            operacion="panelCrearCuenta",
            codigo_http=201,
            cuerpo_respuesta={"contrasena_temporal": "secreto"},
        )
    with _falla():  # tampoco con cuerpo NULL pero sin marcarlo como omitido
        _clave(cuenta, operacion="panelCrearCuenta", codigo_http=201)


@pytest.mark.parametrize(
    "campos",
    [
        {"operacion": "panelBorrarTodo"},
        {"huella_peticion": "0" * 63 + "Z"},
        {"codigo_http": 409},
        {"cuerpo_omitido": True, "cuerpo_respuesta": {"a": 1}},
        {"cuerpo_respuesta": {"relleno": "x" * 70_000}},
    ],
)
def test_AC_TKT003_04_idempotencia_rechaza_filas_invalidas(campos):
    cuenta = crear_cuenta("editora.idem2")
    with _falla():
        _clave(cuenta, **campos)


def test_AC_TKT003_04_idempotencia_clave_unica_por_cuenta_y_ventana_24h():
    cuenta = crear_cuenta("editora.idem3")
    clave = uuid.uuid4()
    fila = _clave(cuenta, clave=clave, codigo_http=201, cuerpo_respuesta={"id": 1})
    fila.refresh_from_db()
    assert fila.expira_en - fila.creado_en == IdempotenciaPeticion._meta.get_field(
        "expira_en"
    ).db_default.rhs.value
    with _falla():  # misma clave para la misma cuenta, aunque sea otra operación
        _clave(cuenta, clave=clave, operacion="panelCrearDestino")
    _clave(crear_cuenta("editora.idem4"), clave=clave, codigo_http=200, cuerpo_respuesta={})
    with _falla(), connection.cursor() as cursor:
        cursor.execute(
            "UPDATE app.idempotencia_peticion SET expira_en = creado_en + interval '25 hours' "
            "WHERE id = %s",
            [fila.pk],
        )


def test_AC_TKT003_04_trigger_diferido_exige_respuesta_al_confirmar():
    cuenta = crear_cuenta("editora.idem5")
    # Protocolo DEC-AUTO-124: INSERT sin respuesta y UPDATE antes del commit -> válido.
    fila = _clave(cuenta)
    IdempotenciaPeticion.objects.filter(pk=fila.pk).update(
        codigo_http=201, recurso_id=5, cuerpo_respuesta={"id": 5}
    )
    forzar_diferidas("trg_idempotencia_completa")
    # Confirmar una fila sin respuesta -> error del trigger.
    with _falla():
        _clave(cuenta)
        forzar_diferidas("trg_idempotencia_completa")
    # Una fila borrada antes del commit (ROLLBACK lógico del efecto) no molesta.
    borrada = _clave(cuenta)
    IdempotenciaPeticion.objects.filter(pk=borrada.pk).delete()
    forzar_diferidas("trg_idempotencia_completa")


# ---------------------------------------------------------------------------
# Vista v_medio_uso, cache_limites y registro de tareas
# ---------------------------------------------------------------------------
def test_AC_TKT003_02_vista_medio_uso_une_portada_galeria_y_hero():
    portada = crear_medio()
    galeria = crear_medio()
    hero = crear_medio()
    destino = crear_contenido("DESTINO", **campos_publicado("DESTINO", portada=portada))
    ContenidoMedio.objects.create(contenido=destino, tipo_contenido="DESTINO", medio=galeria)
    ConfigInicio.objects.create(hero_titular="Explora", hero_subtitulo="x", hero_medio=hero)

    usos = {u.rol: u for u in MedioUso.objects.filter(medio__in=[portada, galeria, hero])}
    assert set(usos) == {"PORTADA", "GALERIA", "HERO"}
    assert usos["PORTADA"].contenido_id == destino.pk
    assert usos["PORTADA"].estado_editorial == "PUBLICADO"
    assert usos["GALERIA"].medio_id == galeria.pk
    assert usos["HERO"].contenido_id is None
    assert str(usos["HERO"]) == f"HERO del medio #{hero.pk}"
    assert list(portada.usos.values_list("rol", flat=True)) == ["PORTADA"]


def test_AC_TKT003_02_cache_limites_sirve_a_la_cache_de_django():
    cache.set("limite:prueba", 3, 60)
    assert cache.get("limite:prueba") == 3
    assert _valor("SELECT count(*) FROM app.cache_limites") >= 1
    call_command("createcachetable", verbosity=0)  # la tabla ya existe: no hace nada
    assert _valor("SELECT relpersistence FROM pg_class WHERE oid = 'app.cache_limites'::regclass") == "u"


def test_AC_TKT003_04_ops_ejecucion_tarea():
    tarea = OpsEjecucionTarea.objects.create(tarea="PURGA_OPS")
    tarea.refresh_from_db()
    assert tarea.resultado == "EN_CURSO"
    assert str(tarea) == f"PURGA_OPS #{tarea.pk}"
    with _falla():
        OpsEjecucionTarea.objects.create(tarea="TAREA_DESCONOCIDA")
    with _falla():
        OpsEjecucionTarea.objects.create(tarea="PURGA_OPS", resultado="QUIZA")
    cuenta = crear_cuenta("editora.idem6")
    assert str(_clave(cuenta, codigo_http=200, cuerpo_respuesta={})).startswith(
        "Idempotencia panelCrearGuia"
    )


def test_AC_TKT003_08_backend_de_pruebas_solo_envuelve_el_vaciado_de_auditoria():
    operaciones = DatabaseOperations(connection)
    estilo = type("Estilo", (), {"SQL_KEYWORD": staticmethod(str), "SQL_FIELD": staticmethod(str)})
    sql = operaciones.sql_flush(estilo, ["evento_auditoria", "contenido"])
    assert sql[0].startswith("ALTER TABLE") and "DISABLE TRIGGER" in sql[0]
    assert "TRUNCATE" in sql[1]
    assert "ENABLE TRIGGER" in sql[-1]
    assert operaciones.sql_flush(estilo, ["contenido"]) == [
        s for s in operaciones.sql_flush(estilo, ["contenido"])
    ]
    assert "TRIGGER" not in " ".join(operaciones.sql_flush(estilo, ["contenido"]))
    assert operaciones.sql_flush(estilo, []) == []


def test_AC_TKT003_02_str_de_los_modelos_sin_pii():
    for modelo in apps.get_models():
        if modelo._meta.app_label in {"core"}:
            continue
        assert "__str__" in vars(modelo) or any(
            "__str__" in vars(base) for base in modelo.__mro__[1:] if base is not models.Model
        ), modelo
