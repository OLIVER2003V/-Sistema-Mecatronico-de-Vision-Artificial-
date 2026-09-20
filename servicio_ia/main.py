# -*- coding: utf-8 -*-
"""
main.py --- Microservicio Independiente de IA (SORT-MATIC IA Assistant).
Procesa consultas conversacionales, genera reportes ejecutivos en tiempo real y gestiona streaming WebSockets.
Soporta fallback automático entre modelos Gemini configurables por variable de entorno.
"""

import os
import asyncio
from typing import Optional, List, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env local o raíz si existe
base_dir = os.path.dirname(os.path.abspath(__file__))
for env_path in (os.path.join(base_dir, ".env"), os.path.join(base_dir, "..", ".env")):
    if os.path.isfile(env_path):
        load_dotenv(env_path)

from agente_rag import obtener_contexto_planta, ejecutar_comando_faja

app = FastAPI(
    title="SORT-MATIC IA Assistant Microservice",
    description="Microservicio desacoplado de Inteligencia Artificial Generativa y RAG",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODELOS_DEFAULT = "gemini-2.5-flash,gemini-2.0-flash,gemini-1.5-flash,gemini-3.6-flash"


def obtener_lista_modelos() -> List[str]:
    """Retorna la lista ordenada de modelos Gemini a intentar en orden de preferencia."""
    raw = os.environ.get("GEMINI_MODELS", MODELOS_DEFAULT)
    models = [m.strip() for m in raw.split(",") if m.strip()]
    return models if models else ["gemini-2.5-flash"]


def obtener_cliente_gemini():
    """Inicializa el cliente de la API de Google Gemini si la clave está disponible."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return None
    try:
        return genai.Client(api_key=key)
    except Exception as e:
        print(f"Error al inicializar Google Gemini Client: {e}")
        return None


def generar_contenido_con_fallback(client, contents: str, config: Optional[dict] = None) -> Tuple[object, str]:
    """
    Intenta generar contenido probando secuencialmente la lista de modelos configurados.
    Evita fallas cuando un modelo específico experimenta sobrecarga (HTTP 503 / 429).
    """
    modelos = obtener_lista_modelos()
    ultimo_error = None
    for model_name in modelos:
        try:
            kwargs = {"model": model_name, "contents": contents}
            if config:
                kwargs["config"] = config
            response = client.models.generate_content(**kwargs)
            return response, model_name
        except Exception as e:
            print(f"⚠️ Modelo '{model_name}' fallo ({e}). Reintentando con el siguiente modelo de la lista...")
            ultimo_error = e
    if ultimo_error is not None:
        raise ultimo_error
    raise RuntimeError("No hay modelos de IA disponibles para procesar la solicitud.")


def generar_stream_con_fallback(client, contents: str):
    """
    Intenta iniciar streaming probando secuencialmente la lista de modelos configurados.
    """
    modelos = obtener_lista_modelos()
    ultimo_error = None
    for model_name in modelos:
        try:
            response = client.models.generate_content_stream(
                model=model_name,
                contents=contents
            )
            return response, model_name
        except Exception as e:
            print(f"⚠️ Streaming con modelo '{model_name}' fallo ({e}). Reintentando con el siguiente modelo...")
            ultimo_error = e
    if ultimo_error is not None:
        raise ultimo_error
    raise RuntimeError("No hay modelos de IA disponibles para procesar la solicitud de streaming.")


class TurnoHistorial(BaseModel):
    es_usuario: bool
    texto: str


class ConsultaChat(BaseModel):
    pregunta: str
    usuario: Optional[str] = "Operador"
    rol: Optional[str] = "OPERADOR"
    conversacion_id: Optional[str] = None
    historial: Optional[List[TurnoHistorial]] = None


class SolicitudReporte(BaseModel):
    tipo: str = "turno"  # 'turno', 'anomalia', 'lote'
    usuario: Optional[str] = "Supervisor"


@app.get("/salud")
def salud():
    return {
        "estado": "ok",
        "servicio": "servicio_ia",
        "gemini_configurado": bool(os.environ.get("GEMINI_API_KEY")),
        "modelos_configurados": obtener_lista_modelos()
    }


@app.post("/chat")
def chat_asistente(solicitud: ConsultaChat):
    """
    Procesa una pregunta del operador o supervisor, inyecta el contexto de planta en tiempo real,
    evalúa el historial conversacional y devuelve una respuesta estructurada en JSON nativo
    con widgets dinámicos y acción de lienzo (accion_canvas).
    """
    import json

    pregunta = solicitud.pregunta.strip()
    if not pregunta:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    contexto = obtener_contexto_planta()
    client = obtener_cliente_gemini()

    # Detección de comandos de hardware sobre la faja
    comando_ejecutado = None
    p_lower = pregunta.lower()
    if "parar faja" in p_lower or "detener faja" in p_lower or "stop faja" in p_lower:
        comando_ejecutado = ejecutar_comando_faja("STOP")
    elif "arrancar faja" in p_lower or "iniciar faja" in p_lower or "start faja" in p_lower:
        comando_ejecutado = ejecutar_comando_faja("START")

    # Formatear el historial reciente enviado por la app
    historial_str = ""
    if solicitud.historial:
        for t in solicitud.historial[-6:]:
            rol_lbl = "Usuario" if t.es_usuario else "Asistente IA"
            historial_str += f"- {rol_lbl}: {t.texto}\n"
    if not historial_str:
        historial_str = "(Sin historial previo en esta sesión)"

    # Fallback sintético si Gemini no está configurado (sin API key)
    if not client:
        respuesta_base = (
            f"🤖 **Asistente SORT-MATIC (Modo Autónomo / Sintético):**\n\n"
            f"Consulta recibida: *\"{pregunta}\"*\n\n"
            f"**Resumen de Planta:**\n{contexto}\n"
        )
        if comando_ejecutado:
            respuesta_base += f"\n⚙️ **Acción:** {comando_ejecutado['mensaje']}"

        # Determinar widgets sintéticos
        widgets_sinteticos = []
        accion = "agregar" if "agrega" in p_lower or "añade" in p_lower else "reemplazar"
        if "limpiar" in p_lower or "borrar" in p_lower:
            accion = "limpiar"

        if "botella" in p_lower or "conteo" in p_lower or "reporte" in p_lower or "escaneo" in p_lower:
            widgets_sinteticos.append({
                "tipo": "kpi_card",
                "titulo": "Total Botellas Inspeccionadas",
                "valor": 1250,
                "subtitulo": "Lote Activo",
                "color": "cyan"
            })
            widgets_sinteticos.append({
                "tipo": "grafico_barras",
                "titulo": "Botellas por Material Escaneado",
                "datos": [
                    {"etiqueta": "PET", "valor": 800},
                    {"etiqueta": "Vidrio", "valor": 300},
                    {"etiqueta": "Aluminio", "valor": 150}
                ]
            })

        return {
            "respuesta": respuesta_base,
            "accion_canvas": accion,
            "widgets": widgets_sinteticos,
            "conversacion_id": solicitud.conversacion_id,
            "comando_ejecutado": comando_ejecutado,
            "contexto_usado": contexto
        }

    prompt_sistema = f"""
Eres el Asistente Virtual Inteligente de la planta EMBOL S.A. para el sistema mecatrónico SORT-MATIC.
Tu objetivo es ayudar a los operadores y supervisores de calidad a monitorear la faja transportadora,
diagnosticar mermas y generar reportes y dashboards dinámicos interactivos.

=== CONTEXTO DE PLANTA EN TIEMPO REAL ===
{contexto}

=== HISTORIAL DE CONVERSACIÓN ===
{historial_str}

=== SOLICITUD DEL USUARIO ===
Usuario: {solicitud.usuario} (Rol: {solicitud.rol})
Pregunta/Instrucción: "{pregunta}"

=== REGLA OBLIGATORIA: DEBES RESPONDER EXCLUSIVAMENTE CON UN OBJETO JSON VÁLIDO ===
No agregues explicaciones fuera del JSON. El JSON debe tener exactamente estas claves:

{{
  "respuesta": "Texto explicativo amigable en formato Markdown dirigido al usuario.",
  "accion_canvas": "reemplazar | agregar | limpiar",
  "widgets": [
    {{
      "tipo": "kpi_card",
      "titulo": "Título de la métrica",
      "valor": 1250,
      "subtitulo": "Descripción corta",
      "color": "cyan | green | amber | red | blue"
    }},
    {{
      "tipo": "grafico_barras",
      "titulo": "Título del gráfico",
      "datos": [
        {{ "etiqueta": "PET", "valor": 800 }},
        {{ "etiqueta": "Vidrio", "valor": 300 }}
      ]
    }},
    {{
      "tipo": "grafico_pie",
      "titulo": "Título de la gráfica circular",
      "datos": [
        {{ "etiqueta": "Aceptadas", "valor": 1140, "color": "green" }},
        {{ "etiqueta": "Defectuosas", "valor": 60, "color": "red" }}
      ]
    }},
    {{
      "tipo": "tabla_datos",
      "titulo": "Título de la tabla",
      "columnas": ["Columna1", "Columna2", "Columna3"],
      "filas": [
        ["Dato1", "Dato2", "Dato3"]
      ]
    }},
    {{
      "tipo": "alerta_status",
      "titulo": "Título de alerta",
      "mensaje": "Mensaje detallado",
      "nivel": "exito | advertencia | peligro | info"
    }}
  ]
}}

REGLAS PARA "accion_canvas":
- Usar "reemplazar": cuando el usuario pida un nuevo reporte general, un resumen de escaneo o cuando haga una nueva consulta de datos sin indicar agregar a lo existente.
- Usar "agregar": cuando el usuario diga explícitamente "agrega", "añade", "adicionalmente", "también incluye", etc.
- Usar "limpiar": cuando el usuario diga "limpiar pantalla", "borrar lienzo", "reiniciar tablero", etc.

Si la consulta es puramente conversacional y no requiere componentes visuales, "widgets" debe ser una lista vacía [].
Los valores numéricos pueden ser enteros o decimales.
"""

    config_json = {"response_mime_type": "application/json"}

    try:
        response, modelo_usado = generar_contenido_con_fallback(client, prompt_sistema, config=config_json)
        raw_text = response.text.strip()

        # Intentar parsear el JSON devuelto por Gemini
        try:
            parsed = json.loads(raw_text)
        except Exception:
            # Limpieza defensiva en caso de delimitadores de código markdown
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_text)

        respuesta_str = parsed.get("respuesta", "Reporte procesado correctamente.")
        if comando_ejecutado:
            respuesta_str += f"\n\n⚙️ **Acción Ejecutada en Faja:** {comando_ejecutado['mensaje']}"

        return {
            "respuesta": respuesta_str,
            "accion_canvas": parsed.get("accion_canvas", "reemplazar"),
            "widgets": parsed.get("widgets", []),
            "conversacion_id": solicitud.conversacion_id,
            "modelo_usado": modelo_usado,
            "comando_ejecutado": comando_ejecutado,
            "contexto_usado": contexto
        }
    except Exception as e:
        print(f"Error procesando JSON de Gemini: {e}")
        # Retorno defensivo estructurado
        return {
            "respuesta": f"He procesado tu consulta. Sin embargo, ocurrió un detalle al estructurar los gráficos ({e}).\n\nResumen actual:\n{contexto}",
            "accion_canvas": "reemplazar",
            "widgets": [
                {
                    "tipo": "alerta_status",
                    "titulo": "Modo Resumen Directo",
                    "mensaje": f"Se muestra información consolidada de planta.",
                    "nivel": "info"
                }
            ],
            "conversacion_id": solicitud.conversacion_id,
            "comando_ejecutado": comando_ejecutado,
            "contexto_usado": contexto
        }


@app.post("/reporte")
def generar_reporte_ejecutivo(solicitud: SolicitudReporte):
    """
    Genera un reporte ejecutivo en formato Markdown sobre el estado de la producción,
    mermas y diagnósticos recomendados.
    """
    contexto = obtener_contexto_planta()
    client = obtener_cliente_gemini()

    if not client:
        return {
            "reporte_markdown": f"""# 📊 Reporte Ejecutivo de Producción y Calidad (SORT-MATIC)
**Tipo:** {solicitud.tipo.upper()} | **Generado por:** {solicitud.usuario}

## 1. Resumen de Operación
{contexto}

## 2. Diagnóstico de Calidad
* **Estación 1 (Inspección Física):** Los defectos de botella rota y sin etiqueta se encuentran dentro del margen operativo.
* **Estación 2 (Nivel de Llenado):** La detección por geometría se mantiene calibrada a un umbral mínimo del 60%.

## 3. Recomendaciones de Mantenimiento
1. Verificar la limpieza del lente de la cámara fija en la faja.
2. Comprobar la alineación neumática del Servo 1 y Servo 2.
3. Mantener el espacio constante entre botellas con las guías laterales.
""",
            "contexto": contexto
        }

    prompt_reporte = f"""
    Genera un Reporte Ejecutivo de Calidad y Mermas completo en formato Markdown para la planta EMBOL S.A.
    Tipo de reporte solicitado: {solicitud.tipo.upper()} por {solicitud.usuario}.

    {contexto}

    El reporte debe contener:
    # 📊 Reporte Ejecutivo de Inspección y Mermas (SORT-MATIC)
    ## 1. Métricas de Producción en Tiempo Real
    ## 2. Análisis de Causa Raíz de Defectos
    ## 3. Acciones Preventivas Recomendadas para el Supervisor
    """

    try:
        response, modelo_usado = generar_contenido_con_fallback(client, prompt_reporte)
        return {
            "reporte_markdown": response.text,
            "modelo_usado": modelo_usado,
            "contexto": contexto
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar reporte: {e}")


@app.websocket("/ws/chat")
async def websocket_chat_asistente(websocket: WebSocket):
    """
    WebSocket endpoint para streaming en tiempo real de consultas y respuestas con la App Móvil Flutter.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            pregunta = data.get("pregunta", "")
            usuario = data.get("usuario", "Operador Móvil")

            if not pregunta:
                await websocket.send_json({"error": "Pregunta vacía"})
                continue

            contexto = obtener_contexto_planta()
            client = obtener_cliente_gemini()

            if not client:
                await websocket.send_json({
                    "tipo": "respuesta_completa",
                    "texto": f"🤖 **Asistente Móvil (SORT-MATIC):**\nHe recibido: *\"{pregunta}\"*\n\n{contexto}"
                })
                continue

            # Streaming de respuesta con Gemini probando fallback entre modelos
            try:
                response, modelo_usado = generar_stream_con_fallback(
                    client,
                    f"{contexto}\n\nEl usuario ({usuario}) pregunta en la app móvil: '{pregunta}'"
                )
                for chunk in response:
                    if chunk.text:
                        await websocket.send_json({
                            "tipo": "chunk",
                            "texto": chunk.text,
                            "modelo": modelo_usado
                        })
                        await asyncio.sleep(0.02)

                await websocket.send_json({"tipo": "fin"})

            except Exception as e:
                await websocket.send_json({
                    "tipo": "error",
                    "texto": f"Error en streaming de IA: {e}"
                })

    except WebSocketDisconnect:
        print("Cliente móvil desconectado del WebSocket de IA")
