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

from contextlib import asynccontextmanager

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

# URL base para la aplicación (usar la de Railway si está disponible, o localhost para desarrollo)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
RAILWAY_PORT = os.getenv("PORT", "8000") # Puerto que Railway asigna

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación.
    Inicia el bot de Telegram al arrancar y lo detiene al finalizar.
    """
    print("=" * 50)
    print("🤖 SekretariaBot - Iniciando componentes")
    print("=" * 50)
    
    # Configurar e iniciar bot de Telegram
    bot_app = setup_bot()
    if bot_app:
        app.state.bot_app = bot_app
        await bot_app.initialize()
        await bot_app.updater.start_polling()
        await bot_app.start()
        print("✅ Bot de Telegram iniciado y escuchando mensajes.")
    else:
        print("❌ No se pudo iniciar el bot de Telegram.")

    print(f"\n📡 Servidor OAuth disponible en: {BASE_URL}")
    print(f"   - Para autorizar, visita: {BASE_URL}/autorizar")
    print("=" * 50)
    
    yield
    
    # Detener bot de Telegram al finalizar
    if bot_app:
        print("\n" + "=" * 50)
        print("🛑 Deteniendo el bot de Telegram...")
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
        print("✅ Bot de Telegram detenido.")
        print("=" * 50)

app = FastAPI(title="SekretariaBot API", lifespan=lifespan)

# Estado global para el flujo OAuth
oauth_flow = None



@app.get("/")
def root():
    """Health check."""
    return {"status": "running", "bot": "SekretariaBot"}


@app.get("/autorizar")
def iniciar_autorizacion():
    """Inicia el flujo OAuth de Google Calendar usando variables de entorno."""
    global oauth_flow

    client_id = os.getenv("CLIENTID")
    client_secret = os.getenv("GOOGLE_CALENDAR_SECRET")

    if not client_id or not client_secret:
        return {"error": "CLIENTID o GOOGLE_CALENDAR_SECRET (Client Secret) no configurados en el entorno."}

    # Construir la configuración del cliente para el flujo OAuth desde variables de entorno
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [f"{BASE_URL}/oauth2/callback"],
        }
    }
    
    oauth_flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=f"{BASE_URL}/oauth2/callback"
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
    
    
    
    
    
    if __name__ == '__main__':
    
        # Usamos uvicorn para correr la aplicación.
    
        # El bot se iniciará en el manejador de ciclo de vida 'lifespan'.
    
        uvicorn.run(app, host="0.0.0.0", port=int(RAILWAY_PORT), log_level="info")
