# services/eventsub/__init__.py
"""
EventSub - Sistema modular de suscripciones para Twitch EventSub.
"""

from .manager import EventSubManager, manager
from .dispatcher import Dispatcher, dispatcher
from .webhook import WebhookHandler, webhook_handler
from .deduplicator import Deduplicator, deduplicator
from .statistics import StatisticsCollector, stats_collector, EventSubStatistics
from .metrics import MetricsCollector, metrics_collector, EventMetric
from .event_bus import EventBus, event_bus, Event
from .exceptions import *
from .definitions import EventDefinition, ScopeOwner, TransportType, TokenInfo, Subscription, WebhookPayload, EventResult
from .registry import EVENTS
from .subscriptions import subscription_manager, SubscriptionManager
from .cleanup import cleaner, SubscriptionCleaner
from .scopes import scope_validator, ScopeValidator
from .tokens import TokenValidator
from .conditions import condition_builder, ConditionBuilder

__all__ = [
    # Manager
    "EventSubManager",
    "manager",
    # Dispatcher
    "Dispatcher",
    "dispatcher",
    # Webhook
    "WebhookHandler",
    "webhook_handler",
    # Deduplicator
    "Deduplicator",
    "deduplicator",
    # Statistics
    "StatisticsCollector",
    "stats_collector",
    "EventSubStatistics",
    # Metrics
    "MetricsCollector",
    "metrics_collector",
    "EventMetric",
    # Event Bus
    "EventBus",
    "event_bus",
    "Event",
    # Exceptions
    "EventSubError",
    "InvalidScopeError",
    "InvalidConditionError",
    "WebhookUnavailableError",
    "SubscriptionError",
    "TokenMismatchError",
    "DuplicateEventError",
    "HandlerNotFoundError",
    "TransportNotSupportedError",
    "CleanupError",
    # Definitions
    "EventDefinition",
    "ScopeOwner",
    "TransportType",
    "TokenInfo",
    "Subscription",
    "WebhookPayload",
    "EventResult",
    # Registry
    "EVENTS",
    # Subscriptions
    "subscription_manager",
    "SubscriptionManager",
    # Cleanup
    "cleaner",
    "SubscriptionCleaner",
    # Scopes
    "scope_validator",
    "ScopeValidator",
    # Tokens
    "TokenValidator",
    # Conditions
    "condition_builder",
    "ConditionBuilder",
]