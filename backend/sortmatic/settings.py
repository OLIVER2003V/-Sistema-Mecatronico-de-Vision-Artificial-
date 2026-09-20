# -*- coding: utf-8 -*-
"""
Configuracion de Django para SORT-MATIC (EMBOL S.A.).

Todo lo que cambia entre entornos (dev / docker / produccion) se lee de
variables de entorno, con valores por defecto razonables para desarrollo
local. Ver docker-compose.yml y .env.example.

En produccion (DJANGO_DEBUG=false) el arranque FALLA si quedaron las claves
de desarrollo: es preferible no levantar a levantar inseguro.
"""
import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _bool_entorno(nombre, por_defecto="false"):
    return os.environ.get(nombre, por_defecto).strip().lower() in ("1", "true", "si", "yes", "on")


def _lista_entorno(nombre, por_defecto=""):
    crudo = os.environ.get(nombre, por_defecto)
    return [x.strip() for x in crudo.split(",") if x.strip()]


CLAVE_DEV = "clave-de-desarrollo-cambiar-en-produccion"
CLAVE_VISION_DEV = "clave-vision-de-desarrollo-cambiar-en-produccion"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", CLAVE_DEV)
DEBUG = _bool_entorno("DJANGO_DEBUG", "true")
ALLOWED_HOSTS = _lista_entorno("DJANGO_ALLOWED_HOSTS", "*")

# Clave con la que se identifica el modulo vision/ (no tiene usuario humano).
# Ver cuentas/permisos.py -> EsDispositivoVision.
VISION_API_KEY = os.environ.get("VISION_API_KEY", CLAVE_VISION_DEV)

if not DEBUG:
    if SECRET_KEY == CLAVE_DEV:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY sigue siendo la de desarrollo. Defina una clave "
            "larga y aleatoria antes de desplegar con DJANGO_DEBUG=false."
        )
    if VISION_API_KEY == CLAVE_VISION_DEV:
        raise ImproperlyConfigured(
            "VISION_API_KEY sigue siendo la de desarrollo. Defina una clave propia "
            "y pongala tambien en vision/config.json -> backend.api_key."
        )
    if "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS no puede ser '*' en produccion. Liste los dominios."
        )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "channels",
    "cuentas",
    "linea",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Sirve /static/ sin depender de Nginx: util en EC2/ECS detras de un ALB.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sortmatic.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sortmatic.wsgi.application"
ASGI_APPLICATION = "sortmatic.asgi.application"

# Por defecto asume Docker (Postgres + Redis como servicios propios). Para
# correr SIN Docker (sin instalar Postgres ni Redis), poner:
#   DJANGO_DB_ENGINE=sqlite
#   DJANGO_CHANNEL_LAYER=memory
# Ver backend/EJECUTAR_LOCAL.md.
if os.environ.get("DJANGO_DB_ENGINE", "postgres").lower() == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "sortmatic"),
            "USER": os.environ.get("POSTGRES_USER", "sortmatic"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "sortmatic"),
            "HOST": os.environ.get("POSTGRES_HOST", "db"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            # Reusa conexiones: en RDS abrir una por request se nota.
            "CONN_MAX_AGE": int(os.environ.get("POSTGRES_CONN_MAX_AGE", "60")),
        }
    }

if os.environ.get("DJANGO_CHANNEL_LAYER", "redis").lower() == "memory":
    # Sirve para UN solo proceso (daphne local). No usar asi en produccion
    # con varios workers: cada uno tendria su propio grupo "telemetria".
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [
                    {
                        "address": (
                            os.environ.get("REDIS_HOST", "redis"),
                            int(os.environ.get("REDIS_PORT", 6379)),
                        ),
                        "socket_timeout": 10,
                        "socket_connect_timeout": 10,
                    }
                ],
                "capacity": 1500,
                "expiry": 10,
            },
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "America/La_Paz")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Almacenamiento de las fotos de descarte. En AWS se pone DJANGO_ALMACENAMIENTO=s3
# y las fotos van al bucket en vez del disco del contenedor (que es efimero).
ALMACENAMIENTO = os.environ.get("DJANGO_ALMACENAMIENTO", "local").lower()

# El manifiesto lo genera collectstatic; en desarrollo todavia no existe y
# romperia el admin de Django, asi que solo se usa fuera de DEBUG.
ESTATICOS = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
    if not DEBUG
    else "django.contrib.staticfiles.storage.StaticFilesStorage"
)

if ALMACENAMIENTO == "s3":
    AWS_STORAGE_BUCKET_NAME = os.environ["AWS_STORAGE_BUCKET_NAME"]
    AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "us-east-1")
    # Sin credenciales explicitas, boto3 usa el rol de la instancia EC2 / la
    # task role de ECS, que es la forma recomendada (no hay llaves en el .env).
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = _bool_entorno("AWS_QUERYSTRING_AUTH", "true")
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": ESTATICOS},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": ESTATICOS},
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # Para el admin de Django y la API navegable en desarrollo.
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Cerrado por defecto: cada vista abre lo que necesita a proposito.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        # Frena la prueba de contrasenas por fuerza bruta.
        "login": os.environ.get("THROTTLE_LOGIN", "10/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_MINUTOS_ACCESO", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_DIAS_REFRESCO", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS: en Docker/produccion el frontend habla con el backend por el mismo
# Nginx, asi que no hace falta abrirlo. En dev, Vite corre en otro puerto.
CORS_ALLOW_ALL_ORIGINS = _bool_entorno("DJANGO_CORS_ALLOW_ALL", "true")
CORS_ALLOWED_ORIGINS = _lista_entorno("DJANGO_CORS_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = _lista_entorno("DJANGO_CSRF_ORIGINS")

# Fotos de descarte: no deberian pesar mucho (JPEG de una sola botella),
# pero se sube el limite por si acaso.
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# --- Endurecimiento para produccion (detras del ALB/Nginx con TLS) ---
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = _bool_entorno("DJANGO_FORZAR_HTTPS", "true")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SEGUNDOS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        # A stdout: es lo que esperan CloudWatch y `docker logs`.
        "consola": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["consola"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
}
