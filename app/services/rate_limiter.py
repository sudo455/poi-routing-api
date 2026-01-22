"""Rate limiting service with 418 I'm a teapot responses."""
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock


class RateLimiter:
    """In-memory rate limiter with sliding window."""

    def __init__(self, window_seconds: int = 60, block_seconds: int = 180):
        """
        Initialize rate limiter.

        Args:
            window_seconds: Time window for counting requests (default: 60s)
            block_seconds: How long to block after exceeding limit (default: 180s / 3 min)
        """
        self.window_seconds = window_seconds
        self.block_seconds = block_seconds
        self._requests: dict[str, list[datetime]] = defaultdict(list)
        self._blocked_until: dict[str, datetime] = {}
        self._lock = Lock()
        self._teapot_messages = self._load_teapot_messages()

    def _load_teapot_messages(self) -> list[str]:
        """Load teapot messages from JSON file."""
        try:
            path = Path(__file__).parent.parent / 'teapot_messages.json'
            with open(path) as f:
                data = json.load(f)
                return data.get('messages', [])
        except (FileNotFoundError, json.JSONDecodeError):
            return [
                "I'm a teapot. Rate limit exceeded.",
                "Too many requests. Try again in {seconds} seconds."
            ]

    def get_teapot_message(self, retry_after: int) -> str:
        """Get a random teapot message with retry time filled in."""
        message = random.choice(self._teapot_messages)
        return message.format(seconds=retry_after)

    def check(self, user_id: str, user_rate_limit: int) -> tuple[bool, int]:
        """
        Check if user is rate limited.

        Args:
            user_id: The user's ID
            user_rate_limit: User's configured requests per minute limit

        Returns:
            Tuple of (allowed: bool, retry_after: int)
            - allowed: True if request is allowed
            - retry_after: Seconds until rate limit resets (0 if allowed)
        """
        with self._lock:
            now = datetime.now(timezone.utc)

            # Check if user is blocked
            if user_id in self._blocked_until:
                blocked_until = self._blocked_until[user_id]
                if now < blocked_until:
                    retry_after = int((blocked_until - now).total_seconds())
                    return False, retry_after
                else:
                    # Block expired, remove it
                    del self._blocked_until[user_id]
                    self._requests[user_id] = []

            # Clean old requests outside the window
            window_start = now - timedelta(seconds=self.window_seconds)
            self._requests[user_id] = [
                ts for ts in self._requests[user_id]
                if ts > window_start
            ]

            # Check if over limit
            if len(self._requests[user_id]) >= user_rate_limit:
                # Block the user
                self._blocked_until[user_id] = now + timedelta(seconds=self.block_seconds)
                return False, self.block_seconds

            # Record this request
            self._requests[user_id].append(now)
            return True, 0

    def get_remaining(self, user_id: str, user_rate_limit: int) -> int:
        """Get remaining requests for user in current window."""
        with self._lock:
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(seconds=self.window_seconds)

            # Clean and count
            self._requests[user_id] = [
                ts for ts in self._requests[user_id]
                if ts > window_start
            ]

            return max(0, user_rate_limit - len(self._requests[user_id]))

    def reset(self, user_id: str) -> None:
        """Reset rate limit for a user (admin function)."""
        with self._lock:
            if user_id in self._requests:
                del self._requests[user_id]
            if user_id in self._blocked_until:
                del self._blocked_until[user_id]


# Global rate limiter instance
rate_limiter = RateLimiter()
