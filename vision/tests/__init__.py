# -*- coding: utf-8 -*-
"""
Pruebas unitarias del modulo de vision.

Se corren SIN camara, SIN Arduino, SIN backend y sin el modelo best.pt:
verifican la logica pura (reglas de decision, geometria del llenado, mapeo de
datos hacia el backend y recarga de umbrales en caliente).

    cd vision
    python -m unittest discover -s tests -t .

Ver tests/entorno.py: si opencv/numpy no estan instalados en esta PC, se
sustituyen por dobles minimos para poder importar los modulos igual.
"""
