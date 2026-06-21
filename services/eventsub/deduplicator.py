# services/eventsub/deduplicator.py
"""
Deduplicación de mensajes de EventSub.
"""

from collections import deque
from threading import Lock
from typing import Optional


class Deduplicator:
    def __init__(self, maxlen: int = 5000):
        self._maxlen = maxlen
        self._deque: deque[str] = deque(maxlen=maxlen)
        self._set: set[str] = set()
        self._lock = Lock()

    def is_duplicate(self, message_id: str) -> bool:
        with self._lock:
            if message_id in self._set:
                return True

            if len(self._deque) == self._maxlen:
                oldest = self._deque.popleft()
                self._set.discard(oldest)

            self._deque.append(message_id)
            self._set.add(message_id)
            return False

    def clear(self):
        with self._lock:
            self._deque.clear()
            self._set.clear()


deduplicator = Deduplicator()