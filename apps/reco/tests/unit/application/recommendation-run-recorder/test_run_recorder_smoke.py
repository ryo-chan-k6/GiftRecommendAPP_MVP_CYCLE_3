"""MOD-RECO-002 Recommendation Run Recorder smoke tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.application.recommendation_run_recorder import (
    RecommendationRunRecorder,
    RunRecorderError,
    RunStateConflictError,
)
from reco.domain import (
    ExecutionMode,
    OccasionCondition,
    RecommendationRequest,
    RelationshipCondition,
    RunStatus,
)
from reco.infrastructure.db.repositories.pair_master_reader import (
    InMemoryPairMasterReader,
)
from reco.infrastructure.db.repositories.recommendation_run_repository import (
    InMemoryRecommendationRunRepository,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def _load_orchestrator_package() -> None:
    init_path = (
        Path(__file__).resolve().parents[4]
        / "src/reco/application/recommendation-orchestrator/__init__.py"
    )
    spec = importlib.util.spec_from_file_location(
        "reco.application.recommendation_orchestrator",
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load recommendation orchestrator package")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_orchestrator_package()


def _sample_context(*, config_versions: dict[str, str] | None = None) -> ExecutionContext:
    versions = (
        {
            "semantic_config_version_id": "scv-1",
            "model_version_id": "mv-1",
            "ranking_config_id": "rc-1",
        }
        if config_versions is None
        else config_versions
    )
    return ExecutionContext(
        recommendation_request=RecommendationRequest(
            request_id="req-run-recorder-1",
            relationship=RelationshipCondition(relationship_code="friend"),
            occasion=OccasionCondition(occasion_code="birthday"),
        ),
        trace_id="trace-run-recorder",
        execution_mode=ExecutionMode.UI,
        config_versions=versions,
    )


def _recorder(
    *,
    pairs: dict[tuple[str, str], str] | None = None,
    fail_writes: bool = False,
) -> RecommendationRunRecorder:
    pair_reader = InMemoryPairMasterReader(
        pairs=pairs if pairs is not None else {("friend", "birthday"): "pair-1"},
    )
    repository = InMemoryRecommendationRunRepository(
        should_fail_on_write=fail_writes,
    )
    return RecommendationRunRecorder(
        run_repository=repository,
        pair_reader=pair_reader,
        logger=ScaffoldRecoLogger(),
    )


def test_record_run_creates_accepted_then_running() -> None:
    recorder = _recorder()
    context = _sample_context()

    updated = recorder.record_run(context)

    assert updated.recommendation_run is not None
    assert updated.recommendation_run.status is RunStatus.RUNNING
    assert updated.run_id is not None
    assert "MOD-RECO-002" in updated.completed_modules

    stored = recorder.run_repository.get_by_id(updated.run_id)
    assert stored is not None
    assert stored.run_status is RunStatus.RUNNING
    assert stored.started_at is not None
    assert stored.completed_at is None


def test_record_run_emits_structured_logs() -> None:
    logger = ScaffoldRecoLogger()
    recorder = RecommendationRunRecorder(
        run_repository=InMemoryRecommendationRunRepository(),
        pair_reader=InMemoryPairMasterReader(
            pairs={("friend", "birthday"): "pair-1"},
        ),
        logger=logger,
    )

    recorder.record_run(_sample_context())

    events = [record.event for record in logger.records]
    assert "recommendation_run_created" in events
    assert "recommendation_run_status_changed" in events


def test_record_run_fails_when_pair_unresolved() -> None:
    recorder = _recorder(pairs={})

    with pytest.raises(RunRecorderError) as exc_info:
        recorder.record_run(_sample_context())

    assert exc_info.value.error_code == "GRS-REC-002"


def test_record_run_fails_when_version_columns_missing() -> None:
    recorder = _recorder()

    with pytest.raises(RunRecorderError) as exc_info:
        recorder.record_run(_sample_context(config_versions={}))

    assert exc_info.value.error_code == "GRS-REC-002"


def test_terminal_update_after_succeeded_raises_conflict() -> None:
    recorder = _recorder()
    context = recorder.record_run(_sample_context())
    context = recorder.apply_transition(context, RunStatus.SUCCEEDED)

    with pytest.raises(RunStateConflictError) as exc_info:
        recorder.apply_transition(context, RunStatus.FAILED)

    assert exc_info.value.error_code == "GRS-REC-201"
