"""
Parser de intenciones para SekretariaBot.
Usa Gemini 3 Flash Preview para detectar intención y extraer entidades.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import re

from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# Prompt del sistema para Gemini
SYSTEM_PROMPT = """Eres un asistente que analiza mensajes para detectar intenciones de calendario.

Tu trabajo es:
1. Detectar si el mensaje tiene una intención relacionada con calendario
2. Extraer las entidades relevantes (fecha, hora, título, participantes, etc.)
3. Responder SOLO en formato JSON válido

Intenciones posibles:
- crear_evento: Usuario quiere agendar algo nuevo
- editar_evento: Usuario quiere cambiar un evento existente  
- mover_evento: Usuario quiere cambiar fecha/hora de un evento
- eliminar_evento: Usuario quiere cancelar/borrar un evento
- consultar_eventos: Usuario pregunta qué tiene agendado
- disponibilidad: Usuario pregunta si está libre
- otro: No es sobre calendario

Formato de respuesta JSON:
{
    "intencion": "crear_evento|editar_evento|mover_evento|eliminar_evento|consultar_eventos|disponibilidad|otro",
    "confianza": 0.0-1.0,
    "entidades": {
        "titulo": "nombre del evento si aplica",
        "fecha": "YYYY-MM-DD si se menciona",
        "hora": "HH:MM si se menciona", 
        "duracion_minutos": numero si se menciona,
        "participantes": ["email1", "email2"] si se mencionan,
        "ubicacion": "lugar si se menciona",
        "evento_referencia": "descripción del evento que se quiere modificar/eliminar"
    },
    "requiere_confirmacion": true/false,
    "mensaje_aclaracion": "pregunta si falta información crítica"
}

Reglas:
- Si no se especifica año, asume 2026
- Si dice "mañana", "pasado mañana", "el viernes", calcula la fecha
- Si la hora es ambigua (ej: "a las 3"), pide aclaración AM/PM
- Para eliminar/mover eventos, requiere_confirmacion = true
- Si el mensaje no tiene que ver con calendario, intencion = "otro"
"""


def get_gemini_client():
    """Obtiene el cliente de Gemini configurado."""
    if not GEMINI_AVAILABLE:
        return None
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return None
    
    return genai.Client(api_key=api_key)


def parsear_intencion(mensaje: str, fecha_actual: datetime = None) -> Dict[str, Any]:
    """
    Analiza un mensaje y extrae la intención y entidades.
    
    Args:
        mensaje: Texto del usuario
        fecha_actual: Fecha actual para resolver referencias relativas
    
    Returns:
        Diccionario con intención, entidades y metadata
    """
    if fecha_actual is None:
        fecha_actual = datetime.now()
    
    if not GEMINI_AVAILABLE:
        return {
            'success': False,
            'error': 'google-genai no está instalado'
        }
    
    client = get_gemini_client()
    if not client:
        return {
            'success': False,
            'error': 'GEMINI_API_KEY no configurada en .env'
        }
    
    # Contexto temporal
    contexto = f"""
Fecha actual: {fecha_actual.strftime('%Y-%m-%d')}
Día de la semana: {fecha_actual.strftime('%A')}
Hora actual: {fecha_actual.strftime('%H:%M')}

Mensaje del usuario: {mensaje}
"""
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=f"{SYSTEM_PROMPT}\n\n{contexto}"
        )
        
        # Parsear respuesta JSON
        text = response.text.strip()
        
        # Limpiar posibles bloques de código
        if text.startswith('```'):
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
        
        resultado = json.loads(text)
        resultado['success'] = True
        
        # Resolver fechas relativas
        if resultado.get('entidades', {}).get('fecha'):
            resultado['entidades']['fecha_resuelta'] = resolver_fecha(
                resultado['entidades']['fecha'],
                fecha_actual
            )
        
        return resultado
    
    except json.JSONDecodeError:
        try:
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                resultado = json.loads(json_match.group())
                resultado['success'] = True
                return resultado
        except:
            pass
        
        return {
            'success': False,
            'error': 'No se pudo parsear la respuesta',
            'raw_response': response.text
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def resolver_fecha(fecha_str: str, fecha_actual: datetime) -> str:
    """Resuelve referencias de fecha relativas."""
    fecha_str_lower = fecha_str.lower()
    
    if fecha_str_lower == 'hoy':
        return fecha_actual.strftime('%Y-%m-%d')
    elif fecha_str_lower == 'mañana':
        return (fecha_actual + timedelta(days=1)).strftime('%Y-%m-%d')
    elif fecha_str_lower == 'pasado mañana':
        return (fecha_actual + timedelta(days=2)).strftime('%Y-%m-%d')
    
    try:
        datetime.strptime(fecha_str, '%Y-%m-%d')
        return fecha_str
    except ValueError:
        pass
    
    return fecha_str


def es_intencion_calendario(intencion: str) -> bool:
    """Verifica si una intención es relacionada con calendario."""
    intenciones_calendario = {
        'crear_evento', 'editar_evento', 'mover_evento',
        'eliminar_evento', 'consultar_eventos', 'disponibilidad'
    }
    return intencion in intenciones_calendario


if __name__ == '__main__':
    print("Probando parser de intenciones (Gemini 3 Flash Preview)...")
    
    mensajes_test = [
        "Agenda una reunión mañana a las 3pm con Juan",
        "¿Qué tengo el viernes?",
    ]
    
    for msg in mensajes_test:
        print(f"\n📝 '{msg}'")
        resultado = parsear_intencion(msg)
        if resultado.get('success'):
            print(f"   Intención: {resultado.get('intencion')}")
        else:
            print(f"   Error: {resultado.get('error')}")
