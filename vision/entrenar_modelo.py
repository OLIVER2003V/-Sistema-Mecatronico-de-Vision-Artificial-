# -*- coding: utf-8 -*-
"""
entrenar_modelo.py  ---  Ayudas para el modelo YOLO (best.pt).

Ya usas un modelo entrenado (Ultralytics YOLO). Este archivo tiene dos cosas:

  1. --eval : corre best.pt sobre las capturas de  vision/capturas/  y compara
              el veredicto con el codigo que quedo en el nombre del archivo
              (AAAAMMDD_HHMMSS_mmm_<COD>_<detalle>.png ; COD = A / D / L).
              Sirve para medir cuanto acierta con TUS fotos.

  2. Abajo, como referencia, el comando para RE-entrenar con Ultralytics si
     sumas mas fotos etiquetadas.

    python entrenar_modelo.py --eval
    python entrenar_modelo.py --eval --carpeta capturas
"""

import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

AQUI = os.path.dirname(os.path.abspath(__file__))
CODIGOS = ("A", "D", "L", "N")


def cargar_dataset(carpeta):
    """Devuelve [(ruta, cod_esperado), ...] leyendo el COD del nombre de archivo."""
    pares = []
    for r in sorted(glob.glob(os.path.join(carpeta, "*.png")) +
                    glob.glob(os.path.join(carpeta, "*.jpg"))):
        partes = os.path.basename(r).split("_")
        cod = next((p for p in partes if p in CODIGOS), None)
        if cod:
            pares.append((r, cod))
    return pares


def evaluar(carpeta, config):
    import cv2
    from clasificador import clasificar, cargar_config, cargar_modelo

    cfg = cargar_config(config)
    cargar_modelo(cfg)                      # lanza si falta best.pt o ultralytics

    pares = cargar_dataset(carpeta)
    if not pares:
        print("no hay capturas con codigo en el nombre en:", carpeta)
        print("Genera algunas con:  python inspector_botellas.py --guardar")
        return

    conf = {e: {o: 0 for o in CODIGOS} for e in CODIGOS}
    ok = 0
    for ruta, esp in pares:
        img = cv2.imread(ruta)
        if img is None:
            continue
        obt = clasificar(img, cfg)["codigo"]
        conf[esp][obt] = conf[esp].get(obt, 0) + 1
        ok += int(obt == esp)

    n = len(pares)
    print("\n%d capturas   aciertos: %d/%d  (%.1f%%)\n" % (n, ok, n, 100.0 * ok / max(n, 1)))
    print("            obtenido")
    print("esper |  " + "  ".join("%3s" % c for c in CODIGOS))
    print("------+-" + "-" * (5 * len(CODIGOS)))
    for e in CODIGOS:
        print("  %3s | " % e + "  ".join("%3d" % conf[e][o] for o in CODIGOS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", action="store_true", help="medir best.pt contra vision/capturas/")
    ap.add_argument("--carpeta", default=os.path.join(AQUI, "capturas"))
    ap.add_argument("--config", default=os.path.join(AQUI, "config.json"))
    a = ap.parse_args()

    if a.eval:
        evaluar(a.carpeta, a.config)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()

# ==========================================================================
# RE-ENTRENAR con Ultralytics (solo si sumas mas fotos etiquetadas)
# --------------------------------------------------------------------------
# 1. Etiqueta las fotos (cajas) con Roboflow o LabelImg. Clases EXACTAS:
#       Agua  Botella  Etiqueta  Notapa  Rota  Tapa
# 2. Exporta en formato "YOLOv8" -> queda un data.yaml con train/ y val/.
# 3. En Google Colab (GPU gratis):
#
#       pip install ultralytics
#       yolo detect train model=yolov8n.pt data=data.yaml epochs=80 imgsz=640
#
#    (o  model=best.pt  para seguir entrenando el que ya tienes)
# 4. El mejor queda en  runs/detect/train/weights/best.pt . Copialo a
#    vision/best.pt  y listo, el inspector lo toma solo.
# ==========================================================================
