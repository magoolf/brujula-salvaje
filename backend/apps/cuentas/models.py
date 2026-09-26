"""Cuentas del staff, códigos de recuperación MFA y sesiones del panel.

Fuente: DB_HANDOFF v1.1 (tablas cuenta_staff, cuenta_codigo_recuperacion, sesion_panel),
BLUEPRINT §18.4 DATA-024 y STATE-004, ADR-DB-004 §2, ADR-DB-005 §2 (DEC-AUTO-089).

- `CuentaStaff` es AUTH_USER_MODEL: AbstractBaseUser SIN PermissionsMixin (el rol es un campo).
- La cuenta nunca se borra físicamente: las FK entrantes usan PROTECT (salvo sesiones, códigos
  e idempotencia, que desaparecen con ella por CASCADE según el DB_HANDOFF).
- El constraint trigger `trg_cuenta_admin_minimo` se crea en la migración 0002 (RunSQL).
"""

from __future__ import annotations

from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.sessions.base_session import AbstractBaseSession
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now

PATRON_USUARIO = r"^[a-z0-9._-]{1,40}$"


class RolCuenta(models.TextChoices):
    EDITOR = "EDITOR", "Editor"
    ADMINISTRADOR = "ADMINISTRADOR", "Administrador"


class EstadoCuenta(models.TextChoices):
    PENDIENTE_ACTIVACION = "PENDIENTE_ACTIVACION", "Pendiente de activación"
    ACTIVA = "ACTIVA", "Activa"
    BLOQUEADA_TEMPORAL = "BLOQUEADA_TEMPORAL", "Bloqueada temporalmente"
    DESACTIVADA = "DESACTIVADA", "Desactivada"
    ANONIMIZADA = "ANONIMIZADA", "Anonimizada"


# Estados en los que una cuenta puede operar el panel (is_active de Django).
ESTADOS_OPERATIVOS = frozenset({EstadoCuenta.ACTIVA})


class GestorCuentas(BaseUserManager["CuentaStaff"]):
    """Gestor mínimo: búsqueda por clave natural (usuario). El alta es un servicio de TKT-004."""

    def get_by_natural_key(self, username: str | None) -> CuentaStaff:
        return self.get(usuario=username)


