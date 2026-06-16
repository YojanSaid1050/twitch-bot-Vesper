"""
Sistema de permisos y roles
"""

from typing import Optional
from twitchio import Message

from config import settings
from exceptions import PermissionDeniedError


class PermissionLevel:
    """Niveles de permiso"""
    EVERYONE = 0
    REGULAR = 1
    VIP = 2
    MODERATOR = 3
    OWNER = 4


class PermissionChecker:
    """
    Verificador de permisos para comandos
    """
    
    def __init__(self):
        self.broadcaster_name = settings.CHANNEL.lower()
    
    def get_user_level(self, message: Message) -> int:
        """
        Obtener nivel de permiso de un usuario
        
        Args:
            message: Mensaje de Twitch
        
        Returns:
            Nivel de permiso (ver PermissionLevel)
        """
        author = message.author
        
        # Owner (el streamer)
        if author.name.lower() == self.broadcaster_name:
            return PermissionLevel.OWNER
        
        # Moderador
        if author.is_mod:
            return PermissionLevel.MODERATOR
        
        # VIP
        if author.is_vip:
            return PermissionLevel.VIP
        
        # Usuario regular (no es necesario verificar, cualquiera que pueda hablar)
        return PermissionLevel.REGULAR
    
    def is_staff(self, message: Message) -> bool:
        """
        Verificar si el usuario es staff (mod o broadcaster)
        
        Args:
            message: Mensaje de Twitch
        
        Returns:
            True si es mod o broadcaster
        """
        level = self.get_user_level(message)
        return level >= PermissionLevel.MODERATOR
    
    def require_level(self, message: Message, required_level: int) -> bool:
        """
        Verificar si el usuario tiene el nivel requerido
        
        Args:
            message: Mensaje de Twitch
            required_level: Nivel requerido (de PermissionLevel)
        
        Returns:
            True si tiene permisos
        
        Raises:
            PermissionDeniedError: Si no tiene permisos
        """
        user_level = self.get_user_level(message)
        
        if user_level >= required_level:
            return True
        
        # Mensajes de error según el nivel requerido
        if required_level == PermissionLevel.MODERATOR:
            raise PermissionDeniedError("❌ Solo moderadores y el broadcaster pueden usar este comando")
        elif required_level == PermissionLevel.OWNER:
            raise PermissionDeniedError("❌ Solo el broadcaster puede usar este comando")
        elif required_level == PermissionLevel.VIP:
            raise PermissionDeniedError("❌ Solo VIPs, moderadores y el broadcaster pueden usar este comando")
        
        raise PermissionDeniedError("❌ No tienes permiso para usar este comando")


# Instancia global
permission_checker = PermissionChecker()