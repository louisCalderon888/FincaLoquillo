# tests/test_local.py — Simulador de chat en terminal
# Generado por AgentKit

"""
Prueba tu agente sin necesitar WhatsApp.
Simula una conversación en la terminal.
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, limpiar_historial

TELEFONO_TEST = "test-local-001"


async def main():
    """Loop principal del chat de prueba."""
    await inicializar_db()

    print()
    print("=" * 55)
    print("   AgentKit — Test Local (Finca Loquillo)")
    print("=" * 55)
    print()
    print("  Escribe mensajes como si fueras un cliente de Finca Loquillo.")
    print("  Comandos especiales:")
    print("    'limpiar'  — borra el historial de esta conversación")
    print("    'salir'    — termina el test")
    print()
    print("-" * 55)
    print()

    while True:
        try:
            # Entrada de usuario compatible con codificación utf-8 de consola
            mensaje = input("Tu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nTest finalizado.")
            break

        if not mensaje:
            continue

        if mensaje.lower() == "salir":
            print("\nTest finalizado.")
            break

        if mensaje.lower() == "limpiar":
            await limpiar_historial(TELEFONO_TEST)
            print("[Historial borrado]\n")
            continue

        # Obtener historial
        historial = await obtener_historial(TELEFONO_TEST)

        # Generar respuesta
        print("\nLoqui: ", end="", flush=True)
        respuesta, media_url = await generar_respuesta(mensaje, historial)
        print(respuesta)
        if media_url:
            print(f"[Imagen adjunta: {media_url}]")
        print()

        # Guardar historial
        await guardar_mensaje(TELEFONO_TEST, "user", mensaje)
        await guardar_mensaje(TELEFONO_TEST, "assistant", respuesta)


if __name__ == "__main__":
    # Evitar problemas de bucles de eventos asyncio en Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
