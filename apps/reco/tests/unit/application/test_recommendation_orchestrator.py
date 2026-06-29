"""MOD-RECO-001 Recommendation Orchestrator unit tests (module spec §14)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from reco.application.recommendation_orchestrator import (
    GENERIC_REASON_SUMMARY,
    ORCHESTRATOR_MODULE_ORDER,
    OrchestratorPorts,
    ReasonGenerationOutcome,
    RecommendationOrchestrator,
    build_default_stub_ports,
)
from reco.application.recommendation_orchestrator.stubs import (
    StubConfigResolver,
    StubPipelineModule,
    StubReasonGenerator,
)
from reco.application.recommendation_run_recorder import build_scaffold_run_recorder
from recommendation_orchestrator_helpers import ports_with_user_meaning_stubs
from reco.domain import (
    ExecutionCondition,
    ExecutionMode,
    OccasionCondition,
    ReasonStatus,
    RecommendationRequest,
    RecommendationResult,
    RelationshipCondition,
    ResultStatus,
    RunStatus,
)


def _sample_request(*, mode: ExecutionMode = ExecutionMode.UI) -> RecommendationRequest:
    return RecommendationRequest(
        request_id="req-orchestrator-1",
        relationship=RelationshipCondition(relationship_code="friend"),
        occasion=OccasionCondition(occasion_code="birthday"),
        execution=ExecutionCondition(mode=mode, top_k=5),
    )


def _ports_with(ports: OrchestratorPorts, **overrides: object) -> OrchestratorPorts:
    return replace(ports, **overrides)


# §14 No.1 正常系（ui mode）
def test_ui_mode_success_returns_recommendation_result() -> None:
    ports, _ = build_default_stub_ports()
    ports = ports_with_user_meaning_stubs(ports)
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(mode=ExecutionMode.UI),
        trace_id="trace-ui",
    )

    assert outcome.success is True
    assert outcome.recommendation_result is not None
    assert outcome.recommendation_result.item_count > 0
    assert outcome.execution_context is not None
    assert outcome.execution_context.execution_mode == ExecutionMode.UI
    assert outcome.execution_context.recommendation_run is not None
    assert outcome.execution_context.recommendation_run.status is RunStatus.SUCCEEDED
    assert "model_versions.embedding" in outcome.execution_context.config_versions


def test_default_stub_ports_wires_config_version_resolver() -> None:
    from reco.application.config_version_resolver import ConfigVersionResolver

    ports, _ = build_default_stub_ports()
    assert isinstance(ports.config_resolver, ConfigVersionResolver)


def test_default_stub_ports_wires_user_meaning_modules() -> None:
    from reco.application.external_condition_feature_estimator import (
        ExternalConditionFeatureEstimator,
    )
    from reco.application.internal_condition_feature_estimator import (
        InternalConditionFeatureEstimator,
    )
    from reco.application.query_embedding_generator import QueryEmbeddingGenerator
    from reco.application.user_context_builder import UserContextBuilder
    from reco.application.user_feature_generator import UserFeatureGenerator
    from reco.application.user_meaning_projector import UserMeaningProjector
    from reco.application.user_semantic_extractor import UserSemanticExtractor

    ports, _ = build_default_stub_ports()
    assert isinstance(ports.user_semantic_extractor, UserSemanticExtractor)
    assert isinstance(ports.external_feature_estimator, ExternalConditionFeatureEstimator)
    assert isinstance(ports.internal_feature_estimator, InternalConditionFeatureEstimator)
    assert isinstance(ports.user_feature_generator, UserFeatureGenerator)
    assert isinstance(ports.user_meaning_projector, UserMeaningProjector)
    assert isinstance(ports.user_context_builder, UserContextBuilder)
    assert isinstance(ports.query_embedding_generator, QueryEmbeddingGenerator)


# §14 No.2 正常系（evaluation / batch mode）— Stub が execution_mode を echo する挙動
@pytest.mark.parametrize("mode", [ExecutionMode.EVALUATION, ExecutionMode.BATCH])
def test_execution_mode_is_passed_to_config_resolver(mode: ExecutionMode) -> None:
    ports, _ = build_default_stub_ports()
    ports = ports_with_user_meaning_stubs(ports)
    ports = _ports_with(ports, config_resolver=StubConfigResolver())
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(mode=mode),
        trace_id=f"trace-{mode.value}",
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    assert outcome.execution_context.config_versions["execution_mode"] == mode.value


# §14 No.3 処理順序
def test_orchestrator_runs_all_modules_in_order() -> None:
    ports, _ = build_default_stub_ports()
    ports = ports_with_user_meaning_stubs(ports)
    orchestrator = RecommendationOrchestrator(ports)
    outcome = orchestrator.run(
        _sample_request(),
        trace_id="trace-1",
    )

    assert outcome.success is True
    assert outcome.recommendation_result is not None
    assert outcome.execution_context is not None
    assert outcome.execution_context.completed_modules == list(ORCHESTRATOR_MODULE_ORDER)


# §14 No.4 Ranking 責務分離
def test_final_score_calculator_runs_before_final_ranker() -> None:
    ports, _ = build_default_stub_ports()
    ports = ports_with_user_meaning_stubs(ports)
    call_order: list[str] = []

    def track(module: StubPipelineModule) -> None:
        original = module.execute

        def wrapped(context):
            call_order.append(module.module_id)
            return original(context)

        module.execute = wrapped  # type: ignore[method-assign]

    track(ports.final_score_calculator)  # type: ignore[arg-type]
    track(ports.final_ranker)  # type: ignore[arg-type]

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-ranking-order",
    )

    assert outcome.success is True
    assert call_order.index("MOD-RECO-019") < call_order.index("MOD-RECO-020")


# §14 No.5 境界値（0件）— Orchestrator は空 Result を正常終了。GRS-REC-001 は api 層で付与。
def test_zero_candidates_completes_with_empty_result() -> None:
    ports, helpers = build_default_stub_ports()
    ports = ports_with_user_meaning_stubs(ports)

    def build_empty_result(context):
        context.completed_modules.append("MOD-RECO-021")
        run_id = context.run_id or "run-empty"
        context.recommendation_result = RecommendationResult(
            run_id=run_id,
            request_id=context.recommendation_request.request_id,
            items=(),
            result_status=ResultStatus.EMPTY,
            version_info=dict(context.config_versions),
        )
        return context

    ports.result_builder.execute = build_empty_result  # type: ignore[method-assign]

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-empty",
    )

    assert outcome.success is True
    assert outcome.recommendation_result is not None
    assert outcome.recommendation_result.item_count == 0
    assert outcome.recommendation_result.result_status == ResultStatus.EMPTY
    assert helpers["metric_logger"].recorded[-1]["final_result_count"] == 0


# §14 No.6 例外系（下位失敗）
@pytest.mark.parametrize(
    ("module_attr", "error_code", "blocked_module"),
    [
        ("user_semantic_extractor", "GRS-REC-004", "MOD-RECO-005"),
        ("candidate_retriever", "GRS-REC-009", "MOD-RECO-013"),
        ("risk_scorer", "GRS-REC-012", "MOD-RECO-019"),
    ],
)
def test_pipeline_module_failure_propagates_error_code(
    module_attr: str,
    error_code: str,
    blocked_module: str,
) -> None:
    ports, helpers = build_default_stub_ports()
    if module_attr in ("candidate_retriever", "risk_scorer"):
        ports = ports_with_user_meaning_stubs(ports)
    failing = getattr(ports, module_attr)
    failed_module = StubPipelineModule(
        module_id=failing.module_id,
        phase_name=failing.phase_name,
        should_fail=True,
    )
    ports = _ports_with(ports, **{module_attr: failed_module})

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id=f"trace-fail-{module_attr}",
    )

    assert outcome.success is False
    assert outcome.reco_error is not None
    assert outcome.reco_error.error_code == error_code
    assert outcome.execution_context is not None
    assert blocked_module not in outcome.execution_context.completed_modules
    assert helpers["error_handler"].error_log_events


# §14 No.7 依存モジュール失敗（MOD-RECO-003）
def test_downstream_failure_stops_pipeline_and_returns_error() -> None:
    ports, helpers = build_default_stub_ports()
    ports = _ports_with(
        ports,
        config_resolver=StubConfigResolver(should_fail=True),
    )

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-failure",
    )

    assert outcome.success is False
    assert outcome.reco_error is not None
    assert outcome.reco_error.error_code == "GRS-REC-003"
    assert outcome.execution_context is not None
    assert "MOD-RECO-002" not in outcome.execution_context.completed_modules
    assert "MOD-RECO-004" not in outcome.execution_context.completed_modules
    assert helpers["error_handler"].error_log_events


# §14 No.7b MOD-RECO-002 失敗（003 成功後に 002 が失敗）
def test_run_recorder_failure_after_config_resolver() -> None:
    ports, helpers = build_default_stub_ports()
    ports = _ports_with(
        ports,
        run_recorder=build_scaffold_run_recorder(should_fail=True),
    )

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-run-recorder-fail",
    )

    assert outcome.success is False
    assert outcome.reco_error is not None
    assert outcome.reco_error.error_code == "GRS-REC-002"
    assert outcome.execution_context is not None
    assert "MOD-RECO-003" in outcome.execution_context.completed_modules
    assert "MOD-RECO-002" not in outcome.execution_context.completed_modules
    assert "MOD-RECO-004" not in outcome.execution_context.completed_modules
    assert helpers["error_handler"].error_log_events


# §14 No.8 Phase Log 契機（unit: スタブ呼び出し記録）
def test_phase_log_records_major_phase_boundaries() -> None:
    ports, helpers = build_default_stub_ports()
    ports = ports_with_user_meaning_stubs(ports)
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-phase-log",
    )

    assert outcome.success is True
    events = helpers["phase_log_writer"].events
    phase_names = {event["phase_name"] for event in events}
    assert "request_received" in phase_names
    assert "config_resolved" in phase_names
    assert "response_built" in phase_names

    config_events = [event for event in events if event["phase_name"] == "config_resolved"]
    assert any(event["phase_status"] == "started" for event in config_events)
    assert any(event["phase_status"] == "succeeded" for event in config_events)


# §14 No.9 Error Log 接続（unit: MOD-RECO-024 委譲のスタブ記録）
def test_error_handler_records_failure_for_error_log_delegation() -> None:
    ports, helpers = build_default_stub_ports()
    ports = _ports_with(ports, config_resolver=StubConfigResolver(should_fail=True))
    trace_id = "trace-error-log"

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id=trace_id,
    )

    assert outcome.success is False
    error_events = helpers["error_handler"].error_log_events
    assert len(error_events) == 1
    assert error_events[0]["module_id"] == "MOD-RECO-003"
    assert error_events[0]["error_code"] == "GRS-REC-003"
    assert error_events[0]["trace_id"] == trace_id
    assert outcome.execution_context is not None
    assert outcome.execution_context.error_log_events == error_events


# §14 No.12 trace 伝播
def test_trace_id_propagates_to_phase_log_and_metrics() -> None:
    ports, helpers = build_default_stub_ports()
    ports = ports_with_user_meaning_stubs(ports)
    trace_id = "trace-propagation-xyz"

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id=trace_id,
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    assert outcome.execution_context.trace_id == trace_id
    assert all(event["trace_id"] == trace_id for event in helpers["phase_log_writer"].events)
    assert helpers["metric_logger"].recorded[-1]["trace_id"] == trace_id


# §14 No.13 Reason fallback
def test_reason_fallback_injects_generic_reason() -> None:
    ports, _ = build_default_stub_ports()
    ports = ports_with_user_meaning_stubs(ports)
    ports = _ports_with(
        ports,
        reason_generator=StubReasonGenerator(
            outcome=ReasonGenerationOutcome.UNRECOVERABLE
        ),
    )

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-fallback",
    )

    assert outcome.success is True
    assert outcome.recommendation_result is not None
    item = outcome.recommendation_result.items[0]
    assert item.reason_summary == GENERIC_REASON_SUMMARY
    assert item.is_fallback is True
    assert item.reason_status == ReasonStatus.COMPLETED
