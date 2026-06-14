# tests/test_simulate_booking.py
import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, obtener_historial

async def main():
    await inicializar_db()
    telefono = "test-booking-001"
    
    mensaje = "Hola, me gustaría reservar el glamping nido de amor para el 2026-06-25. Mi nombre es Juan Pérez, whatsapp +573102223344, email juan@perez.com, somos 2 personas y no tenemos notas adicionales."
    print(f"Usuario: {mensaje}\n")
    
    historial = await obtener_historial(telefono)
    respuesta, media_url = await generar_respuesta(mensaje, historial)
    
    print(f"Loqui: {respuesta}")
    if media_url:
        print(f"[Imagen: {media_url}]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
