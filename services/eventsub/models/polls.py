# services/eventsub/models/polls.py
"""
Modelos para eventos de encuestas.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass(slots=True)
class PollChoice:
    """Opción de una encuesta."""
    id: str
    title: str
    votes: int
    percentage: float


@dataclass(slots=True)
class PollBeginEvent:
    """Evento de inicio de encuesta."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    poll_id: str
    title: str
    choices: List[PollChoice]
    started_at: datetime
    duration_seconds: int
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class PollProgressEvent:
    """Evento de progreso de encuesta."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    poll_id: str
    title: str
    choices: List[PollChoice]
    votes: int
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class PollEndEvent:
    """Evento de fin de encuesta."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    poll_id: str
    title: str
    choices: List[PollChoice]
    votes: int
    status: str  # "completed", "archived", "cancelled", etc.
    ended_at: datetime
    timestamp: datetime = datetime.now()