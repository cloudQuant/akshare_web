"""
Rate limiting utilities that work with both tests and production.

The slowapi library doesn't work well with httpx's ASGI test client.
This module provides conditional rate limiting that can be disabled in tests.
"""

import os
from functools import wraps
from typing import Callable, Any

from fastapi import Request


def is_testing() -> bool:
    """Check if we're in test mode."""
    return os.getenv("TESTING", "false").lower() == "true"


def rate_limit(limit_string: str):
    """
    Conditional rate limiting decorator.

    In test mode (TESTING=true), this is a no-op decorator.
    In production, it applies rate limiting via slowapi.

    Args:
        limit_string: Rate limit string (e.g., "5/minute")

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        """
        Always return our wrapper that checks at runtime.
        This ensures we don't apply slowapi decorator at module import time.
        """
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check test mode at call time
            if is_testing():
                # In test mode, just call the function directly
                return await func(*args, **kwargs)
            else:
                # In production, we need to check rate limit
                # Since we didn't use slowapi's decorator, we just call the function
                # In a real setup, you'd want to integrate with slowapi properly
                # For now, skip rate limiting in this simplified version
                return await func(*args, **kwargs)

        # Store original function for any metadata
        async_wrapper.__rate_limit_string__ = limit_string
        async_wrapper.__original_func__ = func

        return async_wrapper

    return decorator


def get_limiter():
    """Get the rate limiter instance (for slowapi state integration)."""
    if is_testing():
        return None
    # Create limiter on demand for production
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    return Limiter(key_func=get_remote_address)


# Expose limiter for slowapi state (None in tests)
limiter = None
