# -*- coding: utf-8 -*-
"""CRUD de usuarios del Administrador de sistemas y sus candados de seguridad."""
from django.contrib.auth import get_user_model

from cuentas.models import RegistroAuditoria, Rol, rol_de

from .ayudas import CasoBase, crear_usuario

Usuario = get_user_model()


class CrudUsuariosTests(CasoBase):
    def setUp(self):
        super().setUp()
        self.entrar_como(self.admin)

    def _crear(self, **extra):
        datos = {
            "username": "nuevo_operador",
            "password": "ClaveDePrueba987",
            "rol": Rol.OPERADOR,
            "first_name": "Nora",
            "email": "nora@embol.local",
        }
        datos.update(extra)
        return self.client.post("/api/usuarios/", datos, format="json")

    def test_alta_de_usuario(self):
        r = self._crear()
        self.assertEqual(r.status_code, 201)
        usuario = Usuario.objects.get(username="nuevo_operador")
        self.assertEqual(rol_de(usuario), Rol.OPERADOR)
        self.assertTrue(usuario.check_password("ClaveDePrueba987"))

    def test_la_password_nunca_vuelve_en_la_respuesta(self):
        r = self._crear()
        self.assertNotIn("password", r.data)
        listado = self.client.get("/api/usuarios/")
        for fila in listado.data["results"]:
            self.assertNotIn("password", fila)

    def test_no_se_puede_repetir_el_nombre_de_usuario(self):
        self._crear()
        r = self._crear(email="otra@embol.local")
        self.assertEqual(r.status_code, 400)
        self.assertIn("username", r.data)

    def test_el_nombre_de_usuario_no_distingue_mayusculas(self):
        self._crear()
        r = self._crear(username="NUEVO_OPERADOR")
        self.assertEqual(r.status_code, 400)

    def test_password_debil_se_rechaza(self):
        r = self._crear(password="1234")
        self.assertEqual(r.status_code, 400)
        self.assertIn("password", r.data)

    def test_alta_sin_password_se_rechaza(self):
        datos = {"username": "sin_clave", "rol": Rol.OPERADOR}
        r = self.client.post("/api/usuarios/", datos, format="json")
        self.assertEqual(r.status_code, 400)

    def test_edicion_sin_password_conserva_la_anterior(self):
        self._crear()
        usuario = Usuario.objects.get(username="nuevo_operador")
        r = self.client.patch(
            "/api/usuarios/%s/" % usuario.pk, {"first_name": "Norah"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        usuario.refresh_from_db()
        self.assertEqual(usuario.first_name, "Norah")
        self.assertTrue(usuario.check_password("ClaveDePrueba987"))

    def test_cambio_de_rol(self):
        self._crear()
        usuario = Usuario.objects.get(username="nuevo_operador")
        r = self.client.patch(
            "/api/usuarios/%s/" % usuario.pk, {"rol": Rol.SUPERVISOR}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        usuario.refresh_from_db()
        self.assertEqual(rol_de(usuario), Rol.SUPERVISOR)

    def test_baja_de_usuario(self):
        self._crear()
        usuario = Usuario.objects.get(username="nuevo_operador")
        r = self.client.delete("/api/usuarios/%s/" % usuario.pk)
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Usuario.objects.filter(username="nuevo_operador").exists())

    def test_busqueda_y_filtro_por_rol(self):
        self._crear()
        r = self.client.get("/api/usuarios/?rol=%s" % Rol.SUPERVISOR)
        nombres = [f["username"] for f in r.data["results"]]
        self.assertIn("super_prueba", nombres)
        self.assertNotIn("nuevo_operador", nombres)

        r = self.client.get("/api/usuarios/?buscar=nuevo")
        self.assertEqual([f["username"] for f in r.data["results"]], ["nuevo_operador"])

    def test_las_altas_y_bajas_quedan_en_la_bitacora(self):
        self._crear()
        usuario = Usuario.objects.get(username="nuevo_operador")
        self.client.delete("/api/usuarios/%s/" % usuario.pk)
        acciones = set(RegistroAuditoria.objects.values_list("accion", flat=True))
        self.assertIn(RegistroAuditoria.USUARIO_CREADO, acciones)
        self.assertIn(RegistroAuditoria.USUARIO_ELIMINADO, acciones)


class CandadosDeAdministradorTests(CasoBase):
    """El sistema no puede quedarse sin nadie que lo administre."""

    def setUp(self):
        super().setUp()
        self.entrar_como(self.admin)

    def test_no_puedo_borrarme_a_mi_mismo(self):
        r = self.client.delete("/api/usuarios/%s/" % self.admin.pk)
        self.assertEqual(r.status_code, 400)
        self.assertTrue(Usuario.objects.filter(pk=self.admin.pk).exists())

    def test_no_puedo_desactivarme_a_mi_mismo(self):
        r = self.client.patch(
            "/api/usuarios/%s/" % self.admin.pk, {"is_active": False}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_no_puedo_quitarme_el_rol_de_administrador(self):
        r = self.client.patch(
            "/api/usuarios/%s/" % self.admin.pk, {"rol": Rol.OPERADOR}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(rol_de(self.admin), Rol.ADMINISTRADOR)

    def test_no_se_puede_degradar_al_ultimo_administrador(self):
        otro = crear_usuario("admin2", Rol.ADMINISTRADOR)
        self.entrar_como(otro)
        # Con dos administradores, bajar al primero se permite...
        r = self.client.patch(
            "/api/usuarios/%s/" % self.admin.pk, {"rol": Rol.OPERADOR}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        # ...pero ahora 'otro' es el unico que queda y no puede irse.
        r = self.client.patch(
            "/api/usuarios/%s/" % otro.pk, {"rol": Rol.OPERADOR}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    def test_con_otro_administrador_activo_si_se_puede_borrar_uno(self):
        otro = crear_usuario("admin2", Rol.ADMINISTRADOR)
        r = self.client.delete("/api/usuarios/%s/" % otro.pk)
        self.assertEqual(r.status_code, 204)

    def test_un_administrador_desactivado_no_cuenta_como_respaldo(self):
        crear_usuario("admin_suspendido", Rol.ADMINISTRADOR, activo=False)
        otro = crear_usuario("admin2", Rol.ADMINISTRADOR)
        self.entrar_como(otro)
        self.client.patch("/api/usuarios/%s/" % self.admin.pk, {"rol": Rol.OPERADOR}, format="json")
        r = self.client.patch("/api/usuarios/%s/" % otro.pk, {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 400)


class CatalogoDeRolesTests(CasoBase):
    def test_devuelve_los_tres_roles_con_sus_permisos(self):
        self.entrar_como(self.admin)
        r = self.client.get("/api/roles/")
        self.assertEqual(r.status_code, 200)
        valores = {fila["valor"] for fila in r.data}
        self.assertEqual(valores, {Rol.ADMINISTRADOR, Rol.SUPERVISOR, Rol.OPERADOR})
        operador = next(f for f in r.data if f["valor"] == Rol.OPERADOR)
        self.assertEqual(sorted(operador["permisos"]), ["control_faja", "monitoreo"])
