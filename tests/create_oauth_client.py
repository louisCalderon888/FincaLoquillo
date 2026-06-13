"""
Script completo para crear OAuth2 client via la API IAP de Google Cloud
y generar el client_secret.json compatible con google-auth-oauthlib.
"""
import urllib.request
import urllib.error
import json
import subprocess
import os
import sys

GCLOUD_CMD = r'C:\Users\71427321_893\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
PROJECT_NUMBER = '308738143849'
PROJECT_ID = 'finca-loquillo'
BRAND_NAME = f'projects/{PROJECT_NUMBER}/brands/{PROJECT_NUMBER}'
OUTPUT_PATH = 'config/client_secret.json'

def get_access_token():
    result = subprocess.run(
        [GCLOUD_CMD, 'auth', 'print-access-token'],
        capture_output=True, text=True, shell=True
    )
    return result.stdout.strip()

def api_request(url, method='GET', data=None, token=None):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        try:
            return json.loads(err_body), e.code
        except Exception:
            return {'error': err_body}, e.code

token = get_access_token()
print(f"Token OK: {token[:20]}...\n")

# Listar clientes existentes en el brand
print(f"=== Listando OAuth Clients en brand ===")
data, status = api_request(
    f'https://iap.googleapis.com/v1/{BRAND_NAME}/identityAwareProxyClients',
    token=token
)
print(f"Status: {status}")

clients = data.get('identityAwareProxyClients', [])
print(f"Clientes existentes: {len(clients)}")
for c in clients:
    print(f"  - {c.get('displayName')} | {c.get('name')} | secret: {c.get('secret','')[:10]}...")

# Si ya existe uno para "Loqui Local", usarlo; si no, crear uno nuevo
existing_client = None
for c in clients:
    if 'Loqui' in c.get('displayName', '') or 'local' in c.get('displayName', '').lower():
        existing_client = c
        break

if existing_client:
    print(f"\nUsando cliente existente: {existing_client.get('displayName')}")
    client_data = existing_client
else:
    print("\nCreando nuevo OAuth client...")
    client_data, status2 = api_request(
        f'https://iap.googleapis.com/v1/{BRAND_NAME}/identityAwareProxyClients',
        method='POST',
        data={'displayName': 'Loqui Local Desktop'},
        token=token
    )
    print(f"Status crear cliente: {status2}")
    print(json.dumps(client_data, indent=2))

if 'name' not in client_data:
    print("\nERROR: No se pudo obtener el cliente OAuth.")
    sys.exit(1)

# Extraer client_id del name (formato: projects/XXX/brands/YYY/identityAwareProxyClients/CLIENT_ID)
client_name = client_data['name']
client_id_raw = client_name.split('/')[-1]
client_secret = client_data.get('secret', '')

if not client_secret:
    print("\nEl cliente no tiene secret. Intentando resetear secret...")
    reset_data, reset_status = api_request(
        f'https://iap.googleapis.com/v1/{client_name}:resetSecret',
        method='POST',
        data={},
        token=token
    )
    print(f"Status reset: {reset_status}")
    print(json.dumps(reset_data, indent=2))
    client_secret = reset_data.get('secret', '')

print(f"\nclient_id (raw): {client_id_raw}")
print(f"client_secret: {client_secret[:10]}..." if client_secret else "client_secret: VACÍO")

# Construir client_secret.json en formato installedApp compatible con google-auth-oauthlib
# El client_id real para OAuth es el número de proyecto + sufijo .apps.googleusercontent.com
# Para IAP clients el formato es diferente — necesitamos construirlo correctamente
client_secret_json = {
    "installed": {
        "client_id": client_id_raw,
        "project_id": PROJECT_ID,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": client_secret,
        "redirect_uris": ["http://localhost"]
    }
}

os.makedirs('config', exist_ok=True)
with open(OUTPUT_PATH, 'w') as f:
    json.dump(client_secret_json, f, indent=2)

print(f"\nclient_secret.json guardado en: {OUTPUT_PATH}")
print(json.dumps(client_secret_json, indent=2))
