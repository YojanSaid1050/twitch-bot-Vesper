# services/eventsub/models/moderation.py
"""
Modelos para eventos de moderación.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class BanEvent:
    """Evento de ban/ timeout."""
    user_id: str
    user_name: str
    user_login: str
    moderator_user_id: str
    moderator_name: str
    moderator_login: str
    reason: str
    duration_seconds: Optional[int]  # None = ban permanente
    is_permanent: bool
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class UnbanEvent:
    """Evento de unban."""
    user_id: str
    user_name: str
    user_login: str
    moderator_user_id: str
    moderator_name: str
    moderator_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class TimeoutEvent:
    """Evento de timeout."""
    user_id: str
    user_name: str
    user_login: str
    moderator_user_id: str
    moderator_name: str
    moderator_login: str
    reason: str
    duration_seconds: int
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class ClearChatEvent:
    """Evento de limpieza de chat."""
    moderator_user_id: str
    moderator_name: str
    moderator_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class DeleteMessageEvent:
    """Evento de eliminación de mensaje."""
    target_user_id: str
    target_user_name: str
    target_user_login: str
    moderator_user_id: str
    moderator_name: str
    moderator_login: str
    message_id: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class SuspiciousUserEvent:
    """Evento de usuario sospechoso."""
    user_id: str
    user_name: str
    user_login: str
    moderator_user_id: str
    moderator_name: str
    moderator_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    reason: str
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class ShieldModeEvent:
    """Evento de Shield Mode."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    moderator_user_id: str
    moderator_name: str
    moderator_login: str
    action: str  # "begin" o "end"
    timestamp: datetime = datetime.now()