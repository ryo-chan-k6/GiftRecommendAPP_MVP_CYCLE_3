"""MOD-RECO-023 Reason Generator implementation."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from time import perf_counter
from typing import TYPE_CHECKING

from reco.application.recommendation_orchestrator.ports import (
    ReasonGenerationOutcome,
    ReasonGenerationResult,
)
from reco.domain.recommendation.result import (
    ReasonStatus,
    RecommendationResultItem,
)
from reco.infrastructure.external_ai.client import ExternalAiClient, ScaffoldExternalAiClient
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import GENERIC_REASON_SUMMARY, MODULE_ID, PHASE_NAME
from .errors import ReasonGeneratorError
from .in_memory_repository import (
    InMemoryItemSemanticReadRepository,
    InMemoryRecommendationReasonRepository,
    build_default_in_memory_item_semantic_read_repository,
    build_default_in_memory_reason_template_repository,
)
from .input_parser import parse_reason_generator_input
from .models import GeneratedReason, ReasonGeneratorRunMetrics
from .ports import ItemSemanticReadPort, ReasonTemplateReadPort, RecommendationReasonRepositoryPort
from .reason_engine import aggregate_outcome, generate_reasons_for_run

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class ReasonGenerator:
    """ReasonGeneratorPort implementation for MOD-RECO-023."""

    template_reader: ReasonTemplateReadPort = field(
        default_factory=build_default_in_memory_reason_template_repository,
    )
    item_semantic_reader: ItemSemanticReadPort = field(
        default_factory=build_default_in_memory_item_semantic_read_repository,
    )
    reason_repository: RecommendationReasonRepositoryPort = field(
        default_factory=InMemoryRecommendationReasonRepository,
    )
    llm_client: ExternalAiClient | None = field(default_factory=ScaffoldExternalAiClient)
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def generate(self, context: ExecutionContext) -> ReasonGenerationResult:
        started = perf_counter()
        try:
            reason_input = parse_reason_generator_input(context)
        except ReasonGeneratorError:
            context.completed_modules.append(self.module_id)
            return ReasonGenerationResult(outcome=ReasonGenerationOutcome.UNRECOVERABLE)

        semantic_config_version_id = context.config_versions.get("semantic_config_version_id")
        if not semantic_config_version_id:
            semantic_config_version_id = "scaffold-semantic-config-version"

        item_ids = tuple(item.item_id for item in reason_input.items)
        semantic_records = self.item_semantic_reader.fetch_by_item_ids(
            item_ids,
            semantic_config_version_id=semantic_config_version_id,
        )

        generated, metrics = generate_reasons_for_run(
            reason_input,
            recommendation_request=context.recommendation_request,
            feature_match_result=context.feature_match_result,
            meaning_match_result=context.meaning_match_result,
            risk_penalty_result=context.risk_penalty_result,
            semantic_records=semantic_records,
            template_reader=self.template_reader,
            reason_repository=self.reason_repository,
            llm_client=self.llm_client,
        )

        latency_ms = int((perf_counter() - started) * 1_000)
        metrics = ReasonGeneratorRunMetrics(
            reason_generator_item_count=metrics.reason_generator_item_count,
            reason_generator_success_count=metrics.reason_generator_success_count,
            reason_generator_fallback_count=metrics.reason_generator_fallback_count,
            reason_generator_persisted=metrics.reason_generator_persisted,
            reason_generation_latency_ms=latency_ms,
        )

        _attach_outputs(context, generated, metrics)
        self._log_generation_completed(context, metrics, generated)

        context.completed_modules.append(self.module_id)
        outcome = aggregate_outcome(generated)
        first_reason = generated[0] if generated else None
        return ReasonGenerationResult(
            outcome=outcome,
            reason_summary=first_reason.reason_summary if first_reason else GENERIC_REASON_SUMMARY,
            is_fallback=any(reason.is_fallback for reason in generated),
        )

    def _log_generation_completed(
        self,
        context: ExecutionContext,
        metrics: ReasonGeneratorRunMetrics,
        generated: tuple[GeneratedReason, ...],
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            reason_generator_item_count=metrics.reason_generator_item_count,
            reason_generator_success_count=metrics.reason_generator_success_count,
            reason_generator_fallback_count=metrics.reason_generator_fallback_count,
            reason_generator_persisted=metrics.reason_generator_persisted,
            reason_generation_latency_ms=metrics.reason_generation_latency_ms,
            module_id=self.module_id,
            fallback_item_count=sum(1 for reason in generated if reason.is_fallback),
        )


def _attach_outputs(
    context: ExecutionContext,
    generated: tuple[GeneratedReason, ...],
    metrics: ReasonGeneratorRunMetrics,
) -> None:
    recommendation_result = context.recommendation_result
    if recommendation_result is None:
        raise ReasonGeneratorError(
            "recommendation_result is required on execution_context",
        )

    reason_by_item_id = {reason.item_id: reason for reason in generated}
    updated_items: list[RecommendationResultItem] = []
    for item in recommendation_result.items:
        generated_reason = reason_by_item_id.get(item.item_id)
        if generated_reason is None:
            updated_items.append(item)
            continue

        updated_items.append(
            RecommendationResultItem(
                item_id=item.item_id,
                rank=item.rank,
                final_score=item.final_score,
                reason_summary=generated_reason.reason_summary,
                reason_status=ReasonStatus.COMPLETED,
                is_fallback=generated_reason.is_fallback or item.is_fallback,
            ),
        )

    version_info = dict(recommendation_result.version_info or {})
    version_info.update(
        {
            "reason_generator_item_count": str(metrics.reason_generator_item_count),
            "reason_generator_success_count": str(metrics.reason_generator_success_count),
            "reason_generator_fallback_count": str(metrics.reason_generator_fallback_count),
            "reason_generator_persisted": "true" if metrics.reason_generator_persisted else "false",
            "reason_generation_latency_ms": str(metrics.reason_generation_latency_ms),
        },
    )
    for reason in generated:
        if reason.recommendation_reason_id:
            version_info[
                f"item:{reason.item_id}:recommendation_reason_id"
            ] = reason.recommendation_reason_id

    context.recommendation_result = replace(
        recommendation_result,
        items=tuple(updated_items),
        version_info=version_info,
    )
    context.reason_generator_item_count = metrics.reason_generator_item_count
    context.reason_generator_success_count = metrics.reason_generator_success_count
    context.reason_generator_fallback_count = metrics.reason_generator_fallback_count
    context.reason_generator_persisted = metrics.reason_generator_persisted
    context.reason_generation_latency_ms = metrics.reason_generation_latency_ms


def build_default_reason_generator() -> ReasonGenerator:
    return ReasonGenerator()
