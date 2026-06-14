# agent/brain.py — Cerebro del agente con OpenCode (API compatible con OpenAI)
# Generado por AgentKit
#
# Soporta autenticación a Google via:
#  1. GOOGLE_SERVICE_ACCOUNT_JSON (recomendado para producción, nunca expira)
#  2. GOOGLE_CREDENTIALS_JSON (OAuth2 desktop, fallback)

import os
import yaml
import logging
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
logger = logging.getLogger("agentkit")

# Configurar cliente de OpenAI apuntando a OpenCode
OPENCODE_BASE_URL = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/go/v1")
opencode_api_key = os.getenv("OPENCODE_API_KEY") or os.getenv("OPENAI_API_KEY")

if opencode_api_key:
    openai_client = OpenAI(base_url=OPENCODE_BASE_URL, api_key=opencode_api_key)
else:
    openai_client = None
    logger.warning("OPENCODE_API_KEY no encontrada en las variables de entorno.")

from agent.tools import (
    verificar_disponibilidad_glamping,
    verificar_disponibilidad_rango,
    obtener_imagen_glamping,
    registrar_reserva
)


# ─────────────────────────────────────────────────────────────
# DECLARACIONES DE HERRAMIENTAS PARA OPENAI FUNCTION CALLING
# ─────────────────────────────────────────────────────────────

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "verificar_disponibilidad_glamping",
            "description": "Verifica si un glamping está disponible para una fecha específica en formato YYYY-MM-DD.",
            "parameters": {
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
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verificar_disponibilidad_rango",
            "description": "Consulta las próximas fechas disponibles para un glamping en los próximos 30 días.",
            "parameters": {
                "type": "object",
                "properties": {
                    "glamping": {
                        "type": "string",
                        "description": "Nombre del glamping: 'Nido de Amor' o 'Vista Hermosa'."
                    }
                },
                "required": ["glamping"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_imagen_glamping",
            "description": "Retorna la URL de una imagen real del glamping solicitado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "glamping": {
                        "type": "string",
                        "description": "Nombre del glamping: 'Nido de Amor' o 'Vista Hermosa'."
                    }
                },
                "required": ["glamping"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_reserva",
            "description": "Registra una solicitud de reserva pendiente para un glamping.",
            "parameters": {
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
        }
    }
]

# Modelo por defecto: deepseek-v4-flash es el más económico de OpenCode Go
OPENCODE_MODEL = os.getenv("OPENCODE_MODEL", "deepseek-v4-flash")


# ─────────────────────────────────────────────────────────────
# CARGA DE CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────

def cargar_config_prompts() -> dict:
    try:
        with open("config/prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/prompts.yaml no encontrado")
        return {}


def cargar_system_prompt() -> str:
    config = cargar_config_prompts()
    return config.get("system_prompt", "Eres Loqui, el asistente virtual de Finca Loquillo en Buesaco. Responde en español.")


def obtener_mensaje_error() -> str:
    config = cargar_config_prompts()
    return config.get("error_message", "Lo siento, estoy teniendo problemas técnicos. Por favor intenta de nuevo en unos minutos.")


def obtener_mensaje_fallback() -> str:
    config = cargar_config_prompts()
    return config.get("fallback_message", "Disculpa, no entendí tu mensaje. ¿Podrías reformularlo?")


# ─────────────────────────────────────────────────────────────
# GENERACIÓN DE RESPUESTAS
# ─────────────────────────────────────────────────────────────

def _build_messages(mensaje: str, historial: list[dict]) -> list:
    messages = [{"role": "system", "content": cargar_system_prompt()}]
    for msg in historial:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": mensaje})
    return messages


def _ejecutar_funcion(name: str, args: dict) -> tuple[str, str | None]:
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
    Genera una respuesta usando OpenCode (API compatible con OpenAI).
    """
    if not mensaje or len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback(), None

    if not openai_client:
        return "[Modo Simulado - Loqui]: ¡Hola! Para responderte con IA necesito configurar OPENCODE_API_KEY.", None

    messages = _build_messages(mensaje, historial)

    try:
        response = openai_client.chat.completions.create(
            model=OPENCODE_MODEL,
            messages=messages,
            tools=OPENAI_TOOLS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=800
        )

        response_message = response.choices[0].message
        media_url = None

        if response_message.tool_calls:
            messages.append(response_message)

            for tool_call in response_message.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                logger.info(f"OpenCode solicitó llamar a la función: {name} con argumentos {args}")

                resultado_funcion, url_imagen = _ejecutar_funcion(name, args)
                if url_imagen:
                    media_url = url_imagen

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": name,
                    "content": resultado_funcion
                })

            response_final = openai_client.chat.completions.create(
                model=OPENCODE_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            return response_final.choices[0].message.content or obtener_mensaje_fallback(), media_url

        return response_message.content or obtener_mensaje_fallback(), None

    except Exception as e:
        logger.error(f"Error OpenCode/OpenAI API con Function Calling: {e}")
        return obtener_mensaje_error(), None
