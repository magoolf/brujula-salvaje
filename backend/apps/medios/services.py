"""Subida, catalogación y ciclo de vida de medios (STATE-002, RULE-005, DEC-AUTO-044/084/110).

Procesamiento síncrono (sin broker, ADR-DB-005): por archivo se verifica el tipo por contenido
(nunca por la extensión ni el `Content-Type` declarado, THREAT-006), el tamaño y las dimensiones
ANTES de decodificar por completo, se recodifica para eliminar metadatos (EXIF/XMP/IPTC,
THREAT-007) y se generan derivados responsivos. Los archivos se guardan con un nombre generado
por el sistema (la huella sha256), nunca con el nombre original del cliente (THREAT-023).

Layout físico bajo `MEDIA_ROOT` (DEVOPS_HANDOFF §6, DEC-AUTO-110/147, TKT-017): `publico/**` son
los derivados de medios DISPONIBLES, servidos como estáticos por nginx en `MEDIA_PUBLIC_URL`;
`privado/**` son el original saneado (nunca se sirve) y los derivados de medios no DISPONIBLES
(solo alcanzables por sesión vía `GET /panel/medios/{id}/archivo`). `catalogar()`/`retirar()`
mueven los derivados entre ambas raíces al cambiar el estado del medio (`_mover_derivados`).
"""

from __future__ import annotations

import hashlib
import io
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from apps.core.exceptions import ErrorApi, NoEncontrado
from apps.medios.models import (
    LADO_MAYOR_MINIMO_PX,
    PESO_MAXIMO_BYTES,
    PIXELES_MAXIMOS,
    EstadoMedio,
    FormatoDerivado,
    FormatoOrigen,
    Medio,
    MedioDerivado,
)

logger = structlog.get_logger("brujula.medios")

_FORMATOS_ORIGEN_PIL = {
    "JPEG": FormatoOrigen.JPEG,
    "PNG": FormatoOrigen.PNG,
    "WEBP": FormatoOrigen.WEBP,
}
ANCHOS_DERIVADOS = (400, 800, 1200, 1600, 2000)
FORMATOS_DERIVADOS = (FormatoDerivado.WEBP, FormatoDerivado.JPEG, FormatoDerivado.AVIF)

# TKT-017: layout físico de MEDIA_ROOT documentado en `docs/05_operacion/DEVOPS_HANDOFF.md` §6
# (Dependencias y tareas del Developer) y DEC-AUTO-147, pero nunca implementado por TKT-006 --
# esa es la causa raíz de los 404 en /media/publico/**: `apps.contenido.api.serializers`
# construye la URL pública como `MEDIA_PUBLIC_URL + derivado.ruta` (fuera de
# `archivos_permitidos`, no se toca), y nginx (`infra/proxy/nginx.conf`, tampoco se toca) solo
# sirve archivos bajo `MEDIA_ROOT/publico/**`; este módulo guardaba todo bajo
# `MEDIA_ROOT/medios/**`, una ruta que nginx nunca expone. `MedioDerivado.ruta` y
# `Medio.archivo_saneado_ruta` se guardan SIN el prefijo de área (p. ej.
# `derivados/<hash>-800.avif`, igual que ya asumían `apps/contenido/tests/publicos.py` y
# `fabricas.py`); el área física
# (`publico/` o `privado/`) se resuelve en tiempo de escritura/lectura a partir del estado del
# medio, nunca se persiste en BD.
RAIZ_PUBLICA = "publico"
RAIZ_PRIVADA = "privado"
# Permisos documentados en DEVOPS_HANDOFF §6 (FILE_UPLOAD_PERMISSIONS 0o640 privado / 0o644
# publico; directorios 0o750 / 0o755). No hay una `FILE_UPLOAD_PERMISSIONS` global en settings
# porque estos archivos no pasan por el manejador de subidas de Django (se escriben a mano tras
# validarlos), así que el modo se fija aquí explícitamente.
_MODO_ARCHIVO = {RAIZ_PUBLICA: 0o644, RAIZ_PRIVADA: 0o640}
_MODO_DIRECTORIO = {RAIZ_PUBLICA: 0o755, RAIZ_PRIVADA: 0o750}


class MedioEnUso(ErrorApi):
    codigo = "medio_en_uso"


class TransicionInvalida(ErrorApi):
    codigo = "transicion_invalida"


@dataclass(frozen=True)
class ResultadoArchivo:
    nombre_archivo: str
    resultado: str  # ACEPTADO | RECHAZADO | DUPLICADO
    medio: Medio | None = None
    medio_existente_id: int | None = None
    motivo: dict[str, str] | None = None


