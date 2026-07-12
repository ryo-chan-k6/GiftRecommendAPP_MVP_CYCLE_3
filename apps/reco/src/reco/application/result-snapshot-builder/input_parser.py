"""Input parsing for MOD-RECO-022."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .constants import BUILDER_ITEMS_VERSION_INFO_KEY
from .errors import ResultSnapshotBuilderError
from .models import SnapshotBuilderInput, SnapshotBuilderInputItem

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


def parse_snapshot_builder_input(context: ExecutionContext) -> SnapshotBuilderInput:
    """execution_context から Snapshot 構築入力を解釈する。"""
    recommendation_result = context.recommendation_result
    if recommendation_result is None:
        raise ResultSnapshotBuilderError(
            "recommendation_result is required on execution_context",
        )

    version_info = recommendation_result.version_info or {}
    recommendation_result_id = version_info.get("recommendation_result_id")
    if not recommendation_result_id:
        raise ResultSnapshotBuilderError(
            "recommendation_result_id is required in recommendation_result.version_info",
        )

    result_item_count_raw = version_info.get("result_item_count")
    if result_item_count_raw is None:
        raise ResultSnapshotBuilderError(
            "result_item_count is required in recommendation_result.version_info",
        )

    try:
        result_item_count = int(result_item_count_raw)
    except ValueError as exc:
        raise ResultSnapshotBuilderError(
            "result_item_count must be an integer",
        ) from exc

    if result_item_count < 1:
        raise ResultSnapshotBuilderError(
            "result_item_count must be >= 1 for snapshot builder",
        )

    items = _parse_items(version_info, recommendation_result_id, context)
    if len(items) != result_item_count:
        raise ResultSnapshotBuilderError(
            "items length does not match result_item_count",
        )

    return SnapshotBuilderInput(
        recommendation_result_id=recommendation_result_id,
        result_item_count=result_item_count,
        items=items,
    )


def _parse_items(
    version_info: dict[str, str],
    recommendation_result_id: str,
    context: ExecutionContext,
) -> tuple[SnapshotBuilderInputItem, ...]:
    encoded = version_info.get(BUILDER_ITEMS_VERSION_INFO_KEY)
    if encoded:
        return _parse_encoded_items(encoded, recommendation_result_id)

    return _parse_domain_items(context, recommendation_result_id)


def _parse_encoded_items(
    encoded: str,
    recommendation_result_id: str,
) -> tuple[SnapshotBuilderInputItem, ...]:
    try:
        payload = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise ResultSnapshotBuilderError(
            "invalid _builder_items JSON in version_info",
        ) from exc

    if not isinstance(payload, list):
        raise ResultSnapshotBuilderError(
            "_builder_items must be a JSON array",
        )

    items: list[SnapshotBuilderInputItem] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ResultSnapshotBuilderError(
                "_builder_items entries must be objects",
            )
        items.append(_item_from_dict(entry, recommendation_result_id))
    return tuple(items)


def _parse_domain_items(
    context: ExecutionContext,
    recommendation_result_id: str,
) -> tuple[SnapshotBuilderInputItem, ...]:
    recommendation_result = context.recommendation_result
    if recommendation_result is None:
        raise ResultSnapshotBuilderError(
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

    items: list[SnapshotBuilderInputItem] = []
    for domain_item in recommendation_result.items:
        context_score = context_scores.get(domain_item.item_id)
        if context_score is None:
            raise ResultSnapshotBuilderError(
                f"context_score missing for item_id: {domain_item.item_id}",
            )

        if domain_item.final_score is None:
            raise ResultSnapshotBuilderError(
                f"final_score missing for item_id: {domain_item.item_id}",
            )

        version_info = recommendation_result.version_info or {}
        item_key = f"item:{domain_item.item_id}:recommendation_result_item_id"
        recommendation_result_item_id = version_info.get(item_key)
        if not recommendation_result_item_id:
            raise ResultSnapshotBuilderError(
                f"{item_key} is required in recommendation_result.version_info",
            )

        items.append(
            SnapshotBuilderInputItem(
                recommendation_result_item_id=recommendation_result_item_id,
                recommendation_result_id=recommendation_result_id,
                item_id=domain_item.item_id,
                rank=domain_item.rank,
                final_score=domain_item.final_score,
                context_score=context_score,
                score_breakdown_json=_optional_breakdown(version_info, domain_item.item_id),
                is_displayed=_optional_bool(version_info, domain_item.item_id, "is_displayed", True),
                is_fallback=domain_item.is_fallback,
            ),
        )

    return tuple(items)


def _item_from_dict(
    entry: dict[str, object],
    recommendation_result_id: str,
) -> SnapshotBuilderInputItem:
    required_fields = (
        "recommendation_result_item_id",
        "item_id",
        "rank",
        "final_score",
        "context_score",
        "is_displayed",
        "is_fallback",
    )
    for field in required_fields:
        if field not in entry:
            raise ResultSnapshotBuilderError(
                f"_builder_items entry missing field: {field}",
            )

    score_breakdown = entry.get("score_breakdown_json")
    if score_breakdown is not None and not isinstance(score_breakdown, dict):
        raise ResultSnapshotBuilderError(
            "score_breakdown_json must be an object when present",
        )

    return SnapshotBuilderInputItem(
        recommendation_result_item_id=str(entry["recommendation_result_item_id"]),
        recommendation_result_id=str(
            entry.get("recommendation_result_id", recommendation_result_id),
        ),
        item_id=str(entry["item_id"]),
        rank=int(entry["rank"]),  # type: ignore[arg-type]
        final_score=float(entry["final_score"]),  # type: ignore[arg-type]
        context_score=float(entry["context_score"]),  # type: ignore[arg-type]
        score_breakdown_json=score_breakdown,
        is_displayed=bool(entry["is_displayed"]),
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
        raise ResultSnapshotBuilderError(
            f"invalid score_breakdown_json for item_id: {item_id}",
        ) from exc
    if not isinstance(payload, dict):
        raise ResultSnapshotBuilderError(
            f"score_breakdown_json must be an object for item_id: {item_id}",
        )
    return payload


def _optional_bool(
    version_info: dict[str, str],
    item_id: str,
    field: str,
    default: bool,
) -> bool:
    raw = version_info.get(f"item:{item_id}:{field}")
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes"}


def encode_builder_items(
    items: tuple[SnapshotBuilderInputItem, ...],
) -> str:
    """version_info 用に 021 明細を JSON エンコードする。"""
    payload = [
        {
            "recommendation_result_item_id": item.recommendation_result_item_id,
            "recommendation_result_id": item.recommendation_result_id,
            "item_id": item.item_id,
            "rank": item.rank,
            "final_score": item.final_score,
            "context_score": item.context_score,
            "score_breakdown_json": item.score_breakdown_json,
            "is_displayed": item.is_displayed,
            "is_fallback": item.is_fallback,
        }
        for item in items
    ]
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)
