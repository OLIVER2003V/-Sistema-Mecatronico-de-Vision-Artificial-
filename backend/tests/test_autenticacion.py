# -*- coding: utf-8 -*-
"""Inicio de sesion, tokens, roles efectivos y bitacora de acceso."""
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from cuentas.models import PerfilUsuario, RegistroAuditoria, Rol, rol_de

from .ayudas import PASSWORD, CasoBase, crear_usuario

Usuario = get_user_model()


class LoginTests(APITestCase):
    def setUp(self):
        self.usuario = crear_usuario("supervisor1", Rol.SUPERVISOR)

    def test_login_devuelve_tokens_y_rol(self):
        r = self.client.post(
            "/api/auth/login/", {"username": "supervisor1", "password": PASSWORD}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)
        self.assertEqual(r.data["usuario"]["rol"], Rol.SUPERVISOR)

    def test_login_con_password_incorrecta_falla(self):
        r = self.client.post(
            "/api/auth/login/", {"username": "supervisor1", "password": "otra"}, format="json"
        )
        self.assertEqual(r.status_code, 401)

    def test_login_de_usuario_inactivo_falla(self):
        crear_usuario("dado_de_baja", Rol.OPERADOR, activo=False)
        r = self.client.post(
            "/api/auth/login/", {"username": "dado_de_baja", "password": PASSWORD}, format="json"
        )
        self.assertEqual(r.status_code, 401)

    def test_login_sin_rol_asignado_falla(self):
        sin_rol = Usuario.objects.create_user(username="huerfano", password=PASSWORD)
        PerfilUsuario.objects.filter(usuario=sin_rol).delete()
        r = self.client.post(
            "/api/auth/login/", {"username": "huerfano", "password": PASSWORD}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    def test_login_queda_en_la_bitacora(self):
        self.client.post(
            "/api/auth/login/", {"username": "supervisor1", "password": PASSWORD}, format="json"
        )
        registro = RegistroAuditoria.objects.filter(accion=RegistroAuditoria.INICIO_SESION).first()
        self.assertIsNotNone(registro)
        self.assertEqual(registro.usuario_nombre, "supervisor1")

    def test_login_limita_intentos_por_fuerza_bruta(self):
        # DRF fija THROTTLE_RATES como atributo de clase al importar, asi que
        # override_settings(REST_FRAMEWORK=...) no alcanza para cambiarlo.
        from unittest.mock import patch

        from django.core.cache import cache
        from rest_framework.throttling import SimpleRateThrottle

        cache.clear()
        try:
            with patch.object(SimpleRateThrottle, "THROTTLE_RATES", {"login": "3/min"}):
                codigos = [
                    self.client.post(
                        "/api/auth/login/",
                        {"username": "supervisor1", "password": "mala"},
                        format="json",
                    ).status_code
                    for _ in range(5)
                ]
        finally:
            cache.clear()
        self.assertEqual(codigos[-1], 429, "el 4to intento fallido deberia quedar bloqueado")


class RolEfectivoTests(APITestCase):
    def test_superusuario_es_administrador_aunque_su_perfil_diga_otra_cosa(self):
        jefe = Usuario.objects.create_superuser(username="root", password=PASSWORD)
        PerfilUsuario.objects.update_or_create(usuario=jefe, defaults={"rol": Rol.OPERADOR})
        self.assertEqual(rol_de(jefe), Rol.ADMINISTRADOR)

    def test_usuario_inactivo_no_tiene_rol(self):
        usuario = crear_usuario("inactivo", Rol.SUPERVISOR, activo=False)
        self.assertIsNone(rol_de(usuario))

    def test_la_signal_crea_el_perfil_de_todo_usuario_nuevo(self):
        nuevo = Usuario.objects.create_user(username="recien", password=PASSWORD)
        self.assertEqual(nuevo.perfil.rol, Rol.OPERADOR)


class SesionTests(CasoBase):
    def test_yo_devuelve_rol_y_permisos(self):
        self.entrar_como(self.operador)
        r = self.client.get("/api/auth/yo/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["rol"], Rol.OPERADOR)
        self.assertEqual(sorted(r.data["permisos"]), ["control_faja", "monitoreo"])

    def test_yo_sin_token_es_401(self):
        self.assertEqual(self.client.get("/api/auth/yo/").status_code, 401)

    def test_cambio_de_password_propia(self):
        self.entrar_como(self.operador)
        r = self.client.post(
            "/api/auth/password/",
            {"password_actual": PASSWORD, "password_nueva": "OtraClaveLarga456"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.check_password("OtraClaveLarga456"))

    def test_cambio_de_password_con_actual_incorrecta_falla(self):
        self.entrar_como(self.operador)
        r = self.client.post(
            "/api/auth/password/",
            {"password_actual": "equivocada", "password_nueva": "OtraClaveLarga456"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.check_password(PASSWORD))
