"""Casos de uso de acceso al panel y de cuentas del staff (MOD-009, MOD-013).

Independientes de HTTP (Skill_Backend §4.2): reciben datos simples y devuelven modelos o valores.
Fuentes: ADR-API-001, BLUEPRINT FEAT-029..032/045, STATE-003/004, RULE-015/017, DEC-AUTO-036..038/
049/102/119, THREAT-001/002/004/018/024/025/027, DB_HANDOFF cuenta_staff y ADR-DB-004.

Reglas clave:
- Anti enumeración (THREAT-018): usuario inexistente, cuenta no operativa o contraseña errónea →
  la misma respuesta 401 `credenciales_invalidas` y el mismo coste (siempre se ejecuta el hash).
- Bloqueo progresivo (DEC-AUTO-049/102): 5 fallos seguidos → bloqueo de 15 min que se duplica en
  cada bloqueo consecutivo (máximo 60 min); la progresión se reinicia tras un acceso correcto o
  tras 1 h sin bloqueos. Se lleva por usuario normalizado exista o no la cuenta: en la fila de la
  cuenta si puede operar, y en la caché (clave HMAC) si no existe o no está operativa.
- Los fallos del segundo factor cuentan como intentos fallidos (FEAT-030).
- Toda acción se audita en la misma transacción (FEAT-046). Nunca se registran secretos.
- Las contraseñas temporales se devuelven una sola vez y solo se guarda su hash (AC-106).
"""

from __future__ import annotations

import secrets
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

import structlog
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.auditoria.models import AccionAuditoria, ResultadoAuditoria
from apps.auditoria.services import registrar_evento, seudonimizar_eventos_de_cuenta
from apps.core import idempotencia
from apps.core.exceptions import ErrorApi
from apps.core.throttling import huella_hmac
from apps.cuentas import mfa, selectors
from apps.cuentas.models import (
    CuentaCodigoRecuperacion,
    CuentaStaff,
    EstadoCuenta,
    RolCuenta,
    SesionPanel,
)

logger = structlog.get_logger("brujula.cuentas")

MAXIMO_FALLOS = 5
BLOQUEO_BASE = timedelta(minutes=15)
BLOQUEO_MAXIMO = timedelta(minutes=60)
REINICIO_PROGRESION = timedelta(hours=1)
LONGITUD_MINIMA_CONTRASENA = 12
TIPO_ENTIDAD_CUENTA = "CUENTA"
_TTL_ANTI_REPETICION_TOTP = 120
_LOCK_CUENTAS_ADMIN = "cuentas_admin"


class Paso(StrEnum):
    """paso_pendiente de SesionEstado (STATE-004, orden SCR-030 → 031 → 032 → 033)."""

    NINGUNO = "NINGUNO"
    MFA = "MFA"
    CAMBIO_CREDENCIAL = "CAMBIO_CREDENCIAL"
    CONFIGURAR_MFA = "CONFIGURAR_MFA"
    AUTORIZACION = "AUTORIZACION"


# ---------------------------------------------------------------------------
# Errores de negocio (RFC 9457, catálogo de apps/core/problemas.py)
# ---------------------------------------------------------------------------
class CredencialesInvalidas(ErrorApi):
    codigo = "credenciales_invalidas"


class AccesoBloqueado(ErrorApi):
    codigo = "acceso_bloqueado_temporalmente"

    def __init__(self, hasta: datetime) -> None:
        segundos = max(1, int((hasta - timezone.now()).total_seconds()) + 1)
        super().__init__(cabeceras={"Retry-After": str(segundos)})


class MfaInvalido(ErrorApi):
    codigo = "mfa_invalido"


class TransicionInvalida(ErrorApi):
    codigo = "transicion_invalida"


def _validacion(campo: str, mensaje: str) -> ErrorApi:
    return ErrorApi(codigo="validacion", errors={campo: [mensaje]})


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def normalizar_usuario(usuario: str) -> str:
    return unicodedata.normalize("NFKC", usuario).strip().lower()


def contrasena_temporal() -> str:
    """24 caracteres aleatorios (≈144 bits); contrato: 16..64 (CuentaConCredencialTemporal)."""
    return secrets.token_urlsafe(18)


_HASH_FICTICIO: list[str] = []


def _hash_ficticio() -> str:
    """Hash de referencia para igualar el coste del login de un usuario inexistente."""
    if not _HASH_FICTICIO:
        _HASH_FICTICIO.append(make_password(secrets.token_urlsafe(24)))
    return _HASH_FICTICIO[0]


