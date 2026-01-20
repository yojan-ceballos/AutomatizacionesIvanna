"""
Generador de respuestas amigables para SekretariaBot.
Usa Gemini 3 Flash Preview para crear mensajes naturales.
"""

import os
from typing import Dict, Any, List

from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


PERSONALIDAD = """Eres SekretariaBot, una asistente virtual amigable y profesional.
Tu estilo:
- Amable y cálida, usa emojis con moderación (📅, ✅, 🕐)
- Profesional pero no robótica
- Breve y directa
"""


def get_gemini_client():
    """Obtiene el cliente de Gemini configurado."""
    if not GEMINI_AVAILABLE:
        return None
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return None
    
    return genai.Client(api_key=api_key)


# Templates base (fallback)
TEMPLATES = {
    'evento_creado': "✅ Listo! Agendé '{titulo}' para el {fecha} a las {hora}.",
    'evento_eliminado': "🗑️ Eliminé el evento '{titulo}' de tu calendario.",
    'evento_editado': "✏️ Actualicé el evento '{titulo}'.",
    'eventos_listados': "📅 Aquí están tus eventos:\n{lista}",
    'disponible': "✅ Estás libre el {fecha} a las {hora}.",
    'no_disponible': "⚠️ Tienes conflicto: {conflictos}",
    'confirmacion_requerida': "❓ {mensaje}\nResponde 'sí' para confirmar.",
    'error': "😅 Hubo un problema: {mensaje}",
    'no_autorizado': "🔒 Lo siento, no tengo permisos para esa función.",
    'fuera_alcance': "📅 Solo puedo ayudarte con tu calendario. ¿Necesitas agendar algo?",
}


def generar_respuesta(tipo: str, datos: Dict[str, Any], incluir_fuente: bool = False) -> str:
    """
    Genera una respuesta amigable según el tipo de acción.
    
    Args:
        tipo: Tipo de respuesta
        datos: Datos relevantes
        incluir_fuente: Si incluir info técnica (ID)
    
    Returns:
        Mensaje formateado
    """
    client = get_gemini_client()
    
    # Si Gemini está disponible, generar respuesta más natural
    if client:
        prompt = f"""{PERSONALIDAD}

Genera una respuesta para:
Tipo: {tipo}
Datos: {datos}

Respuesta corta (1-2 oraciones), amigable. Solo texto plano con emojis.
"""
        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt
            )
            respuesta = response.text.strip()
            
            if incluir_fuente and datos.get('id'):
                respuesta += f"\n\n📋 ID: {datos['id']}"
            
            return respuesta
        except Exception:
            pass
    
    # Fallback a template
    template = TEMPLATES.get(tipo, "Operación completada.")
    try:
        respuesta = template.format(**datos)
    except KeyError:
        respuesta = template
    
    if incluir_fuente and datos.get('id'):
        respuesta += f"\n\n📋 ID: {datos['id']}"
    
    return respuesta


def formatear_lista_eventos(eventos: List[Dict[str, Any]]) -> str:
    """Formatea una lista de eventos."""
    if not eventos:
        return "📭 No tienes eventos programados."
    
    lineas = []
    for evento in eventos:
        hora = evento.get('inicio', '').split('T')[1][:5] if 'T' in evento.get('inicio', '') else ''
        lineas.append(f"• {hora} - {evento['titulo']}")
    
    return "\n".join(lineas)


def mensaje_confirmacion(accion: str, evento: str) -> str:
    """Genera mensaje de confirmación para acciones destructivas."""
    mensajes = {
        'eliminar': f"❓ ¿Confirmas que quieres eliminar '{evento}'?",
        'mover': f"❓ ¿Confirmas que quieres mover '{evento}'?",
        'editar': f"❓ ¿Confirmas los cambios a '{evento}'?",
    }
    return mensajes.get(accion, f"❓ ¿Confirmas esta acción sobre '{evento}'?") + "\nResponde 'sí' para confirmar."


def mensaje_bienvenida() -> str:
    """Genera mensaje de bienvenida."""
    return """👋 ¡Hola! Soy SekretariaBot, tu asistente de calendario.

Puedo ayudarte a:
📅 Agendar eventos
🔍 Consultar tu calendario  
✏️ Editar o mover citas
🗑️ Cancelar eventos

¿En qué te puedo ayudar?"""


if __name__ == '__main__':
    print(mensaje_bienvenida())
