"""MVP stub implementations for downstream MOD-RECO-* ports."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from reco.domain.recommendation.inputs import ExecutionMode


def _ensure_application_package(import_root: str, package_dir: str) -> None:
    if import_root in sys.modules:
        return

    init_path = (
        Path(__file__).resolve().parent.parent / package_dir / "__init__.py"
    )
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load application package: {import_root}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def _ensure_run_recorder_package() -> None:
    _ensure_application_package(
        "reco.application.recommendation_run_recorder",
        "recommendation-run-recorder",
    )


def _ensure_config_version_resolver_package() -> None:
    _ensure_application_package(
        "reco.application.config_version_resolver",
        "config-version-resolver",
    )


def _ensure_user_semantic_extractor_package() -> None:
    _ensure_application_package(
        "reco.application.user_semantic_extractor",
        "user-semantic-extractor",
    )


def _ensure_external_condition_feature_estimator_package() -> None:
    _ensure_application_package(
        "reco.application.external_condition_feature_estimator",
        "external-condition-feature-estimator",
    )


def _ensure_internal_condition_feature_estimator_package() -> None:
    _ensure_application_package(
        "reco.application.internal_condition_feature_estimator",
        "internal-condition-feature-estimator",
    )


def _ensure_user_feature_generator_package() -> None:
    _ensure_application_package(
        "reco.application.user_feature_generator",
        "user-feature-generator",
    )


def _ensure_user_meaning_projector_package() -> None:
    _ensure_application_package(
        "reco.application.user_meaning_projector",
        "user-meaning-projector",
    )


def _ensure_user_context_builder_package() -> None:
    _ensure_application_package(
        "reco.application.user_context_builder",
        "user-context-builder",
    )


def _ensure_query_embedding_generator_package() -> None:
    _ensure_application_package(
        "reco.application.query_embedding_generator",
        "query-embedding-generator",
    )


def _ensure_candidate_retriever_package() -> None:
    _ensure_application_package(
        "reco.application.candidate_retriever",
        "candidate-retriever",
    )


def _ensure_post_hard_filter_executor_package() -> None:
    _ensure_application_package(
        "reco.application.post_hard_filter_executor",
        "post-hard-filter-executor",
    )


def _ensure_feature_matcher_package() -> None:
    _ensure_application_package(
        "reco.application.feature_matcher",
        "feature-matcher",
    )


def _ensure_meaning_match_aggregator_package() -> None:
    _ensure_application_package(
        "reco.application.meaning_match_aggregator",
        "meaning-match-aggregator",
    )


def _ensure_context_scorer_package() -> None:
    _ensure_application_package(
        "reco.application.context_scorer",
        "context-scorer",
    )


def _ensure_popularity_scorer_package() -> None:
    _ensure_application_package(
        "reco.application.popularity_scorer",
        "popularity-scorer",
    )


def _ensure_risk_scorer_package() -> None:
    _ensure_application_package(
        "reco.application.risk_scorer",
        "risk-scorer",
    )


def _ensure_final_score_calculator_package() -> None:
    _ensure_application_package(
        "reco.application.final_score_calculator",
        "final-score-calculator",
    )


def _ensure_final_ranker_package() -> None:
    _ensure_application_package(
        "reco.application.final_ranker",
        "final-ranker",
    )


def _ensure_recommendation_result_builder_package() -> None:
    _ensure_application_package(
        "reco.application.recommendation_result_builder",
        "recommendation-result-builder",
    )


def _ensure_result_snapshot_builder_package() -> None:
    _ensure_application_package(
        "reco.application.result_snapshot_builder",
        "result-snapshot-builder",
    )


def _ensure_reason_generator_package() -> None:
    _ensure_application_package(
        "reco.application.reason_generator",
        "reason-generator",
    )


def _ensure_error_log_writer_package() -> None:
    _ensure_application_package(
        "reco.application.error_log_writer",
        "error-log-writer",
    )


def _ensure_phase_log_writer_package() -> None:
    _ensure_application_package(
        "reco.application.phase_log_writer",
        "phase-log-writer",
    )


def _ensure_metric_logger_package() -> None:
    _ensure_application_package(
        "reco.application.metric_logger",
        "metric-logger",
    )


def _build_default_orchestrator_error_handler():
    """Wire MOD-RECO-024 with MOD-RECO-029 InMemory writer for MVP composition."""
    _ensure_error_log_writer_package()
    from reco.application.error_log_writer import build_default_error_log_writer
    from reco.application.reco_error_handler import RecoErrorHandler

    return RecoErrorHandler(
        error_log_writer=build_default_error_log_writer(),
        append_test_seam_events=True,
    )


@dataclass
class _OrchestratorPhaseLogWriterAdapter:
    """Wrap PhaseLogWriter and preserve Stub-compatible `.events` for composition tests."""

    writer: object
    module_id: str = "MOD-RECO-028"
    events: list[dict[str, object]] = field(default_factory=list)

    def record_phase(
        self,
        context: ExecutionContext,
        *,
        phase_name: str,
        phase_status: PhaseStatus,
        module_id: str | None = None,
        error_code: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        before = len(context.phase_log_events)
        self.writer.record_phase(
            context,
            phase_name=phase_name,
            phase_status=phase_status,
            module_id=module_id,
            error_code=error_code,
            duration_ms=duration_ms,
        )
        if len(context.phase_log_events) > before:
            self.events.append(context.phase_log_events[-1])


def _build_default_orchestrator_phase_log_writer() -> _OrchestratorPhaseLogWriterAdapter:
    """Wire MOD-RECO-028 with InMemory repository for MVP composition."""
    _ensure_phase_log_writer_package()
    from reco.application.phase_log_writer import build_default_phase_log_writer

    return _OrchestratorPhaseLogWriterAdapter(writer=build_default_phase_log_writer())


def _build_default_orchestrator_metric_logger():
    """Wire MOD-RECO-025 with InMemory repository for MVP composition."""
    _ensure_metric_logger_package()
    from reco.application.metric_logger import build_default_metric_logger

    return build_default_metric_logger()


_ensure_run_recorder_package()
_ensure_config_version_resolver_package()
_ensure_user_semantic_extractor_package()
_ensure_external_condition_feature_estimator_package()
_ensure_internal_condition_feature_estimator_package()
_ensure_user_feature_generator_package()
_ensure_user_meaning_projector_package()
_ensure_user_context_builder_package()
_ensure_query_embedding_generator_package()
_ensure_candidate_retriever_package()
_ensure_post_hard_filter_executor_package()
_ensure_feature_matcher_package()
_ensure_meaning_match_aggregator_package()
_ensure_context_scorer_package()
_ensure_popularity_scorer_package()
_ensure_risk_scorer_package()
_ensure_final_score_calculator_package()
_ensure_final_ranker_package()
_ensure_recommendation_result_builder_package()
_ensure_result_snapshot_builder_package()
_ensure_reason_generator_package()

from reco.application.candidate_retriever import build_default_candidate_retriever  # noqa: E402
from reco.application.config_version_resolver import build_default_config_resolver  # noqa: E402
from reco.application.external_condition_feature_estimator import (  # noqa: E402
    build_default_external_condition_feature_estimator,
)
from reco.application.context_scorer import build_default_context_scorer  # noqa: E402
from reco.application.final_ranker import build_default_final_ranker  # noqa: E402
from reco.application.final_score_calculator import (  # noqa: E402
    build_default_final_score_calculator,
)
from reco.application.feature_matcher import build_default_feature_matcher  # noqa: E402
from reco.application.meaning_match_aggregator import (  # noqa: E402
    build_default_meaning_match_aggregator,
)
from reco.application.popularity_scorer import (  # noqa: E402
    build_default_in_memory_item_review_summary_repository,
    build_default_popularity_scorer,
)
from reco.application.post_hard_filter_executor import (  # noqa: E402
    build_default_post_hard_filter_executor,
)
from reco.application.risk_scorer import build_default_risk_scorer  # noqa: E402
from reco.application.internal_condition_feature_estimator import (  # noqa: E402
    build_default_internal_condition_feature_estimator,
)
from reco.application.query_embedding_generator import (  # noqa: E402
    build_default_query_embedding_generator,
)
from reco.application.reason_generator import build_default_reason_generator  # noqa: E402
from reco.application.recommendation_result_builder import (  # noqa: E402
    build_default_recommendation_result_builder,
)
from reco.application.recommendation_run_recorder import build_scaffold_run_recorder  # noqa: E402
from reco.application.result_snapshot_builder import (  # noqa: E402
    build_default_result_snapshot_builder,
)
from reco.application.user_context_builder import build_default_user_context_builder  # noqa: E402
from reco.application.user_feature_generator import (  # noqa: E402
    build_default_user_feature_generator,
)
from reco.application.user_meaning_projector import (  # noqa: E402
    build_default_user_meaning_projector,
)
from reco.application.user_semantic_extractor import (  # noqa: E402
    build_default_user_semantic_extractor,
)

from .errors import RecoError
from .execution_context import ExecutionContext
from .ports import (
    ConfigResolverPort,
    ErrorHandlerPort,
    MetricLoggerPort,
    OrchestratorPorts,
    PhaseLogWriterPort,
    PhaseStatus,
    PipelineModulePort,
    ReasonGenerationOutcome,
    ReasonGenerationResult,
    ReasonGeneratorPort,
)


@dataclass
class StubConfigResolver:
    module_id: str = "MOD-RECO-003"
    should_fail: bool = False

    def resolve(self, context: ExecutionContext) -> ExecutionContext:
        if self.should_fail:
            raise RuntimeError("config resolver failed")

        context.config_versions = {
            "semantic_config_version_id": "scaffold-semantic-v1",
            "model_version_id": "scaffold-model-v1",
            "matching_config_id": "scaffold-matching-v1",
            "ranking_config_id": "scaffold-ranking-v1",
            "execution_mode": context.execution_mode.value,
        }
        context.completed_modules.append(self.module_id)
        return context


@dataclass
class StubPipelineModule:
    module_id: str
    phase_name: str
    should_fail: bool = False

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        if self.should_fail:
            raise RuntimeError(f"{self.module_id} failed")

        context.completed_modules.append(self.module_id)
        return context


@dataclass
class StubReasonGenerator:
    module_id: str = "MOD-RECO-023"
    phase_name: str = "reason_generated"
    outcome: ReasonGenerationOutcome = ReasonGenerationOutcome.SUCCESS
    reason_summary: str = "scaffold reason"

    def generate(self, context: ExecutionContext) -> ReasonGenerationResult:
        context.completed_modules.append(self.module_id)
        return ReasonGenerationResult(
            outcome=self.outcome,
            reason_summary=self.reason_summary,
            is_fallback=self.outcome == ReasonGenerationOutcome.INTERNAL_FALLBACK,
        )


@dataclass
class StubPartialFallbackReasonGenerator:
    """Simulate MOD-RECO-023 per-Item success/fallback for Orchestrator integration tests."""

    module_id: str = "MOD-RECO-023"
    phase_name: str = "reason_generated"
    fallback_item_ids: frozenset[str] = frozenset()
    success_reason_summary: str = "scaffold reason"

    def generate(self, context: ExecutionContext) -> ReasonGenerationResult:
        from reco.domain.recommendation.result import (
            ReasonStatus,
            RecommendationResult,
            RecommendationResultItem,
        )

        from .constants import GENERIC_REASON_SUMMARY

        result = context.recommendation_result
        if result is None:
            context.completed_modules.append(self.module_id)
            return ReasonGenerationResult(outcome=ReasonGenerationOutcome.UNRECOVERABLE)

        updated_items: list[RecommendationResultItem] = []
        fallback_count = 0
        success_count = 0

        for item in result.items:
            if item.item_id in self.fallback_item_ids:
                updated_items.append(
                    RecommendationResultItem(
                        item_id=item.item_id,
                        rank=item.rank,
                        final_score=item.final_score,
                        reason_summary=GENERIC_REASON_SUMMARY,
                        reason_status=ReasonStatus.COMPLETED,
                        is_fallback=True,
                    )
                )
                fallback_count += 1
                continue

            updated_items.append(
                RecommendationResultItem(
                    item_id=item.item_id,
                    rank=item.rank,
                    final_score=item.final_score,
                    reason_summary=self.success_reason_summary,
                    reason_status=ReasonStatus.COMPLETED,
                    is_fallback=False,
                )
            )
            success_count += 1

        version_info = dict(result.version_info or {})
        version_info.update(
            {
                "reason_generator_item_count": str(len(updated_items)),
                "reason_generator_success_count": str(success_count),
                "reason_generator_fallback_count": str(fallback_count),
                "reason_generator_persisted": "true",
                "reason_generation_latency_ms": "0",
            },
        )
        context.recommendation_result = RecommendationResult(
            run_id=result.run_id,
            request_id=result.request_id,
            items=tuple(updated_items),
            result_status=result.result_status,
            version_info=version_info,
        )
        context.reason_generator_item_count = len(updated_items)
        context.reason_generator_success_count = success_count
        context.reason_generator_fallback_count = fallback_count
        context.reason_generator_persisted = True
        context.reason_generation_latency_ms = 0
        context.completed_modules.append(self.module_id)

        if fallback_count == 0:
            outcome = ReasonGenerationOutcome.SUCCESS
        else:
            outcome = ReasonGenerationOutcome.INTERNAL_FALLBACK

        return ReasonGenerationResult(
            outcome=outcome,
            reason_summary=self.success_reason_summary,
            is_fallback=fallback_count > 0,
        )


@dataclass
class StubErrorHandler:
    module_id: str = "MOD-RECO-024"
    error_log_events: list[dict[str, object]] = field(default_factory=list)

    def handle(
        self,
        context: ExecutionContext,
        *,
        module_id: str,
        error_code: str,
        message: str,
        phase_name: str | None = None,
        cause: BaseException | None = None,
    ) -> RecoError:
        event = {
            "module_id": module_id,
            "error_code": error_code,
            "message": message,
            "phase_name": phase_name,
            "trace_id": context.trace_id,
        }
        self.error_log_events.append(event)
        context.error_log_events.append(event)
        return RecoError(
            error_code=error_code,
            message=message,
            module_id=module_id,
            phase_name=phase_name,
        )


@dataclass
class StubPhaseLogWriter:
    module_id: str = "MOD-RECO-028"
    events: list[dict[str, object]] = field(default_factory=list)

    def record_phase(
        self,
        context: ExecutionContext,
        *,
        phase_name: str,
        phase_status: PhaseStatus,
        module_id: str | None = None,
        error_code: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        event = {
            "phase_name": phase_name,
            "phase_status": phase_status.value,
            "module_id": module_id,
            "error_code": error_code,
            "duration_ms": duration_ms,
            "trace_id": context.trace_id,
            "run_id": context.run_id,
        }
        self.events.append(event)
        context.phase_log_events.append(event)


@dataclass
class StubMetricLogger:
    module_id: str = "MOD-RECO-025"
    recorded: list[dict[str, object]] = field(default_factory=list)

    def record_metrics(self, context: ExecutionContext) -> None:
        metrics = {
            "recommendation_latency_ms": context.recommendation_latency_ms,
            "reason_fallback_count": context.reason_fallback_count,
            "final_result_count": (
                context.recommendation_result.item_count
                if context.recommendation_result
                else 0
            ),
            "trace_id": context.trace_id,
            "run_id": context.run_id,
        }
        self.recorded.append(metrics)


def build_default_stub_ports() -> tuple[OrchestratorPorts, dict[str, object]]:
    """Create MVP stub ports with deterministic scaffold behavior."""

    phase_log_writer = _build_default_orchestrator_phase_log_writer()
    error_handler = _build_default_orchestrator_error_handler()
    metric_logger = _build_default_orchestrator_metric_logger()

    ports = OrchestratorPorts(
        run_recorder=build_scaffold_run_recorder(),
        config_resolver=build_default_config_resolver(),
        user_semantic_extractor=build_default_user_semantic_extractor(),
        external_feature_estimator=build_default_external_condition_feature_estimator(),
        internal_feature_estimator=build_default_internal_condition_feature_estimator(),
        user_feature_generator=build_default_user_feature_generator(),
        user_meaning_projector=build_default_user_meaning_projector(),
        user_context_builder=build_default_user_context_builder(),
        query_embedding_generator=build_default_query_embedding_generator(),
        candidate_retriever=build_default_candidate_retriever(),
        post_hard_filter=build_default_post_hard_filter_executor(),
        feature_matcher=build_default_feature_matcher(),
        meaning_match_aggregator=build_default_meaning_match_aggregator(),
        context_scorer=build_default_context_scorer(),
        popularity_scorer=build_default_popularity_scorer(
            build_default_in_memory_item_review_summary_repository(),
        ),
        risk_scorer=build_default_risk_scorer(),
        final_score_calculator=build_default_final_score_calculator(),
        final_ranker=build_default_final_ranker(),
        result_builder=build_default_recommendation_result_builder(),
        snapshot_builder=build_default_result_snapshot_builder(),
        reason_generator=build_default_reason_generator(),
        error_handler=error_handler,
        phase_log_writer=phase_log_writer,
        metric_logger=metric_logger,
    )

    helpers = {
        "phase_log_writer": phase_log_writer,
        "error_handler": error_handler,
        "metric_logger": metric_logger,
    }
    return ports, helpers


def resolve_execution_mode(
    recommendation_request,
    explicit_mode: ExecutionMode | None,
) -> ExecutionMode:
    if explicit_mode is not None:
        return explicit_mode
    execution = recommendation_request.execution
    if execution is not None:
        return execution.mode
    return ExecutionMode.UI
