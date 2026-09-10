# -*- coding: utf-8 -*-
"""
probar_modelo.py  ---  Corre best.pt sobre imagenes sueltas (sin camara ni Arduino).

Pone algunas fotos de botellas en  vision/muestras/  (o usa --carpeta) y:

    python probar_modelo.py

Imprime el veredicto A / D / L de cada imagen (con las confianzas por clase) y
guarda un mosaico anotado en  resultado_modelo.png . Sirve para comprobar que
el modelo carga y que la regla de decision hace lo que esperas ANTES de
conectar el hardware.

    A = aceptada     D = defectuosa (Rota/Notapa/falta etiqueta o tapa)
    L = nivel de agua bajo      N = el modelo no ve una botella
"""

import argparse
import glob
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clasificador import (clasificar, cargar_config, cargar_modelo,
                          dibujar_diagnostico, ruta_modelo)

AQUI = os.path.dirname(os.path.abspath(__file__))
EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


def _mosaico(tiles, por_fila=4):
    alto = max(t.shape[0] for t in tiles)
    ancho = max(t.shape[1] for t in tiles)
    norm = []
    for t in tiles:
        t = cv2.copyMakeBorder(t, 0, alto - t.shape[0], 0, ancho - t.shape[1],
                               cv2.BORDER_CONSTANT, value=(30, 30, 30))
        norm.append(t)
    filas = []
    for i in range(0, len(norm), por_fila):
        fila = norm[i:i + por_fila]
        while len(fila) < por_fila:
            fila.append(np.full_like(norm[0], 30))
        filas.append(np.hstack(fila))
    return np.vstack(filas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--carpeta", default=None,
                    help="carpeta con imagenes (def: muestras/ y si no capturas/)")
    ap.add_argument("--modelo", default=None, help="ruta a best.pt")
    ap.add_argument("--config", default=os.path.join(AQUI, "config.json"))
    ap.add_argument("--sin-ventana", action="store_true")
    args = ap.parse_args()

    cfg = cargar_config(args.config)
    if args.modelo:
        cfg["modelo"]["ruta"] = args.modelo
    try:
        cargar_modelo(cfg)
    except (FileNotFoundError, ImportError) as e:
        print(e, file=sys.stderr)
        return 2

    carpeta = args.carpeta
    if not carpeta:
        for cand in ("muestras", "capturas"):
            p = os.path.join(AQUI, cand)
            if os.path.isdir(p) and any(f.lower().endswith(EXTS) for f in os.listdir(p)):
                carpeta = p
                break
    if not carpeta or not os.path.isdir(carpeta):
        print("No hay imagenes para probar. Copia algunas fotos de botellas en\n  %s\n"
              "y volve a correr  python probar_modelo.py" % os.path.join(AQUI, "muestras"))
        return 1

    rutas = sorted(r for r in glob.glob(os.path.join(carpeta, "*"))
                   if r.lower().endswith(EXTS))
    if not rutas:
        print("la carpeta %s no tiene imagenes %s" % (carpeta, list(EXTS)))
        return 1

    print("modelo :", ruta_modelo(cfg))
    print("carpeta:", carpeta)
    print("-" * 68)
    tiles, cont = [], {}
    for r in rutas:
        img = cv2.imread(r)
        if img is None:
            print("  no pude leer", os.path.basename(r))
            continue
        res = clasificar(img, cfg)
        cod = res["codigo"]
        cont[cod] = cont.get(cod, 0) + 1
        confs = " ".join("%s=%.2f" % (k.replace("conf_", ""), v)
                         for k, v in res["metricas"].items()
                         if k.startswith("conf_") or k == "nivel_llenado")
        print("  %-28s -> %s  %-14s | %s" % (os.path.basename(r)[:28], cod,
                                             res["etiqueta"], confs))
        vis = dibujar_diagnostico(img, res, cfg)
        esc = 360.0 / max(vis.shape[1], 1)
        vis = cv2.resize(vis, (int(vis.shape[1] * esc), int(vis.shape[0] * esc)))
        for grosor, color in ((3, (0, 0, 0)), (1, (255, 255, 255))):
            cv2.putText(vis, "%s  %s" % (cod, res["etiqueta"]), (8, vis.shape[0] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, grosor, cv2.LINE_AA)
        tiles.append(vis)
    print("-" * 68)
    print("resumen:", cont)

    if tiles:
        salida = os.path.join(AQUI, "resultado_modelo.png")
        cv2.imwrite(salida, _mosaico(tiles))
        print("mosaico:", salida)
        if not args.sin_ventana:
            try:
                cv2.imshow("probar_modelo", cv2.imread(salida))
                print("tecla sobre la ventana para cerrar...")
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            except cv2.error:
                print("(sin entorno grafico: abri resultado_modelo.png)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
