"""Reason fallback injection (MOD-RECO-001 §10.3)."""

from __future__ import annotations

from reco.domain.recommendation.result import (
    ReasonStatus,
    RecommendationResult,
    RecommendationResultItem,
    ResultStatus,
)

from .constants import GENERIC_REASON_SUMMARY
from .execution_context import ExecutionContext


def inject_generic_reason_fallback(context: ExecutionContext) -> ExecutionContext:
    """Inject §17.2 generic reason text when MOD-RECO-023 is unrecoverable."""
    result = context.recommendation_result
    if result is None:
        return context

    updated_items: list[RecommendationResultItem] = []
    fallback_count = 0

    for item in result.items:
        if item.reason_summary:
            updated_items.append(item)
            continue

        updated_items.append(
            RecommendationResultItem(
                item_id=item.item_id,
                rank=item.rank,
                final_score=item.final_score,
                reason_summary=GENERIC_REASON_SUMMARY,
                reason_status=ReasonStatus.COMPLETED,
                is_fallback=True,
            )
        )
        fallback_count += 1

    result_status = result.result_status
    if fallback_count and fallback_count < len(result.items):
        result_status = ResultStatus.PARTIAL

    context.recommendation_result = RecommendationResult(
        run_id=result.run_id,
        request_id=result.request_id,
        items=tuple(updated_items),
        result_status=result_status,
        version_info=result.version_info,
    )
    context.reason_fallback_count += fallback_count
    return context
