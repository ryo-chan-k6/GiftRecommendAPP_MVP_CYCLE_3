"""MOD-RECO-028 §14 unit test coverage (module spec No.1–11, 14).

| §14 No | 観点 | テスト関数 |
| -----: | ---- | ---------- |
| 1 | Port 契約 | `test_record_phase_accepts_section6_arguments` |
| 2 | started INSERT | `test_started_insert_creates_row_and_retains_phase_log_id` |
| 3 | 終端 UPDATE | `test_succeeded_terminal_updates_started_row`, `test_failed_terminal_updates_started_row` |
| 4 | trace / owner | `test_trace_id_and_owner_id_match_execution_context` |
| 5 | run_id バッファ | `test_buffered_events_flush_after_run_id_is_available` |
| 6 | enum 検証 | `test_all_fourteen_phase_names_persist_to_db` |
| 7 | enum 外 | `test_invalid_phase_name_stays_in_memory_only` |
| 8 | 失敗非伝播 | `test_insert_failure_does_not_propagate`, `test_update_failure_does_not_propagate` |
| 9 | detail マスキング | `test_detail_json_uses_allowlist_only` |
| 10 | InMemory Repository | `test_in_memory_repository_runs_without_external_db` |
| 11 | Stub 互換 | `test_phase_log_events_match_stub_compatible_shape` |
| 12 | Orchestrator 連携 | out of scope（integration） |
| 13 | 失敗フェーズ | out of scope（integration） |
| 14 | trace 伝播 | `test_trace_id_on_all_persisted_phase_rows` |
"""

from __future__ import annotations

import pytest
from conftest import (
    DEFAULT_RUN_ID,
    DEFAULT_TRACE_ID,
    STUB_COMPATIBLE_EVENT_KEYS,
    build_writer,
    record_failed,
    record_started,
    record_succeeded,
    sample_context,
    sample_rich_context,
)
from reco.application.phase_log_writer.constants import (
    ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES,
)
from reco.application.phase_log_writer.mapper import build_terminal_detail_json
from reco.application.phase_log_writer.repository import InMemoryPhaseLogRepository
from reco.application.recommendation_orchestrator.ports import PhaseStatus


def test_record_phase_accepts_section6_arguments() -> None:
    """§14 No.1: PhaseLogWriterPort.record_phase() accepts §6 arguments."""
    writer, repo = build_writer()
    context = sample_context()

    writer.record_phase(
        context,
        phase_name="request_received",
        phase_status=PhaseStatus.STARTED,
        module_id="MOD-RECO-001",
        error_code=None,
        duration_ms=None,
    )
    writer.record_phase(
        context,
        phase_name="request_received",
        phase_status=PhaseStatus.SUCCEEDED,
        module_id="MOD-RECO-001",
        error_code=None,
        duration_ms=20,
    )

    assert len(repo.records) == 1
    assert len(context.phase_log_events) == 2


def test_started_insert_creates_row_and_retains_phase_log_id() -> None:
    """§14 No.2: started INSERT creates one row and keeps phase_log_id for UPDATE."""
    writer, repo = build_writer()
    context = sample_context()

    record_started(writer, context, phase_name="config_resolved")
    assert len(repo.records) == 1
    phase_log_id = next(iter(repo.records.keys()))

    record_succeeded(writer, context, phase_name="config_resolved", duration_ms=9)

    assert len(repo.records) == 1
    assert phase_log_id in repo.records
    assert repo.records[phase_log_id].phase_status == "succeeded"


def test_succeeded_terminal_updates_started_row() -> None:
    """§14 No.3: succeeded terminal UPDATE updates the same started row."""
    writer, repo = build_writer()
    context = sample_context()

    record_started(writer, context, phase_name="matching_completed")
    record_succeeded(
        writer,
        context,
        phase_name="matching_completed",
        duration_ms=33,
        module_id="MOD-RECO-015",
    )

    record = next(iter(repo.records.values()))
    assert record.phase_status == "succeeded"
    assert record.completed_at is not None
    assert record.duration_ms == 33
    assert record.detail_json.get("source_module_id") == "MOD-RECO-015"


def test_failed_terminal_updates_started_row() -> None:
    """§14 No.3: failed terminal UPDATE updates the same started row."""
    writer, repo = build_writer()
    context = sample_context()

    record_started(writer, context, phase_name="ranking_completed")
    record_failed(
        writer,
        context,
        phase_name="ranking_completed",
        error_code="GRS-REC-012",
        duration_ms=44,
    )

    record = next(iter(repo.records.values()))
    assert record.phase_status == "failed"
    assert record.error_code == "GRS-REC-012"
    assert record.completed_at is not None
    assert record.duration_ms == 44


def test_trace_id_and_owner_id_match_execution_context() -> None:
    """§14 No.4: trace_id and owner_id match ExecutionContext."""
    writer, repo = build_writer()
    context = sample_context()

    record_started(writer, context, phase_name="retrieval_completed")

    record = next(iter(repo.records.values()))
    assert record.trace_id == DEFAULT_TRACE_ID
    assert record.owner_id == DEFAULT_RUN_ID


def test_buffered_events_flush_after_run_id_is_available() -> None:
    """§14 No.5: pre-run events flush to DB once run_id becomes available."""
    writer, repo = build_writer()
    context = sample_context(include_run=False)

    record_started(writer, context, phase_name="request_received")
    assert repo.records == {}
    assert len(context.phase_log_events) == 1

    context.recommendation_run = sample_context().recommendation_run
    record_succeeded(writer, context, phase_name="request_received", duration_ms=7)

    assert len(repo.records) == 1
    record = next(iter(repo.records.values()))
    assert record.phase_status == "succeeded"
    assert record.owner_id == DEFAULT_RUN_ID


