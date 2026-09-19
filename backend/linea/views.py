# -*- coding: utf-8 -*-
"""
Vistas de SORT-MATIC.

Quien puede que (ver cuentas/permisos.py):
    vision/ (clave X-API-Key)  telemetria, comandos/siguiente, camara/frame,
                               configuracion/vision, estado-faja (POST)
    Operador                   kpis, estado-faja (GET), comandos (POST), lotes (GET)
    Supervisor                 + tendencia, mermas, configuracion (PUT), lotes (PATCH/cerrar)
    Administrador              todo lo anterior

TelemetriaView es la puerta de entrada de vision/telemetria_cliente.py: cada
POST es una botella procesada. Se asocia al lote activo y, si con esa botella
se llega a la capacidad del lote, se cierra y se abre el siguiente en la misma
transaccion (select_for_update evita que dos POST casi simultaneos rompan el
conteo). Despues de confirmar la transaccion se emite por WebSocket.
"""
import base64

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncHour
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.models import RegistroAuditoria, registrar
from cuentas.permisos import (
    EsDispositivoVision,
    EsDispositivoVisionOSupervisor,
    EsPersonalDeLinea,
    EsSupervisor,
    LecturaPersonalEscrituraSupervisor,
)

from .models import ComandoFaja, ConfiguracionLinea, EstadoFaja, FotoDescarte, Inspeccion, LoteProduccion
from .serializers import (
    ComandoFajaSerializer,
    ConfiguracionLineaSerializer,
    EstadoFajaEntradaSerializer,
    EstadoFajaSerializer,
    InspeccionSerializer,
    LoteProduccionSerializer,
    MermaSerializer,
    TelemetriaEntradaSerializer,
)

GRUPO_TELEMETRIA = "telemetria"

# Tope de resultados que la galeria de mermas acepta por pagina: evita que un
# ?page_size enorme haga que el backend arme miles de URLs firmadas de S3.
TAMANO_PAGINA_MAXIMO = 200


def _emitir(evento, datos):
    capa = get_channel_layer()
    if capa is None:
        return
    async_to_sync(capa.group_send)(
        GRUPO_TELEMETRIA, {"type": "evento.telemetria", "evento": evento, "datos": datos}
    )


def _lote_con_total(lote_id):
    return (
        LoteProduccion.objects.annotate(total_inspecciones=Count("inspecciones"))
        .get(pk=lote_id)
    )


def _resolver_lote(lote_param):
    if lote_param:
        lote = LoteProduccion.objects.filter(pk=lote_param).first() if str(lote_param).isdigit() else None
        if lote is None:
            lote = LoteProduccion.objects.filter(correlativo=lote_param).first()
        return lote
    return (
        LoteProduccion.objects.filter(estado=LoteProduccion.ACTIVO).first()
        or LoteProduccion.objects.order_by("-numero").first()
    )


# ------------------------------------------------------------ configuracion --

