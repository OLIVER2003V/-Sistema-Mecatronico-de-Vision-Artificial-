# -*- coding: utf-8 -*-
"""Analiticos: KPIs del lote, Pareto de defectos y tendencia horaria."""
from django.test import override_settings

from linea.models import ConfiguracionLinea, Inspeccion

from .ayudas import CLAVE_VISION, CasoBase


@override_settings(VISION_API_KEY=CLAVE_VISION)
class KpiTests(CasoBase):
    def setUp(self):
        super().setUp()
        config = ConfiguracionLinea.actual()
        config.botellas_por_lote = 100
        config.save()
        self.como_dispositivo()
        for resultado in ("ACEPTADA", "ACEPTADA", "ACEPTADA", "DEFECTUOSA", "LLENADO_BAJO"):
            datos = {"resultado": resultado}
            if resultado == "DEFECTUOSA":
                datos["tipo_defecto"] = Inspeccion.SIN_ETIQUETA
            self.client.post("/api/telemetria/", datos, format="json")
        self.entrar_como(self.operador)

    def test_tasas_del_lote(self):
        r = self.client.get("/api/kpis/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["total_inspecciones"], 5)
        self.assertEqual(r.data["yield_rate"], 60.0)
        self.assertEqual(r.data["reject_rate"], 40.0)
        self.assertEqual(r.data["tasa_llenado_bajo"], 20.0)

    def test_contadores_que_mira_el_operador(self):
        r = self.client.get("/api/kpis/")
        self.assertEqual(
            r.data["conteos"],
            {
                "aceptadas": 3,
                "defectuosa": 1,
                "sin_etiqueta": 1,
                "sin_tapa": 0,
                "otro_defecto": 0,
                "llenado_bajo": 1,
                "rechazadas_total": 2,
            },
        )

    def test_defecto_predominante(self):
        r = self.client.get("/api/kpis/")
        self.assertEqual(r.data["defecto_predominante"]["tipo_defecto"], Inspeccion.SIN_ETIQUETA)
        self.assertEqual(r.data["defecto_predominante"]["porcentaje"], 100.0)

    def test_la_cadencia_teorica_sale_de_la_configuracion(self):
        config = ConfiguracionLinea.actual()
        config.velocidad_teorica = 77.0
        config.save()
        r = self.client.get("/api/kpis/")
        self.assertEqual(r.data["cadencia_teorica_bpm"], 77.0)

    def test_se_puede_consultar_por_correlativo(self):
        r = self.client.get("/api/kpis/?lote=LOTE-EMBOL-0001")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["lote"]["correlativo"], "LOTE-EMBOL-0001")

    def test_un_lote_inexistente_da_404(self):
        self.assertEqual(self.client.get("/api/kpis/?lote=LOTE-EMBOL-9999").status_code, 404)

    def test_un_lote_no_numerico_no_rompe_la_consulta(self):
        self.assertEqual(self.client.get("/api/kpis/?lote=abc").status_code, 404)

    def test_tendencia_horaria(self):
        r = self.client.get("/api/tendencia/")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.data), 1)
        self.assertEqual(sum(p["aceptadas"] + p["rechazadas"] for p in r.data), 5)


class SinDatosTests(CasoBase):
    def test_kpis_sin_ningun_lote_da_404(self):
        self.entrar_como(self.operador)
        self.assertEqual(self.client.get("/api/kpis/").status_code, 404)

    def test_tendencia_sin_datos_devuelve_lista_vacia(self):
        self.entrar_como(self.operador)
        r = self.client.get("/api/tendencia/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])

    def test_no_hay_lote_activo_todavia(self):
        self.entrar_como(self.operador)
        self.assertEqual(self.client.get("/api/lotes/activo/").status_code, 404)
