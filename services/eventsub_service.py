"""
Servicio para manejar EventSub de Twitch
"""

import asyncio
import json
import hmac
import hashlib
import requests
import threading
from flask import Flask, request, jsonify
from typing import Optional, Dict

from config import settings
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
                    logger.warning("No hay canal disponible para enviar notificación")
                    return
                
                if event_type == "channel.follow":
                    user_name = event_data.get("user_name", event_data.get("user_login", "Alguien"))
                    message = f"🕯️ Una nueva alma se une al ritual... ¡Bienvenido {user_name}! Que la oscuridad te guíe. 🖤"
                    await self.channel.send(message)
                    logger.info(f"📢 Notificación de follow enviada: {user_name}")
                
                elif event_type == "channel.subscribe":
                    user_name = event_data.get("user_name", event_data.get("user_login", "Alguien"))
                    tier = event_data.get("tier", "1000")
                    is_gift = event_data.get("is_gift", False)
                    
                    tier_names = {
                        "1000": "Tier 1",
                        "2000": "Tier 2", 
                        "3000": "Tier 3"
                    }
                    tier_name = tier_names.get(tier, "desconocido")
                    
                    if is_gift:
                        message = f"🎁 {user_name} ha recibido una suscripción Tier {tier_name} como regalo! ¡Bienvenido a la cofradía! 🕯️"
                    else:
                        message = f"🎉 {user_name} se ha suscrito con {tier_name}! ¡Bienvenido a la cofradía del ritual! 🕯️"
                    
                    await self.channel.send(message)
                    logger.info(f"📢 Notificación de sub enviada: {user_name} - {tier_name}")
                
                elif event_type == "channel.subscription.gift":
                    user_name = event_data.get("user_name", event_data.get("user_login", "Alguien"))
                    total = event_data.get("total", 1)
                    tier = event_data.get("tier", "1000")
                    
                    message = f"🎁 {user_name} ha regalado {total} suscripción(es) Tier {tier}! ¡Qué generosidad ilumina el altar! 🕯️"
                    await self.channel.send(message)
                    logger.info(f"📢 Notificación de gift sub enviada: {user_name} - {total} subs")
                
                elif event_type == "channel.subscription.message":
                    user_name = event_data.get("user_name", event_data.get("user_login", "Alguien"))
                    message_text = event_data.get("message", {}).get("text", "")
                    
                    if message_text:
                        message = f"💬 {user_name} compartió un mensaje en su suscripción: '{message_text[:100]}' 🕯️"
                        await self.channel.send(message)
                        logger.info(f"📢 Notificación de mensaje de sub enviada: {user_name}")
                
                elif event_type == "channel.raid":
                    from_broadcaster = event_data.get("from_broadcaster_user_name", event_data.get("from_name", "Alguien"))
                    viewers = event_data.get("viewers", 0)
                    
                    message = f"⚔️ ¡UNA HORDA LLEGA! {from_broadcaster} nos invade con {viewers} almas. ¡Preparaos para el caos ritual! 🐉"
                    await self.channel.send(message)
                    logger.info(f"📢 Notificación de raid enviada: {from_broadcaster} - {viewers} viewers")
                
                elif event_type == "channel.cheer":
                    user_name = event_data.get("user_name", event_data.get("user_login", "Alguien"))
                    bits = event_data.get("bits", 0)
                    message_text = event_data.get("message", "")
                    
                    message = f"💎 {user_name} ha lanzado {bits} bits al altar! ¡La llama se aviva con tu generosidad! 🔥"
                    if message_text:
                        message += f" Mensaje: '{message_text[:50]}'"
                    
                    await self.channel.send(message)
                    logger.info(f"📢 Notificación de cheers enviada: {user_name} - {bits} bits")
                
                else:
                    logger.debug(f"Evento no manejado: {event_type}")
                    
            except Exception as e:
                logger.error(f"Error enviando notificación: {e}")
        
        # Ejecutar async en el loop del bot
        if self.bot and self.bot.loop:
            asyncio.run_coroutine_threadsafe(send_notification(), self.bot.loop)
        else:
            logger.warning("No se pudo enviar notificación: bot loop no disponible")
    
    def subscribe_to_events(self):
        """Suscribirse a eventos via API de Twitch"""
        if not settings.BROADCASTER_TOKEN:
            logger.error("No hay token para suscribirse a eventos")
            return
        
        # URL pública de Render (configurar en .env)
        callback_url = settings.EVENTSUB_CALLBACK_URL
        
        if not callback_url:
            logger.error("EVENTSUB_CALLBACK_URL no configurado")
            return
        
        # Lista de eventos a suscribir
        events = [
            ("channel.follow", 1),
            ("channel.subscribe", 1),
            ("channel.subscription.gift", 1),
            ("channel.subscription.message", 1),
            ("channel.raid", 1),
            ("channel.cheer", 1)
        ]
        
        headers = {
            "Authorization": f"Bearer {settings.BROADCASTER_TOKEN}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }
        
        logger.info(f"📡 Suscribiendo a eventos via {callback_url}")
        
        for event_type, version in events:
            subscription = {
                "type": event_type,
                "version": str(version),
                "condition": {
                    "broadcaster_user_id": settings.BROADCASTER_ID
                },
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
                    logger.info(f"✅ Suscrito a {event_type}")
                elif response.status_code == 409:
                    logger.info(f"ℹ️ Ya suscrito a {event_type}")
                else:
                    logger.error(f"❌ Error suscribiendo a {event_type}: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Error en suscripción {event_type}: {e}")
    
    def stop(self):
        """Detener servidor webhook"""
        self.is_running = False
        logger.info("🛑 Servidor webhook detenido")


# Instancia global
eventsub_service = EventSubService()