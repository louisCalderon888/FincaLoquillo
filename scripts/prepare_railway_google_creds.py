"""
Script helper para preparar la variable GOOGLE_CREDENTIALS_JSON de Railway.

Lee config/token.json (generado tras el login OAuth2 local) y lo convierte
en una única línea JSON lista para pegar como variable de entorno en Railway.

USO:
    python scripts/prepare_railway_google_creds.py
    python scripts/prepare_railway_google_creds.py --stdout
    python scripts/prepare_railway_google_creds.py --file railway_google_creds.txt

ADVERTENCIA DE SEGURIDAD:
    El token JSON contiene refresh_token y client_secret. Trátalo como una
    contraseña: no lo compartas, no lo subas a GitHub, no lo guardes en logs.
"""
import argparse
import json
import os
import sys

TOKEN_PATH = "config/token.json"


def main():
    parser = argparse.ArgumentParser(
        description="Prepara GOOGLE_CREDENTIALS_JSON para Railway."
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Imprime la credencial en stdout en lugar de guardarla en archivo."
    )
    parser.add_argument(
        "--file",
        default=".railway_google_creds.tmp",
        help="Ruta del archivo temporal donde guardar la credencial (default: .railway_google_creds.tmp)"
    )
    args = parser.parse_args()

    if not os.path.exists(TOKEN_PATH):
        print(f"❌ No se encontró {TOKEN_PATH}")
        print("Ejecuta primero: python tests/test_google_auth.py")
        sys.exit(1)

    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token_data = json.load(f)

    # Campos mínimos necesarios para Credentials.from_authorized_user_info
    required = ["token", "refresh_token", "token_uri", "client_id", "client_secret"]
    missing = [k for k in required if not token_data.get(k)]
    if missing:
        print(f"⚠️  El token local no tiene los campos: {missing}")
        print("Recomendación: vuelve a generar el token con test_google_auth.py")
        sys.exit(1)

    one_line = json.dumps(token_data, separators=(",", ":"))

    if args.stdout:
        print(one_line)
    else:
        try:
            with open(args.file, "w", encoding="utf-8") as f:
                f.write(one_line)
            print("🔐 Credencial guardada temporalmente en:")
            print(f"   {os.path.abspath(args.file)}")
            print()
            print("Pasos para Railway:")
            print("1. Abre el archivo de arriba.")
            print("2. Copia TODO el contenido (es una sola línea muy larga).")
            print("3. Ve a Railway → tu proyecto → Variables.")
            print("4. Crea una variable llamada GOOGLE_CREDENTIALS_JSON y pega el contenido.")
            print("5. Borra el archivo temporal cuando termines:")
            print(f"   del {args.file}")
        except Exception as e:
            print(f"❌ No se pudo escribir el archivo: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
