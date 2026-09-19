# -*- coding: utf-8 -*-
"""Utilidades compartidas por las pruebas: usuarios por rol y clientes autenticados."""
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from cuentas.models import Rol

Usuario = get_user_model()

CLAVE_VISION = "clave-de-prueba-del-dispositivo"
PASSWORD = "PruebaSegura123"


def crear_usuario(nombre, rol, password=PASSWORD, activo=True):
    usuario = Usuario.objects.create_user(username=nombre, password=password, is_active=activo)
    # La signal post_save ya creo el perfil; se edita ESE objeto (y no un
    # update_or_create) para que el usuario en memoria no quede con el rol
    # viejo cacheado en la relacion inversa.
    perfil = usuario.perfil
    perfil.rol = rol
    perfil.save(update_fields=["rol"])
    return usuario


def token_de(usuario):
    return str(RefreshToken.for_user(usuario).access_token)


def imagen_de_prueba(nombre="captura.jpg"):
    """JPEG minimo valido: ImageField lo rechaza si no es una imagen de verdad."""
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (12, 34, 56)).save(buffer, format="JPEG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/jpeg")


class CasoBase(APITestCase):
    """Crea un usuario por rol y deja atajos para autenticar el cliente."""

    def setUp(self):
        super().setUp()
        self.admin = crear_usuario("admin_prueba", Rol.ADMINISTRADOR)
        self.supervisor = crear_usuario("super_prueba", Rol.SUPERVISOR)
        self.operador = crear_usuario("oper_prueba", Rol.OPERADOR)

    def entrar_como(self, usuario):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer %s" % token_de(usuario))
        return usuario

    def salir(self):
        self.client.credentials()

    def como_dispositivo(self):
        """Cabecera de vision/: no hay usuario, solo la clave del dispositivo."""
        self.client.credentials(HTTP_X_API_KEY=CLAVE_VISION)
