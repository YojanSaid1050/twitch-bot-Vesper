# services/eventsub/dispatcher.py
"""
Dispatcher de eventos: recibe un evento y lo envía al handler adecuado.
"""

import asyncio
import time
from typing import Dict, Any, Callable, Awaitable, Optional
from .statistics import stats_collector
from .metrics import metrics_collector, EventMetric
from .exceptions import HandlerNotFoundError
from utils.logger import get_logger

logger = get_logger(__name__)


class Dispatcher:
    def __init__(self):
        self._handlers: Dict[str, Callable[[Any], Awaitable[None]]] = {}

    def register(self, event_type: str, handler: Callable[[Any], Awaitable[None]]):
        self._handlers[event_type] = handler
        logger.debug(f"Handler registrado para {event_type}")

    async def dispatch(self, event_type: str, event_data: Any, message_id: str):
        start_time = time.time()
        try:
            handler = self._handlers.get(event_type)
            if handler is None:
                handler = self._handlers.get("generic")
                if handler is None:
                    stats_collector.increment("subscription_errors")
                    logger.warning(f"No hay handler para {event_type}")
                    return

            await handler(event_data)
            stats_collector.increment("events_processed")
            duration = (time.time() - start_time) * 1000
            metrics_collector.add(
                EventMetric(
                    event_type=event_type,
                    message_id=message_id,
                    status="success",
                    duration_ms=duration,
                )
            )
        except Exception as e:
            stats_collector.increment("subscription_errors")
            duration = (time.time() - start_time) * 1000
            metrics_collector.add(
                EventMetric(
                    event_type=event_type,
                    message_id=message_id,
                    status="error",
                    duration_ms=duration,
                    error=str(e),
                )
            )
            logger.error(f"Error en handler de {event_type}: {e}", exc_info=True)


dispatcher = Dispatcher()