"""Input parsing for MOD-RECO-023."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .constants import BUILDER_ITEMS_VERSION_INFO_KEY
from .errors import ReasonGeneratorError
from .models import ReasonGeneratorInput, ReasonGeneratorInputItem

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


def parse_reason_generator_input(context: ExecutionContext) -> ReasonGeneratorInput:
    """execution_context から Reason 生成入力を解釈する。"""
    recommendation_result = context.recommendation_result
    if recommendation_result is None:
        raise ReasonGeneratorError(
            "recommendation_result is required on execution_context",
        )

    version_info = recommendation_result.version_info or {}
    snapshot_persisted = version_info.get("snapshot_builder_items_persisted")
    if snapshot_persisted != "true":
        raise ReasonGeneratorError(
            "snapshot_builder_items_persisted must be true before reason generation",
        )

    result_item_count_raw = version_info.get("result_item_count")
    if result_item_count_raw is None:
        raise ReasonGeneratorError(
            "result_item_count is required in recommendation_result.version_info",
        )

    try:
        result_item_count = int(result_item_count_raw)
    except ValueError as exc:
        raise ReasonGeneratorError(
            "result_item_count must be an integer",
        ) from exc

    if result_item_count < 0:
        raise ReasonGeneratorError(
            "result_item_count must be >= 0 for reason generator",
        )

    # 0 件 empty 結果では理由生成対象がない（Matching short-circuit 後など）。
    if result_item_count == 0:
        return ReasonGeneratorInput(
            result_item_count=0,
            items=(),
        )

    items = _parse_items(version_info, context)
    if len(items) != result_item_count:
        raise ReasonGeneratorError(
            "items length does not match result_item_count",
        )

    return ReasonGeneratorInput(
        result_item_count=result_item_count,
        items=items,
    )


def _parse_items(
    version_info: dict[str, str],
    context: ExecutionContext,
) -> tuple[ReasonGeneratorInputItem, ...]:
    encoded = version_info.get(BUILDER_ITEMS_VERSION_INFO_KEY)
    if encoded:
        return _parse_encoded_items(encoded)

    return _parse_domain_items(context)


def _parse_encoded_items(encoded: str) -> tuple[ReasonGeneratorInputItem, ...]:
    try:
        payload = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise ReasonGeneratorError(
            "invalid _builder_items JSON in version_info",
        ) from exc

    if not isinstance(payload, list):
        raise ReasonGeneratorError(
            "_builder_items must be a JSON array",
        )

    items: list[ReasonGeneratorInputItem] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ReasonGeneratorError(
                "_builder_items entries must be objects",
            )
        items.append(_item_from_dict(entry))
    return tuple(sorted(items, key=lambda item: item.rank))


def _parse_domain_items(context: ExecutionContext) -> tuple[ReasonGeneratorInputItem, ...]:
    recommendation_result = context.recommendation_result
    if recommendation_result is None:
        raise ReasonGeneratorError(
            "recommendation_result is required on execution_context",
        )

    context_scores = {
        entry.item_id: entry.context_score
        for entry in (
            context.context_score_result.entries
            if context.context_score_result is not None
            else ()
        )
    }

    version_info = recommendation_result.version_info or {}
    items: list[ReasonGeneratorInputItem] = []
    for domain_item in recommendation_result.items:
        context_score = context_scores.get(domain_item.item_id)
        if context_score is None:
            raise ReasonGeneratorError(
                f"context_score missing for item_id: {domain_item.item_id}",
            )

        if domain_item.final_score is None:
            raise ReasonGeneratorError(
                f"final_score missing for item_id: {domain_item.item_id}",
            )

        item_key = f"item:{domain_item.item_id}:recommendation_result_item_id"
        recommendation_result_item_id = version_info.get(item_key)
        if not recommendation_result_item_id:
            raise ReasonGeneratorError(
                f"{item_key} is required in recommendation_result.version_info",
            )

        items.append(
            ReasonGeneratorInputItem(
                recommendation_result_item_id=recommendation_result_item_id,
                item_id=domain_item.item_id,
                rank=domain_item.rank,
                final_score=domain_item.final_score,
                context_score=context_score,
                score_breakdown_json=_optional_breakdown(version_info, domain_item.item_id),
                is_fallback=domain_item.is_fallback,
            ),
        )

    return tuple(sorted(items, key=lambda item: item.rank))


def _item_from_dict(entry: dict[str, object]) -> ReasonGeneratorInputItem:
    required_fields = (
        "recommendation_result_item_id",
        "item_id",
        "rank",
        "final_score",
        "context_score",
        "is_fallback",
    )
    for field in required_fields:
        if field not in entry:
            raise ReasonGeneratorError(
                f"_builder_items entry missing field: {field}",
            )

    score_breakdown = entry.get("score_breakdown_json")
    if score_breakdown is not None and not isinstance(score_breakdown, dict):
        raise ReasonGeneratorError(
            "score_breakdown_json must be an object when present",
        )

    return ReasonGeneratorInputItem(
        recommendation_result_item_id=str(entry["recommendation_result_item_id"]),
        item_id=str(entry["item_id"]),
        rank=int(entry["rank"]),  # type: ignore[arg-type]
        final_score=float(entry["final_score"]),  # type: ignore[arg-type]
        context_score=float(entry["context_score"]),  # type: ignore[arg-type]
        score_breakdown_json=score_breakdown,
        is_fallback=bool(entry["is_fallback"]),
    )


def _optional_breakdown(
    version_info: dict[str, str],
    item_id: str,
) -> dict[str, object] | None:
    encoded = version_info.get(f"item:{item_id}:score_breakdown_json")
    if encoded is None:
        return None
    try:
        payload = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise ReasonGeneratorError(
            f"invalid score_breakdown_json for item_id: {item_id}",
        ) from exc
    if not isinstance(payload, dict):
        raise ReasonGeneratorError(
            f"score_breakdown_json must be an object for item_id: {item_id}",
        )
    return payload
