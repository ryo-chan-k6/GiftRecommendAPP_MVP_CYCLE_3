"""Rakuten API infrastructure scaffold."""

from batch.infrastructure.rakuten.adapter import (
    AdaptedRankingRaw,
    adapt_genre_raw_payload,
    adapt_ranking_raw_payload,
)
from batch.infrastructure.rakuten.client import (
    RakutenApiClient,
    RakutenGenre,
    RakutenGenreApiError,
    RakutenItem,
    RakutenRankingApiError,
    RakutenRankingEntry,
    ScaffoldRakutenApiClient,
)

__all__ = [
    "AdaptedRankingRaw",
    "RakutenApiClient",
    "RakutenGenre",
    "RakutenGenreApiError",
    "RakutenItem",
    "RakutenRankingApiError",
    "RakutenRankingEntry",
    "ScaffoldRakutenApiClient",
    "adapt_genre_raw_payload",
    "adapt_ranking_raw_payload",
]