def _duracion_bloqueo(bloqueos_consecutivos: int) -> timedelta:
    factor: int = 2 ** max(0, bloqueos_consecutivos - 1)
    return min(BLOQUEO_BASE * factor, BLOQUEO_MAXIMO)


def _estado_tras_bloqueo(cuenta: CuentaStaff) -> str:
    """Estado al que vuelve una cuenta al cumplirse el bloqueo (STATE-003)."""
    if cuenta.autorizacion_otorgada_en is not None and not cuenta.debe_cambiar_credencial:
        return EstadoCuenta.ACTIVA
    return EstadoCuenta.PENDIENTE_ACTIVACION


def _auditar(
    accion: AccionAuditoria,
    actor: CuentaStaff | None,
    *,
    resultado: ResultadoAuditoria = ResultadoAuditoria.EXITO,
    objetivo: CuentaStaff | None = None,
    campos: list[str] | None = None,
    ip: str | None = None,
    etiqueta: str | None = None,
) -> None:
    registrar_evento(
        accion=accion,
        resultado=resultado,
        actor_id=actor.pk if actor is not None else None,
        actor_etiqueta=etiqueta or (actor.usuario if actor is not None else None),
        tipo_entidad=TIPO_ENTIDAD_CUENTA if objetivo is not None else None,
        entidad_id=objetivo.pk if objetivo is not None else None,
        # Sin PII: el título de la entidad sobrevive a la anonimización (trigger inmutable).
        entidad_titulo=f"Cuenta #{objetivo.pk}" if objetivo is not None else None,
        campos_cambiados=campos,
        ip=ip,
    )


def invalidar_sesiones(cuenta_id: int, *, excepto: str | None = None) -> int:
    """Borra las sesiones de una cuenta (THREAT-002/025, AC-107)."""
    sesiones = SesionPanel.objects.filter(cuenta_id=cuenta_id)
    if excepto:
        sesiones = sesiones.exclude(session_key=excepto)
    borradas, _ = sesiones.delete()
    return borradas


# ---------------------------------------------------------------------------
# Contador de fallos por usuario normalizado sin cuenta operativa (caché, clave HMAC)
# ---------------------------------------------------------------------------
def _clave_fallos(usuario: str) -> str:
    return f"login:{huella_hmac(f'login|{usuario}')}"


def _leer_fallos(usuario: str) -> dict[str, Any]:
    datos = cache.get(_clave_fallos(usuario))
    return dict(datos) if isinstance(datos, dict) else {"intentos": 0, "bloqueos": 0, "hasta": None}


def _bloqueo_en_cache(usuario: str, ahora: datetime) -> datetime | None:
    hasta = _leer_fallos(usuario).get("hasta")
    if hasta and datetime.fromisoformat(hasta) > ahora:
        return datetime.fromisoformat(hasta)
    return None


def _fallo_en_cache(usuario: str, ahora: datetime) -> datetime | None:
    """Suma un fallo; devuelve el fin del bloqueo si con él se bloquea."""
    datos = _leer_fallos(usuario)
    hasta = datetime.fromisoformat(datos["hasta"]) if datos.get("hasta") else None
    if hasta is not None and ahora - hasta > REINICIO_PROGRESION:
        datos["bloqueos"] = 0
    datos["intentos"] = int(datos.get("intentos", 0)) + 1
    nuevo_bloqueo: datetime | None = None
    if datos["intentos"] >= MAXIMO_FALLOS:
        datos["bloqueos"] = int(datos.get("bloqueos", 0)) + 1
        nuevo_bloqueo = ahora + _duracion_bloqueo(datos["bloqueos"])
        datos["hasta"] = nuevo_bloqueo.isoformat()
        datos["intentos"] = 0
    ttl = int((BLOQUEO_MAXIMO + REINICIO_PROGRESION).total_seconds())
    cache.set(_clave_fallos(usuario), datos, ttl)
    return nuevo_bloqueo


# ---------------------------------------------------------------------------
# Contador de fallos de una cuenta operativa (fila de cuenta_staff, bajo FOR UPDATE)
# ---------------------------------------------------------------------------
def _liberar_bloqueo_cumplido(cuenta: CuentaStaff, ahora: datetime) -> None:
    if cuenta.bloqueado_hasta is not None and cuenta.bloqueado_hasta <= ahora:
        if cuenta.estado == EstadoCuenta.BLOQUEADA_TEMPORAL:
            cuenta.estado = _estado_tras_bloqueo(cuenta)
        if ahora - cuenta.bloqueado_hasta > REINICIO_PROGRESION:
            cuenta.bloqueos_consecutivos = 0
        cuenta.bloqueado_hasta = None
        cuenta.intentos_fallidos = 0


