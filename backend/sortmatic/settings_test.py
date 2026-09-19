# -*- coding: utf-8 -*-
"""
Settings para correr pruebas rapidas SIN Postgres ni Redis (sqlite en memoria
+ channel layer en memoria). Uso:

    python manage.py test tests --settings=sortmatic.settings_test
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

# La misma clave que usa tests/ayudas.py para simular al modulo de vision.
VISION_API_KEY = "clave-de-prueba-del-dispositivo"

# El throttling cuenta por IP en una cache compartida entre pruebas: si queda
# activo, una prueba de login hace fallar a la siguiente. Hay una prueba propia
# que lo reactiva con override_settings (ver tests/test_autenticacion.py).
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {"login": None}}  # noqa: F405

# Hashing rapido: las pruebas crean muchos usuarios y PBKDF2 los hace lentos.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

ALMACENAMIENTO = "local"

# Muchas pruebas verifican 4xx a proposito: django.request los loguea como
# WARNING y taparian la salida del test runner.
LOGGING = {**LOGGING, "root": {**LOGGING["root"], "level": "ERROR"}}  # noqa: F405
