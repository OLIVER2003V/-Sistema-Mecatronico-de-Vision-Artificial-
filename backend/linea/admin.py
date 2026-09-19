from django.contrib import admin

from .models import (
    ComandoFaja,
    ConfiguracionLinea,
    EstadoFaja,
    FotoDescarte,
    Inspeccion,
    LoteProduccion,
)


@admin.register(ConfiguracionLinea)
class ConfiguracionLineaAdmin(admin.ModelAdmin):
    list_display = (
        "version",
        "botellas_por_lote",
        "umbral_llenado_minimo",
        "confianza_etiqueta",
        "confianza_tapa",
        "actualizado_en",
    )
    readonly_fields = ("version", "actualizado_en")


@admin.register(EstadoFaja)
class EstadoFajaAdmin(admin.ModelAdmin):
    list_display = ("en_marcha", "arduino_conectado", "ultimo_comando", "actualizado_en")


@admin.register(LoteProduccion)
class LoteProduccionAdmin(admin.ModelAdmin):
    list_display = ("correlativo", "estado", "capacidad_lote", "fecha_inicio", "fecha_fin")
    list_filter = ("estado",)


@admin.register(Inspeccion)
class InspeccionAdmin(admin.ModelAdmin):
    list_display = ("lote", "resultado", "tipo_defecto", "estacion_descarte", "fecha_hora")
    list_filter = ("resultado", "tipo_defecto", "lote")
    date_hierarchy = "fecha_hora"


@admin.register(FotoDescarte)
class FotoDescarteAdmin(admin.ModelAdmin):
    list_display = ("inspeccion", "creada_en")


@admin.register(ComandoFaja)
class ComandoFajaAdmin(admin.ModelAdmin):
    list_display = ("accion", "solicitado_por", "creado_en", "consumido_en")
    list_filter = ("accion",)
