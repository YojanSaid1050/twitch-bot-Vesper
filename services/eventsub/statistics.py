# services/eventsub/statistics.py
"""
Estadísticas del sistema EventSub.
"""

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Any


@dataclass(slots=True)
class EventSubStatistics:
    subscriptions_created: int = 0
    subscriptions_skipped: int = 0
    subscriptions_failed: int = 0
    subscriptions_recreated: int = 0
    subscriptions_failed_scopes: int = 0
    subscriptions_failed_token: int = 0
    events_processed: int = 0
    events_duplicated: int = 0
    webhook_verifications: int = 0
    webhook_failures: int = 0
    retry_attempts: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "subscriptions_created": self.subscriptions_created,
            "subscriptions_skipped": self.subscriptions_skipped,
            "subscriptions_failed": self.subscriptions_failed,
            "subscriptions_recreated": self.subscriptions_recreated,
            "subscriptions_failed_scopes": self.subscriptions_failed_scopes,
            "subscriptions_failed_token": self.subscriptions_failed_token,
            "events_processed": self.events_processed,
            "events_duplicated": self.events_duplicated,
            "webhook_verifications": self.webhook_verifications,
            "webhook_failures": self.webhook_failures,
            "retry_attempts": self.retry_attempts,
        }


class StatisticsCollector:
    def __init__(self):
        self._stats = EventSubStatistics()
        self._lock = Lock()

    def increment(self, attr: str, amount: int = 1):
        with self._lock:
            if hasattr(self._stats, attr):
                current = getattr(self._stats, attr)
                setattr(self._stats, attr, current + amount)

    def get(self) -> EventSubStatistics:
        with self._lock:
            return self._stats

    def reset(self):
        with self._lock:
            self._stats = EventSubStatistics()


stats_collector = StatisticsCollector()