# services/eventsub/models/raids.py
"""
Modelos para eventos de raids.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class RaidEvent:
    """Evento de raid entrante."""
    from_broadcaster_user_id: str
    from_broadcaster_name: str
    from_broadcaster_login: str
    to_broadcaster_user_id: str
    to_broadcaster_name: str
    to_broadcaster_login: str
    viewers: int
    timestamp: datetime = datetime.now()