# -*- coding: utf-8 -*-
"""Geometria del nivel de llenado, filtro espacial y carga de configuracion."""
import json
import os
import tempfile
import unittest

from . import entorno

entorno.preparar()

from clasificador import (  # noqa: E402
    CONFIG_DEFECTO,
    _fusionar,
    _nivel_llenado,
    _superpone_botella,
    cargar_config,
    ruta_modelo,
)

# Botella de 200 px de alto: y=100 (tapa) a y=300 (base), x de 50 a 150.
BOTELLA = [50, 100, 150, 300]
CUELLO = 0.15  # el hombro queda en y = 100 + 0.15*200 = 130


class NivelDeLlenadoTests(unittest.TestCase):
    """0 = vacia, ~1 = llena hasta el hombro. Ver _nivel_llenado()."""

    def test_sin_botella_no_se_puede_medir(self):
        self.assertIsNone(_nivel_llenado(None, [0, 0, 10, 10], CUELLO))

    def test_botella_sin_agua_da_cero(self):
        self.assertEqual(_nivel_llenado(BOTELLA, None, CUELLO), 0.0)

    def test_agua_hasta_el_hombro_da_uno(self):
        agua = [55, 130, 145, 300]
        self.assertAlmostEqual(_nivel_llenado(BOTELLA, agua, CUELLO), 1.0, places=2)

    def test_agua_a_media_botella_da_la_mitad(self):
        # util = de y=130 (hombro) a y=300 (base) = 170 px; la mitad es y=215
        agua = [55, 215, 145, 300]
        self.assertAlmostEqual(_nivel_llenado(BOTELLA, agua, CUELLO), 0.5, places=2)

    def test_agua_que_sube_por_el_cuello_no_pasa_de_uno(self):
        agua = [55, 100, 145, 300]  # hasta la mismisima tapa
        self.assertLessEqual(_nivel_llenado(BOTELLA, agua, CUELLO), 1.0)

    def test_un_dedo_de_agua_da_poco(self):
        agua = [55, 285, 145, 300]
        self.assertLess(_nivel_llenado(BOTELLA, agua, CUELLO), 0.2)

    def test_una_caja_de_botella_degenerada_no_rompe(self):
        self.assertIsNone(_nivel_llenado([50, 100, 150, 100], [55, 130, 145, 140], CUELLO))

    def test_un_cuello_mas_largo_sube_la_medicion(self):
        """
        cuello_frac recorta el alto UTIL (la parte que se llena). Cuanto mas
        cuello se declara, menos alto util queda y la misma agua representa
        una fraccion mayor. Por eso al calibrar se ajusta este valor hasta que
        una botella llena marque ~1.0.
        """
        agua = [55, 215, 145, 300]
        corto = _nivel_llenado(BOTELLA, agua, 0.05)
        largo = _nivel_llenado(BOTELLA, agua, 0.40)
        self.assertGreater(largo, corto)


class FiltroEspacialTests(unittest.TestCase):
    """Lo que no cae sobre la botella es ruido del fondo y no debe contar."""

    def test_una_tapa_sobre_la_botella_cuenta(self):
        self.assertTrue(_superpone_botella([60, 95, 140, 135], BOTELLA))

    def test_una_tapa_en_el_fondo_no_cuenta(self):
        self.assertFalse(_superpone_botella([600, 600, 680, 660], BOTELLA))

    def test_sin_botella_de_referencia_nada_cuenta(self):
        self.assertFalse(_superpone_botella([60, 95, 140, 135], None))

    def test_una_caja_mitad_afuera_no_alcanza(self):
        # Solo un cuarto del area cae dentro de la botella agrandada.
        self.assertFalse(_superpone_botella([190, 340, 400, 560], BOTELLA))


class ConfiguracionTests(unittest.TestCase):
    def test_la_fusion_conserva_las_claves_no_tocadas(self):
        fusion = _fusionar(CONFIG_DEFECTO, {"modelo": {"nivel_min": 0.9}})
        self.assertEqual(fusion["modelo"]["nivel_min"], 0.9)
        self.assertEqual(fusion["modelo"]["ruta"], CONFIG_DEFECTO["modelo"]["ruta"])
        self.assertIn("camara", fusion)

    def test_la_fusion_no_modifica_el_original(self):
        _fusionar(CONFIG_DEFECTO, {"modelo": {"nivel_min": 0.9}})
        self.assertEqual(CONFIG_DEFECTO["modelo"]["nivel_min"], 0.60)

    def test_un_archivo_inexistente_deja_los_valores_por_defecto(self):
        cfg = cargar_config(os.path.join(tempfile.gettempdir(), "no-existe-12345.json"))
        self.assertEqual(cfg["modelo"]["nivel_min"], CONFIG_DEFECTO["modelo"]["nivel_min"])

    def test_un_json_roto_no_tumba_el_arranque(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write("{esto no es json")
            ruta = f.name
        try:
            cfg = cargar_config(ruta)
            self.assertEqual(cfg["modelo"]["nivel_min"], CONFIG_DEFECTO["modelo"]["nivel_min"])
        finally:
            os.unlink(ruta)

    def test_el_config_del_repo_trae_la_clave_del_dispositivo(self):
        cfg = cargar_config(os.path.join(entorno.RAIZ, "config.json"))
        self.assertIn("api_key", cfg["backend"])
        self.assertIn("url_configuracion", cfg["backend"])
        self.assertIn("url_estado", cfg["backend"])

    def test_el_config_del_repo_es_json_valido(self):
        with open(os.path.join(entorno.RAIZ, "config.json"), encoding="utf-8") as f:
            json.load(f)

    def test_una_ruta_relativa_se_resuelve_dentro_de_vision(self):
        ruta = ruta_modelo({"modelo": {"ruta": "best.pt"}})
        self.assertTrue(os.path.isabs(ruta))
        self.assertEqual(os.path.dirname(ruta), entorno.RAIZ)

    def test_una_ruta_absoluta_se_respeta(self):
        absoluta = os.path.join(tempfile.gettempdir(), "otro.pt")
        self.assertEqual(ruta_modelo({"modelo": {"ruta": absoluta}}), absoluta)


if __name__ == "__main__":
    unittest.main()
