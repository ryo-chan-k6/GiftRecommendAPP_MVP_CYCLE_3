"""Staging Transformer: Raw JSON → staging_* 候補行."""

from __future__ import annotations

import json
import re
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
    StagingGenreRow,
    StagingItemImageRow,
    StagingItemRow,
    StagingRankingSignalRow,
)

SOURCE_API_ITEM_SEARCH = "item_search"
SOURCE_API_ITEM_RANKING = "item_ranking"
SOURCE_API_GENRE_SEARCH = "genre_search"
SOURCE_API_ATTRIBUTE_SEARCH = "attribute_search"

_OFFSET_COMPACT = re.compile(r"([+-])(\d{2})(\d{2})$")


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


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_last_build_date(value: Any) -> datetime:
    """Parse Rakuten lastBuildDate into aware datetime (accepts ``+0900``)."""

    text = _as_str(value)
    if not text:
        raise StagingTransformError(
            code="GRS-BAT-004",
            message="invalid ranking payload: missing lastBuildDate",
        )
    normalized = _OFFSET_COMPACT.sub(r"\1\2:\3", text)
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise StagingTransformError(
            code="GRS-BAT-004",
            message=f"invalid ranking payload: lastBuildDate parse failed: {exc}",
        ) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


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


def transform_item_ranking(
    *,
    meta: RawMetadataSeed,
    payload: dict[str, Any],
    staged_at: datetime | None = None,
) -> RawTransformResult:
    """item_ranking Raw → staging_ranking_signal 候補（薄い自前 parse）。"""

    now = staged_at or datetime.now(UTC)
    last_build_date = _parse_last_build_date(payload.get("lastBuildDate"))
    external_genre_id = _to_int(payload.get("genreId"), default=0)
    if external_genre_id is None:
        external_genre_id = 0
    period = _as_str(payload.get("period")) or "daily"

    items_raw = payload.get("Items")
    if not isinstance(items_raw, list):
        raise StagingTransformError(
            code="GRS-BAT-004",
            message="invalid ranking payload: missing Items list",
        )
    if not items_raw:
        raise StagingTransformError(
            code="GRS-BAT-004",
            message="invalid ranking payload: empty Items",
        )

    rows: list[StagingRankingSignalRow] = []
    for entry in items_raw:
        item = _unwrap_item(entry)
        if item is None:
            continue
        rank = _to_int(item.get("rank"))
        item_code = _as_str(item.get("itemCode"))
        if rank is None or not item_code:
            raise StagingTransformError(
                code="GRS-BAT-004",
                message="invalid ranking payload: item missing rank/itemCode",
            )
        rows.append(
            StagingRankingSignalRow(
                raw_metadata_id=meta.raw_metadata_id,
                external_item_code=item_code,
                external_genre_id=external_genre_id,
                rank=rank,
                period=period,
                last_build_date=last_build_date,
                staged_at=now,
            )
        )

    if not rows:
        raise StagingTransformError(
            code="GRS-BAT-004",
            message="invalid ranking payload: empty Items",
        )

    return RawTransformResult(
        raw_metadata_id=meta.raw_metadata_id,
        source_api=SOURCE_API_ITEM_RANKING,
        ranking_rows=tuple(rows),
    )


def _genre_name(node: dict[str, Any]) -> str | None:
    return _as_str(node.get("jaName")) or _as_str(node.get("genreName"))


def _genre_level(node: dict[str, Any]) -> int | None:
    level = _to_int(node.get("level"))
    if level is not None:
        return level
    return _to_int(node.get("genreLevel"))


def _node_is_leaf(node: dict[str, Any], *, fallback: bool) -> bool:
    nested = node.get("children")
    if isinstance(nested, list):
        return len(nested) == 0
    return fallback


def transform_genre_search(
    *,
    meta: RawMetadataSeed,
    payload: dict[str, Any],
    staged_at: datetime | None = None,
) -> RawTransformResult:
    """genre_search Raw → staging_genre 候補（genre + children/ancestors/siblings）。"""

    now = staged_at or datetime.now(UTC)
    genre_obj = payload.get("genre")
    if not isinstance(genre_obj, dict):
        raise StagingTransformError(
            code="GRS-BAT-004",
            message="invalid genre payload: missing genre object",
        )

    top_children = payload.get("children")
    top_children_list = top_children if isinstance(top_children, list) else []
    source = meta.source or "rakuten"

    # (node, is_leaf_fallback) — root uses top-level children emptiness
    candidates: list[tuple[dict[str, Any], bool]] = [
        (genre_obj, len(top_children_list) == 0),
    ]
    for key in ("children", "ancestors", "siblings"):
        arr = payload.get(key)
        if not isinstance(arr, list):
            continue
        for entry in arr:
            if isinstance(entry, dict):
                candidates.append((entry, True))

    rows_by_id: dict[int, StagingGenreRow] = {}
    for node, leaf_fallback in candidates:
        genre_id = _to_int(node.get("genreId"))
        name = _genre_name(node)
        if genre_id is None or not name:
            raise StagingTransformError(
                code="GRS-BAT-004",
                message="invalid genre payload: node missing genreId/(jaName|genreName)",
            )
        level = _genre_level(node)
        if level is None:
            raise StagingTransformError(
                code="GRS-BAT-004",
                message=f"invalid genre payload: genreId={genre_id} missing level/genreLevel",
            )
        parent = _to_int(node.get("parentGenreId"))
        if genre_id not in rows_by_id:
            rows_by_id[genre_id] = StagingGenreRow(
                raw_metadata_id=meta.raw_metadata_id,
                source=source,
                external_genre_id=genre_id,
                genre_name=name,
                parent_external_genre_id=parent,
                genre_level=level,
                is_leaf=_node_is_leaf(node, fallback=leaf_fallback),
                staged_at=now,
            )

    if not rows_by_id:
        raise StagingTransformError(
            code="GRS-BAT-004",
            message="invalid genre payload: no genre rows",
        )

    return RawTransformResult(
        raw_metadata_id=meta.raw_metadata_id,
        source_api=SOURCE_API_GENRE_SEARCH,
        genre_rows=tuple(rows_by_id.values()),
    )


def transform_raw(
    *,
    meta: RawMetadataSeed,
    body: bytes,
    staged_at: datetime | None = None,
) -> RawTransformResult:
    """source_api に応じて Staging 候補へ変換."""

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

    if source_api == SOURCE_API_ITEM_RANKING:
        return transform_item_ranking(meta=meta, payload=payload, staged_at=staged_at)

    if source_api == SOURCE_API_GENRE_SEARCH:
        return transform_genre_search(meta=meta, payload=payload, staged_at=staged_at)

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
