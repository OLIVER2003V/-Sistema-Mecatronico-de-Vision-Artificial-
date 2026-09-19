# -*- coding: utf-8 -*-
"""
Modelos de SORT-MATIC.

    ConfiguracionLinea  -- fila unica (singleton, pk=1) con los umbrales de la
                            linea Y los parametros del modelo de vision. Es la
                            fuente de verdad: vision/ la consulta y se
                            reconfigura en caliente (ver vision/telemetria_cliente.py).
    EstadoFaja          -- fila unica con marcha/paro para el panel SCADA.
    LoteProduccion      -- lotes con correlativo LOTE-EMBOL-0001, 0002, ...
                            Solo puede haber UNO en estado ACTIVO a la vez.
    Inspeccion          -- una fila por botella procesada por vision/.
    FotoDescarte        -- foto de la botella, solo para las rechazadas.
    ComandoFaja         -- cola de START/STOP/RESET del dashboard al Arduino.
"""
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils import timezone


def _porcentaje(por_defecto, texto, minimo=0.0, maximo=100.0):
    return models.FloatField(
        default=por_defecto,
        validators=[MinValueValidator(minimo), MaxValueValidator(maximo)],
        help_text=texto,
    )


class ConfiguracionLinea(models.Model):
    """
    Parametros que el Supervisor de calidad edita desde la HMI.

    Los porcentajes se guardan en 0-100 porque es lo que el supervisor lee en
    pantalla; vision/ trabaja en 0-1 y la conversion la hace parametros_vision().

    Se opera siempre como una unica fila (pk=1). Ver ConfiguracionLinea.actual().
    """

    CPU = "cpu"
    GPU = "0"
    DISPOSITIVO_CHOICES = [(CPU, "CPU"), (GPU, "GPU (CUDA 0)")]
    TAMANO_CHOICES = [(v, "%d px" % v) for v in (320, 416, 512, 640, 768, 960, 1280)]

    # --- Calidad del producto ---
    umbral_llenado_minimo = _porcentaje(
        60.0, "Llenado minimo para aprobar una botella. Por debajo se descarta en la estacion 2."
    )

    # --- Certeza del modelo de vision (lo que el supervisor llama "nivel de confianza") ---
    confianza_etiqueta = _porcentaje(
        80.0, "Certeza minima para dar por presente la ETIQUETA. Mas alto = mas exigente."
    )
    confianza_tapa = _porcentaje(
        65.0, "Certeza minima para dar por presente la TAPA. Mas alto = mas exigente."
    )
    confianza_deteccion = _porcentaje(
        25.0, "Certeza minima para que el sistema considere que ve un objeto. Mas bajo = ve mas, con mas ruido."
    )
    confianza_defecto = _porcentaje(
        50.0, "Certeza minima para marcar una botella como rota o sin tapa."
    )
    fraccion_cuello = _porcentaje(
        15.0,
        "Altura del cuello mas la tapa como porcentaje de la botella. Calibra la medicion de llenado.",
        maximo=50.0,
    )
    tamano_imagen = models.PositiveIntegerField(
        default=640,
        choices=TAMANO_CHOICES,
        help_text="Resolucion a la que se analiza cada foto. Mas alta = mas precisa y mas lenta.",
    )
    dispositivo_inferencia = models.CharField(
        max_length=8,
        default=CPU,
        choices=DISPOSITIVO_CHOICES,
        help_text="Procesador que ejecuta el modelo de vision.",
    )

    # --- Produccion ---
    velocidad_teorica = models.FloatField(
        default=40.0,
        validators=[MinValueValidator(1.0), MaxValueValidator(600.0)],
        help_text="Cadencia teorica de la faja, en botellas por minuto (BPM).",
    )
    botellas_por_lote = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(100000)],
        help_text="Cuantas botellas entran en cada lote antes de abrir el siguiente.",
    )

    # Sube en cada guardado: vision/ lo compara para saber si tiene que
    # recargar sin pedir todo el objeto ni confiar en relojes sincronizados.
    version = models.PositiveIntegerField(default=0, editable=False)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = "Configuracion de linea"
        verbose_name_plural = "Configuracion de linea"

    def __str__(self):
        return "Config v%s (N=%s, llenado_min=%s%%)" % (
            self.version,
            self.botellas_por_lote,
            self.umbral_llenado_minimo,
        )

    def save(self, *args, **kwargs):
        self.version = (self.version or 0) + 1
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"version"}
        super().save(*args, **kwargs)

    @classmethod
    def actual(cls):
        obj, _creado = cls.objects.get_or_create(pk=1)
        return obj

    def parametros_vision(self):
        """
        Los mismos umbrales en el formato que consume vision/clasificador.py
        (fracciones 0-1 y las claves que ya usa config.json -> "modelo").
        """
        return {
            "conf_ok": round(self.confianza_etiqueta / 100.0, 4),
            "conf_ok_tapa": round(self.confianza_tapa / 100.0, 4),
            "conf_detectar": round(self.confianza_deteccion / 100.0, 4),
            "conf_defecto": round(self.confianza_defecto / 100.0, 4),
            "nivel_min": round(self.umbral_llenado_minimo / 100.0, 4),
            "cuello_frac": round(self.fraccion_cuello / 100.0, 4),
            "imgsz": int(self.tamano_imagen),
            "dispositivo": self.dispositivo_inferencia,
        }


