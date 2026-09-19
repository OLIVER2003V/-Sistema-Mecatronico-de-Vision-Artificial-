# -*- coding: utf-8 -*-
"""
Crea (o repara) una cuenta por cada rol para poder entrar al dashboard por
primera vez. Es idempotente: si el usuario ya existe solo se le corrige el
rol y se lo reactiva, nunca se le pisa la contrasena.

    python manage.py crear_usuarios_iniciales
    python manage.py crear_usuarios_iniciales --password "MiClaveSegura123"

Sin --password se genera una contrasena aleatoria por usuario y se imprime
UNA sola vez: no queda ninguna credencial fija escrita en el repositorio.
"""
import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from cuentas.models import PerfilUsuario, Rol

Usuario = get_user_model()

CUENTAS = [
    ("admin", Rol.ADMINISTRADOR, "Ana", "Administradora"),
    ("supervisor", Rol.SUPERVISOR, "Sergio", "Supervisor"),
    ("operador", Rol.OPERADOR, "Omar", "Operador"),
]

ALFABETO = string.ascii_letters + string.digits


def _password_aleatoria(largo=14):
    return "".join(secrets.choice(ALFABETO) for _ in range(largo))


class Command(BaseCommand):
    help = "Crea un usuario por cada rol (administrador, supervisor, operador)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=None,
            help="Contrasena para las cuentas nuevas (por defecto, una aleatoria por cuenta).",
        )

    @transaction.atomic
    def handle(self, *args, **opciones):
        fija = opciones["password"]
        creadas = []

        for nombre, rol, nombre_pila, apellido in CUENTAS:
            usuario = Usuario.objects.filter(username=nombre).first()
            if usuario is None:
                password = fija or _password_aleatoria()
                usuario = Usuario.objects.create_user(
                    username=nombre,
                    password=password,
                    first_name=nombre_pila,
                    last_name=apellido,
                    email="%s@embol.local" % nombre,
                    is_staff=(rol == Rol.ADMINISTRADOR),
                    is_superuser=(rol == Rol.ADMINISTRADOR),
                )
                creadas.append((nombre, rol, password))
            else:
                if not usuario.is_active:
                    usuario.is_active = True
                    usuario.save(update_fields=["is_active"])
                self.stdout.write("  ya existia: %s" % nombre)

            PerfilUsuario.objects.update_or_create(usuario=usuario, defaults={"rol": rol})

        if not creadas:
            self.stdout.write(self.style.SUCCESS("Nada que crear: las tres cuentas ya existen."))
            return

        self.stdout.write(self.style.SUCCESS("\nCuentas creadas (anote las contrasenas AHORA):"))
        for nombre, rol, password in creadas:
            self.stdout.write("  %-12s %-14s %s" % (nombre, rol, password))
        self.stdout.write(
            self.style.WARNING("\nCambie estas contrasenas al entrar. No se vuelven a mostrar.")
        )
