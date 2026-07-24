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
    HttpRakutenApiClient,
    RakutenApiClient,
    RakutenGenre,
    RakutenGenreApiError,
    RakutenItem,
    RakutenItemSearchApiError,
    RakutenRankingApiError,
    RakutenRankingEntry,
    ScaffoldRakutenApiClient,
    create_rakuten_client,
    mask_rakuten_secret,
    resolve_live_rakuten_flag,
)

__all__ = [
    "AdaptedItemSearchCandidate",
    "AdaptedItemSearchRaw",
    "AdaptedRankingRaw",
    "HttpRakutenApiClient",
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
    "create_rakuten_client",
    "mask_rakuten_secret",
    "resolve_live_rakuten_flag",
]
