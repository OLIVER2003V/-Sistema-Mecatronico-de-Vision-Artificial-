"""
ASGI para SORT-MATIC: HTTP normal (DRF) + WebSocket (Channels) en la misma app.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sortmatic.settings")

# get_asgi_application() debe llamarse antes de importar nada que toque
# modelos de Django (incluido linea.routing).
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

import linea.routing  # noqa: E402
from cuentas.middleware import AutenticacionJWTWebSocket  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AutenticacionJWTWebSocket(URLRouter(linea.routing.websocket_urlpatterns))
        ),
    }
)
