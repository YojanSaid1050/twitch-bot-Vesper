# services/eventsub/definitions.py
"""
Definiciones de tipos y estructuras de datos para EventSub.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime


class ScopeOwner(Enum):
    APP = "app"
    BROADCASTER = "broadcaster"
    MODERATOR = "moderator"
    USER = "user"


class TransportType(Enum):
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"


@dataclass(slots=True)
class EventDefinition:
    type: str
    version: str
    handler: str
    required_scopes: List[str] = field(default_factory=list)
    scope_owner: ScopeOwner = ScopeOwner.APP
    condition_fields: Dict[str, str] = field(default_factory=dict)
    transport_support: List[TransportType] = field(default_factory=lambda: [TransportType.WEBHOOK])
    enabled: bool = True


@dataclass(slots=True)
class TokenInfo:
    scopes: List[str] = field(default_factory=list)
    user_id: Optional[str] = None
    login: Optional[str] = None
    expires_at: float = 0.0
    fetched_at: float = 0.0


@dataclass(slots=True)
class Subscription:
    id: str
    type: str
    version: str
    status: str
    condition: Dict[str, str]
    transport: Dict[str, Any]
    created_at: datetime


@dataclass(slots=True)
class WebhookPayload:
    message_id: str
    message_type: str
    timestamp: str
    signature: str
    raw_body: str
    data: Dict[str, Any]


@dataclass(slots=True)
class EventResult:
    success: bool
    event_type: str
    message_id: str
    error: Optional[str] = None
    processed_at: datetime = field(default_factory=datetime.now)