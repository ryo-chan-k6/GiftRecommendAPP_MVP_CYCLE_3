"""MOD-RECO-001 Recommendation Orchestrator unit tests (module spec §14)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from reco.application.recommendation_orchestrator import (
    GENERIC_REASON_SUMMARY,
    ORCHESTRATOR_MODULE_ORDER,
    PIPELINE_HARD_TIMEOUT_MS,
    OrchestratorPorts,
    ReasonGenerationOutcome,
    RecommendationOrchestrator,
    build_default_stub_ports,
)
from reco.application.recommendation_orchestrator.stubs import (
    StubPartialFallbackReasonGenerator,
    StubConfigResolver,
    StubPipelineModule,
    StubReasonGenerator,
)
from reco.application.recommendation_run_recorder import build_scaffold_run_recorder
from reco.application.recommendation_orchestrator.phase_name import (
    ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES,
)
from recommendation_orchestrator_helpers import (
    _MATCHING_MODULE_IDS,
    _OUTPUT_MODULE_IDS,
    _RANKING_MODULE_IDS,
    _RETRIEVAL_MODULE_IDS,
    _USER_MEANING_MODULE_IDS,
    assert_matching_execution_context_populated,
    assert_output_execution_context_populated,
    assert_ranking_execution_context_populated,
    assert_retrieval_execution_context_populated,
    assert_user_meaning_execution_context_populated,
    build_wired_default_composition_ports,
    build_wired_ports_with_zero_matching_candidates,
    build_orchestrator_with_elapsed_ms,
    in_memory_error_log_records,
    in_memory_metric_log_records,
    in_memory_phase_log_records,
    in_memory_recommendation_run_records,
    ports_with_matching_stubs,
    ports_with_output_stubs,
    ports_with_ranking_stubs,
    ports_with_retrieval_stubs,
    ports_with_user_meaning_stubs,
)
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


def _wired_ports() -> tuple[OrchestratorPorts, dict[str, object]]:
    return build_wired_default_composition_ports()


# §14 No.1 正常系（ui mode）— デフォルト composition（User Meaning 本実装）
def test_ui_mode_success_returns_recommendation_result() -> None:
    ports, _ = _wired_ports()
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


def test_default_stub_ports_wires_reco_error_handler() -> None:
    from reco.application.reco_error_handler import RecoErrorHandler

    ports, _ = build_default_stub_ports()
    assert isinstance(ports.error_handler, RecoErrorHandler)


def test_default_stub_ports_wires_metric_logger() -> None:
    from reco.application.metric_logger import MetricLogger

    ports, _ = build_default_stub_ports()
    assert isinstance(ports.metric_logger, MetricLogger)


def test_default_stub_ports_wires_retrieval_modules() -> None:
    from reco.application.candidate_retriever import CandidateRetriever
    from reco.application.post_hard_filter_executor import PostHardFilterExecutor

    ports, _ = build_default_stub_ports()
    assert isinstance(ports.candidate_retriever, CandidateRetriever)
    assert isinstance(ports.post_hard_filter, PostHardFilterExecutor)


def test_default_stub_ports_wires_matching_modules() -> None:
    from reco.application.context_scorer import ContextScorer
    from reco.application.feature_matcher import FeatureMatcher
    from reco.application.meaning_match_aggregator import MeaningMatchAggregator

    ports, _ = build_default_stub_ports()
    assert isinstance(ports.feature_matcher, FeatureMatcher)
    assert isinstance(ports.meaning_match_aggregator, MeaningMatchAggregator)
    assert isinstance(ports.context_scorer, ContextScorer)


def test_default_stub_ports_wires_ranking_modules() -> None:
    from reco.application.final_ranker import FinalRanker
    from reco.application.final_score_calculator import FinalScoreCalculator
    from reco.application.popularity_scorer import PopularityScorer
    from reco.application.risk_scorer import RiskScorer

    ports, _ = build_default_stub_ports()
    assert isinstance(ports.popularity_scorer, PopularityScorer)
    assert isinstance(ports.risk_scorer, RiskScorer)
    assert isinstance(ports.final_score_calculator, FinalScoreCalculator)
    assert isinstance(ports.final_ranker, FinalRanker)


def test_default_stub_ports_wires_output_modules() -> None:
    from reco.application.reason_generator import ReasonGenerator
    from reco.application.recommendation_result_builder import RecommendationResultBuilder
    from reco.application.result_snapshot_builder import ResultSnapshotBuilder

    ports, _ = build_default_stub_ports()
    assert isinstance(ports.result_builder, RecommendationResultBuilder)
    assert isinstance(ports.snapshot_builder, ResultSnapshotBuilder)
    assert isinstance(ports.reason_generator, ReasonGenerator)


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


def test_default_composition_completes_user_meaning_phase_modules() -> None:
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-user-meaning-phase",
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    completed = outcome.execution_context.completed_modules
    for module_id in _USER_MEANING_MODULE_IDS:
        assert module_id in completed
    assert completed.index("MOD-RECO-004") < completed.index("MOD-RECO-010")


def test_default_composition_populates_user_meaning_execution_context() -> None:
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-user-meaning-context",
    )

    assert outcome.success is True
    ctx = outcome.execution_context
    assert ctx is not None
    assert_user_meaning_execution_context_populated(ctx)


def test_default_composition_completes_retrieval_phase_modules() -> None:
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-retrieval-phase",
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    completed = outcome.execution_context.completed_modules
    for module_id in _RETRIEVAL_MODULE_IDS:
        assert module_id in completed
    assert completed.index("MOD-RECO-010") < completed.index("MOD-RECO-012")
    assert completed.index("MOD-RECO-012") < completed.index("MOD-RECO-013")


def test_default_composition_populates_retrieval_execution_context() -> None:
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-retrieval-context",
    )

    assert outcome.success is True
    ctx = outcome.execution_context
    assert ctx is not None
    assert_retrieval_execution_context_populated(ctx)


def test_default_composition_completes_matching_phase_modules() -> None:
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-matching-phase",
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    completed = outcome.execution_context.completed_modules
    for module_id in _MATCHING_MODULE_IDS:
        assert module_id in completed
    assert completed.index("MOD-RECO-013") < completed.index("MOD-RECO-014")
    assert completed.index("MOD-RECO-014") < completed.index("MOD-RECO-015")
    assert completed.index("MOD-RECO-015") < completed.index("MOD-RECO-016")
    assert completed.index("MOD-RECO-016") < completed.index("MOD-RECO-017")


def test_default_composition_populates_matching_execution_context() -> None:
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-matching-context",
    )

    assert outcome.success is True
    ctx = outcome.execution_context
    assert ctx is not None
    assert_matching_execution_context_populated(ctx)


def test_default_composition_completes_ranking_phase_modules() -> None:
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-ranking-phase",
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    completed = outcome.execution_context.completed_modules
    for module_id in _RANKING_MODULE_IDS:
        assert module_id in completed
    assert completed.index("MOD-RECO-016") < completed.index("MOD-RECO-017")
    assert completed.index("MOD-RECO-017") < completed.index("MOD-RECO-018")
    assert completed.index("MOD-RECO-018") < completed.index("MOD-RECO-019")
    assert completed.index("MOD-RECO-019") < completed.index("MOD-RECO-020")


def test_default_composition_populates_ranking_execution_context() -> None:
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-ranking-context",
    )

    assert outcome.success is True
    ctx = outcome.execution_context
    assert ctx is not None
    assert_ranking_execution_context_populated(ctx)


def test_default_composition_completes_output_phase_modules() -> None:
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-output-phase",
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    completed = outcome.execution_context.completed_modules
    for module_id in _OUTPUT_MODULE_IDS:
        assert module_id in completed
    assert completed.index("MOD-RECO-020") < completed.index("MOD-RECO-021")
    assert completed.index("MOD-RECO-021") < completed.index("MOD-RECO-022")
    assert completed.index("MOD-RECO-022") < completed.index("MOD-RECO-023")


def test_default_composition_populates_output_execution_context() -> None:
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-output-context",
    )

    assert outcome.success is True
    ctx = outcome.execution_context
    assert ctx is not None
    assert_output_execution_context_populated(ctx)


# §14 No.2 正常系（evaluation / batch mode）— Stub が execution_mode を echo する挙動
@pytest.mark.parametrize("mode", [ExecutionMode.EVALUATION, ExecutionMode.BATCH])
def test_execution_mode_is_passed_to_config_resolver(mode: ExecutionMode) -> None:
    ports, _ = build_default_stub_ports()
    ports = ports_with_user_meaning_stubs(ports)
    ports = ports_with_retrieval_stubs(ports)
    ports = ports_with_matching_stubs(ports)
    ports = ports_with_ranking_stubs(ports)
    ports = ports_with_output_stubs(ports)
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
    ports, _ = _wired_ports()
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
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-ranking-order",
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    completed = outcome.execution_context.completed_modules
    assert completed.index("MOD-RECO-019") < completed.index("MOD-RECO-020")


# §19 No.1 / No.4 / No.5 — Matching 対象 0 件時の Orchestrator 早期終了
def test_section19_zero_matching_skips_matching_ranking_and_returns_empty_result() -> None:
    ports, helpers = build_wired_ports_with_zero_matching_candidates()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-section19-zero-matching",
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    completed = outcome.execution_context.completed_modules
    assert "MOD-RECO-014" in completed
    assert "MOD-RECO-015" not in completed
    assert "MOD-RECO-016" not in completed
    assert "MOD-RECO-017" not in completed
    assert "MOD-RECO-020" not in completed
    # 本番配線（本実装 021/022/023）でも GRS-REC-012 にならず empty 完了する
    assert "MOD-RECO-021" in completed
    assert "MOD-RECO-022" in completed
    assert "MOD-RECO-023" in completed
    assert outcome.execution_context.ranked_items is not None
    assert outcome.execution_context.ranked_items.entries == ()
    assert outcome.execution_context.feature_matcher_candidate_count == 0
    assert outcome.recommendation_result is not None
    assert outcome.recommendation_result.item_count == 0
    assert outcome.recommendation_result.result_status == ResultStatus.EMPTY
    assert helpers["metric_logger"].recorded[-1]["final_result_count"] == 0


# §19 No.2 — Matching 対象 ≥ 1 のとき 015 以降が呼ばれる
def test_section19_matching_target_present_runs_meaning_match_aggregator() -> None:
    ports, _ = _wired_ports()
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-section19-matching-present",
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    completed = outcome.execution_context.completed_modules
    assert "MOD-RECO-014" in completed
    assert "MOD-RECO-015" in completed
    assert "MOD-RECO-016" in completed
    assert outcome.execution_context.feature_matcher_candidate_count == 2


# §19 No.3 — MOD-RECO-014 失敗時は GRS-REC-011 で中断（015 未到達）
def test_section19_feature_matcher_failure_aborts_before_meaning_match_aggregator() -> None:
    ports, helpers = _wired_ports()
    ports = _ports_with(
        ports,
        feature_matcher=StubPipelineModule(
            module_id="MOD-RECO-014",
            phase_name="feature_matched",
            should_fail=True,
        ),
    )

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-section19-feature-matcher-fail",
    )

    assert outcome.success is False
    assert outcome.reco_error is not None
    assert outcome.reco_error.error_code == "GRS-REC-011"
    assert outcome.execution_context is not None
    assert "MOD-RECO-015" not in outcome.execution_context.completed_modules
    assert outcome.execution_context.error_log_events
    assert outcome.reco_error.phase_name == "matching_completed"


# §14 No.5 境界値（0件）— Orchestrator は空 Result を正常終了。GRS-REC-001 は api 層で付与。
def test_zero_candidates_completes_with_empty_result() -> None:
    ports, helpers = _wired_ports()

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

    snapshot_builder = ports.snapshot_builder

    def snapshot_execute(context):
        context.completed_modules.append(snapshot_builder.module_id)
        return context

    ports.snapshot_builder.execute = snapshot_execute  # type: ignore[method-assign]

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
    ports, helpers = _wired_ports()
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
    assert outcome.execution_context.error_log_events


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
    assert outcome.execution_context.error_log_events


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
    assert outcome.execution_context.error_log_events
    assert outcome.reco_error.phase_name == "request_received"


# §14 No.8 Phase Log 契機（integration: MOD-RECO-001→028 本実装）
def test_phase_log_records_major_phase_boundaries() -> None:
    ports, helpers = _wired_ports()
    trace_id = "trace-phase-log"
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id=trace_id,
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    events = outcome.execution_context.phase_log_events
    phase_names = {event["phase_name"] for event in events}
    assert "request_received" in phase_names
    assert "config_resolved" in phase_names
    assert "response_built" in phase_names
    assert "matching_completed" in phase_names
    assert "ranking_completed" in phase_names
    assert "result_generated" in phase_names
    assert phase_names.isdisjoint(
        {
            "run_recorded",
            "pipeline_failed",
            "pipeline_control",
            "feature_matched",
            "ranked",
            "result_built",
            "snapshot_built",
        }
    )
    assert phase_names <= ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES

    config_events = [event for event in events if event["phase_name"] == "config_resolved"]
    assert any(event["phase_status"] == "started" for event in config_events)
    assert any(event["phase_status"] == "succeeded" for event in config_events)

    # §14 No.12 (001 / 028): Orchestrator 正常 Run で主要 phase が InMemory phase_log へ永続化
    records = in_memory_phase_log_records(helpers["phase_log_writer"])
    persisted_phase_names = {record.phase_name for record in records}
    assert "request_received" in persisted_phase_names
    assert "config_resolved" in persisted_phase_names
    assert "matching_completed" in persisted_phase_names
    assert "ranking_completed" in persisted_phase_names
    assert "result_generated" in persisted_phase_names
    assert persisted_phase_names <= ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES

    request_record = next(
        record for record in records if record.phase_name == "request_received"
    )
    assert request_record.phase_status == "started"
    assert request_record.trace_id == trace_id

    config_record = next(
        record for record in records if record.phase_name == "config_resolved"
    )
    assert config_record.phase_status == "succeeded"
    assert config_record.trace_id == trace_id


# §14 No.10 Metric 接続（integration: MOD-RECO-001→025 本実装 / 025 §14 No.10）
def test_success_run_records_tier_1_metrics_via_default_composition() -> None:
    from reco.application.metric_logger.constants import METRIC_SOURCE

    ports, helpers = _wired_ports()
    trace_id = "trace-metric-success"
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id=trace_id,
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    run_id = outcome.execution_context.run_id
    assert run_id is not None

    metric_logger = helpers["metric_logger"]
    assert len(metric_logger.recorded) == 1
    observation = metric_logger.recorded[0]
    assert observation["trace_id"] == trace_id
    assert observation["run_id"] == run_id
    assert observation["recommendation_run_id"] == run_id
    assert observation["final_result_count"] == 2
    assert observation["recommendation_empty"] is False
    assert observation["metric_source"] == METRIC_SOURCE
    for key in (
        "recommendation_latency_ms",
        "pre_filter_candidate_count",
        "retrieval_candidate_count",
        "post_filter_candidate_count",
        "reason_fallback_count",
        "recorded_at",
    ):
        assert key in observation

    persisted = in_memory_metric_log_records(metric_logger)
    assert len(persisted) == 1
    record = persisted[0]
    assert record.trace_id == trace_id
    assert record.recommendation_run_id == run_id
    assert record.final_result_count == 2
    assert record.recommendation_empty is False
    assert record.metric_source == METRIC_SOURCE


# §14 No.11 Metric 非記録（integration: 025 §14 No.11 — 失敗 Run で record_metrics 未呼び出し）
def test_failure_run_does_not_record_metrics() -> None:
    ports, helpers = build_default_stub_ports()
    ports = _ports_with(ports, config_resolver=StubConfigResolver(should_fail=True))
    trace_id = "trace-metric-failure"

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id=trace_id,
    )

    assert outcome.success is False
    metric_logger = helpers["metric_logger"]
    assert metric_logger.recorded == []
    assert in_memory_metric_log_records(metric_logger) == []


# §14 No.11 タイムアウト（integration: MOD-RECO-001 §14 No.11 — hard 8,000ms → GRS-REC-101）
def test_pipeline_hard_timeout_returns_grs_rec_101() -> None:
    ports, helpers = build_default_stub_ports()
    trace_id = "trace-pipeline-timeout"
    outcome = build_orchestrator_with_elapsed_ms(
        ports,
        elapsed_ms=PIPELINE_HARD_TIMEOUT_MS + 1,
    ).run(
        _sample_request(),
        trace_id=trace_id,
    )

    assert outcome.success is False
    assert outcome.reco_error is not None
    assert outcome.reco_error.error_code == "GRS-REC-101"
    assert outcome.reco_error.module_id == "MOD-RECO-001"
    assert outcome.execution_context is not None
    assert "MOD-RECO-004" not in outcome.execution_context.completed_modules
    assert outcome.execution_context.error_log_events

    metric_logger = helpers["metric_logger"]
    assert metric_logger.recorded == []
    assert in_memory_metric_log_records(metric_logger) == []

    records = in_memory_error_log_records(helpers["error_handler"])
    assert len(records) == 1
    assert records[0].trace_id == trace_id
    assert records[0].error_code == "GRS-REC-101"
    assert records[0].error_detail_json["source_module_id"] == "MOD-RECO-001"


def test_pipeline_hard_timeout_boundary_does_not_trigger_at_limit() -> None:
    ports, _ = build_default_stub_ports()
    ports = ports_with_user_meaning_stubs(ports)
    ports = ports_with_retrieval_stubs(ports)
    ports = ports_with_matching_stubs(ports)
    ports = ports_with_ranking_stubs(ports)
    ports = ports_with_output_stubs(ports)
    outcome = build_orchestrator_with_elapsed_ms(
        ports,
        elapsed_ms=PIPELINE_HARD_TIMEOUT_MS,
    ).run(
        _sample_request(),
        trace_id="trace-timeout-boundary",
    )

    assert outcome.success is True
    assert outcome.recommendation_result is not None


# §14 No.10 DB / ログ（integration: Run / Phase / Metric が下位モジュール経由で永続化）
def test_section14_no10_success_run_delegates_observability_to_downstream_modules() -> None:
    ports, helpers = _wired_ports()
    request = _sample_request()
    trace_id = "trace-section14-no10-success"

    outcome = RecommendationOrchestrator(ports).run(request, trace_id=trace_id)

    assert outcome.success is True
    context = outcome.execution_context
    assert context is not None
    run_id = context.run_id
    assert run_id is not None

    run_records = in_memory_recommendation_run_records(ports.run_recorder)
    assert len(run_records) == 1
    run_record = run_records[0]
    assert run_record.run_id == run_id
    assert run_record.request_id == request.request_id
    assert run_record.run_status is RunStatus.RUNNING

    phase_records = in_memory_phase_log_records(helpers["phase_log_writer"])
    assert phase_records
    assert all(record.trace_id == trace_id for record in phase_records)
    assert all(record.owner_id == run_id for record in phase_records)

    metric_records = in_memory_metric_log_records(helpers["metric_logger"])
    assert len(metric_records) == 1
    assert metric_records[0].recommendation_run_id == run_id
    assert metric_records[0].trace_id == trace_id

    assert in_memory_error_log_records(helpers["error_handler"]) == []


def test_section14_no10_failure_run_delegates_error_and_phase_to_downstream_modules() -> None:
    ports, helpers = _wired_ports()
    ports = _ports_with(
        ports,
        user_semantic_extractor=StubPipelineModule(
            module_id="MOD-RECO-004",
            phase_name="semantic_extracted",
            should_fail=True,
        ),
    )
    request = _sample_request()
    trace_id = "trace-section14-no10-failure"

    outcome = RecommendationOrchestrator(ports).run(request, trace_id=trace_id)

    assert outcome.success is False
    assert outcome.reco_error is not None
    assert outcome.reco_error.error_code == "GRS-REC-004"
    context = outcome.execution_context
    assert context is not None
    run_id = context.run_id
    assert run_id is not None
    assert "MOD-RECO-002" in context.completed_modules
    assert "MOD-RECO-004" not in context.completed_modules

    run_records = in_memory_recommendation_run_records(ports.run_recorder)
    assert len(run_records) == 1
    assert run_records[0].run_id == run_id

    error_records = in_memory_error_log_records(helpers["error_handler"])
    assert len(error_records) == 1
    assert error_records[0].trace_id == trace_id
    assert error_records[0].error_code == "GRS-REC-004"
    assert error_records[0].request_id == request.request_id

    phase_records = in_memory_phase_log_records(helpers["phase_log_writer"])
    assert phase_records
    assert any(record.phase_status == "failed" for record in phase_records)
    assert all(record.trace_id == trace_id for record in phase_records)

    assert in_memory_metric_log_records(helpers["metric_logger"]) == []


# §14 No.9 Error Log 接続（integration: MOD-RECO-024→029 本実装）
def test_error_handler_records_failure_for_error_log_delegation() -> None:
    ports, helpers = build_default_stub_ports()
    ports = _ports_with(ports, config_resolver=StubConfigResolver(should_fail=True))
    trace_id = "trace-error-log"

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id=trace_id,
    )

    assert outcome.success is False
    assert outcome.execution_context is not None
    error_events = outcome.execution_context.error_log_events
    assert len(error_events) == 1
    assert error_events[0]["module_id"] == "MOD-RECO-003"
    assert error_events[0]["error_code"] == "GRS-REC-003"
    assert error_events[0]["trace_id"] == trace_id

    # §14 No.10 (001 / 024 / 029): Orchestrator 失敗時に 029 InMemory error_log へ永続化
    records = in_memory_error_log_records(helpers["error_handler"])
    assert len(records) == 1
    record = records[0]
    assert record.trace_id == trace_id
    assert record.error_code == "GRS-REC-003"
    assert record.error_detail_json["source_module_id"] == "MOD-RECO-003"
    assert record.request_id == _sample_request().request_id


# §14 No.12 trace 伝播
def test_trace_id_propagates_to_phase_log_and_metrics() -> None:
    ports, helpers = _wired_ports()
    trace_id = "trace-propagation-xyz"

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id=trace_id,
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    assert outcome.execution_context.trace_id == trace_id
    phase_log_events = outcome.execution_context.phase_log_events
    assert all(event["trace_id"] == trace_id for event in phase_log_events)
    assert helpers["metric_logger"].recorded[-1]["trace_id"] == trace_id

    # §14 No.14 (001 / 028): trace_id が永続化 phase_log 行にも設定される
    records = in_memory_phase_log_records(helpers["phase_log_writer"])
    assert records
    assert all(record.trace_id == trace_id for record in records)


# §14 No.13 Reason fallback（全 Item 回復不能注入）
def test_reason_fallback_injects_generic_reason() -> None:
    ports, _ = _wired_ports()
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
    assert outcome.recommendation_result.result_status is not ResultStatus.PARTIAL
    assert all(item.is_fallback for item in outcome.recommendation_result.items)
    item = outcome.recommendation_result.items[0]
    assert item.reason_summary == GENERIC_REASON_SUMMARY
    assert item.is_fallback is True
    assert item.reason_status == ReasonStatus.COMPLETED


# §14 No.14 Reason 部分失敗（integration: 複数 Item で一部のみ fallback → partial）
def test_section14_no14_partial_reason_fallback_marks_result_status_partial() -> None:
    ports, _ = _wired_ports()
    ports = _ports_with(
        ports,
        reason_generator=StubPartialFallbackReasonGenerator(
            fallback_item_ids=frozenset({"item-002"}),
        ),
    )

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-section14-no14-partial",
    )

    assert outcome.success is True
    result = outcome.recommendation_result
    assert result is not None
    assert result.result_status == ResultStatus.PARTIAL
    assert len(result.items) >= 2

    fallback_items = [item for item in result.items if item.is_fallback]
    success_items = [item for item in result.items if not item.is_fallback]
    assert fallback_items
    assert success_items
    assert len(fallback_items) < len(result.items)
    assert fallback_items[0].reason_summary == GENERIC_REASON_SUMMARY
    assert success_items[0].reason_summary != GENERIC_REASON_SUMMARY

    context = outcome.execution_context
    assert context is not None
    assert context.reason_generator_fallback_count == len(fallback_items)
    assert context.reason_generator_success_count == len(success_items)


# Orchestrator 単体: User Meaning / Retrieval を Stub に戻して下流のみ検証する従来経路
def test_orchestrator_with_user_meaning_stubs_still_completes_pipeline() -> None:
    ports, _ = build_default_stub_ports()
    ports = ports_with_user_meaning_stubs(ports)
    ports = ports_with_retrieval_stubs(ports)
    ports = ports_with_matching_stubs(ports)
    ports = ports_with_ranking_stubs(ports)
    ports = ports_with_output_stubs(ports)
    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-stub-user-meaning",
    )

    assert outcome.success is True
    assert outcome.execution_context is not None
    assert outcome.execution_context.completed_modules == list(ORCHESTRATOR_MODULE_ORDER)
