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
    StubRunRecorder,
)
from reco.domain import (
    ExecutionCondition,
    ExecutionMode,
    ReasonStatus,
    RecommendationRequest,
    RelationshipCondition,
)


def _sample_request(*, mode: ExecutionMode = ExecutionMode.UI) -> RecommendationRequest:
    return RecommendationRequest(
        request_id="req-orchestrator-1",
        relationship=RelationshipCondition(relationship_code="friend"),
        execution=ExecutionCondition(mode=mode, top_k=5),
    )


def test_orchestrator_runs_all_modules_in_order() -> None:
    orchestrator = RecommendationOrchestrator()
    outcome = orchestrator.run(
        _sample_request(),
        trace_id="trace-1",
    )

    assert outcome.success is True
    assert outcome.recommendation_result is not None
    assert outcome.execution_context is not None
    assert outcome.execution_context.completed_modules == list(ORCHESTRATOR_MODULE_ORDER)


def test_final_score_calculator_runs_before_final_ranker() -> None:
    ports, _ = build_default_stub_ports()
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


def test_reason_fallback_injects_generic_reason() -> None:
    ports, _ = build_default_stub_ports()
    ports = OrchestratorPorts(
        run_recorder=ports.run_recorder,
        config_resolver=ports.config_resolver,
        user_semantic_extractor=ports.user_semantic_extractor,
        external_feature_estimator=ports.external_feature_estimator,
        internal_feature_estimator=ports.internal_feature_estimator,
        user_feature_generator=ports.user_feature_generator,
        user_meaning_projector=ports.user_meaning_projector,
        user_context_builder=ports.user_context_builder,
        query_embedding_generator=ports.query_embedding_generator,
        pre_hard_filter=ports.pre_hard_filter,
        candidate_retriever=ports.candidate_retriever,
        post_hard_filter=ports.post_hard_filter,
        feature_matcher=ports.feature_matcher,
        meaning_match_aggregator=ports.meaning_match_aggregator,
        context_scorer=ports.context_scorer,
        popularity_scorer=ports.popularity_scorer,
        risk_scorer=ports.risk_scorer,
        final_score_calculator=ports.final_score_calculator,
        final_ranker=ports.final_ranker,
        result_builder=ports.result_builder,
        snapshot_builder=ports.snapshot_builder,
        reason_generator=StubReasonGenerator(
            outcome=ReasonGenerationOutcome.UNRECOVERABLE
        ),
        error_handler=ports.error_handler,
        phase_log_writer=ports.phase_log_writer,
        metric_logger=ports.metric_logger,
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


def test_downstream_failure_stops_pipeline_and_returns_error() -> None:
    ports, helpers = build_default_stub_ports()
    ports = OrchestratorPorts(
        run_recorder=StubRunRecorder(),
        config_resolver=StubConfigResolver(should_fail=True),
        user_semantic_extractor=ports.user_semantic_extractor,
        external_feature_estimator=ports.external_feature_estimator,
        internal_feature_estimator=ports.internal_feature_estimator,
        user_feature_generator=ports.user_feature_generator,
        user_meaning_projector=ports.user_meaning_projector,
        user_context_builder=ports.user_context_builder,
        query_embedding_generator=ports.query_embedding_generator,
        pre_hard_filter=ports.pre_hard_filter,
        candidate_retriever=ports.candidate_retriever,
        post_hard_filter=ports.post_hard_filter,
        feature_matcher=ports.feature_matcher,
        meaning_match_aggregator=ports.meaning_match_aggregator,
        context_scorer=ports.context_scorer,
        popularity_scorer=ports.popularity_scorer,
        risk_scorer=ports.risk_scorer,
        final_score_calculator=ports.final_score_calculator,
        final_ranker=ports.final_ranker,
        result_builder=ports.result_builder,
        snapshot_builder=ports.snapshot_builder,
        reason_generator=ports.reason_generator,
        error_handler=ports.error_handler,
        phase_log_writer=ports.phase_log_writer,
        metric_logger=ports.metric_logger,
    )

    outcome = RecommendationOrchestrator(ports).run(
        _sample_request(),
        trace_id="trace-failure",
    )

    assert outcome.success is False
    assert outcome.reco_error is not None
    assert outcome.reco_error.error_code == "GRS-REC-003"
    assert outcome.execution_context is not None
    assert "MOD-RECO-004" not in outcome.execution_context.completed_modules
    assert helpers["error_handler"].error_log_events