class ConfiguracionLineaView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/configuracion/  -- cualquier rol (el operador la ve de referencia)
    PUT  /api/configuracion/  -- solo Supervisor de calidad

    Al guardar se emite el evento 'configuracion' por WebSocket y sube
    `version`: vision/ lo detecta en su proximo sondeo y se reconfigura en
    caliente, sin reiniciar la inspeccion.
    """

    serializer_class = ConfiguracionLineaSerializer
    permission_classes = [LecturaPersonalEscrituraSupervisor]

    def get_object(self):
        return ConfiguracionLinea.actual()

    def perform_update(self, serializer):
        anterior = ConfiguracionLinea.actual()
        previos = {c: getattr(anterior, c) for c in serializer.validated_data}
        config = serializer.save(actualizado_por=self.request.user)

        cambios = [
            "%s: %s -> %s" % (c, previos[c], getattr(config, c))
            for c in previos
            if previos[c] != getattr(config, c)
        ]
        if cambios:
            registrar(
                self.request,
                RegistroAuditoria.CONFIG_ACTUALIZADA,
                "; ".join(cambios),
            )
        _emitir("configuracion", ConfiguracionLineaSerializer(config).data)


class ConfiguracionVisionView(APIView):
    """
    GET /api/configuracion/vision/ -- umbrales en el formato de
    vision/clasificador.py (fracciones 0-1). Lo consulta el modulo de vision
    cada pocos segundos; si `version` cambio, aplica los nuevos valores sin
    reiniciar (ver vision/telemetria_cliente.py -> ClienteConfiguracion).
    """

    # Sin authentication_classes vacio: el supervisor entra con su JWT y el
    # dispositivo, que no manda Authorization, queda como anonimo y pasa por
    # la clave. Es un GET, asi que SessionAuthentication no exige CSRF.
    permission_classes = [EsDispositivoVisionOSupervisor]

    def get(self, request):
        config = ConfiguracionLinea.actual()
        return Response(
            {
                "version": config.version,
                "actualizado_en": config.actualizado_en,
                "modelo": config.parametros_vision(),
                "botellas_por_lote": config.botellas_por_lote,
            }
        )


# -------------------------------------------------------------------- lotes --

class LoteProduccionViewSet(viewsets.ModelViewSet):
    """
    /api/lotes/         GET  -- historial (cualquier rol)
    /api/lotes/<id>/    PATCH -- cambiar la capacidad del lote ACTIVO (supervisor)
    /api/lotes/<id>/cerrar/  POST -- cerrar el lote y abrir el siguiente (supervisor)
    /api/lotes/activo/  GET  -- el lote en curso

    No se crean lotes a mano: el primero nace con la primera botella y los
    siguientes al llenarse el anterior. Lo que el supervisor gestiona es
    CUANTAS botellas entran en cada lote.
    """

    serializer_class = LoteProduccionSerializer
    permission_classes = [LecturaPersonalEscrituraSupervisor]
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_queryset(self):
        qs = LoteProduccion.objects.annotate(total_inspecciones=Count("inspecciones"))
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado.upper())
        return qs.order_by("-numero")

    def create(self, request, *args, **kwargs):
        return Response(
            {
                "detalle": "Los lotes se abren solos al llenarse el anterior. "
                "Ajuste 'botellas_por_lote' en la configuracion o cierre el lote activo."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=False, methods=["get"], url_path="activo")
    def activo(self, request):
        lote = LoteProduccion.objects.filter(estado=LoteProduccion.ACTIVO).first()
        if lote is None:
            return Response({"detalle": "No hay un lote activo."}, status=status.HTTP_404_NOT_FOUND)
        return Response(LoteProduccionSerializer(_lote_con_total(lote.pk)).data)

    def partial_update(self, request, *args, **kwargs):
        lote = self.get_object()
        if lote.estado != LoteProduccion.ACTIVO:
            return Response(
                {"detalle": "Solo se puede cambiar la capacidad del lote activo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializador = self.get_serializer(lote, data=request.data, partial=True)
        serializador.is_valid(raise_exception=True)
        capacidad = serializador.validated_data.get("capacidad_lote", lote.capacidad_lote)

        with transaction.atomic():
            lote = LoteProduccion.objects.select_for_update().get(pk=lote.pk)
            lote.capacidad_lote = capacidad
            lote.save(update_fields=["capacidad_lote"])
            # Si la nueva capacidad ya quedo cubierta, el lote se cierra en el
            # acto: dejarlo "activo" por encima de su capacidad seria incoherente.
            lote_nuevo = None
            if lote.inspecciones.count() >= capacidad:
                lote.cerrar()
                lote_nuevo = LoteProduccion.crear_siguiente(
                    ConfiguracionLinea.actual().botellas_por_lote
                )

        registrar(
            request,
            RegistroAuditoria.LOTE_ACTUALIZADO,
            "Capacidad de %s = %s" % (lote.correlativo, capacidad),
        )
        datos = LoteProduccionSerializer(_lote_con_total(lote.pk)).data
        if lote_nuevo is None:
            _emitir("progreso_lote", {"lote": datos})
        else:
            _emitir(
                "lote_rotado",
                {
                    "lote_anterior": lote.correlativo,
                    "lote_nuevo": LoteProduccionSerializer(_lote_con_total(lote_nuevo.pk)).data,
                },
            )
        return Response(datos)

    @action(detail=True, methods=["post"], url_path="cerrar", permission_classes=[EsSupervisor])
    def cerrar(self, request, pk=None):
        lote = self.get_object()
        if lote.estado != LoteProduccion.ACTIVO:
            return Response(
                {"detalle": "El lote ya estaba cerrado."}, status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            lote = LoteProduccion.objects.select_for_update().get(pk=lote.pk)
            lote.cerrar()
            lote_nuevo = LoteProduccion.crear_siguiente(ConfiguracionLinea.actual().botellas_por_lote)

        registrar(request, RegistroAuditoria.LOTE_CERRADO, "Cierre manual de %s" % lote.correlativo)
        nuevo = LoteProduccionSerializer(_lote_con_total(lote_nuevo.pk)).data
        _emitir("lote_rotado", {"lote_anterior": lote.correlativo, "lote_nuevo": nuevo})
        return Response({"lote_cerrado": LoteProduccionSerializer(_lote_con_total(lote.pk)).data,
                         "lote_nuevo": nuevo})


class InspeccionViewSet(viewsets.ReadOnlyModelViewSet):
    """Historico de inspecciones; filtrable por ?lote=<id>."""

    serializer_class = InspeccionSerializer
    permission_classes = [EsPersonalDeLinea]

    def get_queryset(self):
        qs = Inspeccion.objects.select_related("lote").all()
        lote_id = self.request.query_params.get("lote")
        if lote_id and str(lote_id).isdigit():
            qs = qs.filter(lote_id=lote_id)
        return qs


# ------------------------------------------------------------------ mermas ---

class MermasView(generics.ListAPIView):
    """
    GET /api/mermas/ -- galeria de botellas descartadas, con su foto.

    Filtros (todos opcionales y combinables):
        ?desde=2026-09-01&hasta=2026-09-19   por fecha (inclusive)
        ?hora_desde=8&hora_hasta=16          por franja horaria (0-23)
        ?tipo_defecto=SIN_TAPA               SIN_ETIQUETA | SIN_TAPA | OTRO
        ?resultado=LLENADO_BAJO              DEFECTUOSA | LLENADO_BAJO
        ?lote=12
        ?con_foto=false                      incluir descartes sin captura
    """

    serializer_class = MermaSerializer
    permission_classes = [EsSupervisor]

    def _entero(self, nombre, minimo, maximo):
        crudo = self.request.query_params.get(nombre)
        if crudo is None or not crudo.lstrip("-").isdigit():
            return None
        valor = int(crudo)
        return valor if minimo <= valor <= maximo else None

    def get_queryset(self):
        params = self.request.query_params
        qs = Inspeccion.objects.select_related("lote", "foto").exclude(
            resultado=Inspeccion.ACEPTADA
        )

        if params.get("con_foto", "true").lower() != "false":
            qs = qs.filter(foto__isnull=False)

        desde = parse_date(params.get("desde", "") or "")
        if desde:
            qs = qs.filter(fecha_hora__date__gte=desde)
        hasta = parse_date(params.get("hasta", "") or "")
        if hasta:
            qs = qs.filter(fecha_hora__date__lte=hasta)

        hora_desde = self._entero("hora_desde", 0, 23)
        if hora_desde is not None:
            qs = qs.filter(fecha_hora__hour__gte=hora_desde)
        hora_hasta = self._entero("hora_hasta", 0, 23)
        if hora_hasta is not None:
            qs = qs.filter(fecha_hora__hour__lte=hora_hasta)

        tipo = params.get("tipo_defecto")
        if tipo in dict(Inspeccion.TIPO_DEFECTO_CHOICES):
            qs = qs.filter(tipo_defecto=tipo)
        resultado = params.get("resultado")
        if resultado in dict(Inspeccion.RESULTADO_CHOICES):
            qs = qs.filter(resultado=resultado)
        lote = params.get("lote")
        if lote and str(lote).isdigit():
            qs = qs.filter(lote_id=lote)

        return qs.order_by("-fecha_hora")

    def paginate_queryset(self, queryset):
        pedido = self.request.query_params.get("page_size")
        if pedido and pedido.isdigit():
            self.paginator.page_size = min(int(pedido), TAMANO_PAGINA_MAXIMO)
        return super().paginate_queryset(queryset)


# -------------------------------------------------------------- telemetria ---

class TelemetriaView(APIView):
    """POST /api/telemetria/ -- una botella procesada por vision/."""

    permission_classes = [EsDispositivoVision]
    authentication_classes = []

    def post(self, request):
        entrada = TelemetriaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = dict(entrada.validated_data)
        foto = datos.pop("foto", None)

        config = ConfiguracionLinea.actual()

        with transaction.atomic():
            lote = (
                LoteProduccion.objects.select_for_update()
                .filter(estado=LoteProduccion.ACTIVO)
                .first()
            )
            if lote is None:
                lote = LoteProduccion.crear_siguiente(config.botellas_por_lote)

            inspeccion = Inspeccion.objects.create(lote=lote, **datos)
            if foto is not None:
                FotoDescarte.objects.create(inspeccion=inspeccion, imagen=foto)

            total = lote.inspecciones.count()
            lote_nuevo = None
            if total >= lote.capacidad_lote:
                lote.cerrar()
                lote_nuevo = LoteProduccion.crear_siguiente(config.botellas_por_lote)

        # Se emite ya con la transaccion confirmada.
        _emitir("inspeccion", InspeccionSerializer(inspeccion).data)
        _emitir("progreso_lote", {"lote": LoteProduccionSerializer(_lote_con_total(lote.pk)).data})
        if lote_nuevo is not None:
            _emitir(
                "lote_rotado",
                {
                    "lote_anterior": lote.correlativo,
                    "lote_nuevo": LoteProduccionSerializer(_lote_con_total(lote_nuevo.pk)).data,
                },
            )

        return Response(InspeccionSerializer(inspeccion).data, status=status.HTTP_201_CREATED)


class KpiView(APIView):
    """
    GET /api/kpis/?lote=<id o correlativo>
    Sin parametro: usa el lote activo, o si no hay ninguno, el ultimo creado.
    Los contadores de este endpoint son los que mira el Operador en la HMI.
    """

    permission_classes = [EsPersonalDeLinea]

    def get(self, request):
        lote = _resolver_lote(request.query_params.get("lote"))
        if lote is None:
            return Response({"detalle": "no hay lotes registrados"}, status=status.HTTP_404_NOT_FOUND)

        inspecciones = Inspeccion.objects.filter(lote=lote)
        total = inspecciones.count()

        def pct(n):
            return round(100.0 * n / total, 2) if total else 0.0

        conteo = inspecciones.aggregate(
            aceptadas=Count("id", filter=Q(resultado=Inspeccion.ACEPTADA)),
            defectuosas=Count("id", filter=Q(resultado=Inspeccion.DEFECTUOSA)),
            llenado_bajo=Count("id", filter=Q(resultado=Inspeccion.LLENADO_BAJO)),
        )
        aceptadas = conteo["aceptadas"]
        defectuosas = conteo["defectuosas"]
        llenado_bajo = conteo["llenado_bajo"]
        rechazadas = defectuosas + llenado_bajo

        fin = lote.fecha_fin or timezone.now()
        minutos = max((fin - lote.fecha_inicio).total_seconds() / 60.0, 1e-6)
        bpm = round(total / minutos, 2)

        defectos_qs = (
            inspecciones.filter(resultado=Inspeccion.DEFECTUOSA)
            .values("tipo_defecto")
            .annotate(n=Count("id"))
        )
        defectos = {(d["tipo_defecto"] or Inspeccion.OTRO): d["n"] for d in defectos_qs}
        predominante = max(defectos.items(), key=lambda kv: kv[1], default=None)
        defecto_predominante = None
        if predominante is not None:
            defecto_predominante = {
                "tipo_defecto": predominante[0],
                "porcentaje": round(100.0 * predominante[1] / defectuosas, 2) if defectuosas else 0.0,
            }

        # Contador simple (numeros crudos, no %) de cada tipo de descarte.
        conteos = {
            "aceptadas": aceptadas,
            "defectuosa": defectuosas,
            "sin_etiqueta": defectos.get(Inspeccion.SIN_ETIQUETA, 0),
            "sin_tapa": defectos.get(Inspeccion.SIN_TAPA, 0),
            "otro_defecto": defectos.get(Inspeccion.OTRO, 0),
            "llenado_bajo": llenado_bajo,
            "rechazadas_total": rechazadas,
        }

        config = ConfiguracionLinea.actual()
        return Response(
            {
                "lote": LoteProduccionSerializer(_lote_con_total(lote.pk)).data,
                "total_inspecciones": total,
                "yield_rate": pct(aceptadas),
                "reject_rate": pct(rechazadas),
                "cadencia_bpm": bpm,
                "cadencia_teorica_bpm": config.velocidad_teorica,
                "tasa_llenado_bajo": pct(llenado_bajo),
                "defecto_predominante": defecto_predominante,
                "defectos": defectos,
                "conteos": conteos,
            }
        )


class TendenciaView(APIView):
    """GET /api/tendencia/?lote=<id> -- aceptadas vs rechazadas, agrupado por hora."""

    permission_classes = [EsPersonalDeLinea]

    def get(self, request):
        lote = _resolver_lote(request.query_params.get("lote"))
        if lote is None:
            return Response([])

        filas = (
            Inspeccion.objects.filter(lote=lote)
            .annotate(hora=TruncHour("fecha_hora"))
            .values("hora")
            .annotate(
                aceptadas=Count("id", filter=Q(resultado=Inspeccion.ACEPTADA)),
                rechazadas=Count("id", filter=~Q(resultado=Inspeccion.ACEPTADA)),
            )
            .order_by("hora")
        )
        return Response(
            [
                {
                    "hora": timezone.localtime(fila["hora"]).strftime("%H:%M"),
                    "aceptadas": fila["aceptadas"],
                    "rechazadas": fila["rechazadas"],
                }
                for fila in filas
            ]
        )


# ------------------------------------------------------- control de la faja --

class ComandoCrearView(generics.CreateAPIView):
    """POST /api/comandos/ -- el operador deja un START/STOP/RESET pendiente."""

    serializer_class = ComandoFajaSerializer
    permission_classes = [EsPersonalDeLinea]
    queryset = ComandoFaja.objects.all()

    def perform_create(self, serializer):
        comando = serializer.save(solicitado_por=self.request.user)
        registrar(self.request, RegistroAuditoria.COMANDO_FAJA, "Comando %s" % comando.accion)
        estado = EstadoFaja.actual()
        estado.ultimo_comando = comando.accion
        estado.save(update_fields=["ultimo_comando"])
        _emitir("estado_faja", EstadoFajaSerializer(estado).data)


class ComandoSiguienteView(APIView):
    """
    GET /api/comandos/siguiente/ -- vision/telemetria_cliente.py (ClienteComandos)
    hace polling aca cada pocos milisegundos. Devuelve el comando pendiente
    mas viejo y lo marca consumido en la misma transaccion, para que dos
    llamadas casi simultaneas no se lleven el mismo comando.
    """

    permission_classes = [EsDispositivoVision]
    authentication_classes = []

    def get(self, request):
        with transaction.atomic():
            comando = (
                ComandoFaja.objects.select_for_update()
                .filter(consumido_en__isnull=True)
                .order_by("creado_en")
                .first()
            )
            if comando is None:
                return Response({"accion": None})
            comando.consumido_en = timezone.now()
            comando.save(update_fields=["consumido_en"])
        return Response({"accion": comando.accion})


class EstadoFajaView(APIView):
    """GET /api/estado-faja/ -- panel SCADA de la HMI (cualquier rol)."""

    permission_classes = [EsPersonalDeLinea]

    def get(self, request):
        return Response(EstadoFajaSerializer(EstadoFaja.actual()).data)


class EstadoFajaReporteView(APIView):
    """
    POST /api/estado-faja/reporte/ -- vision/ reporta lo que dice el firmware
    ('#START' / '#STOP'). Es el estado REAL de la faja, no el ultimo comando
    pedido: si el Arduino esta desconectado, el panel lo muestra.
    """

    permission_classes = [EsDispositivoVision]
    authentication_classes = []

    def post(self, request):
        entrada = EstadoFajaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        estado = EstadoFaja.actual()
        estado.en_marcha = datos["en_marcha"]
        estado.arduino_conectado = datos["arduino_conectado"]
        estado.detalle = datos["detalle"]
        estado.save(update_fields=["en_marcha", "arduino_conectado", "detalle"])

        serializado = EstadoFajaSerializer(estado).data
        _emitir("estado_faja", serializado)
        return Response(serializado)


class CamaraFrameView(APIView):
    """
    POST /api/camara/frame/ -- vision/ manda un JPEG cada pocos cientos de ms
    (ver ClienteCamara). No se persiste: se retransmite tal cual por
    WebSocket (base64) a quien este mirando el dashboard en ese momento.
    """

    permission_classes = [EsDispositivoVision]
    authentication_classes = []

    def post(self, request):
        foto = request.FILES.get("foto")
        if foto is None:
            return Response({"detalle": "falta el archivo 'foto'"}, status=status.HTTP_400_BAD_REQUEST)
        b64 = base64.b64encode(foto.read()).decode("ascii")
        _emitir("camara", {"jpeg_base64": b64})
        return Response({"ok": True})


class SaludView(APIView):
    """
    GET /api/salud/ -- sonda para el balanceador (ALB) y para docker healthcheck.
    Abierta a proposito: no revela nada y tiene que responder sin credenciales.
    """

    permission_classes = []
    authentication_classes = []

    def get(self, request):
        return Response({"estado": "ok", "hora": timezone.now()})
