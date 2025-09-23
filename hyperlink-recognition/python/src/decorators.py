import secrets
import threading
from collections.abc import Callable
from functools import wraps
from time import monotonic
from typing import ParamSpec, TypeVar

from utils.coll_util import hash_value

_P = ParamSpec("_P")
_R = TypeVar("_R")


def ttl_cache(ttl: float) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """
    Time-to-live cache decorator with thread-safety and per-function storage.
    Adds a small jitter to TTL to avoid cache stampedes.
    Decorator that caches the result of a function call for a limited time.

    The first call to the decorated function stores its return value in a cache.
    Subsequent calls with the same arguments within the given time-to-live (TTL)
    will return the cached result instead of re-executing the function.
    Once the TTL expires, the function will be executed again and the cache updated.

    Args:
        ttl (float): Time-to-live in seconds for each cached result.

    Returns:
        A decorator that can be applied to a function to enable time-based caching.
    """

    def decorator(func: Callable[_P, _R]) -> Callable[_P, _R]:
        # Per-function cache and lock to ensure thread-safety
        lock = threading.RLock()
        cache: dict[tuple[str, int, int], tuple[float, _R]] = {}

        @wraps(func)
        def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            if ttl <= 0:
                return func(*args, **kwargs)

            now = monotonic()
            key = (func.__name__, hash_value(args), hash_value(kwargs))

            with lock:
                if entry := cache.get(key):
                    deadline, result = entry
                    if deadline > now:
                        return result

            # Execute outside the lock to avoid holding during user code
            result = func(*args, **kwargs)
            random_float = secrets.randbelow(1_000_000) / 1_000_000.0
            with lock:
                cache[key] = (now + random_float + ttl, result)
            return result

        def cache_clear() -> None:
            with lock:
                cache.clear()

        # Attach cache control to the wrapped function
        wrapped.cache_clear = cache_clear  # type: ignore[attr-defined]

        return wrapped

    return decorator
