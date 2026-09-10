# -*- coding: utf-8 -*-
"""
clasificador.py  ---  Logica de vision de la faja clasificadora de botellas.

Metodo: la botella se fotografia a CONTRALUZ (panel / tira LED detras de un
difusor). En esa imagen la botella es una silueta oscura sobre fondo claro, y
la etiqueta de papel bloquea mas luz que el vidrio -> se ve como una banda
todavia mas oscura con bordes horizontales marcados.

Salida: un codigo de una letra que se le manda al Arduino.
    'A'  aprobada             -> sigue de largo
    'E'  problema de etiqueta -> falta / torcida / rota
    'D'  defecto fisico       -> abollada / sin tapa / aplastada
    'N'  no hay botella       (el inspector lo trata como 'A')

Los umbrales viven en config.json y se ajustan con:
    python inspector_botellas.py --calibrar

Si cambias las letras del protocolo, cambialas tambien en faja_botellas.ino.
"""

import json
import os

import cv2
import numpy as np

# ------------------------------------------------------------------ config ---

CONFIG_DEFECTO = {
    "camara": {"indice": 0, "ancho": 1280, "alto": 720,
               "exposicion": -6, "autoexposicion": False},
    "serial": {"puerto": "AUTO", "baudios": 9600},

    # Region de interes [x, y, w, h] dentro del cuadro. w=h=0 -> cuadro completo.
    "roi": [0, 0, 0, 0],

    # Segmentacion
    "umbral_fondo": 0,      # 0 = Otsu automatico
    "invertir": True,       # True: botella mas OSCURA que el fondo (contraluz)
    "area_min": 6000,       # px de silueta para considerar que hay botella

    # Forma
    "relacion_nominal": 2.6,    # alto/ancho de una botella sana (se calibra)
    "aplastada_factor": 0.75,   # si relacion < nominal*factor -> aplastada
    "tapa_franja": 0.08,        # fraccion superior de la botella que mira la "tapa"
    "tapa_ancho_min": 0.30,     # ancho de esa franja / ancho del cuerpo; menor -> sin tapa
    "abolladura_px": 8,         # desvio max. del borde respecto de su suavizado
    "extent_min": 0.70,         # area_silueta / area_bbox minima (informativo)

    # Etiqueta
    "etiqueta_y": [0.30, 0.80],       # franja vertical donde se busca la etiqueta
    "etiqueta_x": 0.70,              # ancho central analizado (fraccion del ancho)
    "etiqueta_contraste_min": 14,   # cuanto mas oscura que el vidrio para contar como etiqueta
    "etiqueta_min_filas_frac": 0.15,  # filas con etiqueta minimas (fraccion de la franja)
    "etiqueta_alto_min_frac": 0.12,  # alto de la banda continua / alto botella; menor -> rota
    "etiqueta_area_min": 0.50,      # relleno horizontal medio de la etiqueta; menor -> rota
    "etiqueta_rota_std": 0.20,      # variacion del relleno; mayor -> rota
    "torcida_px": 10,               # inclinacion del borde superior de la etiqueta
    "torcida_centro_px": 14,        # desplazamiento lateral de la etiqueta respecto del eje

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
    cfg = dict(CONFIG_DEFECTO)
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
    datos["_comentario"] = ("Ajustado con inspector_botellas.py --calibrar. "
                            "Distancias en pixeles salvo que se indique.")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------- segmentar ---

def segmentar(bgr, cfg):
    """Devuelve (mascara_uint8, bbox|None, gris). mascara: 255 = botella."""
    gris = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr.ndim == 3 else bgr
    gris = cv2.GaussianBlur(gris, (5, 5), 0)

    tipo = cv2.THRESH_BINARY_INV if cfg.get("invertir", True) else cv2.THRESH_BINARY
    u = int(cfg.get("umbral_fondo", 0) or 0)
    if u <= 0:
        _, mask = cv2.threshold(gris, 0, 255, tipo | cv2.THRESH_OTSU)
    else:
        _, mask = cv2.threshold(gris, u, 255, tipo)

    # cerrar reflejos y agujeros; limpiar motas
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return mask, None, gris
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < cfg.get("area_min", 6000):
        return mask, None, gris

    limpia = np.zeros_like(mask)
    cv2.drawContours(limpia, [c], -1, 255, cv2.FILLED)
    x, y, w, h = cv2.boundingRect(c)
    return limpia, (int(x), int(y), int(w), int(h)), gris


# --------------------------------------------------------------- clasificar --

def _res(codigo, etiqueta, detalle, metr, mask):
    return {"codigo": codigo, "etiqueta": etiqueta, "detalle": detalle,
            "metricas": metr, "mask": mask}


def _corrida(bmask):
    """(inicio, fin) de la corrida contigua de True mas larga en un vector bool."""
    mejor_i = mejor_l = i = 0
    n = len(bmask)
    while i < n:
        if bmask[i]:
            j = i
            while j < n and bmask[j]:
                j += 1
            if j - i > mejor_l:
                mejor_l, mejor_i = j - i, i
            i = j
        else:
            i += 1
    return mejor_i, mejor_i + mejor_l


def clasificar(bgr, cfg):
    """Nunca lanza excepcion: ante un cuadro raro devuelve 'A' (dejar pasar)."""
    try:
        return _clasificar_impl(bgr, cfg)
    except Exception as e:  # noqa: BLE001  -- no romper el lazo serie
        return _res("A", "error", "excepcion: %r" % (e,), {}, None)


def _clasificar_impl(bgr, cfg):
    metr = {}
    mask, bbox, gris = segmentar(bgr, cfg)
    if bbox is None:
        return _res("N", "vacio", "no se detecta botella", metr, mask)

    x, y, w, h = bbox
    metr["ancho_px"] = int(w)
    metr["alto_px"] = int(h)
    rel = h / float(max(w, 1))
    metr["relacion"] = rel

    sub = mask[y:y + h, x:x + w] > 0
    anchos = sub.sum(axis=1).astype(np.int32)
    hay = anchos > 0
    metr["extent"] = float(sub.sum()) / float(max(w * h, 1))

    cuerpo_slice = anchos[int(0.35 * h):int(0.90 * h)]
    cuerpo_slice = cuerpo_slice[cuerpo_slice > 0]
    cuerpo_w = float(np.median(cuerpo_slice)) if cuerpo_slice.size else 1.0
    cuerpo_w = max(cuerpo_w, 1.0)

    # ---- APLASTADA (defecto): demasiado baja para su ancho ----
    nominal = float(cfg.get("relacion_nominal", 0) or 0)
    if nominal > 0 and rel < nominal * cfg.get("aplastada_factor", 0.75):
        return _res("D", "aplastada", "relacion %.2f < %.2f" % (rel, nominal), metr, mask)

    # ---- ABOLLADA (defecto): borde del cuerpo se aparta de su recta ----
    b0, b1 = int(0.30 * h), int(0.92 * h)
    izq = np.argmax(sub, axis=1).astype(float)
    der = (w - 1 - np.argmax(sub[:, ::-1], axis=1)).astype(float)
    val = hay.copy()
    val[:b0] = False
    val[b1:] = False
    dev_max = 0.0
    if val.sum() > 12:
        for borde in (izq[val], der[val]):
            d = np.abs(borde - np.median(borde))
            # un pico de 1-2 filas es ruido de segmentacion: lo aplastamos
            d = np.minimum(np.minimum(d, np.roll(d, 1)), np.roll(d, -1))
            dev_max = max(dev_max, float(np.max(d)))
    metr["borde_desvio_px"] = dev_max
    if dev_max > cfg.get("abolladura_px", 8):
        return _res("D", "abollada", "borde +/- %.1f px" % dev_max, metr, mask)

    # ---- SIN TAPA (defecto): la franja superior es tan angosta como el cuello ----
    ft = max(2, int(cfg.get("tapa_franja", 0.08) * h))
    franja = anchos[:ft]
    franja = franja[franja > 0]
    tapa_ratio = (float(np.percentile(franja, 85)) / cuerpo_w) if franja.size else 0.0
    metr["tapa_ratio"] = tapa_ratio
    if tapa_ratio < cfg.get("tapa_ancho_min", 0.30):
        return _res("D", "sin_tapa", "franja superior %.2f del cuerpo" % tapa_ratio, metr, mask)

    # ---- ETIQUETA ----
    ey0 = max(0, y + int(cfg["etiqueta_y"][0] * h))
    ey1 = y + int(cfg["etiqueta_y"][1] * h)
    exf = float(cfg.get("etiqueta_x", 0.70))
    ex0 = max(0, x + int((1 - exf) / 2 * w))
    ex1 = x + int((1 + exf) / 2 * w)
    roi_g = gris[ey0:ey1, ex0:ex1].astype(np.float32)
    roi_m = mask[ey0:ey1, ex0:ex1] > 0
    if roi_g.size == 0 or roi_m.sum() < 20:
        return _res("A", "buena", "sin datos de etiqueta, se aprueba", metr, mask)

    filas = roi_g.shape[0]
    perfil = np.full(filas, np.nan, np.float32)
    for r in range(filas):
        v = roi_g[r][roi_m[r]]
        if v.size:
            perfil[r] = np.median(v)
    if np.isnan(perfil).all():
        return _res("A", "buena", "etiqueta no evaluable", metr, mask)
    idx = np.arange(filas)
    bueno = ~np.isnan(perfil)
    perfil = np.interp(idx, idx[bueno], perfil[bueno])

    base = float(np.median(perfil[:max(3, filas // 6)]))   # vidrio, arriba de la etiqueta
    oscuro = base - perfil                                  # >0 donde hay algo mas opaco
    metr["etiqueta_contraste"] = float(np.max(oscuro))
    es_etq = oscuro > cfg.get("etiqueta_contraste_min", 14)

    if es_etq.sum() < cfg.get("etiqueta_min_filas_frac", 0.15) * filas:
        return _res("E", "sin_etiqueta",
                    "contraste maximo %.1f" % metr["etiqueta_contraste"], metr, mask)

    r0, r1 = _corrida(es_etq)
    metr["etiqueta_alto_px"] = int(r1 - r0)
    metr["etiqueta_alto_frac"] = (r1 - r0) / float(max(h, 1))

    umb = base - cfg.get("etiqueta_contraste_min", 14) * 0.6
    banda = (roi_g < umb) & roi_m
    banda[:r0] = False
    banda[r1:] = False

    # --- TORCIDA: borde superior inclinado o etiqueta corrida del eje ---
    cols_top = []
    for c in range(banda.shape[1]):
        f = np.where(banda[:, c])[0]
        if f.size:
            cols_top.append((c, f[0]))
    pend_px = 0.0
    if len(cols_top) > banda.shape[1] * 0.35:
        cc = np.array([p[0] for p in cols_top], float)
        rr = np.array([p[1] for p in cols_top], float)
        m = np.polyfit(cc, rr, 1)[0]
        pend_px = abs(m) * banda.shape[1]
    metr["etiqueta_inclinacion_px"] = pend_px

    ys, xs = np.where(banda)
    desp_px = abs(xs.mean() + ex0 - (x + w / 2.0)) if xs.size else 0.0
    metr["etiqueta_desplazada_px"] = float(desp_px)

    if pend_px > cfg.get("torcida_px", 10) or desp_px > cfg.get("torcida_centro_px", 14):
        return _res("E", "etiqueta_torcida",
                    "inclinacion %.1f px, desplazada %.1f px" % (pend_px, desp_px), metr, mask)

    # --- ROTA (por altura): la banda continua de etiqueta es demasiado corta ---
    # (una etiqueta partida deja solo un pedazo contiguo)
    if metr["etiqueta_alto_frac"] < cfg.get("etiqueta_alto_min_frac", 0.12):
        return _res("E", "etiqueta_rota",
                    "banda de %d px (%.0f%% del alto)"
                    % (r1 - r0, 100 * metr["etiqueta_alto_frac"]), metr, mask)

    # --- ROTA (por relleno): poco relleno horizontal o muy irregular ---
    seg = slice(r0, r1)
    lab_w = banda[seg].sum(axis=1).astype(float)
    sil_w = roi_m[seg].sum(axis=1).astype(float)
    ratio = lab_w / np.maximum(sil_w, 1.0)
    relleno = float(np.mean(ratio)) if ratio.size else 0.0
    relleno_std = float(np.std(ratio)) if ratio.size else 1.0
    metr["etiqueta_relleno"] = relleno
    metr["etiqueta_relleno_std"] = relleno_std
    if relleno < cfg.get("etiqueta_area_min", 0.50) or relleno_std > cfg.get("etiqueta_rota_std", 0.20):
        return _res("E", "etiqueta_rota",
                    "relleno %.2f (std %.2f)" % (relleno, relleno_std), metr, mask)

    return _res("A", "buena", "sin defectos", metr, mask)


# --------------------------------------------------------------- diagnostico -

def dibujar_diagnostico(bgr, res, cfg):
    """Imagen con la silueta y la franja de etiqueta marcadas (para --calibrar)."""
    vis = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR) if bgr.ndim == 2 else bgr.copy()
    mask = res.get("mask")
    if mask is not None and mask.shape[:2] == vis.shape[:2]:
        borde = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT,
                                 cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        vis[borde > 0] = (0, 255, 0)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            x, y, w, h = cv2.boundingRect(max(cnts, key=cv2.contourArea))
            ey0 = y + int(cfg["etiqueta_y"][0] * h)
            ey1 = y + int(cfg["etiqueta_y"][1] * h)
            exf = float(cfg.get("etiqueta_x", 0.70))
            ex0 = x + int((1 - exf) / 2 * w)
            ex1 = x + int((1 + exf) / 2 * w)
            cv2.rectangle(vis, (x, y), (x + w, y + h), (255, 160, 0), 1)
            cv2.rectangle(vis, (ex0, ey0), (ex1, ey1), (0, 160, 255), 1)
    col = {"A": (0, 200, 0), "E": (0, 200, 255), "D": (0, 0, 255), "N": (150, 150, 150)}
    cv2.rectangle(vis, (0, 0), (vis.shape[1] - 1, vis.shape[0] - 1),
                  col.get(res["codigo"], (200, 200, 200)), 4)
    return vis
