# agent/tools.py — Herramientas del agente
# Generado por AgentKit

import os
import yaml
import logging

logger = logging.getLogger("agentkit")

# Mock de base de datos de reservas de glamping (Fechas ocupadas)
# Formato: {"tipo_glamping": ["YYYY-MM-DD", "YYYY-MM-DD"]}
RESERVAS_MOCK = {
    "nido de amor": ["2026-06-15", "2026-06-20", "2026-06-21"],
    "vista hermosa": ["2026-06-15", "2026-06-16", "2026-06-22"]
}

# URLs públicas de imágenes de stock premium de Glampings para simular el envío de fotos reales
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


# ════════════════════════════════════════════════════════════
# NUEVOS CASOS DE USO
# ════════════════════════════════════════════════════════════

def verificar_disponibilidad_glamping(glamping: str, fecha: str) -> str:
    """
    Verifica si un tipo de glamping está disponible para una fecha específica (Formato YYYY-MM-DD).
    """
    nombre_normalizado = glamping.lower().strip()
    
    if "nido" in nombre_normalizado or "amor" in nombre_normalizado:
        key = "nido de amor"
    elif "vista" in nombre_normalizado or "hermosa" in nombre_normalizado:
        key = "vista hermosa"
    else:
        return "Disculpa, solo disponemos del 'Glamping Nido de Amor' y el 'Glamping Vista Hermosa'. ¿Cuál de los dos te gustaría verificar?"

    # Validar si la fecha ya está reservada
    fechas_ocupadas = RESERVAS_MOCK.get(key, [])
    if fecha in fechas_ocupadas:
        return f"Lo siento, el {key.title()} ya se encuentra RESERVADO para el día {fecha}. Te sugiero consultar por otra fecha cercana."
    else:
        return f"¡Buenas noticias! El {key.title()} está DISPONIBLE para el día {fecha}. Recuerda que puedes reservarlo con un abono del 50%."


def obtener_imagen_glamping(glamping: str) -> str:
    """
    Retorna la URL de la imagen asociada a un glamping.
    """
    nombre_normalizado = glamping.lower().strip()
    
    if "nido" in nombre_normalizado or "amor" in nombre_normalizado:
        return FOTOS_GLAMPING["nido de amor"]
    elif "vista" in nombre_normalizado or "hermosa" in nombre_normalizado:
        return FOTOS_GLAMPING["vista hermosa"]
    
    return ""
