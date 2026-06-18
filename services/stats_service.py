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
            
            return data[0]
        except TwitchAPIError as e:
            logger.error(f"Error obteniendo stream info: {e}")
            log_service.add_log('error', f'Error obteniendo stream info: {e}', 'stats_service')
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
            
            return data[0]
        except TwitchAPIError as e:
            logger.error(f"Error obteniendo canal info: {e}")
            log_service.add_log('error', f'Error obteniendo canal info: {e}', 'stats_service')
            return None
    
    async def get_followers_count(self) -> int:
        """Obtener número de seguidores"""
        try:
            result = self.api.get(
                "channels/followers",
                params={"broadcaster_id": self.broadcaster_id}
            )
            
            return result.get("total", 0)
        except TwitchAPIError as e:
            if e.status_code in [400, 403, 404]:
                logger.debug(f"Seguidores no disponibles: {e.status_code}")
            else:
                logger.error(f"Error obteniendo seguidores: {e}")
                log_service.add_log('error', f'Error obteniendo seguidores: {e}', 'stats_service')
            return 0
    
    async def get_subscribers_count(self) -> int:
        """Obtener número de suscriptores"""
        try:
            result = self.api.get(
                "subscriptions",
                params={"broadcaster_id": self.broadcaster_id}
            )
            
            return result.get("total", 0)
        except TwitchAPIError as e:
            if e.status_code in [400, 403, 404]:
                logger.debug(f"Suscriptores no disponibles: {e.status_code}")
            else:
                logger.error(f"Error obteniendo suscriptores: {e}")
                log_service.add_log('error', f'Error obteniendo suscriptores: {e}', 'stats_service')
            return 0
    
    async def get_uptime(self) -> Optional[timedelta]:
        """Obtener tiempo de stream"""
        stream_info = await self.get_stream_info()
        
        if not stream_info:
            return None
        
        started_at = datetime.fromisoformat(stream_info["started_at"].replace("Z", "+00:00"))
        uptime = datetime.now().astimezone() - started_at
        
        return uptime
    
    async def get_viewer_count(self) -> int:
        """Obtener número de espectadores"""
        stream_info = await self.get_stream_info()
        
        if not stream_info:
            return 0
        
        return stream_info.get("viewer_count", 0)
    
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