"""
Rate limiting utilities that work with both tests and production.

The slowapi library doesn't work well with httpx's ASGI test client.
This module provides conditional rate limiting that can be disabled in tests.
"""

import os
from functools import wraps
from typing import Callable, Any

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def is_testing() -> bool:
    """Check if we're in test mode."""
    return os.getenv("TESTING", "false").lower() == "true"


# Singleton limiter instance (created lazily for production)
_limiter: Limiter | None = None


def get_limiter() -> Limiter | None:
    """Get or create the shared rate limiter instance.

    Returns None in test mode.
    """
    global _limiter
    if is_testing():
        return None
    if _limiter is None:
        _limiter = Limiter(key_func=get_remote_address)
    return _limiter


def rate_limit(limit_string: str):
    """
    Conditional rate limiting decorator.

    In test mode (TESTING=true), this is a no-op decorator.
    In production, it enforces rate limits via slowapi.

    Args:
        limit_string: Rate limit string (e.g., "5/minute")

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if is_testing():
                return await func(*args, **kwargs)

            # Extract Request from args/kwargs (FastAPI injects it)
            request: Request | None = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is not None:
                lim = get_limiter()
                if lim is not None:
                    # Use slowapi's internal check
                    lim._check_request_limit(request, func, [limit_string])

            return await func(*args, **kwargs)

        async_wrapper.__rate_limit_string__ = limit_string
        async_wrapper.__original_func__ = func

        return async_wrapper

    return decorator