def _registrar_fallo(cuenta: CuentaStaff, ahora: datetime, ip: str | None) -> datetime | None:
    """Suma un fallo a la cuenta (ya bloqueada con FOR UPDATE) y audita. Fin del bloqueo o None."""
    cuenta.intentos_fallidos += 1
    nuevo_bloqueo: datetime | None = None
    if cuenta.intentos_fallidos >= MAXIMO_FALLOS:
        cuenta.bloqueos_consecutivos += 1
        nuevo_bloqueo = ahora + _duracion_bloqueo(cuenta.bloqueos_consecutivos)
        cuenta.bloqueado_hasta = nuevo_bloqueo
        cuenta.intentos_fallidos = 0
        cuenta.estado = EstadoCuenta.BLOQUEADA_TEMPORAL
    cuenta.save(
        update_fields=["intentos_fallidos", "bloqueos_consecutivos", "bloqueado_hasta", "estado"]
    )
    _auditar(AccionAuditoria.LOGIN_FALLIDO, cuenta, resultado=ResultadoAuditoria.FALLO, ip=ip)
    if nuevo_bloqueo is not None:
        _auditar(AccionAuditoria.BLOQUEO, cuenta, resultado=ResultadoAuditoria.EXITO, ip=ip)
    return nuevo_bloqueo


def _restablecer_contador(cuenta: CuentaStaff) -> None:
    cuenta.intentos_fallidos = 0
    cuenta.bloqueos_consecutivos = 0
    cuenta.bloqueado_hasta = None
    if cuenta.estado == EstadoCuenta.BLOQUEADA_TEMPORAL:
        cuenta.estado = _estado_tras_bloqueo(cuenta)


# ---------------------------------------------------------------------------
# Login por pasos (FLOW-010, ADR-API-001 §3-4)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoLogin:
    cuenta: CuentaStaff
    requiere_mfa: bool


def iniciar_sesion(usuario: str, contrasena: str, ip: str | None) -> ResultadoLogin:
    """Primer paso del login. Lanza CredencialesInvalidas o AccesoBloqueado."""
    normalizado = normalizar_usuario(usuario)
    ahora = timezone.now()
    bloqueo: datetime | None = None
    exito: ResultadoLogin | None = None
    with transaction.atomic():
        cuenta = (
            CuentaStaff.objects.select_for_update()
            .filter(usuario=normalizado, estado__in=selectors.ESTADOS_CON_SESION)
            .first()
        )
        if cuenta is None:
            bloqueo = _fallo_sin_cuenta(normalizado, contrasena, ahora, ip)
        else:
            _liberar_bloqueo_cumplido(cuenta, ahora)
            if cuenta.bloqueado_hasta is not None:
                bloqueo = cuenta.bloqueado_hasta
                cuenta.save(update_fields=["estado", "intentos_fallidos", "bloqueado_hasta"])
            elif cuenta.check_password(contrasena):
                exito = _credencial_correcta(cuenta, ahora, ip)
            else:
                bloqueo = _registrar_fallo(cuenta, ahora, ip)
                if bloqueo is None:
                    exito = None
    if exito is not None:
        return exito
    if bloqueo is not None:
        raise AccesoBloqueado(bloqueo)
    raise CredencialesInvalidas()


def _fallo_sin_cuenta(
    usuario: str, contrasena: str, ahora: datetime, ip: str | None
) -> datetime | None:
    """Usuario inexistente o no operativo: mismo coste, contador en caché y auditoría."""
    bloqueo_vigente = _bloqueo_en_cache(usuario, ahora)
    if bloqueo_vigente is not None:
        return bloqueo_vigente
    check_password(contrasena, _hash_ficticio())
    nuevo_bloqueo = _fallo_en_cache(usuario, ahora)
    existente = selectors.cuenta_por_usuario(usuario)
    actor = existente if existente is not None else None
    _auditar(AccionAuditoria.LOGIN_FALLIDO, actor, resultado=ResultadoAuditoria.FALLO, ip=ip)
    if nuevo_bloqueo is not None:
        _auditar(AccionAuditoria.BLOQUEO, actor, ip=ip)
    return nuevo_bloqueo


