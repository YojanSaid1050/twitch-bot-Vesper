"""
Servicio para manejar EventSub de Twitch
"""

import asyncio
import requests
import threading
from flask import Flask, request, jsonify
from typing import Optional, Dict

from config import settings
from services.notification_service import notification_service
from utils.logger import get_logger

logger = get_logger(__name__)


class EventSubService:
    """Servicio para recibir eventos via webhook local"""
    
    def __init__(self):
        self.bot = None
        self.channel = None
        self.webhook_port = settings.BOT_WEBHOOK_PORT
        self.app = None
        self.server_thread = None
        self.is_running = False
        
    def set_bot(self, bot):
        """Establecer referencia al bot"""
        self.bot = bot
        if bot.connected_channels:
            self.channel = bot.connected_channels[0]
        notification_service.set_bot(bot)
    
    def start_webhook_server(self):
        """Iniciar servidor webhook local"""
        if self.is_running:
            return
        
        self.app = Flask(__name__)
        
        @self.app.route('/webhook', methods=['POST'])
        def handle_webhook():
            """Recibir eventos del servidor público"""
            data = request.json
            event_type = data.get('type')
            event_data = data.get('data', {})
            
            logger.info(f"📨 Evento recibido: {event_type}")
            
            # Procesar evento
            if self.bot and self.channel:
                self._process_event(event_type, event_data)
            
            return jsonify({"status": "ok"}), 200
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({"status": "alive"}), 200
        
        def run_server():
            try:
                self.app.run(host='0.0.0.0', port=self.webhook_port, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                logger.error(f"Error en servidor webhook: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.is_running = True
        logger.info(f"✅ Servidor webhook local iniciado en puerto {self.webhook_port}")
    
    def _process_event(self, event_type: str, event_data: Dict):
        """Procesar evento y enviar notificación al chat"""
        
        async def send_notification():
            try:
                if not self.channel:
                    return
                
                if event_type == "channel.subscribe":
                    user_name = event_data.get("user_name", event_data.get("user_login", "Alguien"))
                    tier = event_data.get("tier", "1000")
                    is_gift = event_data.get("is_gift", False)
                    
                    if not is_gift:
                        await notification_service.on_subscribe(self.channel, user_name, tier, "sub")
                
                elif event_type == "channel.subscription.gift":
                    user_name = event_data.get("user_name", event_data.get("user_login", "Alguien"))
                    total = event_data.get("total", 1)
                    tier = event_data.get("tier", "1000")
                    
                    message = f"🎁 {user_name} ha regalado {total} suscripción(es) Tier {tier}! ¡Qué generosidad ilumina el altar! 🕯️"
                    await self.channel.send(message)
                
                elif event_type == "channel.raid":
                    from_broadcaster = event_data.get("from_broadcaster_user_name", "Alguien")
                    viewers = event_data.get("viewers", 0)
                    await notification_service.on_raid(self.channel, from_broadcaster, viewers)
                
                elif event_type == "channel.cheer":
                    user_name = event_data.get("user_name", "Alguien")
                    bits = event_data.get("bits", 0)
                    message = f"💎 {user_name} ha lanzado {bits} bits al altar! 🔥"
                    await self.channel.send(message)
                    
            except Exception as e:
                logger.error(f"Error enviando notificación: {e}")
        
        if self.bot and self.bot.loop:
            asyncio.run_coroutine_threadsafe(send_notification(), self.bot.loop)
    
    def subscribe_to_events(self):
        """Suscribirse a eventos via API de Twitch (solo los que funcionan)"""
        app_token = getattr(settings, 'APP_ACCESS_TOKEN', '')
        
        if not app_token:
            logger.error("❌ No hay APP_ACCESS_TOKEN configurado")
            return
        
        callback_url = settings.EVENTSUB_CALLBACK_URL
        
        if not callback_url:
            logger.error("❌ EVENTSUB_CALLBACK_URL no configurado")
            return
        
        headers = {
            "Authorization": f"Bearer {app_token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }
        
        # Solo eventos que funcionan con App Token
        events = [
            ("channel.subscribe", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.subscription.gift", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.raid", "1", {"to_broadcaster_user_id": settings.BROADCASTER_ID})
        ]
        
        logger.info(f"📡 Suscribiendo a eventos via {callback_url}")
        
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
                elif response.status_code == 409:
                    logger.info(f"ℹ️ Ya suscrito a {event_type}")
                else:
                    logger.error(f"❌ Error en {event_type}: {response.status_code}")
            except Exception as e:
                logger.error(f"Error en {event_type}: {e}")
        
        # Iniciar polling para follows
        if self.bot and self.bot.loop:
            asyncio.run_coroutine_threadsafe(
                self._start_follow_polling(), 
                self.bot.loop
            )
    
    async def _start_follow_polling(self):
        """Iniciar polling de follows"""
        notification_service.start_follow_polling()
    
    def stop(self):
        """Detener servidor webhook"""
        self.is_running = False
        logger.info("🛑 Servidor webhook detenido")


# Instancia global
eventsub_service = EventSubService()