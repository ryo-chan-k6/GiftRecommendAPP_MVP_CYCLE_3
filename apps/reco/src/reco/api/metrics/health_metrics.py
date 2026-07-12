"""API-INT-001 health metric recording (reco_health_check_count)."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger("reco.api.health.metric")

METRIC_NAME = "reco_health_check_count"

_lock = Lock()
_counts: Counter[str] = Counter()


@dataclass(frozen=True)
class HealthMetricEvent:
    """In-process observation for unit tests / local observability."""

    result: str
    http_status: int
    trace_id: str | None = None
    request_id: str | None = None


_events: list[HealthMetricEvent] = []


def reset_health_metrics() -> None:
    """Clear in-process counters (unit tests)."""
    with _lock:
        _counts.clear()
        _events.clear()


def get_health_metric_count(result: str | None = None) -> int:
    """Return recorded count. If result is None, return total."""
    with _lock:
        if result is None:
            return int(sum(_counts.values()))
        return int(_counts[result])


def get_health_metric_events() -> list[HealthMetricEvent]:
    with _lock:
        return list(_events)


def record_reco_health_check(
    *,
    result: str,
    http_status: int,
    trace_id: str | None = None,
    request_id: str | None = None,
) -> None:
    """Increment reco_health_check_count with a result label.

    MOD-RECO-025 MetricLogger は Run 単位のため、health はエンドポイント層の
    軽量カウンタ + 構造化ログで境界を満たす（実装仕様書 §8）。
    """
    event = HealthMetricEvent(
        result=result,
        http_status=http_status,
        trace_id=trace_id,
        request_id=request_id,
    )
    with _lock:
        _counts[result] += 1
        _events.append(event)

    logger.info(
        "%s result=%s http_status=%s trace_id=%s request_id=%s",
        METRIC_NAME,
        result,
        http_status,
        trace_id or "",
        request_id or "",
    )
