# services/eventsub/handlers/rewards.py
"""
Handlers para eventos de recompensas de puntos de canal.
"""

from services.eventsub.models import RewardRedemptionAddEvent, RewardRedemptionUpdateEvent
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_reward_redemption_add(event_data: dict) -> None:
    """Procesa un evento de canje de recompensa."""
    try:
        reward = RewardRedemptionAddEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            redemption_id=event_data.get("redemption_id", ""),
            reward_id=event_data.get("reward", {}).get("id", ""),
            reward_title=event_data.get("reward", {}).get("title", "Recompensa"),
            reward_cost=event_data.get("reward", {}).get("cost", 0),
            input=event_data.get("input", ""),
            status=event_data.get("status", "unfulfilled"),
            redeemed_at=datetime.fromisoformat(event_data.get("redeemed_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="reward.redemption.add", payload=reward))
        logger.info(f"Recompensa canjeada: {reward.user_name} - {reward.reward_title}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_reward_redemption_add: {e}")
        stats_collector.increment("subscription_errors")


async def handle_reward_redemption_update(event_data: dict) -> None:
    """Procesa un evento de actualización de canje de recompensa."""
    try:
        reward = RewardRedemptionUpdateEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            redemption_id=event_data.get("redemption_id", ""),
            reward_id=event_data.get("reward", {}).get("id", ""),
            reward_title=event_data.get("reward", {}).get("title", "Recompensa"),
            reward_cost=event_data.get("reward", {}).get("cost", 0),
            status=event_data.get("status", "fulfilled"),
            redeemed_at=datetime.fromisoformat(event_data.get("redeemed_at", "").replace("Z", "+00:00")),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="reward.redemption.update", payload=reward))
        logger.info(f"Recompensa actualizada: {reward.user_name} - {reward.reward_title} - {reward.status}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_reward_redemption_update: {e}")
        stats_collector.increment("subscription_errors")