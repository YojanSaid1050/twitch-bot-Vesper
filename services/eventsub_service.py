"""
Servicio para manejar EventSub de Twitch
Suscripciones a todos los eventos relevantes usando App Access Token (según documentación oficial)
"""

import asyncio
import requests
from typing import Optional, Dict

from config import settings
from services.notification_service import notification_service
from services.log_service import log_service
from utils.logger import get_logger

logger = get_logger(__name__)


class EventSubService:
    def __init__(self):
        self.bot = None
        self.channel = None

    def set_bot(self, bot):
        self.bot = bot
        if bot.connected_channels:
            self.channel = bot.connected_channels[0]
        notification_service.set_bot(bot)
        log_service.add_log('info', 'EventSub service vinculado al bot', 'bot')

    def _process_event(self, event_type: str, event_data: Dict):
        """
        Procesa eventos entrantes y los registra en los logs.
        Los eventos se clasifican por fuente: 'moderation', 'stats' o 'system'.
        """
        async def send_notification():
            try:
                if not self.channel:
                    return

                # ========== EVENTOS DE MODERACIÓN ==========
                if event_type == "channel.ban":
                    user = event_data.get("user_name", "Desconocido")
                    moderator = event_data.get("moderator_user_name", "Staff")
                    reason = event_data.get("reason", "Sin especificar")
                    log_service.add_log('info', f'🔨 Ban aplicado a {user} por {moderator} - Razón: "{reason}"', 'moderation')

                elif event_type == "channel.unban":
                    user = event_data.get("user_name", "Desconocido")
                    moderator = event_data.get("moderator_user_name", "Staff")
                    log_service.add_log('info', f'🔓 Unban aplicado a {user} por {moderator}', 'moderation')

                elif event_type == "channel.timeout":
                    user = event_data.get("user_name", "Desconocido")
                    moderator = event_data.get("moderator_user_name", "Staff")
                    duration = event_data.get("duration_seconds", 0)
                    reason = event_data.get("reason", "Sin especificar")
                    log_service.add_log('info', f'⏰ Timeout a {user} por {duration}s (razón: "{reason}") por {moderator}', 'moderation')

                elif event_type == "channel.untimeout":
                    user = event_data.get("user_name", "Desconocido")
                    moderator = event_data.get("moderator_user_name", "Staff")
                    log_service.add_log('info', f'⏳ Timeout removido a {user} por {moderator}', 'moderation')

                # ========== EVENTOS DE SEGUIDORES ==========
                elif event_type == "channel.follow":
                    user = event_data.get("user_name", "Desconocido")
                    log_service.add_log('info', f'⭐ Nuevo seguidor: {user}', 'stats')
                    # Opcional: notificación en chat
                    # await self.channel.send(f"🕯️ Una nueva alma se une al ritual... ¡Bienvenido, {user}!")

                # ========== EVENTOS DE SUSCRIPCIONES ==========
                elif event_type == "channel.subscribe":
                    user = event_data.get("user_name", "Desconocido")
                    tier = event_data.get("tier", "1000")
                    is_gift = event_data.get("is_gift", False)
                    if not is_gift:
                        log_service.add_log('info', f'🎉 Nueva suscripción de {user} (Tier {tier})', 'stats')
                        # Notificar al sistema de notificaciones
                        await notification_service.on_subscribe(self.channel, user, tier, "sub")
                    else:
                        log_service.add_log('info', f'🎁 Suscripción regalada a {user} (Tier {tier})', 'stats')

                elif event_type == "channel.subscription.gift":
                    user = event_data.get("user_name", "Alguien")  # quien regala
                    total = event_data.get("total", 1)
                    tier = event_data.get("tier", "1000")
                    log_service.add_log('info', f'🎁 {user} regaló {total} suscripción(es) Tier {tier}', 'stats')
                    # Notificación en chat (opcional)
                    # await self.channel.send(f"🎁 {user} ha ofrendado {total} suscripción(es) Tier {tier}! El altar se ilumina.")

                elif event_type == "channel.subscription.message":
                    user = event_data.get("user_name", "Desconocido")
                    tier = event_data.get("tier", "1000")
                    message = event_data.get("message", {}).get("text", "")
                    log_service.add_log('info', f'💬 Re-suscripción de {user} (Tier {tier}) con mensaje: "{message[:50]}"', 'stats')
                    # También se puede notificar en chat

                # ========== EVENTOS DE RAIDS ==========
                elif event_type == "channel.raid":
                    from_broadcaster = event_data.get("from_broadcaster_user_name", "Alguien")
                    viewers = event_data.get("viewers", 0)
                    log_service.add_log('info', f'⚔️ Raid entrante de {from_broadcaster} con {viewers} espectadores', 'stats')
                    await notification_service.on_raid(self.channel, from_broadcaster, viewers)

                # ========== EVENTOS DE CHEERS ==========
                elif event_type == "channel.cheer":
                    user = event_data.get("user_name", "Alguien")
                    bits = event_data.get("bits", 0)
                    message = event_data.get("message", "")
                    log_service.add_log('info', f'💎 {user} envió {bits} bits - Mensaje: "{message[:30]}"', 'stats')
                    # Notificación en chat (opcional)
                    # await self.channel.send(f"💎 {user} ha derramado {bits} bits sobre el altar!")

                # ========== EVENTOS DE STREAM (online/offline) ==========
                elif event_type == "stream.online":
                    streamer = event_data.get("broadcaster_user_name", "Desconocido")
                    game = event_data.get("game_name", "No especificado")
                    title = event_data.get("title", "Sin título")
                    log_service.add_log('info', f'📡 Stream EN VIVO: {streamer} está jugando {game} - "{title}"', 'system')
                    # Notificación en chat (opcional)
                    # await self.channel.send(f"📡 El ritual ha comenzado! {streamer} está jugando {game}.")

                elif event_type == "stream.offline":
                    streamer = event_data.get("broadcaster_user_name", "Desconocido")
                    log_service.add_log('info', f'🌙 Stream OFFLINE: {streamer} se ha desconectado', 'system')

                # ========== EVENTOS DE PREDICCIONES ==========
                elif event_type == "channel.prediction.begin":
                    title = event_data.get("title", "Sin título")
                    outcomes = event_data.get("outcomes", [])
                    log_service.add_log('info', f'🔮 Predicción iniciada: "{title}" - Opciones: {len(outcomes)}', 'stats')

                elif event_type == "channel.prediction.end":
                    title = event_data.get("title", "Sin título")
                    status = event_data.get("status", "desconocido")
                    log_service.add_log('info', f'🔮 Predicción finalizada: "{title}" - Estado: {status}', 'stats')

                # ========== EVENTOS DE ENCUESTAS ==========
                elif event_type == "channel.poll.begin":
                    title = event_data.get("title", "Sin título")
                    choices = len(event_data.get("choices", []))
                    log_service.add_log('info', f'📊 Encuesta iniciada: "{title}" - {choices} opciones', 'stats')

                elif event_type == "channel.poll.end":
                    title = event_data.get("title", "Sin título")
                    status = event_data.get("status", "desconocido")
                    log_service.add_log('info', f'📊 Encuesta finalizada: "{title}" - Estado: {status}', 'stats')

                # ========== EVENTOS DE HYPE TRAIN ==========
                elif event_type == "channel.hype_train.begin":
                    level = event_data.get("level", 0)
                    total = event_data.get("total", 0)
                    log_service.add_log('info', f'🚂 Hype Train comenzó! Nivel {level} - Total: {total}', 'stats')

                elif event_type == "channel.hype_train.end":
                    level = event_data.get("level", 0)
                    total = event_data.get("total", 0)
                    log_service.add_log('info', f'🚂 Hype Train finalizado! Nivel alcanzado {level} - Total: {total}', 'stats')

                # ========== EVENTOS DE REDENCIÓN DE PUNTOS DE CANAL ==========
                elif event_type == "channel.channel_points_custom_reward_redemption.add":
                    user = event_data.get("user_name", "Desconocido")
                    reward_title = event_data.get("reward", {}).get("title", "Recompensa")
                    log_service.add_log('info', f'🎯 {user} redimió puntos: {reward_title}', 'stats')

                # ========== EVENTOS DE SUSCRIPCIÓN A EVENTOS (confirmación) ==========
                # No se procesan, son internos

            except Exception as e:
                logger.error(f"Error procesando evento {event_type}: {e}")
                log_service.add_log('error', f'Error procesando evento {event_type}: {e}', 'bot')

        if self.bot and self.bot.loop:
            asyncio.run_coroutine_threadsafe(send_notification(), self.bot.loop)

    def subscribe_to_events(self):
        """
        Suscribirse a todos los eventos relevantes usando App Access Token.
        Según documentación oficial de Twitch, las suscripciones por webhook
        requieren App Access Token (no User Access Token).
        """
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

        # Lista completa de eventos a suscribir
        events = [
            # Moderación (requieren scopes en el token del usuario, pero la suscripción es con App Token)
            ("channel.ban", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.unban", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.timeout", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.untimeout", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),

            # Seguidores (requiere moderator_user_id para v2)
            ("channel.follow", "2", {
                "broadcaster_user_id": settings.BROADCASTER_ID,
                "moderator_user_id": settings.BOT_ID  # El bot es moderador
            }),

            # Suscripciones
            ("channel.subscribe", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.subscription.gift", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.subscription.message", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),

            # Raids
            ("channel.raid", "1", {"to_broadcaster_user_id": settings.BROADCASTER_ID}),

            # Cheers
            ("channel.cheer", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),

            # Stream online/offline
            ("stream.online", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("stream.offline", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),

            # Predicciones
            ("channel.prediction.begin", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.prediction.end", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),

            # Encuestas
            ("channel.poll.begin", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.poll.end", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),

            # Hype Train
            ("channel.hype_train.begin", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
            ("channel.hype_train.end", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),

            # Redenciones de puntos de canal
            ("channel.channel_points_custom_reward_redemption.add", "1", {"broadcaster_user_id": settings.BROADCASTER_ID}),
        ]

        logger.info(f"📡 Suscribiendo a {len(events)} eventos via {callback_url}")
        log_service.add_log('info', f'Suscribiendo a {len(events)} eventos via {callback_url}', 'bot')

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
                    json=subscription,
                    timeout=10
                )
                if response.status_code == 202:
                    logger.info(f"✅ Suscrito a {event_type} (v{version})")
                    log_service.add_log('info', f'Suscrito a {event_type}', 'bot')
                elif response.status_code == 409:
                    logger.info(f"ℹ️ Ya suscrito a {event_type}")
                else:
                    logger.error(f"❌ Error en {event_type}: {response.status_code} - {response.text}")
                    log_service.add_log('error', f'Error suscribiendo a {event_type}: {response.status_code}', 'bot')
            except Exception as e:
                logger.error(f"Error en {event_type}: {e}")
                log_service.add_log('error', f'Error en {event_type}: {e}', 'bot')

        # Iniciar polling de follows como respaldo (por si EventSub falla)
        if self.bot and self.bot.loop:
            asyncio.run_coroutine_threadsafe(
                self._start_follow_polling(),
                self.bot.loop
            )

    async def _start_follow_polling(self):
        """Inicia el polling de follows como respaldo."""
        notification_service.start_follow_polling()

    def stop(self):
        """Detiene el servicio (no hay servidor webhook que detener)."""
        logger.info("🛑 EventSub detenido")
        log_service.add_log('info', 'EventSub detenido', 'bot')

eventsub_service = EventSubService()