def _ruta_absoluta(area: str, relativa: str) -> Path:
    return Path(settings.MEDIA_ROOT) / area / relativa


def _preparar_directorio(directorio: Path, area: str) -> None:
    """Crea `directorio` si falta y le fija el modo de DEVOPS_HANDOFF §6 (0o755 publico / 0o750
    privado) solo cuando esta llamada lo crea -- nunca reescribe el modo de un directorio ya
    existente (p. ej. la raíz `publico/`/`privado/` que crea `init-volumes`, propiedad de 10001,
    fuera del alcance de este ticket)."""
    if directorio.exists():
        return
    directorio.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directorio, _MODO_DIRECTORIO[area])
    except OSError:  # pragma: no cover - defensivo (FS sin chmod POSIX real)
        logger.warning("chmod_directorio_fallo", directorio=str(directorio))


def _guardar_bytes(area: str, relativa: str, contenido: bytes) -> None:
    ruta = _ruta_absoluta(area, relativa)
    _preparar_directorio(ruta.parent, area)
    ruta.write_bytes(contenido)
    try:
        os.chmod(ruta, _MODO_ARCHIVO[area])
    except OSError:  # pragma: no cover - defensivo (FS sin chmod POSIX real)
        logger.warning("chmod_archivo_fallo", ruta=str(ruta))


def _sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def _validar_formato_y_tamano(contenido: bytes) -> tuple[str, Image.Image]:
    """Abre la imagen y valida el formato real (por contenido) y el tamaño antes de decodificar
    por completo (`Image.open` es perezoso: solo lee la cabecera hasta `load()`/`verify()`)."""
    if len(contenido) < 1 or len(contenido) > PESO_MAXIMO_BYTES:
        raise _rechazo("tamano_excedido", "El archivo supera los 10 MB permitidos.")
    try:
        imagen = Image.open(io.BytesIO(contenido))
        formato = imagen.format
    except Image.DecompressionBombError as exc:
        # TKT-012: Pillow ya rechaza en `open` (solo leyendo la cabecera) una imagen de más del
        # doble de `Image.MAX_IMAGE_PIXELS`; esa excepción NO es OSError y antes escapaba como
        # 500. Es el mismo rechazo de negocio que el límite de 40 MP de abajo.
        raise _rechazo(
            "megapixeles_excedidos", "La imagen supera los 40 megapíxeles permitidos."
        ) from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise _rechazo("archivo_corrupto", "El archivo no es una imagen válida.") from exc
    if formato not in _FORMATOS_ORIGEN_PIL:
        raise _rechazo("formato_no_permitido", "Solo se admiten imágenes JPEG, PNG o WebP.")
    ancho, alto = imagen.size
    if ancho <= 0 or alto <= 0:
        raise _rechazo("archivo_corrupto", "El archivo no es una imagen válida.")
    if ancho * alto > PIXELES_MAXIMOS:
        raise _rechazo("megapixeles_excedidos", "La imagen supera los 40 megapíxeles permitidos.")
    if max(ancho, alto) < LADO_MAYOR_MINIMO_PX:
        raise _rechazo(
            "dimensiones_insuficientes",
            f"El lado mayor debe ser de al menos {LADO_MAYOR_MINIMO_PX}px.",
        )
    try:
        imagen.load()
    except OSError as exc:
        raise _rechazo("archivo_corrupto", "El archivo no es una imagen válida.") from exc
    return formato, imagen


class _RechazadoError(Exception):
    def __init__(self, code: str, detalle: str) -> None:
        self.code = code
        self.detalle = detalle
        super().__init__(detalle)


def _rechazo(code: str, detalle: str) -> _RechazadoError:
    return _RechazadoError(code, detalle)


def _resanear(imagen: Image.Image) -> tuple[bytes, str, str]:
    """Recodifica sin EXIF/XMP/IPTC (THREAT-007): un `Image.new` a partir de los píxeles
    descarta cualquier metadato del archivo original. Devuelve (contenido, sha256, extensión)."""
    modo = "RGB" if imagen.mode not in ("RGB", "RGBA") else imagen.mode
    limpia = Image.new(modo, imagen.size)
    limpia.putdata(imagen.convert(modo).get_flattened_data())
    salida = io.BytesIO()
    extension = "jpg" if modo == "RGB" else "png"
    limpia.save(salida, format="JPEG" if modo == "RGB" else "PNG", quality=92)
    contenido = salida.getvalue()
    return contenido, _sha256(contenido), extension


