# services/eventsub/handlers/hype_train.py
"""
Handlers para eventos de Hype Train.
"""

from services.eventsub.models import HypeTrainBeginEvent, HypeTrainProgressEvent, HypeTrainEndEvent
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_hype_train_begin(event_data: dict) -> None:
    """Procesa un evento de inicio de Hype Train."""
    try:
        top_contributions = []
        for tc in event_data.get("top_contributions", []):
            top_contributions.append({
                "user_id": tc.get("user_id", ""),
                "user_name": tc.get("user_name", "Desconocido"),
                "user_login": tc.get("user_login", ""),
                "type": tc.get("type", "bits"),
                "total": tc.get("total", 0)
            })
        begin = HypeTrainBeginEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            total=event_data.get("total", 0),
            progress=event_data.get("progress", 0),
            goal=event_data.get("goal", 0),
            top_contributions=top_contributions,
            started_at=datetime.fromisoformat(event_data.get("started_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="hype_train.begin", payload=begin))
        logger.info(f"Hype Train iniciado: {begin.progress}/{begin.goal}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_hype_train_begin: {e}")
        stats_collector.increment("subscription_errors")


async def handle_hype_train_progress(event_data: dict) -> None:
    """Procesa un evento de progreso de Hype Train."""
    try:
        top_contributions = []
        for tc in event_data.get("top_contributions", []):
            top_contributions.append({
                "user_id": tc.get("user_id", ""),
                "user_name": tc.get("user_name", "Desconocido"),
                "user_login": tc.get("user_login", ""),
                "type": tc.get("type", "bits"),
                "total": tc.get("total", 0)
            })
        progress = HypeTrainProgressEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            total=event_data.get("total", 0),
            progress=event_data.get("progress", 0),
            goal=event_data.get("goal", 0),
            top_contributions=top_contributions,
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="hype_train.progress", payload=progress))
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_hype_train_progress: {e}")
        stats_collector.increment("subscription_errors")


async def handle_hype_train_end(event_data: dict) -> None:
    """Procesa un evento de fin de Hype Train."""
    try:
        top_contributions = []
        for tc in event_data.get("top_contributions", []):
            top_contributions.append({
                "user_id": tc.get("user_id", ""),
                "user_name": tc.get("user_name", "Desconocido"),
                "user_login": tc.get("user_login", ""),
                "type": tc.get("type", "bits"),
                "total": tc.get("total", 0)
            })
        end = HypeTrainEndEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            total=event_data.get("total", 0),
            progress=event_data.get("progress", 0),
            goal=event_data.get("goal", 0),
            top_contributions=top_contributions,
            ended_at=datetime.fromisoformat(event_data.get("ended_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="hype_train.end", payload=end))
        logger.info(f"Hype Train finalizado: {end.progress}/{end.goal}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_hype_train_end: {e}")
        stats_collector.increment("subscription_errors")