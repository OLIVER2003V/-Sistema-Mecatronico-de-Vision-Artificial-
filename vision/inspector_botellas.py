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
  python inspector_botellas.py --modelo C:\ruta\best.pt --puerto COM4 --camara 1

Teclas en la ventana:  q salir   c calibrar on/off   r reset contadores
                       s guardar config   ESPACIO inspeccionar (solo --sin-arduino)

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


def abrir_camara(cfg):
    idx = int(cfg["camara"]["indice"])
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(idx)
    else:
        cap = cv2.VideoCapture(idx)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg["camara"]["ancho"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg["camara"]["alto"])
    if not cfg["camara"].get("autoexposicion", False):
        # 0.25 = manual en muchos drivers de Windows; puede fallar en silencio
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, float(cfg["camara"]["exposicion"]))
    return cap


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
    ap.add_argument("--config", default=os.path.join(AQUI, "config.json"))
    ap.add_argument("--modelo", default=None, help="ruta a best.pt (def: vision/best.pt)")
    ap.add_argument("--sin-ventana", action="store_true",
                    help="no abrir ventana (PC sin entorno grafico)")
    args = ap.parse_args()

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
        ser = serial.Serial(puerto, int(cfg["serial"]["baudios"]), timeout=0)
        time.sleep(2.0)            # el UNO se reinicia al abrir el puerto
        ser.reset_input_buffer()
        print("Arduino en %s @ %s baudios" % (puerto, cfg["serial"]["baudios"]))

    # ---- camara ----
    cap = abrir_camara(cfg)
    if not cap or not cap.isOpened():
        print("no se pudo abrir la camara (indice %s)" % cfg["camara"]["indice"], file=sys.stderr)
        if ser is not None:
            ser.close()
        return 2

    cont = {"A": 0, "D": 0, "L": 0}
    ultimo = "-"
    ventana = not args.sin_ventana
    if ventana:
        try:
            cv2.namedWindow("inspector", cv2.WINDOW_NORMAL)
        except cv2.error:
            ventana = False

    print("Teclas: [q] salir  [c] calibrar  [r] reset  [s] guardar config  "
          "[ESPACIO] inspeccionar (sin-arduino)")
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
                data = ser.read(256)
                if data:
                    if b"B" in data:
                        disparar = True
                    for linea in data.split(b"\n"):
                        s = linea.strip().decode("ascii", "ignore")
                        if s.startswith("#"):
                            print("  arduino:", s)

            # --- ventana / teclado ---
            if ventana:
                if args.calibrar:
                    res = clasificar(roi, cfg, modelo)
                    vis = dibujar_diagnostico(roi, res, cfg)
                    poner_texto(vis, "CALIBRAR  %s  %s" % (res["codigo"], res["etiqueta"]), 10, 24)
                    yy = 46
                    for k, v in res["metricas"].items():
                        txt = ("%s: %.1f" % (k, v)) if isinstance(v, float) else ("%s: %s" % (k, v))
                        poner_texto(vis, txt, 10, yy)
                        yy += 18
                    cv2.imshow("inspector", vis)
                else:
                    vis = roi.copy()
                    poner_texto(vis, "A:%d  D:%d  L:%d   ultimo: %s"
                                % (cont["A"], cont["D"], cont["L"], ultimo), 10, 24)
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
                elif k == ord(" ") and args.sin_arduino:
                    disparar = True
            else:
                time.sleep(0.01)

            # --- inspeccion ---
            if disparar and not args.calibrar:
                res = clasificar(roi, cfg, modelo)
                cod = "A" if res["codigo"] == "N" else res["codigo"]
                if ser is not None:
                    ser.write(cod.encode("ascii"))
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