def _credencial_correcta(cuenta: CuentaStaff, ahora: datetime, ip: str | None) -> ResultadoLogin:
    if cuenta.mfa_activo:
        # El contador NO se reinicia hasta superar el segundo factor (si no, adivinar el TOTP
        # tendría intentos ilimitados volviendo a introducir la contraseña).
        cuenta.save(update_fields=["estado", "intentos_fallidos", "bloqueado_hasta"])
        return ResultadoLogin(cuenta=cuenta, requiere_mfa=True)
    _acceso_completo(cuenta, ahora, ip)
    return ResultadoLogin(cuenta=cuenta, requiere_mfa=False)


def _acceso_completo(cuenta: CuentaStaff, ahora: datetime, ip: str | None) -> None:
    _restablecer_contador(cuenta)
    cuenta.last_login = ahora
    cuenta.save(
        update_fields=[
            "intentos_fallidos",
            "bloqueos_consecutivos",
            "bloqueado_hasta",
            "estado",
            "last_login",
        ]
    )
    _auditar(AccionAuditoria.LOGIN_OK, cuenta, ip=ip)


def _clave_anti_repeticion(cuenta_id: int) -> str:
    return f"totp:{huella_hmac(f'totp|{cuenta_id}')}"


def _totp_valido(cuenta: CuentaStaff, codigo: str) -> bool:
    """TOTP correcto y no reutilizado (anti repetición dentro de la ventana)."""
    if not cuenta.secreto_mfa:
        return False
    try:
        secreto = mfa.descifrar_secreto(cuenta.secreto_mfa)
    except mfa.SecretoIlegibleError:
        logger.error("mfa_secreto_ilegible", cuenta_id=cuenta.pk)
        return False
    periodo = mfa.verificar_totp(secreto, codigo)
    if periodo is None:
        return False
    clave = _clave_anti_repeticion(cuenta.pk)
    ultimo = cache.get(clave)
    if isinstance(ultimo, int) and periodo <= ultimo:
        return False
    cache.set(clave, periodo, _TTL_ANTI_REPETICION_TOTP)
    return True


def _consumir_codigo_recuperacion(cuenta: CuentaStaff, codigo: str) -> bool:
    usados = CuentaCodigoRecuperacion.objects.filter(
        cuenta=cuenta,
        hash_codigo=mfa.hash_codigo_recuperacion(cuenta.pk, codigo),
        usado_en__isnull=True,
    ).update(usado_en=timezone.now())
    return usados == 1


def verificar_mfa(cuenta_id: int, codigo: str, ip: str | None) -> CuentaStaff:
    """Segundo paso del login (TOTP o código de recuperación). Un fallo cuenta como intento."""
    ahora = timezone.now()
    bloqueo: datetime | None = None
    correcto = False
    with transaction.atomic():
        cuenta = CuentaStaff.objects.select_for_update().get(pk=cuenta_id)
        _liberar_bloqueo_cumplido(cuenta, ahora)
        if cuenta.bloqueado_hasta is not None:
            bloqueo = cuenta.bloqueado_hasta
        elif "-" in codigo:
            correcto = _consumir_codigo_recuperacion(cuenta, codigo)
        else:
            correcto = _totp_valido(cuenta, codigo)
        if correcto:
            _acceso_completo(cuenta, ahora, ip)
        elif bloqueo is None:
            bloqueo = _registrar_fallo(cuenta, ahora, ip)
    if correcto:
        return cuenta
    if bloqueo is not None:
        raise AccesoBloqueado(bloqueo)
    raise MfaInvalido()


def paso_pendiente(cuenta: CuentaStaff, *, mfa_verificado: bool, version_vigente: str) -> Paso:
    if cuenta.mfa_activo and not mfa_verificado:
        return Paso.MFA
    if cuenta.debe_cambiar_credencial:
        return Paso.CAMBIO_CREDENCIAL
    if cuenta.es_administrador and not cuenta.mfa_activo:
        return Paso.CONFIGURAR_MFA
    if cuenta.autorizacion_version_politica != version_vigente:
        return Paso.AUTORIZACION
    return Paso.NINGUNO


def cerrar_sesion(cuenta: CuentaStaff, ip: str | None) -> None:
    """Audita el cierre; la vista borra la sesión (logout y "No autorizo")."""
    _auditar(AccionAuditoria.LOGOUT, cuenta, ip=ip)


# ---------------------------------------------------------------------------
# Credencial propia (FEAT-031, RULE-017)
# ---------------------------------------------------------------------------
_MENSAJE_POLITICA = (
    "Elige una contraseña menos común. Usa al menos 12 caracteres; una frase larga funciona bien."
)