class EstadoFaja(models.Model):
    """
    Marcha/paro de la faja para el panel SCADA de la HMI.

    Lo reporta vision/ leyendo las lineas '#START' / '#STOP' que imprime el
    firmware: asi el panel muestra lo que REALMENTE pasa en la faja y no solo
    lo que se pidio (un START puede no llegar si el Arduino esta desconectado).
    """

    en_marcha = models.BooleanField(default=False)
    arduino_conectado = models.BooleanField(default=False)
    ultimo_comando = models.CharField(max_length=10, blank=True)
    detalle = models.CharField(max_length=120, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estado de la faja"
        verbose_name_plural = "Estado de la faja"

    def __str__(self):
        return "Faja %s" % ("en marcha" if self.en_marcha else "detenida")

    @classmethod
    def actual(cls):
        obj, _creado = cls.objects.get_or_create(pk=1)
        return obj


class LoteProduccion(models.Model):
    ACTIVO = "ACTIVO"
    FINALIZADO = "FINALIZADO"
    ESTADO_CHOICES = [(ACTIVO, "Activo"), (FINALIZADO, "Finalizado")]

    correlativo = models.CharField(max_length=32, unique=True, editable=False)
    numero = models.PositiveIntegerField(unique=True, editable=False)
    capacidad_lote = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100000)]
    )
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=ACTIVO)
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-numero"]
        constraints = [
            UniqueConstraint(
                fields=["estado"],
                condition=Q(estado="ACTIVO"),
                name="unico_lote_activo",
            ),
        ]

    def __str__(self):
        return self.correlativo

    @classmethod
    def crear_siguiente(cls, capacidad):
        """Crea el proximo lote ACTIVO con correlativo LOTE-EMBOL-NNNN."""
        ultimo = cls.objects.order_by("-numero").first()
        numero = (ultimo.numero + 1) if ultimo else 1
        correlativo = "LOTE-EMBOL-%04d" % numero
        return cls.objects.create(
            correlativo=correlativo,
            numero=numero,
            capacidad_lote=capacidad,
            estado=cls.ACTIVO,
        )

    @classmethod
    def obtener_o_crear_activo(cls, capacidad_defecto):
        activo = cls.objects.filter(estado=cls.ACTIVO).first()
        return activo if activo is not None else cls.crear_siguiente(capacidad_defecto)

    def cerrar(self):
        self.estado = self.FINALIZADO
        self.fecha_fin = timezone.now()
        self.save(update_fields=["estado", "fecha_fin"])


