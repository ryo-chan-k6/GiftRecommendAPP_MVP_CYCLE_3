"""Normalized Payload Builder / Hash Calculator (仕様書 §9.5 / 外部連携 §6.4)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _as_str_list(value: Any) -> list[str]:
    """Normalize image URL arrays / attributeIds to a stable string list."""

    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if not isinstance(value, (list, tuple)):
        return [str(value)]

    urls: list[str] = []
    for entry in value:
        if entry is None:
            continue
        if isinstance(entry, str):
            if entry:
                urls.append(entry)
            continue
        if isinstance(entry, dict):
            for key in ("imageUrl", "image_url", "url"):
                raw = entry.get(key)
                if isinstance(raw, str) and raw:
                    urls.append(raw)
                    break
            continue
        urls.append(str(entry))
    return urls


def build_normalized_payload(item: dict[str, Any]) -> dict[str, Any]:
    """Build canonical normalized payload for hash (外部商品データ連携設計書 §6.4).

    NULL / 欠落は ``None``、配列は空を許す。キー順序は固定（sort_keys で canonical JSON）。
    """

    return {
        "attributeIds": _as_str_list(item.get("attributeIds")),
        "availability": item.get("availability"),
        "catchcopy": item.get("catchcopy"),
        "genreId": item.get("genreId"),
        "itemCaption": item.get("itemCaption"),
        "itemCode": item.get("itemCode"),
        "itemName": item.get("itemName"),
        "itemPrice": item.get("itemPrice"),
        "itemUrl": item.get("itemUrl"),
        "mediumImageUrls": _as_str_list(item.get("mediumImageUrls")),
        "reviewAverage": item.get("reviewAverage"),
        "reviewCount": item.get("reviewCount"),
        "shopCode": item.get("shopCode"),
        "smallImageUrls": _as_str_list(item.get("smallImageUrls")),
    }


def compute_normalized_hash(payload: dict[str, Any]) -> str:
    """SHA-256 hex of canonical JSON (separators compact, sort_keys)."""

    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(body).hexdigest()


def content_hash_for_bytes(body: bytes) -> str:
    """SHA-256 hex of Raw Object body (content_hash 照合用)."""

    return hashlib.sha256(body).hexdigest()
