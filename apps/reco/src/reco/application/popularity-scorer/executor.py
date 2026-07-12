"""MOD-RECO-017 Popularity Scorer implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, PHASE_NAME
from .errors import PopularityScorerError
from .models import PopularityScoreResult, PopularityScorerRunMetrics
from .ports import ItemReviewSummaryRepositoryPort
from .scoring_engine import run_popularity_scoring

if TYPE_CHECKING:
    from reco.application.context_scorer.models import ContextScoreResult
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class PopularityScorer:
    """PipelineModulePort implementation for Popularity Scorer."""

    review_summary_repository: ItemReviewSummaryRepositoryPort
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        result, metrics = self.score_popularity(context)
        _attach_outputs(context, result, metrics)
        context.completed_modules.append(self.module_id)
        return context

    def score_popularity(
        self,
        context: ExecutionContext,
    ) -> tuple[PopularityScoreResult, PopularityScorerRunMetrics]:
        started = perf_counter()
        context_score_result = self._validate_context(context)

        try:
            result, metrics = run_popularity_scoring(
                context_score_result=context_score_result,
                config_versions=context.config_versions,
                review_summary_repository=self.review_summary_repository,
            )
        except PopularityScorerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PopularityScorerError(
                f"popularity scoring failed for run: {context.run_id}",
            ) from exc

        latency_ms = int((perf_counter() - started) * 1_000)
        metrics = PopularityScorerRunMetrics(
            popularity_scorer_candidate_count=metrics.popularity_scorer_candidate_count,
            popularity_scorer_latency_ms=latency_ms,
            popularity_missing_signal_count=metrics.popularity_missing_signal_count,
            popularity_score_value_out_of_range_count=(
                metrics.popularity_score_value_out_of_range_count
            ),
        )
        self._log_scoring_completed(context, result, metrics)
        return result, metrics

    def _validate_context(self, context: ExecutionContext) -> ContextScoreResult:
        if context.run_id is None:
            raise PopularityScorerError("run_id is required on execution_context")

        context_score_result = context.context_score_result
        if context_score_result is None:
            raise PopularityScorerError(
                "context_score_result is required on execution_context",
            )

        return context_score_result

    def _log_scoring_completed(
        self,
        context: ExecutionContext,
        result: PopularityScoreResult,
        metrics: PopularityScorerRunMetrics,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            popularity_scorer_candidate_count=metrics.popularity_scorer_candidate_count,
            popularity_scorer_latency_ms=metrics.popularity_scorer_latency_ms,
            popularity_missing_signal_count=metrics.popularity_missing_signal_count,
            popularity_score_value_out_of_range_count=(
                metrics.popularity_score_value_out_of_range_count
            ),
            total_scored=result.total_scored,
            max_review_count_in_candidates=result.max_review_count_in_candidates,
            module_id=self.module_id,
        )


def _attach_outputs(
    context: ExecutionContext,
    result: PopularityScoreResult,
    metrics: PopularityScorerRunMetrics,
) -> None:
    context.popularity_score_result = result
    context.popularity_scorer_candidate_count = (
        metrics.popularity_scorer_candidate_count
    )
    context.popularity_scorer_latency_ms = metrics.popularity_scorer_latency_ms
    context.popularity_missing_signal_count = metrics.popularity_missing_signal_count
    context.popularity_score_value_out_of_range_count = (
        metrics.popularity_score_value_out_of_range_count
    )


def build_default_popularity_scorer(
    review_summary_repository: ItemReviewSummaryRepositoryPort,
) -> PopularityScorer:
    return PopularityScorer(review_summary_repository=review_summary_repository)
