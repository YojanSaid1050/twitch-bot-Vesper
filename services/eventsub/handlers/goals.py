# services/eventsub/handlers/goals.py
"""
Handlers para eventos de metas.
"""

from services.eventsub.models import GoalBeginEvent, GoalProgressEvent, GoalEndEvent
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_goal_begin(event_data: dict) -> None:
    """Procesa un evento de inicio de meta."""
    try:
        begin = GoalBeginEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            goal_id=event_data.get("goal_id", ""),
            goal_type=event_data.get("type", "follower"),
            description=event_data.get("description", "Meta"),
            current_amount=event_data.get("current_amount", 0),
            target_amount=event_data.get("target_amount", 0),
            started_at=datetime.fromisoformat(event_data.get("started_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="goal.begin", payload=begin))
        logger.info(f"Meta iniciada: {begin.description} - {begin.goal_type}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_goal_begin: {e}")
        stats_collector.increment("subscription_errors")


async def handle_goal_progress(event_data: dict) -> None:
    """Procesa un evento de progreso de meta."""
    try:
        progress = GoalProgressEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            goal_id=event_data.get("goal_id", ""),
            goal_type=event_data.get("type", "follower"),
            description=event_data.get("description", "Meta"),
            current_amount=event_data.get("current_amount", 0),
            target_amount=event_data.get("target_amount", 0),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="goal.progress", payload=progress))
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_goal_progress: {e}")
        stats_collector.increment("subscription_errors")


async def handle_goal_end(event_data: dict) -> None:
    """Procesa un evento de fin de meta."""
    try:
        end = GoalEndEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            goal_id=event_data.get("goal_id", ""),
            goal_type=event_data.get("type", "follower"),
            description=event_data.get("description", "Meta"),
            current_amount=event_data.get("current_amount", 0),
            target_amount=event_data.get("target_amount", 0),
            achieved=event_data.get("achieved", False),
            ended_at=datetime.fromisoformat(event_data.get("ended_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="goal.end", payload=end))
        logger.info(f"Meta finalizada: {end.description} - {'Lograda' if end.achieved else 'No lograda'}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_goal_end: {e}")
        stats_collector.increment("subscription_errors")