from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CamaraFrameView,
    ComandoCrearView,
    ComandoSiguienteView,
    ConfiguracionLineaView,
    ConfiguracionVisionView,
    EstadoFajaReporteView,
    EstadoFajaView,
    InspeccionViewSet,
    KpiView,
    LoteProduccionViewSet,
    MermasView,
    SaludView,
    TelemetriaView,
    TendenciaView,
)

router = DefaultRouter()
router.register("lotes", LoteProduccionViewSet, basename="lote")
router.register("inspecciones", InspeccionViewSet, basename="inspeccion")

urlpatterns = [
    path("salud/", SaludView.as_view(), name="salud"),
    path("telemetria/", TelemetriaView.as_view(), name="telemetria"),
    path("kpis/", KpiView.as_view(), name="kpis"),
    path("tendencia/", TendenciaView.as_view(), name="tendencia"),
    path("mermas/", MermasView.as_view(), name="mermas"),
    path("configuracion/", ConfiguracionLineaView.as_view(), name="configuracion"),
    path("configuracion/vision/", ConfiguracionVisionView.as_view(), name="configuracion-vision"),
    path("comandos/", ComandoCrearView.as_view(), name="comando-crear"),
    path("comandos/siguiente/", ComandoSiguienteView.as_view(), name="comando-siguiente"),
    path("estado-faja/", EstadoFajaView.as_view(), name="estado-faja"),
    path("estado-faja/reporte/", EstadoFajaReporteView.as_view(), name="estado-faja-reporte"),
    path("camara/frame/", CamaraFrameView.as_view(), name="camara-frame"),
    path("", include(router.urls)),
]
