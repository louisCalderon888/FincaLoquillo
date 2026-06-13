# agent/brain.py — Cerebro del agente: conexión con Gemini API
# Generado por AgentKit

"""
Lógica de IA del agente. Lee el system prompt de prompts.yaml
y genera respuestas usando la API de Google Gemini.
"""

import os
import yaml
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("agentkit")

# Configurar API Key de Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("GEMINI_API_KEY no encontrada en las variables de entorno.")


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


async def generar_respuesta(mensaje: str, historial: list[dict]) -> str:
    """
    Genera una respuesta usando Gemini API.
    """
    if not mensaje or len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback()

    api_key_env = os.getenv("GEMINI_API_KEY")
    if not api_key_env:
        return "[Modo Simulado - Loqui]: ¡Hola! Para responderte de verdad necesito que agregues tu GEMINI_API_KEY en el archivo .env. Por ahora, simulo decirte que Finca Loquillo es hermosa, cobramos $10.000 la entrada y ofrecemos Glampings espectaculares desde $180.000. ¿Qué te gustaría saber?"

    system_prompt = cargar_system_prompt()

    # Formatear el historial de chat al formato esperado por Gemini (contents)
    contents = []
    for msg in historial:
        # Mapear roles: SQLAlchemy almacena 'assistant', Gemini espera 'model'
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [msg["content"]]
        })

    # Agregar el mensaje actual del usuario
    contents.append({
        "role": "user",
        "parts": [mensaje]
    })

    try:
        # Inicializar el modelo con las instrucciones del sistema (system_instruction)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_prompt
        )

        # Usar run_in_executor para ejecutar la llamada síncrona de Gemini de manera asíncrona
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Llamar a la API de Gemini
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(contents)
        )

        respuesta = response.text
        logger.info("Respuesta generada con Gemini con éxito")
        return respuesta

    except Exception as e:
        logger.error(f"Error Gemini API: {e}")
        return obtener_mensaje_error()
