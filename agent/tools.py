# agent/tools.py — Herramientas del agente con integración a Google Sheets y Google Calendar
# Generado por AgentKit y mejorado para reservas en tiempo real con OAuth2 Desktop Flow

import os
import json
import yaml
import logging
import sys
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("agentkit")

# ─────────────────────────────────────────────────────────────
# IMPORTS ROBUSTOS DE LIBRERÍAS GOOGLE
# ─────────────────────────────────────────────────────────────
GSPREAD_AVAILABLE = False
try:
    import gspread
    GSPREAD_AVAILABLE = True
except ImportError:
    logger.warning("gspread no está instalado. Las reservas usarán modo simulado.")

GOOGLE_API_CLIENT_AVAILABLE = False
try:
    from googleapiclient.discovery import build
    GOOGLE_API_CLIENT_AVAILABLE = True
except ImportError:
    logger.warning("google-api-python-client no está instalado. Calendar usará modo simulado.")

logger.info(f"Google libs disponibles — gspread: {GSPREAD_AVAILABLE}, googleapiclient: {GOOGLE_API_CLIENT_AVAILABLE}")

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

def _construir_credenciales_desde_dict(creds_data: dict, scopes: list):
    """
    Construye un objeto Credentials desde un dict JSON.
    Soporta los formatos:
    - service_account (cuenta de servicio)
    - authorized_user (gcloud ADC, formato con client_id/client_secret/refresh_token)
    - oauth2 token guardado por google_auth_oauthlib
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account

    tipo = creds_data.get("type", "")

    if tipo == "service_account":
        logger.info("Tipo: service_account")
        return service_account.Credentials.from_service_account_info(creds_data, scopes=scopes)

    # authorized_user (gcloud ADC) o token guardado por oauthlib
    # El formato de gcloud no incluye token_uri, lo añadimos explícitamente
    if not creds_data.get("token_uri"):
        creds_data["token_uri"] = "https://oauth2.googleapis.com/token"

    try:
        creds = Credentials.from_authorized_user_info(creds_data, scopes=scopes)
        logger.info("Credenciales de usuario OAuth2 construidas correctamente")
        if creds.expired or not creds.token:
            creds.refresh(Request())
            logger.info("Token refrescado correctamente")
        return creds
    except Exception:
        # Construcción manual (para formato authorized_user de gcloud)
        creds = Credentials(
            token=creds_data.get("access_token"),
            refresh_token=creds_data.get("refresh_token"),
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
            token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            scopes=scopes
        )
        if not creds.token or creds.expired:
            creds.refresh(Request())
            logger.info("Token refrescado correctamente (construcción manual)")
        return creds


def _obtener_credenciales_google():
    """
    Obtiene credenciales de Google.

    Orden de prioridad:
    1. GOOGLE_SERVICE_ACCOUNT_JSON (service account — recomendado, nunca expira)
    2. GOOGLE_CREDENTIALS_JSON (OAuth2 en variable de entorno)
    3. Archivo local config/token.json (desarrollo local)
    4. Flujo interactivo OAuth2 Desktop con config/client_secret.json (solo si hay TTY)
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/calendar"
    ]

    def _validar_service_account(data: dict) -> bool:
        return (
            data.get("type") == "service_account"
            and data.get("private_key")
            and data.get("client_email")
        )

    def _validar_oauth(data: dict) -> bool:
        campos = ["client_id", "client_secret", "refresh_token"]
        return all(data.get(c) for c in campos)

    # ── PRIORIDAD 1: GOOGLE_SERVICE_ACCOUNT_JSON ──
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        try:
            sa_data = json.loads(sa_json)
            if not _validar_service_account(sa_data):
                logger.error(
                    "GOOGLE_SERVICE_ACCOUNT_JSON no tiene formato de service account. "
                    "Campos requeridos: type=service_account, private_key, client_email"
                )
            else:
                creds = _construir_credenciales_desde_dict(sa_data, SCOPES)
                if creds:
                    logger.info(
                        f"Credenciales cargadas desde GOOGLE_SERVICE_ACCOUNT_JSON (service account: {sa_data.get('client_email')})"
                    )
                    return creds
        except json.JSONDecodeError as e:
            logger.error(f"GOOGLE_SERVICE_ACCOUNT_JSON no es un JSON válido: {e}")
        except Exception as e:
            logger.error(f"Error cargando service account: {e}")

    # ── PRIORIDAD 2: GOOGLE_CREDENTIALS_JSON (OAuth2) ──
    google_creds_env = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if google_creds_env:
        try:
            creds_data = json.loads(google_creds_env)
            if creds_data.get("type") == "service_account":
                if _validar_service_account(creds_data):
                    creds = _construir_credenciales_desde_dict(creds_data, SCOPES)
                    if creds:
                        logger.info("Service account detectada en GOOGLE_CREDENTIALS_JSON")
                        return creds
            elif not _validar_oauth(creds_data):
                logger.error("GOOGLE_CREDENTIALS_JSON no tiene client_id, client_secret ni refresh_token.")
            else:
                creds = _construir_credenciales_desde_dict(creds_data, SCOPES)
                if creds:
                    logger.info("Credenciales OAuth2 cargadas desde GOOGLE_CREDENTIALS_JSON")
                    return creds
        except json.JSONDecodeError as e:
            logger.error(f"GOOGLE_CREDENTIALS_JSON no es un JSON válido: {e}")
        except Exception as e:
            logger.error(f"Error cargando credenciales desde GOOGLE_CREDENTIALS_JSON: {e}")

    creds = None
    token_path = "config/token.json"
    client_secret_path = "config/client_secret.json"

    # ── PRIORIDAD 3: Archivo local token.json ──
    if os.path.exists(token_path):
        try:
            with open(token_path, "r") as f:
                token_data = json.load(f)
            if token_data.get("type") == "service_account" and _validar_service_account(token_data):
                creds = _construir_credenciales_desde_dict(token_data, SCOPES)
                logger.info("Service account cargada desde archivo local")
            elif not _validar_oauth(token_data):
                logger.error("El archivo de token local no tiene los campos mínimos requeridos.")
            else:
                creds = _construir_credenciales_desde_dict(token_data, SCOPES)
                logger.info("Credenciales OAuth2 cargadas desde archivo de token local")
        except Exception as e:
            logger.error(f"Error cargando credenciales locales: {e}")
            creds = None

    # Si no hay credenciales válidas, intentar refresh o flujo interactivo
    if not creds or not creds.valid:
        if creds and creds.expired and hasattr(creds, 'refresh_token') and creds.refresh_token:
            from google.auth.transport.requests import Request
            try:
                creds.refresh(Request())
                logger.info("Token de OAuth2 refrescado con éxito")
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                logger.error(f"Error refrescando token: {e}")
                creds = None

        if not creds:
            if not os.path.exists(client_secret_path):
                logger.warning(
                    "No se encontraron credenciales de Google configuradas. "
                    "Se utilizará el modo simulado (mock)."
                )
                return None

            # Evitar flujo interactivo en entornos sin TTY
            if not sys.stdin.isatty():
                logger.warning(
                    "Entorno no interactivo detectado. No se puede iniciar el flujo OAuth2 de escritorio. "
                    "Configura GOOGLE_SERVICE_ACCOUNT_JSON como variable de entorno."
                )
                return None

            try:
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
                creds = flow.run_local_server(port=0, open_browser=True)

                with open(token_path, "w") as token:
                    token.write(creds.to_json())
                logger.info("Flujo interactivo completado y credenciales guardadas localmente")
            except Exception as e:
                logger.error(f"Error en flujo interactivo OAuth2: {e}")
                return None

    return creds


