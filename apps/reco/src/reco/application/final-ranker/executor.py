"""MOD-RECO-020 Final Ranker implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, PHASE_NAME
from .errors import FinalRankerError
from .models import FinalRankerRunMetrics, RankedItems
from .ranking_engine import run_final_ranking

if TYPE_CHECKING:
    from reco.application.feature_matcher.models import FeatureMatchResult
    from reco.application.final_score_calculator.models import FinalScoreResult
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class FinalRanker:
    """PipelineModulePort implementation for Final Ranker."""

    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        result, metrics = self.rank_candidates(context)
        _attach_outputs(context, result, metrics)
        context.completed_modules.append(self.module_id)
        return context

    def rank_candidates(
        self,
        context: ExecutionContext,
    ) -> tuple[RankedItems, FinalRankerRunMetrics]:
        started = perf_counter()
        final_score_result, feature_match_result = self._validate_context(context)

        try:
            result, metrics = run_final_ranking(
                final_score_result=final_score_result,
                feature_match_result=feature_match_result,
                recommendation_request=context.recommendation_request,
                config_versions=context.config_versions,
            )
        except FinalRankerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise FinalRankerError(
                f"final ranking failed for run: {context.run_id}",
            ) from exc

        latency_ms = int((perf_counter() - started) * 1_000)
        metrics = FinalRankerRunMetrics(
            final_ranker_selected_count=metrics.final_ranker_selected_count,
            final_ranker_latency_ms=latency_ms,
            final_ranker_mmr_applied=metrics.final_ranker_mmr_applied,
            mmr_rank_shift_count=metrics.mmr_rank_shift_count,
            final_ranker_feature_match_missing_count=(
                metrics.final_ranker_feature_match_missing_count
            ),
            top_k_clipped=metrics.top_k_clipped,
        )
        self._log_ranking_completed(context, result, metrics)
        return result, metrics

    def _validate_context(
        self,
        context: ExecutionContext,
    ) -> tuple[FinalScoreResult, FeatureMatchResult]:
        if context.run_id is None:
            raise FinalRankerError("run_id is required on execution_context")

        final_score_result = getattr(context, "final_score_result", None)
        if final_score_result is None:
            raise FinalRankerError(
                "final_score_result is required on execution_context",
            )

        feature_match_result = context.feature_match_result
        if feature_match_result is None:
            raise FinalRankerError(
                "feature_match_result is required on execution_context",
            )

        if context.recommendation_request is None:
            raise FinalRankerError(
                "recommendation_request is required on execution_context",
            )

        return final_score_result, feature_match_result

    def _log_ranking_completed(
        self,
        context: ExecutionContext,
        result: RankedItems,
        metrics: FinalRankerRunMetrics,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            final_ranker_selected_count=metrics.final_ranker_selected_count,
            final_ranker_latency_ms=metrics.final_ranker_latency_ms,
            final_ranker_mmr_applied=metrics.final_ranker_mmr_applied,
            mmr_rank_shift_count=metrics.mmr_rank_shift_count,
            final_ranker_feature_match_missing_count=(
                metrics.final_ranker_feature_match_missing_count
            ),
            top_k_clipped=metrics.top_k_clipped,
            top_k_used=result.top_k_used,
            mmr_applied=result.mmr_applied,
            module_id=self.module_id,
        )


def _attach_outputs(
    context: ExecutionContext,
    result: RankedItems,
    metrics: FinalRankerRunMetrics,
) -> None:
    context.ranked_items = result  # type: ignore[assignment]
    context.final_ranker_selected_count = metrics.final_ranker_selected_count  # type: ignore[attr-defined]
    context.final_ranker_latency_ms = metrics.final_ranker_latency_ms  # type: ignore[attr-defined]
    context.final_ranker_mmr_applied = metrics.final_ranker_mmr_applied  # type: ignore[attr-defined]
    context.mmr_rank_shift_count = metrics.mmr_rank_shift_count  # type: ignore[attr-defined]
    context.final_ranker_feature_match_missing_count = (  # type: ignore[attr-defined]
        metrics.final_ranker_feature_match_missing_count
    )
    context.top_k_clipped = metrics.top_k_clipped  # type: ignore[attr-defined]


def build_default_final_ranker() -> FinalRanker:
    return FinalRanker()
