# agent/brain.py — Cerebro del agente con Google GenAI (SDK oficial)
# Generado por AgentKit

import os
import yaml
import logging
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger("agentkit")

# Configurar cliente de Google GenAI
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai_client = genai.Client(api_key=api_key)
else:
    genai_client = None
    logger.warning("GEMINI_API_KEY no encontrada en las variables de entorno.")

from agent.tools import (
    verificar_disponibilidad_glamping,
    verificar_disponibilidad_rango,
    obtener_imagen_glamping,
    registrar_reserva
)


# ─────────────────────────────────────────────────────────────
# DECLARACIONES DE HERRAMIENTAS PARA GEMINI
# ─────────────────────────────────────────────────────────────

GEMINI_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="verificar_disponibilidad_glamping",
            description="Verifica si un glamping está disponible para una fecha específica en formato YYYY-MM-DD.",
            parameters={
                "type": "object",
                "properties": {
                    "glamping": {
                        "type": "string",
                        "description": "Nombre del glamping: 'Nido de Amor' o 'Vista Hermosa'."
                    },
                    "fecha": {
                        "type": "string",
                        "description": "Fecha a consultar en formato YYYY-MM-DD."
                    }
                },
                "required": ["glamping", "fecha"]
            }
        ),
        types.FunctionDeclaration(
            name="verificar_disponibilidad_rango",
            description="Consulta las próximas fechas disponibles para un glamping en los próximos 30 días.",
            parameters={
                "type": "object",
                "properties": {
                    "glamping": {
                        "type": "string",
                        "description": "Nombre del glamping: 'Nido de Amor' o 'Vista Hermosa'."
                    }
                },
                "required": ["glamping"]
            }
        ),
        types.FunctionDeclaration(
            name="obtener_imagen_glamping",
            description="Retorna la URL de una imagen real del glamping solicitado.",
            parameters={
                "type": "object",
                "properties": {
                    "glamping": {
                        "type": "string",
                        "description": "Nombre del glamping: 'Nido de Amor' o 'Vista Hermosa'."
                    }
                },
                "required": ["glamping"]
            }
        ),
        types.FunctionDeclaration(
            name="registrar_reserva",
            description="Registra una solicitud de reserva pendiente para un glamping.",
            parameters={
                "type": "object",
                "properties": {
                    "nombre_cliente": {"type": "string", "description": "Nombre completo del cliente."},
                    "telefono": {"type": "string", "description": "Número de teléfono del cliente."},
                    "email": {"type": "string", "description": "Correo electrónico del cliente."},
                    "whatsapp": {"type": "string", "description": "Número de WhatsApp de contacto."},
                    "glamping": {"type": "string", "description": "Nombre del glamping: 'Nido de Amor' o 'Vista Hermosa'."},
                    "fecha_reserva": {"type": "string", "description": "Fecha de llegada en formato YYYY-MM-DD."},
                    "num_personas": {"type": "string", "description": "Cantidad de personas (default '1')."},
                    "notas": {"type": "string", "description": "Notas u observaciones especiales."}
                },
                "required": ["nombre_cliente", "telefono", "email", "whatsapp", "glamping", "fecha_reserva"]
            }
        )
    ])
]


# ─────────────────────────────────────────────────────────────
# CARGA DE CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────

def cargar_config_prompts() -> dict:
    """Lee toda la configuración desde config/prompts.yaml."""
    try:
        with open("config/prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/prompts.yaml no encontrado")
        return {}


def cargar_system_prompt() -> str:
    """Lee el system prompt desde config/prompts.yaml."""
    config = cargar_config_prompts()
    return config.get("system_prompt", "Eres Loqui, el asistente virtual de Finca Loquillo en Buesaco. Responde en español.")


def obtener_mensaje_error() -> str:
    """Retorna el mensaje de error configurado en prompts.yaml."""
    config = cargar_config_prompts()
    return config.get("error_message", "Lo siento, estoy teniendo problemas técnicos. Por favor intenta de nuevo en unos minutos.")


