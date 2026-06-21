# services/eventsub/models/goals.py
"""
Modelos para eventos de metas.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class GoalBeginEvent:
    """Evento de inicio de meta."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    goal_id: str
    goal_type: str  # "follower", "subscription", "bits"
    description: str
    current_amount: int
    target_amount: int
    started_at: datetime
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class GoalProgressEvent:
    """Evento de progreso de meta."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    goal_id: str
    goal_type: str
    description: str
    current_amount: int
    target_amount: int
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class GoalEndEvent:
    """Evento de fin de meta."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    goal_id: str
    goal_type: str
    description: str
    current_amount: int
    target_amount: int
    achieved: bool
    ended_at: datetime
    timestamp: datetime = datetime.now()