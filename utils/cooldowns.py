"""
Gestor de cooldowns en memoria (global por comando y por usuario).

No depende de Twitch ni de la base de datos para poder probarse aislado.
"""

import time
from typing import Callable, Dict, Tuple


class CooldownManager:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._global: Dict[str, float] = {}
        self._per_user: Dict[Tuple[str, str], float] = {}

    def remaining(self, key: str, global_seconds: float = 0, user_id: str = None, user_seconds: float = 0) -> float:
        """Segundos que faltan para poder usar `key` (0 si ya se puede)."""
        now = self._clock()
        left = 0.0
        if global_seconds > 0 and key in self._global:
            left = max(left, self._global[key] + global_seconds - now)
        if user_id and user_seconds > 0 and (key, user_id) in self._per_user:
            left = max(left, self._per_user[(key, user_id)] + user_seconds - now)
        return max(0.0, left)

    def trigger(self, key: str, user_id: str = None) -> None:
        now = self._clock()
        self._global[key] = now
        if user_id:
            self._per_user[(key, user_id)] = now

    def try_use(self, key: str, global_seconds: float = 0, user_id: str = None, user_seconds: float = 0) -> bool:
        """Si no hay cooldown activo lo registra y devuelve True; si no, False."""
        if self.remaining(key, global_seconds, user_id, user_seconds) > 0:
            return False
        self.trigger(key, user_id)
        return True

    def reset(self, key: str = None) -> None:
        if key is None:
            self._global.clear()
            self._per_user.clear()
            return
        self._global.pop(key, None)
        for k in [k for k in self._per_user if k[0] == key]:
            del self._per_user[k]


# Instancia global compartida por los comandos
cooldowns = CooldownManager()
