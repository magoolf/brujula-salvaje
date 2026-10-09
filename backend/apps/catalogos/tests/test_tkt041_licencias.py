"""TKT-041: catalogos.0004 añade CC BY y CC BY-SA 2.0/2.5/3.0 (fotografías de Wikimedia Commons).

Idempotente, reversible por clave natural y con el texto legal oficial de cada versión
(REQ-043, REQ-071: toda licencia de la semilla exige atribución y es compatible con publicar).
"""

from __future__ import annotations

import importlib

import pytest
from django.apps import apps
from django.db.models import ProtectedError

from apps.catalogos.models import Licencia
from apps.medios.models import EstadoMedio, Medio

pytestmark = pytest.mark.django_db

migracion = importlib.import_module(
    "apps.catalogos.migrations.0004_licencias_cc_versiones_anteriores"
)

ESPERADAS = {
    "CC-BY-2.0": "https://creativecommons.org/licenses/by/2.0/",
    "CC-BY-2.5": "https://creativecommons.org/licenses/by/2.5/",
    "CC-BY-3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC-BY-SA-2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
    "CC-BY-SA-2.5": "https://creativecommons.org/licenses/by-sa/2.5/",
    "CC-BY-SA-3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
}


def test_TKT041_migracion_siembra_versiones_cc_con_atribucion_y_texto_legal() -> None:
    licencias = {lic.codigo: lic for lic in Licencia.objects.filter(codigo__in=ESPERADAS)}
    assert set(licencias) == set(ESPERADAS)
    for codigo, url in ESPERADAS.items():
        licencia = licencias[codigo]
        assert licencia.url_texto_legal == url
        assert licencia.requiere_atribucion is True
        assert licencia.compatible_publicacion is True
        assert licencia.activo is True
        assert licencia.nombre.startswith("Creative Commons Atribución")


def test_TKT041_migracion_idempotente_y_no_pisa_ediciones() -> None:
    Licencia.objects.filter(codigo="CC-BY-2.0").update(nombre="Editada por el administrador")
    antes = Licencia.objects.count()
    migracion.sembrar(apps, None)
    migracion.sembrar(apps, None)
    assert Licencia.objects.count() == antes
    assert Licencia.objects.get(codigo="CC-BY-2.0").nombre == "Editada por el administrador"


def test_TKT041_migracion_reversible_por_clave_natural() -> None:
    antes = Licencia.objects.count()
    migracion.retirar(apps, None)
    assert not Licencia.objects.filter(codigo__in=ESPERADAS).exists()
    assert Licencia.objects.count() == antes - len(ESPERADAS)
    assert Licencia.objects.filter(codigo="CC-BY-SA-4.0").exists()  # no toca catalogos.0002
    migracion.sembrar(apps, None)
    assert Licencia.objects.count() == antes


def test_TKT041_reverse_no_retira_en_silencio_una_licencia_en_uso() -> None:
    Medio.objects.create(
        archivo_saneado_ruta="originales/" + "a" * 64 + ".jpg",
        formato_origen="JPEG",
        ancho_px=1600,
        alto_px=1067,
        peso_bytes=1000,
        huella_sha256="a" * 64,
        sha256_saneado="b" * 64,
        texto_alternativo="Lago de montaña",
        autor_credito="Autora",
        licencia=Licencia.objects.get(codigo="CC-BY-SA-3.0"),
        estado=EstadoMedio.DISPONIBLE,
    )
    with pytest.raises(ProtectedError):
        migracion.retirar(apps, None)