def _obtener_cliente_sheets():
    """Autentica con Google Sheets usando las credenciales obtenidas."""
    if not GSPREAD_AVAILABLE:
        raise RuntimeError("gspread no está instalado.")
    creds = _obtener_credenciales_google()
    if not creds:
        raise FileNotFoundError("Credenciales OAuth2 no configuradas correctamente.")
    return gspread.authorize(creds)


def _obtener_servicio_calendar():
    """Autentica y obtiene servicio de Google Calendar API."""
    if not GOOGLE_API_CLIENT_AVAILABLE:
        raise RuntimeError("google-api-python-client no está instalado.")
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
        
        ahora = datetime.now(timezone.utc)
        time_min = ahora.isoformat()
        time_max = (ahora + timedelta(days=90)).isoformat()
        
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
    Si las credenciales o librerías no están disponibles, usa modo simulado (fallback) y
    lo informa claramente al cliente.
    """
    glamping_normalizado = normalizar_nombre_glamping(glamping)
    if not glamping_normalizado:
        return "No pude identificar el glamping seleccionado para realizar la reserva. Por favor especifica 'Nido de Amor' o 'Vista Hermosa'."

    SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
    CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "")

    # Determinar si podemos intentar Google APIs de verdad
    tiene_credenciales = bool(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        or os.getenv("GOOGLE_CREDENTIALS_JSON")
        or os.path.exists("config/token.json")
        or os.path.exists("config/client_secret.json")
    )
    puede_usar_sheets = bool(SHEET_ID and GSPREAD_AVAILABLE and tiene_credenciales)
    puede_usar_calendar = bool(CALENDAR_ID and GOOGLE_API_CLIENT_AVAILABLE and tiene_credenciales)

    sheets_ok = False
    calendar_ok = False

    if puede_usar_sheets:
        try:
            gc = _obtener_cliente_sheets()
            sheet = gc.open_by_key(SHEET_ID)

            try:
                worksheet = sheet.worksheet("Reservas")
            except Exception:
                worksheet = sheet.add_worksheet(title="Reservas", rows=1000, cols=12)
                encabezados = [
                    "Fecha de Solicitud", "Nombre Cliente", "Teléfono", "WhatsApp",
                    "Email", "Glamping", "Fecha de Llegada", "N° Personas",
                    "Precio Total", "Abono (50%)", "Estado Pago", "Notas"
                ]
                worksheet.append_row(encabezados)

            # Calcular precio según el glamping
            if "vista hermosa" in glamping_normalizado.lower():
                precio_total = 350000
            else:
                precio_total = 180000
            abono = precio_total // 2

            nueva_fila = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                nombre_cliente,
                telefono,
                whatsapp,
                email,
                glamping_normalizado,
                fecha_reserva,
                num_personas,
                f"${precio_total:,} COP".replace(",", "."),
                f"${abono:,} COP".replace(",", "."),
                "Pendiente confirmación",
                notas
            ]
            worksheet.append_row(nueva_fila)
            logger.info(f"Fila agregada a Google Sheets para {nombre_cliente}")
            sheets_ok = True
        except Exception as e:
            logger.error(f"Error escribiendo en Google Sheets: {e}")

    if puede_usar_calendar:
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
            calendar_ok = True
        except Exception as e:
            logger.error(f"Error creando evento en Google Calendar: {e}")

    # Actualizar mock local (también usado como fallback de disponibilidad)
    key = glamping_normalizado.lower()
    if key in RESERVAS_MOCK:
        if fecha_reserva not in RESERVAS_MOCK[key]:
            RESERVAS_MOCK[key].append(fecha_reserva)

    # Construir mensaje según el resultado real
    if sheets_ok or calendar_ok:
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
    else:
        # Modo fallback: la reserva queda en memoria local pero no en Google
        logger.warning("Reserva guardada en modo fallback (memoria local). No se pudo escribir en Google Sheets/Calendar.")
        resumen = (
            f"¡He tomado tu solicitud de reserva! 🎉\n\n"
            f"📋 Detalle de la Solicitud:\n"
            f"- Nombre: {nombre_cliente}\n"
            f"- WhatsApp: {whatsapp}\n"
            f"- Email: {email}\n"
            f"- Glamping: {glamping_normalizado}\n"
            f"- Fecha de llegada: {fecha_reserva}\n"
            f"- Personas: {num_personas}\n"
            f"- Notas: {notas}\n"
            f"- Estado: Pendiente confirmación\n\n"
            f"⚠️ Nota: En este momento no pude sincronizar automáticamente con nuestro calendario. "
            f"Un miembro del equipo te contactará muy pronto para confirmar disponibilidad y el abono del 50%. "
            f"Disculpa las molestias. ¡Te esperamos! 🌲"
        )

    return resumen
