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


class RakutenApiClient(Protocol):
    """Rakuten external API boundary (Phase4a protocol)."""

    def search_items(self, *, keyword: str, page: int = 1) -> tuple[RakutenItem, ...]: ...

    def fetch_ranking(self, *, genre_id: str, page: int = 1) -> tuple[RakutenRankingEntry, ...]: ...

    def fetch_genre(self, *, genre_id: str) -> RakutenGenre | None: ...

    def fetch_genre_raw(self, *, genre_id: str) -> dict[str, object]: ...


@dataclass
class ScaffoldRakutenApiClient:
    """Phase4a placeholder client without outbound Rakuten API calls."""

    items: tuple[RakutenItem, ...] = ()
    ranking: tuple[RakutenRankingEntry, ...] = ()
    genres: dict[str, RakutenGenre] = field(default_factory=dict)
    raw_responses: dict[str, dict[str, object]] = field(default_factory=dict)
    fail_genre_ids: set[str] = field(default_factory=set)
    search_calls: list[dict[str, object]] = field(default_factory=list)
    ranking_calls: list[dict[str, object]] = field(default_factory=list)
    genre_calls: list[dict[str, object]] = field(default_factory=list)

    def search_items(self, *, keyword: str, page: int = 1) -> tuple[RakutenItem, ...]:
        self.search_calls.append({"keyword": keyword, "page": page})
        return self.items

    def fetch_ranking(self, *, genre_id: str, page: int = 1) -> tuple[RakutenRankingEntry, ...]:
        self.ranking_calls.append({"genre_id": genre_id, "page": page})
        return self.ranking

    def fetch_genre(self, *, genre_id: str) -> RakutenGenre | None:
        self.genre_calls.append({"genre_id": genre_id})
        if genre_id in self.fail_genre_ids:
            raise RakutenGenreApiError(
                genre_id=genre_id,
                code="GRS-EXT-100",
                message="scaffold forced genre fetch failure",
            )
        return self.genres.get(genre_id)

    def fetch_genre_raw(self, *, genre_id: str) -> dict[str, object]:
        """Return Raw JSON-compatible payload for Object Storage persistence."""

        self.genre_calls.append({"genre_id": genre_id, "mode": "raw"})
        if genre_id in self.fail_genre_ids:
            raise RakutenGenreApiError(
                genre_id=genre_id,
                code="GRS-EXT-100",
                message="scaffold forced genre fetch failure",
            )
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
