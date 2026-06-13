# tests/configure_twilio_webhook.py
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
webhook_url = "https://fincaloquillo-production.up.railway.app/webhook"

async def configure():
    print("Configurando webhook de Twilio...")
    # URL de la API de Twilio para actualizar la configuración de su Sandbox
    # El Sandbox de Twilio se gestiona a nivel de servicio de mensajería o configurando el webhook global del Sandbox
    # Para cambiar el webhook del Sandbox de WhatsApp directamente, se actualiza la configuración de la cuenta.
    
    # Intentamos listar los números y servicios asociados
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/IncomingPhoneNumbers.json"
    auth = (account_sid, auth_token)
    
    async with httpx.AsyncClient() as client:
        # Los mensajes de Sandbox de WhatsApp normalmente se envían a la URL configurada en la sección "WhatsApp Sandbox Settings" de la consola.
        # No se pueden configurar de forma programática a través de la API estándar de números de teléfono entrantes (ya que es un número compartido).
        # Sin embargo, podemos consultar si hay registros de errores en la API de alertas de Twilio para diagnosticar el problema.
        
        alerts_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Monitor/Alerts.json"
        response = await client.get(alerts_url, auth=auth)
        if response.status_code == 200:
            alerts = response.json().get("alerts", [])
            if alerts:
                print("\nÚltimas alertas/errores detectados en Twilio:")
                for alert in alerts[:3]:
                    print(f"- {alert.get('alert_text')} (Código: {alert.get('error_code')})")
            else:
                print("\nNo se detectaron alertas de error recientes en la API de Twilio.")
        else:
            print("No se pudo consultar el registro de alertas de Twilio.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(configure())
