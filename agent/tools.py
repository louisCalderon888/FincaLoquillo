# agent/tools.py — Herramientas del agente con integración a Google Sheets
# Generado por AgentKit

import os
import json
import yaml
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")

# ─────────────────────────────────────────────────────────────
# BASE DE DATOS DE DISPONIBILIDAD (se actualiza con reservas reales)
# Al principio usa el mock; cuando integremos Sheets, lo leeremos de ahí.
# ─────────────────────────────────────────────────────────────
RESERVAS_MOCK = {
    "nido de amor": ["2026-06-15", "2026-06-20", "2026-06-21"],
    "vista hermosa": ["2026-06-15", "2026-06-16", "2026-06-22"]
}

# URLs de imágenes de los glampings (puedes reemplazarlas con fotos reales de la Finca)
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


def verificar_disponibilidad_glamping(glamping: str, fecha: str) -> str:
    """
    Verifica si un tipo de glamping está disponible para una fecha específica.
    Parámetros:
        glamping: nombre del glamping ('nido de amor' o 'vista hermosa')
        fecha: fecha en formato YYYY-MM-DD
    """
    nombre_normalizado = glamping.lower().strip()

    if "nido" in nombre_normalizado or "amor" in nombre_normalizado:
        key = "nido de amor"
    elif "vista" in nombre_normalizado or "hermosa" in nombre_normalizado:
        key = "vista hermosa"
    else:
        return "Solo tenemos el 'Glamping Nido de Amor' y el 'Glamping Vista Hermosa'. ¿Cuál te gustaría consultar?"

    fechas_ocupadas = RESERVAS_MOCK.get(key, [])
    if fecha in fechas_ocupadas:
        return f"Lo siento, el {key.title()} está RESERVADO para el {fecha}. Te sugiero consultar otra fecha."
    else:
        return f"¡Buenas noticias! El {key.title()} está DISPONIBLE para el {fecha}. Puedes reservarlo con el 50% de abono."


def obtener_imagen_glamping(glamping: str) -> str:
    """
    Retorna la URL de la imagen asociada al glamping solicitado.
    Parámetros:
        glamping: nombre del glamping ('nido de amor' o 'vista hermosa')
    """
    nombre_normalizado = glamping.lower().strip()
    if "nido" in nombre_normalizado or "amor" in nombre_normalizado:
        return FOTOS_GLAMPING["nido de amor"]
    elif "vista" in nombre_normalizado or "hermosa" in nombre_normalizado:
        return FOTOS_GLAMPING["vista hermosa"]
    return ""


# ─────────────────────────────────────────────────────────────
# INTEGRACIÓN CON GOOGLE SHEETS — Gestión de Reservas
# ─────────────────────────────────────────────────────────────

def _obtener_cliente_sheets():
    """
    Autentica con Google Sheets usando las credenciales de la cuenta de servicio.
    Las credenciales se cargan desde la variable de entorno GOOGLE_CREDENTIALS_JSON
    o desde el archivo config/google_credentials.json.
    """
    import gspread
    from google.oauth2.service_account import Credentials

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # Intentar cargar desde variable de entorno (para producción en Railway)
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if credentials_json:
        creds_dict = json.loads(credentials_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        # Cargar desde archivo local (para desarrollo)
        creds_path = "config/google_credentials.json"
        if not os.path.exists(creds_path):
            raise FileNotFoundError(
                "No se encontraron credenciales de Google. "
                "Coloca tu archivo google_credentials.json en config/ "
                "o define la variable GOOGLE_CREDENTIALS_JSON en .env"
            )
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)

    return gspread.authorize(creds)


def registrar_reserva_sheets(
    nombre_cliente: str,
    telefono: str,
    glamping: str,
    fecha_reserva: str,
    num_personas: str = "1",
    almuerzos: str = "No",
    notas: str = ""
) -> str:
    """
    Registra una nueva reserva en Google Sheets.
    Parámetros:
        nombre_cliente: nombre completo del cliente
        telefono: número de teléfono del cliente
        glamping: tipo de glamping ('Nido de Amor' o 'Vista Hermosa')
        fecha_reserva: fecha de llegada (YYYY-MM-DD)
        num_personas: número de personas (default: 1)
        almuerzos: si desean almuerzos (Sí/No)
        notas: observaciones adicionales
    """
    SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

    if not SHEET_ID:
        logger.warning("GOOGLE_SHEET_ID no configurado en .env")
        return (
            f"¡Genial! Anoté tu solicitud de reserva:\n"
            f"- Nombre: {nombre_cliente}\n"
            f"- Glamping: {glamping}\n"
            f"- Fecha: {fecha_reserva}\n"
            f"- Personas: {num_personas}\n\n"
            "El equipo de Finca Loquillo te contactará pronto para confirmar el abono del 50%. 🌲"
        )

    try:
        gc = _obtener_cliente_sheets()
        sheet = gc.open_by_key(SHEET_ID)

        # Obtener o crear la hoja "Reservas"
        try:
            worksheet = sheet.worksheet("Reservas")
        except Exception:
            worksheet = sheet.add_worksheet(title="Reservas", rows=1000, cols=10)
            # Agregar encabezados si es hoja nueva
            encabezados = [
                "Fecha de Solicitud", "Nombre Cliente", "Teléfono",
                "Glamping", "Fecha de Llegada", "N° Personas",
                "Almuerzos", "Estado Pago", "Notas"
            ]
            worksheet.append_row(encabezados)

        # Agregar la nueva fila de reserva
        nueva_fila = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            nombre_cliente,
            telefono,
            glamping,
            fecha_reserva,
            num_personas,
            almuerzos,
            "Pendiente de pago",  # Estado inicial
            notas
        ]
        worksheet.append_row(nueva_fila)

        logger.info(f"Reserva registrada en Sheets: {nombre_cliente} - {glamping} - {fecha_reserva}")

        # Bloquear la fecha en el mock para reflejar disponibilidad inmediata
        key = glamping.lower().strip()
        if key in RESERVAS_MOCK:
            if fecha_reserva not in RESERVAS_MOCK[key]:
                RESERVAS_MOCK[key].append(fecha_reserva)

        return (
            f"¡Reserva registrada con éxito! 🎉\n\n"
            f"📋 Resumen de tu solicitud:\n"
            f"- Nombre: {nombre_cliente}\n"
            f"- Glamping: {glamping}\n"
            f"- Fecha de llegada: {fecha_reserva}\n"
            f"- Personas: {num_personas}\n"
            f"- Almuerzos incluidos: {almuerzos}\n\n"
            f"Para CONFIRMAR tu reserva, realiza el abono del 50% y envía el comprobante de pago. "
            f"Nuestro equipo te enviará los datos bancarios y las instrucciones para llegar. 🌲"
        )

    except Exception as e:
        logger.error(f"Error al registrar reserva en Google Sheets: {e}")
        return (
            f"Anoté tu reserva internamente:\n"
            f"- {nombre_cliente} / {glamping} / {fecha_reserva}\n\n"
            f"El equipo de Finca Loquillo te contactará para confirmar. "
            f"Disculpa si hay alguna demora. 🙏"
        )
