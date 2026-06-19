"""
Servicio de estadísticas del stream
"""

from datetime import datetime, timedelta
from typing import Optional, Dict

from config import settings
from services.twitch_api import TwitchAPI
from exceptions import TwitchAPIError
from utils.logger import get_logger
from services.log_service import log_service

logger = get_logger(__name__)


class StatsService:
    """Servicio para obtener estadísticas del stream"""
    
    def __init__(self):
        self.api = TwitchAPI(use_broadcaster_token=False)
        self.broadcaster_id = settings.BROADCASTER_ID
        self._stream_info = None
        self._last_update = None
    
    async def get_stream_info(self) -> Optional[Dict]:
        """Obtener información actual del stream"""
        try:
            result = self.api.get(
                "streams",
                params={"user_id": self.broadcaster_id}
            )
            
            data = result.get("data", [])
            
            if not data:
                return None
            
            # Log de éxito (estadísticas)
            stream_data = data[0]
            log_service.add_log(
                'info', 
                f'Stream info obtenida: {stream_data.get("game_name", "Desconocido")} - {stream_data.get("viewer_count", 0)} viewers',
                'stats'
            )
            return stream_data
        except TwitchAPIError as e:
            logger.error(f"Error obteniendo stream info: {e}")
            log_service.add_log('error', f'Error obteniendo stream info: {e}', 'twitch_api')
            return None
    
    async def get_channel_info(self) -> Optional[Dict]:
        """Obtener información del canal (título, juego, etc)"""
        try:
            result = self.api.get(
                "channels",
                params={"broadcaster_id": self.broadcaster_id}
            )
            
            data = result.get("data", [])
            
            if not data:
                return None
            
            # Log de éxito (estadísticas)
            channel_data = data[0]
            log_service.add_log(
                'info', 
                f'Canal info obtenida: "{channel_data.get("title", "Sin título")}" - {channel_data.get("game_name", "No especificado")}',
                'stats'
            )
            return channel_data
        except TwitchAPIError as e:
            logger.error(f"Error obteniendo canal info: {e}")
            log_service.add_log('error', f'Error obteniendo canal info: {e}', 'twitch_api')
            return None
    
    async def get_followers_count(self) -> int:
        """Obtener número de seguidores"""
        try:
            result = self.api.get(
                "channels/followers",
                params={"broadcaster_id": self.broadcaster_id}
            )
            
            total = result.get("total", 0)
            # Log de éxito (estadísticas)
            log_service.add_log('info', f'Seguidores obtenidos: {total}', 'stats')
            return total
        except TwitchAPIError as e:
            if e.status_code in [400, 403, 404]:
                logger.debug(f"Seguidores no disponibles: {e.status_code}")
            else:
                logger.error(f"Error obteniendo seguidores: {e}")
                log_service.add_log('error', f'Error obteniendo seguidores: {e}', 'twitch_api')
            return 0
    
    async def get_subscribers_count(self) -> int:
        """Obtener número de suscriptores"""
        try:
            result = self.api.get(
                "subscriptions",
                params={"broadcaster_id": self.broadcaster_id}
            )
            
            total = result.get("total", 0)
            # Log de éxito (estadísticas)
            log_service.add_log('info', f'Suscriptores obtenidos: {total}', 'stats')
            return total
        except TwitchAPIError as e:
            if e.status_code in [400, 403, 404]:
                logger.debug(f"Suscriptores no disponibles: {e.status_code}")
            else:
                logger.error(f"Error obteniendo suscriptores: {e}")
                log_service.add_log('error', f'Error obteniendo suscriptores: {e}', 'twitch_api')
            return 0
    
    async def get_uptime(self) -> Optional[timedelta]:
        """Obtener tiempo de stream"""
        stream_info = await self.get_stream_info()
        
        if not stream_info:
            return None
        
        started_at = datetime.fromisoformat(stream_info["started_at"].replace("Z", "+00:00"))
        uptime = datetime.now().astimezone() - started_at
        
        # Log de éxito (estadísticas) - solo si tiene más de 1 minuto para no saturar
        if uptime.total_seconds() > 60:
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            log_service.add_log('info', f'Uptime calculado: {hours}h {minutes}m', 'stats')
        
        return uptime
    
    async def get_viewer_count(self) -> int:
        """Obtener número de espectadores"""
        stream_info = await self.get_stream_info()
        
        if not stream_info:
            return 0
        
        viewers = stream_info.get("viewer_count", 0)
        # Log de éxito (estadísticas) - solo si hay espectadores
        if viewers > 0:
            log_service.add_log('info', f'Espectadores actuales: {viewers}', 'stats')
        return viewers
    
    async def format_uptime(self) -> str:
        """Formatear uptime para mostrar"""
        uptime = await self.get_uptime()
        
        if not uptime:
            return "⏱️ El stream no está en vivo 🕯️"
        
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or not parts:
            parts.append(f"{minutes}m")
        
        return f"⏱️ Stream activo por: {' '.join(parts)}"


# Instancia global
stats_service = StatsService()