def validar_politica_contrasena(contrasena: str, cuenta: CuentaStaff) -> None:
    """RULE-017: >= 12 caracteres, no común (lista local), distinta del usuario y del nombre."""
    texto = contrasena.strip().lower()
    comunes = CommonPasswordValidator().passwords
    usuario = (cuenta.usuario or "").lower()
    nombre = (cuenta.nombre_visible or "").lower().replace(" ", "")
    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA or texto in comunes:
        raise _validacion("contrasena_nueva", _MENSAJE_POLITICA)
    if usuario and (usuario in texto or texto in usuario):
        raise _validacion("contrasena_nueva", "La contraseña no puede contener tu usuario.")
    if nombre and texto.replace(" ", "") == nombre:
        raise _validacion("contrasena_nueva", "La contraseña no puede ser tu nombre.")


def cambiar_contrasena(
    cuenta_id: int, actual: str, nueva: str, *, sesion_actual: str | None
) -> CuentaStaff:
    with transaction.atomic():
        cuenta = CuentaStaff.objects.select_for_update().get(pk=cuenta_id)
        if not cuenta.check_password(actual):
            raise _validacion("contrasena_actual", "La contraseña actual no es correcta.")
        validar_politica_contrasena(nueva, cuenta)
        if cuenta.check_password(nueva):
            raise _validacion("contrasena_nueva", "La nueva contraseña debe ser distinta.")
        cuenta.set_password(nueva)
        cuenta.debe_cambiar_credencial = False
        if (
            cuenta.estado == EstadoCuenta.PENDIENTE_ACTIVACION
            and cuenta.autorizacion_otorgada_en is not None
        ):
            cuenta.estado = EstadoCuenta.ACTIVA
        cuenta.save(update_fields=["password", "debe_cambiar_credencial", "estado"])
        invalidar_sesiones(cuenta.pk, excepto=sesion_actual)
        _auditar(AccionAuditoria.CAMBIO_CREDENCIAL, cuenta, campos=["password"])
    return cuenta


# ---------------------------------------------------------------------------
# Autorización de tratamiento (FEAT-032, DEC-AUTO-038, REQ-070)
# ---------------------------------------------------------------------------
def registrar_autorizacion(cuenta_id: int, version: str) -> CuentaStaff:
    vigente = selectors.politica_vigente()
    if version != vigente.version:
        raise ErrorApi(
            codigo="conflicto_version",
            detalle="La política de tratamiento cambió. Revisa la versión vigente.",
        )
    with transaction.atomic():
        cuenta = CuentaStaff.objects.select_for_update().get(pk=cuenta_id)
        cuenta.autorizacion_otorgada_en = timezone.now()
        cuenta.autorizacion_version_politica = vigente.version
        if (
            cuenta.estado == EstadoCuenta.PENDIENTE_ACTIVACION
            and not cuenta.debe_cambiar_credencial
        ):
            cuenta.estado = EstadoCuenta.ACTIVA
        cuenta.save(
            update_fields=["autorizacion_otorgada_en", "autorizacion_version_politica", "estado"]
        )
        _auditar(
            AccionAuditoria.AUTORIZACION_ACEPTADA,
            cuenta,
            campos=["autorizacion_otorgada_en", "autorizacion_version_politica"],
        )
    return cuenta


# ---------------------------------------------------------------------------
# MFA propio (FEAT-030)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ActivacionMfa:
    secreto: str
    uri: str


def _reemplazar_codigos(cuenta: CuentaStaff) -> list[str]:
    CuentaCodigoRecuperacion.objects.filter(cuenta=cuenta).delete()
    codigos = mfa.nuevos_codigos_recuperacion()
    CuentaCodigoRecuperacion.objects.bulk_create(
        CuentaCodigoRecuperacion(
            cuenta=cuenta, hash_codigo=mfa.hash_codigo_recuperacion(cuenta.pk, c)
        )
        for c in codigos
    )
    return codigos


