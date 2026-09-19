# -*- coding: utf-8 -*-
"""
El WebSocket de telemetria tambien tiene que estar cerrado: sin un token
valido en la query string, la linea de produccion no se muestra.

Se usa TransactionTestCase porque el consumer resuelve el usuario en otro
hilo (database_sync_to_async) y no veria los datos creados dentro de la
transaccion de un TestCase normal.
"""
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase

from cuentas.models import Rol
from linea.consumers import CIERRE_NO_AUTORIZADO
from sortmatic.asgi import application

from .ayudas import crear_usuario, token_de

RUTA = "/ws/telemetria/"


class AutenticacionWebSocketTests(TransactionTestCase):
    async def _conectar(self, consulta=""):
        comunicador = WebsocketCommunicator(application, RUTA + consulta)
        conectado, detalle = await comunicador.connect()
        return comunicador, conectado, detalle

    async def test_sin_token_se_rechaza(self):
        comunicador, conectado, codigo = await self._conectar()
        self.assertFalse(conectado)
        self.assertEqual(codigo, CIERRE_NO_AUTORIZADO)
        await comunicador.disconnect()

    async def test_con_token_invalido_se_rechaza(self):
        comunicador, conectado, codigo = await self._conectar("?token=basura")
        self.assertFalse(conectado)
        self.assertEqual(codigo, CIERRE_NO_AUTORIZADO)
        await comunicador.disconnect()

    async def test_con_token_valido_se_acepta(self):
        from channels.db import database_sync_to_async

        usuario = await database_sync_to_async(crear_usuario)("ws_operador", Rol.OPERADOR)
        token = await database_sync_to_async(token_de)(usuario)

        comunicador, conectado, _ = await self._conectar("?token=%s" % token)
        self.assertTrue(conectado)
        await comunicador.disconnect()

    async def test_un_usuario_desactivado_no_entra(self):
        from channels.db import database_sync_to_async

        usuario = await database_sync_to_async(crear_usuario)("ws_baja", Rol.SUPERVISOR)
        token = await database_sync_to_async(token_de)(usuario)
        await database_sync_to_async(
            lambda: type(usuario).objects.filter(pk=usuario.pk).update(is_active=False)
        )()

        comunicador, conectado, codigo = await self._conectar("?token=%s" % token)
        self.assertFalse(conectado)
        self.assertEqual(codigo, CIERRE_NO_AUTORIZADO)
        await comunicador.disconnect()

    async def test_el_cliente_conectado_recibe_los_eventos(self):
        from channels.db import database_sync_to_async
        from channels.layers import get_channel_layer

        usuario = await database_sync_to_async(crear_usuario)("ws_lector", Rol.OPERADOR)
        token = await database_sync_to_async(token_de)(usuario)
        comunicador, conectado, _ = await self._conectar("?token=%s" % token)
        self.assertTrue(conectado)

        await get_channel_layer().group_send(
            "telemetria",
            {"type": "evento.telemetria", "evento": "estado_faja", "datos": {"en_marcha": True}},
        )
        mensaje = await comunicador.receive_json_from()
        self.assertEqual(mensaje["evento"], "estado_faja")
        self.assertTrue(mensaje["datos"]["en_marcha"])
        await comunicador.disconnect()
