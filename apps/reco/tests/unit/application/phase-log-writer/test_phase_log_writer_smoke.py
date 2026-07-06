"""MOD-RECO-028 Phase Log Writer smoke tests (implementation Task)."""

from __future__ import annotations

from conftest import (
    DEFAULT_RUN_ID,
    DEFAULT_TRACE_ID,
    build_writer,
    record_started,
    record_succeeded,
    sample_context,
)
from reco.application.phase_log_writer.repository import InMemoryPhaseLogRepository
from reco.application.recommendation_orchestrator.ports import PhaseStatus


def test_record_phase_started_inserts_phase_log_row() -> None:
    writer, repo = build_writer()
    context = sample_context()

    record_started(writer, context, phase_name="request_received")

    assert len(repo.records) == 1
    record = next(iter(repo.records.values()))
    assert record.phase_name == "request_received"
    assert record.phase_status == "started"
    assert record.owner_id == DEFAULT_RUN_ID
    assert record.trace_id == DEFAULT_TRACE_ID


def test_record_phase_terminal_updates_started_row() -> None:
    writer, repo = build_writer()
    context = sample_context()

    record_started(writer, context, phase_name="config_resolved")
    record_succeeded(writer, context, phase_name="config_resolved", duration_ms=25)

    assert len(repo.records) == 1
    record = next(iter(repo.records.values()))
    assert record.phase_status == "succeeded"
    assert record.completed_at is not None
    assert record.duration_ms == 25


def test_record_phase_appends_stub_compatible_in_memory_events() -> None:
    writer, _repo = build_writer()
    context = sample_context()

    writer.record_phase(
        context,
        phase_name="request_received",
        phase_status=PhaseStatus.STARTED,
        module_id="MOD-RECO-001",
    )

    assert len(context.phase_log_events) == 1
    event = context.phase_log_events[0]
    assert event["phase_name"] == "request_received"
    assert event["phase_status"] == "started"
    assert event["module_id"] == "MOD-RECO-001"
    assert event["trace_id"] == DEFAULT_TRACE_ID
    assert event["run_id"] == DEFAULT_RUN_ID


def test_record_phase_buffers_until_run_id_is_available() -> None:
    writer, repo = build_writer()
    context = sample_context(include_run=False)

    record_started(writer, context, phase_name="request_received")
    assert repo.records == {}
    assert len(context.phase_log_events) == 1

    context.recommendation_run = sample_context().recommendation_run
    record_succeeded(writer, context, phase_name="request_received", duration_ms=8)

    assert len(repo.records) == 1
    record = next(iter(repo.records.values()))
    assert record.phase_status == "succeeded"
    assert record.duration_ms == 8


def test_record_phase_skips_db_for_enum_outside_phase_name() -> None:
    writer, repo = build_writer()
    context = sample_context()

    writer.record_phase(
        context,
        phase_name="run_recorded",
        phase_status=PhaseStatus.STARTED,
    )

    assert repo.records == {}
    assert len(context.phase_log_events) == 1


def test_record_phase_does_not_propagate_repository_insert_failure() -> None:
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
