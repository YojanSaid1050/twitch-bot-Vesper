# services/eventsub/models/predictions.py
"""
Modelos para eventos de predicciones.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(slots=True)
class PredictionOutcome:
    """Resultado de una predicción."""
    id: str
    title: str
    color: str
    points: int
    top_predictors: List[dict]


@dataclass(slots=True)
class PredictionBeginEvent:
    """Evento de inicio de predicción."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    prediction_id: str
    title: str
    outcomes: List[PredictionOutcome]
    started_at: datetime
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class PredictionProgressEvent:
    """Evento de progreso de predicción."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    prediction_id: str
    title: str
    outcomes: List[PredictionOutcome]
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class PredictionLockEvent:
    """Evento de bloqueo de predicción."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    prediction_id: str
    title: str
    outcomes: List[PredictionOutcome]
    locked_at: datetime
    timestamp: datetime = datetime.now()


@dataclass(slots=True)
class PredictionEndEvent:
    """Evento de fin de predicción."""
    broadcaster_user_id: str
    broadcaster_name: str
    broadcaster_login: str
    prediction_id: str
    title: str
    winning_outcome_id: Optional[str]
    outcomes: List[PredictionOutcome]
    status: str  # "resolved", "canceled", etc.
    ended_at: datetime
    timestamp: datetime = datetime.now()