"""Unit tests for T7 item_active_status_candidate Retention cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from batch.application.item_active_status.models import CandidateRow
from batch.application.item_active_status.repositories import ItemActiveStatusRepositories
from batch.application.item_active_status.retention import (
    DEFAULT_RETENTION_DAYS,
    RetentionCleanupJob,
    is_retention_eligible,
)
from batch.infrastructure.db import ScaffoldDbWriter

NOW = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)


def _repos() -> ItemActiveStatusRepositories:
    return ItemActiveStatusRepositories(db_writer=ScaffoldDbWriter())


def _cand(
    *,
    cid: str,
    status: str,
    applied_at: datetime | None = None,
    updated_at: datetime | None = None,
    detected_at: datetime | None = None,
) -> CandidateRow:
    return CandidateRow(
        candidate_id=cid,
        batch_run_id="run-1",
        source="rakuten",
        external_item_code=f"shop:{cid}",
        candidate_active_status="unavailable",
        candidate_status=status,  # type: ignore[arg-type]
        detected_at=detected_at or NOW - timedelta(days=30),
        applied_at=applied_at,
        updated_at=updated_at,
    )


def test_detected_is_never_eligible() -> None:
    row = _cand(cid="d1", status="detected")
    assert is_retention_eligible(row, now=NOW) is False


def test_applied_older_than_14_days_is_deleted() -> None:
    repos = _repos()
    old = NOW - timedelta(days=DEFAULT_RETENTION_DAYS + 1)
    repos.seed_candidate(_cand(cid="a1", status="applied", applied_at=old, updated_at=old))
    result = RetentionCleanupJob(repositories=repos).run(job_run_id="r1", now=NOW)
    assert result.status == "succeeded"
    assert result.deleted_count == 1
    assert "a1" not in repos.candidates
    assert "a1" in repos.deleted_candidate_ids


def test_applied_within_14_days_is_kept() -> None:
    repos = _repos()
    young = NOW - timedelta(days=DEFAULT_RETENTION_DAYS - 1)
    repos.seed_candidate(_cand(cid="a2", status="applied", applied_at=young, updated_at=young))
    result = RetentionCleanupJob(repositories=repos).run(job_run_id="r2", now=NOW)
    assert result.deleted_count == 0
    assert result.skipped_young_count == 1
    assert "a2" in repos.candidates


def test_superseded_uses_updated_at() -> None:
    repos = _repos()
    old = NOW - timedelta(days=20)
    repos.seed_candidate(_cand(cid="s1", status="superseded", updated_at=old))
    result = RetentionCleanupJob(repositories=repos).run(job_run_id="r3", now=NOW)
    assert result.deleted_count == 1
    assert "s1" not in repos.candidates


def test_discarded_young_kept() -> None:
    repos = _repos()
    young = NOW - timedelta(days=2)
    repos.seed_candidate(_cand(cid="x1", status="discarded", updated_at=young))
    result = RetentionCleanupJob(repositories=repos).run(job_run_id="r4", now=NOW)
    assert result.deleted_count == 0
    assert "x1" in repos.candidates


def test_detected_skipped_even_when_old() -> None:
    repos = _repos()
    repos.seed_candidate(
        _cand(cid="d2", status="detected", detected_at=NOW - timedelta(days=100))
    )
    # force-delete must also refuse detected
    assert repos.delete_candidate("d2") is False
    result = RetentionCleanupJob(repositories=repos).run(job_run_id="r5", now=NOW)
    assert result.skipped_detected_count == 1
    assert result.deleted_count == 0
    assert "d2" in repos.candidates


def test_mixed_run_metrics() -> None:
    repos = _repos()
    old = NOW - timedelta(days=20)
    young = NOW - timedelta(days=1)
    repos.seed_candidate(_cand(cid="d3", status="detected"))
    repos.seed_candidate(_cand(cid="a3", status="applied", applied_at=old, updated_at=old))
    repos.seed_candidate(_cand(cid="s3", status="superseded", updated_at=young))
    result = RetentionCleanupJob(repositories=repos).run(job_run_id="r6", now=NOW)
    assert result.status == "succeeded"
    assert result.scanned_count == 3
    assert result.deleted_count == 1
    assert result.skipped_detected_count == 1
    assert result.skipped_young_count == 1
    assert set(repos.candidates) == {"d3", "s3"}


def test_dry_run_does_not_delete() -> None:
    repos = _repos()
    old = NOW - timedelta(days=20)
    repos.seed_candidate(_cand(cid="a4", status="applied", applied_at=old, updated_at=old))
    result = RetentionCleanupJob(repositories=repos).run(
        job_run_id="r7", now=NOW, dry_run=True
    )
    assert result.deleted_count == 1
    assert "a4" in repos.candidates
    assert repos.deleted_candidate_ids == []
