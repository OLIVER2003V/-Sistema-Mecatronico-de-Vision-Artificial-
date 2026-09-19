# -*- coding: utf-8 -*-
"""Control de marcha y paro: cola de comandos y panel SCADA."""
from django.test import override_settings

from cuentas.models import RegistroAuditoria
from linea.models import ComandoFaja, EstadoFaja

from .ayudas import CLAVE_VISION, CasoBase


@override_settings(VISION_API_KEY=CLAVE_VISION)
class ComandosTests(CasoBase):
    def test_el_operador_puede_arrancar_y_parar(self):
        self.entrar_como(self.operador)
        for accion in (ComandoFaja.START, ComandoFaja.STOP, ComandoFaja.RESET):
            with self.subTest(accion=accion):
                r = self.client.post("/api/comandos/", {"accion": accion}, format="json")
                self.assertEqual(r.status_code, 201)

    def test_queda_registrado_quien_lo_pidio(self):
        self.entrar_como(self.operador)
        self.client.post("/api/comandos/", {"accion": "STOP"}, format="json")
        self.assertEqual(ComandoFaja.objects.get().solicitado_por, self.operador)

    def test_el_comando_va_a_la_bitacora(self):
        self.entrar_como(self.operador)
        self.client.post("/api/comandos/", {"accion": "START"}, format="json")
        registro = RegistroAuditoria.objects.get(accion=RegistroAuditoria.COMANDO_FAJA)
        self.assertIn("START", registro.descripcion)

    def test_una_accion_inventada_se_rechaza(self):
        self.entrar_como(self.operador)
        r = self.client.post("/api/comandos/", {"accion": "AUTODESTRUIR"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_vision_consume_los_comandos_en_orden(self):
        self.entrar_como(self.operador)
        for accion in ("START", "STOP", "RESET"):
            self.client.post("/api/comandos/", {"accion": accion}, format="json")

        self.como_dispositivo()
        recibidos = [
            self.client.get("/api/comandos/siguiente/").data["accion"] for _ in range(3)
        ]
        self.assertEqual(recibidos, ["START", "STOP", "RESET"])

    def test_un_comando_no_se_entrega_dos_veces(self):
        self.entrar_como(self.operador)
        self.client.post("/api/comandos/", {"accion": "STOP"}, format="json")

        self.como_dispositivo()
        self.assertEqual(self.client.get("/api/comandos/siguiente/").data["accion"], "STOP")
        self.assertIsNone(self.client.get("/api/comandos/siguiente/").data["accion"])

    def test_sin_comandos_pendientes_devuelve_nulo(self):
        self.como_dispositivo()
        r = self.client.get("/api/comandos/siguiente/")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.data["accion"])


@override_settings(VISION_API_KEY=CLAVE_VISION)
class PanelScadaTests(CasoBase):
    def test_arranca_detenida(self):
        self.entrar_como(self.operador)
        r = self.client.get("/api/estado-faja/")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["en_marcha"])

    def test_vision_reporta_la_marcha_real(self):
        self.como_dispositivo()
        r = self.client.post(
            "/api/estado-faja/reporte/",
            {"en_marcha": True, "arduino_conectado": True, "detalle": "#START"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        estado = EstadoFaja.actual()
        self.assertTrue(estado.en_marcha)
        self.assertEqual(estado.detalle, "#START")

    def test_el_panel_muestra_el_arduino_desconectado(self):
        self.como_dispositivo()
        self.client.post(
            "/api/estado-faja/reporte/",
            {"en_marcha": False, "arduino_conectado": False, "detalle": "sin puerto serie"},
            format="json",
        )
        self.entrar_como(self.operador)
        r = self.client.get("/api/estado-faja/")
        self.assertFalse(r.data["arduino_conectado"])

    def test_pedir_un_comando_no_da_por_hecho_que_la_faja_arranco(self):
        """El estado real lo confirma vision/; el comando solo queda anotado."""
        self.entrar_como(self.operador)
        self.client.post("/api/comandos/", {"accion": "START"}, format="json")
        estado = EstadoFaja.actual()
        self.assertEqual(estado.ultimo_comando, "START")
        self.assertFalse(estado.en_marcha)

    def test_un_humano_no_puede_falsear_el_estado(self):
        self.entrar_como(self.supervisor)
        r = self.client.post(
            "/api/estado-faja/reporte/", {"en_marcha": True}, format="json"
        )
        self.assertEqual(r.status_code, 403)

    def test_el_estado_se_emite_por_websocket(self):
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        capa = get_channel_layer()
        async_to_sync(capa.group_add)("telemetria", "scada")
        self.como_dispositivo()
        self.client.post("/api/estado-faja/reporte/", {"en_marcha": True}, format="json")

        recibido = async_to_sync(capa.receive)("scada")
        self.assertEqual(recibido["evento"], "estado_faja")
        self.assertTrue(recibido["datos"]["en_marcha"])
