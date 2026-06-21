# services/eventsub/retry.py
"""
Manejo de reintentos con backoff exponencial.
"""

import time
import random
from typing import Callable, Any, Optional
from functools import wraps
from .exceptions import EventSubError


class RetryConfig:
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (EventSubError,)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


def with_retry(config: Optional[RetryConfig] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 1
            last_exception = None
            while attempt <= config.max_attempts:
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt == config.max_attempts:
                        break
                    delay = config.base_delay * (2 ** (attempt - 1))
                    if config.jitter:
                        delay += random.uniform(0, 0.5 * delay)
                    delay = min(delay, config.max_delay)
                    time.sleep(delay)
                    attempt += 1
            raise last_exception or EventSubError("Reintentos agotados")
        return wrapper
    return decorator


def retry_call(func: Callable, config: Optional[RetryConfig] = None, *args, **kwargs) -> Any:
    if config is None:
        config = RetryConfig()
    decorated = with_retry(config)(func)
    return decorated(*args, **kwargs)