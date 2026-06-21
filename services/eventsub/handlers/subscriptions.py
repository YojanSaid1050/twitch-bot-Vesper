# services/eventsub/handlers/subscriptions.py
"""
Handlers para eventos de suscripciones.
"""

from services.eventsub.models import (
    SubscribeEvent, SubscriptionEndEvent,
    SubscriptionGiftEvent, SubscriptionMessageEvent
)
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_subscribe(event_data: dict) -> None:
    """Procesa un evento de nueva suscripción."""
    try:
        sub = SubscribeEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            tier=event_data.get("tier", "1000"),
            is_gift=event_data.get("is_gift", False),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="subscription.new", payload=sub))
        logger.info(f"Nueva suscripción: {sub.user_name} - Tier {sub.tier}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_subscribe: {e}")
        stats_collector.increment("subscription_errors")


async def handle_subscription_end(event_data: dict) -> None:
    """Procesa un evento de fin de suscripción."""
    try:
        end = SubscriptionEndEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            tier=event_data.get("tier", "1000"),
            is_gift=event_data.get("is_gift", False),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="subscription.end", payload=end))
        logger.info(f"Suscripción terminada: {end.user_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_subscription_end: {e}")
        stats_collector.increment("subscription_errors")


async def handle_subscription_gift(event_data: dict) -> None:
    """Procesa un evento de suscripción regalada."""
    try:
        gift = SubscriptionGiftEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Alguien"),
            user_login=event_data.get("user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            total=event_data.get("total", 1),
            tier=event_data.get("tier", "1000"),
            cumulative_total=event_data.get("cumulative_total"),
            is_anonymous=event_data.get("is_anonymous", False),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="subscription.gift", payload=gift))
        logger.info(f"Suscripción regalada: {gift.total} por {gift.user_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_subscription_gift: {e}")
        stats_collector.increment("subscription_errors")


async def handle_subscription_message(event_data: dict) -> None:
    """Procesa un evento de re-suscripción con mensaje."""
    try:
        message = SubscriptionMessageEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            tier=event_data.get("tier", "1000"),
            message=event_data.get("message", {}).get("text", ""),
            cumulative_months=event_data.get("cumulative_months", 0),
            streak_months=event_data.get("streak_months"),
            duration_months=event_data.get("duration_months", 0),
            is_gift=event_data.get("is_gift", False),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="subscription.resub", payload=message))
        logger.info(f"Re-suscripción: {message.user_name} - {message.cumulative_months} meses")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_subscription_message: {e}")
        stats_collector.increment("subscription_errors")