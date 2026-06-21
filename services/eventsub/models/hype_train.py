# services/eventsub/models/hype_train.py
"""
Modelos para eventos de Hype Train.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass(slots=True)
class HypeTrainContribution:
    """Contribución al Hype Train."""
    user_id: str
    user_name: str
    user_login: str
    type: str  # "bits", "subscription"
    total: int


@dataclass(slots=True)
class HypeTrainBeginEvent:
    """Evento de inicio de Hype Train."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    total: int
    progress: int
    goal: int
    top_contributions: List[HypeTrainContribution]
    started_at: datetime
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class HypeTrainProgressEvent:
    """Evento de progreso de Hype Train."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    total: int
    progress: int
    goal: int
    top_contributions: List[HypeTrainContribution]
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class HypeTrainEndEvent:
    """Evento de fin de Hype Train."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    total: int
    progress: int
    goal: int
    top_contributions: List[HypeTrainContribution]
    ended_at: datetime
    timestamp: datetime = datetime.now()