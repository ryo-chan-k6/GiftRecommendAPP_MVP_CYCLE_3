"""Result build logic for MOD-RECO-021."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from reco.domain.recommendation.result import (
    RecommendationResult,
    RecommendationResultItem,
    ResultStatus,
)

from .errors import RecommendationResultBuilderError
from .models import (
    BuiltRecommendationResult,
    BuiltRecommendationResultItem,
    RecommendationResultHeaderInsertRow,
    RecommendationResultBuilderRunMetrics,
    ResultHeaderStatus,
)

if TYPE_CHECKING:
    from reco.application.context_scorer.models import ContextScoreResult
    from reco.application.final_ranker.models import RankedItems
    from reco.application.meaning_match_aggregator.models import MeaningMatchResult
    from reco.application.popularity_scorer.models import PopularityScoreResult
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )
    from reco.application.risk_scorer.models import RiskPenaltyResult

_VERSION_KEY_CANDIDATES: tuple[tuple[str, ...], ...] = (
    ("semantic_config_version_id", "semantic_config_version"),
    ("model_version_id", "model_version", "model_versions.embedding"),
    ("matching_config_id", "matching_config"),
    ("ranking_config_id", "ranking_config"),
)


def resolve_version_ids(
    config_versions: dict[str, str],
) -> tuple[str, str, str, str]:
    resolved: list[str] = []
    for keys in _VERSION_KEY_CANDIDATES:
        value = None
        for key in keys:
            candidate = config_versions.get(key)
            if candidate:
                value = candidate
                break
        if not value:
            raise RecommendationResultBuilderError(
                f"missing config version key: {keys[0]}",
            )
        resolved.append(value)
    return resolved[0], resolved[1], resolved[2], resolved[3]


def _index_by_item_id(entries: tuple[object, ...]) -> dict[str, object]:
    return {getattr(entry, "item_id"): entry for entry in entries}


def _build_score_breakdown_json(
    *,
    ranked_breakdown: dict[str, object],
    context_score: float,
    social_match: float,
    symbolic_match: float,
    popularity_score: float | None,
    risk_penalty: float | None,
    final_score: float,
    formula_version: str,
) -> tuple[dict[str, object], bool]:
    breakdown = deepcopy(ranked_breakdown)
    partial = False

    breakdown["context_score"] = {
        "value": context_score,
        "social_match": social_match,
        "symbolic_match": symbolic_match,
    }

    if popularity_score is not None:
        breakdown["popularity_score"] = {"value": popularity_score}
    else:
        partial = True

    if risk_penalty is not None:
        breakdown["risk_penalty"] = {"value": risk_penalty}
    else:
        partial = True

    breakdown["final_score"] = {
        "value": final_score,
        "formula_version": formula_version,
    }
    return breakdown, partial


def build_recommendation_result(
    context: ExecutionContext,
) -> tuple[BuiltRecommendationResult, RecommendationResultBuilderRunMetrics]:
    ranked_items = context.ranked_items
    if ranked_items is None:
        raise RecommendationResultBuilderError(
            "ranked_items is required on execution_context",
        )

    if context.recommendation_run is None:
        raise RecommendationResultBuilderError(
            "recommendation_run is required on execution_context",
        )

    request = context.recommendation_request
    run_id = context.run_id
    if run_id is None:
        raise RecommendationResultBuilderError("run_id is required on execution_context")

    semantic_id, model_id, matching_id, ranking_id = resolve_version_ids(
        context.config_versions,
    )
    request_mode = _resolve_request_mode(context)
    generated_at = datetime.now(UTC)
    recommendation_result_id = str(uuid4())
    entries = ranked_items.entries
    item_count = len(entries)
    result_status = (
        ResultHeaderStatus.EMPTY if item_count == 0 else ResultHeaderStatus.GENERATED
    )
    fallback_used = any(getattr(entry, "is_fallback", False) for entry in entries)

    header = RecommendationResultHeaderInsertRow(
        recommendation_result_id=recommendation_result_id,
        recommendation_request_id=request.request_id,
        recommendation_run_id=run_id,
        request_mode=request_mode,
        trace_id=context.trace_id,
        result_status=result_status,
        top_k=ranked_items.top_k_used,
        result_item_count=item_count,
        candidate_count=context.retrieval_candidate_count,
        fallback_used=fallback_used,
        semantic_config_version_id=semantic_id,
        model_version_id=model_id,
        matching_config_id=matching_id,
        ranking_config_id=ranking_id,
        reason_template_version_id=None,
        generated_at=generated_at,
    )

    if item_count == 0:
        metrics = RecommendationResultBuilderRunMetrics(
            result_builder_item_count=0,
            result_builder_latency_ms=0,
            result_builder_header_persisted=False,
            zero_result_header_count=1,
            score_breakdown_partial_count=0,
        )
        return BuiltRecommendationResult(header=header, items=()), metrics

    context_scores = _require_score_result(
        context.context_score_result,
        field_name="context_score_result",
    )
    meaning_matches = _require_score_result(
        context.meaning_match_result,
        field_name="meaning_match_result",
    )
    popularity_by_item = _index_by_item_id(
        context.popularity_score_result.entries
        if context.popularity_score_result is not None
        else (),
    )
    risk_by_item = _index_by_item_id(
        context.risk_penalty_result.entries
        if context.risk_penalty_result is not None
        else (),
    )
    context_by_item = _index_by_item_id(context_scores.entries)
    meaning_by_item = _index_by_item_id(meaning_matches.entries)

    formula_version = ranking_id
    partial_count = 0
    built_items: list[BuiltRecommendationResultItem] = []

    for entry in sorted(entries, key=lambda item: item.rank):
        context_entry = context_by_item.get(entry.item_id)
        if context_entry is None:
            raise RecommendationResultBuilderError(
                f"context_score missing for item_id: {entry.item_id}",
            )

        meaning_entry = meaning_by_item.get(entry.item_id)
        if meaning_entry is None:
            raise RecommendationResultBuilderError(
                f"meaning_match missing for item_id: {entry.item_id}",
            )

        popularity_entry = popularity_by_item.get(entry.item_id)
        risk_entry = risk_by_item.get(entry.item_id)
        popularity_score = (
            getattr(popularity_entry, "popularity_score", None)
            if popularity_entry is not None
            else None
        )
        risk_penalty = (
            getattr(risk_entry, "risk_penalty", None) if risk_entry is not None else None
        )

        score_breakdown_json, partial = _build_score_breakdown_json(
            ranked_breakdown=dict(entry.score_breakdown),
            context_score=getattr(context_entry, "context_score"),
            social_match=getattr(meaning_entry, "social_match"),
            symbolic_match=getattr(meaning_entry, "symbolic_match"),
            popularity_score=popularity_score,
            risk_penalty=risk_penalty,
            final_score=entry.final_score,
            formula_version=formula_version,
        )
        if partial:
            partial_count += 1

        built_items.append(
            BuiltRecommendationResultItem(
                recommendation_result_item_id=str(uuid4()),
                recommendation_result_id=recommendation_result_id,
                item_id=entry.item_id,
                rank=entry.rank,
                final_score=entry.final_score,
                context_score=getattr(context_entry, "context_score"),
                score_breakdown_json=score_breakdown_json,
                is_displayed=entry.is_displayed,
                is_fallback=getattr(entry, "is_fallback", False),
            ),
        )

    metrics = RecommendationResultBuilderRunMetrics(
        result_builder_item_count=len(built_items),
        result_builder_latency_ms=0,
        result_builder_header_persisted=False,
        zero_result_header_count=0,
        score_breakdown_partial_count=partial_count,
    )
    return BuiltRecommendationResult(header=header, items=tuple(built_items)), metrics


def _require_score_result(
    value: ContextScoreResult | MeaningMatchResult | None,
    *,
    field_name: str,
) -> ContextScoreResult | MeaningMatchResult:
    if value is None:
        raise RecommendationResultBuilderError(
            f"{field_name} is required when ranked_items has entries",
        )
    return value


def _resolve_request_mode(context: ExecutionContext) -> str:
    execution = context.recommendation_request.execution
    if execution is not None:
        return execution.mode.value
    return context.execution_mode.value


def to_domain_recommendation_result(
    built: BuiltRecommendationResult,
) -> RecommendationResult:
    status = (
        ResultStatus.EMPTY
        if built.header.result_status == ResultHeaderStatus.EMPTY
        else ResultStatus.COMPLETED
    )
    items = tuple(
        RecommendationResultItem(
            item_id=item.item_id,
            rank=item.rank,
            final_score=item.final_score,
            is_fallback=item.is_fallback,
        )
        for item in built.items
    )
    version_info = {
        "recommendation_result_id": built.header.recommendation_result_id,
        "semantic_config_version_id": built.header.semantic_config_version_id,
        "model_version_id": built.header.model_version_id,
        "matching_config_id": built.header.matching_config_id,
        "ranking_config_id": built.header.ranking_config_id,
        "request_mode": built.header.request_mode,
        "trace_id": built.header.trace_id,
        "top_k": str(built.header.top_k),
        "result_item_count": str(built.header.result_item_count),
    }
    if built.header.candidate_count is not None:
        version_info["candidate_count"] = str(built.header.candidate_count)

    return RecommendationResult(
        run_id=built.header.recommendation_run_id,
        request_id=built.header.recommendation_request_id,
        items=items,
        result_status=status,
        version_info=version_info,
    )
