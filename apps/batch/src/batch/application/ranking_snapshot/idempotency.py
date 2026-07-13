"""BATCH-002 helpers: object_key / content_hash / snapshot & signal idempotent keys."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

SOURCE_RAKUTEN = "rakuten"
SOURCE_API_RANKING = "item_ranking"


def build_ranking_raw_object_key(
    *,
    batch_run_id: str,
    api_call_log_id: str,
    fetched_on: date | None = None,
) -> str:
    """Build Object Storage key for ranking Raw JSON (仕様書 §10.2)."""

    day = (fetched_on or date.today()).isoformat()
    return (
        f"raw/rakuten/{SOURCE_API_RANKING}/dt={day}/"
        f"batch_run_id={batch_run_id}/{api_call_log_id}.json"
    )


def content_hash_for_payload(payload: dict[str, Any] | bytes) -> str:
    """SHA-256 hash of canonical JSON or raw bytes (no secret fields expected)."""

    if isinstance(payload, bytes):
        body = payload
    else:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    return hashlib.sha256(body).hexdigest()


def ranking_snapshot_idempotency_key(
    *,
    source: str,
    external_genre_id: str,
    period: str,
    last_build_date: str,
) -> tuple[str, str, str, str]:
    """Idempotency key for ranking_snapshot (仕様書 §11)."""

    return (source, external_genre_id, period, last_build_date)


def popularity_signal_idempotency_key(
    *,
    ranking_snapshot_id: str,
    rank: int,
) -> tuple[str, int]:
    """Idempotency key for item_popularity_signal (仕様書 §11)."""

    return (ranking_snapshot_id, rank)
