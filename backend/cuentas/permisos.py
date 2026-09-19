# -*- coding: utf-8 -*-
"""
Permisos por rol para la API.

El administrador de sistemas es superconjunto: entra a todo. El supervisor de
calidad entra ademas a lo del operador (necesita ver la linea para decidir).
El operador solo monitorea y arranca/para la faja.

Aparte de los roles humanos esta EsDispositivoVision: el modulo vision/ no
tiene un usuario, se identifica con una clave estatica en la cabecera
X-API-Key (ver settings.VISION_API_KEY y vision/telemetria_cliente.py).
"""
import hmac

from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Rol, rol_de

CABECERA_CLAVE = "HTTP_X_API_KEY"


class _PorRol(BasePermission):
    roles = ()

    def has_permission(self, request, view):
        return rol_de(getattr(request, "user", None)) in self.roles


class EsAdministrador(_PorRol):
    """Gestion de usuarios y auditoria."""

    message = "Se requiere el rol de Administrador de sistemas."
    roles = (Rol.ADMINISTRADOR,)


class EsSupervisor(_PorRol):
    """Analiticos, lotes, parametros del modelo y galeria de mermas."""

    message = "Se requiere el rol de Supervisor de calidad."
    roles = (Rol.ADMINISTRADOR, Rol.SUPERVISOR)


class EsPersonalDeLinea(_PorRol):
    """Cualquier rol valido: monitoreo de la linea y control de marcha/paro."""

    message = "Se requiere una cuenta activa con rol asignado."
    roles = (Rol.ADMINISTRADOR, Rol.SUPERVISOR, Rol.OPERADOR)


class LecturaPersonalEscrituraSupervisor(BasePermission):
    """Leer: cualquier rol. Modificar: supervisor o administrador."""

    message = "Solo el Supervisor de calidad puede modificar este recurso."

    def has_permission(self, request, view):
        rol = rol_de(getattr(request, "user", None))
        if request.method in SAFE_METHODS:
            return rol in (Rol.ADMINISTRADOR, Rol.SUPERVISOR, Rol.OPERADOR)
        return rol in (Rol.ADMINISTRADOR, Rol.SUPERVISOR)


class EsDispositivoVision(BasePermission):
    """
    El modulo vision/ manda telemetria y consulta configuracion con una clave
    estatica. Se compara en tiempo constante para no filtrar el prefijo
    correcto por diferencias de tiempo de respuesta.
    """

    message = "Cabecera X-API-Key ausente o invalida."

    def has_permission(self, request, view):
        enviada = request.META.get(CABECERA_CLAVE, "")
        esperada = settings.VISION_API_KEY
        if not enviada or not esperada:
            return False
        return hmac.compare_digest(str(enviada), str(esperada))


class EsDispositivoVisionOSupervisor(BasePermission):
    """Lo que consume vision/ pero que el supervisor tambien puede consultar."""

    message = "Se requiere la clave del dispositivo o el rol de Supervisor."

    def has_permission(self, request, view):
        return EsDispositivoVision().has_permission(request, view) or EsSupervisor().has_permission(
            request, view
        )
