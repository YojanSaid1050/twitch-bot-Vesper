# services/eventsub/models/chat.py
"""
Modelos para eventos de chat.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ChatMessageDeleteEvent:
    """Evento de eliminación de mensaje de chat."""
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
class ChatClearEvent:
    """Evento de limpieza de chat."""
    moderator_user_id: str
    moderator_name: str
    moderator_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class ChatClearUserMessagesEvent:
    """Evento de limpieza de mensajes de un usuario."""
    target_user_id: str
    target_user_name: str
    target_user_login: str
    moderator_user_id: str
    moderator_name: str
    moderator_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    timestamp: datetime = datetime.now()