class Inspeccion(models.Model):
    ACEPTADA = "ACEPTADA"
    DEFECTUOSA = "DEFECTUOSA"
    LLENADO_BAJO = "LLENADO_BAJO"
    RESULTADO_CHOICES = [
        (ACEPTADA, "Aceptada"),
        (DEFECTUOSA, "Defectuosa"),
        (LLENADO_BAJO, "Llenado bajo"),
    ]

    # El modelo de vision hoy distingue "sin etiqueta" y "sin tapa"; no
    # detecta abolladuras. OTRO queda como comodin por si se agregan clases.
    SIN_ETIQUETA = "SIN_ETIQUETA"
    SIN_TAPA = "SIN_TAPA"
    OTRO = "OTRO"
    TIPO_DEFECTO_CHOICES = [
        (SIN_ETIQUETA, "Sin etiqueta"),
        (SIN_TAPA, "Sin tapa"),
        (OTRO, "Otro"),
    ]

    ESTACION_1 = "ESTACION_1"
    ESTACION_2 = "ESTACION_2"
    ESTACION_CHOICES = [
        (ESTACION_1, "Estacion 1 (defecto fisico)"),
        (ESTACION_2, "Estacion 2 (llenado bajo)"),
    ]

    lote = models.ForeignKey(
        LoteProduccion, related_name="inspecciones", on_delete=models.PROTECT
    )
    resultado = models.CharField(max_length=15, choices=RESULTADO_CHOICES)
    tipo_defecto = models.CharField(
        max_length=15, choices=TIPO_DEFECTO_CHOICES, null=True, blank=True
    )
    nivel_llenado_detectado = models.FloatField(
        null=True, blank=True, help_text="Porcentaje 0-100 estimado por geometria"
    )
    confianza_ia = models.FloatField(null=True, blank=True, help_text="Porcentaje 0-100")
    estacion_descarte = models.CharField(
        max_length=12, choices=ESTACION_CHOICES, null=True, blank=True
    )
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_hora"]
        indexes = [
            models.Index(fields=["lote", "resultado"]),
            # La galeria de mermas filtra por fecha sobre todo el historico.
            models.Index(fields=["-fecha_hora", "resultado"]),
        ]

    def __str__(self):
        return "%s - %s (%s)" % (self.lote.correlativo, self.resultado, self.fecha_hora)


def ruta_foto_descarte(instancia, nombre_original):
    """
    Nombre aleatorio por foto. Con almacenamiento local las capturas se sirven
    por URL directa, asi que un nombre previsible ('captura.jpg') dejaria el
    historial de mermas al alcance de cualquiera que adivinara la ruta.
    """
    extension = Path(nombre_original or "").suffix.lower() or ".jpg"
    if extension not in (".jpg", ".jpeg", ".png", ".webp"):
        extension = ".jpg"
    hoy = timezone.localdate()
    return "descartes/%04d/%02d/%02d/%s%s" % (hoy.year, hoy.month, hoy.day, uuid4().hex, extension)


class FotoDescarte(models.Model):
    inspeccion = models.OneToOneField(
        Inspeccion, related_name="foto", on_delete=models.CASCADE
    )
    imagen = models.ImageField(upload_to=ruta_foto_descarte)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Foto de la inspeccion #%s" % self.inspeccion_id


class ComandoFaja(models.Model):
    """
    Cola chica de comandos START/STOP/RESET desde el dashboard hacia el
    Arduino. El frontend crea filas (POST /api/comandos/); vision/ las
    consume por polling (GET /api/comandos/siguiente/, ver
    telemetria_cliente.py -> ClienteComandos) y escribe la letra al puerto
    serie. Queda guardado en la base (no en memoria) para que funcione igual
    con uno o varios procesos del backend.
    """

    START = "START"
    STOP = "STOP"
    RESET = "RESET"
    ACCION_CHOICES = [(START, "Start"), (STOP, "Stop"), (RESET, "Reset")]

    accion = models.CharField(max_length=10, choices=ACCION_CHOICES)
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    consumido_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["creado_en"]
        indexes = [models.Index(fields=["consumido_en", "creado_en"])]

    def __str__(self):
        return "%s (%s)" % (self.accion, "consumido" if self.consumido_en else "pendiente")
