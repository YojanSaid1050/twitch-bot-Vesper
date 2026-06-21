# services/eventsub/handlers/followers.py
"""
Handler para eventos de seguidores.
"""

from services.eventsub.models import FollowEvent
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_follow(event_data: dict) -> None:
    """Procesa un evento de nuevo seguidor."""
    try:
        follow = FollowEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            followed_at=datetime.fromisoformat(event_data.get("followed_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="follow.new", payload=follow))
        logger.info(f"Nuevo seguidor: {follow.user_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_follow: {e}")
        stats_collector.increment("subscription_errors")