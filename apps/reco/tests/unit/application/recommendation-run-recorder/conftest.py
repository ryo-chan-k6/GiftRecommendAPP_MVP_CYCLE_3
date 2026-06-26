"""Test bootstrap and shared fixtures for MOD-RECO-002 unit tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.application.recommendation_run_recorder import RecommendationRunRecorder
from reco.domain import (
    ExecutionMode,
    OccasionCondition,
    RecommendationRequest,
    RelationshipCondition,
)
from reco.infrastructure.db.repositories.pair_master_reader import (
    InMemoryPairMasterReader,
)
from reco.infrastructure.db.repositories.recommendation_run_repository import (
    InMemoryRecommendationRunRepository,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def _load_run_recorder_package() -> None:
    init_path = (
        Path(__file__).resolve().parents[4]
        / "src/reco/application/recommendation-run-recorder/__init__.py"
    )
    spec = importlib.util.spec_from_file_location(
        "reco.application.recommendation_run_recorder",
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load recommendation run recorder package")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_run_recorder_package()

DEFAULT_CONFIG_VERSIONS: dict[str, str] = {
    "semantic_config_version_id": "scv-1",
    "model_version_id": "mv-1",
    "ranking_config_id": "rc-1",
}


@pytest.fixture
def sample_context() -> ExecutionContext:
    return _sample_context()


def _sample_context(*, config_versions: dict[str, str] | None = None) -> ExecutionContext:
    versions = DEFAULT_CONFIG_VERSIONS if config_versions is None else config_versions
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


def build_recorder(
    *,
    pairs: dict[tuple[str, str], str] | None = None,
    fail_writes: bool = False,
    known_request_ids: set[str] | None = None,
    known_version_ids: set[str] | None = None,
    logger: ScaffoldRecoLogger | None = None,
) -> RecommendationRunRecorder:
    pair_reader = InMemoryPairMasterReader(
        pairs=pairs if pairs is not None else {("friend", "birthday"): "pair-1"},
    )
    repository = InMemoryRecommendationRunRepository(
        should_fail_on_write=fail_writes,
        known_request_ids=known_request_ids or set(),
        known_version_ids=known_version_ids or set(),
    )
    return RecommendationRunRecorder(
        run_repository=repository,
        pair_reader=pair_reader,
        logger=logger or ScaffoldRecoLogger(),
    )
