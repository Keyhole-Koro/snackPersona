"""
Token-bucket rate limiter with async support.

Limits both requests-per-minute and tokens-per-minute.  When the bucket is
empty the caller is blocked (async sleep / sync sleep) until capacity
recovers.  Includes exponential-backoff retry logic for transient API errors.
"""

import asyncio
import time
import threading
from typing import Optional

from snackPersona.utils.logger import logger


class RateLimiter:
    """
    Thread-safe, async-compatible token-bucket rate limiter.

    Parameters
    ----------
    requests_per_minute : int
        Max requests allowed per minute.
    tokens_per_minute : int
        Max total tokens (prompt + completion) allowed per minute.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 150_000,
    ):
        self.rpm = requests_per_minute
        self.tpm = tokens_per_minute

        # Request bucket
        self._req_tokens = float(requests_per_minute)
        self._req_last_refill = time.monotonic()

        # Token bucket
        self._tok_tokens = float(tokens_per_minute)
        self._tok_last_refill = time.monotonic()

        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _refill(self) -> None:
        now = time.monotonic()

        # Requests
        elapsed = now - self._req_last_refill
        self._req_tokens = min(
            float(self.rpm),
            self._req_tokens + elapsed * (self.rpm / 60.0),
        )
        self._req_last_refill = now

        # Tokens
        elapsed_tok = now - self._tok_last_refill
        self._tok_tokens = min(
            float(self.tpm),
            self._tok_tokens + elapsed_tok * (self.tpm / 60.0),
        )
        self._tok_last_refill = now

    def _wait_time(self, estimated_tokens: int = 1) -> float:
        """Seconds to wait until both buckets have capacity."""
        waits: list[float] = []
        if self._req_tokens < 1.0:
            waits.append((1.0 - self._req_tokens) / (self.rpm / 60.0))
        if self._tok_tokens < estimated_tokens:
            needed = estimated_tokens - self._tok_tokens
            waits.append(needed / (self.tpm / 60.0))
        return max(waits) if waits else 0.0

    def _consume(self, estimated_tokens: int = 1) -> None:
        self._req_tokens -= 1.0
        self._tok_tokens -= estimated_tokens

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def acquire_sync(self, estimated_tokens: int = 500) -> None:
        """Block (sync) until the request can proceed."""
        while True:
            with self._lock:
                self._refill()
                wait = self._wait_time(estimated_tokens)
                if wait <= 0:
                    self._consume(estimated_tokens)
                    return
            logger.debug(f"[RateLimiter] Waiting {wait:.2f}s (sync)")
            time.sleep(min(wait, 5.0))

    async def acquire(self, estimated_tokens: int = 500) -> None:
        """Await until the request can proceed (async)."""
        while True:
            with self._lock:
                self._refill()
                wait = self._wait_time(estimated_tokens)
                if wait <= 0:
                    self._consume(estimated_tokens)
                    return
            logger.debug(f"[RateLimiter] Waiting {wait:.2f}s (async)")
            await asyncio.sleep(min(wait, 5.0))

    def report_actual_tokens(self, actual_tokens: int, estimated: int = 500) -> None:
        """
        Correct the token bucket after learning the actual token count.

        If actual < estimated we refund the difference; if actual > estimated
        we debit extra.
        """
        diff = actual_tokens - estimated
        if diff == 0:
            return
        with self._lock:
            self._tok_tokens -= diff


class NoOpRateLimiter(RateLimiter):
    """Rate limiter that never blocks."""

    def __init__(self):
        super().__init__(requests_per_minute=999_999, tokens_per_minute=999_999_999)

    def acquire_sync(self, estimated_tokens: int = 500) -> None:
        return

    async def acquire(self, estimated_tokens: int = 500) -> None:
        return
