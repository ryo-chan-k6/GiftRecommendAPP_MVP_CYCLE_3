"""Pydantic schemas for API-INT-002 (契約仕様書 / OpenAPI 準拠)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExecutionModeSchema(StrEnum):
    UI = "ui"
    EVALUATION = "evaluation"
    BATCH = "batch"


class RelationshipInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationship_code: str = Field(alias="relationshipCode")
    relationship_label: str | None = Field(default=None, alias="relationshipLabel")


class OccasionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occasion_code: str = Field(alias="occasionCode")
    occasion_label: str | None = Field(default=None, alias="occasionLabel")


class BudgetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    budget_min: int | None = Field(default=None, alias="budgetMin", ge=0)
    budget_max: int | None = Field(default=None, alias="budgetMax", ge=0)
    currency: str | None = None
    tax_included: bool | None = Field(default=None, alias="taxIncluded")


class PreferredConditionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_text: str | None = Field(default=None, alias="preferredText", max_length=500)


class NonPreferredConditionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    non_preferred_text: str | None = Field(
        default=None,
        alias="nonPreferredText",
        max_length=500,
    )


class NgConditionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ng_text: str | None = Field(default=None, alias="ngText", max_length=300)
    ng_keywords: list[str] | None = Field(default=None, alias="ngKeywords")
    ng_categories: list[str] | None = Field(default=None, alias="ngCategories")


class ExecutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ExecutionModeSchema
    top_k: int | None = Field(default=None, alias="topK", ge=1, le=50)
    candidate_limit: int | None = Field(default=None, alias="candidateLimit", ge=1)
    include_reason: bool | None = Field(default=None, alias="includeReason")
    include_debug_info: bool | None = Field(default=None, alias="includeDebugInfo")
    eval_case_id: str | None = Field(default=None, alias="evalCaseId")
    config_name: str | None = Field(default=None, alias="configName")
    version_label: str | None = Field(default=None, alias="versionLabel")
    model_version_id: str | None = Field(default=None, alias="modelVersionId")


class NormalizedRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationship: RelationshipInput
    occasion: OccasionInput
    budget: BudgetInput | None = None
    preferred_condition: PreferredConditionInput | None = Field(
        default=None,
        alias="preferredCondition",
    )
    non_preferred_condition: NonPreferredConditionInput | None = Field(
        default=None,
        alias="nonPreferredCondition",
    )
    ng_condition: NgConditionInput | None = Field(default=None, alias="ngCondition")
    free_text: str | None = Field(default=None, alias="freeText", max_length=800)
    execution: ExecutionInput


class RecoRecommendationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_request_id: str = Field(alias="recommendationRequestId")
    recommendation_request: NormalizedRecommendationRequest = Field(
        alias="recommendationRequest",
    )


class MetaResponse(BaseModel):
    trace_id: str = Field(alias="traceId")
    request_id: str = Field(alias="requestId")
    generated_at: str | None = Field(default=None, alias="generatedAt")
    result_code: str | None = Field(default=None, alias="resultCode")


class ErrorDetailResponse(BaseModel):
    field: str
    message: str


class ErrorBodyResponse(BaseModel):
    code: str
    message: str
    details: list[ErrorDetailResponse] | None = None


class ErrorResponseEnvelope(BaseModel):
    error: ErrorBodyResponse
    meta: MetaResponse


class WarningItemResponse(BaseModel):
    code: str
    severity: str | None = None
    message: str | None = None


class CandidateCountsResponse(BaseModel):
    retrieval_count: int | None = Field(default=None, alias="retrievalCount")
    matching_count: int | None = Field(default=None, alias="matchingCount")
    ranking_count: int | None = Field(default=None, alias="rankingCount")


class FeatureDistributionStatResponse(BaseModel):
    mean: float | None = None
    p95: float | None = None


class MetricSummaryResponse(BaseModel):
    recommendation_latency_ms: int | None = Field(
        default=None,
        alias="recommendationLatencyMs",
    )
    phase_duration_ms: dict[str, int] | None = Field(
        default=None,
        alias="phaseDurationMs",
    )
    feature_distribution: dict[str, FeatureDistributionStatResponse] | None = Field(
        default=None,
        alias="featureDistribution",
    )


class ReasonBadgeResponse(BaseModel):
    label: str | None = None
    code: str | None = None


class InternalRecommendationResultItemResponse(BaseModel):
    recommendation_result_item_id: str = Field(alias="recommendationResultItemId")
    item_id: str = Field(alias="itemId")
    rank: int
    item_name: str = Field(alias="itemName")
    item_price: int = Field(alias="itemPrice")
    item_url: str = Field(alias="itemUrl")
    item_image_url: str | None = Field(default=None, alias="itemImageUrl")
    item_catchcopy: str | None = Field(default=None, alias="itemCatchcopy")
    shop_name: str | None = Field(default=None, alias="shopName")
    context_score: float = Field(alias="contextScore")
    social_match: float | None = Field(default=None, alias="socialMatch")
    symbolic_match: float | None = Field(default=None, alias="symbolicMatch")
    popularity_score: float | None = Field(default=None, alias="popularityScore")
    risk_penalty: float | None = Field(default=None, alias="riskPenalty")
    final_score: float = Field(alias="finalScore")
    score_breakdown: dict[str, Any] | None = Field(default=None, alias="scoreBreakdown")
    reason_summary: str | None = Field(default=None, alias="reasonSummary")
    reason_points: list[str] | None = Field(default=None, alias="reasonPoints")
    reason_detail: str | None = Field(default=None, alias="reasonDetail")
    recommendation_reason_id: str | None = Field(
        default=None,
        alias="recommendationReasonId",
    )
    reason_status: str | None = Field(default=None, alias="reasonStatus")
    reason_badges: list[ReasonBadgeResponse] | None = Field(
        default=None,
        alias="reasonBadges",
    )
    caution_note: str | None = Field(default=None, alias="cautionNote")
    is_fallback: bool | None = Field(default=None, alias="isFallback")


class ReasonDataItemResponse(BaseModel):
    recommendation_result_item_id: str = Field(alias="recommendationResultItemId")
    item_id: str = Field(alias="itemId")
    reason_status: str = Field(alias="reasonStatus")
    reason_summary: str | None = Field(default=None, alias="reasonSummary")
    is_fallback: bool | None = Field(default=None, alias="isFallback")
    reason_detail: str | None = Field(default=None, alias="reasonDetail")
    reason_points: list[str] | None = Field(default=None, alias="reasonPoints")


class ReasonDataResponse(BaseModel):
    items: list[ReasonDataItemResponse]


class RecoRunMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    mode: str | None = None
    debug_payload: dict[str, Any] | None = Field(default=None, alias="debugPayload")


class RecoRecommendationRunResponseData(BaseModel):
    recommendation_run_id: str = Field(alias="recommendationRunId")
    recommendation_result_id: str = Field(alias="recommendationResultId")
    recommendation_request_id: str = Field(alias="recommendationRequestId")
    result_status: str = Field(alias="resultStatus")
    top_k: int = Field(alias="topK")
    result_item_count: int = Field(alias="resultItemCount")
    fallback_used: bool = Field(alias="fallbackUsed")
    display_message: str | None = Field(default=None, alias="displayMessage")
    candidate_counts: CandidateCountsResponse | None = Field(
        default=None,
        alias="candidateCounts",
    )
    warnings: list[WarningItemResponse] | None = None
    metric_summary: MetricSummaryResponse | None = Field(
        default=None,
        alias="metricSummary",
    )
    reason_data: ReasonDataResponse | None = Field(default=None, alias="reasonData")
    result_items: list[InternalRecommendationResultItemResponse] = Field(
        alias="resultItems",
    )
    metadata: RecoRunMetadataResponse | None = None


class RecoRecommendationRunSuccessResponse(BaseModel):
    data: RecoRecommendationRunResponseData
    meta: MetaResponse
