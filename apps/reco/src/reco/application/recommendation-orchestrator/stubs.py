"""MVP stub implementations for downstream MOD-RECO-* ports."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from reco.domain.recommendation.inputs import ExecutionMode
from reco.domain.recommendation.result import (
    ReasonStatus,
    RecommendationResult,
    RecommendationResultItem,
    ResultStatus,
)


def _ensure_run_recorder_package() -> None:
    import_root = "reco.application.recommendation_run_recorder"
    if import_root in sys.modules:
        return

    init_path = (
        Path(__file__).resolve().parent.parent
        / "recommendation-run-recorder/__init__.py"
    )
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load recommendation run recorder package")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_ensure_run_recorder_package()

from reco.application.recommendation_run_recorder import build_scaffold_run_recorder  # noqa: E402

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
    artifact_key: str | None = None

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        if self.should_fail:
            raise RuntimeError(f"{self.module_id} failed")

        if self.artifact_key is not None:
            context.ranked_items.append(
                {
                    "module_id": self.module_id,
                    "artifact": self.artifact_key,
                }
            )

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

    result_builder = StubPipelineModule(
        module_id="MOD-RECO-021",
        phase_name="response_built",
        artifact_key="recommendation_result",
    )
    snapshot_builder = StubPipelineModule(
        module_id="MOD-RECO-022",
        phase_name="snapshot_built",
        artifact_key="result_snapshot",
    )
    final_score_calculator = StubPipelineModule(
        module_id="MOD-RECO-019",
        phase_name="final_score_calculated",
        artifact_key="final_score",
    )
    final_ranker = StubPipelineModule(
        module_id="MOD-RECO-020",
        phase_name="ranked",
        artifact_key="ranked_items",
    )

    phase_log_writer = StubPhaseLogWriter()
    error_handler = StubErrorHandler()
    metric_logger = StubMetricLogger()

    ports = OrchestratorPorts(
        run_recorder=build_scaffold_run_recorder(),
        config_resolver=StubConfigResolver(),
        user_semantic_extractor=StubPipelineModule(
            "MOD-RECO-004", "semantic_extracted"
        ),
        external_feature_estimator=StubPipelineModule(
            "MOD-RECO-005", "external_feature_estimated"
        ),
        internal_feature_estimator=StubPipelineModule(
            "MOD-RECO-006", "internal_feature_estimated"
        ),
        user_feature_generator=StubPipelineModule(
            "MOD-RECO-007", "user_feature_generated"
        ),
        user_meaning_projector=StubPipelineModule(
            "MOD-RECO-008", "user_meaning_projected"
        ),
        user_context_builder=StubPipelineModule(
            "MOD-RECO-009", "user_context_built"
        ),
        query_embedding_generator=StubPipelineModule(
            "MOD-RECO-010", "query_embedding_generated"
        ),
        pre_hard_filter=StubPipelineModule("MOD-RECO-011", "pre_hard_filtered"),
        candidate_retriever=StubPipelineModule("MOD-RECO-012", "retrieval_completed"),
        post_hard_filter=StubPipelineModule("MOD-RECO-013", "post_hard_filtered"),
        feature_matcher=StubPipelineModule("MOD-RECO-014", "feature_matched"),
        meaning_match_aggregator=StubPipelineModule(
            "MOD-RECO-015", "meaning_match_aggregated"
        ),
        context_scorer=StubPipelineModule("MOD-RECO-016", "context_scored"),
        popularity_scorer=StubPipelineModule("MOD-RECO-017", "popularity_scored"),
        risk_scorer=StubPipelineModule("MOD-RECO-018", "risk_scored"),
        final_score_calculator=final_score_calculator,
        final_ranker=final_ranker,
        result_builder=result_builder,
        snapshot_builder=snapshot_builder,
        reason_generator=StubReasonGenerator(),
        error_handler=error_handler,
        phase_log_writer=phase_log_writer,
        metric_logger=metric_logger,
    )

    # Post-process hooks wired into result_builder via monkey-patch style closure
    _attach_result_builder_hook(result_builder, ports)

    helpers = {
        "phase_log_writer": phase_log_writer,
        "error_handler": error_handler,
        "metric_logger": metric_logger,
    }
    return ports, helpers


def _attach_result_builder_hook(
    result_builder: StubPipelineModule,
    ports: OrchestratorPorts,
) -> None:
    original_execute = result_builder.execute

    def execute(context: ExecutionContext) -> ExecutionContext:
        updated = original_execute(context)
        if updated.recommendation_result is not None:
            return updated

        run_id = updated.run_id or "run-scaffold"
        updated.recommendation_result = RecommendationResult(
            run_id=run_id,
            request_id=updated.recommendation_request.request_id,
            items=(
                RecommendationResultItem(
                    item_id="item-scaffold-1",
                    rank=1,
                    final_score=0.75,
                    reason_summary=None,
                    reason_status=None,
                    is_fallback=False,
                ),
            ),
            result_status=ResultStatus.COMPLETED,
            version_info=dict(updated.config_versions),
        )
        return updated

    result_builder.execute = execute  # type: ignore[method-assign]


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
