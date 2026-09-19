# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import PerfilUsuario, RegistroAuditoria


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "rol", "telefono", "actualizado_en")
    list_filter = ("rol",)
    search_fields = ("usuario__username", "usuario__email")


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("creado_en", "usuario_nombre", "accion", "descripcion", "direccion_ip")
    list_filter = ("accion",)
    search_fields = ("usuario_nombre", "descripcion")
    readonly_fields = [c.name for c in RegistroAuditoria._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
