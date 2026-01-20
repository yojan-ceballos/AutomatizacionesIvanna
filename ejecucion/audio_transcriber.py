"""
Transcriptor de audio para SekretariaBot.
Usa Gemini 3 Flash Preview para convertir audio a texto.
"""

import os
from pathlib import Path
import tempfile

from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def get_gemini_client():
    """Obtiene el cliente de Gemini configurado."""
    if not GEMINI_AVAILABLE:
        return None
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return None
    
    return genai.Client(api_key=api_key)


def transcribir_audio(audio_path: str) -> dict:
    """
    Transcribe un archivo de audio a texto usando Gemini.
    
    Args:
        audio_path: Ruta al archivo de audio
    
    Returns:
        Diccionario con texto transcrito o error
    """
    if not GEMINI_AVAILABLE:
        return {
            'success': False,
            'error': 'google-genai no está instalado. Ejecuta: pip install google-genai'
        }
    
    client = get_gemini_client()
    if not client:
        return {
            'success': False,
            'error': 'GEMINI_API_KEY no configurada en .env'
        }
    
    try:
        # Subir archivo de audio
        audio_file = client.files.upload(file=audio_path)
        
        # Transcribir con Gemini
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                "Transcribe el siguiente audio al español. Solo devuelve el texto transcrito, sin explicaciones adicionales.",
                audio_file
            ]
        )
        
        return {
            'success': True,
            'texto': response.text.strip(),
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


async def transcribir_audio_telegram(voice_file, bot) -> dict:
    """
    Descarga y transcribe un mensaje de voz de Telegram.
    
    Args:
        voice_file: Objeto de archivo de voz de Telegram
        bot: Instancia del bot de Telegram
    
    Returns:
        Diccionario con texto transcrito o error
    """
    try:
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
            tmp_path = tmp.name
        
        # Descargar el archivo de voz
        file = await bot.get_file(voice_file.file_id)
        await file.download_to_drive(tmp_path)
        
        # Transcribir con Gemini
        resultado = transcribir_audio(tmp_path)
        
        # Limpiar archivo temporal
        Path(tmp_path).unlink(missing_ok=True)
        
        return resultado
    except Exception as e:
        return {
            'success': False,
            'error': f'Error al procesar audio: {str(e)}',
        }


if __name__ == '__main__':
    print("Módulo de transcripción (Gemini 3 Flash Preview)")
    print(f"google-genai disponible: {GEMINI_AVAILABLE}")
    if GEMINI_AVAILABLE:
        api_key = os.getenv('GEMINI_API_KEY')
        print(f"GEMINI_API_KEY configurada: {'Sí' if api_key else 'No'}")
