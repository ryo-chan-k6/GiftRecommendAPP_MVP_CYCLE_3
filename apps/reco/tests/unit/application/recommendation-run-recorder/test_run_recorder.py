"""MOD-RECO-002 Recommendation Run Recorder unit tests (module spec §14)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from conftest import _sample_context, build_recorder
from reco.application.recommendation_orchestrator import (
    OrchestratorPorts,
    RecommendationOrchestrator,
    build_default_stub_ports,
)
from reco.application.recommendation_run_recorder import (
    RunRecorderError,
    RunStateConflictError,
    build_scaffold_run_recorder,
)
from reco.domain import RecommendationRun, RunStatus
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def _ports_with(ports: OrchestratorPorts, **overrides: object) -> OrchestratorPorts:
    return replace(ports, **overrides)


# §14 No.1 正常系（accepted INSERT）
def test_record_run_creates_accepted_row_and_returns_run_id() -> None:
    logger = ScaffoldRecoLogger()
    recorder = build_recorder(logger=logger)
    context = _sample_context()

    updated = recorder.record_run(context)

    assert updated.recommendation_run is not None
    assert updated.run_id is not None
    assert "MOD-RECO-002" in updated.completed_modules

    created_logs = [
        record for record in logger.records if record.event == "recommendation_run_created"
    ]
    assert len(created_logs) == 1
    assert created_logs[0].attributes["run_status"] == RunStatus.ACCEPTED.value
    assert created_logs[0].attributes["recommendation_run_id"] == updated.run_id


# §14 No.1 続き: record_run 完了時点では running
def test_record_run_transitions_to_running_with_started_at() -> None:
    recorder = build_recorder()
    updated = recorder.record_run(_sample_context())

    assert updated.recommendation_run is not None
    assert updated.recommendation_run.status is RunStatus.RUNNING

    stored = recorder.run_repository.get_by_id(updated.run_id)
    assert stored is not None
    assert stored.run_status is RunStatus.RUNNING
    assert stored.started_at is not None
    assert stored.completed_at is None


# §14 No.2 正常系（running → succeeded）
def test_apply_transition_to_succeeded_sets_completed_at() -> None:
    recorder = build_recorder()
    context = recorder.record_run(_sample_context())

    updated = recorder.apply_transition(context, RunStatus.SUCCEEDED)

    assert updated.recommendation_run is not None
    assert updated.recommendation_run.status is RunStatus.SUCCEEDED

    stored = recorder.run_repository.get_by_id(updated.run_id)
    assert stored is not None
    assert stored.run_status is RunStatus.SUCCEEDED
    assert stored.started_at is not None
    assert stored.completed_at is not None


# §14 No.3 正常系（failed）
def test_apply_transition_to_failed_sets_completed_at() -> None:
    recorder = build_recorder()
    context = recorder.record_run(_sample_context())

    updated = recorder.apply_transition(context, RunStatus.FAILED)

    stored = recorder.run_repository.get_by_id(updated.run_id)
    assert stored is not None
    assert stored.run_status is RunStatus.FAILED
    assert stored.completed_at is not None


# §14 No.4 境界値（同一 Request 再実行）— unit: 複数 Run INSERT 可能
def test_same_request_can_create_multiple_runs() -> None:
    recorder = build_recorder()
    context = _sample_context()

    first = recorder.record_run(context)
    second = recorder.record_run(_sample_context())

    assert first.run_id is not None
    assert second.run_id is not None
    assert first.run_id != second.run_id
    assert len(recorder.run_repository.runs) == 2


# §14 No.5 例外系（Pair 未解決）
def test_record_run_fails_when_pair_unresolved() -> None:
    recorder = build_recorder(pairs={})

    with pytest.raises(RunRecorderError) as exc_info:
        recorder.record_run(_sample_context())

    assert exc_info.value.error_code == "GRS-REC-002"
    assert recorder.run_repository.runs == {}


# §14 No.6 例外系（version 欠落）
@pytest.mark.parametrize(
    "config_versions",
    [
        {},
        {"semantic_config_version_id": "scv-1"},
        {"semantic_config_version_id": "scv-1", "model_version_id": "mv-1"},
    ],
)
def test_record_run_fails_when_version_columns_missing(
    config_versions: dict[str, str],
) -> None:
    recorder = build_recorder()

    with pytest.raises(RunRecorderError) as exc_info:
        recorder.record_run(_sample_context(config_versions=config_versions))

    assert exc_info.value.error_code == "GRS-REC-002"


def test_record_run_accepts_fallback_version_keys() -> None:
    recorder = build_recorder()
    context = _sample_context(
        config_versions={
            "semantic_config_version": "scv-fallback",
            "model_version": "mv-fallback",
            "ranking_config": "rc-fallback",
        },
    )

    updated = recorder.record_run(context)

    assert updated.run_id is not None
    stored = recorder.run_repository.get_by_id(updated.run_id)
    assert stored is not None
    assert stored.semantic_config_version_id == "scv-fallback"
    assert stored.model_version_id == "mv-fallback"
    assert stored.ranking_config_id == "rc-fallback"



def test_record_run_accepts_model_versions_embedding_key() -> None:
    """MOD-RECO-003 §9.1: model_versions.embedding を Run 列 model_version_id へマップ."""
    recorder = build_recorder()
    context = _sample_context(
        config_versions={
            "semantic_config_version_id": "scv-1",
            "model_versions.embedding": "mv-embedding-1",
            "ranking_config_id": "rc-1",
        },
    )

    updated = recorder.record_run(context)

    assert updated.run_id is not None
    stored = recorder.run_repository.get_by_id(updated.run_id)
    assert stored is not None
    assert stored.model_version_id == "mv-embedding-1"

# §14 No.7 例外系（FK 違反）— unit: 存在しない recommendation_request_id
def test_record_run_fails_when_request_does_not_exist() -> None:
    recorder = build_recorder(known_request_ids={"req-other"})

    with pytest.raises(RunRecorderError) as exc_info:
        recorder.record_run(_sample_context())

    assert exc_info.value.error_code == "GRS-REC-002"
    assert "not found" in exc_info.value.message


def test_record_run_fails_when_config_version_ids_do_not_exist() -> None:
    recorder = build_recorder(
        known_version_ids={"scv-1", "mv-1"},
    )

    with pytest.raises(RunRecorderError) as exc_info:
        recorder.record_run(_sample_context())

    assert exc_info.value.error_code == "GRS-REC-002"


def test_record_run_fails_when_insert_raises() -> None:
    recorder = build_recorder(fail_writes=True)

    with pytest.raises(RunRecorderError) as exc_info:
        recorder.record_run(_sample_context())

    assert exc_info.value.error_code == "GRS-REC-002"


# §14 No.8 終端ガード
@pytest.mark.parametrize(
    "terminal",
    [RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELED],
)
def test_terminal_update_raises_grs_rec_201(terminal: RunStatus) -> None:
    recorder = build_recorder()
    context = recorder.record_run(_sample_context())
    if terminal is not RunStatus.SUCCEEDED:
        context = recorder.apply_transition(context, terminal)
    else:
        context = recorder.apply_transition(context, RunStatus.SUCCEEDED)

    with pytest.raises(RunStateConflictError) as exc_info:
        recorder.apply_transition(context, RunStatus.RUNNING)

    assert exc_info.value.error_code == "GRS-REC-201"


# §14 No.9 状態遷移整合 — apply_transition 経由
def test_apply_transition_rejects_accepted_to_succeeded() -> None:
    recorder = build_recorder()
    repository = recorder.run_repository
    accepted = repository.insert_accepted(
        request_id="req-1",
        pair_id="pair-1",
        semantic_config_version_id="scv-1",
        model_version_id="mv-1",
        ranking_config_id="rc-1",
    )
    context = _sample_context()
    context.recommendation_run = RecommendationRun(
        run_id=accepted.run_id,
        request_id=accepted.request_id,
        status=RunStatus.ACCEPTED,
    )

    with pytest.raises(RunStateConflictError) as exc_info:
        recorder.apply_transition(context, RunStatus.SUCCEEDED)

    assert exc_info.value.error_code == "GRS-REC-201"


# §14 No.10 Orchestrator 連携（記録失敗時にパイプライン中断）
def test_orchestrator_stops_when_run_recorder_fails() -> None:
    ports, helpers = build_default_stub_ports()
    ports = _ports_with(
        ports,
        run_recorder=build_scaffold_run_recorder(should_fail=True),
    )

    outcome = RecommendationOrchestrator(ports).run(
        _sample_context().recommendation_request,
        trace_id="trace-run-recorder-fail",
    )

    assert outcome.success is False
    assert outcome.reco_error is not None
    assert outcome.reco_error.error_code == "GRS-REC-002"
    assert outcome.execution_context is not None
    assert "MOD-RECO-003" in outcome.execution_context.completed_modules
    assert "MOD-RECO-002" not in outcome.execution_context.completed_modules
    assert helpers["error_handler"].error_log_events


# §14 No.11 DB / ログ — integration 観点のため本 Task では Orchestrator 側で部分確認
def test_record_run_emits_structured_logs_with_trace_id() -> None:
    logger = ScaffoldRecoLogger()
    recorder = build_recorder(logger=logger)

    recorder.record_run(_sample_context())

    events = [record.event for record in logger.records]
    assert "recommendation_run_created" in events
    assert "recommendation_run_status_changed" in events
    assert all(record.context.trace_id == "trace-run-recorder" for record in logger.records)


# §14 No.12 0件結果 — Run は succeeded（候補件数に非依存）
def test_zero_candidate_completion_can_mark_run_succeeded() -> None:
    recorder = build_recorder()
    context = recorder.record_run(_sample_context())

    updated = recorder.apply_transition(context, RunStatus.SUCCEEDED)

    assert updated.recommendation_run is not None
    assert updated.recommendation_run.status is RunStatus.SUCCEEDED


# §14 No.13 canceled（任意）
def test_apply_transition_to_canceled_sets_completed_at() -> None:
    recorder = build_recorder()
    context = recorder.record_run(_sample_context())

    updated = recorder.apply_transition(context, RunStatus.CANCELED)

    stored = recorder.run_repository.get_by_id(updated.run_id)
    assert stored is not None
    assert stored.run_status is RunStatus.CANCELED
    assert stored.completed_at is not None


def test_record_run_is_idempotent_when_already_running() -> None:
    recorder = build_recorder()
    context = recorder.record_run(_sample_context())
    run_id = context.run_id

    replayed = recorder.record_run(context)

    assert replayed.run_id == run_id
    assert replayed.recommendation_run is not None
    assert replayed.recommendation_run.status is RunStatus.RUNNING


def test_record_run_rejects_existing_non_running_run() -> None:
    recorder = build_recorder()
    context = recorder.record_run(_sample_context())
    context.recommendation_run = context.recommendation_run.with_status(
        RunStatus.SUCCEEDED,
    )

    with pytest.raises(RunRecorderError) as exc_info:
        recorder.record_run(context)

    assert exc_info.value.error_code == "GRS-REC-002"
