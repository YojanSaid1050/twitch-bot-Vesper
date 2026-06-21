# services/eventsub/event_bus.py
"""
Event Bus interno para comunicación desacoplada entre módulos.
"""

from typing import Dict, List, Callable, Any, Awaitable
from dataclasses import dataclass, field
import asyncio
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class Event:
    """Evento interno del sistema."""
    type: str
    payload: Any
    source: str = "eventsub"
    timestamp: float = field(default_factory=lambda: __import__('time').time())


class EventBus:
    """Bus de eventos interno para comunicación entre módulos."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {}
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        """Suscribe un handler a un tipo de evento."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Handler suscrito a {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        """Cancela la suscripción de un handler."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    async def publish(self, event: Event):
        """
        Publica un evento a todos los suscriptores.
        """
        async with self._lock:
            handlers = self._subscribers.get(event.type, [])
            # También notificar a suscriptores de "all"
            all_handlers = self._subscribers.get("all", [])
            all_handlers.extend(handlers)

        if not all_handlers:
            return

        for handler in all_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error en handler para {event.type}: {e}", exc_info=True)

    def clear(self):
        """Limpia todos los suscriptores."""
        self._subscribers.clear()


# Instancia global
event_bus = EventBus()