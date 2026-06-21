# services/eventsub/handlers/automod.py
"""
Handlers para eventos de Automod.
"""

from services.eventsub.models import AutoModHoldEvent, AutoModUpdateEvent
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_automod_hold(event_data: dict) -> None:
    """Procesa un evento de mensaje en hold de Automod."""
    try:
        hold = AutoModHoldEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            moderator_user_id=event_data.get("moderator_user_id", ""),
            moderator_name=event_data.get("moderator_user_name", "Staff"),
            moderator_login=event_data.get("moderator_user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            message_id=event_data.get("message_id", ""),
            message=event_data.get("message", ""),
            reason=event_data.get("reason", "Automod"),
            held_at=datetime.fromisoformat(event_data.get("held_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="automod.hold", payload=hold))
        logger.info(f"Automod hold: {hold.user_name} - {hold.reason}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_automod_hold: {e}")
        stats_collector.increment("subscription_errors")


async def handle_automod_update(event_data: dict) -> None:
    """Procesa un evento de actualización de mensaje en Automod."""
    try:
        update = AutoModUpdateEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            moderator_user_id=event_data.get("moderator_user_id", ""),
            moderator_name=event_data.get("moderator_user_name", "Staff"),
            moderator_login=event_data.get("moderator_user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            message_id=event_data.get("message_id", ""),
            message=event_data.get("message", ""),
            status=event_data.get("status", "approved"),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="automod.update", payload=update))
        logger.info(f"Automod update: {update.user_name} - {update.status}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_automod_update: {e}")
        stats_collector.increment("subscription_errors")