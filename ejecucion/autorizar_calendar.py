"""
Script para autorizar el acceso a Google Calendar.
Ejecutar una vez para generar token.json.
"""

import os
import sys
from pathlib import Path

# Agregar el directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar']
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / 'credentials.json'
TOKEN_FILE = PROJECT_ROOT / 'token.json'


def autorizar():
    """Ejecuta el flujo OAuth y guarda el token."""
    
    print("=" * 50)
    print("🔐 Autorización de Google Calendar")
    print("=" * 50)
    
    if not CREDENTIALS_FILE.exists():
        print(f"\n❌ No se encontró: {CREDENTIALS_FILE}")
        print("\nPasos para obtener credentials.json:")
        print("1. Ve a https://console.cloud.google.com/")
        print("2. Crea un proyecto o selecciona uno")
        print("3. Ve a 'APIs y servicios' > 'Biblioteca'")
        print("4. Busca 'Google Calendar API' y habilítala")
        print("5. Ve a 'Credenciales' > 'Crear credenciales'")
        print("6. Selecciona 'ID de cliente OAuth' > 'Aplicación de escritorio'")
        print("7. Descarga el JSON y guárdalo como 'credentials.json'")
        return
    
    # Verificar si ya existe token válido
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.valid:
            print("\n✅ Ya tienes un token válido!")
            print(f"   Archivo: {TOKEN_FILE}")
            return
        elif creds and creds.expired and creds.refresh_token:
            print("\n🔄 Refrescando token expirado...")
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            print("✅ Token refrescado!")
            return
    
    # Ejecutar flujo OAuth
    print("\n🌐 Abriendo navegador para autorizar...")
    print("   (Si no se abre, copia la URL que aparece)")
    
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE), SCOPES
    )
    creds = flow.run_local_server(port=0)
    
    # Guardar token
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
    
    print(f"\n✅ ¡Autorización exitosa!")
    print(f"   Token guardado en: {TOKEN_FILE}")
    print("\n   Ahora puedes ejecutar el bot normalmente.")


if __name__ == '__main__':
    autorizar()
