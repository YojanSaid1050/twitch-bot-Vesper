import time
import requests
from typing import Optional, Tuple
from threading import Lock

class TokenValidator:
    _cache = {}
    _cache_ttl = 60
    _lock = Lock()

    @classmethod
    def validate(cls, token: str) -> Tuple[bool, Optional[int]]:
        if not token:
            return False, None

        with cls._lock:
            if token in cls._cache:
                cached_time, expires_at = cls._cache[token]
                if time.time() - cached_time < cls._cache_ttl:
                    if expires_at and expires_at > time.time():
                        return True, int(expires_at - time.time())
                    elif expires_at is None:
                        return True, None
                    else:
                        del cls._cache[token]

        try:
            response = requests.get(
                "https://id.twitch.tv/oauth2/validate",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                expires_in = data.get("expires_in", 0)
                expires_at = time.time() + expires_in
                with cls._lock:
                    cls._cache[token] = (time.time(), expires_at)
                return True, expires_in
            else:
                with cls._lock:
                    cls._cache[token] = (time.time(), None)
                return False, None
        except Exception:
            with cls._lock:
                cls._cache[token] = (time.time(), None)
            return False, None

    @classmethod
    def invalidate(cls, token: str):
        with cls._lock:
            if token in cls._cache:
                del cls._cache[token]