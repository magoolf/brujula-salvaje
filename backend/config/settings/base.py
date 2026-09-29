"""Settings comunes de Brújula Salvaje (Django 5.2, generado con django-admin startproject).

Todos los valores dependientes del entorno se leen de variables (DEVOPS_HANDOFF §7,
.env.example). Los módulos dev/test/prod solo ajustan lo que difiere.
Referencias: Skill_Backend §7 y §12, ADR-API-001, ADR-API-002, ADR-DB-001 §7, ADR-DB-005.
"""

from __future__ import annotations

from pathlib import Path

from config.settings import _env

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Núcleo
# ---------------------------------------------------------------------------
SECRET_KEY = _env.texto("DJANGO_SECRET_KEY")
DEBUG = _env.booleano("DJANGO_DEBUG", False)
ALLOWED_HOSTS = _env.lista("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend")

# Modelo de datos (TKT-003, DB_HANDOFF v1.1). No se instalan django.contrib.auth, contenttypes
# ni sessions: el DB_HANDOFF no contiene sus tablas (auth_*, django_content_type, django_session).
# La cuenta del staff es AbstractBaseUser sin PermissionsMixin (roles = campo `rol`) y las
# sesiones del panel van en `sesion_panel` (DEC-AUTO-089). La autenticación del panel es propia
# (apps.cuentas.autenticacion, TKT-004, OBS-QA003-06): no usa ModelBackend ni auth_*.
# django.contrib.postgres aporta ArrayField, SearchVectorField, GinIndex y OpClass.
INSTALLED_APPS = [
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.cuentas",
    "apps.catalogos",
    "apps.medios",
    "apps.contenido",
    "apps.inicio",
    "apps.auditoria",
    "apps.busqueda",
    "apps.ops",
]

# DATA-024: tabla cuenta_staff (DB_HANDOFF: "AUTH_USER_MODEL = modelo de esta tabla").
AUTH_USER_MODEL = "cuentas.CuentaStaff"

MIDDLEWARE = [
    # Primero: fija trace_id (traceparent W3C) antes de cualquier otro componente.
    "apps.core.middleware.TrazaMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.CabecerasSeguridadMiddleware",
    "apps.core.middleware.RegistroPeticionMiddleware",
    # Sesiones del panel sobre sesion_panel (SESSION_ENGINE). Perezoso: solo toca la BD y fija la
    # cookie si una vista del panel usa la sesión (las rutas públicas nunca la usan, RULE-029).
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
APPEND_SLASH = False  # las rutas del contrato no terminan en "/" (contracts/openapi.yaml)

TEMPLATES: list[dict[str, object]] = []

# ---------------------------------------------------------------------------
# Base de datos (ADR-DB-001 §7): psycopg 3, CONN_MAX_AGE + health checks, search_path del rol
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": _env.texto("DB_HOST", "db"),
        "PORT": str(_env.entero("DB_PORT", 5432)),
        "NAME": _env.texto("DB_NAME", "brujula"),
        "USER": _env.texto("DB_USER", "app_rw"),
        "PASSWORD": _env.texto("DB_PASSWORD"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            # Acota la conexión; /health/ready añade statement_timeout de 1 s (ADR-DB-005 §4).
            "connect_timeout": _env.entero("DB_CONNECT_TIMEOUT", 2),
            "application_name": "brujula-backend",
        },
        "TEST": {"NAME": "test_brujula"},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Caché: solo contadores de limitación de tasa (ADR-DB-005 §3, DB_HANDOFF cache_limites).
# La tabla UNLOGGED app.cache_limites la crea la migración ops.0001_inicial (RunSQL, TKT-003);
# su esquema es el de createcachetable, que así no tiene nada que crear.
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        # HALLAZGO-QA004-01: sin desalojo de entradas vigentes (apps/core/cache.py). Al superar
        # MAX_ENTRIES solo se purgan las caducadas: los estados de seguridad no se desalojan.
        "BACKEND": "apps.core.cache.CacheSinDesalojo",
        "LOCATION": "cache_limites",
        "TIMEOUT": 3600,  # TTL <= 1 h
        "OPTIONS": {"MAX_ENTRIES": 5000},
    }
}

# ---------------------------------------------------------------------------
# Internacionalización
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "es"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# ---------------------------------------------------------------------------
# Medios (el tratamiento completo es de TKT-006; aquí solo las rutas del entorno)
# ---------------------------------------------------------------------------
MEDIA_ROOT = _env.texto("MEDIA_ROOT", str(BASE_DIR / "media"))
MEDIA_PUBLIC_URL = _env.texto("MEDIA_PUBLIC_URL", "/media/publico/")
LIBRO_ANONIMIZACIONES_PATH = _env.texto(
    "LIBRO_ANONIMIZACIONES_PATH", str(BASE_DIR / "ops" / "libro_anonimizaciones.log")
)

# ---------------------------------------------------------------------------
# Secretos de aplicación
# ---------------------------------------------------------------------------
THROTTLE_HMAC_KEY = _env.texto("THROTTLE_HMAC_KEY")
MFA_FERNET_KEY = _env.texto("MFA_FERNET_KEY")

