# services/eventsub/cache.py
"""
Caché centralizada para tokens, scopes, etc.
"""

import time
from typing import Dict, Optional, Any
from threading import Lock


class EventSubCache:
    """Caché simple con TTL."""

    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry["expires_at"] < time.time():
                del self._cache[key]
                return None
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        if ttl is None:
            ttl = self._default_ttl
        expires_at = time.time() + ttl
        with self._lock:
            self._cache[key] = {"value": value, "expires_at": expires_at}

    def invalidate(self, key: str):
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()


cache = EventSubCache()