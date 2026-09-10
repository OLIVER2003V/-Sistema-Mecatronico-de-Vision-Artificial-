# -*- coding: utf-8 -*-
"""
clasificador.py  ---  Clasificacion de botellas con el modelo YOLO (best.pt).

El modelo (Ultralytics YOLO) detecta 6 clases:
    Botella  Etiqueta  Tapa  Agua   -> lo que TIENE que estar en una botella sana
    Rota     Notapa                 -> defectos fisicos

Regla de decision -> 3 salidas que se le mandan al Arduino:

    'A'  ACEPTADA    : Botella + Etiqueta + Tapa + Agua, las cuatro con
                       confianza >= conf_ok (0.80), y sin Rota ni Notapa.
    'D'  DEFECTUOSA  : hay Rota o Notapa, o falta Botella / Etiqueta / Tapa.
    'L'  NIVEL AGUA  : lo fisico esta bien pero el Agua no llega a conf_ok
                       (botella mal llenada o vacia). Estacion propia.
    'N'  sin botella : el modelo no ve una botella (el inspector lo trata como 'A').

Umbrales -> config.json, seccion "modelo". Si cambias estas letras, cambialas
tambien en faja_botellas/faja_botellas.ino.

DONDE VA EL MODELO
------------------
Copia tu best.pt dentro de la carpeta  vision/  (queda como vision/best.pt).
Alternativas: poner la ruta en config.json -> "modelo": {"ruta": "..."}  o
pasar  --modelo C:\\ruta\\best.pt  al inspector.
"""

import json
import os

import cv2
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))

# Nombres de clase que necesita la regla (se comparan en minuscula).
CLS_REQUERIDAS = ("botella", "etiqueta", "tapa", "agua")
CLS_DEFECTO = ("rota", "notapa")
CLS_TODAS = CLS_REQUERIDAS + CLS_DEFECTO

# ------------------------------------------------------------------ config ---

CONFIG_DEFECTO = {
    "camara": {"indice": 0, "ancho": 1280, "alto": 720,
               "exposicion": -6, "autoexposicion": False},
    "serial": {"puerto": "AUTO", "baudios": 9600},

    # Region de interes [x, y, w, h] dentro del cuadro. w=h=0 -> cuadro completo.
    "roi": [0, 0, 0, 0],

    # Clasificador YOLO
    "modelo": {
        "ruta": "best.pt",        # relativa a vision/ o ruta absoluta
        "conf_ok": 0.80,          # el "minimo 80%" de las clases que deben estar
        "conf_detectar": 0.25,    # una clase "aparece" a partir de esta confianza
        "conf_defecto": 0.50,     # Rota / Notapa cuentan como defecto a partir de aca
        "imgsz": 640,
        "dispositivo": "cpu",     # "cpu"  o  "0" para la primera GPU
    },

    "guardar_dir": "capturas",
}


