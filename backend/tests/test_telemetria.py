# -*- coding: utf-8 -*-
"""Entrada de telemetria desde vision/: validacion, fotos y eventos WebSocket."""
import shutil
import tempfile

from channels.layers import get_channel_layer
from django.test import override_settings

from linea.models import ConfiguracionLinea, FotoDescarte, Inspeccion

from .ayudas import CLAVE_VISION, CasoBase, imagen_de_prueba

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="sortmatic-pruebas-")


@override_settings(VISION_API_KEY=CLAVE_VISION, MEDIA_ROOT=MEDIA_TEMPORAL)
class TelemetriaTests(CasoBase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        config = ConfiguracionLinea.actual()
        config.botellas_por_lote = 100
        config.save()
        self.como_dispositivo()

    def _botella(self, **datos):
        return self.client.post("/api/telemetria/", datos, format="json")

    def test_defecto_guarda_tipo_y_estacion(self):
        r = self._botella(
            resultado="DEFECTUOSA",
            tipo_defecto=Inspeccion.SIN_TAPA,
            estacion_descarte=Inspeccion.ESTACION_1,
            confianza_ia=91.5,
        )
        self.assertEqual(r.status_code, 201)
        inspeccion = Inspeccion.objects.get(pk=r.data["id"])
        self.assertEqual(inspeccion.tipo_defecto, Inspeccion.SIN_TAPA)
        self.assertEqual(inspeccion.estacion_descarte, Inspeccion.ESTACION_1)
        self.assertEqual(inspeccion.confianza_ia, 91.5)

    def test_una_aceptada_no_arrastra_motivo_de_descarte(self):
        """Si viniera un tipo_defecto en una aceptada, ensuciaria el Pareto."""
        r = self._botella(
            resultado="ACEPTADA",
            tipo_defecto=Inspeccion.SIN_TAPA,
            estacion_descarte=Inspeccion.ESTACION_1,
        )
        inspeccion = Inspeccion.objects.get(pk=r.data["id"])
        self.assertIsNone(inspeccion.tipo_defecto)
        self.assertIsNone(inspeccion.estacion_descarte)

    def test_resultado_desconocido_se_rechaza(self):
        self.assertEqual(self._botella(resultado="EXPLOTO").status_code, 400)

    def test_resultado_es_obligatorio(self):
        self.assertEqual(self._botella(confianza_ia=50).status_code, 400)

    def test_porcentajes_fuera_de_rango_se_rechazan(self):
        self.assertEqual(self._botella(resultado="ACEPTADA", confianza_ia=140).status_code, 400)
        self.assertEqual(
            self._botella(resultado="ACEPTADA", nivel_llenado_detectado=-5).status_code, 400
        )

    def test_la_foto_se_guarda_con_nombre_aleatorio(self):
        """Un nombre previsible dejaria la galeria de mermas al alcance de cualquiera."""
        r = self.client.post(
            "/api/telemetria/",
            {"resultado": "DEFECTUOSA", "tipo_defecto": "OTRO", "foto": imagen_de_prueba()},
            format="multipart",
        )
        self.assertEqual(r.status_code, 201)
        foto = FotoDescarte.objects.get(inspeccion_id=r.data["id"])
        self.assertTrue(foto.imagen.name.startswith("descartes/"))
        self.assertNotIn("captura", foto.imagen.name)

    def test_una_aceptada_no_necesita_foto(self):
        r = self._botella(resultado="ACEPTADA")
        self.assertFalse(FotoDescarte.objects.filter(inspeccion_id=r.data["id"]).exists())

    def test_un_archivo_que_no_es_imagen_se_rechaza(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        falsa = SimpleUploadedFile("virus.jpg", b"esto no es una imagen", content_type="image/jpeg")
        r = self.client.post(
            "/api/telemetria/",
            {"resultado": "DEFECTUOSA", "foto": falsa},
            format="multipart",
        )
        self.assertEqual(r.status_code, 400)


@override_settings(VISION_API_KEY=CLAVE_VISION)
class EventosWebSocketTests(CasoBase):
    """La telemetria debe publicarse en el grupo que escucha el dashboard."""

    def setUp(self):
        super().setUp()
        self.como_dispositivo()

    def test_una_botella_emite_inspeccion_y_progreso(self):
        from asgiref.sync import async_to_sync

        capa = get_channel_layer()
        async_to_sync(capa.group_add)("telemetria", "prueba")
        self.client.post("/api/telemetria/", {"resultado": "ACEPTADA"}, format="json")

        recibido = async_to_sync(capa.receive)("prueba")
        self.assertEqual(recibido["evento"], "inspeccion")
        recibido = async_to_sync(capa.receive)("prueba")
        self.assertEqual(recibido["evento"], "progreso_lote")

    def test_al_rotar_el_lote_se_avisa(self):
        from asgiref.sync import async_to_sync

        config = ConfiguracionLinea.actual()
        config.botellas_por_lote = 1
        config.save()

        capa = get_channel_layer()
        async_to_sync(capa.group_add)("telemetria", "prueba2")
        self.client.post("/api/telemetria/", {"resultado": "ACEPTADA"}, format="json")

        eventos = [async_to_sync(capa.receive)("prueba2")["evento"] for _ in range(3)]
        self.assertEqual(eventos, ["inspeccion", "progreso_lote", "lote_rotado"])
