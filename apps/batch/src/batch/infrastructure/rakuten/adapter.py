"""Rakuten genre / ranking response adapters for BATCH-001 / BATCH-002."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from batch.infrastructure.rakuten.client import (
    RakutenGenre,
    RakutenGenreApiError,
    RakutenItemSearchApiError,
    RakutenRankingApiError,
    RakutenRankingEntry,
)


@dataclass(frozen=True)
class AdaptedRankingRaw:
    """Normalized ranking payload extracted from formatVersion=2 style Raw dict."""

    last_build_date: str
    entries: tuple[RakutenRankingEntry, ...]
    genre_id: str


def adapt_genre_raw_payload(payload: dict[str, object], *, requested_genre_id: str) -> RakutenGenre:
    """Map Rakuten genre search JSON (formatVersion=2 shape) to RakutenGenre.

    Secret fields are never expected in payloads persisted by this adapter.
    """

    genre_obj = payload.get("genre")
    if not isinstance(genre_obj, dict):
        raise RakutenGenreApiError(
            genre_id=requested_genre_id,
            code="GRS-EXT-103",
            message="invalid genre payload: missing genre object",
        )

    genre_id = _as_str(genre_obj.get("genreId")) or requested_genre_id
    genre_name = _as_str(genre_obj.get("jaName")) or _as_str(genre_obj.get("genreName"))
    if not genre_name:
        raise RakutenGenreApiError(
            genre_id=genre_id,
            code="GRS-EXT-103",
            message="invalid genre payload: missing jaName/genreName",
        )

    parent_genre_id = _as_str(genre_obj.get("parentGenreId"))
    if parent_genre_id is None:
        ancestors = payload.get("ancestors")
        if isinstance(ancestors, list) and ancestors:
            first = ancestors[0]
            if isinstance(first, dict):
                parent_genre_id = _as_str(first.get("genreId"))

    level_raw = genre_obj.get("level")
    genre_level: int | None
    if isinstance(level_raw, int):
        genre_level = level_raw
    elif isinstance(level_raw, str) and level_raw.isdigit():
        genre_level = int(level_raw)
    else:
        genre_level = None

    children: list[str] = []
    children_raw = payload.get("children")
    if isinstance(children_raw, list):
        for child in children_raw:
            if isinstance(child, dict):
                child_id = _as_str(child.get("genreId"))
                if child_id:
                    children.append(child_id)

    return RakutenGenre(
        genre_id=genre_id,
        genre_name=genre_name,
        parent_genre_id=parent_genre_id,
        genre_level=genre_level,
        children=tuple(children),
    )


def adapt_ranking_raw_payload(
    payload: dict[str, object],
    *,
    requested_genre_id: str,
    period: str = "daily",
    page: int = 1,
) -> AdaptedRankingRaw:
    """Map Rakuten item ranking JSON (formatVersion=2 shape) to AdaptedRankingRaw.

    Extracts lastBuildDate and Items[{rank, itemCode}].
    Secret fields are never expected in payloads persisted by this adapter.
    """

    _ = period  # reserved for future validation against payload.period
    last_build_date = _as_str(payload.get("lastBuildDate"))
    if not last_build_date:
        raise RakutenRankingApiError(
            genre_id=requested_genre_id,
            page=page,
            code="GRS-EXT-103",
            message="invalid ranking payload: missing lastBuildDate",
        )

    genre_id = _as_str(payload.get("genreId")) or requested_genre_id

    items_raw = payload.get("Items")
    if not isinstance(items_raw, list):
        raise RakutenRankingApiError(
            genre_id=requested_genre_id,
            page=page,
            code="GRS-EXT-103",
            message="invalid ranking payload: missing Items list",
        )

    entries: list[RakutenRankingEntry] = []
    for item in items_raw:
        if not isinstance(item, dict):
            continue
        # formatVersion=2 では flat、または {"Item": {...}} の両形を許容
        item_obj = item.get("Item") if isinstance(item.get("Item"), dict) else item
        if not isinstance(item_obj, dict):
            continue
        rank = _as_int(item_obj.get("rank"))
        item_code = _as_str(item_obj.get("itemCode"))
        if rank is None or not item_code:
            raise RakutenRankingApiError(
                genre_id=requested_genre_id,
                page=page,
                code="GRS-EXT-103",
                message="invalid ranking payload: item missing rank/itemCode",
            )
        entries.append(RakutenRankingEntry(rank=rank, item_code=item_code))

    if not entries:
        raise RakutenRankingApiError(
            genre_id=requested_genre_id,
            page=page,
            code="GRS-EXT-103",
            message="invalid ranking payload: empty Items",
        )

    return AdaptedRankingRaw(
        last_build_date=last_build_date,
        entries=tuple(entries),
        genre_id=genre_id,
    )


@dataclass(frozen=True)
class AdaptedItemSearchCandidate:
    """Single product candidate from item search Raw."""

    external_item_code: str
    item_name: str | None = None
    genre_id: str | None = None
    availability: int | None = None


@dataclass(frozen=True)
class AdaptedItemSearchRaw:
    """Normalized item search payload extracted from formatVersion=2 style Raw dict."""

    candidates: tuple[AdaptedItemSearchCandidate, ...]


def adapt_item_search_raw_payload(
    payload: dict[str, object],
    *,
    cursor_type: str,
    page: int = 1,
    allow_empty: bool = False,
) -> AdaptedItemSearchRaw:
    """Map Rakuten item search JSON (formatVersion=2 shape) to candidates.

    When ``allow_empty`` is True (BATCH-004 recheck), empty Items / zero candidates
    return an empty AdaptedItemSearchRaw instead of raising GRS-EXT-103.
    Default remains False so BATCH-003 behavior is unchanged.

    Secret fields are never expected in payloads persisted by this adapter.
    """

    items_raw = payload.get("Items")
    if not isinstance(items_raw, list):
        if allow_empty and items_raw is None:
            return AdaptedItemSearchRaw(candidates=())
        raise RakutenItemSearchApiError(
            cursor_type=cursor_type,
            page=page,
            code="GRS-EXT-103",
            message="invalid item search payload: missing Items list",
        )

    candidates: list[AdaptedItemSearchCandidate] = []
    for item in items_raw:
        if not isinstance(item, dict):
            continue
        item_obj = item.get("Item") if isinstance(item.get("Item"), dict) else item
        if not isinstance(item_obj, dict):
            continue
        item_code = _as_str(item_obj.get("itemCode"))
        if not item_code:
            continue
        candidates.append(
            AdaptedItemSearchCandidate(
                external_item_code=item_code,
                item_name=_as_str(item_obj.get("itemName")),
                genre_id=_as_str(item_obj.get("genreId")),
                availability=_as_int(item_obj.get("availability")),
            )
        )

    if not candidates:
        if allow_empty:
            return AdaptedItemSearchRaw(candidates=())
        raise RakutenItemSearchApiError(
            cursor_type=cursor_type,
            page=page,
            code="GRS-EXT-103",
            message="invalid item search payload: empty Items",
        )

    return AdaptedItemSearchRaw(candidates=tuple(candidates))


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None
