"""
WSGI de respaldo (manage.py runserver, comandos de administracion, etc).
El servicio real corre con Daphne sobre sortmatic.asgi:application.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sortmatic.settings")

application = get_wsgi_application()
