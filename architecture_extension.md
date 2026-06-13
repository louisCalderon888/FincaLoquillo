# Extensión de Casos de Uso en Finca Loquillo

Esta guía explica técnicamente cómo expandir las capacidades de tu agente de WhatsApp utilizando la arquitectura modular de AgentKit + Gemini.

## 1. Patrón Arquitectónico de AgentKit

El flujo actual es:
```
[WhatsApp] ── Twilio ──> [FastAPI (main.py)] ──> [Brain (brain.py)] ──> [Gemini API]
                                                       │
                                                       └── (Si requiere datos) ──> [Tools (tools.py)]
```

Para dotar al agente de nuevas capacidades (como verificar reservas reales, registrar clientes, calcular cotizaciones o enviar enlaces de pago), extendemos principalmente **`agent/tools.py`** y enseñamos a **`agent/brain.py`** a invocar estas funciones.

---

## 2. Ejemplo: Integración de Reservas en Google Calendar / CRM

### Paso 1: Definir la herramienta en `agent/tools.py`
Agrega una función que haga la petición externa:

```python
import httpx

def crear_reserva_crm(telefono: str, nombre: str, fecha: str, glamping_tipo: str) -> str:
    """
    Registra una reserva en tu base de datos o CRM de reservas.
    """
    try:
        # Ejemplo de envío de datos a un webhook de automatización (Make.com, n8n, Zapier o base de datos propia)
        # payload = {"telefono": telefono, "nombre": nombre, "fecha": fecha, "glamping": glamping_tipo}
        # httpx.post("https://mi-crm.com/api/reservas", json=payload)
        
        # Guardamos localmente o retornamos la confirmación
        return f"¡Listo! Registré tu solicitud de reserva para el {glamping_tipo} el día {fecha} a nombre de {nombre}."
    except Exception as e:
        return f"Lo siento, ocurrió un problema al registrar la reserva en el sistema: {str(e)}"
```

### Paso 2: Habilitar Function Calling en Gemini (`agent/brain.py`)
Gemini admite la definición de herramientas (Tools). Puedes declarar la función en la configuración del modelo de Gemini para que decida llamarla automáticamente cuando el usuario pida agendar una noche de glamping.

---

## 3. Ejemplo: Pasarela de Pago Dinámica (Wompi, Bold, MercadoPago)
Si deseas que el agente genere y envíe un link de cobro real:

1. Creas una función `generar_link_pago(monto: int, descripcion: str)` en `agent/tools.py`.
2. Esta función se conecta a la API de tu pasarela de pago y devuelve un enlace único (ej. `https://wompi.co/pay/123xyz`).
3. El agente recibe ese link desde la función y se lo envía al cliente de manera amigable por WhatsApp: 
   *"Aquí tienes el link de pago para confirmar tu reserva del Glamping Nido de Amor por $180,000 COP: [link]"*.
