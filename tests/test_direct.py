# tests/test_direct.py
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Asegurar que la salida en consola use UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial

async def test():
    await inicializar_db()
    telefono = "test-direct-001"
    
    mensaje = "Hola! Quisiera saber qué glampings tienen disponibles, qué incluyen y qué precio tienen por noche. También si venden almuerzos."
    print(f"Usuario: {mensaje}\n")
    
    historial = await obtener_historial(telefono)
    respuesta = await generar_respuesta(mensaje, historial)
    
    print(f"Loqui: {respuesta}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test())
