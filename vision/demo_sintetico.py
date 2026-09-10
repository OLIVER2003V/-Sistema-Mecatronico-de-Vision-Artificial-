# -*- coding: utf-8 -*-
"""
demo_sintetico.py  ---  Prueba la logica de vision SIN camara ni Arduino.

Dibuja 8 botellas sinteticas a contraluz (una por tipo), las pasa por
clasificador.clasificar() y arma un mosaico 2x4 con el resultado.
Borde verde = coincide con lo esperado ; borde rojo = falla.

    python demo_sintetico.py               # abre ventana + guarda demo_resultado.png
    python demo_sintetico.py --sin-ventana # solo guarda la imagen

Sirve como prueba de humo: si el mosaico sale casi todo verde, el pipeline
esta bien instalado. Los umbrales finos se ajustan luego con fotos reales
(inspector_botellas.py --calibrar).
"""

import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clasificador import clasificar, cargar_config

FONDO = 245     # fondo iluminado (contraluz)
VIDRIO = 150    # cuerpo de la botella
ETIQUETA = 60   # papel: bloquea mas luz
TAPA = 45       # tapa opaca

W, H = 300, 520


def _lienzo():
    return np.full((H, W), FONDO, np.uint8)


def _cuerpo(img, cx, cuerpo_w, top, bot):
    x0, x1 = cx - cuerpo_w // 2, cx + cuerpo_w // 2
    cv2.rectangle(img, (x0, top + 40), (x1, bot), VIDRIO, -1)
    cv2.ellipse(img, (cx, top + 40), (cuerpo_w // 2, 40), 0, 180, 360, VIDRIO, -1)  # hombro
    cv2.ellipse(img, (cx, bot), (cuerpo_w // 2, 18), 0, 0, 180, VIDRIO, -1)          # base


def _cuello_tapa(img, cx, top, con_tapa=True):
    cv2.rectangle(img, (cx - 15, top + 8), (cx + 15, top + 44), VIDRIO, -1)   # cuello
    if con_tapa:
        cv2.rectangle(img, (cx - 26, top - 14), (cx + 26, top + 12), TAPA, -1)  # tapa ancha
        cv2.ellipse(img, (cx, top - 14), (26, 8), 0, 180, 360, TAPA, -1)


def _etiqueta(img, cx, cuerpo_w, y0, y1, angulo=0.0, dx=0, recorte=0.0):
    cap = np.zeros((H, W), np.uint8)
    x0, x1 = cx - int(cuerpo_w * 0.44), cx + int(cuerpo_w * 0.44)
    cv2.rectangle(cap, (x0, y0), (x1, y1), 255, -1)
    if recorte > 0:                       # rasgadura: sacar una franja del medio
        ry0 = y0 + int((y1 - y0) * 0.38)
        ry1 = y0 + int((y1 - y0) * 0.62)
        cv2.rectangle(cap, (x0 - 5, ry0), (x1 + 5, ry1), 0, -1)
    if angulo != 0.0 or dx != 0:
        M = cv2.getRotationMatrix2D((float(cx), (y0 + y1) / 2.0), angulo, 1.0)
        M[0, 2] += dx
        cap = cv2.warpAffine(cap, M, (W, H))
    img[cap > 0] = ETIQUETA


def generar(tipo):
    img = _lienzo()
    cx, cuerpo_w = W // 2, 135
    top, bot = 120, 470
    if tipo == "aplastada":
        top = int(bot - (bot - top) * 0.52)     # mucho mas baja

    _cuerpo(img, cx, cuerpo_w, top, bot)
    _cuello_tapa(img, cx, top, con_tapa=(tipo != "sin_tapa"))

    if tipo == "abollada":
        # muesca localizada en el lado derecho del cuerpo (unos 35 px de fondo)
        pts = np.array([[cx + 80, 288], [cx + 32, 305], [cx + 80, 322]], np.int32)
        cv2.fillPoly(img, [pts], FONDO)

    y0 = top + int((bot - top) * 0.42)
    y1 = top + int((bot - top) * 0.63)
    if tipo == "sin_etiqueta":
        pass
    elif tipo == "etiqueta_torcida":
        _etiqueta(img, cx, cuerpo_w, y0, y1, angulo=14.0, dx=10)
    elif tipo == "etiqueta_rota":
        _etiqueta(img, cx, cuerpo_w, y0, y1, recorte=0.5)
    else:
        _etiqueta(img, cx, cuerpo_w, y0, y1)

    img = cv2.GaussianBlur(img, (3, 3), 0)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


CASOS = [
    ("buena", "A"),
    ("buena", "A"),
    ("sin_etiqueta", "E"),
    ("etiqueta_torcida", "E"),
    ("etiqueta_rota", "E"),
    ("abollada", "D"),
    ("sin_tapa", "D"),
    ("aplastada", "D"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-ventana", action="store_true")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     "config.json"))
    args = ap.parse_args()
    cfg = cargar_config(args.config)

    tiles, aciertos = [], 0
    print("  # | tipo             | esperado | obtenido | etiqueta")
    print("----+------------------+----------+----------+---------------------")
    for i, (tipo, esp) in enumerate(CASOS):
        bgr = generar(tipo)
        res = clasificar(bgr, cfg)
        cod = "A" if res["codigo"] == "N" else res["codigo"]
        ok = (cod == esp)
        aciertos += int(ok)
        print("  %d | %-16s | %-8s | %-8s | %s%s"
              % (i, tipo, esp, cod, res["etiqueta"], "" if ok else "   <== FALLA"))
        borde = (0, 170, 0) if ok else (0, 0, 220)
        t = cv2.copyMakeBorder(bgr, 6, 30, 6, 6, cv2.BORDER_CONSTANT, value=borde)
        cv2.putText(t, "esp %s / obt %s" % (esp, cod), (10, t.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(t)

    mosaico = np.vstack([np.hstack(tiles[:4]), np.hstack(tiles[4:])])
    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_resultado.png")
    cv2.imwrite(salida, mosaico)
    print("\naciertos: %d/8     imagen: %s" % (aciertos, salida))

    if not args.sin_ventana:
        try:
            cv2.imshow("demo", mosaico)
            print("tecla sobre la ventana para cerrar...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        except cv2.error:
            print("(sin entorno grafico: abri demo_resultado.png)")


if __name__ == "__main__":
    main()
