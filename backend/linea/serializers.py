# -*- coding: utf-8 -*-
from rest_framework import serializers

from .models import (
    ComandoFaja,
    ConfiguracionLinea,
    EstadoFaja,
    FotoDescarte,
    Inspeccion,
    LoteProduccion,
)


class ConfiguracionLineaSerializer(serializers.ModelSerializer):
    """
    Lo que edita el Supervisor de calidad. Los help_text del modelo viajan al
    frontend en `ayuda` para que la pantalla explique cada parametro sin
    duplicar los textos en el codigo de React.
    """

    ayuda = serializers.SerializerMethodField()

    class Meta:
        model = ConfiguracionLinea
        fields = [
            "umbral_llenado_minimo",
            "confianza_etiqueta",
            "confianza_tapa",
            "confianza_deteccion",
            "confianza_defecto",
            "fraccion_cuello",
            "tamano_imagen",
            "dispositivo_inferencia",
            "velocidad_teorica",
            "botellas_por_lote",
            "version",
            "actualizado_en",
            "ayuda",
        ]
        read_only_fields = ["version", "actualizado_en"]

    def get_ayuda(self, obj):
        campos = self.Meta.fields
        return {
            f.name: f.help_text
            for f in ConfiguracionLinea._meta.get_fields()
            if getattr(f, "help_text", "") and f.name in campos
        }

    def validate(self, datos):
        def valor(nombre):
            if nombre in datos:
                return datos[nombre]
            return getattr(self.instance, nombre) if self.instance is not None else None

        deteccion = valor("confianza_deteccion")
        if deteccion is not None:
            # Una clase solo "aparece" a partir de confianza_deteccion: si ese
            # piso queda por encima de los umbrales de aprobacion, la etiqueta
            # o la tapa nunca podrian darse por validas y TODO saldria defectuoso.
            for campo, nombre in (
                ("confianza_etiqueta", "de la etiqueta"),
                ("confianza_tapa", "de la tapa"),
                ("confianza_defecto", "de defecto"),
            ):
                umbral = valor(campo)
                if umbral is not None and deteccion > umbral:
                    raise serializers.ValidationError(
                        {
                            "confianza_deteccion": (
                                "No puede superar la certeza %s (%.0f%%): con ese piso el "
                                "sistema nunca llegaria a evaluarla." % (nombre, umbral)
                            )
                        }
                    )
        return datos


class EstadoFajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoFaja
        fields = ["en_marcha", "arduino_conectado", "ultimo_comando", "detalle", "actualizado_en"]
        read_only_fields = fields


class EstadoFajaEntradaSerializer(serializers.Serializer):
    """Lo que reporta vision/ al leer las lineas '#' del firmware."""

    en_marcha = serializers.BooleanField()
    arduino_conectado = serializers.BooleanField(required=False, default=True)
    detalle = serializers.CharField(required=False, allow_blank=True, max_length=120, default="")


class LoteProduccionSerializer(serializers.ModelSerializer):
    # se anota con .annotate(total_inspecciones=Count(...)) en las vistas
    total_inspecciones = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = LoteProduccion
        fields = [
            "id",
            "correlativo",
            "numero",
            "capacidad_lote",
            "estado",
            "fecha_inicio",
            "fecha_fin",
            "total_inspecciones",
        ]
        read_only_fields = ["id", "correlativo", "numero", "estado", "fecha_inicio", "fecha_fin"]


class FotoDescarteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FotoDescarte
        fields = ["id", "imagen", "creada_en"]


class InspeccionSerializer(serializers.ModelSerializer):
    foto = FotoDescarteSerializer(read_only=True)
    lote_correlativo = serializers.CharField(source="lote.correlativo", read_only=True)

    class Meta:
        model = Inspeccion
        fields = [
            "id",
            "lote",
            "lote_correlativo",
            "resultado",
            "tipo_defecto",
            "nivel_llenado_detectado",
            "confianza_ia",
            "estacion_descarte",
            "fecha_hora",
            "foto",
        ]
        read_only_fields = ["lote", "fecha_hora"]


class MermaSerializer(serializers.ModelSerializer):
    """Una entrada de la galeria de mermas: la inspeccion rechazada con su foto."""

    lote_correlativo = serializers.CharField(source="lote.correlativo", read_only=True)
    resultado_nombre = serializers.CharField(source="get_resultado_display", read_only=True)
    tipo_defecto_nombre = serializers.CharField(source="get_tipo_defecto_display", read_only=True)
    estacion_nombre = serializers.CharField(source="get_estacion_descarte_display", read_only=True)
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Inspeccion
        fields = [
            "id",
            "lote",
            "lote_correlativo",
            "resultado",
            "resultado_nombre",
            "tipo_defecto",
            "tipo_defecto_nombre",
            "estacion_descarte",
            "estacion_nombre",
            "nivel_llenado_detectado",
            "confianza_ia",
            "fecha_hora",
            "imagen_url",
        ]

    def get_imagen_url(self, obj):
        foto = getattr(obj, "foto", None)
        if foto is None or not foto.imagen:
            return None
        nombre = getattr(foto.imagen, "name", "") or ""
        if nombre.startswith("http://") or nombre.startswith("https://"):
            if "?" in nombre:
                return nombre
            try:
                from urllib.parse import urlparse
                parsed = urlparse(nombre)
                if hasattr(foto.imagen, "storage") and hasattr(foto.imagen.storage, "url"):
                    key = parsed.path.lstrip("/")
                    if key:
                        return foto.imagen.storage.url(key)
            except Exception:
                pass
            return nombre

        url = foto.imagen.url
        pedido = self.context.get("request")
        return pedido.build_absolute_uri(url) if pedido is not None and url.startswith("/") else url


class ComandoFajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComandoFaja
        fields = ["id", "accion", "creado_en", "consumido_en"]
        read_only_fields = ["id", "creado_en", "consumido_en"]


class TelemetriaEntradaSerializer(serializers.Serializer):
    """Lo que manda vision/telemetria_cliente.py por cada botella procesada."""

    resultado = serializers.ChoiceField(choices=Inspeccion.RESULTADO_CHOICES)
    tipo_defecto = serializers.ChoiceField(
        choices=Inspeccion.TIPO_DEFECTO_CHOICES,
        required=False,
        allow_null=True,
        default=None,
    )
    nivel_llenado_detectado = serializers.FloatField(
        required=False, allow_null=True, default=None, min_value=0, max_value=100
    )
    confianza_ia = serializers.FloatField(
        required=False, allow_null=True, default=None, min_value=0, max_value=100
    )
    estacion_descarte = serializers.ChoiceField(
        choices=Inspeccion.ESTACION_CHOICES,
        required=False,
        allow_null=True,
        default=None,
    )
    foto = serializers.ImageField(required=False, allow_null=True)

    def validate(self, datos):
        if datos.get("resultado") == Inspeccion.ACEPTADA:
            # Una botella aprobada no arrastra motivo de descarte: si viniera,
            # ensuciaria el Pareto de defectos y los contadores de merma.
            datos["tipo_defecto"] = None
            datos["estacion_descarte"] = None
        return datos