def _generar_derivados(imagen: Image.Image, huella: str) -> list[MedioDerivado]:
    derivados: list[MedioDerivado] = []
    ancho_original, alto_original = imagen.size
    anchos = sorted({a for a in ANCHOS_DERIVADOS if a <= ancho_original} | {ancho_original})
    base = imagen.convert("RGB")
    for ancho in anchos:
        alto = round(alto_original * (ancho / ancho_original))
        redimensionada = base.resize((ancho, alto), Image.Resampling.LANCZOS)
        for formato in FORMATOS_DERIVADOS:
            buffer = io.BytesIO()
            try:
                redimensionada.save(buffer, format=str(formato))
            except (OSError, ValueError, KeyError):
                # El soporte de escritura AVIF depende de que Pillow esté compilado con
                # libavif; si no está disponible se omite ese derivado (se registra y se sigue).
                logger.warning("derivado_omitido", formato=str(formato), ancho=ancho)
                continue
            contenido = buffer.getvalue()
            sha = _sha256(contenido)
            # Recién generado: el medio dueño siempre está en PENDIENTE_METADATOS (DEC-AUTO-110,
            # ningún medio nace DISPONIBLE), así que el derivado empieza en `privado/`;
            # `catalogar()` lo mueve a `publico/` si y cuando el medio pasa a DISPONIBLE.
            ruta = f"derivados/{huella}-{ancho}.{str(formato).lower()}"
            _guardar_bytes(RAIZ_PRIVADA, ruta, contenido)
            derivados.append(
                MedioDerivado(
                    formato=formato,
                    ancho_px=ancho,
                    alto_px=alto,
                    ruta=ruta,
                    peso_bytes=len(contenido),
                    sha256=sha,
                )
            )
    return derivados


def _mover_derivados(medio: Medio, *, hacia: str) -> None:
    """DEC-AUTO-147 / DEVOPS_HANDOFF §6: al pasar a DISPONIBLE (`catalogar`) o al retirarse
    (`retirar`) los derivados YA GENERADOS se mueven físicamente entre `privado/` y `publico/`
    (nunca se regeneran). `reactivar()` no llama a esta función: solo transiciona
    RETIRADO -> PENDIENTE_METADATOS, y en ambos estados los derivados viven en `privado/`
    (DEC-AUTO-110: solo DISPONIBLE es público) -- no hay nada que mover.

    Se ejecuta de forma síncrona dentro de la misma transacción de BD, no diferida con
    `transaction.on_commit()` (Skill_Backend Regla 05): un `shutil.move` en el mismo volumen
    local no es de la categoría de efecto externo que esa regla obliga a diferir (email, Celery,
    webhook, API externa) -- no hay entrega duplicada ni latencia de red que proteger. Además, en
    cada función que la llama es la ÚLTIMA sentencia, después de guardar el estado y auditar: si
    algo posterior fallara y revirtiera la transacción no se habría llegado aquí. Idempotente
    (comprobación de destino/origen) para que una repetición de `cargar_semilla` o una doble
    llamada no fallen si ya se movió antes."""
    origen_area = RAIZ_PRIVADA if hacia == RAIZ_PUBLICA else RAIZ_PUBLICA
    for derivado in medio.derivados.all():
        origen = _ruta_absoluta(origen_area, derivado.ruta)
        destino = _ruta_absoluta(hacia, derivado.ruta)
        if destino.exists():
            continue  # ya movido (idempotencia)
        if not origen.exists():
            # No debería ocurrir con datos consistentes (se registra pero no se aborta la
            # transición de estado, ya confirmada en BD: un archivo perdido es un problema de
            # infraestructura/volumen, no una razón para bloquear la catalogación/retiro).
            logger.warning(
                "derivado_no_encontrado_al_mover",
                medio_id=medio.pk,
                ruta=derivado.ruta,
                origen_area=origen_area,
            )
            continue
        _preparar_directorio(destino.parent, hacia)
        shutil.move(str(origen), str(destino))
        try:
            os.chmod(destino, _MODO_ARCHIVO[hacia])
        except OSError:  # pragma: no cover - defensivo (FS sin chmod POSIX real)
            logger.warning("chmod_archivo_fallo", ruta=str(destino))


def _medio_por_huella(huella: str) -> Medio | None:
    return Medio.objects.filter(huella_sha256=huella).first()


