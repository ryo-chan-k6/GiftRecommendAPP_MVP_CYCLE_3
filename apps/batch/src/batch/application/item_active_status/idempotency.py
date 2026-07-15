"""BATCH-008 idempotency helpers and restriction ranking."""

from __future__ import annotations

from batch.application.item_active_status.resolve import RESTRICTION_RANK, candidate_allows_reactivation

SOURCE_RAKUTEN = "rakuten"

__all__ = [
    "RESTRICTION_RANK",
    "SOURCE_RAKUTEN",
    "candidate_allows_reactivation",
    "item_idempotency_key",
]


def item_idempotency_key(*, source: str, external_item_code: str) -> tuple[str, str]:
    return (source, external_item_code)
