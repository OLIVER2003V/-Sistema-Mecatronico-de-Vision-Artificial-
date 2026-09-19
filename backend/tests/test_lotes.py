# -*- coding: utf-8 -*-
"""Gestion de lotes: rotacion automatica, cambio de capacidad y cierre manual."""
from django.db import IntegrityError, transaction
from django.test import override_settings

from linea.models import ConfiguracionLinea, Inspeccion, LoteProduccion

from .ayudas import CLAVE_VISION, CasoBase


@override_settings(VISION_API_KEY=CLAVE_VISION)
class RotacionAutomaticaTests(CasoBase):
    def setUp(self):
        super().setUp()
        config = ConfiguracionLinea.actual()
        config.botellas_por_lote = 3
        config.save()
        self.como_dispositivo()

    def _botella(self, resultado="ACEPTADA", **extra):
        datos = {"resultado": resultado}
        datos.update(extra)
        return self.client.post("/api/telemetria/", datos, format="json")

    def test_la_primera_botella_abre_el_primer_lote(self):
        r = self._botella()
        self.assertEqual(r.status_code, 201)
        lote = LoteProduccion.objects.get()
        self.assertEqual(lote.correlativo, "LOTE-EMBOL-0001")
        self.assertEqual(lote.estado, LoteProduccion.ACTIVO)

    def test_al_llenarse_se_cierra_y_abre_el_siguiente(self):
        for _ in range(3):
            self._botella()

        self.assertEqual(LoteProduccion.objects.count(), 2)
        primero = LoteProduccion.objects.get(correlativo="LOTE-EMBOL-0001")
        segundo = LoteProduccion.objects.get(correlativo="LOTE-EMBOL-0002")
        self.assertEqual(primero.estado, LoteProduccion.FINALIZADO)
        self.assertIsNotNone(primero.fecha_fin)
        self.assertEqual(segundo.estado, LoteProduccion.ACTIVO)
        self.assertEqual(primero.inspecciones.count(), 3)

    def test_el_correlativo_es_consecutivo(self):
        for _ in range(7):  # 2 lotes completos + 1 en curso
            self._botella()
        correlativos = list(
            LoteProduccion.objects.order_by("numero").values_list("correlativo", flat=True)
        )
        self.assertEqual(correlativos, ["LOTE-EMBOL-0001", "LOTE-EMBOL-0002", "LOTE-EMBOL-0003"])

    def test_la_base_impide_dos_lotes_activos(self):
        self._botella()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LoteProduccion.objects.create(
                    correlativo="LOTE-EMBOL-9999", numero=9999, capacidad_lote=5
                )

    def test_el_lote_nuevo_toma_la_capacidad_vigente(self):
        for _ in range(3):
            self._botella()
        config = ConfiguracionLinea.actual()
        config.botellas_por_lote = 10
        config.save()
        for _ in range(3):
            self._botella()
        self.assertEqual(LoteProduccion.objects.get(correlativo="LOTE-EMBOL-0002").capacidad_lote, 3)


@override_settings(VISION_API_KEY=CLAVE_VISION)
class GestionDeLotesTests(CasoBase):
    def setUp(self):
        super().setUp()
        config = ConfiguracionLinea.actual()
        config.botellas_por_lote = 10
        config.save()
        self.como_dispositivo()
        for _ in range(4):
            self.client.post("/api/telemetria/", {"resultado": "ACEPTADA"}, format="json")
        self.lote = LoteProduccion.objects.get(estado=LoteProduccion.ACTIVO)

    def test_el_supervisor_cambia_la_capacidad_del_lote_activo(self):
        self.entrar_como(self.supervisor)
        r = self.client.patch(
            "/api/lotes/%s/" % self.lote.pk, {"capacidad_lote": 25}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.capacidad_lote, 25)
        self.assertEqual(self.lote.estado, LoteProduccion.ACTIVO)

    def test_bajar_la_capacidad_por_debajo_de_lo_producido_cierra_el_lote(self):
        self.entrar_como(self.supervisor)
        r = self.client.patch("/api/lotes/%s/" % self.lote.pk, {"capacidad_lote": 4}, format="json")
        self.assertEqual(r.status_code, 200)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.estado, LoteProduccion.FINALIZADO)
        self.assertEqual(LoteProduccion.objects.filter(estado=LoteProduccion.ACTIVO).count(), 1)

    def test_capacidad_cero_se_rechaza(self):
        self.entrar_como(self.supervisor)
        r = self.client.patch("/api/lotes/%s/" % self.lote.pk, {"capacidad_lote": 0}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_el_operador_no_puede_cambiar_la_capacidad(self):
        self.entrar_como(self.operador)
        r = self.client.patch("/api/lotes/%s/" % self.lote.pk, {"capacidad_lote": 25}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_cierre_manual_abre_el_siguiente(self):
        self.entrar_como(self.supervisor)
        r = self.client.post("/api/lotes/%s/cerrar/" % self.lote.pk)
        self.assertEqual(r.status_code, 200)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.estado, LoteProduccion.FINALIZADO)
        self.assertEqual(r.data["lote_nuevo"]["correlativo"], "LOTE-EMBOL-0002")
        self.assertEqual(r.data["lote_nuevo"]["estado"], LoteProduccion.ACTIVO)

    def test_no_se_puede_cerrar_dos_veces(self):
        self.entrar_como(self.supervisor)
        self.client.post("/api/lotes/%s/cerrar/" % self.lote.pk)
        r = self.client.post("/api/lotes/%s/cerrar/" % self.lote.pk)
        self.assertEqual(r.status_code, 400)

    def test_el_operador_no_puede_cerrar_lotes(self):
        self.entrar_como(self.operador)
        r = self.client.post("/api/lotes/%s/cerrar/" % self.lote.pk)
        self.assertEqual(r.status_code, 403)

    def test_no_se_pueden_crear_lotes_a_mano(self):
        self.entrar_como(self.supervisor)
        r = self.client.post("/api/lotes/", {"capacidad_lote": 5}, format="json")
        self.assertEqual(r.status_code, 405)

    def test_el_endpoint_activo_devuelve_el_lote_en_curso(self):
        self.entrar_como(self.operador)
        r = self.client.get("/api/lotes/activo/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["correlativo"], self.lote.correlativo)
        self.assertEqual(r.data["total_inspecciones"], 4)

    def test_el_listado_se_puede_filtrar_por_estado(self):
        self.entrar_como(self.supervisor)
        self.client.post("/api/lotes/%s/cerrar/" % self.lote.pk)
        r = self.client.get("/api/lotes/?estado=FINALIZADO")
        self.assertEqual([f["correlativo"] for f in r.data["results"]], ["LOTE-EMBOL-0001"])

    def test_las_inspecciones_quedan_atadas_a_su_lote(self):
        self.assertEqual(Inspeccion.objects.filter(lote=self.lote).count(), 4)
