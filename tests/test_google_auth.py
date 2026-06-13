"""
tests/test_google_auth.py — Verifica que las credenciales de Google funcionen
correctamente listando calendarios y luego sheets accesibles.
"""
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools import _obtener_credenciales_google

def main():
    print("\n=== Test de Autenticación Google ===\n")
    
    creds = _obtener_credenciales_google()
    if not creds:
        print("ERROR: No se pudieron obtener credenciales de Google.")
        sys.exit(1)

    print(f"OK - Credenciales obtenidas. Token válido: {bool(creds.token)}\n")

    # Test Google Calendar
    try:
        from googleapiclient.discovery import build
        svc = build("calendar", "v3", credentials=creds)
        cal_list = svc.calendarList().list().execute()
        calendars = cal_list.get("items", [])
        print(f"Calendarios encontrados ({len(calendars)}):")
        for c in calendars:
            print(f"  - {c['summary']}")
            print(f"    ID: {c['id']}")
        print()
    except Exception as e:
        print(f"ERROR al acceder a Google Calendar: {e}\n")

    # Test Google Sheets (listar archivos de Drive con tipo Sheets)
    try:
        from googleapiclient.discovery import build
        drive_svc = build("drive", "v3", credentials=creds)
        results = drive_svc.files().list(
            q="mimeType='application/vnd.google-apps.spreadsheet'",
            fields="files(id, name)",
            pageSize=10
        ).execute()
        sheets = results.get("files", [])
        print(f"Google Sheets encontradas en Drive ({len(sheets)}):")
        for s in sheets:
            print(f"  - {s['name']}")
            print(f"    ID: {s['id']}")
        print()
    except Exception as e:
        print(f"ERROR al acceder a Google Drive/Sheets: {e}\n")

if __name__ == "__main__":
    main()
