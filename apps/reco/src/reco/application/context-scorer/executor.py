"""MOD-RECO-016 Context Scorer implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, PHASE_NAME
from .errors import ContextScorerError
from .models import ContextScoreResult, ContextScorerRunMetrics
from .scoring_engine import run_context_scoring

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class ContextScorer:
    """PipelineModulePort implementation for Context Scorer."""

    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        result, metrics = self.score_context(context)
        _attach_outputs(context, result, metrics)
        context.completed_modules.append(self.module_id)
        return context

    def score_context(
        self,
        context: ExecutionContext,
    ) -> tuple[ContextScoreResult, ContextScorerRunMetrics]:
        started = perf_counter()
        meaning_match_result = self._validate_context(context)

        try:
            result, metrics, warning_code = run_context_scoring(
                meaning_match_result=meaning_match_result,
                config_versions=context.config_versions,
                context=context,
            )
        except ContextScorerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ContextScorerError(
                f"context scoring failed for run: {context.run_id}",
            ) from exc

        latency_ms = int((perf_counter() - started) * 1_000)
        metrics = ContextScorerRunMetrics(
            context_scorer_candidate_count=metrics.context_scorer_candidate_count,
            context_scorer_latency_ms=latency_ms,
            context_score_value_out_of_range_count=(
                metrics.context_score_value_out_of_range_count
            ),
            lambda_ctx_applied=metrics.lambda_ctx_applied,
        )
        self._log_scoring_completed(context, result, metrics, warning_code)
        return result, metrics

    def _validate_context(self, context: ExecutionContext):
        if context.run_id is None:
            raise ContextScorerError("run_id is required on execution_context")

        meaning_match_result = getattr(context, "meaning_match_result", None)
        if meaning_match_result is None:
            raise ContextScorerError(
                "meaning_match_result is required on execution_context",
            )

        return meaning_match_result

    def _log_scoring_completed(
        self,
        context: ExecutionContext,
        result: ContextScoreResult,
        metrics: ContextScorerRunMetrics,
        warning_code: str | None,
    ) -> None:
        if warning_code is not None:
            context.error_log_events.append(
                {
                    "module_id": self.module_id,
                    "level": "warning",
                    "message": (
                        f"{warning_code}; using lambda_ctx={metrics.lambda_ctx_applied} "
                        f"for run {context.run_id}"
                    ),
                    "trace_id": context.trace_id,
                },
            )
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            context_scorer_candidate_count=metrics.context_scorer_candidate_count,
            context_scorer_latency_ms=metrics.context_scorer_latency_ms,
            context_score_value_out_of_range_count=(
                metrics.context_score_value_out_of_range_count
            ),
            lambda_ctx_applied=metrics.lambda_ctx_applied,
            total_scored=result.total_scored,
            lambda_ctx_warning_code=warning_code,
            module_id=self.module_id,
        )


def _attach_outputs(
    context: ExecutionContext,
    result: ContextScoreResult,
    metrics: ContextScorerRunMetrics,
) -> None:
    context.context_score_result = result  # type: ignore[attr-defined]
    context.context_scorer_candidate_count = (  # type: ignore[attr-defined]
        metrics.context_scorer_candidate_count
    )
    context.context_scorer_latency_ms = metrics.context_scorer_latency_ms  # type: ignore[attr-defined]
    context.context_score_value_out_of_range_count = (  # type: ignore[attr-defined]
        metrics.context_score_value_out_of_range_count
    )
    context.lambda_ctx_applied = metrics.lambda_ctx_applied  # type: ignore[attr-defined]


def build_default_context_scorer() -> ContextScorer:
    return ContextScorer()
