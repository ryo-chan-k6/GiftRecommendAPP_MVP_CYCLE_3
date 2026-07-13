"""Rakuten API infrastructure scaffold."""

from batch.infrastructure.rakuten.adapter import (
    AdaptedItemSearchCandidate,
    AdaptedItemSearchRaw,
    AdaptedRankingRaw,
    adapt_genre_raw_payload,
    adapt_item_search_raw_payload,
    adapt_ranking_raw_payload,
)
from batch.infrastructure.rakuten.client import (
    RakutenApiClient,
    RakutenGenre,
    RakutenGenreApiError,
    RakutenItem,
    RakutenItemSearchApiError,
    RakutenRankingApiError,
    RakutenRankingEntry,
    ScaffoldRakutenApiClient,
)

__all__ = [
    "AdaptedItemSearchCandidate",
    "AdaptedItemSearchRaw",
    "AdaptedRankingRaw",
    "RakutenApiClient",
    "RakutenGenre",
    "RakutenGenreApiError",
    "RakutenItem",
    "RakutenItemSearchApiError",
    "RakutenRankingApiError",
    "RakutenRankingEntry",
    "ScaffoldRakutenApiClient",
    "adapt_genre_raw_payload",
    "adapt_item_search_raw_payload",
    "adapt_ranking_raw_payload",
]