def _fusionar(base, extra):
    """Mezcla recursiva: extra pisa base."""
    out = dict(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _fusionar(out[k], v)
        else:
            out[k] = v
    return out


def cargar_config(ruta):
    cfg = _fusionar(CONFIG_DEFECTO, {})
    if ruta and os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                disco = json.load(f)
            disco.pop("_comentario", None)
            cfg = _fusionar(CONFIG_DEFECTO, disco)
        except (ValueError, OSError) as e:
            print("aviso: no se pudo leer %s (%s); uso valores por defecto" % (ruta, e))
    return cfg


def guardar_config(cfg, ruta):
    datos = dict(cfg)
    datos["_comentario"] = ("Config de la faja. La seccion 'modelo' controla el "
                            "clasificador YOLO (best.pt). conf_ok = el 'minimo 80%'.")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------ modelo ---

_MODELO = None
_MODELO_RUTA = None
_MODELO_MAPA = {}      # indice de clase del modelo -> nombre canonico en minuscula


def ruta_modelo(cfg):
    r = (cfg.get("modelo") or {}).get("ruta", "best.pt")
    return r if os.path.isabs(r) else os.path.join(AQUI, r)


def cargar_modelo(cfg, forzar=False):
    """
    Carga best.pt una sola vez (se cachea a nivel de modulo).
    Lanza FileNotFoundError o ImportError con un mensaje claro si falta algo;
    el inspector lo llama al arrancar para fallar temprano.
    """
    global _MODELO, _MODELO_RUTA, _MODELO_MAPA
    ruta = ruta_modelo(cfg)
    if _MODELO is not None and _MODELO_RUTA == ruta and not forzar:
        return _MODELO

    if not os.path.exists(ruta):
        raise FileNotFoundError(
            "no encuentro el modelo YOLO en:\n  %s\n"
            "Copia tu best.pt ahi, o pon la ruta en config.json -> modelo.ruta, "
            "o usa  --modelo RUTA." % ruta)
    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise ImportError(
            "falta la libreria 'ultralytics'. Instalala con:\n"
            "  python -m pip install -r requirements.txt") from e

    modelo = YOLO(ruta)
    nombres = modelo.names if isinstance(modelo.names, dict) else dict(enumerate(modelo.names))
    por_nombre = {str(v).lower(): int(k) for k, v in nombres.items()}
    mapa, faltan = {}, []
    for c in CLS_TODAS:
        if c in por_nombre:
            mapa[por_nombre[c]] = c
        else:
            faltan.append(c)
    if faltan:
        print("aviso: el modelo no trae las clases %s. Clases del modelo: %s"
              % (faltan, list(nombres.values())))
    _MODELO, _MODELO_RUTA, _MODELO_MAPA = modelo, ruta, mapa
    return modelo


# --------------------------------------------------------------- clasificar --

def _res(codigo, etiqueta, detalle, metr, dets):
    return {"codigo": codigo, "etiqueta": etiqueta, "detalle": detalle,
            "metricas": metr, "detecciones": dets}


def clasificar(bgr, cfg, modelo=None):
    """Nunca lanza: ante un error de inferencia deja pasar la botella ('A')."""
    try:
        return _clasificar_impl(bgr, cfg, modelo)
    except Exception as e:  # noqa: BLE001  -- no romper el lazo serie
        return _res("A", "error", "excepcion: %r" % (e,), {}, [])


def _clasificar_impl(bgr, cfg, modelo):
    m = cfg.get("modelo") or {}
    conf_ok = float(m.get("conf_ok", 0.80))
    conf_det = float(m.get("conf_detectar", 0.25))
    conf_def = float(m.get("conf_defecto", 0.50))
    modelo = modelo or cargar_modelo(cfg)

    salida = modelo.predict(bgr, imgsz=int(m.get("imgsz", 640)), conf=conf_det,
                            device=m.get("dispositivo", "cpu"), verbose=False)
    r = salida[0]

    # confianza maxima por clase canonica + lista de cajas para dibujar
    cmax = {c: 0.0 for c in CLS_TODAS}
    dets = []
    cajas = getattr(r, "boxes", None)
    if cajas is not None and len(cajas) and cajas.cls is not None:
        idx = cajas.cls.cpu().numpy().astype(int)
        conf = cajas.conf.cpu().numpy()
        xyxy = cajas.xyxy.cpu().numpy()
        for i, ci in enumerate(idx):
            nombre = _MODELO_MAPA.get(int(ci))
            cf = float(conf[i])
            dets.append((nombre or str(int(ci)), cf, [float(v) for v in xyxy[i]]))
            if nombre and cf > cmax[nombre]:
                cmax[nombre] = cf

    metr = {"conf_%s" % c: round(cmax[c], 3) for c in CLS_TODAS}
    metr["n_cajas"] = len(dets)

    # ---- regla de decision (el orden importa) ----
    if cmax["botella"] < conf_det:
        return _res("N", "sin_botella", "no se ve una botella", metr, dets)

    if cmax["rota"] >= conf_def:
        return _res("D", "rota", "Rota conf %.2f" % cmax["rota"], metr, dets)
    if cmax["notapa"] >= conf_def:
        return _res("D", "sin_tapa", "Notapa conf %.2f" % cmax["notapa"], metr, dets)
    if cmax["etiqueta"] < conf_ok:
        return _res("D", "falta_etiqueta",
                    "Etiqueta conf %.2f < %.2f" % (cmax["etiqueta"], conf_ok), metr, dets)
    if cmax["tapa"] < conf_ok:
        return _res("D", "falta_tapa",
                    "Tapa conf %.2f < %.2f" % (cmax["tapa"], conf_ok), metr, dets)

    # fisico OK: lo unico que puede fallar es el nivel de agua
    if cmax["agua"] < conf_ok:
        return _res("L", "nivel_bajo",
                    "Agua conf %.2f < %.2f" % (cmax["agua"], conf_ok), metr, dets)

    return _res("A", "aceptada", "Botella/Etiqueta/Tapa/Agua OK", metr, dets)


# --------------------------------------------------------------- diagnostico -

COLOR_COD = {"A": (0, 200, 0), "D": (0, 0, 255), "L": (0, 200, 255), "N": (150, 150, 150)}


def dibujar_diagnostico(bgr, res, cfg=None):
    """Imagen con las cajas del modelo y un borde del color del veredicto."""
    vis = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR) if bgr.ndim == 2 else bgr.copy()
    for nombre, cf, (x1, y1, x2, y2) in res.get("detecciones", []):
        p1, p2 = (int(x1), int(y1)), (int(x2), int(y2))
        cv2.rectangle(vis, p1, p2, (255, 200, 0), 2)
        etq = "%s %.2f" % (nombre, cf)
        yy = p1[1] - 5 if p1[1] > 14 else p1[1] + 14
        cv2.putText(vis, etq, (p1[0], yy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(vis, etq, (p1[0], yy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1, cv2.LINE_AA)
    col = COLOR_COD.get(res["codigo"], (200, 200, 200))
    cv2.rectangle(vis, (0, 0), (vis.shape[1] - 1, vis.shape[0] - 1), col, 4)
    return vis
