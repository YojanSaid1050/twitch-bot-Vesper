# services/eventsub/models/automod.py
"""
Modelos para eventos de Automod.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass(slots=True)
class AutoModHoldEvent:
    """Evento de mensaje en hold de Automod."""
    user_id: str
    user_name: str
    user_login: str
    moderator_user_id: str
    moderator_name: str
    moderator_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    message_id: str
    message: str
    reason: str
    held_at: datetime
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class AutoModUpdateEvent:
    """Evento de actualización de mensaje en Automod."""
    user_id: str
    user_name: str
    user_login: str
    moderator_user_id: str
    moderator_name: str
    moderator_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    message_id: str
    message: str
    status: str  # "approved", "denied"
    timestamp: datetime = datetime.now()