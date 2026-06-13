# agent/brain.py — Cerebro del agente con soporte de Function Calling para Gemini API
# Generado por AgentKit

import os
import yaml
import logging
import json
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

from agent.tools import verificar_disponibilidad_glamping, obtener_imagen_glamping, registrar_reserva_sheets


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


async def generar_respuesta(mensaje: str, historial: list[dict]) -> tuple[str, str]:
    """
    Genera una respuesta usando Gemini API y soporta retorno opcional de una URL de imagen (media_url).
    
    Returns:
        tuple: (texto_de_respuesta, media_url_opcional)
    """
    if not mensaje or len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback(), None

    api_key_env = os.getenv("GEMINI_API_KEY")
    if not api_key_env:
        return "[Modo Simulado - Loqui]: ¡Hola! Para responderte con IA necesito la clave de Gemini en el .env.", None

    system_prompt = cargar_system_prompt()

    # Formatear el historial
    contents = []
    for msg in historial:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [msg["content"]]
        })

    # Mensaje actual
    contents.append({
        "role": "user",
        "parts": [mensaje]
    })

    try:
        # Declaramos las herramientas que Gemini puede usar
        # Para mantener el flujo asíncrono robusto y rápido, usaremos el SDK de Google Generative AI declarando las funciones nativas.
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_prompt,
            tools=[verificar_disponibilidad_glamping, obtener_imagen_glamping, registrar_reserva_sheets]
        )

        import asyncio
        loop = asyncio.get_event_loop()
        
        # Llamar a Gemini de forma asíncrona
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(contents)
        )

        media_url = None
        respuesta_texto = ""

        # Verificar si Gemini decidió llamar a alguna función (Function Call)
        # Si Gemini llama a una función, la ejecutamos y le devolvemos el resultado a Gemini para que termine de dar la respuesta final al cliente.
        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            
            # ¿Es una llamada a función?
            if part.function_call:
                function_call = part.function_call
                name = function_call.name
                args = function_call.args
                
                logger.info(f"Gemini solicitó llamar a la función: {name} con argumentos {args}")
                
                # Ejecutar la función solicitada
                if name == "verificar_disponibilidad_glamping":
                    glamping = args.get("glamping")
                    fecha = args.get("fecha")
                    resultado_funcion = verificar_disponibilidad_glamping(glamping, fecha)
                    
                    # Volver a llamar a Gemini pasándole el resultado de la función
                    # Añadir la respuesta del modelo solicitando la llamada y la respuesta de la función al historial
                    contents.append(response.candidates[0].content)
                    contents.append({
                        "role": "function",
                        "parts": [{
                            "function_response": {
                                "name": "verificar_disponibilidad_glamping",
                                "response": {"result": resultado_funcion}
                            }
                        }]
                    })
                    
                    response_final = await loop.run_in_executor(
                        None,
                        lambda: model.generate_content(contents)
                    )
                    respuesta_texto = response_final.text
                    
                elif name == "registrar_reserva_sheets":
                    resultado_funcion = registrar_reserva_sheets(
                        nombre_cliente=args.get("nombre_cliente", ""),
                        telefono=args.get("telefono", ""),
                        glamping=args.get("glamping", ""),
                        fecha_reserva=args.get("fecha_reserva", ""),
                        num_personas=args.get("num_personas", "1"),
                        almuerzos=args.get("almuerzos", "No"),
                        notas=args.get("notas", "")
                    )
                    contents.append(response.candidates[0].content)
                    contents.append({
                        "role": "function",
                        "parts": [{
                            "function_response": {
                                "name": "registrar_reserva_sheets",
                                "response": {"result": resultado_funcion}
                            }
                        }]
                    })
                    response_final = await loop.run_in_executor(
                        None,
                        lambda: model.generate_content(contents)
                    )
                    respuesta_texto = response_final.text

                elif name == "obtener_imagen_glamping":
                    glamping = args.get("glamping")
                    media_url = obtener_imagen_glamping(glamping)
                    
                    # Le informamos a Gemini que obtuvimos la foto para que complemente la respuesta
                    resultado_funcion = f"URL de imagen obtenida con éxito: {media_url}. Envía un mensaje amigable al cliente confirmando el envío de la foto."
                    contents.append(response.candidates[0].content)
                    contents.append({
                        "role": "function",
                        "parts": [{
                            "function_response": {
                                "name": "obtener_imagen_glamping",
                                "response": {"result": resultado_funcion}
                            }
                        }]
                    })
                    
                    response_final = await loop.run_in_executor(
                        None,
                        lambda: model.generate_content(contents)
                    )
                    respuesta_texto = response_final.text
            else:
                respuesta_texto = response.text
        else:
            respuesta_texto = response.text

        return respuesta_texto, media_url

    except Exception as e:
        logger.error(f"Error Gemini API con Function Calling: {e}")
        return obtener_mensaje_error(), None