def subir_medios(actor_id: int, archivos: list[UploadedFile]) -> list[ResultadoArchivo]:
    resultados: list[ResultadoArchivo] = []
    for archivo in archivos:
        nombre = archivo.name or "archivo"
        contenido = archivo.read()
        try:
            formato, imagen = _validar_formato_y_tamano(contenido)
        except _RechazadoError as exc:
            resultados.append(
                ResultadoArchivo(
                    nombre_archivo=nombre,
                    resultado="RECHAZADO",
                    motivo={"code": exc.code, "detalle": exc.detalle},
                )
            )
            continue

        huella = _sha256(contenido)
        existente = _medio_por_huella(huella)
        if existente is not None:
            resultados.append(
                ResultadoArchivo(
                    nombre_archivo=nombre, resultado="DUPLICADO", medio_existente_id=existente.pk
                )
            )
            continue

        with transaction.atomic():
            saneado, sha_saneado, extension = _resanear(imagen)
            # El original saneado nunca se sirve (THREAT-023, ADR-API-002 §8): siempre vive en
            # `privado/`, en todo estado del medio (no lo mueve `_mover_derivados`, que solo
            # actúa sobre `MedioDerivado`).
            ruta_relativa = f"originales/{huella}.{extension}"
            try:
                # Savepoint propio (TKT-012): si otra petición concurrente insertó la misma
                # huella entre la comprobación de arriba y este INSERT, el IntegrityError solo
                # deshace este savepoint. Sin él, la transacción exterior quedaba rota y la
                # consulta de abajo fallaba (TransactionManagementError -> 500) en vez de
                # responder DUPLICADO.
                with transaction.atomic():
                    medio = Medio.objects.create(
                        archivo_saneado_ruta=ruta_relativa,
                        formato_origen=_FORMATOS_ORIGEN_PIL[formato],
                        ancho_px=imagen.width,
                        alto_px=imagen.height,
                        peso_bytes=len(contenido),
                        huella_sha256=huella,
                        sha256_saneado=sha_saneado,
                        subido_por_id=actor_id,
                    )
            except IntegrityError:
                existente = _medio_por_huella(huella)
                resultados.append(
                    ResultadoArchivo(
                        nombre_archivo=nombre,
                        resultado="DUPLICADO",
                        medio_existente_id=existente.pk if existente else None,
                    )
                )
                continue
            _guardar_bytes(RAIZ_PRIVADA, ruta_relativa, saneado)
            derivados = _generar_derivados(imagen, huella)
            # `bulk_create` inserta `char(64)` por una expresión UNNEST que Postgres/psycopg
            # castea a `char[]` (longitud 1 por omisión) y trunca cada huella a un carácter: se
            # crea cada derivado por separado, como ya hace `apps.contenido.tests.publicos`.
            for derivado in derivados:
                derivado.medio = medio
                derivado.save()
        resultados.append(
            ResultadoArchivo(nombre_archivo=nombre, resultado="ACEPTADO", medio=medio)
        )
    return resultados


def obtener(medio_id: int) -> Medio:
    medio = Medio.objects.select_related("licencia").filter(pk=medio_id).first()
    if medio is None:
        raise NoEncontrado()
    return medio


def _pendientes_catalogacion(medio: Medio, *, licencia_compatible: bool | None) -> list[str]:
    pendientes = []
    if not medio.texto_alternativo:
        pendientes.append("texto_alternativo")
    if not medio.autor_credito:
        pendientes.append("autor_credito")
    if medio.licencia_id is None:
        pendientes.append("licencia")
    elif not licencia_compatible:
        pendientes.append("licencia_incompatible")
    return pendientes


def catalogar(medio_id: int, actor_id: int, datos: dict[str, Any]) -> Medio:
    from apps.catalogos.models import Licencia

    with transaction.atomic():
        medio = Medio.objects.select_for_update().filter(pk=medio_id).first()
        if medio is None:
            raise NoEncontrado()
        for campo in (
            "titulo_interno",
            "texto_alternativo",
            "pie_de_foto",
            "autor_credito",
            "fuente_url",
        ):
            if campo in datos:
                setattr(medio, campo, datos[campo])
        if "licencia_id" in datos:
            medio.licencia_id = datos["licencia_id"]
        licencia_compatible = (
            Licencia.objects.filter(pk=medio.licencia_id, compatible_publicacion=True).exists()
            if medio.licencia_id is not None
            else None
        )
        pendientes = _pendientes_catalogacion(medio, licencia_compatible=licencia_compatible)
        pasa_a_disponible = medio.estado == EstadoMedio.PENDIENTE_METADATOS and not pendientes
        if pasa_a_disponible:
            medio.estado = EstadoMedio.DISPONIBLE
        elif (
            medio.estado == EstadoMedio.DISPONIBLE
            and "licencia_incompatible" in pendientes
            and _en_uso_publicado(medio.pk)
        ):
            raise ErrorApi(
                codigo="regla_negocio",
                errors={
                    "licencia_id": [
                        "Licencia incompatible: el medio está en uso por contenido publicado."
                    ]
                },
            )
        medio.actualizado_en = timezone.now()
        medio.save()
        from apps.auditoria import services as auditoria
        from apps.auditoria.models import AccionAuditoria

        auditoria.registrar_evento(
            accion=AccionAuditoria.EDITAR_MEDIO,
            actor_id=actor_id,
            tipo_entidad="MEDIO",
            entidad_id=medio.pk,
        )
        if pasa_a_disponible:
            _mover_derivados(medio, hacia=RAIZ_PUBLICA)
        return medio


