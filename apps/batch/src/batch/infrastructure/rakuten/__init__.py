"""Rakuten API infrastructure scaffold."""

from batch.infrastructure.rakuten.adapter import adapt_genre_raw_payload
from batch.infrastructure.rakuten.client import (
    RakutenApiClient,
    RakutenGenre,
    RakutenGenreApiError,
    RakutenItem,
    RakutenRankingEntry,
    ScaffoldRakutenApiClient,
)

__all__ = [
    "RakutenApiClient",
    "RakutenGenre",
    "RakutenGenreApiError",
    "RakutenItem",
    "RakutenRankingEntry",
    "ScaffoldRakutenApiClient",
    "adapt_genre_raw_payload",
]
