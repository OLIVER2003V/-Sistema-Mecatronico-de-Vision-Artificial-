# -*- coding: utf-8 -*-
"""
Vistas de cuentas: inicio de sesion, datos del usuario en curso, CRUD de
usuarios (solo administrador) y bitacora de auditoria.
"""
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import PerfilUsuario, RegistroAuditoria, Rol, registrar, rol_de
from .permisos import EsAdministrador, EsPersonalDeLinea
from .serializers import (
    CambioPasswordSerializer,
    LoginSerializer,
    RegistroAuditoriaSerializer,
    UsuarioSerializer,
)

Usuario = get_user_model()

# Lo que puede hacer cada rol; el frontend lo usa para armar el menu. La
# autorizacion de verdad la hace cuentas/permisos.py en cada endpoint: esto
# es solo para no mostrar botones que igual irian a dar 403.
PERMISOS_POR_ROL = {
    Rol.ADMINISTRADOR: [
        "usuarios",
        "auditoria",
        "analiticos",
        "lotes",
        "parametros",
        "mermas",
        "monitoreo",
        "control_faja",
    ],
    Rol.SUPERVISOR: ["analiticos", "lotes", "parametros", "mermas", "monitoreo", "control_faja"],
    Rol.OPERADOR: ["monitoreo", "control_faja"],
}


def datos_sesion(usuario):
    rol = rol_de(usuario)
    return {
        "usuario": UsuarioSerializer(usuario).data,
        "rol": rol,
        "permisos": PERMISOS_POR_ROL.get(rol, []),
    }


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ -- devuelve access + refresh + datos del usuario."""

    serializer_class = LoginSerializer
    # Limita los intentos por IP (ver REST_FRAMEWORK.DEFAULT_THROTTLE_RATES).
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        respuesta = super().post(request, *args, **kwargs)
        if respuesta.status_code == status.HTTP_200_OK:
            nombre = str(request.data.get("username", ""))[:150]
            usuario = Usuario.objects.filter(username=nombre).first()
            registrar(request, RegistroAuditoria.INICIO_SESION, "Inicio de sesion", usuario=usuario)
        return respuesta


class YoView(APIView):
    """GET /api/auth/yo/ -- quien soy, que rol tengo y que puedo ver."""

    permission_classes = [EsPersonalDeLinea]

    def get(self, request):
        return Response(datos_sesion(request.user))


class CambiarPasswordView(APIView):
    """POST /api/auth/password/ -- el usuario cambia su propia contrasena."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializador = CambioPasswordSerializer(data=request.data, context={"request": request})
        serializador.is_valid(raise_exception=True)
        serializador.save()
        return Response({"detalle": "Contrasena actualizada."})


class UsuarioViewSet(viewsets.ModelViewSet):
    """
    /api/usuarios/ -- CRUD de usuarios. Solo Administrador de sistemas.

    Dos candados para no dejar el sistema sin quien lo administre:
      * nadie puede desactivarse, bajarse el rol ni borrarse a si mismo;
      * no se puede quitar/desactivar/borrar al ultimo administrador activo.
    """

    serializer_class = UsuarioSerializer
    permission_classes = [EsAdministrador]

    def get_queryset(self):
        qs = Usuario.objects.select_related("perfil").order_by("username")
        buscar = self.request.query_params.get("buscar")
        if buscar:
            qs = qs.filter(
                Q(username__icontains=buscar)
                | Q(first_name__icontains=buscar)
                | Q(last_name__icontains=buscar)
                | Q(email__icontains=buscar)
            )
        rol = self.request.query_params.get("rol")
        if rol:
            qs = qs.filter(perfil__rol=rol)
        return qs

    @staticmethod
    def _otros_administradores(excluido_pk):
        return (
            PerfilUsuario.objects.filter(rol=Rol.ADMINISTRADOR, usuario__is_active=True)
            .exclude(usuario__pk=excluido_pk)
            .exists()
        )

    def _error(self, mensaje):
        return Response({"detalle": mensaje}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        usuario = serializer.save()
        registrar(
            self.request,
            RegistroAuditoria.USUARIO_CREADO,
            "Alta de '%s' con rol %s" % (usuario.username, rol_de(usuario)),
        )

    def update(self, request, *args, **kwargs):
        objetivo = self.get_object()
        es_uno_mismo = objetivo.pk == request.user.pk
        rol_nuevo = (request.data.get("rol") or "").upper() or None
        activo_nuevo = request.data.get("is_active")
        se_desactiva = activo_nuevo is False or str(activo_nuevo).lower() == "false"
        deja_de_ser_admin = rol_nuevo is not None and rol_nuevo != Rol.ADMINISTRADOR

        if es_uno_mismo and se_desactiva:
            return self._error("No puede desactivar su propia cuenta.")
        if es_uno_mismo and deja_de_ser_admin:
            return self._error("No puede quitarse a si mismo el rol de administrador.")
        if (se_desactiva or deja_de_ser_admin) and rol_de(objetivo) == Rol.ADMINISTRADOR:
            if not self._otros_administradores(objetivo.pk):
                return self._error("Debe quedar al menos un administrador activo.")

        respuesta = super().update(request, *args, **kwargs)
        if respuesta.status_code == status.HTTP_200_OK:
            registrar(
                request,
                RegistroAuditoria.USUARIO_ACTUALIZADO,
                "Edicion de '%s'" % objetivo.username,
            )
        return respuesta

    def destroy(self, request, *args, **kwargs):
        objetivo = self.get_object()
        if objetivo.pk == request.user.pk:
            return self._error("No puede eliminar su propia cuenta.")
        if rol_de(objetivo) == Rol.ADMINISTRADOR and not self._otros_administradores(objetivo.pk):
            return self._error("Debe quedar al menos un administrador activo.")

        nombre = objetivo.username
        respuesta = super().destroy(request, *args, **kwargs)
        registrar(request, RegistroAuditoria.USUARIO_ELIMINADO, "Baja de '%s'" % nombre)
        return respuesta


class RolesView(APIView):
    """GET /api/roles/ -- catalogo de roles para los formularios del frontend."""

    permission_classes = [EsAdministrador]

    def get(self, request):
        return Response(
            [
                {"valor": valor, "nombre": nombre, "permisos": PERMISOS_POR_ROL.get(valor, [])}
                for valor, nombre in Rol.choices
            ]
        )


class AuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """/api/auditoria/ -- bitacora, solo lectura y solo para el administrador."""

    serializer_class = RegistroAuditoriaSerializer
    permission_classes = [EsAdministrador]

    def get_queryset(self):
        qs = RegistroAuditoria.objects.all()
        accion = self.request.query_params.get("accion")
        if accion:
            qs = qs.filter(accion=accion)
        return qs