def iniciar_activacion_mfa(cuenta_id: int, contrasena: str, ip: str | None) -> ActivacionMfa:
    """Inicio de la activación TOTP con reautenticación (CHG-API-002, DEC-AUTO-215/218).

    Una sesión robada no puede vincular un segundo factor del atacante. La contraseña se
    comprueba como en el login: un fallo suma al contador de RULE-017 (5 → bloqueo progresivo) y
    se audita como LOGIN_FALLIDO; la sesión no se cierra ni se rota. Solo con la contraseña
    correcta se genera el secreto provisional, que sustituye a cualquier otro previo.
    """
    ahora = timezone.now()
    bloqueo: datetime | None = None
    secreto: str | None = None
    with transaction.atomic():
        cuenta = CuentaStaff.objects.select_for_update().get(pk=cuenta_id)
        if cuenta.mfa_activo:
            raise TransicionInvalida("La verificación en dos pasos ya está activa.")
        _liberar_bloqueo_cumplido(cuenta, ahora)
        campos = ["estado", "intentos_fallidos", "bloqueos_consecutivos", "bloqueado_hasta"]
        if cuenta.bloqueado_hasta is not None:
            bloqueo = cuenta.bloqueado_hasta
            cuenta.save(update_fields=campos)
        elif cuenta.check_password(contrasena):
            secreto = mfa.nuevo_secreto()
            cuenta.secreto_mfa = mfa.cifrar_secreto(secreto)
            cuenta.save(update_fields=[*campos, "secreto_mfa"])
        else:
            bloqueo = _registrar_fallo(cuenta, ahora, ip)
    if secreto is not None:
        return ActivacionMfa(secreto=secreto, uri=mfa.uri_otpauth(secreto, cuenta.usuario or ""))
    if bloqueo is not None:
        raise AccesoBloqueado(bloqueo)
    raise CredencialesInvalidas()


def confirmar_activacion_mfa(cuenta_id: int, codigo: str) -> list[str]:
    with transaction.atomic():
        cuenta = CuentaStaff.objects.select_for_update().get(pk=cuenta_id)
        if cuenta.mfa_activo or not cuenta.secreto_mfa:
            raise TransicionInvalida(
                "Inicia primero la activación de la verificación en dos pasos."
            )
        if not _totp_valido(cuenta, codigo):
            raise _validacion("codigo", "El código no es válido.")
        cuenta.mfa_activo = True
        cuenta.save(update_fields=["mfa_activo"])
        codigos = _reemplazar_codigos(cuenta)
        _auditar(AccionAuditoria.MFA_ACTIVAR, cuenta, campos=["mfa_activo"])
    return codigos


def regenerar_codigos_recuperacion(cuenta_id: int, codigo: str) -> list[str]:
    with transaction.atomic():
        cuenta = CuentaStaff.objects.select_for_update().get(pk=cuenta_id)
        if not cuenta.mfa_activo:
            raise TransicionInvalida("La verificación en dos pasos no está activa.")
        if not _totp_valido(cuenta, codigo):
            raise _validacion("codigo", "El código no es válido.")
        codigos = _reemplazar_codigos(cuenta)
        _auditar(AccionAuditoria.MFA_ACTIVAR, cuenta, campos=["codigos_recuperacion"])
    return codigos


def desactivar_mfa(cuenta_id: int, contrasena: str, codigo: str) -> None:
    with transaction.atomic():
        cuenta = CuentaStaff.objects.select_for_update().get(pk=cuenta_id)
        if cuenta.es_administrador:
            raise ErrorApi(codigo="mfa_obligatorio")
        if not cuenta.mfa_activo:
            raise TransicionInvalida("La verificación en dos pasos no está activa.")
        if not cuenta.check_password(contrasena):
            raise _validacion("contrasena", "La contraseña no es correcta.")
        valido = (
            _consumir_codigo_recuperacion(cuenta, codigo)
            if "-" in codigo
            else _totp_valido(cuenta, codigo)
        )
        if not valido:
            raise _validacion("codigo", "El código no es válido.")
        cuenta.mfa_activo = False
        cuenta.secreto_mfa = None
        cuenta.save(update_fields=["mfa_activo", "secreto_mfa"])
        CuentaCodigoRecuperacion.objects.filter(cuenta=cuenta).delete()
        _auditar(AccionAuditoria.MFA_DESACTIVAR, cuenta, campos=["mfa_activo"])


# ---------------------------------------------------------------------------
# Gestión de cuentas por el Administrador (FEAT-045, FLOW-015, RULE-015)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CuentaConTemporal:
    cuenta: CuentaStaff
    contrasena_temporal: str


