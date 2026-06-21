# services/eventsub/handlers/generic.py
"""
Handler genérico para eventos no específicos.
"""

from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_generic_event(event_data: dict) -> None:
    """
    Handler genérico para eventos que no tienen un handler específico.
    Solo publica el evento en el bus para que otros módulos lo procesen.
    """
    try:
        # Publicar el evento genérico en el bus
        await event_bus.publish(
            Event(
                type="event.generic",
                payload=event_data,
                source="eventsub"
            )
        )
        # Registrar estadística
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_generic_event: {e}")
        stats_collector.increment("subscription_errors")