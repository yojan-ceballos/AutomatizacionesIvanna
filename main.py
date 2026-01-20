"""
Main entry point para SekretariaBot.
Ejecuta el bot de Telegram y servidor FastAPI para OAuth.
"""

import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn
from dotenv import load_dotenv
from telegram import Update

from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import Flow

# Importar el setup_bot del módulo de Telegram
from ejecucion.telegram_bot import setup_bot

load_dotenv()

# Configuración
PROJECT_ROOT = Path(__file__).parent
CREDENTIALS_FILE = PROJECT_ROOT / 'credentials.json'
TOKEN_FILE = PROJECT_ROOT / 'token.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']

app = FastAPI(title="SekretariaBot API")

# Estado global para el flujo OAuth
oauth_flow = None


@app.get("/")
def root():
    """Health check."""
    return {"status": "running", "bot": "SekretariaBot"}


@app.get("/autorizar")
def iniciar_autorizacion():
    """Inicia el flujo OAuth de Google Calendar."""
    global oauth_flow
    
    if not CREDENTIALS_FILE.exists():
        return {"error": "credentials.json no encontrado"}
    
    oauth_flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/oauth2/callback"
    )
    
    auth_url, _ = oauth_flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    return HTMLResponse(f"""
    <html>
        <head><title>Autorizar SekretariaBot</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>🔐 Autorizar Google Calendar</h1>
            <p>Haz clic para autorizar el acceso:</p>
            <a href="{auth_url}" style="
                display: inline-block;
                padding: 15px 30px;
                background: #4285f4;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-size: 18px;
            ">Autorizar con Google</a>
        </body>
    </html>
    """)


@app.get("/oauth2/callback")
def oauth_callback(request: Request):
    """Callback de OAuth - recibe el código de autorización."""
    global oauth_flow
    
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    
    if error:
        return HTMLResponse(f"""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>❌ Error</h1>
            <p>{error}</p>
        </body></html>
        """)
    
    if not code:
        return {"error": "No se recibió código de autorización"}
    
    if not oauth_flow:
        return {"error": "Flujo OAuth no iniciado. Ve a /autorizar primero."}
    
    try:
        # Intercambiar código por token
        oauth_flow.fetch_token(code=code)
        creds = oauth_flow.credentials
        
        # Guardar token
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        
        return HTMLResponse(f"""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>✅ ¡Autorización exitosa!</h1>
            <p>Token guardado en <code>token.json</code></p>
            <p>Ya puedes usar el bot de Telegram para gestionar tu calendario.</p>
        </body></html>
        """)
    except Exception as e:
        return HTMLResponse(f"""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>❌ Error</h1>
            <p>{str(e)}</p>
        </body></html>
        """)


# Importar el setup_bot del módulo de Telegram
from ejecucion.telegram_bot import setup_bot

# ... (código existente) ...

@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("🤖 SekretariaBot - Iniciando componentes")
    print("=" * 50)
    
    # Iniciar bot de Telegram como tarea en segundo plano
    print("💬 Bot de Telegram configurando e iniciando polling...")
    bot_app = setup_bot()
    if bot_app:
        # Esto inicia el polling en el mismo event loop de FastAPI
        asyncio.create_task(bot_app.run_polling(allowed_updates=Update.ALL_TYPES))
        print("✅ Bot de Telegram iniciado y escuchando mensajes.")
    else:
        print("❌ No se pudo iniciar el bot de Telegram.")
    
    print("\n📡 Servidor OAuth: http://localhost:8000")
    print("   - Autorizar: http://localhost:8000/autorizar")
    print("=" * 50)

if __name__ == '__main__':
    # Usamos uvicorn para correr la aplicación. El bot se iniciará en el evento 'startup'.
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
