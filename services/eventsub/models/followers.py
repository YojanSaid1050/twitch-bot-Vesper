# services/eventsub/models/followers.py
"""
Modelos para eventos de seguidores.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class FollowEvent:
    """Evento de nuevo seguidor."""
    user_id: str
    user_name: str
    user_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    followed_at: datetime
    timestamp: datetime = datetime.now()