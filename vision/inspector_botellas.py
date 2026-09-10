# -*- coding: utf-8 -*-
"""
inspector_botellas.py  ---  Programa principal de vision de la faja.

Ciclo:
  1. El Arduino manda 'B' cuando hay una botella detenida frente a la camara.
  2. Se toma el cuadro, se recorta la ROI y se clasifica con el modelo YOLO.
  3. Se le responde al Arduino con 'A' (aceptada) / 'D' (defectuosa) / 'L' (nivel de agua).

Necesita el modelo best.pt (ver clasificador.py: va en vision/best.pt).

Uso:
  python inspector_botellas.py                 # con Arduino (autodetecta el COM)
  python inspector_botellas.py --sin-arduino   # sin hardware: ESPACIO simula una botella
  python inspector_botellas.py --calibrar      # muestra las confianzas del modelo en vivo
  python inspector_botellas.py --guardar       # guarda cada captura en capturas/ (para reentrenar)
  python inspector_botellas.py --listar-camaras # lista las camaras conectadas y sale
  python inspector_botellas.py --modelo C:\ruta\best.pt --puerto COM4 --camara 1

Teclas en la ventana:  q salir   c calibrar on/off   r reset contadores
                       s guardar config   0-9 cambiar de camara
                       ESPACIO inspeccionar (solo --sin-arduino)

OJO: un solo programa a la vez puede abrir el COM. Cerra el Monitor Serie del
Arduino IDE antes de correr esto.
"""

import argparse
import os
import sys
import time
from datetime import datetime

import cv2
import numpy as np  # noqa: F401  (lo usan helpers al crecer)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clasificador import (cargar_config, guardar_config, clasificar,
                          dibujar_diagnostico, cargar_modelo, ruta_modelo)

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

AQUI = os.path.dirname(os.path.abspath(__file__))


def _abrir(idx):
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(idx)
    else:
        cap = cv2.VideoCapture(idx)
    return cap


def abrir_camara(cfg):
    cap = _abrir(int(cfg["camara"]["indice"]))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg["camara"]["ancho"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg["camara"]["alto"])
    if not cfg["camara"].get("autoexposicion", False):
        # 0.25 = manual en muchos drivers de Windows; puede fallar en silencio
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, float(cfg["camara"]["exposicion"]))
    return cap


def _log_cv(silencioso):
    """Baja/sube el nivel de log de OpenCV (el sondeo de camaras es ruidoso)."""
    try:
        lg = cv2.utils.logging
        lg.setLogLevel(lg.LOG_LEVEL_SILENT if silencioso else lg.LOG_LEVEL_WARNING)
    except Exception:  # noqa: BLE001
        pass


def listar_camaras(maxn=8):
    """Prueba los indices 0..maxn-1 y muestra cuales entregan imagen."""
    print("Buscando camaras (indices 0..%d)..." % (maxn - 1))
    _log_cv(True)
    hay, fallos = [], 0
    for i in range(maxn):
        cap = _abrir(i)
        abre = cap.isOpened()
        r, f = cap.read() if abre else (False, None)
        cap.release()
        if r and f is not None:
            h, w = f.shape[:2]
            print("  camara %d :  %dx%d" % (i, w, h))
            hay.append(i)
            fallos = 0
        else:
            if abre:
                print("  camara %d :  abre pero no entrega imagen" % i)
            fallos += 1
            if fallos >= 3 and hay:      # ya no vienen mas
                break
    _log_cv(False)
    if hay:
        print("\nElegi con  --camara N  (o las teclas 0-9 en la ventana). "
              "Ej: --camara %d" % hay[0])
    else:
        print("  no se encontro ninguna camara.")
    return hay


def detectar_puerto(cfg):
    p = cfg["serial"].get("puerto", "AUTO")
    if p and p != "AUTO":
        return p
    if list_ports is None:
        return None
    puertos = list(list_ports.comports())
    for info in puertos:
        txt = ((info.description or "") + " " + (info.manufacturer or "")).lower()
        if any(k in txt for k in ("ch340", "arduino", "usb serial", "wch", "usb-serial")):
            return info.device
    return puertos[0].device if puertos else None


def recortar_roi(frame, cfg):
    x, y, w, h = (cfg.get("roi") or [0, 0, 0, 0])[:4]
    if w > 0 and h > 0:
        return frame[y:y + h, x:x + w].copy()
    return frame


