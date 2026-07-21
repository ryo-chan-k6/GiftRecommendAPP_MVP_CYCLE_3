"""Staging Transformer: Raw JSON → staging_* 候補行."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from batch.application.raw_staging.hashing import (
    build_normalized_payload,
    compute_normalized_hash,
)
from batch.application.raw_staging.models import (
    ItemTransformBundle,
    RawMetadataSeed,
    RawTransformResult,
    StagingItemImageRow,
    StagingItemRow,
)

SOURCE_API_ITEM_SEARCH = "item_search"
SOURCE_API_ITEM_RANKING = "item_ranking"
SOURCE_API_GENRE_SEARCH = "genre_search"
SOURCE_API_ATTRIBUTE_SEARCH = "attribute_search"


class StagingTransformError(Exception):
    """Raised when transform fails (GRS-BAT-004)."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _unwrap_item(entry: Any) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None
    nested = entry.get("Item")
    if isinstance(nested, dict):
        return nested
    return entry


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items_raw = payload.get("Items")
    if not isinstance(items_raw, list):
        return []
    result: list[dict[str, Any]] = []
    for entry in items_raw:
        item = _unwrap_item(entry)
        if item is not None:
            result.append(item)
    return result


def _extract_image_urls(item: dict[str, Any], key: str) -> list[str]:
    value = item.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if not isinstance(value, (list, tuple)):
        return []
    urls: list[str] = []
    for entry in value:
        if isinstance(entry, str) and entry:
            urls.append(entry)
        elif isinstance(entry, dict):
            for url_key in ("imageUrl", "image_url", "url"):
                raw = entry.get(url_key)
                if isinstance(raw, str) and raw:
                    urls.append(raw)
                    break
    return urls


def _to_int(value: Any, *, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_images(
    *,
    raw_metadata_id: str,
    external_item_code: str,
    item: dict[str, Any],
    staged_at: datetime,
) -> tuple[StagingItemImageRow, ...]:
    medium = _extract_image_urls(item, "mediumImageUrls")
    small = _extract_image_urls(item, "smallImageUrls")
    rows: list[StagingItemImageRow] = []

    primary_set = False
    for order, url in enumerate(medium):
        is_primary = not primary_set and order == 0
        if is_primary:
            primary_set = True
        rows.append(
            StagingItemImageRow(
                raw_metadata_id=raw_metadata_id,
                external_item_code=external_item_code,
                image_url=url,
                image_size_type="medium",
                display_order=order,
                is_primary_candidate=is_primary,
                staged_at=staged_at,
            )
        )
    for order, url in enumerate(small):
        is_primary = not primary_set and order == 0
        if is_primary:
            primary_set = True
        rows.append(
            StagingItemImageRow(
                raw_metadata_id=raw_metadata_id,
                external_item_code=external_item_code,
                image_url=url,
                image_size_type="small",
                display_order=order,
                is_primary_candidate=is_primary,
                staged_at=staged_at,
            )
        )
    return tuple(rows)


def transform_item_search(
    *,
    meta: RawMetadataSeed,
    payload: dict[str, Any],
    staged_at: datetime | None = None,
) -> RawTransformResult:
    """item_search Raw → staging_item + staging_item_image 候補."""

    now = staged_at or datetime.now(UTC)
    bundles: list[ItemTransformBundle] = []
    for item in _extract_items(payload):
        code = item.get("itemCode")
        if code is None:
            continue
        external_item_code = str(code)
        normalized = build_normalized_payload(item)
        normalized_hash = compute_normalized_hash(normalized)
        price = _to_int(item.get("itemPrice"), default=0)
        if price is None:
            price = 0
        row = StagingItemRow(
            raw_metadata_id=meta.raw_metadata_id,
            source=meta.source or "rakuten",
            external_item_code=external_item_code,
            item_name=str(item.get("itemName") or ""),
            item_caption=str(item["itemCaption"]) if item.get("itemCaption") is not None else None,
            catchcopy=str(item["catchcopy"]) if item.get("catchcopy") is not None else None,
            price=price,
            item_url=str(item.get("itemUrl") or ""),
            external_genre_id=_to_int(item.get("genreId")),
            shop_code=str(item["shopCode"]) if item.get("shopCode") is not None else None,
            availability=_to_int(item.get("availability")),
            review_average=_to_float(item.get("reviewAverage")),
            review_count=_to_int(item.get("reviewCount")),
            normalized_hash=normalized_hash,
            diff_status=None,
            staged_at=now,
        )
        images = _build_images(
            raw_metadata_id=meta.raw_metadata_id,
            external_item_code=external_item_code,
            item=item,
            staged_at=now,
        )
        bundles.append(
            ItemTransformBundle(item=row, images=images, normalized_payload=normalized)
        )

    return RawTransformResult(
        raw_metadata_id=meta.raw_metadata_id,
        source_api=SOURCE_API_ITEM_SEARCH,
        items=tuple(bundles),
    )


def transform_raw(
    *,
    meta: RawMetadataSeed,
    body: bytes,
    staged_at: datetime | None = None,
) -> RawTransformResult:
    """source_api に応じて Staging 候補へ変換（ranking/genre は MVP stub）。"""

    source_api = meta.source_api
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StagingTransformError(
            code="GRS-BAT-004",
            message=f"invalid raw json: {exc}",
        ) from exc

    if not isinstance(payload, dict):
        raise StagingTransformError(code="GRS-BAT-004", message="raw json root must be object")

    if source_api == SOURCE_API_ITEM_SEARCH:
        return transform_item_search(meta=meta, payload=payload, staged_at=staged_at)

    if source_api in {SOURCE_API_ITEM_RANKING, SOURCE_API_GENRE_SEARCH}:
        # MVP: 再処理オプション。本 Task では skip stub（item_search 主経路を優先）
        return RawTransformResult(
            raw_metadata_id=meta.raw_metadata_id,
            source_api=source_api,
            items=(),
            skipped=True,
            skip_reason=f"{source_api} stub skipped (MVP item_search path)",
        )

    if source_api == SOURCE_API_ATTRIBUTE_SEARCH:
        return RawTransformResult(
            raw_metadata_id=meta.raw_metadata_id,
            source_api=source_api,
            items=(),
            skipped=True,
            skip_reason="attribute_search out of scope",
        )

    raise StagingTransformError(
        code="GRS-BAT-004",
        message=f"unsupported source_api: {source_api}",
    )
