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
TAPA = 52       # tapa opaca

W, H = 300, 540

# Distribucion vertical de la botella "sana" (en pixeles).
Y_TAPA_TOP = 70
Y_TAPA_BOT = 96
Y_CUELLO_BOT = 138
Y_HOMBRO_BOT = 184
Y_CUERPO_BOT = 470
BODY_W = 135
NECK_W = 30
CAP_W = 52


def _poner_etiqueta(img, cx, y0, y1, angulo=0.0, dx=0, rasgar=False):
    lab = np.zeros(img.shape[:2], np.uint8)
    x0, x1 = cx - int(BODY_W * 0.42), cx + int(BODY_W * 0.42)
    cv2.rectangle(lab, (x0, y0), (x1, y1), 255, -1)
    if rasgar:                                  # sacar una franja del medio
        ry0 = y0 + int((y1 - y0) * 0.40)
        ry1 = y0 + int((y1 - y0) * 0.60)
        cv2.rectangle(lab, (x0 - 6, ry0), (x1 + 6, ry1), 0, -1)
    if angulo != 0.0 or dx != 0:
        M = cv2.getRotationMatrix2D((float(cx), (y0 + y1) / 2.0), angulo, 1.0)
        M[0, 2] += dx
        lab = cv2.warpAffine(lab, M, (img.shape[1], img.shape[0]))
    # recortar la etiqueta al cuerpo: solo pintar donde YA hay botella
    img[(lab > 0) & (img < 240)] = ETIQUETA


def generar(tipo):
    img = np.full((H, W), FONDO, np.uint8)
    cx = W // 2
    y_cuerpo_bot = Y_CUERPO_BOT if tipo != "aplastada" else 280

    # cuerpo + base redondeada
    cv2.rectangle(img, (cx - BODY_W // 2, Y_HOMBRO_BOT),
                  (cx + BODY_W // 2, y_cuerpo_bot), VIDRIO, -1)
    cv2.ellipse(img, (cx, y_cuerpo_bot), (BODY_W // 2, 16), 0, 0, 180, VIDRIO, -1)
    # hombro (trapecio del cuello al cuerpo)
    hombro = np.array([[cx - NECK_W // 2, Y_CUELLO_BOT], [cx + NECK_W // 2, Y_CUELLO_BOT],
                       [cx + BODY_W // 2, Y_HOMBRO_BOT], [cx - BODY_W // 2, Y_HOMBRO_BOT]],
                      np.int32)
    cv2.fillPoly(img, [hombro], VIDRIO)
    # cuello
    cv2.rectangle(img, (cx - NECK_W // 2, Y_TAPA_BOT), (cx + NECK_W // 2, Y_CUELLO_BOT),
                  VIDRIO, -1)
    # tapa (todas menos "sin_tapa")
    if tipo != "sin_tapa":
        cv2.rectangle(img, (cx - CAP_W // 2, Y_TAPA_TOP), (cx + CAP_W // 2, Y_TAPA_BOT),
                      TAPA, -1)

    # etiqueta
    y0 = Y_HOMBRO_BOT + int((y_cuerpo_bot - Y_HOMBRO_BOT) * 0.30)
    y1 = Y_HOMBRO_BOT + int((y_cuerpo_bot - Y_HOMBRO_BOT) * 0.62)
    if tipo == "sin_etiqueta":
        pass
    elif tipo == "etiqueta_torcida":
        _poner_etiqueta(img, cx, y0, y1, angulo=16.0, dx=8)
    elif tipo == "etiqueta_rota":
        _poner_etiqueta(img, cx, y0, y1, rasgar=True)
    else:
        _poner_etiqueta(img, cx, y0, y1)

    # abolladura: DESPUES de la etiqueta, muerde cuerpo y etiqueta a la vez
    if tipo == "abollada":
        yc = Y_HOMBRO_BOT + int((y_cuerpo_bot - Y_HOMBRO_BOT) * 0.32)
        pts = np.array([[cx + BODY_W // 2 + 12, yc - 22],
                        [cx + BODY_W // 2 - 42, yc + 2],
                        [cx + BODY_W // 2 + 12, yc + 26]], np.int32)
        cv2.fillPoly(img, [pts], FONDO)

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