def _en_uso_publicado(medio_id: int) -> bool:
    from apps.contenido.models import Contenido, ContenidoMedio, EstadoEditorial
    from apps.inicio.models import ConfigInicio

    en_contenido = Contenido.objects.filter(
        portada_id=medio_id, estado_editorial=EstadoEditorial.PUBLICADO
    ).exists()
    en_galeria = ContenidoMedio.objects.filter(
        medio_id=medio_id, contenido__estado_editorial=EstadoEditorial.PUBLICADO
    ).exists()
    en_hero = ConfigInicio.objects.filter(hero_medio_id=medio_id).exists()
    return en_contenido or en_galeria or en_hero


def usos(medio_id: int) -> list[dict[str, Any]]:
    from apps.contenido.models import Contenido, ContenidoMedio
    from apps.inicio.models import ConfigInicio

    filas: list[dict[str, Any]] = []
    for c in Contenido.objects.filter(portada_id=medio_id):
        filas.append(
            {
                "tipo_contenido": c.tipo,
                "contenido_id": c.pk,
                "titulo": c.titulo,
                "estado_editorial": c.estado_editorial,
                "rol": "PORTADA",
            }
        )
    for cm in ContenidoMedio.objects.filter(medio_id=medio_id).select_related("contenido"):
        filas.append(
            {
                "tipo_contenido": cm.contenido.tipo,
                "contenido_id": cm.contenido_id,
                "titulo": cm.contenido.titulo,
                "estado_editorial": cm.contenido.estado_editorial,
                "rol": "GALERIA",
            }
        )
    if ConfigInicio.objects.filter(hero_medio_id=medio_id).exists():
        filas.append(
            {
                "tipo_contenido": "CONFIG_INICIO",
                "contenido_id": medio_id,
                "titulo": "Portada de inicio",
                "estado_editorial": None,
                "rol": "HERO",
            }
        )
    return filas


def retirar(medio_id: int, actor_id: int) -> Medio:
    with transaction.atomic():
        medio = Medio.objects.select_for_update().filter(pk=medio_id).first()
        if medio is None:
            raise NoEncontrado()
        if _en_uso_publicado(medio_id):
            usos_actuales = usos(medio_id)
            raise MedioEnUso(extra={"usos": usos_actuales, "total_usos": len(usos_actuales)})
        medio.estado = EstadoMedio.RETIRADO
        medio.actualizado_en = timezone.now()
        medio.save()
        from apps.auditoria import services as auditoria
        from apps.auditoria.models import AccionAuditoria

        auditoria.registrar_evento(
            accion=AccionAuditoria.RETIRAR_MEDIO,
            actor_id=actor_id,
            tipo_entidad="MEDIO",
            entidad_id=medio.pk,
        )
        _mover_derivados(medio, hacia=RAIZ_PRIVADA)
        return medio


def reactivar(medio_id: int, actor_id: int) -> Medio:
    # RETIRADO -> PENDIENTE_METADATOS (abajo): ambos son estados "no DISPONIBLE", y `retirar()`
    # ya dejó los derivados en `privado/` -- no hay nada que `_mover_derivados` deba hacer aquí
    # (DEC-AUTO-110: solo DISPONIBLE es público).
    with transaction.atomic():
        medio = Medio.objects.select_for_update().filter(pk=medio_id).first()
        if medio is None:
            raise NoEncontrado()
        if medio.estado != EstadoMedio.RETIRADO:
            raise TransicionInvalida()
        medio.estado = EstadoMedio.PENDIENTE_METADATOS
        medio.actualizado_en = timezone.now()
        medio.save()
        return medio
