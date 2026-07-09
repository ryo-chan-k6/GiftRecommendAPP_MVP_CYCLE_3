"""Response mapper: domain RecommendationResult + ExecutionContext → API Response."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from reco.api.middleware.trace_context import TraceContext
from reco.api.schemas.recommendations import (
    CandidateCountsResponse,
    FeatureDistributionStatResponse,
    InternalRecommendationResultItemResponse,
    MetaResponse,
    MetricSummaryResponse,
    ReasonDataItemResponse,
    ReasonDataResponse,
    RecoRecommendationRunResponseData,
    RecoRecommendationRunSuccessResponse,
    RecoRunMetadataResponse,
    WarningItemResponse,
)
from reco.domain.recommendation.inputs import ExecutionMode
from reco.domain.recommendation.result import (
    ReasonStatus,
    RecommendationResult,
    RecommendationResultItem,
    ResultStatus,
)

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )

_ZERO_RESULT_MESSAGE = "条件に合う商品が見つかりませんでした。"
_UI_DEFAULT_TOP_K = 10


def _version_info_get(version_info: dict[str, str] | None, key: str) -> str | None:
    if not version_info:
        return None
    value = version_info.get(key)
    if value is None or value == "":
        return None
    return value


def _item_version_key(item_id: str, suffix: str) -> str:
    return f"item:{item_id}:{suffix}"


def _parse_score_breakdown(version_info: dict[str, str] | None, item_id: str) -> dict[str, Any] | None:
    raw = _version_info_get(version_info, _item_version_key(item_id, "score_breakdown_json"))
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _map_result_status(status: ResultStatus, item_count: int) -> str:
    # 契約: 0 件も completed。domain EMPTY は API completed へ正規化。
    if item_count == 0 or status == ResultStatus.EMPTY:
        return "completed"
    if status == ResultStatus.PARTIAL:
        return "partial"
    return "completed"


def _resolve_top_k(context: ExecutionContext) -> int:
    execution = context.recommendation_request.execution
    if execution is not None and execution.top_k is not None:
        return execution.top_k
    return _UI_DEFAULT_TOP_K


def _build_candidate_counts(context: ExecutionContext) -> CandidateCountsResponse:
    return CandidateCountsResponse(
        retrieval_count=context.retrieval_candidate_count,
        matching_count=context.feature_matcher_candidate_count,
        ranking_count=context.final_ranker_selected_count,
    )


def _build_warnings(context: ExecutionContext, top_k: int) -> list[WarningItemResponse]:
    warnings: list[WarningItemResponse] = []
    retrieval_count = context.retrieval_candidate_count or 0
    matching_count = context.feature_matcher_candidate_count or 0

    if retrieval_count == 0:
        warnings.append(
            WarningItemResponse(
                code="NO_CANDIDATES_AFTER_RETRIEVAL",
                severity="warn",
            ),
        )
        return warnings

    threshold = min(top_k, 5)
    if matching_count >= 1 and matching_count < threshold:
        warnings.append(
            WarningItemResponse(
                code="LOW_CANDIDATES_AFTER_MATCHING",
                severity="warn",
            ),
        )

    return warnings


def _should_include_debug(context: ExecutionContext) -> bool:
    execution = context.recommendation_request.execution
    if execution is None:
        return False
    if execution.mode == ExecutionMode.EVALUATION:
        return True
    return bool(execution.include_debug_info)


def _build_metric_summary(context: ExecutionContext) -> MetricSummaryResponse | None:
    phase_duration: dict[str, int] = {}
    if context.retrieval_latency_ms is not None:
        phase_duration["retrieval"] = context.retrieval_latency_ms
    if context.feature_matcher_latency_ms is not None:
        phase_duration["matching"] = context.feature_matcher_latency_ms
    if context.final_ranker_latency_ms is not None:
        phase_duration["ranking"] = context.final_ranker_latency_ms
    if context.reason_generation_latency_ms is not None:
        phase_duration["reason"] = context.reason_generation_latency_ms

    if not phase_duration and context.recommendation_latency_ms == 0:
        return None

    return MetricSummaryResponse(
        recommendation_latency_ms=context.recommendation_latency_ms,
        phase_duration_ms=phase_duration or None,
    )


def _map_result_item(
    item: RecommendationResultItem,
    *,
    version_info: dict[str, str] | None,
    include_debug: bool,
    include_reason: bool,
) -> InternalRecommendationResultItemResponse:
    item_id = item.item_id
    result_item_id = (
        _version_info_get(version_info, _item_version_key(item_id, "recommendation_result_item_id"))
        or f"result_item_{item_id}"
    )
    item_name = (
        _version_info_get(version_info, _item_version_key(item_id, "item_name_snapshot"))
        or f"Item {item_id}"
    )
    final_score = item.final_score if item.final_score is not None else 0.0
    score_breakdown = _parse_score_breakdown(version_info, item_id) if include_debug else None

    reason_summary = item.reason_summary
    reason_status: str | None = None
    if include_reason and item.item_id:
        reason_status = (
            item.reason_status.value
            if item.reason_status is not None
            else ReasonStatus.COMPLETED.value
        )
        if not reason_summary:
            reason_summary = "推薦候補として選定しました。"

    return InternalRecommendationResultItemResponse(
        recommendationResultItemId=result_item_id,
        itemId=item_id,
        rank=item.rank,
        itemName=item_name,
        itemPrice=0,
        itemUrl=f"https://example.com/items/{item_id}",
        contextScore=final_score,
        finalScore=final_score,
        scoreBreakdown=score_breakdown,
        reasonSummary=reason_summary,
        reasonStatus=reason_status,
        isFallback=item.is_fallback,
    )


def _build_reason_data(
    items: tuple[RecommendationResultItem, ...],
    *,
    include_reason: bool,
    include_debug: bool,
    version_info: dict[str, str] | None,
) -> ReasonDataResponse | None:
    if not include_reason or not include_debug or not items:
        return None
    reason_items = [
        ReasonDataItemResponse(
            recommendationResultItemId=(
                _version_info_get(
                    version_info,
                    _item_version_key(item.item_id, "recommendation_result_item_id"),
                )
                or f"result_item_{item.item_id}"
            ),
            itemId=item.item_id,
            reasonStatus=(
                item.reason_status.value
                if item.reason_status is not None
                else ReasonStatus.COMPLETED.value
            ),
            reasonSummary=item.reason_summary,
            isFallback=item.is_fallback,
        )
        for item in items
    ]
    return ReasonDataResponse(items=reason_items)


def _build_metadata(
    context: ExecutionContext,
    *,
    include_debug: bool,
) -> RecoRunMetadataResponse:
    execution = context.recommendation_request.execution
    mode = execution.mode.value if execution is not None else "ui"
    debug_payload: dict[str, Any] | None = None
    if include_debug and execution is not None:
        debug_payload = {
            key: value
            for key, value in {
                "evalCaseId": execution.eval_case_id,
                "configName": execution.config_name,
                "versionLabel": execution.version_label,
                "modelVersionId": execution.model_version_id,
            }.items()
            if value is not None
        }
        if context.config_versions:
            debug_payload["configVersions"] = dict(context.config_versions)
    return RecoRunMetadataResponse(mode=mode, debugPayload=debug_payload or None)


def to_success_response(
    *,
    result: RecommendationResult,
    context: ExecutionContext,
    trace: TraceContext,
) -> RecoRecommendationRunSuccessResponse:
    version_info = result.version_info
    item_count = result.item_count
    top_k = _resolve_top_k(context)
    include_debug = _should_include_debug(context)
    execution = context.recommendation_request.execution
    include_reason = bool(execution and execution.include_reason)

    result_id = (
        _version_info_get(version_info, "recommendation_result_id")
        or f"result_{result.run_id}"
    )
    api_status = _map_result_status(result.result_status, item_count)
    fallback_used = any(item.is_fallback for item in result.items) or (
        context.reason_fallback_count > 0
    )

    result_items = [
        _map_result_item(
            item,
            version_info=version_info,
            include_debug=include_debug,
            include_reason=include_reason,
        )
        for item in result.items
    ]

    meta = MetaResponse(
        traceId=trace.trace_id,
        requestId=trace.request_id,
        generatedAt=datetime.now(tz=UTC).isoformat(),
        resultCode="GRS-REC-001" if item_count == 0 else None,
    )

    data = RecoRecommendationRunResponseData(
        recommendationRunId=result.run_id,
        recommendationResultId=result_id,
        recommendationRequestId=result.request_id or context.recommendation_request.request_id,
        resultStatus=api_status,
        topK=top_k,
        resultItemCount=item_count,
        fallbackUsed=fallback_used,
        displayMessage=_ZERO_RESULT_MESSAGE if item_count == 0 else None,
        candidateCounts=_build_candidate_counts(context),
        warnings=_build_warnings(context, top_k) or None,
        metricSummary=_build_metric_summary(context),
        reasonData=_build_reason_data(
            result.items,
            include_reason=include_reason,
            include_debug=include_debug,
            version_info=version_info,
        ),
        resultItems=result_items,
        metadata=_build_metadata(context, include_debug=include_debug),
    )
    return RecoRecommendationRunSuccessResponse(data=data, meta=meta)
