# services/eventsub_service.py
"""
Fachada del sistema EventSub.
Únicamente expone la API pública.
"""

from services.eventsub.manager import manager
from services.eventsub.dispatcher import dispatcher
from services.eventsub.webhook import webhook_handler
from services.eventsub.deduplicator import deduplicator
from services.eventsub.statistics import stats_collector
from services.eventsub.metrics import metrics_collector
from services.eventsub.event_bus import event_bus
from services.eventsub.handlers import *
from utils.logger import get_logger

logger = get_logger(__name__)


class EventSubService:
    """Fachada del sistema EventSub."""

    def __init__(self):
        self._manager = manager
        self._dispatcher = dispatcher
        self._webhook_handler = webhook_handler
        self._deduplicator = deduplicator
        self._stats = stats_collector
        self._metrics = metrics_collector
        self._event_bus = event_bus
        self._bot = None
        self._initialized = False

    def set_bot(self, bot):
        """Establece la instancia del bot."""
        self._bot = bot
        if not self._initialized:
            self._register_handlers()
            self._initialized = True

    def _register_handlers(self):
        """Registra los handlers para cada tipo de evento en el dispatcher."""
        # Mapeo de tipos de evento a handlers
        handlers = {
            # Stream
            "stream.online": handle_stream_online,
            "stream.offline": handle_stream_offline,
            "channel.update": handle_channel_update,

            # Subscriptions
            "channel.subscribe": handle_subscribe,
            "channel.subscription.end": handle_subscription_end,
            "channel.subscription.gift": handle_subscription_gift,
            "channel.subscription.message": handle_subscription_message,

            # Followers
            "channel.follow": handle_follow,

            # Raids
            "channel.raid": handle_raid,

            # VIP
            "channel.vip.add": handle_vip_add,
            "channel.vip.remove": handle_vip_remove,

            # Predictions
            "channel.prediction.begin": handle_prediction_begin,
            "channel.prediction.progress": handle_prediction_progress,
            "channel.prediction.lock": handle_prediction_lock,
            "channel.prediction.end": handle_prediction_end,

            # Polls
            "channel.poll.begin": handle_poll_begin,
            "channel.poll.progress": handle_poll_progress,
            "channel.poll.end": handle_poll_end,

            # Rewards
            "channel.channel_points_custom_reward_redemption.add": handle_reward_redemption_add,
            "channel.channel_points_custom_reward_redemption.update": handle_reward_redemption_update,

            # Goals
            "channel.goal.begin": handle_goal_begin,
            "channel.goal.progress": handle_goal_progress,
            "channel.goal.end": handle_goal_end,

            # Hype Train
            "channel.hype_train.begin": handle_hype_train_begin,
            "channel.hype_train.progress": handle_hype_train_progress,
            "channel.hype_train.end": handle_hype_train_end,

            # Shoutouts
            "channel.shoutout.create": handle_shoutout_create,
            "channel.shoutout.receive": handle_shoutout_receive,

            # Automod
            "automod.message.hold": handle_automod_hold,
            "automod.message.update": handle_automod_update,

            # Chat
            "channel.chat.message_delete": handle_chat_message_delete,
            "channel.chat.clear": handle_chat_clear,
            "channel.chat.clear_user_messages": handle_chat_clear_user_messages,

            # Moderation (adicionales) - BAN y UNBAN ELIMINADOS
            "channel.moderator.add": handle_vip_add,  # Similar a VIP
            "channel.moderator.remove": handle_vip_remove,
            "channel.shield_mode.begin": handle_shield_mode,
            "channel.shield_mode.end": handle_shield_mode,
            "channel.suspicious_user.message": handle_suspicious_user,
            "channel.suspicious_user.update": handle_suspicious_user,
        }

        # Registrar cada handler
        for event_type, handler in handlers.items():
            self._dispatcher.register(event_type, handler)

        # Handler genérico para eventos no registrados
        self._dispatcher.register("generic", handle_generic_event)

        logger.info(f"Registrados {len(handlers)} handlers para EventSub")

    def process_webhook(self, message_id: str, event_type: str, event_data: dict) -> None:
        """
        Procesa un webhook entrante.
        """
        # 1. Deduplicar
        if self._deduplicator.is_duplicate(message_id):
            self._stats.increment("events_duplicated")
            return

        # 2. Despachar al handler correspondiente
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._safe_dispatch(event_type, event_data, message_id))
        except RuntimeError:
            # Si no hay loop, crear uno temporal
            asyncio.run(self._safe_dispatch(event_type, event_data, message_id))

    async def _safe_dispatch(self, event_type: str, event_data: dict, message_id: str):
        """Ejecuta el dispatch de forma segura."""
        try:
            await self._dispatcher.dispatch(event_type, event_data, message_id)
        except Exception as e:
            logger.error(f"Error en dispatch de {event_type}: {e}", exc_info=True)
            self._stats.increment("subscription_errors")

    def subscribe_to_events(self):
        """Inicia las suscripciones."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._manager.start())
        except RuntimeError:
            asyncio.run(self._manager.start())

    def stop(self):
        """Detiene el sistema."""
        self._manager.stop()

    def get_statistics(self) -> dict:
        """Devuelve estadísticas del sistema."""
        return self._stats.get().to_dict()

    def get_recent_metrics(self, limit: int = 100) -> list:
        """Devuelve métricas recientes."""
        return self._metrics.get_recent(limit)

    def get_event_bus(self):
        """Devuelve el event bus para suscripciones externas."""
        return self._event_bus


# Instancia global (compatibilidad con código existente)
eventsub_service = EventSubService()