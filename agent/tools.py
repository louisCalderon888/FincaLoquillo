# agent/tools.py — Herramientas del agente con integración a Google Sheets y Google Calendar
# Generado por AgentKit y mejorado para reservas en tiempo real con OAuth2 Desktop Flow

import os
import json
import yaml
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("agentkit")

# ─────────────────────────────────────────────────────────────
# BASE DE DATOS DE DISPONIBILIDAD EN MEMORIA (FALLBACK MOCK)
# ─────────────────────────────────────────────────────────────
RESERVAS_MOCK = {
    "nido de amor": ["2026-06-15", "2026-06-20", "2026-06-21"],
    "vista hermosa": ["2026-06-15", "2026-06-16", "2026-06-22"]
}

FOTOS_GLAMPING = {
    "nido de amor": "https://images.unsplash.com/photo-1544644181-1484b3fdfc62?auto=format&fit=crop&w=800&q=80",
    "vista hermosa": "https://images.unsplash.com/photo-1510312305653-8ed496efae75?auto=format&fit=crop&w=800&q=80"
}


def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    """Retorna el horario de atención del negocio."""
    info = cargar_info_negocio()
    return {
        "horario": info.get("negocio", {}).get("horario", "24/7"),
        "esta_abierto": True,
    }


def buscar_en_knowledge(consulta: str) -> str:
    """Busca información relevante en los archivos de /knowledge."""
    resultados = []
    knowledge_dir = "knowledge"
    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."
    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue
    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica en mis archivos locales."


# ─────────────────────────────────────────────────────────────
# AUXILIAR: AUTENTICACIÓN GOOGLE APIS CON OAUTH2
# ─────────────────────────────────────────────────────────────