def obtener_mensaje_fallback() -> str:
    """Retorna el mensaje de fallback configurado en prompts.yaml."""
    config = cargar_config_prompts()
    return config.get("fallback_message", "Disculpa, no entendí tu mensaje. ¿Podrías reformularlo?")


# ─────────────────────────────────────────────────────────────
# GENERACIÓN DE RESPUESTAS
# ─────────────────────────────────────────────────────────────

def _build_contents(mensaje: str, historial: list[dict]) -> list:
    """Construye la lista de contents para Google GenAI a partir del historial."""
    contents = []
    for msg in historial:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=mensaje)]))
    return contents


def _ejecutar_funcion(name: str, args: dict) -> tuple[str, str | None]:
    """
    Ejecuta la herramienta solicitada por Gemini.
    Retorna (resultado_texto, media_url_opcional).
    """
    media_url = None
    resultado = ""

    if name == "verificar_disponibilidad_glamping":
        resultado = verificar_disponibilidad_glamping(
            glamping=args.get("glamping", ""),
            fecha=args.get("fecha", "")
        )
    elif name == "verificar_disponibilidad_rango":
        resultado = verificar_disponibilidad_rango(
            glamping=args.get("glamping", "")
        )
    elif name == "obtener_imagen_glamping":
        media_url = obtener_imagen_glamping(
            glamping=args.get("glamping", "")
        )
        resultado = f"URL de imagen obtenida: {media_url}."
    elif name == "registrar_reserva":
        resultado = registrar_reserva(
            nombre_cliente=args.get("nombre_cliente", ""),
            telefono=args.get("telefono", ""),
            email=args.get("email", ""),
            whatsapp=args.get("whatsapp", ""),
            glamping=args.get("glamping", ""),
            fecha_reserva=args.get("fecha_reserva", ""),
            num_personas=args.get("num_personas", "1"),
            notas=args.get("notas", "")
        )
    else:
        resultado = f"Función desconocida: {name}"

    return resultado, media_url


async def generar_respuesta(mensaje: str, historial: list[dict]) -> tuple[str, str]:
    """
    Genera una respuesta usando Google GenAI y soporta retorno opcional de una URL de imagen.

    Returns:
        tuple: (texto_de_respuesta, media_url_opcional)
    """
    if not mensaje or len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback(), None

    if not genai_client:
        return "[Modo Simulado - Loqui]: ¡Hola! Para responderte con IA necesito la clave de Gemini en el .env.", None

    system_prompt = cargar_system_prompt()
    contents = _build_contents(mensaje, historial)

    try:
        # Primera llamada: Gemini puede decidir usar una herramienta
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=GEMINI_TOOLS,
                temperature=0.7
            )
        )

        media_url = None

        # ¿Gemini pidió function calls?
        if response.function_calls:
            for function_call in response.function_calls:
                name = function_call.name
                args = dict(function_call.args) if function_call.args else {}
                logger.info(f"Gemini solicitó llamar a la función: {name} con argumentos {args}")

                resultado_funcion, url_imagen = _ejecutar_funcion(name, args)
                if url_imagen:
                    media_url = url_imagen

                # Agregar la llamada y el resultado al historial
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))]
                ))
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(function_response=types.FunctionResponse(
                        name=name,
                        response={"result": resultado_funcion}
                    ))]
                ))

            # Segunda llamada: Gemini genera respuesta final en lenguaje natural
            response_final = genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=GEMINI_TOOLS,
                    temperature=0.7
                )
            )
            return response_final.text or obtener_mensaje_fallback(), media_url

        # Sin function calls: respuesta directa
        return response.text or obtener_mensaje_fallback(), None

    except Exception as e:
        logger.error(f"Error Google GenAI con Function Calling: {e}")
        return obtener_mensaje_error(), None
