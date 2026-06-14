# tests/test_diagnostico_google.py
"""
Diagnóstico completo de la integración con Google Sheets y Google Calendar.
Verifica: credenciales, permisos, IDs configurados, lectura/escritura.
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def diagnostico():
    print("=" * 60)
    print("  DIAGNÓSTICO DE INTEGRACIÓN GOOGLE")
    print("=" * 60)
    print()

    # 1. Variables de entorno
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "")
    
    print("[1] VARIABLES DE ENTORNO")
    print(f"  GOOGLE_SHEET_ID    = '{sheet_id}'")
    print(f"  GOOGLE_CALENDAR_ID = '{calendar_id}'")
    if not sheet_id:
        print("  ⚠️  GOOGLE_SHEET_ID está VACÍO — las reservas NO se guardarán en Sheets")
    if not calendar_id:
        print("  ⚠️  GOOGLE_CALENDAR_ID está VACÍO — no se consultará disponibilidad real")
    print()

    # 2. Credenciales OAuth
    print("[2] ARCHIVOS DE CREDENCIALES")
    token_exists = os.path.exists("config/token.json")
    client_secret_exists = os.path.exists("config/client_secret.json")
    print(f"  config/token.json         = {'✅ Existe' if token_exists else '❌ NO existe'}")
    print(f"  config/client_secret.json = {'✅ Existe' if client_secret_exists else '❌ NO existe'}")
    print()

    if not token_exists:
        print("  ❌ Sin token.json no se puede autenticar con Google APIs.")
        print("  Ejecuta: python tests/test_google_auth.py para generar uno.")
        return

    # 3. Probar autenticación
    print("[3] AUTENTICACIÓN GOOGLE")
    try:
        from agent.tools import _obtener_credenciales_google
        creds = _obtener_credenciales_google()
        if creds and creds.valid:
            print(f"  ✅ Credenciales válidas. Token presente: {bool(creds.token)}")
        elif creds and creds.expired:
            print(f"  ⚠️  Token expirado pero con refresh_token: {bool(creds.refresh_token)}")
        else:
            print(f"  ❌ No se pudieron obtener credenciales válidas.")
            return
    except Exception as e:
        print(f"  ❌ Error obteniendo credenciales: {e}")
        return
    print()

    # 4. Google Sheets
    print("[4] GOOGLE SHEETS")
    if sheet_id:
        try:
            import gspread
            gc = gspread.authorize(creds)
            sheet = gc.open_by_key(sheet_id)
            print(f"  ✅ Spreadsheet encontrado: '{sheet.title}'")
            print(f"  Hojas disponibles:")
            for ws in sheet.worksheets():
                print(f"    - '{ws.title}' ({ws.row_count} filas x {ws.col_count} cols)")
            
            # Verificar si existe la hoja "Reservas"
            try:
                reservas_ws = sheet.worksheet("Reservas")
                print(f"  ✅ Hoja 'Reservas' encontrada")
                # Leer encabezados
                headers = reservas_ws.row_values(1)
                print(f"  Encabezados: {headers}")
                # Contar filas con datos
                all_values = reservas_ws.get_all_values()
                print(f"  Total filas (incluyendo encabezado): {len(all_values)}")
            except gspread.exceptions.WorksheetNotFound:
                print(f"  ⚠️  Hoja 'Reservas' NO existe — se creará automáticamente en la primera reserva")
        except Exception as e:
            print(f"  ❌ Error accediendo al Spreadsheet: {e}")
            if "404" in str(e):
                print(f"  💡 El ID '{sheet_id}' no existe o no tienes acceso.")
                print(f"  💡 Verifica el ID en la URL del spreadsheet:")
                print(f"     https://docs.google.com/spreadsheets/d/TU_ID/edit")
    else:
        print("  ⏭️  Saltando — GOOGLE_SHEET_ID no configurado")
    print()

    # 5. Google Calendar
    print("[5] GOOGLE CALENDAR")
    if calendar_id:
        try:
            from googleapiclient.discovery import build
            from datetime import datetime, timedelta
            
            service = build('calendar', 'v3', credentials=creds)
            
            # Verificar acceso al calendario
            try:
                cal = service.calendars().get(calendarId=calendar_id).execute()
                print(f"  ✅ Calendario encontrado: '{cal.get('summary', 'Sin nombre')}'")
                print(f"  Zona horaria: {cal.get('timeZone', 'No definida')}")
            except Exception as e:
                print(f"  ❌ Error accediendo al calendario '{calendar_id}': {e}")
                if "404" in str(e):
                    print(f"  💡 El Calendar ID '{calendar_id}' no existe.")
                    print(f"  💡 Calendarios disponibles:")
                    cal_list = service.calendarList().list().execute()
                    for c in cal_list.get('items', []):
                        print(f"     - '{c['summary']}' → ID: {c['id']}")
                return
            
            # Listar eventos próximos
            ahora = datetime.utcnow()
            time_min = ahora.isoformat() + 'Z'
            time_max = (ahora + timedelta(days=30)).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=10
            ).execute()
            events = events_result.get('items', [])
            
            print(f"  Eventos próximos (30 días): {len(events)}")
            for ev in events:
                start = ev.get('start', {}).get('date') or ev.get('start', {}).get('dateTime', '')
                summary = ev.get('summary', '(sin título)')
                print(f"    - {start[:10]}: {summary}")
            
            if not events:
                print(f"  ℹ️  No hay eventos en los próximos 30 días — todas las fechas aparecerán como disponibles")
                
        except Exception as e:
            print(f"  ❌ Error con Google Calendar: {e}")
    else:
        print("  ⏭️  Saltando — GOOGLE_CALENDAR_ID no configurado")
    print()

    # 6. Resumen
    print("=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    ok_count = 0
    issues = []
    
    if sheet_id:
        ok_count += 1
    else:
        issues.append("GOOGLE_SHEET_ID no configurado")
    
    if calendar_id:
        ok_count += 1
    else:
        issues.append("GOOGLE_CALENDAR_ID no configurado")
    
    if token_exists:
        ok_count += 1
    else:
        issues.append("config/token.json no existe")
    
    print(f"  ✅ {ok_count} verificaciones OK")
    if issues:
        print(f"  ⚠️  {len(issues)} problemas encontrados:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print(f"  🎉 ¡Todo configurado correctamente!")


if __name__ == "__main__":
    diagnostico()
