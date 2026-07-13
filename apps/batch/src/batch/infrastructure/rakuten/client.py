"""Rakuten API client scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class RakutenItem:
    """Placeholder for a Rakuten marketplace item."""

    item_code: str
    item_name: str


@dataclass(frozen=True)
class RakutenRankingEntry:
    """Placeholder for a Rakuten ranking hit."""

    rank: int
    item_code: str


@dataclass(frozen=True)
class RakutenGenre:
    """Rakuten genre node used by BATCH-001 and ranking fetch."""

    genre_id: str
    genre_name: str
    parent_genre_id: str | None = None
    genre_level: int | None = None
    children: tuple[str, ...] = ()


class RakutenGenreApiError(Exception):
    """Raised when genre fetch fails (mapped to GRS-EXT-* in the job layer)."""

    def __init__(self, *, genre_id: str, code: str, message: str) -> None:
        self.genre_id = genre_id
        self.code = code
        self.message = message
        super().__init__(f"{code}: genre_id={genre_id}: {message}")


class RakutenRankingApiError(Exception):
    """Raised when ranking fetch fails (mapped to GRS-EXT-* in the job layer)."""

    def __init__(self, *, genre_id: str, page: int, code: str, message: str) -> None:
        self.genre_id = genre_id
        self.page = page
        self.code = code
        self.message = message
        super().__init__(f"{code}: genre_id={genre_id} page={page}: {message}")


class RakutenItemSearchApiError(Exception):
    """Raised when item search fetch fails (mapped to GRS-EXT-* in the job layer)."""

    def __init__(self, *, cursor_type: str, page: int, code: str, message: str) -> None:
        self.cursor_type = cursor_type
        self.page = page
        self.code = code
        self.message = message
        super().__init__(f"{code}: cursor_type={cursor_type} page={page}: {message}")


class RakutenApiClient(Protocol):
    """Rakuten external API boundary (Phase4a protocol)."""

    def search_items(self, *, keyword: str, page: int = 1) -> tuple[RakutenItem, ...]: ...

    def fetch_ranking(self, *, genre_id: str, page: int = 1) -> tuple[RakutenRankingEntry, ...]: ...

    def fetch_ranking_raw(
        self,
        *,
        genre_id: str,
        period: str = "daily",
        page: int = 1,
    ) -> dict[str, object]: ...

    def fetch_item_search_raw(
        self,
        *,
        cursor_type: str,
        genre_id: str | None = None,
        keyword: str | None = None,
        item_code: str | None = None,
        sort: str | None = None,
        page: int = 1,
        hits: int = 30,
    ) -> dict[str, object]: ...

    def fetch_genre(self, *, genre_id: str) -> RakutenGenre | None: ...

    def fetch_genre_raw(self, *, genre_id: str) -> dict[str, object]: ...


@dataclass
class ScaffoldRakutenApiClient:
    """Phase4a placeholder client without outbound Rakuten API calls."""

    items: tuple[RakutenItem, ...] = ()
    ranking: tuple[RakutenRankingEntry, ...] = ()
    genres: dict[str, RakutenGenre] = field(default_factory=dict)
    raw_responses: dict[str, dict[str, object]] = field(default_factory=dict)
    # key: (genre_id, period, page)
    ranking_raw_responses: dict[tuple[str, str, int], dict[str, object]] = field(default_factory=dict)
    # key: (cursor_type, genre_id|keyword|item_code|*, page)
    item_search_raw_responses: dict[tuple[str, str, int], dict[str, object]] = field(
        default_factory=dict
    )
    fail_genre_ids: set[str] = field(default_factory=set)
    rate_limited_genre_ids: set[str] = field(default_factory=set)
    fail_ranking_keys: set[tuple[str, str, int]] = field(default_factory=set)
    rate_limited_ranking_keys: set[tuple[str, str, int]] = field(default_factory=set)
    fail_item_search_keys: set[tuple[str, str, int]] = field(default_factory=set)
    rate_limited_item_search_keys: set[tuple[str, str, int]] = field(default_factory=set)
    search_calls: list[dict[str, object]] = field(default_factory=list)
    ranking_calls: list[dict[str, object]] = field(default_factory=list)
    genre_calls: list[dict[str, object]] = field(default_factory=list)
    item_search_calls: list[dict[str, object]] = field(default_factory=list)

    def search_items(self, *, keyword: str, page: int = 1) -> tuple[RakutenItem, ...]:
        self.search_calls.append({"keyword": keyword, "page": page})
        return self.items

    def fetch_ranking(self, *, genre_id: str, page: int = 1) -> tuple[RakutenRankingEntry, ...]:
        self.ranking_calls.append({"genre_id": genre_id, "page": page})
        return self.ranking

    def fetch_ranking_raw(
        self,
        *,
        genre_id: str,
        period: str = "daily",
        page: int = 1,
    ) -> dict[str, object]:
        """Return Raw JSON-compatible ranking payload for Object Storage persistence."""

        key = (genre_id, period, page)
        self.ranking_calls.append(
            {"genre_id": genre_id, "period": period, "page": page, "mode": "raw"}
        )
        self._raise_if_ranking_forced_failure(genre_id=genre_id, period=period, page=page)
        if key in self.ranking_raw_responses:
            return dict(self.ranking_raw_responses[key])

        if self.ranking:
            return {
                "lastBuildDate": "2026-07-13T00:00:00+0900",
                "genreId": genre_id,
                "period": period,
                "Items": [
                    {"rank": entry.rank, "itemCode": entry.item_code} for entry in self.ranking
                ],
            }

        raise RakutenRankingApiError(
            genre_id=genre_id,
            page=page,
            code="GRS-EXT-104",
            message="ranking not found in scaffold",
        )

    def fetch_item_search_raw(
        self,
        *,
        cursor_type: str,
        genre_id: str | None = None,
        keyword: str | None = None,
        item_code: str | None = None,
        sort: str | None = None,
        page: int = 1,
        hits: int = 30,
    ) -> dict[str, object]:
        """Return Raw JSON-compatible item search payload for Object Storage persistence."""

        scope_key = item_code or keyword or genre_id or "*"
        key = (cursor_type, scope_key, page)
        self.item_search_calls.append(
            {
                "cursor_type": cursor_type,
                "genre_id": genre_id,
                "keyword": keyword,
                "item_code": item_code,
                "sort": sort,
                "page": page,
                "hits": hits,
                "mode": "raw",
            }
        )
        self._raise_if_item_search_forced_failure(
            cursor_type=cursor_type,
            scope_key=scope_key,
            page=page,
        )
        if key in self.item_search_raw_responses:
            return dict(self.item_search_raw_responses[key])

        if self.items:
            return {
                "Items": [
                    {
                        "Item": {
                            "itemCode": item.item_code,
                            "itemName": item.item_name,
                        }
                    }
                    for item in self.items
                ]
            }

        raise RakutenItemSearchApiError(
            cursor_type=cursor_type,
            page=page,
            code="GRS-EXT-104",
            message="item search not found in scaffold",
        )

    def fetch_genre(self, *, genre_id: str) -> RakutenGenre | None:
        self.genre_calls.append({"genre_id": genre_id})
        self._raise_if_forced_failure(genre_id)
        return self.genres.get(genre_id)

    def fetch_genre_raw(self, *, genre_id: str) -> dict[str, object]:
        """Return Raw JSON-compatible payload for Object Storage persistence."""

        self.genre_calls.append({"genre_id": genre_id, "mode": "raw"})
        self._raise_if_forced_failure(genre_id)
        if genre_id in self.raw_responses:
            return dict(self.raw_responses[genre_id])

        genre = self.genres.get(genre_id)
        if genre is None:
            raise RakutenGenreApiError(
                genre_id=genre_id,
                code="GRS-EXT-104",
                message="genre not found in scaffold",
            )
        return {
            "genre": {
                "genreId": genre.genre_id,
                "jaName": genre.genre_name,
                "level": genre.genre_level,
            },
            "ancestors": (
                [{"genreId": genre.parent_genre_id}] if genre.parent_genre_id else []
            ),
            "children": [{"genreId": child_id} for child_id in genre.children],
        }

    def _raise_if_forced_failure(self, genre_id: str) -> None:
        if genre_id in self.rate_limited_genre_ids:
            raise RakutenGenreApiError(
                genre_id=genre_id,
                code="GRS-EXT-102",
                message="scaffold forced rate limit",
            )
        if genre_id in self.fail_genre_ids:
            raise RakutenGenreApiError(
                genre_id=genre_id,
                code="GRS-EXT-100",
                message="scaffold forced genre fetch failure",
            )

    def _raise_if_ranking_forced_failure(
        self,
        *,
        genre_id: str,
        period: str,
        page: int,
    ) -> None:
        key = (genre_id, period, page)
        if key in self.rate_limited_ranking_keys:
            raise RakutenRankingApiError(
                genre_id=genre_id,
                page=page,
                code="GRS-EXT-102",
                message="scaffold forced ranking rate limit",
            )
        if key in self.fail_ranking_keys:
            raise RakutenRankingApiError(
                genre_id=genre_id,
                page=page,
                code="GRS-EXT-100",
                message="scaffold forced ranking fetch failure",
            )

    def _raise_if_item_search_forced_failure(
        self,
        *,
        cursor_type: str,
        scope_key: str,
        page: int,
    ) -> None:
        key = (cursor_type, scope_key, page)
        if key in self.rate_limited_item_search_keys:
            raise RakutenItemSearchApiError(
                cursor_type=cursor_type,
                page=page,
                code="GRS-EXT-102",
                message="scaffold forced item search rate limit",
            )
        if key in self.fail_item_search_keys:
            raise RakutenItemSearchApiError(
                cursor_type=cursor_type,
                page=page,
                code="GRS-EXT-100",
                message="scaffold forced item search fetch failure",
            )
