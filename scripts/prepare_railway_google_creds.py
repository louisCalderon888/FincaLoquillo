"""
Script helper para preparar la variable GOOGLE_CREDENTIALS_JSON de Railway.

Lee config/token.json (generado tras el login OAuth2 local) y lo convierte
en una única línea JSON lista para pegar como variable de entorno en Railway.

USO:
    python scripts/prepare_railway_google_creds.py

Luego copia el texto impreso (sin comillas exteriores) en:
    Railway → Variables → GOOGLE_CREDENTIALS_JSON
"""
import json
import os
import sys

TOKEN_PATH = "config/token.json"


def main():
    if not os.path.exists(TOKEN_PATH):
        print(f"❌ No se encontró {TOKEN_PATH}")
        print("Ejecuta primero: python tests/test_google_auth.py")
        sys.exit(1)

    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token_data = json.load(f)

    # Asegurar campos mínimos necesarios para Credentials.from_authorized_user_info
    required = ["token", "refresh_token", "token_uri", "client_id", "client_secret"]
    missing = [k for k in required if not token_data.get(k)]
    if missing:
        print(f"⚠️  El token local no tiene los campos: {missing}")
        print("Recomendación: vuelve a generar el token con test_google_auth.py")
        sys.exit(1)

    one_line = json.dumps(token_data, separators=(",", ":"))

    print("=" * 60)
    print("  GOOGLE_CREDENTIALS_JSON PARA RAILWAY")
    print("=" * 60)
    print()
    print("Copia esta única línea y pégala en Railway → Variables:")
    print()
    print(one_line)
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
