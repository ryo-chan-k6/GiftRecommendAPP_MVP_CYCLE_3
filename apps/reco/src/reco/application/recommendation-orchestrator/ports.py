"""Downstream module ports for MOD-RECO-001."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .errors import RecoError
from .execution_context import ExecutionContext


class PhaseStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ReasonGenerationOutcome(StrEnum):
    SUCCESS = "success"
    INTERNAL_FALLBACK = "internal_fallback"
    UNRECOVERABLE = "unrecoverable"


@dataclass(frozen=True)
class ReasonGenerationResult:
    outcome: ReasonGenerationOutcome
    reason_summary: str | None = None
    is_fallback: bool = False


class RunRecorderPort(Protocol):
    module_id: str

    def record_run(self, context: ExecutionContext) -> ExecutionContext: ...


class ConfigResolverPort(Protocol):
    module_id: str

    def resolve(self, context: ExecutionContext) -> ExecutionContext: ...


class PipelineModulePort(Protocol):
    """Generic synchronous module invoked in pipeline order."""

    module_id: str
    phase_name: str

    def execute(self, context: ExecutionContext) -> ExecutionContext: ...


class ReasonGeneratorPort(Protocol):
    module_id: str
    phase_name: str

    def generate(self, context: ExecutionContext) -> ReasonGenerationResult: ...


class ErrorHandlerPort(Protocol):
    module_id: str

    def handle(
        self,
        context: ExecutionContext,
        *,
        module_id: str,
        error_code: str,
        message: str,
        phase_name: str | None = None,
    ) -> RecoError: ...


class PhaseLogWriterPort(Protocol):
    module_id: str

    def record_phase(
        self,
        context: ExecutionContext,
        *,
        phase_name: str,
        phase_status: PhaseStatus,
        module_id: str | None = None,
        error_code: str | None = None,
        duration_ms: int | None = None,
    ) -> None: ...


class MetricLoggerPort(Protocol):
    module_id: str

    def record_metrics(self, context: ExecutionContext) -> None: ...


@dataclass
class OrchestratorPorts:
    """Container for all downstream module ports."""

    run_recorder: RunRecorderPort
    config_resolver: ConfigResolverPort
    user_semantic_extractor: PipelineModulePort
    external_feature_estimator: PipelineModulePort
    internal_feature_estimator: PipelineModulePort
    user_feature_generator: PipelineModulePort
    user_meaning_projector: PipelineModulePort
    user_context_builder: PipelineModulePort
    query_embedding_generator: PipelineModulePort
    pre_hard_filter: PipelineModulePort
    candidate_retriever: PipelineModulePort
    post_hard_filter: PipelineModulePort
    feature_matcher: PipelineModulePort
    meaning_match_aggregator: PipelineModulePort
    context_scorer: PipelineModulePort
    popularity_scorer: PipelineModulePort
    risk_scorer: PipelineModulePort
    final_score_calculator: PipelineModulePort
    final_ranker: PipelineModulePort
    result_builder: PipelineModulePort
    snapshot_builder: PipelineModulePort
    reason_generator: ReasonGeneratorPort
    error_handler: ErrorHandlerPort
    phase_log_writer: PhaseLogWriterPort
    metric_logger: MetricLoggerPort | None = None

    def ordered_pipeline_modules(self) -> tuple[PipelineModulePort, ...]:
        return (
            self.user_semantic_extractor,
            self.external_feature_estimator,
            self.internal_feature_estimator,
            self.user_feature_generator,
            self.user_meaning_projector,
            self.user_context_builder,
            self.query_embedding_generator,
            self.pre_hard_filter,
            self.candidate_retriever,
            self.post_hard_filter,
            self.feature_matcher,
            self.meaning_match_aggregator,
            self.context_scorer,
            self.popularity_scorer,
            self.risk_scorer,
            self.final_score_calculator,
            self.final_ranker,
            self.result_builder,
            self.snapshot_builder,
        )
