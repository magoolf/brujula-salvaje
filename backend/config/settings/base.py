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

# Autenticación/sesiones del panel llegan en TKT-004 (sesion_panel, AUTH_USER_MODEL en TKT-003):
# aquí no se instala django.contrib.auth para no fijar un modelo de usuario antes de tiempo.
INSTALLED_APPS = [
    "rest_framework",
    "drf_spectacular",
    "apps.core",
]

MIDDLEWARE = [
    # Primero: fija trace_id (traceparent W3C) antes de cualquier otro componente.
    "apps.core.middleware.TrazaMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.CabecerasSeguridadMiddleware",
    "apps.core.middleware.RegistroPeticionMiddleware",
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
# La tabla UNLOGGED app.cache_limites la crea la migración ops.0001 (TKT-003).
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_limites",
        "TIMEOUT": 3600,  # TTL <= 1 h
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
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = False

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
    # Autenticación del panel: TKT-004 (sesión Django, ADR-API-001).
    "DEFAULT_AUTHENTICATION_CLASSES": [],
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
