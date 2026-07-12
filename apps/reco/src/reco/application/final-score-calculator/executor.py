"""MOD-RECO-019 Final Score Calculator implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, PHASE_NAME
from .errors import FinalScoreCalculatorError
from .models import FinalScoreCalculatorRunMetrics, FinalScoreResult
from .scoring_engine import run_final_score_calculation

if TYPE_CHECKING:
    from reco.application.context_scorer.models import ContextScoreResult
    from reco.application.popularity_scorer.models import PopularityScoreResult
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )
    from reco.application.risk_scorer.models import RiskPenaltyResult


@dataclass
class FinalScoreCalculator:
    """PipelineModulePort implementation for Final Score Calculator."""

    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        result, metrics = self.calculate_final_score(context)
        _attach_outputs(context, result, metrics)
        context.completed_modules.append(self.module_id)
        return context

    def calculate_final_score(
        self,
        context: ExecutionContext,
    ) -> tuple[FinalScoreResult, FinalScoreCalculatorRunMetrics]:
        started = perf_counter()
        (
            risk_penalty_result,
            context_score_result,
            popularity_score_result,
        ) = self._validate_context(context)

        try:
            result, metrics = run_final_score_calculation(
                risk_penalty_result=risk_penalty_result,
                context_score_result=context_score_result,
                popularity_score_result=popularity_score_result,
                config_versions=context.config_versions,
            )
        except FinalScoreCalculatorError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise FinalScoreCalculatorError(
                f"final score calculation failed for run: {context.run_id}",
            ) from exc

        latency_ms = int((perf_counter() - started) * 1_000)
        metrics = FinalScoreCalculatorRunMetrics(
            final_score_calculator_candidate_count=(
                metrics.final_score_calculator_candidate_count
            ),
            final_score_calculator_latency_ms=latency_ms,
            final_score_excluded_candidate_count=(
                metrics.final_score_excluded_candidate_count
            ),
            final_score_value_out_of_range_count=(
                metrics.final_score_value_out_of_range_count
            ),
        )
        self._log_calculation_completed(context, result, metrics)
        return result, metrics

    def _validate_context(
        self,
        context: ExecutionContext,
    ) -> tuple[RiskPenaltyResult, ContextScoreResult, PopularityScoreResult]:
        if context.run_id is None:
            raise FinalScoreCalculatorError("run_id is required on execution_context")

        risk_penalty_result = context.risk_penalty_result
        if risk_penalty_result is None:
            raise FinalScoreCalculatorError(
                "risk_penalty_result is required on execution_context",
            )

        context_score_result = context.context_score_result
        if context_score_result is None:
            raise FinalScoreCalculatorError(
                "context_score_result is required on execution_context",
            )

        popularity_score_result = context.popularity_score_result
        if popularity_score_result is None:
            raise FinalScoreCalculatorError(
                "popularity_score_result is required on execution_context",
            )

        return risk_penalty_result, context_score_result, popularity_score_result

    def _log_calculation_completed(
        self,
        context: ExecutionContext,
        result: FinalScoreResult,
        metrics: FinalScoreCalculatorRunMetrics,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            final_score_calculator_candidate_count=(
                metrics.final_score_calculator_candidate_count
            ),
            final_score_calculator_latency_ms=metrics.final_score_calculator_latency_ms,
            final_score_excluded_candidate_count=(
                metrics.final_score_excluded_candidate_count
            ),
            final_score_value_out_of_range_count=(
                metrics.final_score_value_out_of_range_count
            ),
            total_scored=result.total_scored,
            module_id=self.module_id,
        )


def _attach_outputs(
    context: ExecutionContext,
    result: FinalScoreResult,
    metrics: FinalScoreCalculatorRunMetrics,
) -> None:
    context.final_score_result = result
    context.final_score_calculator_candidate_count = (
        metrics.final_score_calculator_candidate_count
    )
    context.final_score_calculator_latency_ms = metrics.final_score_calculator_latency_ms
    context.final_score_excluded_candidate_count = (
        metrics.final_score_excluded_candidate_count
    )
    context.final_score_value_out_of_range_count = (
        metrics.final_score_value_out_of_range_count
    )


def build_default_final_score_calculator() -> FinalScoreCalculator:
    return FinalScoreCalculator()
