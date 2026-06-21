# services/eventsub/models/shoutouts.py
"""
Modelos para eventos de Shoutout.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ShoutoutCreateEvent:
    """Evento de shoutout creado."""
    from_broadcaster_user_id: str
    from_broadcaster_name: str
    from_broadcaster_login: str
    to_broadcaster_user_id: str
    to_broadcaster_name: str
    to_broadcaster_login: str
    viewer_count: int
    started_at: datetime
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class ShoutoutReceiveEvent:
    """Evento de shoutout recibido."""
    from_broadcaster_user_id: str
    from_broadcaster_name: str
    from_broadcaster_login: str
    to_broadcaster_user_id: str
    to_broadcaster_name: str
    to_broadcaster_login: str
    viewer_count: int
    started_at: datetime
    timestamp: datetime = datetime.now()