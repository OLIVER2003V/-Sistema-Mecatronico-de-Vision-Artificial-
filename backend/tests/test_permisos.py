# -*- coding: utf-8 -*-
"""
Matriz de acceso: que puede tocar cada rol.

Es la prueba mas importante del modulo de seguridad. Si manana alguien agrega
un endpoint sin permission_class, aca se nota: DRF por defecto exige
IsAuthenticated (ver settings.REST_FRAMEWORK) y estas pruebas verifican que
ademas el rol correcto sea el unico que entra.
"""
from django.test import override_settings

from .ayudas import CLAVE_VISION, CasoBase

# (metodo, ruta, cuerpo) -> roles que SI deben poder
MATRIZ = [
    ("get", "/api/usuarios/", None, {"admin"}),
    ("get", "/api/auditoria/", None, {"admin"}),
    ("get", "/api/roles/", None, {"admin"}),
    ("get", "/api/mermas/", None, {"admin", "supervisor"}),
    ("get", "/api/tendencia/", None, {"admin", "supervisor", "operador"}),
    ("get", "/api/kpis/", None, {"admin", "supervisor", "operador"}),
    ("get", "/api/lotes/", None, {"admin", "supervisor", "operador"}),
    ("get", "/api/configuracion/", None, {"admin", "supervisor", "operador"}),
    ("get", "/api/estado-faja/", None, {"admin", "supervisor", "operador"}),
    ("post", "/api/comandos/", {"accion": "STOP"}, {"admin", "supervisor", "operador"}),
    ("patch", "/api/configuracion/", {"velocidad_teorica": 45}, {"admin", "supervisor"}),
]


@override_settings(VISION_API_KEY=CLAVE_VISION)
class MatrizDeAccesoTests(CasoBase):
    def test_cada_rol_solo_entra_donde_corresponde(self):
        usuarios = {
            "admin": self.admin,
            "supervisor": self.supervisor,
            "operador": self.operador,
        }
        for metodo, ruta, cuerpo, permitidos in MATRIZ:
            for etiqueta, usuario in usuarios.items():
                with self.subTest(ruta=ruta, metodo=metodo, rol=etiqueta):
                    self.entrar_como(usuario)
                    respuesta = getattr(self.client, metodo)(ruta, cuerpo, format="json")
                    if etiqueta in permitidos:
                        self.assertNotIn(
                            respuesta.status_code,
                            (401, 403),
                            "%s deberia poder %s %s" % (etiqueta, metodo, ruta),
                        )
                    else:
                        self.assertEqual(
                            respuesta.status_code,
                            403,
                            "%s NO deberia poder %s %s" % (etiqueta, metodo, ruta),
                        )

    def test_sin_token_todo_responde_401(self):
        self.salir()
        for metodo, ruta, cuerpo, _ in MATRIZ:
            with self.subTest(ruta=ruta, metodo=metodo):
                respuesta = getattr(self.client, metodo)(ruta, cuerpo, format="json")
                self.assertEqual(respuesta.status_code, 401)

    def test_token_invalido_no_sirve(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer esto-no-es-un-token")
        self.assertEqual(self.client.get("/api/kpis/").status_code, 401)

    def test_la_sonda_de_salud_es_publica(self):
        self.salir()
        r = self.client.get("/api/salud/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["estado"], "ok")


@override_settings(VISION_API_KEY=CLAVE_VISION)
class AccesoDelDispositivoTests(CasoBase):
    """Endpoints que consume vision/: van con X-API-Key, no con usuario."""

    RUTAS_DISPOSITIVO = [
        ("post", "/api/telemetria/", {"resultado": "ACEPTADA"}),
        ("get", "/api/comandos/siguiente/", None),
        ("post", "/api/estado-faja/reporte/", {"en_marcha": True}),
    ]

    def test_con_la_clave_correcta_entra(self):
        for metodo, ruta, cuerpo in self.RUTAS_DISPOSITIVO:
            with self.subTest(ruta=ruta):
                self.como_dispositivo()
                r = getattr(self.client, metodo)(ruta, cuerpo, format="json")
                self.assertNotIn(r.status_code, (401, 403))

    def test_sin_clave_no_entra(self):
        for metodo, ruta, cuerpo in self.RUTAS_DISPOSITIVO:
            with self.subTest(ruta=ruta):
                self.salir()
                r = getattr(self.client, metodo)(ruta, cuerpo, format="json")
                self.assertEqual(r.status_code, 403)

    def test_con_clave_equivocada_no_entra(self):
        self.client.credentials(HTTP_X_API_KEY="clave-que-no-es")
        r = self.client.post("/api/telemetria/", {"resultado": "ACEPTADA"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_un_operador_no_puede_inyectar_telemetria(self):
        """La telemetria viene del dispositivo; un humano no debe poder falsearla."""
        self.entrar_como(self.operador)
        r = self.client.post("/api/telemetria/", {"resultado": "ACEPTADA"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_el_dispositivo_no_puede_listar_usuarios(self):
        self.como_dispositivo()
        self.assertEqual(self.client.get("/api/usuarios/").status_code, 401)

    def test_configuracion_de_vision_la_lee_el_dispositivo_y_el_supervisor(self):
        self.como_dispositivo()
        self.assertEqual(self.client.get("/api/configuracion/vision/").status_code, 200)
        self.entrar_como(self.supervisor)
        self.assertEqual(self.client.get("/api/configuracion/vision/").status_code, 200)
        self.entrar_como(self.operador)
        self.assertEqual(self.client.get("/api/configuracion/vision/").status_code, 403)
