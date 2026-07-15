"""BATCH-004 §9.3 active_status 候補 Resolver 写像."""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.item_recheck.idempotency import SOURCE_RAKUTEN
from batch.application.item_recheck.models import ResolvedCandidate
from batch.infrastructure.rakuten import AdaptedItemSearchCandidate


def resolve_active_status_candidate(
    *,
    batch_run_id: str,
    external_item_code: str,
    candidates: tuple[AdaptedItemSearchCandidate, ...] | list[AdaptedItemSearchCandidate],
    item_id: str | None = None,
    raw_metadata_id: str | None = None,
    api_call_log_id: str | None = None,
    source: str = SOURCE_RAKUTEN,
    detected_at: datetime | None = None,
) -> ResolvedCandidate:
    """Map adapted Item Search result to IF-DB-BATCH-020 detected candidate.

    | detection_basis | reason_code         | candidate_active_status |
    | --------------- | ------------------- | ----------------------- |
    | empty_hit       | empty_hit           | unavailable             |
    | availability    | availability_zero   | unavailable             |
    | api_success     | available           | active                  |
    """

    now = detected_at or datetime.now(UTC)
    items = tuple(candidates)

    if not items:
        return ResolvedCandidate(
            batch_run_id=batch_run_id,
            source=source,
            external_item_code=external_item_code,
            candidate_active_status="unavailable",
            reason_code="empty_hit",
            detection_basis="empty_hit",
            candidate_status="detected",
            item_id=item_id,
            raw_metadata_id=raw_metadata_id,
            api_call_log_id=api_call_log_id,
            detected_at=now,
            applied_at=None,
        )

    primary = items[0]
    if primary.availability == 0:
        return ResolvedCandidate(
            batch_run_id=batch_run_id,
            source=source,
            external_item_code=external_item_code,
            candidate_active_status="unavailable",
            reason_code="availability_zero",
            detection_basis="availability",
            candidate_status="detected",
            item_id=item_id,
            raw_metadata_id=raw_metadata_id,
            api_call_log_id=api_call_log_id,
            detected_at=now,
            applied_at=None,
        )

    # availability is None or non-zero → saleable / api_success
    return ResolvedCandidate(
        batch_run_id=batch_run_id,
        source=source,
        external_item_code=external_item_code,
        candidate_active_status="active",
        reason_code="available",
        detection_basis="api_success",
        candidate_status="detected",
        item_id=item_id,
        raw_metadata_id=raw_metadata_id,
        api_call_log_id=api_call_log_id,
        detected_at=now,
        applied_at=None,
    )
