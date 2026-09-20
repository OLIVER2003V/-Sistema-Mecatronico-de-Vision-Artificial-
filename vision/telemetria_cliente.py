# -*- coding: utf-8 -*-
"""
telemetria_cliente.py  ---  Puente entre el lazo de vision y el backend
SORT-MATIC (Django), SIN frenar nunca el lazo de OpenCV/YOLO.

Regla de oro de todo este archivo: el veredicto ya se le mando al Arduino por
el puerto serie ANTES de hablar con el backend. Si el backend esta caido,
lento o inalcanzable, la faja sigue clasificando botellas igual. Por eso
todos los clientes de aca:

  * trabajan en un hilo aparte (daemon),
  * descartan datos antes que acumular sin limite,
  * atrapan los errores de red y como mucho imprimen un aviso.

Clientes disponibles
--------------------
    ClienteTelemetria    manda cada botella procesada (+ la foto si fue merma)
    ClienteComandos      trae los START/STOP/RESET que salen del dashboard
    ClienteCamara        manda un JPEG chico cada tanto para la vista en vivo
    ClienteConfiguracion trae los umbrales que edita el Supervisor de calidad
                         y los aplica EN CALIENTE (sin reiniciar la inspeccion)
    ClienteEstadoFaja    reporta marcha/paro real para el panel SCADA

Autenticacion
-------------
El modulo de vision no tiene usuario: se identifica con una clave estatica en
la cabecera X-API-Key. Tiene que coincidir con VISION_API_KEY del backend.
Se configura en config.json -> backend.api_key (o en la variable de entorno
SORTMATIC_API_KEY, que tiene prioridad para no dejar la clave en un archivo).

Config (config.json -> "backend"):
    {
      "url": "http://localhost:8000/api/telemetria/",
      "api_key": "...",
      "activo": true,
      "enviar_fotos": true
    }
"""

import os
import queue
import threading
import time

try:
    import requests
except ImportError:
    requests = None

try:
    import cv2
except ImportError:
    cv2 = None

_TAM_COLA = 100
_TIMEOUT_S = 2.0
CABECERA_CLAVE = "X-API-Key"

# cod (A/D/L, lo que ya viaja por el puerto serie) -> lo que espera el backend
_MAP_RESULTADO = {"A": "ACEPTADA", "D": "DEFECTUOSA", "L": "LLENADO_BAJO"}
_MAP_ESTACION = {"D": "ESTACION_1", "L": "ESTACION_2"}
# etiqueta de clasificador.py -> tipo_defecto del backend (ver Inspeccion.TIPO_DEFECTO_CHOICES)
_MAP_DEFECTO = {
    "falta_etiqueta": "SIN_ETIQUETA",
    "falta_tapa": "SIN_TAPA",
    "sin_tapa": "SIN_TAPA",
    "rota": "OTRO",
}

# Claves que el backend tiene permitido pisar en config["modelo"]. La ruta de
# best.pt NO esta: es un detalle de esta PC, no algo que decida el dashboard.
CLAVES_MODELO = (
    "conf_ok",
    "conf_ok_tapa",
    "conf_detectar",
    "conf_defecto",
    "nivel_min",
    "cuello_frac",
    "imgsz",
    "dispositivo",
)


def clave_api(cfg_backend):
    """
    La variable de entorno SORTMATIC_API_KEY / VISION_API_KEY o del archivo .env gana:
    permite no escribir la clave secreta en config.json para evitar subir credenciales a repositorios.
    """
    env_key = os.environ.get("SORTMATIC_API_KEY") or os.environ.get("VISION_API_KEY")
    if env_key:
        return env_key

    # Si se pasa un diccionario con api_key explícita (como en config.json o en unit tests)
    if isinstance(cfg_backend, dict) and "api_key" in cfg_backend:
        key = cfg_backend["api_key"]
        if key and key != "CONFIGURAR_EN_ENV":
            return key

    # Buscar SORTMATIC_API_KEY en archivo .env local si existe
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for ruta_env in (os.path.join(base_dir, ".env"), os.path.join(base_dir, "..", ".env")):
        if os.path.isfile(ruta_env):
            try:
                with open(ruta_env, "r", encoding="utf-8") as f:
                    for linea in f:
                        linea = linea.strip()
                        if linea and not linea.startswith("#") and "=" in linea:
                            k, v = linea.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k == "SORTMATIC_API_KEY" and v:
                                return v
            except Exception:
                pass

    return (cfg_backend or {}).get("api_key", "")


