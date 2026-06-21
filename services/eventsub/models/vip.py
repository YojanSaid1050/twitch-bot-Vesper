# services/eventsub/models/vip.py
"""
Modelos para eventos de VIP.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class VIPAddEvent:
    """Evento de VIP añadido."""
    user_id: str
    user_name: str
    user_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class VIPRemoveEvent:
    """Evento de VIP removido."""
    user_id: str
    user_name: str
    user_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    timestamp: datetime = datetime.now()