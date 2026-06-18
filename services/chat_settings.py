"""
Servicio para gestionar configuraciones del chat
"""

from typing import Optional
from config import settings
from services.twitch_api import TwitchAPI
from exceptions import TwitchAPIError, ValidationError
from utils.logger import get_logger
from services.log_service import log_service

logger = get_logger(__name__)


class ChatSettings:
    """
    Servicio para configurar ajustes del chat (modo lento, followers, etc)
    """
    
    def __init__(self):
        self.api = TwitchAPI(use_broadcaster_token=False)
        self.broadcaster_id = settings.BROADCASTER_ID
        self.moderator_id = settings.BOT_ID
    
    def _get_params(self) -> dict:
        return {
            "broadcaster_id": self.broadcaster_id,
            "moderator_id": self.moderator_id
        }
    
    async def set_slow_mode(self, enabled: bool, wait_time: Optional[int] = None) -> bool:
        if enabled and (wait_time is None or wait_time < 1):
            raise ValidationError("El tiempo de espera debe ser mayor a 0")
        if enabled and wait_time > 120:
            raise ValidationError("El tiempo de espera no puede exceder 120 segundos")
        
        payload = {"slow_mode": enabled}
        if enabled:
            payload["slow_mode_wait_time"] = wait_time
        
        logger.info(f"Configurando modo lento: enabled={enabled}, wait_time={wait_time}")
        log_service.add_log('info', f'Modo lento {"activado" if enabled else "desactivado"} (wait_time={wait_time})', 'chat_settings')
        
        try:
            response = self.api.patch("chat/settings", params=self._get_params(), json=payload)
            return response is None
        except Exception as e:
            logger.error(f"Error configurando modo lento: {e}")
            log_service.add_log('error', f'Error configurando modo lento: {e}', 'chat_settings')
            raise
    
    async def set_follower_mode(self, enabled: bool, duration_minutes: Optional[int] = None) -> bool:
        if enabled and duration_minutes is None:
            duration_minutes = 10
        if enabled and duration_minutes < 1:
            raise ValidationError("La duración debe ser mayor a 0")
        if enabled and duration_minutes > 129600:
            raise ValidationError("La duración no puede exceder 90 días")
        
        payload = {"follower_mode": enabled}
        if enabled:
            payload["follower_mode_duration"] = duration_minutes
        
        logger.info(f"Configurando modo followers: enabled={enabled}, duration={duration_minutes}")
        log_service.add_log('info', f'Modo seguidores {"activado" if enabled else "desactivado"} (duration={duration_minutes})', 'chat_settings')
        
        try:
            response = self.api.patch("chat/settings", params=self._get_params(), json=payload)
            return response is None
        except Exception as e:
            logger.error(f"Error configurando modo followers: {e}")
            log_service.add_log('error', f'Error configurando modo followers: {e}', 'chat_settings')
            raise
    
    async def set_emote_mode(self, enabled: bool) -> bool:
        logger.info(f"Configurando modo solo emotes: enabled={enabled}")
        log_service.add_log('info', f'Modo emotes {"activado" if enabled else "desactivado"}', 'chat_settings')
        
        try:
            response = self.api.patch("chat/settings", params=self._get_params(), json={"emote_mode": enabled})
            return response is None
        except Exception as e:
            logger.error(f"Error configurando modo emotes: {e}")
            log_service.add_log('error', f'Error configurando modo emotes: {e}', 'chat_settings')
            raise
    
    async def set_subscriber_mode(self, enabled: bool) -> bool:
        logger.info(f"Configurando modo solo suscriptores: enabled={enabled}")
        log_service.add_log('info', f'Modo suscriptores {"activado" if enabled else "desactivado"}', 'chat_settings')
        
        try:
            response = self.api.patch("chat/settings", params=self._get_params(), json={"subscriber_mode": enabled})
            return response is None
        except Exception as e:
            logger.error(f"Error configurando modo suscriptores: {e}")
            log_service.add_log('error', f'Error configurando modo suscriptores: {e}', 'chat_settings')
            raise