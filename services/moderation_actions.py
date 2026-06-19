"""
Servicio para acciones de moderación (timeout, ban, etc)
"""

import requests
from typing import Optional

from config import settings
from services.twitch_api import TwitchAPI
from services.log_service import log_service
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
        self.token = settings.BOT_TOKEN
    
    async def get_user_id(self, username: str) -> Optional[str]:
        try:
            result = self.api.get(
                "users",
                params={"login": username.lower()}
            )
            data = result.get("data", [])
            if not data:
                return None
            return data[0]["id"]
        except Exception as e:
            logger.error(f"Error obteniendo ID de {username}: {e}")
            log_service.add_log('error', f'Error obteniendo ID de {username}: {e}', 'twitch_api')
            return None
    
    async def delete_message(self, message_id: str) -> bool:
        token = settings.BOT_TOKEN
        if token.startswith("oauth:"):
            token = token[6:]
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }
        
        params = {
            "broadcaster_id": self.broadcaster_id,
            "moderator_id": self.moderator_id,
            "message_id": message_id
        }
        
        url = f"{self.api.base_url}/moderation/chat"
        
        try:
            logger.info(f"🗑️ Intentando eliminar mensaje {message_id}")
            response = requests.delete(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 204:
                logger.info(f"✅ Mensaje {message_id} eliminado correctamente")
                log_service.add_log('info', f'Mensaje {message_id} eliminado', 'moderation')
                return True
            elif response.status_code == 401:
                logger.warning("Token expirado, refrescando...")
                log_service.add_log('warning', 'Token expirado al eliminar mensaje, refrescando...', 'token_manager')
                from services.token_manager import token_manager
                token_manager.refresh_bot_token()
                return await self.delete_message(message_id)
            else:
                logger.error(f"❌ Error eliminando mensaje: {response.status_code} - {response.text}")
                log_service.add_log('error', f'Error eliminando mensaje {message_id}: {response.status_code}', 'twitch_api')
                return False
        except Exception as e:
            logger.error(f"❌ Excepción al eliminar mensaje: {e}")
            log_service.add_log('error', f'Excepción al eliminar mensaje {message_id}: {e}', 'bot')
            return False
    
    async def timeout(self, username: str, duration_seconds: int, reason: str = "") -> bool:
        user_id = await self.get_user_id(username)
        if not user_id:
            raise ResourceNotFoundError(f"Usuario {username} no encontrado")
        
        token = settings.BOT_TOKEN
        if token.startswith("oauth:"):
            token = token[6:]
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }
        
        url = f"{self.api.base_url}/moderation/bans?broadcaster_id={self.broadcaster_id}&moderator_id={self.moderator_id}"
        
        payload = {
            "data": {
                "user_id": user_id,
                "duration": duration_seconds
            }
        }
        if reason:
            payload["data"]["reason"] = reason[:500]
        
        logger.info(f"⏰ Timeout a {username} (ID: {user_id}) por {duration_seconds}s")
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"✅ Timeout aplicado a {username}")
                log_service.add_log('info', f'Timeout aplicado a {username} por {duration_seconds}s. Razón: {reason}', 'moderation')
                return True
            elif response.status_code == 401:
                logger.warning("Token expirado, refrescando...")
                log_service.add_log('warning', f'Token expirado al aplicar timeout a {username}', 'token_manager')
                from services.token_manager import token_manager
                token_manager.refresh_bot_token()
                return await self.timeout(username, duration_seconds, reason)
            else:
                error_msg = f"Error {response.status_code}: {response.text}"
                logger.error(f"❌ {error_msg}")
                log_service.add_log('error', f'Error aplicando timeout a {username}: {response.status_code}', 'twitch_api')
                raise TwitchAPIError(error_msg, status_code=response.status_code)
        except Exception as e:
            logger.error(f"❌ Error en timeout: {e}")
            log_service.add_log('error', f'Error en timeout a {username}: {e}', 'twitch_api')
            raise TwitchAPIError(f"Error en timeout: {e}")
    
    async def ban(self, username: str, reason: str = "") -> bool:
        log_service.add_log('info', f'Ban aplicado a {username}. Razón: {reason}', 'moderation')
        return await self.timeout(username, 1209600, reason)
    
    async def unban(self, username: str) -> bool:
        user_id = await self.get_user_id(username)
        if not user_id:
            raise ResourceNotFoundError(f"Usuario {username} no encontrado")
        
        token = settings.BOT_TOKEN
        if token.startswith("oauth:"):
            token = token[6:]
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }
        
        url = f"{self.api.base_url}/moderation/bans?broadcaster_id={self.broadcaster_id}&moderator_id={self.moderator_id}&user_id={user_id}"
        
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            if response.status_code == 204:
                logger.info(f"✅ {username} desbaneado")
                log_service.add_log('info', f'Unban aplicado a {username}', 'moderation')
                return True
            elif response.status_code == 401:
                logger.warning("Token expirado, refrescando...")
                log_service.add_log('warning', f'Token expirado al desbanear a {username}', 'token_manager')
                from services.token_manager import token_manager
                token_manager.refresh_bot_token()
                return await self.unban(username)
            else:
                logger.error(f"❌ Error desbaneando: {response.status_code} - {response.text}")
                log_service.add_log('error', f'Error desbaneando a {username}: {response.status_code}', 'twitch_api')
                return False
        except Exception as e:
            logger.error(f"❌ Error desbaneando: {e}")
            log_service.add_log('error', f'Error desbaneando a {username}: {e}', 'twitch_api')
            return False
    
    async def clear_chat(self) -> bool:
        token = settings.BOT_TOKEN
        if token.startswith("oauth:"):
            token = token[6:]
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }
        
        url = f"{self.api.base_url}/moderation/chat_clear?broadcaster_id={self.broadcaster_id}&moderator_id={self.moderator_id}"
        
        try:
            response = requests.post(url, headers=headers, timeout=10)
            if response.status_code == 204:
                logger.info("✅ Chat limpiado")
                log_service.add_log('info', 'Chat limpiado', 'moderation')
                return True
            elif response.status_code == 401:
                logger.warning("Token expirado, refrescando...")
                log_service.add_log('warning', 'Token expirado al limpiar chat', 'token_manager')
                from services.token_manager import token_manager
                token_manager.refresh_bot_token()
                return await self.clear_chat()
            else:
                logger.error(f"❌ Error limpiando chat: {response.status_code} - {response.text}")
                log_service.add_log('error', f'Error limpiando chat: {response.status_code}', 'twitch_api')
                return False
        except Exception as e:
            logger.error(f"❌ Error limpiando chat: {e}")
            log_service.add_log('error', f'Error limpiando chat: {e}', 'twitch_api')
            return False
    
    async def vip(self, username: str) -> bool:
        user_id = await self.get_user_id(username)
        if not user_id:
            raise ResourceNotFoundError(f"Usuario {username} no encontrado")
        
        token = settings.BROADCASTER_TOKEN
        if token.startswith("oauth:"):
            token = token[6:]
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }
        
        params = {
            "broadcaster_id": self.broadcaster_id,
            "user_id": user_id
        }
        
        url = f"{self.api.base_url}/channels/vips"
        
        try:
            response = requests.post(url, headers=headers, params=params, timeout=10)
            if response.status_code == 204:
                logger.info(f"✅ {username} es VIP ahora")
                log_service.add_log('info', f'VIP añadido a {username}', 'moderation')
                return True
            elif response.status_code == 401:
                logger.warning("Token expirado, refrescando...")
                log_service.add_log('warning', f'Token expirado al agregar VIP a {username}', 'token_manager')
                from services.token_manager import token_manager
                token_manager.refresh_broadcaster_token()
                return await self.vip(username)
            else:
                logger.error(f"❌ Error agregando VIP: {response.status_code} - {response.text}")
                log_service.add_log('error', f'Error agregando VIP a {username}: {response.status_code}', 'twitch_api')
                return False
        except Exception as e:
            logger.error(f"❌ Error agregando VIP: {e}")
            log_service.add_log('error', f'Error agregando VIP a {username}: {e}', 'twitch_api')
            return False
    
    async def unvip(self, username: str) -> bool:
        user_id = await self.get_user_id(username)
        if not user_id:
            raise ResourceNotFoundError(f"Usuario {username} no encontrado")
        
        token = settings.BROADCASTER_TOKEN
        if token.startswith("oauth:"):
            token = token[6:]
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }
        
        params = {
            "broadcaster_id": self.broadcaster_id,
            "user_id": user_id
        }
        
        url = f"{self.api.base_url}/channels/vips"
        
        try:
            response = requests.delete(url, headers=headers, params=params, timeout=10)
            if response.status_code == 204:
                logger.info(f"✅ {username} ya no es VIP")
                log_service.add_log('info', f'VIP removido de {username}', 'moderation')
                return True
            elif response.status_code == 401:
                logger.warning("Token expirado, refrescando...")
                log_service.add_log('warning', f'Token expirado al remover VIP de {username}', 'token_manager')
                from services.token_manager import token_manager
                token_manager.refresh_broadcaster_token()
                return await self.unvip(username)
            else:
                logger.error(f"❌ Error removiendo VIP: {response.status_code} - {response.text}")
                log_service.add_log('error', f'Error removiendo VIP de {username}: {response.status_code}', 'twitch_api')
                return False
        except Exception as e:
            logger.error(f"❌ Error removiendo VIP: {e}")
            log_service.add_log('error', f'Error removiendo VIP de {username}: {e}', 'twitch_api')
            return False