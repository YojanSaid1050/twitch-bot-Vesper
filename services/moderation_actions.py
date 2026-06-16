"""
Servicio para acciones de moderación (timeout, ban, etc)
"""

from typing import Optional, List, Dict

from config import settings
from services.twitch_api import TwitchAPI
from exceptions import TwitchAPIError, ResourceNotFoundError
from utils.logger import get_logger


logger = get_logger(__name__)


class ModerationActions:
    """
    Servicio para acciones de moderación
    """
    
    def __init__(self):
        self.api = TwitchAPI(use_broadcaster_token=False)
        self.broadcaster_id = settings.BROADCASTER_ID
        self.moderator_id = settings.BOT_ID
    
    def _get_mod_params(self) -> dict:
        """Parámetros comunes para acciones de moderación"""
        return {
            "broadcaster_id": self.broadcaster_id,
            "moderator_id": self.moderator_id
        }
    
    async def get_user_id(self, username: str) -> Optional[str]:
        """
        Obtener ID de un usuario por su nombre
        
        Args:
            username: Nombre del usuario
        
        Returns:
            ID del usuario o None si no existe
        """
        result = self.api.get(
            "users",
            params={"login": username.lower()}
        )
        
        data = result.get("data", [])
        
        if not data:
            return None
        
        return data[0]["id"]
    
    async def timeout(self, username: str, duration_seconds: int, reason: str = "") -> bool:
        """
        Aplicar timeout a un usuario
        
        Args:
            username: Nombre del usuario
            duration_seconds: Duración en segundos (1-1209600 = 14 días)
            reason: Razón del timeout
        
        Returns:
            True si fue exitoso
        """
        user_id = await self.get_user_id(username)
        
        if not user_id:
            raise ResourceNotFoundError(f"Usuario {username} no encontrado")
        
        payload = {
            "user_id": user_id,
            "duration": duration_seconds,
            "reason": reason[:500] if reason else ""  # Máximo 500 caracteres
        }
        
        logger.info(f"Timeout a {username} por {duration_seconds}s: {reason}")
        
        response = self.api.post(
            "moderation/bans",
            params=self._get_mod_params(),
            json=payload
        )
        
        return response is not None
    
    async def ban(self, username: str, reason: str = "") -> bool:
        """
        Banear a un usuario permanentemente
        
        Args:
            username: Nombre del usuario
            reason: Razón del ban
        
        Returns:
            True si fue exitoso
        """
        return await self.timeout(username, 1209600, reason)  # 14 días (máximo)
    
    async def unban(self, username: str) -> bool:
        """
        Desbanear a un usuario
        
        Args:
            username: Nombre del usuario
        
        Returns:
            True si fue exitoso
        """
        user_id = await self.get_user_id(username)
        
        if not user_id:
            raise ResourceNotFoundError(f"Usuario {username} no encontrado")
        
        logger.info(f"Desbaneando a {username}")
        
        response = self.api.delete(
            "moderation/bans",
            params={
                "broadcaster_id": self.broadcaster_id,
                "moderator_id": self.moderator_id,
                "user_id": user_id
            }
        )
        
        return response is None  # 204 = éxito
    
    async def clear_chat(self) -> bool:
        """
        Limpiar el chat completamente (timeout de 1 segundo a todos)
        
        Returns:
            True si fue exitoso
        """
        logger.info("Limpiando chat...")
        
        response = self.api.post(
            "moderation/chat_clear",
            params=self._get_mod_params()
        )
        
        return response is None
    
    async def vip(self, username: str) -> bool:
        """
        Agregar usuario a VIP
        
        Args:
            username: Nombre del usuario
        
        Returns:
            True si fue exitoso
        """
        user_id = await self.get_user_id(username)
        
        if not user_id:
            raise ResourceNotFoundError(f"Usuario {username} no encontrado")
        
        logger.info(f"Agregando VIP a {username}")
        
        response = self.api.post(
            "channels/vips",
            params={
                "broadcaster_id": self.broadcaster_id,
                "user_id": user_id
            }
        )
        
        return response is None
    
    async def unvip(self, username: str) -> bool:
        """
        Remover usuario de VIP
        
        Args:
            username: Nombre del usuario
        
        Returns:
            True si fue exitoso
        """
        user_id = await self.get_user_id(username)
        
        if not user_id:
            raise ResourceNotFoundError(f"Usuario {username} no encontrado")
        
        logger.info(f"Removiendo VIP de {username}")
        
        response = self.api.delete(
            "channels/vips",
            params={
                "broadcaster_id": self.broadcaster_id,
                "user_id": user_id
            }
        )
        
        return response is None