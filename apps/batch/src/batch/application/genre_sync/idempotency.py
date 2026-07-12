"""BATCH-001 helpers: object_key / content_hash / idempotent upsert keys."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

SOURCE_RAKUTEN = "rakuten"
SOURCE_API_GENRE = "genre"


def build_genre_raw_object_key(
    *,
    batch_run_id: str,
    api_call_log_id: str,
    fetched_on: date | None = None,
) -> str:
    """Build Object Storage key for genre Raw JSON (バッチ設計方針書 §9.3)."""

    day = (fetched_on or date.today()).isoformat()
    return (
        f"raw/rakuten/{SOURCE_API_GENRE}/dt={day}/"
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


def external_genre_idempotency_key(*, source: str, external_genre_id: str) -> tuple[str, str]:
    """Idempotency key for external_genre / staging_genre upsert."""

    return (source, external_genre_id)
