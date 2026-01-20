# SekretariaBot - Asistente de Calendario por Telegram

## Objetivo
Bot de Telegram que gestiona Google Calendar. Recibe mensajes (texto/audio), detecta intención, ejecuta acciones en Calendar y responde con estilo amigable (Gemini).

## Entradas
- Mensajes de Telegram (texto o audio)
- ID de usuario de Telegram
- Credenciales OAuth de Google Calendar

## Arquitectura

```
Usuario Telegram
      ↓
[telegram_bot.py] ──→ Audio? ──→ [audio_transcriber.py]
      ↓                                   ↓
[intent_parser.py] ←─────────────────────┘
      ↓
¿Intención de Calendar?
   ├── Sí → [calendar_service.py] → Ejecutar acción
   └── No → Respuesta genérica
      ↓
[gemini_responder.py] → Generar respuesta amigable
      ↓
Enviar respuesta a Telegram
```

## Intenciones Soportadas

| Intención | Ejemplo | Acción |
|-----------|---------|--------|
| `crear_evento` | "Agenda reunión mañana a las 3pm" | Crear evento |
| `editar_evento` | "Cambia la reunión a las 4" | Actualizar evento |
| `mover_evento` | "Mueve la cita al viernes" | Cambiar fecha/hora |
| `eliminar_evento` | "Cancela mi cita con el doctor" | Borrar evento |
| `consultar_eventos` | "¿Qué tengo el 7 de enero?" | Listar eventos |
| `disponibilidad` | "¿Estoy libre el martes?" | Verificar huecos |

## Herramientas/Scripts

| Script | Función |
|--------|---------|
| `ejecucion/telegram_bot.py` | Bot principal, polling de mensajes |
| `ejecucion/audio_transcriber.py` | Whisper/Google STT para audio |
| `ejecucion/calendar_service.py` | CRUD de Google Calendar |
| `ejecucion/intent_parser.py` | Detectar intención con LLM |
| `ejecucion/gemini_responder.py` | Generar respuestas amables |

## Configuración Requerida (.env)

```
TELEGRAM_BOT_TOKEN=tu_token_de_botfather
GOOGLE_API_KEY=para_gemini
# OAuth credentials en credentials.json
```

## Salidas
- Mensajes de respuesta en Telegram
- Eventos creados/modificados en Google Calendar

## Casos Límite

### Confirmación para acciones destructivas
Si el usuario pide borrar o mover eventos de forma ambigua:
> "¿Confirmas que quieres borrar 'Reunión con Juan'? Responde 'sí' para confirmar."

### Fecha/hora incompleta
- Sin año → asumir año actual (2026)
- Sin zona horaria → usar América/Bogotá o pedir aclaración

### Sin autorización OAuth
> "Necesito acceso a tu calendario. Por favor autoriza con /autorizar"

### Intención no relacionada con Calendar
> "Lo siento, solo puedo ayudarte con tu calendario 📅"