# ---------------------------------------------------------------------------
# Proxy de confianza (DEVOPS_HANDOFF §6.4, ADR-API-002 §9, DEC-AUTO-111)
# ---------------------------------------------------------------------------
NUM_PROXIES = _env.entero("DJANGO_NUM_PROXIES", 1)
# REQ-OPS002-01 (RSK-OPS-011): Django no confía en X-Forwarded-Proto de ningún emisor. El esquema
# lo fija gunicorn en wsgi.url_scheme solo para la IP del proxy (--forwarded-allow-ips).
SECURE_PROXY_SSL_HEADER = None
USE_X_FORWARDED_HOST = False
# RSK-OPS-012: redes de los proxies de confianza. X-Forwarded-For solo se usa para la IP del
# cliente (throttling, IP truncada de auditoría) si REMOTE_ADDR pertenece a una de ellas.
# Vacía = comportamiento de DRF con NUM_PROXIES (la red interna "app" solo expone el proxy).
PROXIES_CONFIANZA = _env.lista("DJANGO_TRUSTED_PROXIES", "")

# ---------------------------------------------------------------------------
# Sesión del panel (ADR-API-001 §5, DEC-AUTO-049/089): 30 min de inactividad, 12 h absolutas.
# ---------------------------------------------------------------------------
SESSION_ENGINE = "apps.cuentas.sesiones"
SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
PANEL_INACTIVIDAD_SEGUNDOS = 30 * 60
PANEL_SESION_MAXIMA_SEGUNDOS = 12 * 60 * 60

# Política de tratamiento vigente (FEAT-032, DEC-AUTO-038): se lee de la página institucional
# POLITICA_DATOS. Solo si aún no existe (antes de la carga semilla) se usan estos valores.
POLITICA_TRATAMIENTO_VERSION_RESPALDO = _env.texto("POLITICA_TRATAMIENTO_VERSION", "1.0")
POLITICA_TRATAMIENTO_VIGENTE_DESDE_RESPALDO = _env.texto(
    "POLITICA_TRATAMIENTO_VIGENTE_DESDE", "2026-09-25"
)

# Idempotency-Key (ADR-API-002 §5): espera máxima de un duplicado concurrente (lock_timeout).
IDEMPOTENCIA_LOCK_TIMEOUT_MS = _env.entero("IDEMPOTENCIA_LOCK_TIMEOUT_MS", 3000)

# ---------------------------------------------------------------------------
# Cookies, CSRF y cabeceras (ADR-API-001, DEC-AUTO-101; REQ-055)
# ---------------------------------------------------------------------------
SESSION_COOKIE_NAME = "sessionid"
SESSION_COOKIE_PATH = "/api/v1/panel/"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = _env.booleano("DJANGO_SESSION_COOKIE_SECURE", True)

CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_PATH = "/"
CSRF_COOKIE_HTTPONLY = False  # Angular la lee (withXsrfConfiguration); no es una credencial
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = _env.booleano("DJANGO_CSRF_COOKIE_SECURE", True)
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"
CSRF_TRUSTED_ORIGINS = _env.lista(
    "DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
)
CSRF_FAILURE_VIEW = "apps.core.api.views.csrf_fallido"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = _env.booleano("DJANGO_SECURE_SSL_REDIRECT", False)
SECURE_HSTS_SECONDS = _env.entero("DJANGO_SECURE_HSTS_SECONDS", 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = _env.booleano("DJANGO_SECURE_HSTS_PRELOAD", True)
# Las sondas internas /health/* no deben redirigirse a HTTPS (llegan por la red interna).
SECURE_REDIRECT_EXEMPT = [r"^health/(live|ready)$"]

# Cabeceras de API (contracts/openapi.yaml "Cabeceras globales"; THREAT-014/015)
API_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; frame-ancestors 'none'; object-src 'none'; "
    "base-uri 'self'; form-action 'self'"
)
API_PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
    "serial=(), bluetooth=(), browsing-topics=()"
)

# ---------------------------------------------------------------------------
# Errores RFC 9457 (Skill_Backend §12.1, ADR-API-002 §2, DEC-AUTO-103)
# ---------------------------------------------------------------------------
PROBLEM_TYPE_BASE_URL = _env.texto("PROBLEM_TYPE_BASE_URL", "https://brujulasalvaje.example")

