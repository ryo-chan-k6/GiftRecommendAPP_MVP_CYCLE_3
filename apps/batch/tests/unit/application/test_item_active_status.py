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


def test_max_items_limits_item_keys() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:a", "active"))
    repos.seed_item(_item("shop:b", "active"))
    repos.seed_candidate(
        _cand(
            cid="c-a",
            code="shop:a",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    repos.seed_candidate(
        _cand(
            cid="c-b",
            code="shop:b",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-max", max_items=1)
    assert result.status == "succeeded"
    assert result.item_status_updated_count == 1
    updated = [
        code
        for (src, code), row in repos.items.items()
        if src == "rakuten" and row.active_status == "unavailable"
    ]
    assert len(updated) == 1


def test_cli_scaffold_demo_passes_filters(monkeypatch) -> None:
    from batch.application.item_active_status import __main__ as cli

    captured: dict[str, object] = {}

    class _FakeJob:
        def run(self, **kwargs):  # type: ignore[no-untyped-def]
            captured.update(kwargs)

            class _Result:
                status = "succeeded"
                item_status_updated_count = 0
                candidate_applied_count = 0
                candidate_superseded_count = 0
                reactivation_count = 0
                failed_item_codes: list[str] = []
                completed_phases = ["plan", "finalize"]

            return _Result()

    monkeypatch.setattr(cli, "build_scaffold_demo_job", lambda: _FakeJob())
    code = cli.main(
        [
            "--scaffold-demo",
            "--job-run-id",
            "job-cli",
            "--max-items",
            "42",
            "--source",
            "rakuten",
            "--batch-run-id",
            "run-x",
            "--external-item-codes",
            "shop:1, shop:2",
        ]
    )
    assert code == 0
    assert captured["job_run_id"] == "job-cli"
    assert captured["max_items"] == 42
    assert captured["source"] == "rakuten"
    assert captured["batch_run_id"] == "run-x"
    assert captured["external_item_codes"] == ("shop:1", "shop:2")


def test_cli_without_scaffold_demo_exits_2_without_database_url(monkeypatch) -> None:
    from dataclasses import replace

    from batch.application.item_active_status import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_batch_settings(), database_url=None),
    )
    assert cli.main(["--job-run-id", "job-real"]) == 2


def test_list_detected_candidates_uses_db_reader_when_injected() -> None:
    from datetime import UTC, datetime

    from batch.infrastructure.db import ScaffoldDbReader, ScaffoldDbWriter

    now = datetime.now(UTC)
    reader = ScaffoldDbReader()
    reader.seed(
        "item_active_status_candidate",
        (
            {
                "item_active_status_candidate_id": "cand-1",
                "batch_run_id": "run-1",
                "source": "rakuten",
                "external_item_code": "shop:a",
                "candidate_active_status": "unavailable",
                "candidate_status": "detected",
                "detected_at": now,
                "detection_basis": "availability",
                "reason_code": "availability_zero",
                "item_id": "it_1",
                "applied_at": None,
                "updated_at": None,
            },
            {
                "item_active_status_candidate_id": "cand-applied",
                "batch_run_id": "run-1",
                "source": "rakuten",
                "external_item_code": "shop:b",
                "candidate_active_status": "inactive",
                "candidate_status": "applied",
                "detected_at": now,
                "detection_basis": None,
                "reason_code": None,
                "item_id": None,
                "applied_at": now,
                "updated_at": now,
            },
        ),
    )
    repos = ItemActiveStatusRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    rows = repos.list_detected_candidates(source="rakuten")
    assert [r.candidate_id for r in rows] == ["cand-1"]
    assert reader.fetch_calls[0]["table"] == "item_active_status_candidate"


def test_list_diff_suggestions_resolves_source_via_staging() -> None:
    from datetime import UTC, datetime

    from batch.infrastructure.db import ScaffoldDbReader, ScaffoldDbWriter

    now = datetime.now(UTC)
    reader = ScaffoldDbReader()
    reader.seed(
        "product_diff_result",
        (
            {
                "product_diff_result_id": "pdr_1",
                "batch_run_id": "run-1",
                "staging_item_id": "si_1",
                "external_item_code": "shop:a",
                "diff_status": "unavailable",
                "judged_at": now,
            },
            {
                "product_diff_result_id": "pdr_2",
                "batch_run_id": "run-1",
                "staging_item_id": "si_2",
                "external_item_code": "shop:b",
                "diff_status": "updated",
                "judged_at": now,
            },
        ),
    )
    reader.seed(
        "staging_item",
        (
            {
                "staging_item_id": "si_1",
                "source": "rakuten",
                "external_item_code": "shop:a",
            },
            {
                "staging_item_id": "si_2",
                "source": "rakuten",
                "external_item_code": "shop:b",
            },
        ),
    )
    repos = ItemActiveStatusRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    rows = repos.list_diff_suggestions(source="rakuten")
    assert len(rows) == 2
    by_id = {r.product_diff_result_id: r for r in rows}
    assert by_id["pdr_1"].proposed_active_status == "unavailable"
    assert by_id["pdr_2"].proposed_active_status is None


def test_get_item_uses_db_reader_when_injected() -> None:
    from batch.infrastructure.db import ScaffoldDbReader, ScaffoldDbWriter

    reader = ScaffoldDbReader()
    reader.seed(
        "item",
        (
            {
                "item_id": "it_1",
                "source": "rakuten",
                "external_item_code": "shop:a",
                "active_status": "active",
                "is_active": True,
            },
        ),
    )
    repos = ItemActiveStatusRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    found = repos.get_item(source="rakuten", external_item_code="shop:a")
    assert found is not None
    assert found.item_id == "it_1"
    assert repos.get_item(source="rakuten", external_item_code="missing") is None


def test_applier_does_not_call_retention_delete() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:j", "active"))
    repos.seed_candidate(
        _cand(
            cid="c10",
            code="shop:j",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    ItemActiveStatusJob(repositories=repos).run(job_run_id="job-10")
    assert repos.deleted_candidate_ids == []
    assert all(call.get("op") != "delete" for call in repos.db_writer.write_calls)


def test_excluded_beats_unavailable() -> None:
    """§9.1 / §16: 制限側優先（excluded > unavailable）。"""

    repos = _repos()
    repos.seed_item(_item("shop:excl", "active"))
    repos.seed_diff(
        DiffSuggestion(
            product_diff_result_id="d-excl",
            batch_run_id="run-1",
            source="rakuten",
            external_item_code="shop:excl",
            diff_status="unavailable",
            proposed_active_status="unavailable",
            judged_at=NOW,
        )
    )
    repos.seed_candidate(
        _cand(
            cid="c-excl",
            code="shop:excl",
            status="excluded",
            detected_at=NOW - timedelta(hours=1),
            basis="policy",
            reason="excluded",
        )
    )
    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-excl")
    assert result.status == "succeeded"
    assert repos.items[("rakuten", "shop:excl")].active_status == "excluded"
    assert repos.items[("rakuten", "shop:excl")].is_active is False
    assert repos.candidates["c-excl"].candidate_status == "applied"


def test_non_unavailable_diff_does_not_propose_restriction() -> None:
    """§9.2: new/updated/unchanged は制限提案なし（有効状態を上げない）。"""

    repos = _repos()
    repos.seed_item(_item("shop:new", "inactive"))
    repos.seed_diff(
        _diff(
            did="d-new",
            code="shop:new",
            proposed=None,
            judged_at=NOW,
            diff_status="new",
        )
    )
    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-new")
    assert result.status == "succeeded"
    assert result.diff_input_count == 1
    assert result.item_status_updated_count == 0
    assert repos.items[("rakuten", "shop:new")].active_status == "inactive"


def test_same_status_skips_item_update_but_marks_applied() -> None:
    """§9.4: 採用提案=現行なら Item UPDATE スキップ、候補は applied。"""

    repos = _repos()
    repos.seed_item(_item("shop:same", "unavailable"))
    repos.seed_candidate(
        _cand(
            cid="c-same",
            code="shop:same",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    before_writes = len(repos.db_writer.write_calls)
    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-same")
    assert result.status == "succeeded"
    assert result.item_status_updated_count == 0
    assert repos.candidates["c-same"].candidate_status == "applied"
    assert repos.candidates["c-same"].applied_at is not None
    # item テーブルへの write が無いこと（候補 status 更新のみ）
    item_writes = [
        c for c in repos.db_writer.write_calls[before_writes:] if c["table"] == "item"
    ]
    assert item_writes == []


def test_is_active_syncs_with_active_status() -> None:
    """§18.2 No.2: is_active = (active_status == 'active')。"""

    repos = _repos()
    repos.seed_item(_item("shop:sync", "active"))
    repos.seed_candidate(
        _cand(
            cid="c-sync",
            code="shop:sync",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    ItemActiveStatusJob(repositories=repos).run(job_run_id="job-sync")
    row = repos.items[("rakuten", "shop:sync")]
    assert row.active_status == "unavailable"
    assert row.is_active is False

    repos2 = _repos()
    repos2.seed_item(_item("shop:sync2", "unavailable"))
    repos2.seed_candidate(
        _cand(
            cid="c-sync2",
            code="shop:sync2",
            status="active",
            detected_at=NOW,
            basis="api_success",
            reason="available",
        )
    )
    ItemActiveStatusJob(repositories=repos2).run(job_run_id="job-sync2")
    row2 = repos2.items[("rakuten", "shop:sync2")]
    assert row2.active_status == "active"
    assert row2.is_active is True


def test_selection_by_batch_run_id_and_external_codes() -> None:
    """§18.1.1: batch_run_id / external_item_codes で絞り込み。"""

    repos = _repos()
    repos.seed_item(_item("shop:sel1", "active"))
    repos.seed_item(_item("shop:sel2", "active"))
    repos.seed_candidate(
        CandidateRow(
            candidate_id="c-sel1",
            batch_run_id="run-keep",
            source="rakuten",
            external_item_code="shop:sel1",
            candidate_active_status="unavailable",
            candidate_status="detected",
            detected_at=NOW,
            detection_basis="empty_hit",
            reason_code="empty_hit",
        )
    )
    repos.seed_candidate(
        CandidateRow(
            candidate_id="c-sel2",
            batch_run_id="run-other",
            source="rakuten",
            external_item_code="shop:sel2",
            candidate_active_status="unavailable",
            candidate_status="detected",
            detected_at=NOW,
            detection_basis="empty_hit",
            reason_code="empty_hit",
        )
    )
    result = ItemActiveStatusJob(repositories=repos).run(
        job_run_id="job-sel",
        batch_run_id="run-keep",
        external_item_codes=("shop:sel1",),
    )
    assert result.status == "succeeded"
    assert result.candidate_input_count == 1
    assert repos.items[("rakuten", "shop:sel1")].active_status == "unavailable"
    assert repos.items[("rakuten", "shop:sel2")].active_status == "active"
    assert repos.candidates["c-sel2"].candidate_status == "detected"


def test_phases_completed_in_order() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:ph", "active"))
    repos.seed_candidate(
        _cand(
            cid="c-ph",
            code="shop:ph",
            status="inactive",
            detected_at=NOW,
            basis="availability",
            reason="availability_zero",
        )
    )
    from batch.application.item_active_status.job import ITEM_ACTIVE_STATUS_PHASES

    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-ph")
    assert result.status == "succeeded"
    assert result.completed_phases == list(ITEM_ACTIVE_STATUS_PHASES)


def test_item_not_found_discards_candidate() -> None:
    repos = _repos()
    repos.seed_candidate(
        _cand(
            cid="c-miss",
            code="shop:missing",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-miss")
    assert result.status == "failed"
    assert "shop:missing" in result.failed_item_codes
    assert repos.candidates["c-miss"].candidate_status == "discarded"
    assert result.candidate_discarded_count == 1


def test_partial_success_one_item_fails() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:ok", "active"))
    repos.seed_item(_item("shop:ng", "active"))
    repos.seed_candidate(
        _cand(
            cid="c-ok",
            code="shop:ok",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    repos.seed_candidate(
        _cand(
            cid="c-ng",
            code="shop:ng",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    result = ItemActiveStatusJob(
        repositories=repos,
        fail_item_codes=("shop:ng",),
    ).run(job_run_id="job-partial")
    assert result.status == "partially_succeeded"
    assert repos.items[("rakuten", "shop:ok")].active_status == "unavailable"
    assert repos.items[("rakuten", "shop:ng")].active_status == "active"
    assert repos.candidates["c-ok"].candidate_status == "applied"
    assert repos.candidates["c-ng"].candidate_status == "detected"
    assert "GRS-DB-002" in result.error_codes


def test_if_boundary_no_candidate_insert_no_raw_no_online() -> None:
    """§16 IF 境界: 候補 INSERT しない / Raw 非更新 / Online 非参照（unit 代替）。"""

    repos = _repos()
    repos.seed_item(_item("shop:if", "active"))
    repos.seed_candidate(
        _cand(
            cid="c-if",
            code="shop:if",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    repos.seed_diff(_diff(did="d-if", code="shop:if", proposed="unavailable", judged_at=NOW))
    ItemActiveStatusJob(repositories=repos).run(job_run_id="job-if")

    allowed_tables = {"item", "item_active_status_candidate"}
    tables = {call["table"] for call in repos.db_writer.write_calls}
    assert tables <= allowed_tables
    assert "product_diff_result" not in tables
    assert "raw_payload" not in tables
    assert "item_raw" not in tables
    # INSERT 相当の候補新規行書き込みが無い（status UPDATE のみ）
    for call in repos.db_writer.write_calls:
        if call["table"] == "item_active_status_candidate":
            for row in call["rows"]:  # type: ignore[index]
                assert "candidate_active_status" not in row
                assert "candidate_status" in row


def test_fixture_and_logs_have_no_secret_like_values() -> None:
    repos = _repos()
    repos.seed_item(_item("shop:sec", "active"))
    repos.seed_candidate(
        _cand(
            cid="c-sec",
            code="shop:sec",
            status="unavailable",
            detected_at=NOW,
            basis="empty_hit",
            reason="empty_hit",
        )
    )
    result = ItemActiveStatusJob(repositories=repos).run(job_run_id="job-sec")
    blob = repr(result) + repr(repos.db_writer.write_calls) + repr(repos.error_logs)
    for needle in ("sk-", "password=", "Bearer ", "DATABASE_URL=", "OPENAI_API_KEY="):
        assert needle not in blob
