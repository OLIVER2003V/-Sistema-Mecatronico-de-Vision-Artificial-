# -*- coding: utf-8 -*-
"""
Consumer de WebSocket: solo push de eventos, no recibe comandos del cliente.

Exige un usuario autenticado con rol. El token JWT viaja en la query string y
lo resuelve cuentas/middleware.py, que ademas deja el rol en scope["rol"].
Sin esto la telemetria de la planta quedaria visible para cualquiera que
supiera la URL.
"""
from channels.generic.websocket import AsyncJsonWebsocketConsumer

GRUPO_TELEMETRIA = "telemetria"

CIERRE_NO_AUTORIZADO = 4401


class TelemetriaConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        if self.scope.get("rol") is None:
            await self.close(code=CIERRE_NO_AUTORIZADO)
            return
        await self.channel_layer.group_add(GRUPO_TELEMETRIA, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(GRUPO_TELEMETRIA, self.channel_name)

    # Nombre derivado de {"type": "evento.telemetria"} en views._emitir().
    async def evento_telemetria(self, event):
        await self.send_json({"evento": event["evento"], "datos": event["datos"]})
