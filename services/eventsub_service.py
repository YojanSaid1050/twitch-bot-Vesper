"""
Servicio para manejar EventSub de Twitch
"""

import asyncio
import requests
from typing import Optional, Dict

from config import settings
from services.notification_service import notification_service
from utils.logger import get_logger
from services.log_service import log_service

logger = get_logger(__name__)

class EventSubService:
    """Servicio para recibir eventos via webhook (ahora gestionado por el dashboard)"""
    
    def __init__(self):
        self.bot = None
        self.channel = None
        
    def set_bot(self, bot):
        """Establecer referencia al bot"""
        self.bot = bot
        if bot.connected_channels:
            self.channel = bot.connected_channels[0]
        notification_service.set_bot(bot)
        log_service.add_log('info', 'EventSub service vinculado al bot', 'bot')
    
    def _process_event(self, event_type: str, event_data: Dict):
        """Procesar evento y enviar notificación al chat (estilo místico)"""
        async def send_notification():
            try:
                if not self.channel:
                    return
                
                if event_type == "channel.subscribe":
                    user_name = event_data.get("user_name", event_data.get("user_login", "Alguien"))
                    tier = event_data.get("tier", "1000")
                    is_gift = event_data.get("is_gift", False)
                    if not is_gift:
                        log_service.add_log('info', f'Nueva suscripción de {user_name} (Tier {tier})', 'stats')
                        await notification_service.on_subscribe(self.channel, user_name, tier, "sub")
                
                elif event_type == "channel.subscription.gift":
                    user_name = event_data.get("user_name", event_data.get("user_login", "Alguien"))
                    total = event_data.get("total", 1)
                    tier = event_data.get("tier", "1000")
                    message = f"🎁 {user_name} ha ofrendado {total} suscripción(es) Tier {tier}! El altar se ilumina con su generosidad. 🕯️"
                    await self.channel.send(message)
                    log_service.add_log('info', f'Gift subs: {user_name} regaló {total} suscripciones Tier {tier}', 'stats')
                
                elif event_type == "channel.raid":
                    from_broadcaster = event_data.get("from_broadcaster_user_name", "Alguien")
                    viewers = event_data.get("viewers", 0)
                    log_service.add_log('info', f'Raid entrante de {from_broadcaster} con {viewers} espectadores', 'stats')
                    await notification_service.on_raid(self.channel, from_broadcaster, viewers)
                
                elif event_type == "channel.cheer":
                    user_name = event_data.get("user_name", "Alguien")
                    bits = event_data.get("bits", 0)
                    message = f"💎 {user_name} ha derramado {bits} bits sobre el altar! El poder fluye. 🔥"
                    await self.channel.send(message)
                    log_service.add_log('info', f'Cheer: {user_name} envió {bits} bits', 'stats')
                    
            except Exception as e:
                logger.error(f"Error enviando notificación: {e}")
                log_service.add_log('error', f'Error enviando notificación: {e}', 'bot')
        
        if self.bot and self.bot.loop:
            asyncio.run_coroutine_threadsafe(send_notification(), self.bot.loop)
    
    def subscribe_to_events(self):
        """Suscribirse a eventos via API de Twitch (solo los que funcionan)"""
        app_token = getattr(settings, 'APP_ACCESS_TOKEN', '')
        if not app_token:
            logger.error("❌ No hay APP_ACCESS_TOKEN configurado")
            log_service.add_log('error', 'No hay APP_ACCESS_TOKEN configurado para EventSub', 'bot')
            return
        
        callback_url = settings.EVENTSUB_CALLBACK_URL
        if not callback_url:
            logger.error("❌ EVENTSUB_CALLBACK_URL no configurado")
            log_service.add_log('error', 'EVENTSUB_CALLBACK_URL no configurado', 'bot')
            return
        
        headers = {
            "Authorization": f"Bearer {app_token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }
        
        events = [
            ("channel.subscribe", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.subscription.gift", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.raid", "1", {"to_broadcaster_user_id": settings.BROADCASTER_ID})
        ]
        
        logger.info(f"📡 Suscribiendo a eventos via {callback_url}")
        log_service.add_log('info', f'Suscribiendo a eventos via {callback_url}', 'bot')
        
        for event_type, version, condition in events:
            subscription = {
                "type": event_type,
                "version": version,
                "condition": condition,
                "transport": {
                    "method": "webhook",
                    "callback": f"{callback_url}/webhook/twitch",
                    "secret": settings.TWITCH_WEBHOOK_SECRET
                }
            }
            
            try:
                response = requests.post(
                    "https://api.twitch.tv/helix/eventsub/subscriptions",
                    headers=headers,
                    json=subscription
                )
                if response.status_code == 202:
                    logger.info(f"✅ Suscrito a {event_type} (v{version})")
                    log_service.add_log('info', f'Suscrito a {event_type}', 'bot')
                elif response.status_code == 409:
                    logger.info(f"ℹ️ Ya suscrito a {event_type}")
                else:
                    logger.error(f"❌ Error en {event_type}: {response.status_code}")
                    log_service.add_log('error', f'Error suscribiendo a {event_type}: {response.status_code}', 'bot')
            except Exception as e:
                logger.error(f"Error en {event_type}: {e}")
                log_service.add_log('error', f'Error en {event_type}: {e}', 'bot')
        
        # Iniciar polling para follows
        if self.bot and self.bot.loop:
            asyncio.run_coroutine_threadsafe(
                self._start_follow_polling(), 
                self.bot.loop
            )
    
    async def _start_follow_polling(self):
        notification_service.start_follow_polling()
    
    def stop(self):
        """Detener (ya no hay servidor webhook)"""
        logger.info("🛑 EventSub detenido")
        log_service.add_log('info', 'EventSub detenido', 'bot')


# Instancia global
eventsub_service = EventSubService()