# services/eventsub/models/stream.py
"""
Modelos para eventos de stream.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass(slots=True)
class StreamOnlineEvent:
    """Evento de stream en vivo."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    started_at: datetime
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class StreamOfflineEvent:
    """Evento de stream offline."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class ChannelUpdateEvent:
    """Evento de actualización de canal."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    title: str
    language: str
    category_id: str
    category_name: str
    content_classification_labels: List[str]
    timestamp: datetime = datetime.now()