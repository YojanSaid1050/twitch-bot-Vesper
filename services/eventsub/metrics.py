# services/eventsub/metrics.py
"""
Métricas para el dashboard.
"""

from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime


@dataclass(slots=True)
class EventMetric:
    event_type: str
    message_id: str
    status: str
    duration_ms: float
    processed_at: datetime = field(default_factory=datetime.now)
    error: str = ""


class MetricsCollector:
    def __init__(self, max_metrics: int = 1000):
        self._metrics: list[EventMetric] = []
        self._max = max_metrics

    def add(self, metric: EventMetric):
        self._metrics.append(metric)
        if len(self._metrics) > self._max:
            self._metrics = self._metrics[-self._max:]

    def get_recent(self, limit: int = 100) -> list[EventMetric]:
        return self._metrics[-limit:]

    def clear(self):
        self._metrics.clear()


metrics_collector = MetricsCollector()