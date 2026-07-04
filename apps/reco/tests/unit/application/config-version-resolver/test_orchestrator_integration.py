"""MOD-RECO-003 Orchestrator integration (003 resolve → 002 INSERT)."""

from __future__ import annotations

from dataclasses import replace

from reco.application.config_version_resolver import (
    DEFAULT_EMBEDDING_MODEL_VERSION_ID,
    DEFAULT_MATCHING_CONFIG_ID,
    DEFAULT_RANKING_CONFIG_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    build_default_config_resolver,
)
from reco.application.recommendation_orchestrator import (
    OrchestratorPorts,
    RecommendationOrchestrator,
    build_default_stub_ports,
)
from reco.application.recommendation_run_recorder import build_scaffold_run_recorder
from recommendation_orchestrator_helpers import (
    ports_with_matching_stubs,
    ports_with_ranking_stubs,
    ports_with_retrieval_stubs,
    ports_with_user_meaning_stubs,
)
from reco.domain import (
    ExecutionCondition,
    ExecutionMode,
    OccasionCondition,
    RecommendationRequest,
    RelationshipCondition,
    RunStatus,
)


def _integration_request() -> RecommendationRequest:
    return RecommendationRequest(
        request_id="req-orchestrator-integration-1",
        relationship=RelationshipCondition(relationship_code="friend"),
        occasion=OccasionCondition(occasion_code="birthday"),
        execution=ExecutionCondition(mode=ExecutionMode.UI, top_k=5),
    )


def _ports_with(ports: OrchestratorPorts, **overrides: object) -> OrchestratorPorts:
    return replace(ports, **overrides)


def test_config_resolver_runs_before_run_recorder_and_inserts_run() -> None:
    """§14 No.13: 003 先行解決後に 002 INSERT が成功する（本実装配線）."""
    run_recorder = build_scaffold_run_recorder()
    ports, _ = build_default_stub_ports()
    ports = _ports_with(
        ports,
        config_resolver=build_default_config_resolver(),
        run_recorder=run_recorder,
    )
    ports = ports_with_user_meaning_stubs(ports)
    ports = ports_with_retrieval_stubs(ports)
    ports = ports_with_matching_stubs(ports)
    ports = ports_with_ranking_stubs(ports)

    outcome = RecommendationOrchestrator(ports).run(
        _integration_request(),
        trace_id="trace-config-run-integration",
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    ctx = outcome.execution_context

    assert ctx.config_versions["semantic_config_version_id"] == (
        DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    )
    assert ctx.config_versions["model_versions.embedding"] == (
        DEFAULT_EMBEDDING_MODEL_VERSION_ID
    )
    assert ctx.config_versions["ranking_config_id"] == DEFAULT_RANKING_CONFIG_ID
    assert ctx.config_versions["matching_config_id"] == DEFAULT_MATCHING_CONFIG_ID

    completed = ctx.completed_modules
    assert "MOD-RECO-003" in completed
    assert "MOD-RECO-002" in completed
    assert completed.index("MOD-RECO-003") < completed.index("MOD-RECO-002")

    assert ctx.recommendation_run is not None
    assert ctx.recommendation_run.status is RunStatus.SUCCEEDED
    assert ctx.recommendation_run.semantic_config_version == (
        DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    )
    assert ctx.recommendation_run.model_version == DEFAULT_EMBEDDING_MODEL_VERSION_ID

    stored = run_recorder.run_repository.get_by_id(ctx.recommendation_run.run_id)
    assert stored is not None
    assert stored.matching_config_id == DEFAULT_MATCHING_CONFIG_ID
