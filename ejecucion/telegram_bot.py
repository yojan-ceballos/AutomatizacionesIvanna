"""
Bot principal de Telegram para SekretariaBot.
Coordina todos los módulos: transcripción, parsing de intención, calendario y respuestas.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Importar módulos de ejecución
from ejecucion.audio_transcriber import transcribir_audio_telegram
from ejecucion.intent_parser import parsear_intencion, es_intencion_calendario
from ejecucion.calendar_service import (
    crear_evento, listar_eventos, editar_evento, 
    eliminar_evento, buscar_disponibilidad
)
from ejecucion.gemini_responder import (
    generar_respuesta, formatear_lista_eventos,
    mensaje_confirmacion, mensaje_bienvenida
)

# Importar telegram
try:
    from telegram import Update
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, 
        ContextTypes, filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.error("python-telegram-bot no instalado. Ejecuta: pip install python-telegram-bot")

# Estado de conversación por usuario (para confirmaciones pendientes)
user_states: Dict[int, Dict[str, Any]] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Mensaje de bienvenida."""
    await update.message.reply_text(mensaje_bienvenida())


async def autorizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /autorizar - Inicia flujo OAuth de Google Calendar."""
    try:
        from ejecucion.calendar_service import get_calendar_service
        service = get_calendar_service()
        await update.message.reply_text(
            "✅ ¡Autorización exitosa! Ya puedo gestionar tu calendario."
        )
    except FileNotFoundError as e:
        await update.message.reply_text(
            "❌ No encontré las credenciales de Google.\n"
            "Asegúrate de tener el archivo credentials.json configurado."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error en autorización: {str(e)}"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto del usuario."""
    user_id = update.effective_user.id
    texto = update.message.text
    
    # Verificar si hay una confirmación pendiente
    if user_id in user_states and user_states[user_id].get('pendiente'):
        respuesta = await manejar_confirmacion(user_id, texto)
        await update.message.reply_text(respuesta)
        return
    
    # Parsear intención
    resultado = parsear_intencion(texto, datetime.now())
    
    if not resultado.get('success'):
        await update.message.reply_text(
            generar_respuesta('error', {'mensaje': resultado.get('error', 'Error desconocido')})
        )
        return
    
    intencion = resultado.get('intencion', 'otro')
    entidades = resultado.get('entidades', {})
    
    # Si no es intención de calendario
    if not es_intencion_calendario(intencion):
        await update.message.reply_text(
            generar_respuesta('fuera_alcance', {})
        )
        return
    
    # Si requiere confirmación, guardar estado y pedir
    if resultado.get('requiere_confirmacion'):
        user_states[user_id] = {
            'pendiente': True,
            'intencion': intencion,
            'entidades': entidades,
        }
        await update.message.reply_text(
            mensaje_confirmacion(
                intencion.replace('_evento', ''),
                entidades.get('evento_referencia', entidades.get('titulo', 'este evento'))
            )
        )
        return
    
    # Ejecutar la acción
    respuesta = await ejecutar_accion(intencion, entidades)
    await update.message.reply_text(respuesta)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de voz."""
    voice = update.message.voice
    
    # Indicar que estamos procesando
    await update.message.reply_text("🎤 Procesando audio...")
    
    # Transcribir
    resultado = await transcribir_audio_telegram(voice, context.bot)
    
    if not resultado.get('success'):
        await update.message.reply_text(
            generar_respuesta('error', {'mensaje': resultado.get('error')})
        )
        return
    
    texto = resultado['texto']
    await update.message.reply_text(f"📝 Escuché: \"{texto}\"")
    
    # Procesar como texto normal
    update.message.text = texto
    await handle_message(update, context)


async def manejar_confirmacion(user_id: int, respuesta: str) -> str:
    """Maneja respuestas a confirmaciones pendientes."""
    estado = user_states.get(user_id, {})
    
    # Limpiar estado
    user_states.pop(user_id, None)
    
    respuesta_lower = respuesta.lower().strip()
    
    if respuesta_lower in ['sí', 'si', 'yes', 'confirmo', 'ok']:
        # Ejecutar la acción confirmada
        return await ejecutar_accion(
            estado.get('intencion'),
            estado.get('entidades', {})
        )
    else:
        return "❌ Operación cancelada."


async def ejecutar_accion(intencion: str, entidades: Dict[str, Any]) -> str:
    """Ejecuta una acción de calendario y retorna respuesta."""
    
    try:
        if intencion == 'crear_evento':
            # Construir fecha/hora
            fecha_str = entidades.get('fecha_resuelta', entidades.get('fecha'))
            hora_str = entidades.get('hora', '09:00')
            
            if fecha_str and hora_str:
                fecha_inicio = datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
            else:
                return generar_respuesta('error', {'mensaje': 'Necesito saber la fecha y hora'})
            
            resultado = crear_evento(
                titulo=entidades.get('titulo', 'Evento sin título'),
                fecha_inicio=fecha_inicio,
                duracion_minutos=entidades.get('duracion_minutos', 60),
                ubicacion=entidades.get('ubicacion', ''),
                participantes=entidades.get('participantes', [])
            )
            
            if resultado.get('success'):
                return generar_respuesta('evento_creado', {
                    'titulo': resultado['titulo'],
                    'fecha': fecha_inicio.strftime('%d/%m/%Y'),
                    'hora': fecha_inicio.strftime('%H:%M'),
                    'id': resultado['id']
                }, incluir_fuente=True)
            else:
                return generar_respuesta('error', {'mensaje': resultado.get('error')})
        
        elif intencion == 'consultar_eventos':
            fecha_str = entidades.get('fecha_resuelta', entidades.get('fecha'))
            if fecha_str:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            else:
                fecha = datetime.now()
            
            eventos = listar_eventos(fecha_inicio=fecha, max_resultados=5)
            lista = formatear_lista_eventos(eventos)
            
            return f"📅 Eventos del {fecha.strftime('%d/%m/%Y')}:\n\n{lista}"
        
        elif intencion == 'disponibilidad':
            fecha_str = entidades.get('fecha_resuelta', entidades.get('fecha'))
            hora_str = entidades.get('hora', '09:00')
            
            if fecha_str:
                fecha = datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
            else:
                fecha = datetime.now()
            
            resultado = buscar_disponibilidad(fecha)
            
            if resultado['disponible']:
                return generar_respuesta('disponible', {
                    'fecha': fecha.strftime('%d/%m/%Y'),
                    'hora': fecha.strftime('%H:%M')
                })
            else:
                return generar_respuesta('no_disponible', {
                    'conflictos': resultado['mensaje']
                })
        
        elif intencion == 'eliminar_evento':
            # Buscar evento por referencia
            eventos = listar_eventos(max_resultados=10)
            evento_ref = entidades.get('evento_referencia', '').lower()
            
            evento_encontrado = None
            for e in eventos:
                if evento_ref in e['titulo'].lower():
                    evento_encontrado = e
                    break
            
            if evento_encontrado:
                resultado = eliminar_evento(evento_encontrado['id'])
                if resultado.get('success'):
                    return generar_respuesta('evento_eliminado', {
                        'titulo': evento_encontrado['titulo']
                    })
                else:
                    return generar_respuesta('error', {'mensaje': resultado.get('error')})
            else:
                return generar_respuesta('error', {
                    'mensaje': f'No encontré un evento que coincida con "{evento_ref}"'
                })
        
        elif intencion == 'editar_evento' or intencion == 'mover_evento':
            # Similar a eliminar, buscar y editar
            eventos = listar_eventos(max_resultados=10)
            evento_ref = entidades.get('evento_referencia', '').lower()
            
            evento_encontrado = None
            for e in eventos:
                if evento_ref in e['titulo'].lower():
                    evento_encontrado = e
                    break
            
            if not evento_encontrado:
                return generar_respuesta('error', {
                    'mensaje': f'No encontré un evento que coincida con "{evento_ref}"'
                })
            
            # Construir nueva fecha si se proporciona
            nueva_fecha = None
            fecha_str = entidades.get('fecha_resuelta', entidades.get('fecha'))
            hora_str = entidades.get('hora')
            
            if fecha_str and hora_str:
                nueva_fecha = datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
            elif fecha_str:
                nueva_fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            
            resultado = editar_evento(
                evento_id=evento_encontrado['id'],
                nuevo_titulo=entidades.get('titulo'),
                nueva_fecha=nueva_fecha,
                nueva_ubicacion=entidades.get('ubicacion')
            )
            
            if resultado.get('success'):
                return generar_respuesta('evento_editado', {
                    'titulo': evento_encontrado['titulo']
                })
            else:
                return generar_respuesta('error', {'mensaje': resultado.get('error')})
        
        else:
            return generar_respuesta('fuera_alcance', {})
    
    except Exception as e:
        logger.error(f"Error ejecutando acción: {e}")
        return generar_respuesta('error', {'mensaje': str(e)})


def main():
    """Punto de entrada principal del bot."""
    if not TELEGRAM_AVAILABLE:
        print("❌ python-telegram-bot no está instalado")
        print("   Ejecuta: pip install python-telegram-bot")
        return
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN no configurado en .env")
        return
    
    print("🤖 Iniciando SekretariaBot...")
    
    # Crear aplicación
    app = Application.builder().token(token).build()
    
    # Registrar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("autorizar", autorizar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Iniciar bot
    print("✅ Bot iniciado. Presiona Ctrl+C para detener.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
