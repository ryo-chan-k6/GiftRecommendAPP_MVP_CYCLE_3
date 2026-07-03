"""MOD-RECO-018 Risk Scorer implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, PHASE_NAME
from .errors import RiskScorerError
from .models import RiskPenaltyResult, RiskScorerRunMetrics
from .scoring_engine import run_risk_scoring

if TYPE_CHECKING:
    from reco.application.feature_matcher.models import FeatureMatchResult
    from reco.application.meaning_match_aggregator.models import MeaningMatchResult
    from reco.application.popularity_scorer.models import PopularityScoreResult
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class RiskScorer:
    """PipelineModulePort implementation for Risk Scorer."""

    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        result, metrics = self.score_risk(context)
        _attach_outputs(context, result, metrics)
        context.completed_modules.append(self.module_id)
        return context

    def score_risk(
        self,
        context: ExecutionContext,
    ) -> tuple[RiskPenaltyResult, RiskScorerRunMetrics]:
        started = perf_counter()
        popularity_score_result, feature_match_result, meaning_match_result = (
            self._validate_context(context)
        )

        try:
            result, metrics = run_risk_scoring(
                popularity_score_result=popularity_score_result,
                feature_match_result=feature_match_result,
                meaning_match_result=meaning_match_result,
                config_versions=context.config_versions,
            )
        except RiskScorerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RiskScorerError(
                f"risk scoring failed for run: {context.run_id}",
            ) from exc

        latency_ms = int((perf_counter() - started) * 1_000)
        metrics = RiskScorerRunMetrics(
            risk_scorer_candidate_count=metrics.risk_scorer_candidate_count,
            risk_scorer_latency_ms=latency_ms,
            risk_missing_signal_count=metrics.risk_missing_signal_count,
            risk_penalty_value_out_of_range_count=(
                metrics.risk_penalty_value_out_of_range_count
            ),
            avoid_risk_nonzero_count=metrics.avoid_risk_nonzero_count,
        )
        self._log_scoring_completed(context, result, metrics)
        return result, metrics

    def _validate_context(
        self,
        context: ExecutionContext,
    ) -> tuple[PopularityScoreResult, FeatureMatchResult, MeaningMatchResult]:
        if context.run_id is None:
            raise RiskScorerError("run_id is required on execution_context")

        popularity_score_result = getattr(context, "popularity_score_result", None)
        if popularity_score_result is None:
            raise RiskScorerError(
                "popularity_score_result is required on execution_context",
            )

        feature_match_result = context.feature_match_result
        if feature_match_result is None:
            raise RiskScorerError(
                "feature_match_result is required on execution_context",
            )

        meaning_match_result = context.meaning_match_result
        if meaning_match_result is None:
            raise RiskScorerError(
                "meaning_match_result is required on execution_context",
            )

        return popularity_score_result, feature_match_result, meaning_match_result

    def _log_scoring_completed(
        self,
        context: ExecutionContext,
        result: RiskPenaltyResult,
        metrics: RiskScorerRunMetrics,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            risk_scorer_candidate_count=metrics.risk_scorer_candidate_count,
            risk_scorer_latency_ms=metrics.risk_scorer_latency_ms,
            risk_missing_signal_count=metrics.risk_missing_signal_count,
            risk_penalty_value_out_of_range_count=(
                metrics.risk_penalty_value_out_of_range_count
            ),
            avoid_risk_nonzero_count=metrics.avoid_risk_nonzero_count,
            total_scored=result.total_scored,
            module_id=self.module_id,
        )


def _attach_outputs(
    context: ExecutionContext,
    result: RiskPenaltyResult,
    metrics: RiskScorerRunMetrics,
) -> None:
    context.risk_penalty_result = result  # type: ignore[attr-defined]
    context.risk_scorer_candidate_count = metrics.risk_scorer_candidate_count  # type: ignore[attr-defined]
    context.risk_scorer_latency_ms = metrics.risk_scorer_latency_ms  # type: ignore[attr-defined]
    context.risk_missing_signal_count = metrics.risk_missing_signal_count  # type: ignore[attr-defined]
    context.risk_penalty_value_out_of_range_count = (  # type: ignore[attr-defined]
        metrics.risk_penalty_value_out_of_range_count
    )
    context.avoid_risk_nonzero_count = metrics.avoid_risk_nonzero_count  # type: ignore[attr-defined]


def build_default_risk_scorer() -> RiskScorer:
    return RiskScorer()
