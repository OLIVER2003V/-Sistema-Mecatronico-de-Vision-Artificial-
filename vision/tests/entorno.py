# -*- coding: utf-8 -*-
"""
Deja importar clasificador.py e inspector_botellas.py aunque en esta PC no
esten instaladas las dependencias pesadas de vision.

opencv y numpy hacen falta para procesar imagenes de verdad, no para la
logica que estas pruebas verifican (reglas de decision, geometria, mapeos).
Si estan instaladas se usan las de verdad; si no, se ponen dobles minimos.
Asi la suite corre igual en la PC de la faja y en una maquina de desarrollo
o en un runner de integracion continua.
"""
import importlib
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _ModuloPermisivo(types.ModuleType):
    """Devuelve un objeto cualquiera para cualquier atributo que le pidan."""

    def __getattr__(self, nombre):
        valor = object()
        setattr(self, nombre, valor)
        return valor


def _asegurar(nombre):
    try:
        importlib.import_module(nombre)
    except ImportError:
        sys.modules[nombre] = _ModuloPermisivo(nombre)


def preparar():
    """Llamar antes de importar los modulos de vision/."""
    if RAIZ not in sys.path:
        sys.path.insert(0, RAIZ)
    for nombre in ("cv2", "numpy"):
        _asegurar(nombre)
