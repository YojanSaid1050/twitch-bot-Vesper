# services/eventsub/handlers/raids.py
"""
Handler para eventos de raids.
"""

from services.eventsub.models import RaidEvent
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_raid(event_data: dict) -> None:
    """Procesa un evento de raid."""
    try:
        raid = RaidEvent(
            from_broadcaster_user_id=event_data.get("from_broadcaster_user_id", ""),
            from_broadcaster_name=event_data.get("from_broadcaster_user_name", "Desconocido"),
            from_broadcaster_login=event_data.get("from_broadcaster_user_login", ""),
            to_broadcaster_user_id=event_data.get("to_broadcaster_user_id", ""),
            to_broadcaster_name=event_data.get("to_broadcaster_user_name", "Desconocido"),
            to_broadcaster_login=event_data.get("to_broadcaster_user_login", ""),
            viewers=event_data.get("viewers", 0),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="raid.incoming", payload=raid))
        logger.info(f"Raid de {raid.from_broadcaster_name} con {raid.viewers} espectadores")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_raid: {e}")
        stats_collector.increment("subscription_errors")