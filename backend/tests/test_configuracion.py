# -*- coding: utf-8 -*-
"""
Parametros del modelo de vision que gestiona el Supervisor de calidad, y su
propagacion en caliente hacia vision/ (endpoint /api/configuracion/vision/).
"""
from django.test import override_settings

from linea.models import ConfiguracionLinea

from .ayudas import CLAVE_VISION, CasoBase


class SingletonTests(CasoBase):
    def test_siempre_es_la_misma_fila(self):
        self.assertEqual(ConfiguracionLinea.actual().pk, ConfiguracionLinea.actual().pk)
        self.assertEqual(ConfiguracionLinea.objects.count(), 1)


class EdicionDeParametrosTests(CasoBase):
    def setUp(self):
        super().setUp()
        self.entrar_como(self.supervisor)

    def test_el_supervisor_cambia_el_nivel_minimo_de_llenado(self):
        r = self.client.patch(
            "/api/configuracion/", {"umbral_llenado_minimo": 72.5}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ConfiguracionLinea.actual().umbral_llenado_minimo, 72.5)

    def test_la_respuesta_trae_la_ayuda_de_cada_parametro(self):
        r = self.client.get("/api/configuracion/")
        self.assertIn("ayuda", r.data)
        self.assertIn("umbral_llenado_minimo", r.data["ayuda"])
        self.assertTrue(r.data["ayuda"]["confianza_etiqueta"])

    def test_la_version_sube_en_cada_guardado(self):
        antes = ConfiguracionLinea.actual().version
        self.client.patch("/api/configuracion/", {"velocidad_teorica": 55}, format="json")
        self.assertEqual(ConfiguracionLinea.actual().version, antes + 1)

    def test_queda_registrado_quien_lo_cambio(self):
        self.client.patch("/api/configuracion/", {"velocidad_teorica": 55}, format="json")
        self.assertEqual(ConfiguracionLinea.actual().actualizado_por, self.supervisor)

    def test_porcentaje_fuera_de_rango_se_rechaza(self):
        for valor in (-1, 101):
            with self.subTest(valor=valor):
                r = self.client.patch(
                    "/api/configuracion/", {"confianza_etiqueta": valor}, format="json"
                )
                self.assertEqual(r.status_code, 400)

    def test_lote_de_cero_botellas_se_rechaza(self):
        r = self.client.patch("/api/configuracion/", {"botellas_por_lote": 0}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_tamano_de_imagen_fuera_del_catalogo_se_rechaza(self):
        r = self.client.patch("/api/configuracion/", {"tamano_imagen": 123}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_piso_de_deteccion_no_puede_superar_los_umbrales_de_aprobacion(self):
        """Si el piso quedara por encima, el sistema marcaria TODO como defectuoso."""
        r = self.client.patch(
            "/api/configuracion/",
            {"confianza_deteccion": 90, "confianza_etiqueta": 80},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("confianza_deteccion", r.data)

    def test_el_operador_puede_leerla_pero_no_cambiarla(self):
        self.entrar_como(self.operador)
        self.assertEqual(self.client.get("/api/configuracion/").status_code, 200)
        r = self.client.patch("/api/configuracion/", {"velocidad_teorica": 99}, format="json")
        self.assertEqual(r.status_code, 403)


@override_settings(VISION_API_KEY=CLAVE_VISION)
class ConfiguracionParaVisionTests(CasoBase):
    def test_los_porcentajes_se_entregan_como_fracciones(self):
        config = ConfiguracionLinea.actual()
        config.umbral_llenado_minimo = 65.0
        config.confianza_etiqueta = 82.0
        config.fraccion_cuello = 12.0
        config.save()

        self.como_dispositivo()
        r = self.client.get("/api/configuracion/vision/")
        self.assertEqual(r.status_code, 200)
        self.assertAlmostEqual(r.data["modelo"]["nivel_min"], 0.65)
        self.assertAlmostEqual(r.data["modelo"]["conf_ok"], 0.82)
        self.assertAlmostEqual(r.data["modelo"]["cuello_frac"], 0.12)

    def test_las_claves_son_las_que_espera_clasificador_py(self):
        self.como_dispositivo()
        modelo = self.client.get("/api/configuracion/vision/").data["modelo"]
        self.assertEqual(
            set(modelo),
            {
                "conf_ok",
                "conf_ok_tapa",
                "conf_detectar",
                "conf_defecto",
                "nivel_min",
                "cuello_frac",
                "imgsz",
                "dispositivo",
            },
        )

    def test_un_cambio_del_supervisor_se_ve_en_el_endpoint_de_vision(self):
        self.entrar_como(self.supervisor)
        self.client.patch("/api/configuracion/", {"umbral_llenado_minimo": 40}, format="json")
        version_nueva = ConfiguracionLinea.actual().version

        self.como_dispositivo()
        r = self.client.get("/api/configuracion/vision/")
        self.assertEqual(r.data["version"], version_nueva)
        self.assertAlmostEqual(r.data["modelo"]["nivel_min"], 0.40)
