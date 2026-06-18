"""
Servicio de notificaciones para eventos de Twitch
"""

import asyncio
import requests
from typing import Optional, Set, Dict
from datetime import datetime

from config import settings
from utils.logger import get_logger
from services.log_service import log_service

logger = get_logger(__name__)


class NotificationService:
    """Servicio para manejar notificaciones de eventos"""
    
    def __init__(self):
        self.bot = None
        self.channel = None
        self.known_followers: Dict[str, str] = {}
        self._polling_task = None
        self._polling_active = False
    
    def set_bot(self, bot):
        self.bot = bot
        if bot.connected_channels:
            self.channel = bot.connected_channels[0]
            logger.info(f"📺 Canal establecido: {self.channel.name}")
            log_service.add_log('info', f'Canal establecido: {self.channel.name}', 'notification_service')
    
    async def _get_channel(self):
        if self.channel:
            return self.channel
        if self.bot and self.bot.connected_channels:
            self.channel = self.bot.connected_channels[0]
            logger.info(f"📺 Canal obtenido: {self.channel.name}")
            return self.channel
        return None
    
    def start_follow_polling(self):
        if self._polling_active:
            return
        self._polling_active = True
        
        async def poll_follows():
            await asyncio.sleep(5)
            await self._get_channel()
            await self._load_initial_followers()
            while self._polling_active:
                try:
                    await self._check_new_follows()
                    await asyncio.sleep(30)
                except Exception as e:
                    logger.error(f"Error en polling de follows: {e}")
                    log_service.add_log('error', f'Error en polling de follows: {e}', 'notification_service')
                    await asyncio.sleep(60)
        
        self._polling_task = asyncio.create_task(poll_follows())
        logger.info("✅ Polling de follows iniciado (cada 30 segundos)")
        log_service.add_log('info', 'Polling de follows iniciado', 'notification_service')
    
    async def _load_initial_followers(self):
        try:
            token = settings.BROADCASTER_TOKEN
            if token.startswith("oauth:"):
                token = token[6:]
            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": settings.CLIENT_ID
            }
            params = {
                "broadcaster_id": settings.BROADCASTER_ID,
                "first": 100
            }
            response = requests.get(
                "https://api.twitch.tv/helix/channels/followers",
                headers=headers,
                params=params
            )
            if response.status_code == 200:
                data = response.json()
                self.known_followers = {}
                for follower in data.get("data", []):
                    user_id = follower.get("user_id")
                    user_name = follower.get("user_name")
                    if user_id and user_name:
                        self.known_followers[user_id] = user_name
                logger.info(f"📊 Cargados {len(self.known_followers)} seguidores iniciales")
                log_service.add_log('info', f'Cargados {len(self.known_followers)} seguidores iniciales', 'notification_service')
                if self.known_followers:
                    logger.info(f"   Primeros seguidores: {list(self.known_followers.values())[:5]}")
            elif response.status_code == 401:
                logger.error("❌ Token expirado o sin permisos para cargar seguidores")
                log_service.add_log('error', 'Token expirado o sin permisos para cargar seguidores', 'notification_service')
            else:
                logger.warning(f"⚠️ Error cargando seguidores: {response.status_code}")
                log_service.add_log('warning', f'Error cargando seguidores: {response.status_code}', 'notification_service')
        except Exception as e:
            logger.error(f"Error cargando seguidores iniciales: {e}")
            log_service.add_log('error', f'Error cargando seguidores iniciales: {e}', 'notification_service')
    
    async def _check_new_follows(self):
        channel = await self._get_channel()
        if not channel:
            logger.debug("Canal no disponible aún, reintentando más tarde...")
            return
        try:
            token = settings.BROADCASTER_TOKEN
            if token.startswith("oauth:"):
                token = token[6:]
            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": settings.CLIENT_ID
            }
            params = {
                "broadcaster_id": settings.BROADCASTER_ID,
                "first": 100
            }
            response = requests.get(
                "https://api.twitch.tv/helix/channels/followers",
                headers=headers,
                params=params
            )
            if response.status_code == 200:
                data = response.json()
                current_followers: Dict[str, str] = {}
                for follower in data.get("data", []):
                    user_id = follower.get("user_id")
                    user_name = follower.get("user_name")
                    if user_id and user_name:
                        current_followers[user_id] = user_name
                if self.known_followers:
                    new_followers = []
                    for user_id, user_name in current_followers.items():
                        if user_id not in self.known_followers:
                            new_followers.append((user_id, user_name))
                    if new_followers:
                        logger.info(f"🎉 Detectados {len(new_followers)} nuevos seguidores!")
                        log_service.add_log('info', f'Detectados {len(new_followers)} nuevos seguidores', 'notification_service')
                        for user_id, user_name in new_followers:
                            logger.info(f"   - Nuevo: {user_name} (ID: {user_id})")
                            await self._send_follow_notification(user_name, channel)
                        self.known_followers = current_followers
                    else:
                        logger.debug(f"🔍 No hay nuevos seguidores. Total: {len(current_followers)}")
                else:
                    self.known_followers = current_followers
                    logger.info(f"📊 Lista de seguidores actualizada: {len(self.known_followers)}")
            elif response.status_code == 401:
                logger.error("❌ Token expirado o sin permisos para verificar follows")
                log_service.add_log('error', 'Token expirado o sin permisos para verificar follows', 'notification_service')
            else:
                logger.warning(f"⚠️ Error en API: {response.status_code}")
                log_service.add_log('warning', f'Error en API al verificar follows: {response.status_code}', 'notification_service')
        except Exception as e:
            logger.error(f"Error verificando follows: {e}")
            log_service.add_log('error', f'Error verificando follows: {e}', 'notification_service')
    
    async def _send_follow_notification(self, user_name: str, channel):
        try:
            message = f"🕯️ Una nueva alma se une al ritual... ¡Bienvenido, {user_name}! Que la oscuridad te guíe."
            await channel.send(message)
            logger.info(f"📢 Notificación de follow enviada: {user_name}")
            log_service.add_log('info', f'Notificación de follow enviada para {user_name}', 'notification_service')
        except Exception as e:
            logger.error(f"Error enviando notificación: {e}")
            log_service.add_log('error', f'Error enviando notificación de follow: {e}', 'notification_service')
    
    def stop_polling(self):
        self._polling_active = False
        if self._polling_task:
            self._polling_task.cancel()
        logger.info("🛑 Polling de follows detenido")
        log_service.add_log('info', 'Polling de follows detenido', 'notification_service')


# Instancia global
notification_service = NotificationService()