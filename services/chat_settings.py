"""
Servicio para gestionar configuraciones del chat
"""

from typing import Optional
from config import settings
from services.twitch_api import TwitchAPI
from exceptions import TwitchAPIError, ValidationError
from utils.logger import get_logger


logger = get_logger(__name__)


class ChatSettings:
    """
    Servicio para configurar ajustes del chat (modo lento, followers, etc)
    """
    
    def __init__(self):
        # Los settings del chat requieren token del bot con permisos de moderador
        self.api = TwitchAPI(use_broadcaster_token=False)
        self.broadcaster_id = settings.BROADCASTER_ID
        self.moderator_id = settings.BOT_ID
    
    def _get_params(self) -> dict:
        """Parámetros comunes para las peticiones de chat"""
        return {
            "broadcaster_id": self.broadcaster_id,
            "moderator_id": self.moderator_id
        }
    
    async def set_slow_mode(self, enabled: bool, wait_time: Optional[int] = None) -> bool:
        """
        Configurar modo lento
        
        Args:
            enabled: Activar o desactivar
            wait_time: Segundos de espera entre mensajes (si enabled=True)
        
        Returns:
            True si fue exitoso
        """
        if enabled and (wait_time is None or wait_time < 1):
            raise ValidationError("El tiempo de espera debe ser mayor a 0")
        
        if enabled and wait_time > 120:
            raise ValidationError("El tiempo de espera no puede exceder 120 segundos")
        
        payload = {"slow_mode": enabled}
        
        if enabled:
            payload["slow_mode_wait_time"] = wait_time
        
        logger.info(f"Configurando modo lento: enabled={enabled}, wait_time={wait_time}")
        
        response = self.api.patch(
            "chat/settings",
            params=self._get_params(),
            json=payload
        )
        
        return response is None
    
    async def set_follower_mode(self, enabled: bool, duration_minutes: Optional[int] = None) -> bool:
        """
        Configurar modo followers (solo seguidores pueden hablar)
        
        Args:
            enabled: Activar o desactivar
            duration_minutes: Minutos que el usuario debe haber seguido (si enabled=True)
        
        Returns:
            True si fue exitoso
        """
        if enabled and duration_minutes is None:
            duration_minutes = 10  # Valor por defecto
        
        if enabled and duration_minutes < 1:
            raise ValidationError("La duración debe ser mayor a 0")
        
        if enabled and duration_minutes > 129600:  # 90 días
            raise ValidationError("La duración no puede exceder 90 días")
        
        payload = {"follower_mode": enabled}
        
        if enabled:
            payload["follower_mode_duration"] = duration_minutes
        
        logger.info(f"Configurando modo followers: enabled={enabled}, duration={duration_minutes}")
        
        response = self.api.patch(
            "chat/settings",
            params=self._get_params(),
            json=payload
        )
        
        return response is None
    
    async def set_emote_mode(self, enabled: bool) -> bool:
        """
        Configurar modo solo emotes
        
        Args:
            enabled: Activar o desactivar
        
        Returns:
            True si fue exitoso
        """
        logger.info(f"Configurando modo solo emotes: enabled={enabled}")
        
        response = self.api.patch(
            "chat/settings",
            params=self._get_params(),
            json={"emote_mode": enabled}
        )
        
        return response is None
    
    async def set_subscriber_mode(self, enabled: bool) -> bool:
        """
        Configurar modo solo suscriptores
        
        Args:
            enabled: Activar o desactivar
        
        Returns:
            True si fue exitoso
        """
        logger.info(f"Configurando modo solo suscriptores: enabled={enabled}")
        
        response = self.api.patch(
            "chat/settings",
            params=self._get_params(),
            json={"subscriber_mode": enabled}
        )
        
        return response is None