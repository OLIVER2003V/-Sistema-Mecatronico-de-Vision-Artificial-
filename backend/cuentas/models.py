# -*- coding: utf-8 -*-
"""
Cuentas y roles de SORT-MATIC.

Se usa el User estandar de Django + un PerfilUsuario 1-a-1 con el rol. Se
eligio esto en vez de un AUTH_USER_MODEL propio para no romper las bases de
datos que ya existen (el cambio de modelo de usuario obliga a rehacer las
migraciones desde cero).

    Rol.ADMINISTRADOR  -- gestion de usuarios (CRUD) y auditoria.
    Rol.SUPERVISOR     -- analiticos, lotes, parametros del modelo y mermas.
    Rol.OPERADOR       -- monitoreo de contadores y marcha/paro de la faja.

El administrador es superconjunto de los otros dos: puede entrar a todas las
vistas. Ver cuentas/permisos.py.
"""
from django.conf import settings
from django.db import models


class Rol(models.TextChoices):
    ADMINISTRADOR = "ADMINISTRADOR", "Administrador de sistemas"
    SUPERVISOR = "SUPERVISOR", "Supervisor de calidad"
    OPERADOR = "OPERADOR", "Operador de planta"


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.OPERADOR)
    telefono = models.CharField(max_length=30, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        return "%s (%s)" % (self.usuario.get_username(), self.get_rol_display())


def rol_de(usuario):
    """
    Rol efectivo de un usuario, o None si no esta autenticado/activo.

    Un superusuario de Django siempre cuenta como ADMINISTRADOR aunque su
    perfil diga otra cosa: si no, un `createsuperuser` quedaria sin acceso.
    """
    if usuario is None or not usuario.is_authenticated or not usuario.is_active:
        return None
    if usuario.is_superuser:
        return Rol.ADMINISTRADOR
    perfil = getattr(usuario, "perfil", None)
    return perfil.rol if perfil is not None else None


class RegistroAuditoria(models.Model):
    """
    Bitacora de las acciones sensibles (quien, que, cuando, desde donde).

    Es de solo lectura desde la API: las filas las escribe el backend con
    `registrar()`. El nombre de usuario se copia como texto para que la
    bitacora siga siendo legible si despues se borra la cuenta.
    """

    INICIO_SESION = "INICIO_SESION"
    USUARIO_CREADO = "USUARIO_CREADO"
    USUARIO_ACTUALIZADO = "USUARIO_ACTUALIZADO"
    USUARIO_ELIMINADO = "USUARIO_ELIMINADO"
    CONFIG_ACTUALIZADA = "CONFIG_ACTUALIZADA"
    COMANDO_FAJA = "COMANDO_FAJA"
    LOTE_ACTUALIZADO = "LOTE_ACTUALIZADO"
    LOTE_CERRADO = "LOTE_CERRADO"
    ACCION_CHOICES = [
        (INICIO_SESION, "Inicio de sesion"),
        (USUARIO_CREADO, "Usuario creado"),
        (USUARIO_ACTUALIZADO, "Usuario actualizado"),
        (USUARIO_ELIMINADO, "Usuario eliminado"),
        (CONFIG_ACTUALIZADA, "Configuracion actualizada"),
        (COMANDO_FAJA, "Comando a la faja"),
        (LOTE_ACTUALIZADO, "Lote actualizado"),
        (LOTE_CERRADO, "Lote cerrado"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones",
    )
    usuario_nombre = models.CharField(max_length=150, blank=True)
    accion = models.CharField(max_length=25, choices=ACCION_CHOICES)
    descripcion = models.CharField(max_length=300, blank=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Registro de auditoria"
        verbose_name_plural = "Registros de auditoria"
        indexes = [models.Index(fields=["-creado_en"]), models.Index(fields=["accion"])]

    def __str__(self):
        return "%s - %s (%s)" % (self.creado_en, self.accion, self.usuario_nombre)


def _ip_del_pedido(request):
    """IP del cliente. Detras de un balanceador (AWS ALB) llega en X-Forwarded-For."""
    if request is None:
        return None
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def registrar(request, accion, descripcion="", usuario=None):
    """
    Anota una accion en la bitacora. Nunca lanza: una auditoria que falla no
    debe tumbar la operacion que la origino.
    """
    if usuario is None and request is not None:
        candidato = getattr(request, "user", None)
        if candidato is not None and candidato.is_authenticated:
            usuario = candidato
    try:
        return RegistroAuditoria.objects.create(
            usuario=usuario,
            usuario_nombre=usuario.get_username() if usuario is not None else "sistema",
            accion=accion,
            descripcion=descripcion[:300],
            direccion_ip=_ip_del_pedido(request),
        )
    except Exception:  # noqa: BLE001 -- la auditoria no puede romper el flujo
        return None
