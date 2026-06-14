# tests/test_reservation.py
import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools import registrar_reserva, verificar_disponibilidad_rango

def main():
    print("=== Probando verificación de disponibilidad ===")
    rango = verificar_disponibilidad_rango("nido de amor")
    print(rango)
    print()
    
    print("=== Probando registro de reserva ===")
    resumen = registrar_reserva(
        nombre_cliente="Cliente de Prueba",
        telefono="test-phone",
        email="prueba@finca.com",
        whatsapp="+573000000000",
        glamping="nido de amor",
        fecha_reserva="2026-06-25",
        num_personas="2",
        notas="Test de integración directo"
    )
    print(resumen)

if __name__ == "__main__":
    main()
