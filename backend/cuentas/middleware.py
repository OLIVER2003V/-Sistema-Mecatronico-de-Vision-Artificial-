# -*- coding: utf-8 -*-
"""
Autenticacion del WebSocket de telemetria.

El navegador no puede poner cabeceras en `new WebSocket(...)`, asi que el
token de acceso viaja en la query string: ws://host/ws/telemetria/?token=XXX.
Es el mismo access token JWT que usa la API REST, y como es de vida corta el
riesgo de que quede en un log de proxy es acotado.

Si el token falta o no sirve, el scope queda con AnonymousUser y el consumer
cierra la conexion (ver linea/consumers.py).
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _usuario_y_rol(token_crudo):
    """
    Resuelve el usuario Y su rol aca, dentro del hilo sincrono: el consumer
    corre en async y tocar `usuario.perfil` alli lanzaria SynchronousOnlyOperation.
    """
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.tokens import AccessToken

    from .models import rol_de

    Usuario = get_user_model()
    try:
        token = AccessToken(token_crudo)
        usuario = Usuario.objects.select_related("perfil").get(pk=token["user_id"])
    except (TokenError, KeyError, Usuario.DoesNotExist):
        return AnonymousUser(), None
    if not usuario.is_active:
        return AnonymousUser(), None
    return usuario, rol_de(usuario)


class AutenticacionJWTWebSocket(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        consulta = parse_qs((scope.get("query_string") or b"").decode("utf-8", "ignore"))
        tokens = consulta.get("token") or []
        if tokens:
            scope["user"], scope["rol"] = await _usuario_y_rol(tokens[0])
        else:
            scope["user"], scope["rol"] = AnonymousUser(), None
        return await super().__call__(scope, receive, send)
