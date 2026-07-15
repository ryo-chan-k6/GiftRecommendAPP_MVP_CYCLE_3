"""Unit tests for BATCH-008 Item Active Status Applier."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from batch.application.item_active_status.job import ItemActiveStatusJob
from batch.application.item_active_status.models import CandidateRow, DiffSuggestion, ItemRow
from batch.application.item_active_status.repositories import ItemActiveStatusRepositories
from batch.infrastructure.db import ScaffoldDbWriter

NOW = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)


def _repos() -> ItemActiveStatusRepositories:
    return ItemActiveStatusRepositories(db_writer=ScaffoldDbWriter())


def _item(code: str, status: str, *, item_id: str | None = None) -> ItemRow:
    return ItemRow(
        source="rakuten",
        external_item_code=code,
        active_status=status,  # type: ignore[arg-type]
        item_id=item_id or f"item-{code}",
    )


def _cand(
    *,
    cid: str,
    code: str,
    status: str,
    detected_at: datetime,
    basis: str | None = None,
    reason: str | None = None,
    cand_status: str = "detected",
) -> CandidateRow:
    return CandidateRow(
        candidate_id=cid,
        batch_run_id="run-1",
        source="rakuten",
        external_item_code=code,
        candidate_active_status=status,  # type: ignore[arg-type]
        candidate_status=cand_status,  # type: ignore[arg-type]
        detected_at=detected_at,
        detection_basis=basis,
        reason_code=reason,
    )


def _diff(
    *,
    did: str,
    code: str,
    proposed: str | None,
    judged_at: datetime,
    diff_status: str = "unavailable",
) -> DiffSuggestion:
    return DiffSuggestion(
        product_diff_result_id=did,
        batch_run_id="run-1",
        source="rakuten",
        external_item_code=code,
        diff_status=diff_status,
        proposed_active_status=proposed,  # type: ignore[arg-type]
        judged_at=judged_at,
    )


def test_restriction_side_prefers_unavailable_over_inactive() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:a", "active"))
    # Diff 側は弱い制限（inactive）、候補側は強い制限（unavailable）
    repos.seed_diff(
        DiffSuggestion(
            product_diff_result_id="d1",
            batch_run_id="run-1",
            source="rakuten",
            external_item_code="shop:a",
            diff_status="unavailable",
            proposed_active_status="inactive",
            judged_at=NOW,
        )
    )
    repos.seed_candidate(
        _cand(
            cid="c1",
            code="shop:a",
            status="unavailable",
            detected_at=NOW - timedelta(hours=1),
            basis="empty_hit",
            reason="empty_hit",
        )
    )

    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-1")
    assert result.status == "succeeded"
    assert repos.items[("rakuten", "shop:a")].active_status == "unavailable"
    assert repos.items[("rakuten", "shop:a")].is_active is False
    assert repos.candidates["c1"].candidate_status == "applied"
    assert result.candidate_applied_count == 1


def test_same_restriction_prefers_newer_timestamp() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:b", "active"))
    repos.seed_diff(
        DiffSuggestion(
            product_diff_result_id="d2",
            batch_run_id="run-1",
            source="rakuten",
            external_item_code="shop:b",
            diff_status="unavailable",
            proposed_active_status="unavailable",
            judged_at=NOW - timedelta(hours=2),
        )
    )
    repos.seed_candidate(
        _cand(
            cid="c2",
            code="shop:b",
            status="unavailable",
            detected_at=NOW,
            basis="availability",
            reason="availability_zero",
        )
    )
    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-2")
    assert result.status == "succeeded"
    assert repos.items[("rakuten", "shop:b")].active_status == "unavailable"
    assert repos.candidates["c2"].candidate_status == "applied"


def test_reactivation_allowed_only_with_explicit_candidate() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:c", "unavailable"))
    repos.seed_candidate(
        _cand(
            cid="c3",
            code="shop:c",
            status="active",
            detected_at=NOW,
            basis="api_success",
            reason="available",
        )
    )
    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-3")
    assert result.status == "succeeded"
    assert repos.items[("rakuten", "shop:c")].active_status == "active"
    assert repos.items[("rakuten", "shop:c")].is_active is True
    assert result.reactivation_count == 1
    assert repos.candidates["c3"].candidate_status == "applied"
    assert repos.candidates["c3"].applied_at is not None


def test_reactivation_blocked_when_only_diff_unavailable() -> None:
    """Diff unavailable 単独では active に戻れない（現行が active なら制限へ下げるのは可）."""

    repos = _repos()
    repos.seed_item(_item("shop:d", "unavailable"))
    repos.seed_diff(
        _diff(did="d4", code="shop:d", proposed="unavailable", judged_at=NOW)
    )
    # 候補なし → 制限提案は unavailable。現行と同一なら update skip + no candidate
    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-4")
    assert result.status == "succeeded"
    assert repos.items[("rakuten", "shop:d")].active_status == "unavailable"
    assert result.reactivation_count == 0
    assert result.item_status_updated_count == 0


def test_restriction_beats_reactivation_candidate() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:e", "unavailable"))
    repos.seed_diff(
        _diff(did="d5", code="shop:e", proposed="unavailable", judged_at=NOW)
    )
    repos.seed_candidate(
        _cand(
            cid="c5",
            code="shop:e",
            status="active",
            detected_at=NOW + timedelta(hours=1),
            basis="api_success",
            reason="available",
        )
    )
    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-5")
    assert result.status == "succeeded"
    assert repos.items[("rakuten", "shop:e")].active_status == "unavailable"
    assert result.reactivation_count == 0
    assert repos.candidates["c5"].candidate_status == "superseded"


def test_idempotent_rerun_does_not_reapply_applied() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:f", "active"))
    repos.seed_candidate(
        _cand(
            cid="c6",
            code="shop:f",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    job = ItemActiveStatusJob(repositories=repos)
    first = job.run(job_run_id="job-6a")
    assert first.item_status_updated_count == 1
    assert repos.candidates["c6"].candidate_status == "applied"
    second = job.run(job_run_id="job-6b")
    assert second.candidate_input_count == 0
    assert second.item_status_updated_count == 0
    assert repos.candidates["c6"].candidate_status == "applied"


def test_failed_item_keeps_candidate_detected_for_retry() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:g", "active"))
    repos.seed_candidate(
        _cand(
            cid="c7",
            code="shop:g",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    job = ItemActiveStatusJob(repositories=repos, fail_item_codes=("shop:g",))
    result = job.run(job_run_id="job-7")
    assert result.status == "failed"
    assert repos.candidates["c7"].candidate_status == "detected"
    assert repos.items[("rakuten", "shop:g")].active_status == "active"

    # retry without fail
    retry = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-7r")
    assert retry.status == "succeeded"
    assert repos.candidates["c7"].candidate_status == "applied"
    assert repos.items[("rakuten", "shop:g")].active_status == "unavailable"


def test_no_detected_candidates_still_succeeds() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:h", "active"))
    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-8")
    assert result.status == "succeeded"
    assert result.candidate_input_count == 0
    assert result.item_status_updated_count == 0
    assert repos.deleted_candidate_ids == []


def test_does_not_mutate_diff_rows() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:i", "active"))
    repos.seed_diff(_diff(did="d9", code="shop:i", proposed="unavailable", judged_at=NOW))
    before = repos.diffs["d9"]
    ItemActiveStatusJob(repositories=repos).run(job_run_id="job-9")
    assert repos.diffs["d9"] == before
    # Diff 更新 write が無いこと
    assert all(call["table"] != "product_diff_result" for call in repos.db_writer.write_calls)
