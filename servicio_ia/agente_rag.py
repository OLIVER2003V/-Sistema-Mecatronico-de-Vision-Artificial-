# -*- coding: utf-8 -*-
"""
agente_rag.py --- Conector RAG (Retrieval-Augmented Generation) para el Microservicio de IA.
Consulta métricas e inspecciones en tiempo real al backend Django y prepara el contexto para el LLM.
"""

import os
import requests

BACKEND_URL = os.environ.get("BACKEND_URL") or os.environ.get("DJANGO_BACKEND_URL") or "http://localhost:8000"
BACKEND_URL = BACKEND_URL.rstrip("/")
VISION_API_KEY = os.environ.get("VISION_API_KEY", "clave-vision-de-desarrollo-cambiar-en-produccion")

HEADERS = {
    "X-API-Key": VISION_API_KEY,
    "Content-Type": "application/json"
}


def obtener_contexto_planta() -> str:
    """
    Consulta las APIs del backend Django para construir un contexto fresco en tiempo real
    que alimentará al modelo generativo Gemini.
    """
    try:
        # 1. Consultar KPIs de la línea (/api/kpis/)
        r_kpis = requests.get(f"{BACKEND_URL}/linea/kpis/", headers=HEADERS, timeout=3.0)
        kpis_data = r_kpis.json() if r_kpis.ok else {}

        # 2. Consultar estado actual de la faja (/api/estado-faja/)
        r_estado = requests.get(f"{BACKEND_URL}/linea/estado-faja/", headers=HEADERS, timeout=3.0)
        estado_data = r_estado.json() if r_estado.ok else {}

        # 3. Consultar últimas mermas/defectos (/api/mermas/?page_size=5)
        r_mermas = requests.get(f"{BACKEND_URL}/linea/mermas/?page_size=5", headers=HEADERS, timeout=3.0)
        mermas_resp = r_mermas.json() if r_mermas.ok else {}
        mermas_data = (
            mermas_resp.get("results", [])
            if isinstance(mermas_resp, dict)
            else (mermas_resp if isinstance(mermas_resp, list) else [])
        )

        conteos = kpis_data.get("conteos", {})

        contexto = f"""
=== CONTEXTO DE PLANTA EN TIEMPO REAL (SORT-MATIC) ===
- Estado Faja Transportadora: {'EN MARCHA' if estado_data.get('en_marcha') else 'DETENIDA'}
- Conexión Hardware Arduino: {'CONECTADO' if estado_data.get('arduino_conectado') else 'DESCONECTADO'}
- Total Botellas Inspeccionadas (Lote Activo): {kpis_data.get('total_inspecciones', 0)}
- Cadencia de Producción: {kpis_data.get('cadencia_bpm', 0.0)} BPM (Teórica: {kpis_data.get('cadencia_teorica_bpm', 0.0)} BPM)
- Tasa de Aprobación (Yield Rate): {kpis_data.get('yield_rate', 0.0)}%
- Tasa de Rechazo (Mermas): {kpis_data.get('reject_rate', 0.0)}%
- Conteo Aceptadas: {conteos.get('aceptadas', 0)}
- Conteo Defectuosas Estación 1 (Físicas): {conteos.get('defectuosa', 0)} (Sin Tapa: {conteos.get('sin_tapa', 0)}, Sin Etiqueta: {conteos.get('sin_etiqueta', 0)})
- Conteo Llenado Bajo Estación 2: {conteos.get('llenado_bajo', 0)}

Últimas mermas registradas:
"""
        if isinstance(mermas_data, list) and mermas_data:
            for item in mermas_data[:5]:
                contexto += f"  * Botella #{item.get('id')}: {item.get('resultado')} ({item.get('tipo_defecto', 'N/A')}) - {item.get('fecha_hora', '')}\n"
        else:
            contexto += "  * No hay mermas recientes registradas.\n"

        return contexto.strip()

    except Exception as e:
        return f"=== CONTEXTO DE PLANTA ===\nNota: No se pudo conectar al Backend Django ({e}). Operando en modo autónomo."


def ejecutar_comando_faja(accion: str) -> dict:
    """
    Herramienta invocada por la IA para enviar órdenes de marcha/paro/reset a la faja.
    Acciones válidas: 'START', 'STOP', 'RESET'
    """
    accion = accion.upper()
    if accion not in ("START", "STOP", "RESET"):
        return {"exito": False, "mensaje": f"Acción '{accion}' no válida. Use START, STOP o RESET."}

    try:
        r = requests.post(
            f"{BACKEND_URL}/linea/comandos/",
            json={"accion": accion},
            headers=HEADERS,
            timeout=3.0
        )
        if r.ok:
            return {"exito": True, "mensaje": f"Comando '{accion}' enviado exitosamente a la faja transportadora."}
        return {"exito": False, "mensaje": f"El backend respondió con error: {r.status_code}"}
    except Exception as e:
        return {"exito": False, "mensaje": f"Error de red al enviar comando: {e}"}