def payload_desde_resultado(cod, res):
    """
    Arma el dict que espera POST /api/telemetria/ a partir de lo que devuelve
    clasificador.clasificar() (res) y la letra que YA se le mando al Arduino
    (cod: 'A'/'D'/'L'; una 'N' ya se convierte en 'A' antes de este punto).
    """
    metr = res.get("metricas", {}) or {}
    nivel = metr.get("nivel_llenado", -1.0)

    datos = {
        "resultado": _MAP_RESULTADO.get(cod, "ACEPTADA"),
        "nivel_llenado_detectado": round(nivel * 100, 1) if nivel is not None and nivel >= 0 else None,
        "estacion_descarte": _MAP_ESTACION.get(cod),
    }
    if cod == "D":
        datos["tipo_defecto"] = _MAP_DEFECTO.get(res.get("etiqueta"), "OTRO")
        datos["confianza_ia"] = round(100 * max(
            metr.get("conf_etiqueta", 0.0), metr.get("conf_tapa", 0.0),
            metr.get("conf_rota", 0.0), metr.get("conf_notapa", 0.0),
        ), 1)
    else:
        datos["confianza_ia"] = round(100 * metr.get("conf_botella", 0.0), 1)

    # El backend rechaza porcentajes fuera de 0-100 y una foto sin resultado
    # perderia la botella entera; se recorta aca por si el modelo devolvio algo raro.
    for campo in ("nivel_llenado_detectado", "confianza_ia"):
        valor = datos.get(campo)
        if valor is not None:
            datos[campo] = max(0.0, min(100.0, valor))
    return datos


class _ClienteBase:
    """Sesion HTTP con la clave del dispositivo y un hilo daemon opcional."""

    def __init__(self, cfg_backend):
        self._cfg = cfg_backend or {}
        self._activo = bool(self._cfg.get("activo", True))
        self._hilo = None
        self._sesion = None

        if self._activo and requests is None:
            self._avisar_falta_requests()
            self._activo = False
            return

        if self._activo:
            self._sesion = requests.Session()
            clave = clave_api(self._cfg)
            if clave:
                self._sesion.headers[CABECERA_CLAVE] = clave

    def _avisar_falta_requests(self):
        print("aviso: falta 'requests' (pip install requests); no se hablara con el backend")

    def _arrancar(self, objetivo):
        self._hilo = threading.Thread(target=objetivo, daemon=True)
        self._hilo.start()

    def cerrar(self):
        self._activo = False


