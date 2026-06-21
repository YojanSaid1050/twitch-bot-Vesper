# services/eventsub/handlers/shoutouts.py
"""
Handlers para eventos de Shoutout.
"""

from services.eventsub.models import ShoutoutCreateEvent, ShoutoutReceiveEvent
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_shoutout_create(event_data: dict) -> None:
    """Procesa un evento de shoutout creado."""
    try:
        shoutout = ShoutoutCreateEvent(
            from_broadcaster_user_id=event_data.get("from_broadcaster_user_id", ""),
            from_broadcaster_name=event_data.get("from_broadcaster_user_name", "Desconocido"),
            from_broadcaster_login=event_data.get("from_broadcaster_user_login", ""),
            to_broadcaster_user_id=event_data.get("to_broadcaster_user_id", ""),
            to_broadcaster_name=event_data.get("to_broadcaster_user_name", "Desconocido"),
            to_broadcaster_login=event_data.get("to_broadcaster_user_login", ""),
            viewer_count=event_data.get("viewer_count", 0),
            started_at=datetime.fromisoformat(event_data.get("started_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="shoutout.create", payload=shoutout))
        logger.info(f"Shoutout creado de {shoutout.from_broadcaster_name} a {shoutout.to_broadcaster_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_shoutout_create: {e}")
        stats_collector.increment("subscription_errors")


async def handle_shoutout_receive(event_data: dict) -> None:
    """Procesa un evento de shoutout recibido."""
    try:
        shoutout = ShoutoutReceiveEvent(
            from_broadcaster_user_id=event_data.get("from_broadcaster_user_id", ""),
            from_broadcaster_name=event_data.get("from_broadcaster_user_name", "Desconocido"),
            from_broadcaster_login=event_data.get("from_broadcaster_user_login", ""),
            to_broadcaster_user_id=event_data.get("to_broadcaster_user_id", ""),
            to_broadcaster_name=event_data.get("to_broadcaster_user_name", "Desconocido"),
            to_broadcaster_login=event_data.get("to_broadcaster_user_login", ""),
            viewer_count=event_data.get("viewer_count", 0),
            started_at=datetime.fromisoformat(event_data.get("started_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="shoutout.receive", payload=shoutout))
        logger.info(f"Shoutout recibido de {shoutout.from_broadcaster_name} a {shoutout.to_broadcaster_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_shoutout_receive: {e}")
        stats_collector.increment("subscription_errors")