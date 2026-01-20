"""
Servicio de Google Calendar para SekretariaBot.
Maneja autenticación OAuth y operaciones CRUD de eventos.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scope para acceso completo al calendario
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Rutas de credenciales (relativas al proyecto)
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / 'credentials.json'
TOKEN_FILE = PROJECT_ROOT / 'token.json'

# Zona horaria por defecto
DEFAULT_TIMEZONE = 'America/Bogota'


def get_calendar_service():
    """
    Obtiene el servicio de Google Calendar autenticado.
    Maneja el flujo OAuth si es necesario.
    """
    creds = None
    
    # Cargar token existente
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    # Si no hay credenciales válidas, hacer flujo OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"No se encontró {CREDENTIALS_FILE}. "
                    "Descarga las credenciales de Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Guardar token para próximas ejecuciones
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)


def crear_evento(
    titulo: str,
    fecha_inicio: datetime,
    duracion_minutos: int = 60,
    descripcion: str = "",
    ubicacion: str = "",
    participantes: List[str] = None,
    timezone: str = DEFAULT_TIMEZONE
) -> Dict[str, Any]:
    """
    Crea un nuevo evento en Google Calendar.
    
    Args:
        titulo: Nombre del evento
        fecha_inicio: Fecha y hora de inicio
        duracion_minutos: Duración en minutos (default 60)
        descripcion: Descripción opcional
        ubicacion: Ubicación opcional
        participantes: Lista de emails para invitar
        timezone: Zona horaria
    
    Returns:
        Diccionario con info del evento creado (id, link, etc.)
    """
    service = get_calendar_service()
    
    fecha_fin = fecha_inicio + timedelta(minutes=duracion_minutos)
    
    evento = {
        'summary': titulo,
        'location': ubicacion,
        'description': descripcion,
        'start': {
            'dateTime': fecha_inicio.isoformat(),
            'timeZone': timezone,
        },
        'end': {
            'dateTime': fecha_fin.isoformat(),
            'timeZone': timezone,
        },
    }
    
    if participantes:
        evento['attendees'] = [{'email': email} for email in participantes]
    
    try:
        evento_creado = service.events().insert(
            calendarId='primary',
            body=evento,
            sendUpdates='all' if participantes else 'none'
        ).execute()
        
        return {
            'success': True,
            'id': evento_creado['id'],
            'titulo': evento_creado['summary'],
            'inicio': evento_creado['start'].get('dateTime'),
            'link': evento_creado.get('htmlLink'),
        }
    except HttpError as e:
        return {
            'success': False,
            'error': str(e),
        }


def listar_eventos(
    fecha_inicio: datetime = None,
    fecha_fin: datetime = None,
    max_resultados: int = 10
) -> List[Dict[str, Any]]:
    """
    Lista eventos del calendario en un rango de fechas.
    
    Args:
        fecha_inicio: Desde cuándo buscar (default: ahora)
        fecha_fin: Hasta cuándo buscar (default: +7 días)
        max_resultados: Máximo de eventos a retornar
    
    Returns:
        Lista de eventos con id, título, inicio, fin
    """
    service = get_calendar_service()
    
    if fecha_inicio is None:
        fecha_inicio = datetime.now()
    if fecha_fin is None:
        fecha_fin = fecha_inicio + timedelta(days=7)
    
    try:
        eventos = service.events().list(
            calendarId='primary',
            timeMin=fecha_inicio.isoformat() + 'Z',
            timeMax=fecha_fin.isoformat() + 'Z',
            maxResults=max_resultados,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        resultado = []
        for evento in eventos.get('items', []):
            inicio = evento['start'].get('dateTime', evento['start'].get('date'))
            fin = evento['end'].get('dateTime', evento['end'].get('date'))
            resultado.append({
                'id': evento['id'],
                'titulo': evento.get('summary', 'Sin título'),
                'inicio': inicio,
                'fin': fin,
                'ubicacion': evento.get('location', ''),
                'estado': evento.get('status', 'confirmed'),
            })
        
        return resultado
    except HttpError as e:
        return []


def editar_evento(
    evento_id: str,
    nuevo_titulo: str = None,
    nueva_fecha: datetime = None,
    nueva_duracion: int = None,
    nueva_descripcion: str = None,
    nueva_ubicacion: str = None,
    timezone: str = DEFAULT_TIMEZONE
) -> Dict[str, Any]:
    """
    Edita un evento existente.
    
    Args:
        evento_id: ID del evento a editar
        nuevo_titulo: Nuevo título (opcional)
        nueva_fecha: Nueva fecha/hora de inicio (opcional)
        nueva_duracion: Nueva duración en minutos (opcional)
        nueva_descripcion: Nueva descripción (opcional)
        nueva_ubicacion: Nueva ubicación (opcional)
    
    Returns:
        Resultado de la operación
    """
    service = get_calendar_service()
    
    try:
        # Obtener evento actual
        evento = service.events().get(
            calendarId='primary',
            eventId=evento_id
        ).execute()
        
        # Actualizar campos
        if nuevo_titulo:
            evento['summary'] = nuevo_titulo
        if nueva_descripcion:
            evento['description'] = nueva_descripcion
        if nueva_ubicacion:
            evento['location'] = nueva_ubicacion
        
        if nueva_fecha:
            # Calcular duración original o usar la nueva
            inicio_original = datetime.fromisoformat(
                evento['start']['dateTime'].replace('Z', '+00:00')
            )
            fin_original = datetime.fromisoformat(
                evento['end']['dateTime'].replace('Z', '+00:00')
            )
            duracion = nueva_duracion or int((fin_original - inicio_original).seconds / 60)
            
            evento['start'] = {
                'dateTime': nueva_fecha.isoformat(),
                'timeZone': timezone,
            }
            evento['end'] = {
                'dateTime': (nueva_fecha + timedelta(minutes=duracion)).isoformat(),
                'timeZone': timezone,
            }
        
        evento_actualizado = service.events().update(
            calendarId='primary',
            eventId=evento_id,
            body=evento
        ).execute()
        
        return {
            'success': True,
            'id': evento_actualizado['id'],
            'titulo': evento_actualizado['summary'],
            'mensaje': 'Evento actualizado correctamente',
        }
    except HttpError as e:
        return {
            'success': False,
            'error': str(e),
        }


def eliminar_evento(evento_id: str) -> Dict[str, Any]:
    """
    Elimina un evento del calendario.
    
    Args:
        evento_id: ID del evento a eliminar
    
    Returns:
        Resultado de la operación
    """
    service = get_calendar_service()
    
    try:
        # Obtener info del evento antes de borrar
        evento = service.events().get(
            calendarId='primary',
            eventId=evento_id
        ).execute()
        titulo = evento.get('summary', 'Sin título')
        
        service.events().delete(
            calendarId='primary',
            eventId=evento_id
        ).execute()
        
        return {
            'success': True,
            'mensaje': f'Evento "{titulo}" eliminado correctamente',
        }
    except HttpError as e:
        return {
            'success': False,
            'error': str(e),
        }


def buscar_disponibilidad(
    fecha: datetime,
    duracion_minutos: int = 60
) -> Dict[str, Any]:
    """
    Busca si hay disponibilidad en una fecha/hora específica.
    
    Args:
        fecha: Fecha y hora a verificar
        duracion_minutos: Duración del hueco necesario
    
    Returns:
        Disponibilidad y conflictos si los hay
    """
    fecha_fin = fecha + timedelta(minutes=duracion_minutos)
    eventos = listar_eventos(fecha, fecha_fin, max_resultados=5)
    
    if not eventos:
        return {
            'disponible': True,
            'mensaje': f'Estás libre el {fecha.strftime("%d/%m a las %H:%M")}',
        }
    else:
        conflictos = [e['titulo'] for e in eventos]
        return {
            'disponible': False,
            'conflictos': conflictos,
            'mensaje': f'Tienes {len(eventos)} evento(s): {", ".join(conflictos)}',
        }


if __name__ == '__main__':
    # Test rápido
    print("Probando conexión a Google Calendar...")
    try:
        service = get_calendar_service()
        print("✅ Conexión exitosa")
        
        eventos = listar_eventos(max_resultados=3)
        print(f"\nPróximos {len(eventos)} eventos:")
        for e in eventos:
            print(f"  - {e['titulo']} ({e['inicio']})")
    except Exception as e:
        print(f"❌ Error: {e}")