def _obtener_credenciales_google():
    """
    Obtiene credenciales de Google.
    1. Intenta cargar desde la variable de entorno GOOGLE_CREDENTIALS_JSON (soporta Service Account u OAuth2 Token).
    2. Intenta cargar desde el archivo local config/token.json.
    3. Si no existe y está en local, inicia el flujo interactivo de OAuth2 Desktop con config/client_secret.json.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2 import service_account

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/calendar"
    ]

    # 1. Intentar cargar desde la variable de entorno GOOGLE_CREDENTIALS_JSON
    google_creds_env = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if google_creds_env:
        try:
            creds_data = json.loads(google_creds_env)
            if creds_data.get("type") == "service_account":
                logger.info("Autenticando con Cuenta de Servicio desde GOOGLE_CREDENTIALS_JSON")
                return service_account.Credentials.from_service_account_info(creds_data, scopes=SCOPES)
            else:
                logger.info("Autenticando con Credenciales de Usuario (OAuth2) desde GOOGLE_CREDENTIALS_JSON")
                return Credentials.from_authorized_user_info(creds_data, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Error cargando credenciales desde GOOGLE_CREDENTIALS_JSON de env: {e}")

    creds = None
    token_path = "config/token.json"
    client_secret_path = "config/client_secret.json"

    # 2. Intentar cargar credenciales del token.json existente
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            logger.info("Cargadas credenciales desde config/token.json")
        except Exception as e:
            logger.error(f"Error cargando token.json: {e}")

    # Si no hay credenciales válidas, solicitar al usuario que inicie sesión
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Token de OAuth2 refrescado con éxito")
                # Actualizar token.json con el nuevo token refrescado
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                logger.error(f"Error refrescando token: {e}")
                creds = None

        if not creds:
            if not os.path.exists(client_secret_path):
                logger.warning(
                    f"No se encontró {client_secret_path} ni variable GOOGLE_CREDENTIALS_JSON. "
                    "Se utilizará el modo simulado (mock)."
                )
                return None

            try:
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
                # Ejecutar servidor local para capturar el código de autorización
                creds = flow.run_local_server(port=0, open_browser=True)
                
                # Guardar credenciales para la próxima ejecución
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
                logger.info("Flujo interactivo completado y credenciales guardadas en config/token.json")
            except Exception as e:
                logger.error(f"Error en flujo interactivo OAuth2: {e}")
                return None

    return creds


def _obtener_cliente_sheets():
    """Autentica con Google Sheets usando las credenciales obtenidas."""
    import gspread
    creds = _obtener_credenciales_google()
    if not creds:
        raise FileNotFoundError("Credenciales OAuth2 no configuradas correctamente.")
    return gspread.authorize(creds)


def _obtener_servicio_calendar():
    """Autentica y obtiene servicio de Google Calendar API."""
    from googleapiclient.discovery import build
    creds = _obtener_credenciales_google()
    if not creds:
        raise FileNotFoundError("Credenciales OAuth2 no configuradas correctamente.")
    return build('calendar', 'v3', credentials=creds)


# ─────────────────────────────────────────────────────────────
# FUNCIONES DE DISPONIBILIDAD (CONEXIÓN GOOGLE CALENDAR O MOCK)
# ─────────────────────────────────────────────────────────────

def normalizar_nombre_glamping(glamping: str) -> str:
    """Normaliza el nombre del glamping para consistencia."""
    nombre = glamping.lower().strip()
    if "nido" in nombre or "amor" in nombre:
        return "Nido de Amor"
    elif "vista" in nombre or "hermosa" in nombre:
        return "Vista Hermosa"
    return ""


def obtener_fechas_ocupadas_calendar(glamping_normalizado: str) -> list[str]:
    """
    Consulta Google Calendar para obtener las fechas en formato YYYY-MM-DD
    ocupadas por reservas del glamping especificado.
    """
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
    if not calendar_id:
        logger.warning("GOOGLE_CALENDAR_ID no configurado. Usando mock.")
        return RESERVAS_MOCK.get(glamping_normalizado.lower(), [])

    try:
        service = _obtener_servicio_calendar()
        
        ahora = datetime.utcnow()
        time_min = ahora.isoformat() + 'Z'
        time_max = (ahora + timedelta(days=90)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        ocupadas = []
        for event in events:
            summary = event.get('summary', '').lower()
            if glamping_normalizado.lower() in summary:
                start = event.get('start', {}).get('date') or event.get('start', {}).get('dateTime')
                if start:
                    fecha_str = start[:10]
                    if fecha_str not in ocupadas:
                        ocupadas.append(fecha_str)
        return ocupadas
    except Exception as e:
        logger.error(f"Error consultando Google Calendar: {e}. Usando mock.")
        return RESERVAS_MOCK.get(glamping_normalizado.lower(), [])


def verificar_disponibilidad_glamping(glamping: str, fecha: str) -> str:
    """
    Verifica si un tipo de glamping está disponible para una fecha específica.
    """
    glamping_normalizado = normalizar_nombre_glamping(glamping)
    if not glamping_normalizado:
        return "Solo tenemos el 'Glamping Nido de Amor' y el 'Glamping Vista Hermosa'. ¿Cuál te gustaría consultar?"

    try:
        fechas_ocupadas = obtener_fechas_ocupadas_calendar(glamping_normalizado)
    except Exception:
        fechas_ocupadas = RESERVAS_MOCK.get(glamping_normalizado.lower(), [])

    if fecha in fechas_ocupadas:
        return f"Lo siento, el Glamping {glamping_normalizado} está RESERVADO para el {fecha}. Te sugiero consultar otra fecha."
    else:
        return f"¡Buenas noticias! El Glamping {glamping_normalizado} está DISPONIBLE para el {fecha}. Puedes reservarlo con el 50% de abono."


def verificar_disponibilidad_rango(glamping: str) -> str:
    """
    Retorna las fechas disponibles para los próximos 30 días para un glamping dado.
    """
    glamping_normalizado = normalizar_nombre_glamping(glamping)
    if not glamping_normalizado:
        return "Solo tenemos el 'Glamping Nido de Amor' y el 'Glamping Vista Hermosa'. ¿Cuál te gustaría consultar?"

    try:
        fechas_ocupadas = obtener_fechas_ocupadas_calendar(glamping_normalizado)
    except Exception:
        fechas_ocupadas = RESERVAS_MOCK.get(glamping_normalizado.lower(), [])

    hoy = datetime.now()
    disponibles = []
    
    for i in range(1, 31):
        dia = (hoy + timedelta(days=i)).strftime("%Y-%m-%d")
        if dia not in fechas_ocupadas:
            disponibles.append(dia)
            if len(disponibles) >= 7:
                break

    if disponibles:
        disponibles_formateado = ", ".join(disponibles)
        return f"Para el Glamping {glamping_normalizado}, las siguientes fechas están disponibles próximamente:\n{disponibles_formateado}."
    else:
        return f"Lo siento, no encontré fechas disponibles próximas para el Glamping {glamping_normalizado}."


def obtener_imagen_glamping(glamping: str) -> str:
    """
    Retorna la URL de la imagen asociada al glamping solicitado.
    """
    glamping_normalizado = normalizar_nombre_glamping(glamping)
    if glamping_normalizado:
        return FOTOS_GLAMPING.get(glamping_normalizado.lower(), "")
    return ""


# ─────────────────────────────────────────────────────────────
# REGISTRO DE RESERVA (GOOGLE SHEETS Y GOOGLE CALENDAR)
# ─────────────────────────────────────────────────────────────

def registrar_reserva(
    nombre_cliente: str,
    telefono: str,
    email: str,
    whatsapp: str,
    glamping: str,
    fecha_reserva: str,
    num_personas: str = "1",
    notas: str = ""
) -> str:
    """
    Registra una reserva pendiente en Google Sheets y bloquea la fecha en Google Calendar.
    """
    glamping_normalizado = normalizar_nombre_glamping(glamping)
    if not glamping_normalizado:
        return "No pude identificar el glamping seleccionado para realizar la reserva. Por favor especifica 'Nido de Amor' o 'Vista Hermosa'."

    SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
    CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "")

    # Fallback local / simulación si no se ha configurado OAuth ni credenciales
    if not os.path.exists("config/client_secret.json") and not os.path.exists("config/token.json"):
        logger.warning("No se detectan credenciales de Google OAuth. Simulando reserva en local.")
        key = glamping_normalizado.lower()
        if key in RESERVAS_MOCK:
            if fecha_reserva not in RESERVAS_MOCK[key]:
                RESERVAS_MOCK[key].append(fecha_reserva)
        return (
            f"¡Solicitud de Reserva Registrada (Modo Simulación)! 🎉\n\n"
            f"📋 Resumen:\n"
            f"- Nombre: {nombre_cliente}\n"
            f"- WhatsApp: {whatsapp}\n"
            f"- Email: {email}\n"
            f"- Glamping: {glamping_normalizado}\n"
            f"- Fecha: {fecha_reserva}\n"
            f"- Personas: {num_personas}\n"
            f"- Notas: {notas}\n"
            f"- Estado: Pendiente confirmación\n\n"
            "El equipo de Finca Loquillo te contactará pronto para confirmar el abono del 50%. 🌲"
        )

    # Registrar en Google Sheets
    try:
        gc = _obtener_cliente_sheets()
        sheet = gc.open_by_key(SHEET_ID)

        try:
            worksheet = sheet.worksheet("Reservas")
        except Exception:
            worksheet = sheet.add_worksheet(title="Reservas", rows=1000, cols=10)
            encabezados = [
                "Fecha de Solicitud", "Nombre Cliente", "WhatsApp",
                "Email", "Glamping", "Fecha de Llegada", "N° Personas",
                "Estado Pago", "Notas"
            ]
            worksheet.append_row(encabezados)

        nueva_fila = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            nombre_cliente,
            whatsapp,
            email,
            glamping_normalizado,
            fecha_reserva,
            num_personas,
            "Pendiente confirmación",
            notas
        ]
        worksheet.append_row(nueva_fila)
        logger.info(f"Fila agregada a Google Sheets para {nombre_cliente}")
    except Exception as e:
        logger.error(f"Error escribiendo en Google Sheets: {e}")

    # Crear evento en Google Calendar para bloquear la fecha
    if CALENDAR_ID:
        try:
            service = _obtener_servicio_calendar()
            evento = {
                'summary': f'RESERVA PENDIENTE: Glamping {glamping_normalizado} - {nombre_cliente}',
                'description': f'Reserva registrada por asistente virtual.\nCliente: {nombre_cliente}\nTeléfono: {whatsapp}\nEmail: {email}\nPersonas: {num_personas}\nNotas: {notas}',
                'start': {
                    'date': fecha_reserva,
                },
                'end': {
                    'date': (datetime.strptime(fecha_reserva, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"),
                },
            }
            service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()
            logger.info(f"Evento creado en Google Calendar para {fecha_reserva}")
        except Exception as e:
            logger.error(f"Error creando evento en Google Calendar: {e}")
            
    key = glamping_normalizado.lower()
    if key in RESERVAS_MOCK:
        if fecha_reserva not in RESERVAS_MOCK[key]:
            RESERVAS_MOCK[key].append(fecha_reserva)

    resumen = (
        f"¡Solicitud de reserva registrada con éxito! 🎉\n\n"
        f"📋 Detalle de la Solicitud:\n"
        f"- Nombre: {nombre_cliente}\n"
        f"- WhatsApp: {whatsapp}\n"
        f"- Email: {email}\n"
        f"- Glamping: {glamping_normalizado}\n"
        f"- Fecha de llegada: {fecha_reserva}\n"
        f"- Personas: {num_personas}\n"
        f"- Notas: {notas}\n"
        f"- Estado: Pendiente confirmación\n\n"
        f"Para confirmar tu reserva, realiza el abono del 50% y envía el comprobante por este medio. "
        f"Un miembro del equipo revisará la información y te dará confirmación definitiva. ¡Te esperamos! 🌲"
    )

    return resumen
