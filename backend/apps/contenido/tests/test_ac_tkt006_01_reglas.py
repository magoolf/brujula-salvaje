"""AC-TKT006: reglas de publicación puras (RULE-002..006, 009, 023..027).

Pruebas unitarias sin base de datos: `apps.contenido.reglas` no accede al ORM (Skill_Backend
§4.2/§4.3), así que estas pruebas son rápidas y cubren cada rama de validación explícitamente.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from apps.contenido import reglas

HOY = date.today()
MANANA = HOY + timedelta(days=1)
AYER = HOY - timedelta(days=1)


def _destino_valido(**overrides: object) -> reglas.DatosDestino:
    datos: dict[str, object] = {
        "resumen": "Resumen corto",
        "descripcion_experta": "palabra " * 600,
        "tipos_ids": (1,),
        "tipo_principal_id": 1,
        "dificultad": 3,
        "meses_mejor_epoca": (1, 2),
        "duracion_min_dias": 3,
        "duracion_max_dias": 7,
        "nivel_presupuesto": 2,
        "clima": "Templado",
        "como_llegar": "En bus",
        "seguridad_riesgos": "Ninguno relevante",
        "sostenibilidad": "Lleva tu basura",
        "latitud": 6.5,
        "longitud": -72.3,
        "portada_id": 10,
        "galeria_ids": (10, 11, 12),
        "fecha_ultima_revision": AYER,
        "seo_descripcion": "Descripción SEO única",
        "medios_disponibles_en_galeria": 3,
        "relacionados_publicados": 3,
        "seo_descripcion_en_uso": False,
    }
    datos.update(overrides)
    return reglas.DatosDestino(**datos)  # type: ignore[arg-type]


def test_AC_TKT006_01_destino_valido_no_tiene_errores() -> None:
    assert reglas.validar_destino(_destino_valido()) == []


@pytest.mark.parametrize(
    ("campo", "valor", "code_esperado"),
    [
        ("resumen", None, "requerido"),
        ("descripcion_experta", None, "requerido"),
        ("dificultad", None, "requerido"),
        ("nivel_presupuesto", None, "requerido"),
        ("clima", None, "requerido"),
        ("como_llegar", None, "requerido"),
        ("seguridad_riesgos", None, "requerido"),
        ("sostenibilidad", None, "requerido"),
        ("portada_id", None, "requerido"),
        ("seo_descripcion", None, "requerido"),
    ],
)
def test_AC_TKT006_01_destino_campo_requerido(
    campo: str, valor: object, code_esperado: str
) -> None:
    errores = reglas.validar_destino(_destino_valido(**{campo: valor}))
    codigos = {e["code"] for e in errores}
    assert code_esperado in codigos


def test_AC_TKT006_01_destino_descripcion_corta_falla() -> None:
    errores = reglas.validar_destino(_destino_valido(descripcion_experta="muy corta"))
    assert any(e["code"] == "minimo_palabras" for e in errores)


def test_AC_TKT006_01_destino_sin_tipos_falla() -> None:
    errores = reglas.validar_destino(_destino_valido(tipos_ids=(), tipo_principal_id=None))
    assert any(e["campo"] == "tipos_ids" for e in errores)


def test_AC_TKT006_01_destino_tipo_principal_fuera_de_lista() -> None:
    errores = reglas.validar_destino(_destino_valido(tipos_ids=(1, 2), tipo_principal_id=99))
    assert any(e["code"] == "no_pertenece" for e in errores)


def test_AC_TKT006_01_destino_duracion_invertida() -> None:
    errores = reglas.validar_destino(_destino_valido(duracion_min_dias=10, duracion_max_dias=2))
    assert any(e["code"] == "rango_invalido" for e in errores)


def test_AC_TKT006_01_destino_galeria_insuficiente() -> None:
    errores = reglas.validar_destino(_destino_valido(medios_disponibles_en_galeria=1))
    assert any(e["code"] == "minimo_medios" for e in errores)


def test_AC_TKT006_01_destino_relacionados_insuficientes() -> None:
    errores = reglas.validar_destino(_destino_valido(relacionados_publicados=1))
    assert any(e["code"] == "relacionados_insuficientes" for e in errores)


def test_AC_TKT006_01_destino_seo_duplicado() -> None:
    errores = reglas.validar_destino(_destino_valido(seo_descripcion_en_uso=True))
    assert any(e["code"] == "seo_duplicado" for e in errores)


def test_AC_TKT006_01_destino_fecha_futura() -> None:
    errores = reglas.validar_destino(_destino_valido(fecha_ultima_revision=MANANA))
    assert any(e["code"] == "fecha_futura" for e in errores)


def _itinerario_valido(**overrides: object) -> reglas.DatosItinerario:
    datos: dict[str, object] = {
        "destino_id": 1,
        "destino_estado": "PUBLICADO",
        "resumen": "Resumen",
        "duracion_dias": 2,
        "dificultad": 2,
        "tipos_ids": (1,),
        "tipos_estados": ("PUBLICADO",),
        "riesgos_seguridad": "Ninguno",
        "portada_id": 5,
        "fecha_ultima_revision": AYER,
        "seo_descripcion": "SEO única",
        "numeros_dia": (1, 2),
        "dias_completos": True,
        "relacionados_publicados": 3,
        "seo_descripcion_en_uso": False,
    }
    datos.update(overrides)
    return reglas.DatosItinerario(**datos)  # type: ignore[arg-type]


def test_AC_TKT006_01_itinerario_valido_no_tiene_errores() -> None:
    assert reglas.validar_itinerario(_itinerario_valido()) == []


def test_AC_TKT006_01_itinerario_destino_no_publicado() -> None:
    errores = reglas.validar_itinerario(_itinerario_valido(destino_estado="BORRADOR"))
    assert any(e["code"] == "destino_no_publicado" for e in errores)


def test_AC_TKT006_01_itinerario_tipo_no_publicado() -> None:
    errores = reglas.validar_itinerario(
        _itinerario_valido(tipos_ids=(1, 2), tipos_estados=("PUBLICADO", "BORRADOR"))
    )
    assert any(e["code"] == "itinerario_tipo_no_publicado" for e in errores)


def test_AC_TKT006_01_itinerario_dias_no_coinciden() -> None:
    errores = reglas.validar_itinerario(_itinerario_valido(duracion_dias=3, numeros_dia=(1, 2)))
    assert any(e["code"] == "dias_no_coinciden" for e in errores)


def test_AC_TKT006_01_itinerario_dias_incompletos() -> None:
    errores = reglas.validar_itinerario(_itinerario_valido(dias_completos=False))
    assert any(e["code"] == "dias_incompletos" for e in errores)


def _guia_valida(**overrides: object) -> reglas.DatosGuia:
    datos: dict[str, object] = {
        "categoria_id": 1,
        "resumen": "Resumen",
        "cuerpo": "Cuerpo de la guía",
        "portada_id": 2,
        "fecha_ultima_revision": AYER,
        "seo_descripcion": "SEO",
        "remite_a_metodologia": False,
        "numero_fuentes": 1,
        "relacionados_publicados": 3,
        "seo_descripcion_en_uso": False,
    }
    datos.update(overrides)
    return reglas.DatosGuia(**datos)  # type: ignore[arg-type]


def test_AC_TKT006_01_guia_valida_no_tiene_errores() -> None:
    assert reglas.validar_guia(_guia_valida()) == []


def test_AC_TKT006_01_guia_sin_fuentes_ni_metodologia() -> None:
    errores = reglas.validar_guia(_guia_valida(numero_fuentes=0, remite_a_metodologia=False))
    assert any(e["campo"] == "fuentes" for e in errores)


def test_AC_TKT006_01_guia_remite_a_metodologia_sin_fuentes_es_valido() -> None:
    errores = reglas.validar_guia(_guia_valida(numero_fuentes=0, remite_a_metodologia=True))
    assert not any(e["campo"] == "fuentes" for e in errores)


def _tipo_valido(**overrides: object) -> reglas.DatosTipoAventura:
    datos: dict[str, object] = {
        "resumen": "Resumen",
        "descripcion": "Descripción",
        "portada_id": 3,
        "fecha_ultima_revision": AYER,
        "seo_descripcion": "SEO",
        "numero_checklist": 0,
        "destinos_publicados": 1,
        "relacionados_publicados": 3,
        "seo_descripcion_en_uso": False,
    }
    datos.update(overrides)
    return reglas.DatosTipoAventura(**datos)  # type: ignore[arg-type]


def test_AC_TKT006_01_tipo_aventura_valido_no_tiene_errores() -> None:
    assert reglas.validar_tipo_aventura(_tipo_valido()) == []


def test_AC_TKT006_01_tipo_aventura_checklist_insuficiente() -> None:
    errores = reglas.validar_tipo_aventura(_tipo_valido(numero_checklist=3))
    assert any(e["code"] == "checklist_insuficiente" for e in errores)


def test_AC_TKT006_01_tipo_aventura_checklist_vacio_es_valido() -> None:
    errores = reglas.validar_tipo_aventura(_tipo_valido(numero_checklist=0))
    assert not any(e["code"] == "checklist_insuficiente" for e in errores)


def test_AC_TKT006_01_tipo_aventura_sin_destino_publicado() -> None:
    errores = reglas.validar_tipo_aventura(_tipo_valido(destinos_publicados=0))
    assert any(e["code"] == "tipo_sin_destino_publicado" for e in errores)


def test_AC_TKT006_01_tipo_aventura_sin_destino_publicado_se_puede_omitir() -> None:
    errores = reglas.validar_tipo_aventura(
        _tipo_valido(destinos_publicados=0), exigir_destino_publicado=False
    )
    assert not any(e["code"] == "tipo_sin_destino_publicado" for e in errores)


def _coleccion_valida(**overrides: object) -> reglas.DatosColeccion:
    datos: dict[str, object] = {
        "portada_id": 1,
        "fecha_ultima_revision": AYER,
        "seo_descripcion": "SEO",
        "elementos_publicados": 4,
        "seo_descripcion_en_uso": False,
    }
    datos.update(overrides)
    return reglas.DatosColeccion(**datos)  # type: ignore[arg-type]


def test_AC_TKT006_01_coleccion_valida_no_tiene_errores() -> None:
    assert reglas.validar_coleccion(_coleccion_valida()) == []


def test_AC_TKT006_01_coleccion_bajo_minimo() -> None:
    errores = reglas.validar_coleccion(_coleccion_valida(elementos_publicados=3))
    assert any(e["code"] == "elementos_insuficientes" for e in errores)


def test_AC_TKT006_01_termino_valido_no_tiene_errores() -> None:
    datos = reglas.DatosTermino(fecha_ultima_revision=AYER, vinculado_a_publicado=True)
    assert reglas.validar_termino(datos) == []


def test_AC_TKT006_01_termino_sin_vinculo() -> None:
    datos = reglas.DatosTermino(fecha_ultima_revision=AYER, vinculado_a_publicado=False)
    errores = reglas.validar_termino(datos)
    assert any(e["code"] == "sin_vinculo_publicado" for e in errores)


def test_AC_TKT006_01_pagina_institucional_valida_no_tiene_errores() -> None:
    datos = reglas.DatosPaginaInstitucional(
        cuerpo="Cuerpo",
        version_documento="1.0",
        vigente_desde=AYER,
        fecha_ultima_revision=AYER,
        seo_descripcion="SEO",
    )
    assert reglas.validar_pagina_institucional(datos) == []


def test_AC_TKT006_01_pagina_institucional_sin_cuerpo() -> None:
    datos = reglas.DatosPaginaInstitucional(
        cuerpo=None,
        version_documento="1.0",
        vigente_desde=AYER,
        fecha_ultima_revision=AYER,
        seo_descripcion="SEO",
    )
    errores = reglas.validar_pagina_institucional(datos)
    assert any(e["campo"] == "cuerpo" for e in errores)