# ---------------------------------------------------------------------------
# Django REST framework + drf-spectacular
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_CONTENT_NEGOTIATION_CLASS": "apps.core.negociacion.NegociacionSoloJson",
    "DEFAULT_PAGINATION_CLASS": "apps.core.paginacion.PaginacionNumerada",
    # Autenticación del panel (ADR-API-001): sesión sobre sesion_panel + CSRF en métodos no
    # seguros. Las vistas públicas y de salud la desactivan (authentication_classes = []).
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.cuentas.autenticacion.AutenticacionSesionPanel"],
    "UNAUTHENTICATED_USER": None,
    # Deny-by-default (Blueprint §12): cada vista declara sus permisos explícitamente.
    "DEFAULT_PERMISSION_CLASSES": ["apps.core.permisos.DenegarPorDefecto"],
    # Solo actúa en vistas con `throttle_scope`; clave = HMAC de la IP truncada o de la cuenta.
    "DEFAULT_THROTTLE_CLASSES": ["apps.core.throttling.LimitePorAmbito"],
    # Perfiles x-limite-tasa del contrato (DEC-AUTO-111). "panel-login" usa además el bloqueo
    # por usuario de TKT-004.
    "DEFAULT_THROTTLE_RATES": {
        "publico-lectura": "120/min",
        "publico-busqueda": "30/min",
        "publico-aleatorio": "30/min",
        "panel-login": "10/min",
        "panel-mfa": "10/min",
        "panel-lectura": "600/min",
        "panel-escritura": "120/min",
        "panel-subida": "20/min",
        "panel-vista-previa": "60/min",
    },
    "NUM_PROXIES": NUM_PROXIES,
    "EXCEPTION_HANDLER": "apps.core.exceptions.manejador_excepciones",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "COERCE_DECIMAL_TO_STRING": False,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Brújula Salvaje API",
    "VERSION": "1.0.0",
    "OAS_VERSION": "3.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # Convenciones estructurales del contrato (apps/core/esquema.py, DEC-AUTO-196).
    "DEFAULT_GENERATOR_CLASS": "apps.core.esquema.GeneradorContrato",
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "apps.core.esquema.alinear_con_contrato",
    ],
    # Nombres de los enums del contrato (components.schemas.Rol, EstadoCuenta, AccionAuditoria).
    "ENUM_NAME_OVERRIDES": {
        "Rol": "apps.cuentas.models.RolCuenta",
        "EstadoCuenta": "apps.cuentas.models.EstadoCuenta",
        "AccionAuditoria": "apps.auditoria.models.AccionAuditoria",
        "ResultadoAuditoria": "apps.auditoria.models.ResultadoAuditoria",
        # DEC-AUTO-919 (TKT-006, ciclo "unit tests + cobertura": check --deploy con
        # drf_spectacular.W001). Los 4 overrides de arriba apuntan a una clase TextChoices real
        # porque drf-spectacular calcula el hash de colisión a partir de sus pares (valor,
        # etiqueta) reales. Los 5 de abajo son conjuntos de choices AD-HOC (sin clase de modelo
        # propia, o cuya clase real tiene etiquetas en mayúscula/minúscula que no coinciden con
        # el valor): varios serializers de dominios distintos comparten el mismo NOMBRE de campo
        # ("tipo", "origen", "rol", "tipo_contenido", "destacados"/"destacados_bajo_minimo") para
        # conjuntos de choices distintos o para el mismo conjunto con nombres distintos, y
        # drf-spectacular no puede darles un nombre de componente estable sin ayuda. Se listan
        # como lista literal de valores (no una ruta de cadena): el hash de colisión se calcula
        # igual que en un choice set con etiqueta = valor (sin clase Choices detrás).
        "TipoEntidadContenido": [
            "DESTINO",
            "ITINERARIO",
            "GUIA",
            "TIPO",
            "COLECCION",
            "TERMINO",
            "PAGINA",
        ],
        "TipoRelacionable": ["DESTINO", "ITINERARIO", "GUIA", "TIPO", "COLECCION"],
        "TipoElementoColeccion": ["DESTINO", "ITINERARIO"],
        "RolEntidadOperacion": ["PRINCIPAL", "COPUBLICACION", "CASCADA"],
        "AreaDestacada": ["DESTINOS", "ITINERARIOS", "GUIAS"],
    },
}

# ---------------------------------------------------------------------------
# Logging JSON a stdout sin PII (Skill_Backend §12.3, REQ-057, THREAT-020)
# ---------------------------------------------------------------------------
LOG_LEVEL = _env.texto("DJANGO_LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "apps.core.observabilidad.formateador_json"}},
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        }
    },
    "root": {"handlers": ["stdout"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["stdout"], "level": LOG_LEVEL, "propagate": False},
        # 4xx ya quedan en la línea "peticion" (con trace_id); aquí solo errores de servidor.
        "django.request": {"handlers": ["stdout"], "level": "ERROR", "propagate": False},
        # El proxy emite el access log con IP truncada; el servidor de desarrollo no registra.
        "django.server": {"handlers": [], "level": "CRITICAL", "propagate": False},
        "brujula": {"handlers": ["stdout"], "level": LOG_LEVEL, "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# OpenTelemetry (desactivable con OTEL_SDK_DISABLED; se inicializa en config/wsgi.py)
# ---------------------------------------------------------------------------
OTEL_SDK_DISABLED = _env.booleano("OTEL_SDK_DISABLED", True)
OTEL_EXPORTER_OTLP_ENDPOINT = _env.texto("OTEL_EXPORTER_OTLP_ENDPOINT", "")
OTEL_SERVICE_NAME = _env.texto("OTEL_SERVICE_NAME", "brujula-backend")
