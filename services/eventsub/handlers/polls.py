# services/eventsub/handlers/polls.py
"""
Handlers para eventos de encuestas.
"""

from services.eventsub.models import PollBeginEvent, PollProgressEvent, PollEndEvent
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_poll_begin(event_data: dict) -> None:
    """Procesa un evento de inicio de encuesta."""
    try:
        choices = []
        for c in event_data.get("choices", []):
            choices.append({
                "id": c.get("id", ""),
                "title": c.get("title", ""),
                "votes": c.get("votes", 0),
                "percentage": c.get("percentage", 0.0)
            })
        begin = PollBeginEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            poll_id=event_data.get("poll_id", ""),
            title=event_data.get("title", "Encuesta"),
            choices=choices,
            started_at=datetime.fromisoformat(event_data.get("started_at", "").replace("Z", "+00:00")),
            duration_seconds=event_data.get("duration_seconds", 0),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="poll.begin", payload=begin))
        logger.info(f"Encuesta iniciada: {begin.title}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_poll_begin: {e}")
        stats_collector.increment("subscription_errors")


async def handle_poll_progress(event_data: dict) -> None:
    """Procesa un evento de progreso de encuesta."""
    try:
        choices = []
        for c in event_data.get("choices", []):
            choices.append({
                "id": c.get("id", ""),
                "title": c.get("title", ""),
                "votes": c.get("votes", 0),
                "percentage": c.get("percentage", 0.0)
            })
        progress = PollProgressEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            poll_id=event_data.get("poll_id", ""),
            title=event_data.get("title", "Encuesta"),
            choices=choices,
            votes=event_data.get("votes", 0),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="poll.progress", payload=progress))
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_poll_progress: {e}")
        stats_collector.increment("subscription_errors")


async def handle_poll_end(event_data: dict) -> None:
    """Procesa un evento de fin de encuesta."""
    try:
        choices = []
        for c in event_data.get("choices", []):
            choices.append({
                "id": c.get("id", ""),
                "title": c.get("title", ""),
                "votes": c.get("votes", 0),
                "percentage": c.get("percentage", 0.0)
            })
        end = PollEndEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            poll_id=event_data.get("poll_id", ""),
            title=event_data.get("title", "Encuesta"),
            choices=choices,
            votes=event_data.get("votes", 0),
            status=event_data.get("status", "completed"),
            ended_at=datetime.fromisoformat(event_data.get("ended_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="poll.end", payload=end))
        logger.info(f"Encuesta finalizada: {end.title} - {end.status}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_poll_end: {e}")
        stats_collector.increment("subscription_errors")