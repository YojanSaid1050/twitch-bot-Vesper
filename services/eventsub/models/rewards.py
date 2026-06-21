# services/eventsub/models/rewards.py
"""
Modelos para eventos de recompensas de puntos de canal.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class RewardRedemptionAddEvent:
    """Evento de canje de recompensa."""
    user_id: str
    user_name: str
    user_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    redemption_id: str
    reward_id: str
    reward_title: str
    reward_cost: int
    input: Optional[str]
    status: str
    redeemed_at: datetime
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class RewardRedemptionUpdateEvent:
    """Evento de actualización de canje de recompensa."""
    user_id: str
    user_name: str
    user_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    redemption_id: str
    reward_id: str
    reward_title: str
    reward_cost: int
    status: str  # "fulfilled", "canceled"
    redeemed_at: datetime
    timestamp: datetime = datetime.now()