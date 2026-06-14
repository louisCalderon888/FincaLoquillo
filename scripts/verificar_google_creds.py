"""
Script de diagnóstico para verificar la configuración de Google en Railway o local.

Ejecutar:
    python scripts/verificar_google_creds.py

Soporta:
  - GOOGLE_SERVICE_ACCOUNT_JSON (service account, recomendado)
  - GOOGLE_CREDENTIALS_JSON (OAuth2 desktop)
"""
import json
import os
import sys


def main():
    print("=" * 60)
    print("  DIAGNÓSTICO DE CREDENCIALES GOOGLE")
    print("=" * 60)

    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "")
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    oauth_json = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

    print(f"\nGOOGLE_SHEET_ID:            {'✅ configurado' if sheet_id else '❌ VACÍO'}")
    print(f"GOOGLE_CALENDAR_ID:         {'✅ configurado' if calendar_id else '❌ VACÍO'}")
    print(f"GOOGLE_SERVICE_ACCOUNT_JSON: {'✅ presente' if sa_json else '❌ VACÍO'} (recomendado)")
    print(f"GOOGLE_CREDENTIALS_JSON:     {'✅ presente' if oauth_json else '❌ VACÍO'} (OAuth2)")

    # Verificar Service Account (prioridad)
    if sa_json:
        print("\n--- Analizando GOOGLE_SERVICE_ACCOUNT_JSON ---")
        verificar_json(sa_json, modo="service_account")
        return

    # Verificar OAuth2 (fallback)
    if oauth_json:
        print("\n--- Analizando GOOGLE_CREDENTIALS_JSON (OAuth2) ---")
        verificar_json(oauth_json, modo="oauth")
        return

    # Nada configurado
    print("\n❌ No se encontró ninguna credencial de Google.")
    print("   Opción A (RECOMENDADA): crea una Service Account en")
    print("      https://console.cloud.google.com/iam-admin/serviceaccounts")
    print("   Opción B: usa OAuth2 ejecutando tests/test_google_auth.py")
    print("      y luego scripts/prepare_railway_google_creds.py")
    sys.exit(1)


def verificar_json(raw: str, modo: str):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"\n❌ El JSON no es válido: {e}")
        print("   Solución: vuelve a generarlo o pégalo sin modificar.")
        sys.exit(1)

    if modo == "service_account" or data.get("type") == "service_account":
        verificar_service_account(data)
    else:
        verificar_oauth(data)


def verificar_service_account(data: dict):
    print(f"\nTipo: service_account")
    print(f"   client_email: {data.get('client_email', '❌ FALTA')}")
    print(f"   private_key:  {'✅ presente' if data.get('private_key') else '❌ FALTA'}")
    print(f"   project_id:   {data.get('project_id', '❌ FALTA')}")

    if not data.get("client_email") or not data.get("private_key"):
        print("\n❌ Faltan campos obligatorios. La clave JSON está incompleta.")
        print("   Solución: vuelve a descargar la clave desde Google Cloud Console.")
        sys.exit(1)

    print(f"\n✅ Service Account válida.")
    print(f"\n⚠️  IMPORTANTE: Comparte tu Google Sheet y Calendar con este email:")
    print(f"      {data.get('client_email')}")
    print(f"   Sheet:  Abre tu Google Sheet → Compartir → pega el email → Editor")
    print(f"   Calendar: Abre tu Calendar → Configuración → Compartir → pega el email → Hacer cambios")


def verificar_oauth(data: dict):
    campos = {
        "client_id": "client_id",
        "client_secret": "client_secret",
        "refresh_token": "refresh_token",
        "token_uri": "token_uri",
    }
    print("\nCampos del token OAuth2:")
    all_ok = True
    for key, label in campos.items():
        value = data.get(key)
        status = "✅" if value else "❌ FALTA"
        preview = (value[:8] + "...") if value and isinstance(value, str) else ""
        print(f"   {status} {label}: {preview}")
        if not value:
            all_ok = False

    if not all_ok:
        print("\n❌ Faltan campos obligatorios.")
        print("   Solución: vuelve a generar el token local con:")
        print("      python tests/test_google_auth.py")
        print("   Luego: python scripts/prepare_railway_google_creds.py")
        sys.exit(1)

    print(f"\n✅ Token OAuth2 parece válido.")
    print(f"\n⚠️  OAuth2 Desktop puede expirar cada 7 días en modo testing.")
    print(f"   Para producción, considera usar una Service Account.")


if __name__ == "__main__":
    main()