class CuentaStaff(AbstractBaseUser):
    """DATA-024. `password` guarda el hash adaptativo de Django (nunca la credencial en claro)."""

    usuario = models.CharField(max_length=40, null=True, blank=True, unique=True)
    nombre_visible = models.CharField(max_length=100, null=True, blank=True)  # noqa: DJ001
    rol = models.CharField(max_length=13, choices=RolCuenta.choices)
    estado = models.CharField(
        max_length=20,
        choices=EstadoCuenta.choices,
        default=EstadoCuenta.PENDIENTE_ACTIVACION,
        db_default=EstadoCuenta.PENDIENTE_ACTIVACION,
    )
    debe_cambiar_credencial = models.BooleanField(default=True, db_default=True)
    mfa_activo = models.BooleanField(default=False, db_default=False)
    # Texto cifrado en la aplicación (Fernet/AES-GCM, clave MFA_FERNET_KEY). CONFIDENTIAL.
    secreto_mfa = models.BinaryField(null=True, blank=True)
    intentos_fallidos = models.SmallIntegerField(default=0, db_default=0)
    bloqueos_consecutivos = models.SmallIntegerField(default=0, db_default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    # last_login de Django con el nombre de columna del DB_HANDOFF.
    last_login = models.DateTimeField(null=True, blank=True, db_column="ultimo_acceso_en")
    autorizacion_otorgada_en = models.DateTimeField(null=True, blank=True)
    autorizacion_version_politica = models.CharField(max_length=20, null=True, blank=True)  # noqa: DJ001
    creado_en = models.DateTimeField(db_default=Now())
    desactivado_en = models.DateTimeField(null=True, blank=True)
    anonimizado_en = models.DateTimeField(null=True, blank=True)

    objects: ClassVar[GestorCuentas] = GestorCuentas()

    USERNAME_FIELD = "usuario"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["nombre_visible", "rol"]

    class Meta:
        db_table = "cuenta_staff"
        verbose_name = "cuenta del staff"
        verbose_name_plural = "cuentas del staff"
        constraints = [
            models.CheckConstraint(
                condition=Q(usuario__isnull=True) | Q(usuario__regex=PATRON_USUARIO),
                name="ck_cuenta_staff_usuario_patron",
            ),
            models.CheckConstraint(
                condition=Q(rol__in=RolCuenta.values), name="ck_cuenta_staff_rol"
            ),
            models.CheckConstraint(
                condition=Q(estado__in=EstadoCuenta.values), name="ck_cuenta_staff_estado"
            ),
            models.CheckConstraint(
                condition=Q(intentos_fallidos__gte=0), name="ck_cuenta_staff_intentos"
            ),
            models.CheckConstraint(
                condition=Q(bloqueos_consecutivos__gte=0), name="ck_cuenta_staff_bloqueos"
            ),
            models.CheckConstraint(
                condition=Q(estado=EstadoCuenta.ANONIMIZADA)
                | Q(usuario__isnull=False, nombre_visible__isnull=False),
                name="ck_cuenta_staff_identidad",
            ),
            models.CheckConstraint(
                condition=~Q(estado=EstadoCuenta.ANONIMIZADA)
                | Q(
                    usuario__isnull=True,
                    nombre_visible__isnull=True,
                    secreto_mfa__isnull=True,
                    last_login__isnull=True,
                    anonimizado_en__isnull=False,
                    mfa_activo=False,
                    password__startswith="!",  # noqa: S106 (prefijo de hash inutilizable)
                ),
                name="ck_cuenta_staff_anonimizada",
            ),
            models.CheckConstraint(
                condition=~Q(estado=EstadoCuenta.ACTIVA)
                | Q(
                    autorizacion_otorgada_en__isnull=False,
                    autorizacion_version_politica__isnull=False,
                ),
                name="ck_cuenta_staff_activa_autorizada",
            ),
            models.CheckConstraint(
                condition=~Q(estado__in=[EstadoCuenta.DESACTIVADA, EstadoCuenta.ANONIMIZADA])
                | Q(desactivado_en__isnull=False),
                name="ck_cuenta_staff_desactivada",
            ),
            models.CheckConstraint(
                condition=Q(mfa_activo=False) | Q(secreto_mfa__isnull=False),
                name="ck_cuenta_staff_mfa",
            ),
        ]

    def __str__(self) -> str:
        # Sin PII: el identificador interno basta para trazas y depuración.
        return f"Cuenta #{self.pk}"

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        """Derivado de `estado` (DB_HANDOFF): solo una cuenta ACTIVA opera el panel."""
        return self.estado in ESTADOS_OPERATIVOS

    @property
    def es_administrador(self) -> bool:
        return self.rol == RolCuenta.ADMINISTRADOR


class CuentaCodigoRecuperacion(models.Model):
    """Códigos de recuperación MFA: solo el hash; uso único (usado_en)."""

    cuenta = models.ForeignKey(
        CuentaStaff, on_delete=models.CASCADE, related_name="codigos_recuperacion"
    )
    hash_codigo = models.CharField(max_length=128)
    usado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "cuenta_codigo_recuperacion"
        constraints = [
            models.UniqueConstraint(
                fields=["cuenta", "hash_codigo"], name="uq_cuenta_codigo_recuperacion"
            ),
        ]

    def __str__(self) -> str:
        return f"Código de recuperación #{self.pk}"


class SesionPanel(AbstractBaseSession):
    """STATE-004: sesión del panel con la cuenta asociada (invalidación por cuenta)."""

    cuenta = models.ForeignKey(
        CuentaStaff,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sesiones",
    )
    # Expiración absoluta de 12 h desde la autenticación (THREAT-002).
    autenticado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "sesion_panel"
        verbose_name = "sesión del panel"
        verbose_name_plural = "sesiones del panel"

    def __str__(self) -> str:
        return f"Sesión que expira el {self.expire_date:%Y-%m-%d %H:%M}"

    @classmethod
    def get_session_store_class(cls) -> Any:
        from apps.cuentas.sesiones import SessionStore

        return SessionStore
