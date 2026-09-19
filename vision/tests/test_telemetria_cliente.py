# -*- coding: utf-8 -*-
"""
Puente hacia el backend: mapeo de veredictos, clave del dispositivo y
recarga en caliente de los umbrales que edita el Supervisor de calidad.
"""
import os
import unittest

from . import entorno

entorno.preparar()

from telemetria_cliente import (  # noqa: E402
    CLAVES_MODELO,
    ClienteConfiguracion,
    clave_api,
    payload_desde_resultado,
)


def resultado(etiqueta="aceptada", nivel=0.85, **conf):
    metricas = {"nivel_llenado": nivel, "conf_botella": 0.95}
    metricas.update(conf)
    return {"codigo": "A", "etiqueta": etiqueta, "detalle": "", "metricas": metricas}


class PayloadTests(unittest.TestCase):
    """Lo que viaja por serie (A/D/L) tiene que llegar bien al backend."""

    def test_aceptada(self):
        datos = payload_desde_resultado("A", resultado())
        self.assertEqual(datos["resultado"], "ACEPTADA")
        self.assertIsNone(datos["estacion_descarte"])
        self.assertEqual(datos["nivel_llenado_detectado"], 85.0)

    def test_defecto_fisico_sale_por_la_estacion_1(self):
        datos = payload_desde_resultado("D", resultado("rota", conf_rota=0.91))
        self.assertEqual(datos["resultado"], "DEFECTUOSA")
        self.assertEqual(datos["estacion_descarte"], "ESTACION_1")

    def test_llenado_bajo_sale_por_la_estacion_2(self):
        datos = payload_desde_resultado("L", resultado("nivel_bajo", nivel=0.3))
        self.assertEqual(datos["resultado"], "LLENADO_BAJO")
        self.assertEqual(datos["estacion_descarte"], "ESTACION_2")
        self.assertEqual(datos["nivel_llenado_detectado"], 30.0)

    def test_cada_etiqueta_del_clasificador_tiene_su_tipo_de_defecto(self):
        esperado = {
            "falta_etiqueta": "SIN_ETIQUETA",
            "falta_tapa": "SIN_TAPA",
            "sin_tapa": "SIN_TAPA",
            "rota": "OTRO",
        }
        for etiqueta, tipo in esperado.items():
            with self.subTest(etiqueta=etiqueta):
                datos = payload_desde_resultado("D", resultado(etiqueta))
                self.assertEqual(datos["tipo_defecto"], tipo)

    def test_una_etiqueta_desconocida_cae_en_otro(self):
        datos = payload_desde_resultado("D", resultado("abollada"))
        self.assertEqual(datos["tipo_defecto"], "OTRO")

    def test_sin_medicion_de_nivel_no_se_inventa_un_numero(self):
        datos = payload_desde_resultado("A", resultado(nivel=-1.0))
        self.assertIsNone(datos["nivel_llenado_detectado"])

    def test_los_porcentajes_se_recortan_a_0_100(self):
        """El backend rechaza fuera de rango: perderia la botella entera."""
        datos = payload_desde_resultado("A", resultado(nivel=1.4, conf_botella=1.3))
        self.assertLessEqual(datos["nivel_llenado_detectado"], 100.0)
        self.assertLessEqual(datos["confianza_ia"], 100.0)

    def test_en_un_defecto_se_reporta_la_confianza_mas_alta(self):
        datos = payload_desde_resultado(
            "D", resultado("rota", conf_rota=0.91, conf_etiqueta=0.40)
        )
        self.assertEqual(datos["confianza_ia"], 91.0)

    def test_un_codigo_raro_no_rompe_el_envio(self):
        self.assertEqual(payload_desde_resultado("?", resultado())["resultado"], "ACEPTADA")


class ClaveDelDispositivoTests(unittest.TestCase):
    def test_sale_de_la_configuracion(self):
        self.assertEqual(clave_api({"api_key": "desde-el-json"}), "desde-el-json")

    def test_la_variable_de_entorno_tiene_prioridad(self):
        os.environ["SORTMATIC_API_KEY"] = "desde-el-entorno"
        try:
            self.assertEqual(clave_api({"api_key": "desde-el-json"}), "desde-el-entorno")
        finally:
            del os.environ["SORTMATIC_API_KEY"]

    def test_sin_clave_devuelve_vacio(self):
        self.assertEqual(clave_api({}), "")
        self.assertEqual(clave_api(None), "")


class RecargaEnCalienteTests(unittest.TestCase):
    """
    El supervisor cambia el nivel minimo de llenado en la HMI y la inspeccion
    lo toma sin reiniciarse. Se prueba aplicar() directamente: el hilo de red
    no aporta nada a la logica.
    """

    def setUp(self):
        self.modelo = {
            "ruta": "best.pt",
            "conf_ok": 0.80,
            "nivel_min": 0.60,
            "imgsz": 640,
            "dispositivo": "cpu",
        }
        # activo=False: no arranca el hilo de red, aplicar() se llama a mano.
        self.cliente = ClienteConfiguracion({"activo": False}, self.modelo)

    def test_aplica_los_umbrales_nuevos(self):
        cambio = self.cliente.aplicar({"version": 2, "modelo": {"nivel_min": 0.45}})
        self.assertTrue(cambio)
        self.assertEqual(self.modelo["nivel_min"], 0.45)

    def test_la_misma_version_no_se_reaplica(self):
        self.cliente.aplicar({"version": 2, "modelo": {"nivel_min": 0.45}})
        self.assertFalse(self.cliente.aplicar({"version": 2, "modelo": {"nivel_min": 0.99}}))
        self.assertEqual(self.modelo["nivel_min"], 0.45)

    def test_una_version_nueva_vuelve_a_aplicar(self):
        self.cliente.aplicar({"version": 2, "modelo": {"nivel_min": 0.45}})
        self.assertTrue(self.cliente.aplicar({"version": 3, "modelo": {"nivel_min": 0.70}}))
        self.assertEqual(self.modelo["nivel_min"], 0.70)

    def test_el_dashboard_no_puede_cambiar_la_ruta_del_modelo(self):
        """best.pt es un detalle de esta PC, no algo que decida la HMI."""
        self.cliente.aplicar(
            {"version": 5, "modelo": {"ruta": "/etc/passwd", "nivel_min": 0.5}}
        )
        self.assertEqual(self.modelo["ruta"], "best.pt")

    def test_solo_se_aceptan_las_claves_conocidas(self):
        self.cliente.aplicar({"version": 5, "modelo": {"comando": "rm -rf /", "conf_ok": 0.9}})
        self.assertNotIn("comando", self.modelo)
        self.assertEqual(self.modelo["conf_ok"], 0.9)

    def test_una_respuesta_sin_version_no_toca_nada(self):
        self.assertFalse(self.cliente.aplicar({"modelo": {"nivel_min": 0.1}}))
        self.assertEqual(self.modelo["nivel_min"], 0.60)

    def test_una_respuesta_vacia_no_toca_nada(self):
        self.assertFalse(self.cliente.aplicar({"version": 9, "modelo": {}}))
        self.assertEqual(self.modelo["nivel_min"], 0.60)

    def test_las_claves_permitidas_son_las_del_clasificador(self):
        from clasificador import CONFIG_DEFECTO

        del_modelo = set(CONFIG_DEFECTO["modelo"]) - {"ruta"}
        self.assertEqual(set(CLAVES_MODELO), del_modelo)


if __name__ == "__main__":
    unittest.main()
