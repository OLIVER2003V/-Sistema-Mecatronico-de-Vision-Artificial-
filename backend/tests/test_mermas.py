# -*- coding: utf-8 -*-
"""Galeria y registro de mermas: filtros por fecha, hora y tipo de defecto."""
import shutil
import tempfile
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from linea.models import ConfiguracionLinea, FotoDescarte, Inspeccion, LoteProduccion

from .ayudas import CasoBase, imagen_de_prueba

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="sortmatic-mermas-")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class GaleriaDeMermasTests(CasoBase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.lote = LoteProduccion.crear_siguiente(ConfiguracionLinea.actual().botellas_por_lote)
        ahora = timezone.localtime()
        self.hoy = ahora.date()
        self.ayer = self.hoy - timedelta(days=1)

        self.sin_tapa = self._merma(Inspeccion.DEFECTUOSA, Inspeccion.SIN_TAPA, ahora)
        self.sin_etiqueta = self._merma(Inspeccion.DEFECTUOSA, Inspeccion.SIN_ETIQUETA, ahora)
        self.llenado = self._merma(Inspeccion.LLENADO_BAJO, None, ahora)
        self.vieja = self._merma(
            Inspeccion.DEFECTUOSA, Inspeccion.SIN_TAPA, ahora - timedelta(days=1)
        )
        self.aceptada = self._inspeccion(Inspeccion.ACEPTADA, None, ahora)
        self.entrar_como(self.supervisor)

    def _inspeccion(self, resultado, tipo, momento):
        inspeccion = Inspeccion.objects.create(
            lote=self.lote, resultado=resultado, tipo_defecto=tipo, confianza_ia=88.0
        )
        # fecha_hora es auto_now_add: para probar los filtros hay que fijarla.
        Inspeccion.objects.filter(pk=inspeccion.pk).update(fecha_hora=momento)
        inspeccion.refresh_from_db()
        return inspeccion

    def _merma(self, resultado, tipo, momento):
        inspeccion = self._inspeccion(resultado, tipo, momento)
        FotoDescarte.objects.create(inspeccion=inspeccion, imagen=imagen_de_prueba())
        return inspeccion

    def _ids(self, consulta=""):
        r = self.client.get("/api/mermas/%s" % consulta)
        self.assertEqual(r.status_code, 200)
        return {fila["id"] for fila in r.data["results"]}

    def test_lista_solo_descartes(self):
        self.assertEqual(
            self._ids(), {self.sin_tapa.id, self.sin_etiqueta.id, self.llenado.id, self.vieja.id}
        )

    def test_una_aceptada_nunca_aparece(self):
        self.assertNotIn(self.aceptada.id, self._ids())

    def test_cada_entrada_trae_la_url_de_su_foto(self):
        r = self.client.get("/api/mermas/")
        for fila in r.data["results"]:
            self.assertTrue(fila["imagen_url"], "toda merma listada debe traer su captura")

    def test_trae_los_nombres_legibles_para_la_hmi(self):
        r = self.client.get("/api/mermas/?tipo_defecto=SIN_TAPA")
        fila = r.data["results"][0]
        self.assertEqual(fila["tipo_defecto_nombre"], "Sin tapa")
        self.assertEqual(fila["resultado_nombre"], "Defectuosa")

    def test_filtro_por_tipo_de_defecto(self):
        self.assertEqual(self._ids("?tipo_defecto=SIN_ETIQUETA"), {self.sin_etiqueta.id})

    def test_filtro_por_resultado(self):
        self.assertEqual(self._ids("?resultado=LLENADO_BAJO"), {self.llenado.id})

    def test_filtro_por_fecha_desde(self):
        self.assertNotIn(self.vieja.id, self._ids("?desde=%s" % self.hoy))

    def test_filtro_por_fecha_hasta(self):
        self.assertEqual(self._ids("?hasta=%s" % self.ayer), {self.vieja.id})

    def test_filtro_por_rango_de_fechas(self):
        self.assertEqual(self._ids("?desde=%s&hasta=%s" % (self.ayer, self.ayer)), {self.vieja.id})

    def test_filtro_por_franja_horaria(self):
        hora = timezone.localtime(self.sin_tapa.fecha_hora).hour
        self.assertIn(self.sin_tapa.id, self._ids("?hora_desde=%d&hora_hasta=%d" % (hora, hora)))
        otra = (hora + 2) % 24
        if otra > hora:
            self.assertNotIn(self.sin_tapa.id, self._ids("?hora_desde=%d" % otra))

    def test_filtros_combinados(self):
        self.assertEqual(
            self._ids("?desde=%s&tipo_defecto=SIN_TAPA" % self.hoy), {self.sin_tapa.id}
        )

    def test_filtro_por_lote(self):
        self.assertEqual(len(self._ids("?lote=%s" % self.lote.pk)), 4)
        self.assertEqual(self._ids("?lote=999999"), set())

    def test_una_fecha_mal_escrita_se_ignora_en_vez_de_romper(self):
        r = self.client.get("/api/mermas/?desde=no-es-una-fecha")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 4)

    def test_descartes_sin_foto_solo_con_con_foto_false(self):
        sin_foto = self._inspeccion(Inspeccion.DEFECTUOSA, Inspeccion.OTRO, timezone.localtime())
        self.assertNotIn(sin_foto.id, self._ids())
        self.assertIn(sin_foto.id, self._ids("?con_foto=false"))

    def test_orden_de_la_mas_nueva_a_la_mas_vieja(self):
        r = self.client.get("/api/mermas/")
        fechas = [fila["fecha_hora"] for fila in r.data["results"]]
        self.assertEqual(fechas, sorted(fechas, reverse=True))

    def test_el_tamano_de_pagina_tiene_tope(self):
        r = self.client.get("/api/mermas/?page_size=99999")
        self.assertEqual(r.status_code, 200)
        self.assertLessEqual(len(r.data["results"]), 200)

    def test_el_operador_no_ve_la_galeria(self):
        self.entrar_como(self.operador)
        self.assertEqual(self.client.get("/api/mermas/").status_code, 403)
