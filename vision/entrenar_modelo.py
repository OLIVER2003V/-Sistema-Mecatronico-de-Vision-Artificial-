# -*- coding: utf-8 -*-
"""
entrenar_modelo.py  ---  Clasificador por IA.  PARA MAS ADELANTE (fase "IA").

Idea: cuando tengas varios cientos de capturas reales en vision/capturas/
(generadas con  inspector_botellas.py --guardar), entrenas un modelo que
reemplace o complemente las heuristicas de clasificador.py.

El nombre de archivo lleva la etiqueta:
    AAAAMMDD_HHMMSS_mmm_<COD>_<detalle>.png
    COD = A (buena) | E (etiqueta) | D (defecto)

Este archivo es un ESQUELETO: todavia no entrena nada. Se recomienda correrlo
en Google Colab (GPU gratis). Al final estan los dos enfoques sugeridos.

    python entrenar_modelo.py --datos capturas
"""

import argparse
import glob
import os

CLASES = {"A": 0, "E": 1, "D": 2}


def cargar_dataset(carpeta):
    """Devuelve (rutas, etiquetas) leyendo el COD del nombre de archivo."""
    rutas, etiquetas = [], []
    for r in sorted(glob.glob(os.path.join(carpeta, "*.png"))):
        partes = os.path.basename(r).split("_")
        cod = next((p for p in partes if p in CLASES), None)
        if cod is not None:
            rutas.append(r)
            etiquetas.append(CLASES[cod])
    return rutas, etiquetas


def entrenar(rutas, etiquetas, salida):
    raise NotImplementedError(
        "Todavia sin implementar. Elegi un enfoque (ver comentarios al final):\n"
        "  1) HOG + SVM con scikit-learn  -> liviano, corre en la laptop.\n"
        "  2) CNN (MobileNetV2 fine-tuning) en Colab con Keras -> mas preciso.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    "capturas"))
    ap.add_argument("--salida", default="modelo.tflite")
    a = ap.parse_args()

    rutas, y = cargar_dataset(a.datos)
    print("%d imagenes en %s" % (len(rutas), a.datos))
    print("por clase:", {k: y.count(v) for k, v in CLASES.items()})
    if len(rutas) < 60:
        print("Junta mas capturas antes de entrenar (minimo ~60, ideal 300+).")
        return
    entrenar(rutas, y, a.salida)


if __name__ == "__main__":
    main()

# ==========================================================================
# OPCION 1 - HOG + SVM (scikit-learn). Imagen a 128x256 en gris:
#
#   from skimage.feature import hog
#   from sklearn.svm import SVC
#   from sklearn.model_selection import train_test_split
#   import joblib, cv2, numpy as np
#
#   X = [hog(cv2.resize(cv2.imread(r, 0), (128, 256)), pixels_per_cell=(16, 16))
#        for r in rutas]
#   Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y)
#   clf = SVC(kernel="rbf", probability=True).fit(Xtr, ytr)
#   print("acc:", clf.score(Xte, yte))
#   joblib.dump(clf, "modelo.joblib")
#
# OPCION 2 - CNN en Colab (Keras / TensorFlow):
#
#   base = tf.keras.applications.MobileNetV2(input_shape=(224, 224, 3),
#            include_top=False, weights="imagenet")
#   base.trainable = False
#   modelo = tf.keras.Sequential([
#       base,
#       tf.keras.layers.GlobalAveragePooling2D(),
#       tf.keras.layers.Dropout(0.2),
#       tf.keras.layers.Dense(3, activation="softmax"),
#   ])
#   modelo.compile("adam", "sparse_categorical_crossentropy", metrics=["accuracy"])
#   modelo.fit(ds_train, validation_data=ds_val, epochs=15)
#   # convertir a TFLite y usarlo desde la laptop dentro de clasificador.py
#   open("modelo.tflite", "wb").write(
#       tf.lite.TFLiteConverter.from_keras_model(modelo).convert())
# ==========================================================================
