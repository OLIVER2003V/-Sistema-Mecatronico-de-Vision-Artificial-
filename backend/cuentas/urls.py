# -*- coding: utf-8 -*-
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    AuditoriaViewSet,
    CambiarPasswordView,
    LoginView,
    RolesView,
    UsuarioViewSet,
    YoView,
)

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("auditoria", AuditoriaViewSet, basename="auditoria")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refrescar/", TokenRefreshView.as_view(), name="refrescar-token"),
    path("auth/verificar/", TokenVerifyView.as_view(), name="verificar-token"),
    path("auth/yo/", YoView.as_view(), name="yo"),
    path("auth/password/", CambiarPasswordView.as_view(), name="cambiar-password"),
    path("roles/", RolesView.as_view(), name="roles"),
    path("", include(router.urls)),
]
