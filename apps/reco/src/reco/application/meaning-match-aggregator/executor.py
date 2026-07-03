"""MOD-RECO-015 Meaning Match Aggregator implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .aggregation_engine import run_meaning_match_aggregation
from .constants import MODULE_ID, PHASE_NAME
from .errors import MeaningMatchAggregatorError
from .models import MeaningMatchAggregatorRunMetrics, MeaningMatchResult

if TYPE_CHECKING:
    from reco.application.feature_matcher.models import FeatureMatchResult
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class MeaningMatchAggregator:
    """PipelineModulePort implementation for Meaning Match Aggregator."""

    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        result, metrics = self.aggregate_meaning_match(context)
        _attach_outputs(context, result, metrics)
        context.completed_modules.append(self.module_id)
        return context

    def aggregate_meaning_match(
        self,
        context: ExecutionContext,
    ) -> tuple[MeaningMatchResult, MeaningMatchAggregatorRunMetrics]:
        started = perf_counter()
        feature_match_result, default_matching_config_id = self._validate_context(
            context,
        )

        try:
            result, metrics = run_meaning_match_aggregation(
                feature_match_result=feature_match_result,
                config_versions=context.config_versions,
                default_matching_config_id=default_matching_config_id,
            )
        except MeaningMatchAggregatorError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MeaningMatchAggregatorError(
                f"meaning match aggregation failed for run: {context.run_id}",
            ) from exc

        latency_ms = int((perf_counter() - started) * 1_000)
        metrics = MeaningMatchAggregatorRunMetrics(
            meaning_match_aggregator_candidate_count=(
                metrics.meaning_match_aggregator_candidate_count
            ),
            meaning_match_aggregator_latency_ms=latency_ms,
            meaning_match_value_out_of_range_count=(
                metrics.meaning_match_value_out_of_range_count
            ),
        )
        self._log_aggregation_completed(context, result, metrics)
        return result, metrics

    def _validate_context(
        self,
        context: ExecutionContext,
    ) -> tuple[FeatureMatchResult, str]:
        if context.run_id is None:
            raise MeaningMatchAggregatorError("run_id is required on execution_context")

        feature_match_result = context.feature_match_result
        if feature_match_result is None:
            raise MeaningMatchAggregatorError(
                "feature_match_result is required on execution_context",
            )

        matching_config_id = context.config_versions.get("matching_config_id")
        if not matching_config_id:
            raise MeaningMatchAggregatorError(
                "matching_config_id is required on execution_context.config_versions",
            )

        return feature_match_result, str(matching_config_id)

    def _log_aggregation_completed(
        self,
        context: ExecutionContext,
        result: MeaningMatchResult,
        metrics: MeaningMatchAggregatorRunMetrics,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            meaning_match_aggregator_candidate_count=(
                metrics.meaning_match_aggregator_candidate_count
            ),
            meaning_match_aggregator_latency_ms=metrics.meaning_match_aggregator_latency_ms,
            meaning_match_value_out_of_range_count=(
                metrics.meaning_match_value_out_of_range_count
            ),
            total_aggregated=result.total_aggregated,
            module_id=self.module_id,
        )


def _attach_outputs(
    context: ExecutionContext,
    result: MeaningMatchResult,
    metrics: MeaningMatchAggregatorRunMetrics,
) -> None:
    context.meaning_match_result = result
    context.meaning_match_aggregator_candidate_count = (
        metrics.meaning_match_aggregator_candidate_count
    )
    context.meaning_match_aggregator_latency_ms = metrics.meaning_match_aggregator_latency_ms
    context.meaning_match_value_out_of_range_count = (
        metrics.meaning_match_value_out_of_range_count
    )


def build_default_meaning_match_aggregator() -> MeaningMatchAggregator:
    return MeaningMatchAggregator()
