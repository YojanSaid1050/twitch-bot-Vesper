# services/eventsub/models/subscriptions.py
"""
Modelos para eventos de suscripciones.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class SubscribeEvent:
    """Evento de nueva suscripción."""
    user_id: str
    user_name: str
    user_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    tier: str  # "1000", "2000", "3000"
    is_gift: bool
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class SubscriptionEndEvent:
    """Evento de fin de suscripción."""
    user_id: str
    user_name: str
    user_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    tier: str
    is_gift: bool
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class SubscriptionGiftEvent:
    """Evento de suscripción regalada."""
    user_id: str  # El que regala (o "Anónimo")
    user_name: str
    user_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    total: int  # Número de suscripciones regaladas
    tier: str
    cumulative_total: Optional[int] = None
    is_anonymous: bool = False
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class SubscriptionMessageEvent:
    """Evento de re-suscripción con mensaje."""
    user_id: str
    user_name: str
    user_login: str
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    tier: str
    message: str
    cumulative_months: int
    streak_months: Optional[int]
    duration_months: int
    is_gift: bool
    timestamp: datetime = datetime.now()