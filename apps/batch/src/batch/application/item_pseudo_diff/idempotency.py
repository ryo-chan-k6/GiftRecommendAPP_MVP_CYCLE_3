"""BATCH-003 helpers: object_key / content_hash / fetch_cursor scope fingerprint."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

SOURCE_RAKUTEN = "rakuten"
SOURCE_API_ITEM_SEARCH = "item_search"


def build_item_search_raw_object_key(
    *,
    batch_run_id: str,
    api_call_log_id: str,
    fetched_on: date | None = None,
) -> str:
    """Build Object Storage key for item_search Raw JSON (仕様書 §10.2)."""

    day = (fetched_on or date.today()).isoformat()
    return (
        f"raw/rakuten/{SOURCE_API_ITEM_SEARCH}/dt={day}/"
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


def cursor_scope_fingerprint(
    *,
    cursor_type: str,
    target_external_genre_id: str | None,
    scope: dict[str, Any],
) -> str:
    """Fingerprint for fetch_cursor UNIQUE scope (テーブル定義書 §7.1 相当の簡易実装)."""

    genre_part = target_external_genre_id or ""
    scope_json = json.dumps(scope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    material = f"{genre_part}{cursor_type}{scope_json}"
    return hashlib.md5(material.encode("utf-8")).hexdigest()
