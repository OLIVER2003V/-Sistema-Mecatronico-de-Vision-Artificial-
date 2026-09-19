# -*- coding: utf-8 -*-
"""Lectura de las lineas informativas del firmware para el panel SCADA."""
import unittest

from . import entorno

entorno.preparar()

from inspector_botellas import marcha_desde_linea  # noqa: E402


class MarchaDesdeLineaTests(unittest.TestCase):
    """El panel SCADA muestra marcha/paro REAL, leido de lo que dice el Arduino."""

    def test_start_es_marcha(self):
        self.assertIs(marcha_desde_linea("#START"), True)

    def test_stop_es_paro(self):
        self.assertIs(marcha_desde_linea("#STOP"), False)

    def test_reset_no_cambia_la_marcha(self):
        """RESET pone los contadores en cero; la cinta sigue como estaba."""
        self.assertIsNone(marcha_desde_linea("#RESET"))

    def test_timeout_no_cambia_la_marcha(self):
        """Un TIMEOUT deja pasar la botella, pero no para la faja."""
        self.assertIsNone(marcha_desde_linea("#TIMEOUT"))

    def test_los_contadores_no_dicen_nada_del_estado(self):
        self.assertIsNone(marcha_desde_linea("#tot=12 ok=10 niv=1 df=1"))

    def test_los_avisos_de_arranque_no_dicen_nada_del_estado(self):
        self.assertIsNone(marcha_desde_linea("#LISTO faja botellas"))
        self.assertIsNone(marcha_desde_linea("#PC: S=start X=stop R=reset"))

    def test_una_linea_vacia_no_rompe(self):
        self.assertIsNone(marcha_desde_linea(""))

    def test_no_confunde_start_con_otra_palabra(self):
        self.assertIsNone(marcha_desde_linea("#ESTADO desconocido"))


if __name__ == "__main__":
    unittest.main()
