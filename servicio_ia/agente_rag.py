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
        # 1. Consultar resumen de inspecciones
        r_resumen = requests.get(f"{BACKEND_URL}/api/linea/resumen-hoy/", headers=HEADERS, timeout=3.0)
        resumen_data = r_resumen.json() if r_resumen.ok else {}

        # 2. Consultar estado actual de la faja
        r_estado = requests.get(f"{BACKEND_URL}/api/estado-faja/actual/", headers=HEADERS, timeout=3.0)
        estado_data = r_estado.json() if r_estado.ok else {}

        # 3. Consultar últimas 5 mermas/defectos
        r_mermas = requests.get(f"{BACKEND_URL}/api/linea/inspecciones/?solo_defectos=true&limite=5", headers=HEADERS, timeout=3.0)
        mermas_data = r_mermas.json() if r_mermas.ok else []

        contexto = f"""
=== CONTEXTO DE PLANTA EN TIEMPO REAL (SORT-MATIC) ===
- Estado Faja Transportadora: {'EN MARCHA' if estado_data.get('en_marcha') else 'DETENIDA'}
- Conexión Hardware Arduino: {'CONECTADO' if estado_data.get('arduino_conectado') else 'DESCONECTADO'}
- Total Botellas Inspeccionadas Hoy: {resumen_data.get('total_hoy', 0)}
- Aceptadas: {resumen_data.get('aceptadas_hoy', 0)}
- Defectuosas (Estación 1 - Rota/Etiqueta/Tapa): {resumen_data.get('defectuosas_hoy', 0)}
- Llenado Bajo (Estación 2 - Liquid < 60%): {resumen_data.get('llenado_bajo_hoy', 0)}
- Porcentaje Global de Mermas: {resumen_data.get('porcentaje_mermas', 0.0)}%

Últimas mermas registradas:
"""
        if isinstance(mermas_data, list) and mermas_data:
            for item in mermas_data[:5]:
                contexto += f"  * Botella #{item.get('id')}: {item.get('resultado')} ({item.get('tipo_defecto', 'N/A')}) - Confianza IA: {item.get('confianza_ia')}%\n"
        else:
            contexto += "  * No hay mermas recientes.\n"

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
            f"{BACKEND_URL}/api/comandos/",
            json={"accion": accion},
            headers=HEADERS,
            timeout=3.0
        )
        if r.ok:
            return {"exito": True, "mensaje": f"Comando '{accion}' enviado exitosamente a la faja transportadora."}
        return {"exito": False, "mensaje": f"El backend respondió con error: {r.status_code}"}
    except Exception as e:
        return {"exito": False, "mensaje": f"Error de red al enviar comando: {e}"}
