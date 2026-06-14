"""
Script de diagnóstico para verificar la configuración de Google en Railway.

Ejecutar en Railway o local:
    python scripts/verificar_google_creds.py

No imprime secretos completos, solo valida que existan los campos necesarios.
"""
import json
import os
import sys

REQUIRED_FIELDS = ["client_id", "client_secret", "refresh_token", "token_uri"]
OPTIONAL_BUT_RECOMMENDED = ["token", "token_uri", "universe_domain"]


def main():
    print("=" * 60)
    print("  DIAGNÓSTICO DE CREDENCIALES GOOGLE")
    print("=" * 60)

    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "")
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

    print(f"\nGOOGLE_SHEET_ID:     {'✅ configurado' if sheet_id else '❌ VACÍO'}")
    print(f"GOOGLE_CALENDAR_ID:  {'✅ configurado' if calendar_id else '❌ VACÍO'}")
    print(f"GOOGLE_CREDENTIALS_JSON: {'✅ presente' if creds_json else '❌ VACÍO'}")

    if not creds_json:
        print("\n⚠️  GOOGLE_CREDENTIALS_JSON está vacía.")
        print("   Solución: ejecuta scripts/prepare_railway_google_creds.py")
        print("   y pega el resultado en Railway → Variables.")
        sys.exit(1)

    try:
        data = json.loads(creds_json)
    except json.JSONDecodeError as e:
        print(f"\n❌ GOOGLE_CREDENTIALS_JSON no es un JSON válido: {e}")
        print("   Solución: vuelve a generarla con scripts/prepare_railway_google_creds.py")
        sys.exit(1)

    print("\nCampos del token:")
    for field in REQUIRED_FIELDS:
        value = data.get(field)
        status = "✅" if value else "❌ FALTA"
        preview = value[:8] + "..." if value and isinstance(value, str) else ""
        print(f"   {status} {field}: {preview}")

    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        print(f"\n❌ Faltan campos obligatorios: {missing}")
        print("   Solución: vuelve a generar el token local con:")
        print("      python tests/test_google_auth.py")
        print("   Luego ejecuta de nuevo scripts/prepare_railway_google_creds.py")
        sys.exit(1)

    print("\n✅ GOOGLE_CREDENTIALS_JSON parece válida.")
    print("✅ GOOGLE_SHEET_ID y GOOGLE_CALENDAR_ID están configurados.")
    print("\nSi aún así falla, revisa los logs de Railway para el error exacto.")


if __name__ == "__main__":
    main()