class ClienteTelemetria(_ClienteBase):
    """
    enviar() solo encola y vuelve al toque. Un hilo aparte hace los POST. Si
    el backend esta caido o la cola se llena se pierden telemetrias (no se
    acumulan sin limite), pero la faja no se entera.
    """

    def __init__(self, cfg_backend=None):
        super().__init__(cfg_backend)
        self._url = self._cfg.get("url", "http://localhost:8000/api/telemetria/")
        self._enviar_fotos = bool(self._cfg.get("enviar_fotos", True))
        self._cola = queue.Queue(maxsize=_TAM_COLA)
        self._descartadas = 0
        if self._activo:
            self._arrancar(self._bucle)

    def enviar(self, datos, imagen_bgr=None):
        """No bloquea: encola y devuelve. Si la cola esta llena, descarta (best effort)."""
        if not self._activo:
            return
        jpeg = None
        if imagen_bgr is not None and self._enviar_fotos and cv2 is not None:
            ok, buf = cv2.imencode(".jpg", imagen_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ok:
                jpeg = buf.tobytes()
        try:
            self._cola.put_nowait((datos, jpeg))
        except queue.Full:
            # Se prefiere perder una telemetria a frenar la camara. Se avisa
            # de a poco para no llenar la consola si el backend sigue caido.
            self._descartadas += 1
            if self._descartadas % 25 == 1:
                print("aviso: backend lento o caido; %d telemetrias descartadas" % self._descartadas)

    def _bucle(self):
        while True:
            datos, jpeg = self._cola.get()
            try:
                if jpeg is not None:
                    archivos = {"foto": ("captura.jpg", jpeg, "image/jpeg")}
                    respuesta = self._sesion.post(
                        self._url, data=datos, files=archivos, timeout=_TIMEOUT_S
                    )
                else:
                    respuesta = self._sesion.post(self._url, json=datos, timeout=_TIMEOUT_S)
                if respuesta.status_code == 403:
                    print("aviso: el backend rechazo la clave del dispositivo "
                          "(revisa backend.api_key / VISION_API_KEY)")
            except requests.RequestException as e:
                print("aviso: no se pudo mandar telemetria al backend (%s)" % e)


class ClienteComandos(_ClienteBase):
    """
    Pregunta cada 'intervalo_comandos_ms' si hay un START/STOP/RESET pendiente
    en el dashboard (GET .../comandos/siguiente/) y, si hay, llama a
    escribir(letra) -- normalmente algo que hace ser.write() al Arduino con
    la MISMA letra que ya entiende el firmware (S/X/R). Corre en un hilo
    aparte (daemon): no frena la camara ni el lazo de vision.
    """

    _MAP_ACCION = {"START": "S", "STOP": "X", "RESET": "R"}

    def __init__(self, cfg_backend, escribir):
        super().__init__(cfg_backend)
        self._url = self._cfg.get("url_comandos", "http://localhost:8000/api/comandos/siguiente/")
        self._intervalo = self._cfg.get("intervalo_comandos_ms", 400) / 1000.0
        self._escribir = escribir
        if self._activo:
            self._arrancar(self._bucle)

    def _avisar_falta_requests(self):
        pass  # ya lo aviso ClienteTelemetria

    def _bucle(self):
        while self._activo:
            try:
                r = self._sesion.get(self._url, timeout=_TIMEOUT_S)
                if r.ok:
                    accion = r.json().get("accion")
                    letra = self._MAP_ACCION.get(accion)
                    if letra:
                        print("#comando desde el dashboard: %s" % accion)
                        self._escribir(letra)
            except (requests.RequestException, ValueError) as e:
                print("aviso: no se pudo consultar comandos del dashboard (%s)" % e)
            time.sleep(self._intervalo)


class ClienteConfiguracion(_ClienteBase):
    """
    Trae los umbrales que el Supervisor de calidad edita en la HMI y los
    aplica EN CALIENTE sobre config["modelo"], sin reiniciar la inspeccion
    (requisito de la HU de configuracion del nivel de llenado).

    Solo pide el endpoint y compara 'version': si no cambio, no toca nada.
    Como mucho una inferencia puede usar una mezcla del valor viejo y el
    nuevo durante el instante del cambio, lo cual es inocuo.
    """

    def __init__(self, cfg_backend, cfg_modelo):
        super().__init__(cfg_backend)
        self._url = self._cfg.get(
            "url_configuracion", "http://localhost:8000/api/configuracion/vision/"
        )
        self._intervalo = self._cfg.get("intervalo_configuracion_ms", 3000) / 1000.0
        self._modelo = cfg_modelo
        self._version = None
        if self._activo:
            self._arrancar(self._bucle)

    def _avisar_falta_requests(self):
        pass

    def aplicar(self, datos):
        """Vuelca los umbrales nuevos. Devuelve True si algo cambio."""
        version = datos.get("version")
        if version is None or version == self._version:
            return False
        nuevos = {c: v for c, v in (datos.get("modelo") or {}).items() if c in CLAVES_MODELO}
        if not nuevos:
            return False
        self._modelo.update(nuevos)
        self._version = version
        return True

    def _bucle(self):
        while self._activo:
            try:
                r = self._sesion.get(self._url, timeout=_TIMEOUT_S)
                if r.ok and self.aplicar(r.json()):
                    print("#configuracion actualizada desde el dashboard: llenado min %d%%, "
                          "etiqueta %d%%" % (round(self._modelo.get("nivel_min", 0) * 100),
                                             round(self._modelo.get("conf_ok", 0) * 100)))
            except (requests.RequestException, ValueError) as e:
                print("aviso: no se pudo leer la configuracion del dashboard (%s)" % e)
            time.sleep(self._intervalo)


class ClienteEstadoFaja(_ClienteBase):
    """
    Reporta marcha/paro REAL de la faja para el panel SCADA de la HMI. Se
    llama reportar() al ver las lineas '#START' / '#STOP' que imprime el
    firmware: asi el dashboard muestra lo que pasa en la faja y no solo lo
    que se pidio desde el boton.
    """

    def __init__(self, cfg_backend):
        super().__init__(cfg_backend)
        self._url = self._cfg.get(
            "url_estado", "http://localhost:8000/api/estado-faja/reporte/"
        )
        self._cola = queue.Queue(maxsize=10)
        self._ultimo = None
        if self._activo:
            self._arrancar(self._bucle)

    def _avisar_falta_requests(self):
        pass

    def reportar(self, en_marcha, arduino_conectado=True, detalle=""):
        """No bloquea. Ignora los reportes repetidos para no golpear el backend."""
        if not self._activo:
            return
        estado = (bool(en_marcha), bool(arduino_conectado))
        if estado == self._ultimo:
            return
        self._ultimo = estado
        try:
            self._cola.put_nowait(
                {
                    "en_marcha": estado[0],
                    "arduino_conectado": estado[1],
                    "detalle": detalle[:120],
                }
            )
        except queue.Full:
            pass

    def cerrar(self, espera_s=1.0):
        """
        Espera (poco) a que salga el ultimo reporte. Sin esto, el aviso de
        'faja detenida' al cerrar el inspector se perderia casi siempre: el
        hilo es daemon y muere con el proceso.
        """
        limite = time.time() + espera_s
        while not self._cola.empty() and time.time() < limite:
            time.sleep(0.05)
        super().cerrar()

    def _bucle(self):
        while True:
            datos = self._cola.get()
            try:
                self._sesion.post(self._url, json=datos, timeout=_TIMEOUT_S)
            except requests.RequestException as e:
                print("aviso: no se pudo reportar el estado de la faja (%s)" % e)


class ClienteCamara(_ClienteBase):
    """
    Manda una foto chica (JPEG) del cuadro actual al dashboard cada
    'intervalo_camara_ms', para que se pueda ver "en vivo" (unos pocos FPS,
    no video real) sin abrir la ventana local. actualizar() solo guarda la
    referencia al ultimo cuadro (rapidisimo); el hilo aparte es el que
    redimensiona, comprime y manda -- nunca frena el lazo de camara/YOLO.
    """

    def __init__(self, cfg_backend):
        super().__init__(cfg_backend)
        self._url = self._cfg.get("url_camara", "http://localhost:8000/api/camara/frame/")
        self._intervalo = self._cfg.get("intervalo_camara_ms", 100) / 1000.0
        self._calidad = int(self._cfg.get("calidad_camara", 70))
        self._ancho_max = int(self._cfg.get("ancho_camara", 480))
        self._lock = threading.Lock()
        self._ultimo_frame = None
        self._activo = self._activo and bool(self._cfg.get("camara_activa", True))

        if self._activo and cv2 is None:
            self._activo = False
        if self._activo:
            self._arrancar(self._bucle)

    def _avisar_falta_requests(self):
        pass

    def actualizar(self, frame_bgr):
        """Llamar UNA vez por vuelta del lazo principal. No bloquea."""
        if not self._activo or frame_bgr is None:
            return
        with self._lock:
            self._ultimo_frame = frame_bgr.copy()

    def _redimensionar(self, frame):
        alto, ancho = frame.shape[:2]
        if ancho <= self._ancho_max:
            return frame
        factor = self._ancho_max / float(ancho)
        return cv2.resize(frame, (self._ancho_max, max(1, int(alto * factor))))

    def _bucle(self):
        while self._activo:
            time.sleep(self._intervalo)
            with self._lock:
                frame = self._ultimo_frame
            if frame is None:
                continue
            pequeno = self._redimensionar(frame)
            ok, buf = cv2.imencode(".jpg", pequeno, [cv2.IMWRITE_JPEG_QUALITY, self._calidad])
            if not ok:
                continue
            try:
                archivos = {"foto": ("cam.jpg", buf.tobytes(), "image/jpeg")}
                self._sesion.post(self._url, files=archivos, timeout=_TIMEOUT_S)
            except requests.RequestException:
                pass  # best-effort: no avisar cada vez, seria mucho ruido a varios FPS
