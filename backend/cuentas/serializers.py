# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model, password_validation
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import PerfilUsuario, RegistroAuditoria, Rol, rol_de

Usuario = get_user_model()


class UsuarioSerializer(serializers.ModelSerializer):
    """
    Usuario + su rol, vistos como un solo objeto plano por la API.

    La contrasena solo entra (write_only): nunca se devuelve ni se guarda en
    claro, se pasa por set_password(). Al crear es obligatoria; al editar,
    opcional (si no viene, la contrasena queda como estaba).
    """

    rol = serializers.ChoiceField(choices=Rol.choices, source="perfil.rol")
    telefono = serializers.CharField(
        source="perfil.telefono", required=False, allow_blank=True, max_length=30
    )
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    rol_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "rol",
            "rol_nombre",
            "telefono",
            "password",
            "last_login",
            "date_joined",
        ]
        read_only_fields = ["last_login", "date_joined"]

    def get_rol_nombre(self, obj):
        perfil = getattr(obj, "perfil", None)
        return perfil.get_rol_display() if perfil is not None else ""

    def validate_username(self, valor):
        valor = valor.strip()
        qs = Usuario.objects.filter(username__iexact=valor)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un usuario con ese nombre.")
        return valor

    def validate_password(self, valor):
        password_validation.validate_password(valor)
        return valor

    def validate(self, datos):
        if self.instance is None and not datos.get("password"):
            raise serializers.ValidationError(
                {"password": "Se requiere una contrasena para crear el usuario."}
            )
        return datos

    @transaction.atomic
    def create(self, datos_validados):
        perfil = datos_validados.pop("perfil", {})
        password = datos_validados.pop("password")
        usuario = Usuario(**datos_validados)
        usuario.set_password(password)
        usuario.save()
        # El perfil ya lo creo la signal post_save; aca solo se ajusta.
        PerfilUsuario.objects.update_or_create(usuario=usuario, defaults=perfil)
        usuario.refresh_from_db()
        return usuario

    @transaction.atomic
    def update(self, instancia, datos_validados):
        perfil = datos_validados.pop("perfil", {})
        password = datos_validados.pop("password", None)
        for campo, valor in datos_validados.items():
            setattr(instancia, campo, valor)
        if password:
            instancia.set_password(password)
        instancia.save()
        if perfil:
            PerfilUsuario.objects.update_or_create(usuario=instancia, defaults=perfil)
        instancia.refresh_from_db()
        return instancia


class CambioPasswordSerializer(serializers.Serializer):
    """Cambio de contrasena propia: hay que saber la actual."""

    password_actual = serializers.CharField(write_only=True)
    password_nueva = serializers.CharField(write_only=True)

    def validate_password_actual(self, valor):
        usuario = self.context["request"].user
        if not usuario.check_password(valor):
            raise serializers.ValidationError("La contrasena actual no es correcta.")
        return valor

    def validate_password_nueva(self, valor):
        password_validation.validate_password(valor, self.context["request"].user)
        return valor

    def save(self, **kwargs):
        usuario = self.context["request"].user
        usuario.set_password(self.validated_data["password_nueva"])
        usuario.save(update_fields=["password"])
        return usuario


class LoginSerializer(TokenObtainPairSerializer):
    """
    Agrega el rol dentro del propio token (asi el WebSocket lo conoce sin
    tocar la base) y devuelve los datos del usuario junto a las credenciales.
    """

    @classmethod
    def get_token(cls, usuario):
        token = super().get_token(usuario)
        token["rol"] = rol_de(usuario) or ""
        token["username"] = usuario.get_username()
        return token

    def validate(self, datos):
        resultado = super().validate(datos)
        if rol_de(self.user) is None:
            raise serializers.ValidationError(
                "La cuenta no tiene un rol asignado. Contacte al administrador."
            )
        resultado["usuario"] = UsuarioSerializer(self.user).data
        return resultado


class RegistroAuditoriaSerializer(serializers.ModelSerializer):
    accion_nombre = serializers.CharField(source="get_accion_display", read_only=True)

    class Meta:
        model = RegistroAuditoria
        fields = [
            "id",
            "usuario_nombre",
            "accion",
            "accion_nombre",
            "descripcion",
            "direccion_ip",
            "creado_en",
        ]
