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
    """Placeholder for a Rakuten genre node."""

    genre_id: str
    genre_name: str


class RakutenApiClient(Protocol):
    """Rakuten external API boundary (Phase4a protocol)."""

    def search_items(self, *, keyword: str, page: int = 1) -> tuple[RakutenItem, ...]: ...

    def fetch_ranking(self, *, genre_id: str, page: int = 1) -> tuple[RakutenRankingEntry, ...]: ...

    def fetch_genre(self, *, genre_id: str) -> RakutenGenre | None: ...


@dataclass
class ScaffoldRakutenApiClient:
    """Phase4a placeholder client without outbound Rakuten API calls."""

    items: tuple[RakutenItem, ...] = ()
    ranking: tuple[RakutenRankingEntry, ...] = ()
    genres: dict[str, RakutenGenre] = field(default_factory=dict)
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
        return self.genres.get(genre_id)
