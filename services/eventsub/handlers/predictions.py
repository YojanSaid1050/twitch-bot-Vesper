# services/eventsub/handlers/predictions.py
"""
Handlers para eventos de predicciones.
"""

from services.eventsub.models import (
    PredictionBeginEvent, PredictionProgressEvent,
    PredictionLockEvent, PredictionEndEvent
)
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_prediction_begin(event_data: dict) -> None:
    """Procesa un evento de inicio de predicción."""
    try:
        outcomes = []
        for o in event_data.get("outcomes", []):
            outcomes.append({
                "id": o.get("id", ""),
                "title": o.get("title", ""),
                "color": o.get("color", ""),
                "points": o.get("points", 0),
                "top_predictors": o.get("top_predictors", [])
            })
        begin = PredictionBeginEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            prediction_id=event_data.get("prediction_id", ""),
            title=event_data.get("title", "Predicción"),
            outcomes=outcomes,
            started_at=datetime.fromisoformat(event_data.get("started_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="prediction.begin", payload=begin))
        logger.info(f"Predicción iniciada: {begin.title}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_prediction_begin: {e}")
        stats_collector.increment("subscription_errors")


async def handle_prediction_progress(event_data: dict) -> None:
    """Procesa un evento de progreso de predicción."""
    try:
        outcomes = []
        for o in event_data.get("outcomes", []):
            outcomes.append({
                "id": o.get("id", ""),
                "title": o.get("title", ""),
                "color": o.get("color", ""),
                "points": o.get("points", 0),
                "top_predictors": o.get("top_predictors", [])
            })
        progress = PredictionProgressEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            prediction_id=event_data.get("prediction_id", ""),
            title=event_data.get("title", "Predicción"),
            outcomes=outcomes,
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="prediction.progress", payload=progress))
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_prediction_progress: {e}")
        stats_collector.increment("subscription_errors")


async def handle_prediction_lock(event_data: dict) -> None:
    """Procesa un evento de bloqueo de predicción."""
    try:
        outcomes = []
        for o in event_data.get("outcomes", []):
            outcomes.append({
                "id": o.get("id", ""),
                "title": o.get("title", ""),
                "color": o.get("color", ""),
                "points": o.get("points", 0),
                "top_predictors": o.get("top_predictors", [])
            })
        lock = PredictionLockEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            prediction_id=event_data.get("prediction_id", ""),
            title=event_data.get("title", "Predicción"),
            outcomes=outcomes,
            locked_at=datetime.fromisoformat(event_data.get("locked_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="prediction.lock", payload=lock))
        logger.info(f"Predicción bloqueada: {lock.title}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_prediction_lock: {e}")
        stats_collector.increment("subscription_errors")


async def handle_prediction_end(event_data: dict) -> None:
    """Procesa un evento de fin de predicción."""
    try:
        outcomes = []
        for o in event_data.get("outcomes", []):
            outcomes.append({
                "id": o.get("id", ""),
                "title": o.get("title", ""),
                "color": o.get("color", ""),
                "points": o.get("points", 0),
                "top_predictors": o.get("top_predictors", [])
            })
        end = PredictionEndEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            prediction_id=event_data.get("prediction_id", ""),
            title=event_data.get("title", "Predicción"),
            winning_outcome_id=event_data.get("winning_outcome_id"),
            outcomes=outcomes,
            status=event_data.get("status", "resolved"),
            ended_at=datetime.fromisoformat(event_data.get("ended_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="prediction.end", payload=end))
        logger.info(f"Predicción finalizada: {end.title} - {end.status}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_prediction_end: {e}")
        stats_collector.increment("subscription_errors")