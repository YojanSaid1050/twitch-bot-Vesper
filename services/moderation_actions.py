"""
Servicio para acciones de moderación (timeout, ban, VIP, anuncios, shoutouts...)

Todas las llamadas pasan por TwitchAPI (reintento único tras refrescar el token)
y se ejecutan en un hilo aparte con asyncio.to_thread para no bloquear el
event loop del bot mientras Twitch responde.
"""

import asyncio
from typing import Optional, Dict, Any

from config import settings
from services.twitch_api import TwitchAPI
from services.log_service import log_service
from exceptions import TwitchAPIError, ResourceNotFoundError
from utils.logger import get_logger

logger = get_logger(__name__)

# Duración máxima de un timeout en Twitch (14 días)
MAX_TIMEOUT_SECONDS = 1209600

ANNOUNCEMENT_COLORS = ("primary", "blue", "green", "orange", "purple")


class ModerationActions:
    """
    Servicio para acciones de moderación
    """

    def __init__(self):
        # Token del bot (moderador) para moderación/chat
        self.api = TwitchAPI(use_broadcaster_token=False)
        # Token del streamer para acciones que solo puede hacer el dueño (VIP)
        self.broadcaster_api = TwitchAPI(use_broadcaster_token=True)

    # Se leen en cada llamada: settings puede recargar los IDs desde la base de datos
    @property
    def broadcaster_id(self) -> str:
        return settings.BROADCASTER_ID

    @property
    def moderator_id(self) -> str:
        return settings.MODERATOR_USER_ID or settings.BOT_ID

    def _mod_params(self, **extra) -> Dict[str, Any]:
        params = {"broadcaster_id": self.broadcaster_id, "moderator_id": self.moderator_id}
        params.update(extra)
        return params

    @staticmethod
    async def _call(func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    # ------------------------------------------------------------------
    # Usuarios
    # ------------------------------------------------------------------

    async def get_user(self, username: str) -> Optional[Dict]:
        """Devuelve el objeto de usuario de Helix (id, login, display_name...) o None."""
        username = (username or "").strip().lstrip("@").lower()
        if not username:
            return None
        try:
            result = await self._call(self.api.get, "users", params={"login": username})
            data = (result or {}).get("data", [])
            return data[0] if data else None
        except Exception as e:
            logger.error(f"Error obteniendo usuario {username}: {e}")
            log_service.add_log('error', f'Error obteniendo usuario {username}: {e}', 'twitch_api')
            return None

    async def get_user_id(self, username: str) -> Optional[str]:
        user = await self.get_user(username)
        return user["id"] if user else None

    async def _require_user_id(self, username: str, user_id: Optional[str] = None) -> str:
        if user_id:
            return str(user_id)
        found = await self.get_user_id(username)
        if not found:
            raise ResourceNotFoundError(f"Usuario {username} no encontrado")
        return found

    # ------------------------------------------------------------------
    # Mensajes y chat
    # ------------------------------------------------------------------

    async def delete_message(self, message_id: str) -> bool:
        try:
            await self._call(self.api.delete, "moderation/chat", params=self._mod_params(message_id=message_id))
            logger.info(f"✅ Mensaje {message_id} eliminado correctamente")
            log_service.add_log('info', f'Mensaje {message_id} eliminado', 'moderation')
            return True
        except TwitchAPIError as e:
            logger.error(f"❌ Error eliminando mensaje {message_id}: {e}")
            log_service.add_log('error', f'Error eliminando mensaje {message_id}: {e}', 'twitch_api')
            return False

    async def clear_chat(self) -> bool:
        """Borra todo el chat (DELETE /moderation/chat sin message_id)."""
        await self._call(self.api.delete, "moderation/chat", params=self._mod_params())
        logger.info("✅ Chat limpiado")
        log_service.add_log('info', 'Chat limpiado', 'moderation')
        return True

    async def announce(self, message: str, color: str = "primary") -> bool:
        """Envía un anuncio destacado (requiere moderator:manage:announcements)."""
        color = color if color in ANNOUNCEMENT_COLORS else "primary"
        await self._call(
            self.api.post,
            "chat/announcements",
            params=self._mod_params(),
            json={"message": message[:500], "color": color},
        )
        log_service.add_log('info', f'Anuncio enviado: "{message[:80]}"', 'moderation')
        return True

    async def shoutout(self, to_user_id: str) -> bool:
        """Shoutout oficial de Twitch (requiere moderator:manage:shoutouts)."""
        await self._call(
            self.api.post,
            "chat/shoutouts",
            params={
                "from_broadcaster_id": self.broadcaster_id,
                "to_broadcaster_id": to_user_id,
                "moderator_id": self.moderator_id,
            },
        )
        return True

    # ------------------------------------------------------------------
    # Timeouts y baneos
    # ------------------------------------------------------------------

    async def _ban_request(self, user_id: str, reason: str, duration: Optional[int]) -> None:
        data: Dict[str, Any] = {"user_id": user_id}
        if duration:
            data["duration"] = max(1, min(int(duration), MAX_TIMEOUT_SECONDS))
        if reason:
            data["reason"] = reason[:500]
        await self._call(self.api.post, "moderation/bans", params=self._mod_params(), json={"data": data})

    async def timeout(self, username: str, duration_seconds: int, reason: str = "", user_id: Optional[str] = None) -> bool:
        target_id = await self._require_user_id(username, user_id)
        logger.info(f"⏰ Timeout a {username} (ID: {target_id}) por {duration_seconds}s")
        await self._ban_request(target_id, reason, duration_seconds)
        log_service.add_log('info', f'Timeout aplicado a {username} por {duration_seconds}s. Razón: {reason}', 'moderation')
        return True

    async def ban(self, username: str, reason: str = "", duration: Optional[int] = None, user_id: Optional[str] = None) -> bool:
        """
        Banea a un usuario. Sin `duration` el baneo es PERMANENTE (antes era
        un timeout de 14 días). Las sanciones automáticas pueden pasar una
        duración para mantener el comportamiento temporal.
        """
        target_id = await self._require_user_id(username, user_id)
        await self._ban_request(target_id, reason, duration)
        tipo = f"temporal ({duration}s)" if duration else "permanente"
        log_service.add_log('warning', f'Ban {tipo} aplicado a {username}. Razón: {reason}', 'moderation')
        return True

    async def unban(self, username: str, user_id: Optional[str] = None) -> bool:
        target_id = await self._require_user_id(username, user_id)
        await self._call(self.api.delete, "moderation/bans", params=self._mod_params(user_id=target_id))
        logger.info(f"✅ {username} desbaneado")
        log_service.add_log('info', f'Unban aplicado a {username}', 'moderation')
        return True

    # ------------------------------------------------------------------
    # VIP (solo el streamer puede gestionarlos)
    # ------------------------------------------------------------------

    async def vip(self, username: str) -> bool:
        target_id = await self._require_user_id(username)
        await self._call(
            self.broadcaster_api.post,
            "channels/vips",
            params={"broadcaster_id": self.broadcaster_id, "user_id": target_id},
        )
        logger.info(f"✅ {username} es VIP ahora")
        log_service.add_log('info', f'VIP añadido a {username}', 'moderation')
        return True

    async def unvip(self, username: str) -> bool:
        target_id = await self._require_user_id(username)
        await self._call(
            self.broadcaster_api.delete,
            "channels/vips",
            params={"broadcaster_id": self.broadcaster_id, "user_id": target_id},
        )
        logger.info(f"✅ {username} ya no es VIP")
        log_service.add_log('info', f'VIP removido de {username}', 'moderation')
        return True

    # ------------------------------------------------------------------
    # Seguidores
    # ------------------------------------------------------------------

    async def get_follow_date(self, user_id: str) -> Optional[str]:
        """
        Fecha ISO en que `user_id` empezó a seguir el canal, o None si no lo sigue.
        Requiere moderator:read:followers en el token del bot.
        """
        result = await self._call(
            self.api.get,
            "channels/followers",
            params={"broadcaster_id": self.broadcaster_id, "user_id": user_id},
        )
        data = (result or {}).get("data", [])
        return data[0].get("followed_at") if data else None
