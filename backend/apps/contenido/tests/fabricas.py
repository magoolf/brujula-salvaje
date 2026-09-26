"""Fábricas mínimas para las pruebas de esquema de TKT-003 (datos ficticios, sin PII real)."""

from __future__ import annotations

import hashlib
import itertools
from contextlib import contextmanager
from datetime import date

from django.db import connection, transaction
from django.utils import timezone

from apps.contenido.models import Contenido, EstadoEditorial
from apps.cuentas.models import CuentaStaff, EstadoCuenta, RolCuenta
from apps.medios.models import Medio

_secuencia = itertools.count(1)


def huella(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()


def crear_medio(**campos) -> Medio:
    n = next(_secuencia)
    datos = {
        "archivo_saneado_ruta": f"originales/prueba-{n}.jpg",
        "formato_origen": "JPEG",
        "ancho_px": 1600,
        "alto_px": 1200,
        "peso_bytes": 250_000,
        "huella_sha256": huella(f"original-{n}"),
        "sha256_saneado": huella(f"saneado-{n}"),
    }
    datos.update(campos)
    return Medio.objects.create(**datos)


def crear_contenido(tipo: str, titulo: str | None = None, **campos) -> Contenido:
    n = next(_secuencia)
    datos = {"tipo": tipo, "slug": f"{tipo.lower()}-{n}", "titulo": titulo or f"{tipo} {n}"}
    datos.update(campos)
    return Contenido.objects.create(**datos)


def campos_publicado(tipo: str, **extra) -> dict:
    """Campos que exigen los CHECK de estado PUBLICADO (portada y SEO según el tipo)."""
    ahora = timezone.now()
    n = next(_secuencia)
    datos = {
        "estado_editorial": EstadoEditorial.PUBLICADO,
        "fecha_ultima_revision": date(2026, 9, 1),
        "primera_publicacion_en": ahora,
        "publicado_actualizado_en": ahora,
    }
    if tipo != "TERMINO":
        datos["seo_descripcion"] = f"Descripción SEO de prueba número {n}"
    if tipo not in ("TERMINO", "PAGINA"):
        datos["portada"] = crear_medio()
    datos.update(extra)
    return datos


def crear_cuenta(usuario: str, rol: str = RolCuenta.EDITOR, **campos) -> CuentaStaff:
    datos = {
        "usuario": usuario,
        "nombre_visible": f"Nombre {usuario}",
        "rol": rol,
        "estado": EstadoCuenta.PENDIENTE_ACTIVACION,
        "password": "pbkdf2_sha256$1$sal$hashficticio",
    }
    datos.update(campos)
    return CuentaStaff.objects.create(**datos)


@contextmanager
def como_rol(rol: str):
    """Ejecuta sentencias con SET LOCAL ROLE dentro de un savepoint que siempre se deshace."""
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(f"SET LOCAL ROLE {rol}")
        try:
            yield cursor
        finally:
            transaction.set_rollback(True)


def forzar_diferidas(*nombres: str) -> None:
    """Evalúa ya las constraints/triggers diferidos indicados (por defecto, al hacer commit)."""
    with connection.cursor() as cursor:
        cursor.execute(f"SET CONSTRAINTS {', '.join(nombres)} IMMEDIATE")


def restaurar_diferidas(*nombres: str) -> None:
    """Vuelve a diferir hasta el commit las constraints/triggers indicados."""
    with connection.cursor() as cursor:
        cursor.execute(f"SET CONSTRAINTS {', '.join(nombres)} DEFERRED")
