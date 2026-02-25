"""
In-memory token blacklist for logout support.

Stores revoked JWT tokens with automatic expiry cleanup.

Limitation: In-memory storage does NOT work across multiple workers/processes.
For production with multiple workers, set REDIS_URL in environment and this
module will automatically use Redis instead.
"""

import threading
import time
from datetime import UTC, datetime

from loguru import logger


class TokenBlacklist:
    """Thread-safe in-memory token blacklist with TTL-based auto-cleanup."""

    # Run cleanup every 5 minutes
    _CLEANUP_INTERVAL = 300

    def __init__(self):
        self._blacklist: dict[str, float] = {}  # token -> expiry timestamp
        self._lock = threading.Lock()
        self._cleanup_timer: threading.Timer | None = None
        self._start_cleanup_loop()

    def _start_cleanup_loop(self) -> None:
        """Start the periodic cleanup background timer."""
        self._cleanup_timer = threading.Timer(self._CLEANUP_INTERVAL, self._periodic_cleanup)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

    def _periodic_cleanup(self) -> None:
        """Periodic cleanup callback."""
        try:
            removed = self.cleanup()
            if removed:
                logger.debug(f"Token blacklist cleanup: removed {removed} expired entries")
        except Exception as e:
            logger.error(f"Token blacklist cleanup error: {e}")
        finally:
            self._start_cleanup_loop()

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
            exp = self._blacklist.get(token)
            if exp is None:
                return False
            # Lazily remove expired entry on access
            if exp < time.time():
                del self._blacklist[token]
                return False
            return True

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

    def stop(self) -> None:
        """Stop the cleanup timer (for graceful shutdown)."""
        if self._cleanup_timer is not None:
            self._cleanup_timer.cancel()
            self._cleanup_timer = None


# Global singleton
token_blacklist = TokenBlacklist()