def poner_texto(img, txt, x, y):
    cv2.putText(img, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser(description="Inspector de botellas de la faja clasificadora")
    ap.add_argument("--sin-arduino", action="store_true",
                    help="no usar puerto serie; ESPACIO simula una botella")
    ap.add_argument("--calibrar", action="store_true",
                    help="modo calibracion: muestra metricas, no responde al Arduino, guarda config al salir")
    ap.add_argument("--guardar", nargs="?", const="__cfg__", default=None, metavar="CARPETA",
                    help="guardar cada captura (por defecto la carpeta de config.json)")
    ap.add_argument("--puerto", default=None, help="forzar puerto serie, ej: COM3")
    ap.add_argument("--camara", type=int, default=None, help="forzar indice de camara")
    ap.add_argument("--listar-camaras", action="store_true",
                    help="listar las camaras conectadas y salir")
    ap.add_argument("--config", default=os.path.join(AQUI, "config.json"))
    ap.add_argument("--modelo", default=None, help="ruta a best.pt (def: vision/best.pt)")
    ap.add_argument("--sin-ventana", action="store_true",
                    help="no abrir ventana (PC sin entorno grafico)")
    args = ap.parse_args()

    if args.listar_camaras:
        return 0 if listar_camaras() else 2

    cfg = cargar_config(args.config)
    if args.camara is not None:
        cfg["camara"]["indice"] = args.camara
    if args.puerto:
        cfg["serial"]["puerto"] = args.puerto
    if args.modelo:
        cfg["modelo"]["ruta"] = args.modelo

    # ---- modelo YOLO (se carga una vez; sin el no se puede clasificar) ----
    try:
        modelo = cargar_modelo(cfg)
    except (FileNotFoundError, ImportError) as e:
        print(e, file=sys.stderr)
        return 2
    print("modelo: %s" % ruta_modelo(cfg))
    print("clases: %s" % list(modelo.names.values()))

    guardar_dir = None
    if args.guardar is not None:
        d = cfg.get("guardar_dir", "capturas") if args.guardar == "__cfg__" else args.guardar
        guardar_dir = d if os.path.isabs(d) else os.path.join(AQUI, d)
        os.makedirs(guardar_dir, exist_ok=True)
        print("guardando capturas en:", guardar_dir)

    # ---- puerto serie ----
    ser = None
    if not args.sin_arduino:
        if serial is None:
            print("pyserial no esta instalado. Usa --sin-arduino o 'pip install -r requirements.txt'",
                  file=sys.stderr)
            return 2
        puerto = detectar_puerto(cfg)
        if not puerto:
            print("no se encontro ningun puerto serie. Conecta el Arduino o usa --sin-arduino",
                  file=sys.stderr)
            return 2
        try:
            ser = serial.Serial(puerto, int(cfg["serial"]["baudios"]), timeout=0)
        except serial.SerialException as e:
            print("no se pudo abrir %s: %s" % (puerto, e), file=sys.stderr)
            texto = str(e).lower()
            if "deneg" in texto or "denied" in texto or "permission" in texto or "access" in texto:
                print("El puerto esta ocupado. Cerra el Monitor Serie del Arduino IDE "
                      "(o el IDE entero) y volve a intentar.", file=sys.stderr)
            print("Tambien podes usar --sin-arduino, o --puerto COMx para forzar otro.",
                  file=sys.stderr)
            return 2
        time.sleep(2.0)            # el UNO se reinicia al abrir el puerto
        ser.reset_input_buffer()
        print("Arduino en %s @ %s baudios" % (puerto, cfg["serial"]["baudios"]))

    # ---- camara ----
    cap = abrir_camara(cfg)
    if not cap or not cap.isOpened():
        print("no se pudo abrir la camara (indice %s)" % cfg["camara"]["indice"], file=sys.stderr)
        listar_camaras()
        if ser is not None:
            ser.close()
        return 2

    cont = {"A": 0, "D": 0, "L": 0}
    ultimo = "-"
    fallos_serie = 0
    ventana = not args.sin_ventana
    if ventana:
        try:
            cv2.namedWindow("inspector", cv2.WINDOW_NORMAL)
        except cv2.error:
            ventana = False

    print("Teclas: [q] salir  [c] calibrar  [r] reset  [s] guardar config  "
          "[0-9] cambiar camara  [ESPACIO] inspeccionar (sin-arduino)")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("camara sin senal, reintentando...")
                time.sleep(0.2)
                continue
            roi = recortar_roi(frame, cfg)
            disparar = False

            # --- senal del Arduino: cualquier byte 'B' dispara inspeccion ---
            if ser is not None:
                try:
                    data = ser.read(256)
                except serial.SerialException as e:
                    # el CH340 en Windows a veces "pierde" el puerto un instante
                    fallos_serie += 1
                    print("aviso: fallo de lectura serie (%d): %s" % (fallos_serie, e))
                    try:
                        ser.close()
                        time.sleep(0.5)
                        ser.open()
                        ser.reset_input_buffer()
                        print("puerto %s reabierto" % puerto)
                    except serial.SerialException:
                        pass
                    if fallos_serie >= 5:
                        print("demasiados fallos de %s. Cerra el Arduino IDE (queda tomando "
                              "el puerto) y volve a correr esto." % puerto, file=sys.stderr)
                        return 2
                    time.sleep(0.2)
                    continue
                if data:
                    fallos_serie = 0
                    if b"B" in data:
                        disparar = True
                    for linea in data.split(b"\n"):
                        s = linea.strip().decode("ascii", "ignore")
                        if s.startswith("#"):
                            print("  arduino:", s)

            # --- ventana / teclado ---
            if ventana:
                cam_i = int(cfg["camara"]["indice"])
                if args.calibrar:
                    res = clasificar(roi, cfg, modelo)
                    vis = dibujar_diagnostico(roi, res, cfg)
                    poner_texto(vis, "CALIBRAR  cam:%d  %s  %s"
                                % (cam_i, res["codigo"], res["etiqueta"]), 10, 24)
                    yy = 46
                    for k, v in res["metricas"].items():
                        txt = ("%s: %.1f" % (k, v)) if isinstance(v, float) else ("%s: %s" % (k, v))
                        poner_texto(vis, txt, 10, yy)
                        yy += 18
                    cv2.imshow("inspector", vis)
                else:
                    vis = roi.copy()
                    poner_texto(vis, "cam:%d   A:%d  D:%d  L:%d   ultimo: %s"
                                % (cam_i, cont["A"], cont["D"], cont["L"], ultimo), 10, 24)
                    cv2.imshow("inspector", vis)

                k = cv2.waitKey(1) & 0xFF
                if k == ord("q"):
                    break
                elif k == ord("c"):
                    args.calibrar = not args.calibrar
                elif k == ord("r"):
                    cont = {"A": 0, "D": 0, "L": 0}
                elif k == ord("s"):
                    guardar_config(cfg, args.config)
                    print("config guardada en", args.config)
                elif ord("0") <= k <= ord("9"):
                    nuevo = k - ord("0")
                    if nuevo != int(cfg["camara"]["indice"]):
                        anterior = int(cfg["camara"]["indice"])
                        cfg["camara"]["indice"] = nuevo
                        cap.release()
                        _log_cv(True)
                        cap = abrir_camara(cfg)
                        vale, _ = cap.read()
                        _log_cv(False)
                        if not vale:
                            print("camara %d no disponible; sigo con la %d" % (nuevo, anterior))
                            cap.release()
                            cfg["camara"]["indice"] = anterior
                            cap = abrir_camara(cfg)
                        else:
                            print("camara -> %d" % nuevo)
                elif k == ord(" ") and args.sin_arduino:
                    disparar = True
            else:
                time.sleep(0.01)

            # --- inspeccion ---
            if disparar and not args.calibrar:
                res = clasificar(roi, cfg, modelo)
                cod = "A" if res["codigo"] == "N" else res["codigo"]
                if ser is not None:
                    try:
                        ser.write(cod.encode("ascii"))
                    except serial.SerialException as e:
                        print("aviso: no se pudo enviar '%s' al Arduino: %s" % (cod, e))
                cont[cod] = cont.get(cod, 0) + 1
                ultimo = "%s %s" % (cod, res["etiqueta"])
                print("%s  ->  %s  %s  (%s)"
                      % (datetime.now().strftime("%H:%M:%S"), cod, res["etiqueta"], res["detalle"]))
                if guardar_dir:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                    cv2.imwrite(os.path.join(guardar_dir, "%s_%s_%s.png"
                                             % (ts, cod, res["etiqueta"])), roi)
    finally:
        cap.release()
        if ser is not None:
            ser.close()
        if ventana:
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass

    if args.calibrar:
        guardar_config(cfg, args.config)
        print("config guardada al salir:", args.config)
    print("contadores:", cont)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
