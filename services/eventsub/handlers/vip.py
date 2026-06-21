# services/eventsub/handlers/vip.py
"""
Handlers para eventos de VIP.
"""

from services.eventsub.models import VIPAddEvent, VIPRemoveEvent
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_vip_add(event_data: dict) -> None:
    """Procesa un evento de VIP añadido."""
    try:
        vip = VIPAddEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="vip.add", payload=vip))
        logger.info(f"VIP añadido: {vip.user_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_vip_add: {e}")
        stats_collector.increment("subscription_errors")


async def handle_vip_remove(event_data: dict) -> None:
    """Procesa un evento de VIP removido."""
    try:
        vip = VIPRemoveEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="vip.remove", payload=vip))
        logger.info(f"VIP removido: {vip.user_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_vip_remove: {e}")
        stats_collector.increment("subscription_errors")