"""MOD-BATCH-008 External API Rate Limiter implementation."""

from __future__ import annotations

import math
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field


DEFAULT_MAX_QPS = 2.0
HARD_CAP_QPS = 10.0
DEFAULT_MAX_RETRIES_ON_429 = 2


class RateLimiterConfigError(ValueError):
    """Raised when QPS / interval env values are invalid."""


def resolve_min_interval_seconds(
    *,
    max_qps: float | None = None,
    min_interval_ms: int | None = None,
    hard_cap_qps: float = HARD_CAP_QPS,
    default_max_qps: float = DEFAULT_MAX_QPS,
) -> tuple[float, float]:
    """Resolve (min_interval_seconds, effective_qps).

    Priority:
    1. explicit ``min_interval_ms``
    2. explicit ``max_qps``
    3. env ``RAKUTEN_MIN_INTERVAL_MS``
    4. env ``RAKUTEN_MAX_QPS`` / ``BATCH_EXTERNAL_API_MAX_QPS``
    5. ``default_max_qps`` (2)
    """

    if min_interval_ms is not None:
        interval_ms = int(min_interval_ms)
        if interval_ms <= 0:
            raise RateLimiterConfigError("min_interval_ms must be > 0")
        floor_ms = int(math.ceil(1000.0 / hard_cap_qps))
        if interval_ms < floor_ms:
            raise RateLimiterConfigError(
                f"min_interval_ms={interval_ms} would exceed hard-cap "
                f"{hard_cap_qps:g} QPS (minimum interval {floor_ms} ms)"
            )
        return interval_ms / 1000.0, 1000.0 / interval_ms

    if max_qps is None:
        raw_interval = os.environ.get("RAKUTEN_MIN_INTERVAL_MS")
        if raw_interval is not None and raw_interval.strip() != "":
            try:
                return resolve_min_interval_seconds(
                    min_interval_ms=int(raw_interval),
                    hard_cap_qps=hard_cap_qps,
                    default_max_qps=default_max_qps,
                )
            except ValueError as exc:
                if isinstance(exc, RateLimiterConfigError):
                    raise
                raise RateLimiterConfigError(
                    "RAKUTEN_MIN_INTERVAL_MS must be an integer"
                ) from exc

        raw_qps = (
            os.environ.get("RAKUTEN_MAX_QPS")
            or os.environ.get("BATCH_EXTERNAL_API_MAX_QPS")
            or str(default_max_qps)
        )
        try:
            max_qps = float(raw_qps)
        except ValueError as exc:
            raise RateLimiterConfigError("RAKUTEN_MAX_QPS must be a number") from exc

    if max_qps <= 0:
        raise RateLimiterConfigError("max_qps must be > 0")
    if max_qps > hard_cap_qps:
        raise RateLimiterConfigError(
            f"max_qps={max_qps:g} exceeds hard-cap {hard_cap_qps:g}"
        )

    interval_ms = int(math.ceil(1000.0 / max_qps))
    return interval_ms / 1000.0, max_qps


@dataclass
class ExternalApiRateLimiter:
    """Process-local min-interval rate limiter (MOD-BATCH-008).

    ``acquire()`` blocks until the minimum interval since the previous acquire
    has elapsed. ``wait_after_rate_limit()`` applies a longer pause after HTTP 429.
    """

    min_interval_seconds: float
    effective_qps: float
    hard_cap_qps: float = HARD_CAP_QPS
    max_retries_on_429: int = DEFAULT_MAX_RETRIES_ON_429
    backoff_seconds_on_429: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _last_acquire_at: float | None = field(default=None, repr=False)
    acquire_count: int = 0
    rate_limit_wait_count: int = 0

    @classmethod
    def from_env(
        cls,
        *,
        max_qps: float | None = None,
        min_interval_ms: int | None = None,
        max_retries_on_429: int = DEFAULT_MAX_RETRIES_ON_429,
    ) -> ExternalApiRateLimiter:
        interval_s, effective_qps = resolve_min_interval_seconds(
            max_qps=max_qps,
            min_interval_ms=min_interval_ms,
        )
        return cls(
            min_interval_seconds=interval_s,
            effective_qps=effective_qps,
            max_retries_on_429=max_retries_on_429,
        )

    def acquire(self, *, sleep: Callable[[float], None] | None = None) -> float:
        """Wait if needed, then mark a slot consumed. Returns waited seconds."""

        sleeper = sleep or time.sleep
        waited = 0.0
        with self._lock:
            now = time.monotonic()
            if self._last_acquire_at is not None:
                elapsed = now - self._last_acquire_at
                remaining = self.min_interval_seconds - elapsed
                if remaining > 0:
                    sleeper(remaining)
                    waited = remaining
                    now = time.monotonic()
            self._last_acquire_at = now
            self.acquire_count += 1
        return waited

    def wait_after_rate_limit(self, *, sleep: Callable[[float], None] | None = None) -> float:
        """Backoff after HTTP 429 before a retry acquire."""

        sleeper = sleep or time.sleep
        delay = self.backoff_seconds_on_429
        if delay is None:
            delay = max(self.min_interval_seconds * 2.0, 1.0)
        with self._lock:
            self.rate_limit_wait_count += 1
        sleeper(delay)
        return delay


def create_external_api_rate_limiter(
    *,
    max_qps: float | None = None,
    min_interval_ms: int | None = None,
    enabled: bool = True,
) -> ExternalApiRateLimiter | None:
    """Factory for MOD-BATCH-008. Returns ``None`` when disabled."""

    if not enabled:
        return None
    return ExternalApiRateLimiter.from_env(
        max_qps=max_qps,
        min_interval_ms=min_interval_ms,
    )
