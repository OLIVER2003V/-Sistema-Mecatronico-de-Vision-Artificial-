# -*- coding: utf-8 -*-
"""
Garantiza que TODO usuario tenga un PerfilUsuario, incluso los creados por
`manage.py createsuperuser` o desde el admin de Django. Sin esto, rol_de()
devolveria None y el usuario no podria entrar a ninguna vista.
"""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PerfilUsuario, Rol


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil(sender, instance, created, **kwargs):
    if not created:
        return
    rol = Rol.ADMINISTRADOR if instance.is_superuser else Rol.OPERADOR
    PerfilUsuario.objects.get_or_create(usuario=instance, defaults={"rol": rol})