def _bloquear_reglas_admin() -> None:
    """Serializa las operaciones que afectan a la regla del último Administrador."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [_LOCK_CUENTAS_ADMIN])


def _objetivo(actor: CuentaStaff, cuenta_id: int, *, sobre_si_mismo: bool = False) -> CuentaStaff:
    _bloquear_reglas_admin()
    cuenta = CuentaStaff.objects.select_for_update().filter(pk=cuenta_id).first()
    if cuenta is None:
        raise ErrorApi(codigo="no_encontrado")
    if not sobre_si_mismo and cuenta.pk == actor.pk:
        raise ErrorApi(codigo="operacion_sobre_si_mismo")
    return cuenta


def _exigir_otro_admin_activo(cuenta: CuentaStaff) -> None:
    if cuenta.es_administrador and not selectors.hay_otro_administrador_activo(cuenta.pk):
        raise ErrorApi(codigo="ultimo_administrador")


def _anotar_libro(cuenta_id: int, evento: str) -> None:
    """Libro de anonimizaciones (ADR-DB-004 §4): solo ids, fuera de las copias de la BD."""
    ruta = Path(settings.LIBRO_ANONIMIZACIONES_PATH)
    linea = f"{cuenta_id};{evento};{timezone.now().strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open("a", encoding="utf-8") as libro:
            libro.write(linea)
    except OSError as exc:
        logger.error(
            "libro_anonimizaciones_no_escrito", cuenta_id=cuenta_id, tipo=type(exc).__name__
        )


def crear_cuenta(
    actor: CuentaStaff, *, usuario: str, nombre_visible: str, rol: str
) -> CuentaConTemporal:
    """Alta en PENDIENTE_ACTIVACION con contraseña temporal (DEC-AUTO-036, AC-106)."""
    normalizado = normalizar_usuario(usuario)
    temporal = contrasena_temporal()
    if selectors.cuenta_por_usuario(normalizado) is not None:
        raise ErrorApi(codigo="duplicado", errors={"usuario": ["Ese usuario ya existe."]})
    cuenta = CuentaStaff(
        usuario=normalizado,
        nombre_visible=nombre_visible.strip(),
        rol=rol,
        estado=EstadoCuenta.PENDIENTE_ACTIVACION,
        debe_cambiar_credencial=True,
    )
    cuenta.set_password(temporal)
    try:
        with transaction.atomic():
            cuenta.save(force_insert=True)
    except IntegrityError as exc:  # carrera con otra alta del mismo usuario
        raise ErrorApi(codigo="duplicado", errors={"usuario": ["Ese usuario ya existe."]}) from exc
    _auditar(
        AccionAuditoria.CUENTA_CREAR,
        actor,
        objetivo=cuenta,
        campos=["usuario", "nombre_visible", "rol"],
    )
    return CuentaConTemporal(cuenta=cuenta, contrasena_temporal=temporal)


def actualizar_cuenta(
    actor: CuentaStaff, cuenta_id: int, *, nombre_visible: str | None, rol: str | None
) -> CuentaStaff:
    with transaction.atomic():
        cuenta = _objetivo(actor, cuenta_id, sobre_si_mismo=True)
        if cuenta.estado == EstadoCuenta.ANONIMIZADA:
            raise TransicionInvalida("Una cuenta anonimizada no se modifica.")
        cambios: list[str] = []
        if nombre_visible is not None and nombre_visible.strip() != cuenta.nombre_visible:
            cuenta.nombre_visible = nombre_visible.strip()
            cambios.append("nombre_visible")
        if rol is not None and rol != cuenta.rol:
            if cuenta.pk == actor.pk:
                raise ErrorApi(codigo="operacion_sobre_si_mismo")
            if rol != RolCuenta.ADMINISTRADOR:
                _exigir_otro_admin_activo(cuenta)
            cuenta.rol = rol
            cambios.append("rol")
        if cambios:
            cuenta.save(update_fields=cambios)
            if "rol" in cambios:
                invalidar_sesiones(cuenta.pk)
            _auditar(AccionAuditoria.CUENTA_ROL, actor, objetivo=cuenta, campos=cambios)
    return cuenta


def _emitir_temporal(cuenta: CuentaStaff, *, borrar_mfa: bool) -> tuple[str, list[str]]:
    temporal = contrasena_temporal()
    cuenta.set_password(temporal)
    cuenta.debe_cambiar_credencial = True
    cuenta.estado = EstadoCuenta.PENDIENTE_ACTIVACION
    cuenta.intentos_fallidos = 0
    cuenta.bloqueos_consecutivos = 0
    cuenta.bloqueado_hasta = None
    campos = [
        "password",
        "debe_cambiar_credencial",
        "estado",
        "intentos_fallidos",
        "bloqueos_consecutivos",
        "bloqueado_hasta",
    ]
    if borrar_mfa:
        cuenta.mfa_activo = False
        cuenta.secreto_mfa = None
        campos += ["mfa_activo", "secreto_mfa"]
    return temporal, campos


def restablecer_contrasena(
    actor: CuentaStaff, cuenta_id: int, *, borrar_mfa: bool = False
) -> CuentaConTemporal:
    """Nueva contraseña temporal (y sin MFA si borrar_mfa); invalida sesiones; PENDIENTE."""
    with transaction.atomic():
        cuenta = _objetivo(actor, cuenta_id)
        if cuenta.estado in (EstadoCuenta.DESACTIVADA, EstadoCuenta.ANONIMIZADA):
            raise TransicionInvalida("Reactiva la cuenta antes de restablecerla.")
        if cuenta.estado == EstadoCuenta.ACTIVA:
            _exigir_otro_admin_activo(cuenta)
        temporal, campos = _emitir_temporal(cuenta, borrar_mfa=borrar_mfa)
        cuenta.save(update_fields=campos)
        if borrar_mfa:
            CuentaCodigoRecuperacion.objects.filter(cuenta=cuenta).delete()
        invalidar_sesiones(cuenta.pk)
        _auditar(
            AccionAuditoria.CUENTA_RESTABLECER,
            actor,
            objetivo=cuenta,
            campos=["password", "mfa_activo"] if borrar_mfa else ["password"],
        )
    return CuentaConTemporal(cuenta=cuenta, contrasena_temporal=temporal)


def desactivar_cuenta(actor: CuentaStaff, cuenta_id: int) -> CuentaStaff:
    """Invalida sesiones y credenciales de inmediato (THREAT-025, AC-107)."""
    with transaction.atomic():
        cuenta = _objetivo(actor, cuenta_id)
        if cuenta.estado in (EstadoCuenta.DESACTIVADA, EstadoCuenta.ANONIMIZADA):
            raise TransicionInvalida("La cuenta ya está desactivada.")
        _exigir_otro_admin_activo(cuenta)
        cuenta.estado = EstadoCuenta.DESACTIVADA
        cuenta.desactivado_en = timezone.now()
        cuenta.set_unusable_password()
        cuenta.save(update_fields=["estado", "desactivado_en", "password"])
        invalidar_sesiones(cuenta.pk)
        _auditar(AccionAuditoria.CUENTA_DESACTIVAR, actor, objetivo=cuenta, campos=["estado"])
        transaction.on_commit(lambda: _anotar_libro(cuenta.pk, "DESACTIVADA"))
    return cuenta


def reactivar_cuenta(actor: CuentaStaff, cuenta_id: int) -> CuentaConTemporal:
    with transaction.atomic():
        cuenta = _objetivo(actor, cuenta_id)
        if cuenta.estado != EstadoCuenta.DESACTIVADA:
            raise TransicionInvalida("Solo se reactiva una cuenta desactivada.")
        temporal, campos = _emitir_temporal(cuenta, borrar_mfa=False)
        cuenta.desactivado_en = None
        cuenta.save(update_fields=[*campos, "desactivado_en"])
        _auditar(AccionAuditoria.CUENTA_REACTIVAR, actor, objetivo=cuenta, campos=["estado"])
    return CuentaConTemporal(cuenta=cuenta, contrasena_temporal=temporal)


def anonimizar_cuenta(actor: CuentaStaff, cuenta_id: int) -> CuentaStaff:
    """Anonimizar ahora (solo DESACTIVADA; ADR-DB-004 §2, AC-107, DEC-AUTO-096/127)."""
    with transaction.atomic():
        cuenta = _objetivo(actor, cuenta_id)
        if cuenta.estado != EstadoCuenta.DESACTIVADA:
            raise TransicionInvalida("Solo se anonimiza una cuenta desactivada.")
        cuenta.usuario = None
        cuenta.nombre_visible = None
        cuenta.secreto_mfa = None
        cuenta.mfa_activo = False
        cuenta.last_login = None
        cuenta.set_unusable_password()
        cuenta.estado = EstadoCuenta.ANONIMIZADA
        cuenta.anonimizado_en = timezone.now()
        cuenta.save(
            update_fields=[
                "usuario",
                "nombre_visible",
                "secreto_mfa",
                "mfa_activo",
                "last_login",
                "password",
                "estado",
                "anonimizado_en",
            ]
        )
        CuentaCodigoRecuperacion.objects.filter(cuenta=cuenta).delete()
        invalidar_sesiones(cuenta.pk)
        idempotencia.borrar_claves_de_cuenta(cuenta.pk)
        seudonimizar_eventos_de_cuenta(cuenta.pk)
        _auditar(
            AccionAuditoria.CUENTA_ANONIMIZAR,
            actor,
            objetivo=cuenta,
            campos=["usuario", "nombre_visible", "password", "secreto_mfa"],
        )
        transaction.on_commit(lambda: _anotar_libro(cuenta.pk, "ANONIMIZADA"))
    return cuenta
