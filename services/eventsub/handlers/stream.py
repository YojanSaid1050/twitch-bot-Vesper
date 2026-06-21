# services/eventsub/handlers/stream.py
"""
Handlers para eventos de stream.
"""

from services.eventsub.models import StreamOnlineEvent, StreamOfflineEvent, ChannelUpdateEvent
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_stream_online(event_data: dict) -> None:
    """Procesa un evento de stream en vivo."""
    try:
        online = StreamOnlineEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            started_at=datetime.fromisoformat(event_data.get("started_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="stream.online", payload=online))
        logger.info(f"Stream EN VIVO: {online.broadcaster_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_stream_online: {e}")
        stats_collector.increment("subscription_errors")


async def handle_stream_offline(event_data: dict) -> None:
    """Procesa un evento de stream offline."""
    try:
        offline = StreamOfflineEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="stream.offline", payload=offline))
        logger.info(f"Stream OFFLINE: {offline.broadcaster_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_stream_offline: {e}")
        stats_collector.increment("subscription_errors")


async def handle_channel_update(event_data: dict) -> None:
    """Procesa un evento de actualización de canal."""
    try:
        update = ChannelUpdateEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            title=event_data.get("title", "Sin título"),
            language=event_data.get("language", "es"),
            category_id=event_data.get("category_id", ""),
            category_name=event_data.get("category_name", "No especificado"),
            content_classification_labels=event_data.get("content_classification_labels", []),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="channel.update", payload=update))
        logger.info(f"Canal actualizado: {update.broadcaster_name} - {update.title}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_channel_update: {e}")
        stats_collector.increment("subscription_errors")