@pytest.mark.parametrize("phase_name", sorted(ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES))
def test_all_fourteen_phase_names_persist_to_db(phase_name: str) -> None:
    """§14 No.6: all 14 aggregated phase_name values INSERT / UPDATE to DB."""
    writer, repo = build_writer()
    context = sample_context()

    record_started(writer, context, phase_name=phase_name)
    record_succeeded(writer, context, phase_name=phase_name, duration_ms=5)

    assert len(repo.records) == 1
    record = next(iter(repo.records.values()))
    assert record.phase_name == phase_name
    assert record.phase_status == "succeeded"


def test_invalid_phase_name_stays_in_memory_only() -> None:
    """§14 No.7: enum-outside phase_name is in-memory only (no DB write)."""
    writer, repo = build_writer()
    context = sample_context()

    writer.record_phase(
        context,
        phase_name="run_recorded",
        phase_status=PhaseStatus.STARTED,
    )

    assert repo.records == {}
    assert len(context.phase_log_events) == 1
    assert context.phase_log_events[0]["phase_name"] == "run_recorded"


def test_insert_failure_does_not_propagate() -> None:
    """§14 No.8: repository INSERT failure does not propagate to caller."""
    repo = InMemoryPhaseLogRepository(should_fail_on_insert=True)
    writer, _ = build_writer(repository=repo)
    context = sample_context()

    writer.record_phase(
        context,
        phase_name="request_received",
        phase_status=PhaseStatus.STARTED,
    )

    assert repo.records == {}
    assert len(context.phase_log_events) == 1


def test_update_failure_does_not_propagate() -> None:
    """§14 No.8: repository UPDATE failure does not propagate to caller."""
    repo = InMemoryPhaseLogRepository(should_fail_on_update=True)
    writer, _ = build_writer(repository=repo)
    context = sample_context()

    record_started(writer, context, phase_name="response_built")
    record_succeeded(writer, context, phase_name="response_built", duration_ms=12)

    record = next(iter(repo.records.values()))
    assert record.phase_status == "started"
    assert record.completed_at is None


def test_detail_json_uses_allowlist_only() -> None:
    """§14 No.9: detail_json excludes secrets and prompt-like caller fields."""
    context = sample_rich_context()
    detail = build_terminal_detail_json(context, module_id="MOD-RECO-012")

    assert detail["source_module_id"] == "MOD-RECO-012"
    assert detail["pre_filter_candidate_count"] == 42
    assert detail["retrieval_candidate_count"] == 30
    assert detail["post_filter_candidate_count"] == 18
    assert detail["pre_hard_filter_latency_ms"] == 11
    assert detail["final_result_count"] == 1

    forbidden_keys = {"prompt", "api_key", "authorization", "caller_context", "request_body"}
    assert forbidden_keys.isdisjoint(detail.keys())

    writer, repo = build_writer()
    record_started(writer, context, phase_name="retrieval_completed")
    record_succeeded(
        writer,
        context,
        phase_name="retrieval_completed",
        module_id="MOD-RECO-012",
        duration_ms=18,
    )

    persisted_detail = next(iter(repo.records.values())).detail_json
    assert forbidden_keys.isdisjoint(persisted_detail.keys())
    assert persisted_detail.get("source_module_id") == "MOD-RECO-012"


def test_in_memory_repository_runs_without_external_db() -> None:
    """§14 No.10: InMemory repository enables pytest without production DB."""
    repo = InMemoryPhaseLogRepository()
    writer = build_writer(repository=repo)[0]
    context = sample_context()

    for phase_name in ("request_received", "config_resolved"):
        record_started(writer, context, phase_name=phase_name)
        record_succeeded(writer, context, phase_name=phase_name, duration_ms=3)

    assert len(repo.records) == 2
    assert {record.phase_name for record in repo.records.values()} == {
        "request_received",
        "config_resolved",
    }


def test_phase_log_events_match_stub_compatible_shape() -> None:
    """§14 No.11: context.phase_log_events matches StubPhaseLogWriter shape."""
    writer, _repo = build_writer()
    context = sample_context()

    writer.record_phase(
        context,
        phase_name="semantic_extracted",
        phase_status=PhaseStatus.STARTED,
        module_id="MOD-RECO-005",
    )

    assert len(context.phase_log_events) == 1
    event = context.phase_log_events[0]
    assert set(event.keys()) == STUB_COMPATIBLE_EVENT_KEYS
    assert event["phase_name"] == "semantic_extracted"
    assert event["phase_status"] == "started"
    assert event["module_id"] == "MOD-RECO-005"
    assert event["trace_id"] == DEFAULT_TRACE_ID
    assert event["run_id"] == DEFAULT_RUN_ID


def test_trace_id_on_all_persisted_phase_rows() -> None:
    """§14 No.14: trace_id is set on every persisted phase_log row."""
    writer, repo = build_writer()
    context = sample_context()
    phases = ("request_received", "config_resolved", "response_built")

    for phase_name in phases:
        record_started(writer, context, phase_name=phase_name)
        record_succeeded(writer, context, phase_name=phase_name, duration_ms=4)

    assert len(repo.records) == len(phases)
    assert all(record.trace_id == DEFAULT_TRACE_ID for record in repo.records.values())
