"""
In-memory token blacklist for logout support.

Stores revoked JWT token IDs (jti) with automatic expiry cleanup.
In production with multiple workers, replace with Redis.
"""

import threading
import time
from datetime import UTC, datetime


class TokenBlacklist:
    """Thread-safe in-memory token blacklist with TTL-based cleanup."""

    def __init__(self):
        self._blacklist: dict[str, float] = {}  # token -> expiry timestamp
        self._lock = threading.Lock()

    def revoke(self, token: str, expires_at: float | None = None) -> None:
        """Add a token to the blacklist.

        Args:
            token: The JWT token string to revoke.
            expires_at: Unix timestamp when token expires (for auto-cleanup).
                       If None, token is blacklisted for 24 hours.
        """
        if expires_at is None:
            expires_at = time.time() + 86400  # 24 hours default
        with self._lock:
            self._blacklist[token] = expires_at

    def is_revoked(self, token: str) -> bool:
        """Check if a token has been revoked."""
        with self._lock:
            return token in self._blacklist

    def cleanup(self) -> int:
        """Remove expired entries. Returns number of entries removed."""
        now = time.time()
        with self._lock:
            expired = [t for t, exp in self._blacklist.items() if exp < now]
            for t in expired:
                del self._blacklist[t]
            return len(expired)

    def size(self) -> int:
        """Return current blacklist size."""
        return len(self._blacklist)


# Global singleton
token_blacklist = TokenBlacklist()
