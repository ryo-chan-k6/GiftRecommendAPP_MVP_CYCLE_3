"""MOD-RECO-021 Recommendation Result Builder implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .build_engine import build_recommendation_result, to_domain_recommendation_result
from .constants import MODULE_ID, PHASE_NAME
from .errors import RecommendationResultBuilderError
from .in_memory_repository import InMemoryRecommendationResultRepository
from .models import (
    BuiltRecommendationResult,
    RecommendationResultBuilderRunMetrics,
)
from .ports import RecommendationResultRepositoryPort

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class RecommendationResultBuilder:
    """PipelineModulePort implementation for Recommendation Result Builder."""

    result_repository: RecommendationResultRepositoryPort = field(
        default_factory=InMemoryRecommendationResultRepository,
    )
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        built, _metrics = self.build_result(context)
        _attach_outputs(context, built)
        context.completed_modules.append(self.module_id)
        return context

    def build_result(
        self,
        context: ExecutionContext,
    ) -> tuple[BuiltRecommendationResult, RecommendationResultBuilderRunMetrics]:
        started = perf_counter()

        try:
            built, metrics = build_recommendation_result(context)
            persisted_header = self.result_repository.insert_header(built.header)
        except RecommendationResultBuilderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RecommendationResultBuilderError(
                f"recommendation result build failed for run: {context.run_id}",
            ) from exc

        latency_ms = int((perf_counter() - started) * 1_000)
        metrics = RecommendationResultBuilderRunMetrics(
            result_builder_item_count=metrics.result_builder_item_count,
            result_builder_latency_ms=latency_ms,
            result_builder_header_persisted=True,
            zero_result_header_count=metrics.zero_result_header_count,
            score_breakdown_partial_count=metrics.score_breakdown_partial_count,
        )

        built = BuiltRecommendationResult(
            header=persisted_header,
            items=built.items,
        )
        self._log_build_completed(context, built, metrics)
        return built, metrics

    def _log_build_completed(
        self,
        context: ExecutionContext,
        built: BuiltRecommendationResult,
        metrics: RecommendationResultBuilderRunMetrics,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            result_status=built.header.result_status.value,
            result_builder_item_count=metrics.result_builder_item_count,
            result_builder_latency_ms=metrics.result_builder_latency_ms,
            result_builder_header_persisted=metrics.result_builder_header_persisted,
            zero_result_header_count=metrics.zero_result_header_count,
            score_breakdown_partial_count=metrics.score_breakdown_partial_count,
            module_id=self.module_id,
        )


def _attach_outputs(
    context: ExecutionContext,
    built: BuiltRecommendationResult,
) -> None:
    context.recommendation_result = to_domain_recommendation_result(built)


def build_default_recommendation_result_builder() -> RecommendationResultBuilder:
    return RecommendationResultBuilder()

