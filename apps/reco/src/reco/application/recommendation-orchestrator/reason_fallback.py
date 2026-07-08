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


def apply_partial_result_status_if_needed(context: ExecutionContext) -> ExecutionContext:
    """Set ``result_status`` to ``partial`` when only some Items used Reason fallback."""
    result = context.recommendation_result
    if result is None or not result.items:
        return context

    fallback_count = sum(1 for item in result.items if item.is_fallback)
    if not fallback_count or fallback_count >= len(result.items):
        return context

    context.recommendation_result = RecommendationResult(
        run_id=result.run_id,
        request_id=result.request_id,
        items=result.items,
        result_status=ResultStatus.PARTIAL,
        version_info=result.version_info,
    )
    return context
