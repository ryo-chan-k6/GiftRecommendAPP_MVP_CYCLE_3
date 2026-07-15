"""Request mapper: API DTO (camelCase) → domain RecommendationRequest."""

from __future__ import annotations

import re

from reco.api.errors import ErrorDetail, reco_error_from_code
from reco.api.schemas.recommendations import (
    ExecutionModeSchema,
    RecoRecommendationRunRequest,
)
from reco.domain.recommendation.inputs import (
    BudgetCondition,
    ExecutionCondition,
    ExecutionMode,
    NgCondition,
    NonPreferredCondition,
    OccasionCondition,
    PreferredCondition,
    RelationshipCondition,
)
from reco.domain.recommendation.request import RecommendationRequest

_UI_DEFAULT_TOP_K = 10
_UI_DEFAULT_CANDIDATE_LIMIT = 50
_SEMVER_PATTERN = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")


def validate_recommendation_request(body: RecoRecommendationRunRequest) -> None:
    """契約仕様書 §9 の防御的 Validation。"""
    details: list[ErrorDetail] = []

    if not body.recommendation_request_id.strip():
        details.append(
            ErrorDetail(
                field="recommendationRequestId",
                message="必須項目です。",
            ),
        )

    req = body.recommendation_request
    if not req.relationship.relationship_code.strip():
        details.append(
            ErrorDetail(
                field="recommendationRequest.relationship.relationshipCode",
                message="必須項目です。",
            ),
        )
    if not req.occasion.occasion_code.strip():
        details.append(
            ErrorDetail(
                field="recommendationRequest.occasion.occasionCode",
                message="必須項目です。",
            ),
        )

    execution = req.execution
    config_name = execution.config_name
    version_label = execution.version_label
    has_config_name = config_name is not None and config_name.strip() != ""
    has_version_label = version_label is not None and version_label.strip() != ""
    if has_config_name ^ has_version_label:
        details.append(
            ErrorDetail(
                field="recommendationRequest.execution.configName",
                message="configName と versionLabel はセットで指定してください。",
            ),
        )
    if has_version_label and not _SEMVER_PATTERN.match(version_label or ""):
        details.append(
            ErrorDetail(
                field="recommendationRequest.execution.versionLabel",
                message="semver 形式（vX.Y.Z）で指定してください。",
            ),
        )

    if req.budget is not None:
        budget_min = req.budget.budget_min
        budget_max = req.budget.budget_max
        if budget_min is not None and budget_max is not None and budget_min > budget_max:
            details.append(
                ErrorDetail(
                    field="recommendationRequest.budget",
                    message="budgetMin は budgetMax 以下である必要があります。",
                ),
            )

    top_k = execution.top_k if execution.top_k is not None else _UI_DEFAULT_TOP_K
    candidate_limit = (
        execution.candidate_limit
        if execution.candidate_limit is not None
        else _UI_DEFAULT_CANDIDATE_LIMIT
    )
    if candidate_limit < top_k:
        details.append(
            ErrorDetail(
                field="recommendationRequest.execution.candidateLimit",
                message="candidateLimit は topK 以上である必要があります。",
            ),
        )

    if details:
        raise reco_error_from_code(
            "GRS-REQ-001",
            message="推薦条件が不正です。",
            details=details,
        )


def _map_execution_mode(mode: ExecutionModeSchema) -> ExecutionMode:
    return ExecutionMode(mode.value)


def to_domain_recommendation_request(
    body: RecoRecommendationRunRequest,
) -> RecommendationRequest:
    validate_recommendation_request(body)
    req = body.recommendation_request
    execution = req.execution

    top_k = execution.top_k
    if top_k is None and execution.mode == ExecutionModeSchema.UI:
        top_k = _UI_DEFAULT_TOP_K
    candidate_limit = execution.candidate_limit
    if candidate_limit is None and execution.mode == ExecutionModeSchema.UI:
        candidate_limit = _UI_DEFAULT_CANDIDATE_LIMIT

    return RecommendationRequest(
        request_id=body.recommendation_request_id.strip(),
        relationship=RelationshipCondition(
            relationship_code=req.relationship.relationship_code.strip(),
            relationship_label=req.relationship.relationship_label,
        ),
        occasion=OccasionCondition(
            occasion_code=req.occasion.occasion_code.strip(),
            occasion_label=req.occasion.occasion_label,
        ),
        budget=(
            BudgetCondition(
                budget_min=req.budget.budget_min,
                budget_max=req.budget.budget_max,
                currency=req.budget.currency,
                tax_included=req.budget.tax_included,
            )
            if req.budget is not None
            else None
        ),
        preferred_condition=(
            PreferredCondition(preferred_text=req.preferred_condition.preferred_text)
            if req.preferred_condition is not None
            else None
        ),
        non_preferred_condition=(
            NonPreferredCondition(
                non_preferred_text=req.non_preferred_condition.non_preferred_text,
            )
            if req.non_preferred_condition is not None
            else None
        ),
        ng_condition=(
            NgCondition(
                ng_text=req.ng_condition.ng_text,
                ng_keywords=tuple(
                    keyword.strip()
                    for keyword in (req.ng_condition.ng_keywords or [])
                    if keyword.strip()
                ),
                ng_categories=tuple(
                    category.strip()
                    for category in (req.ng_condition.ng_categories or [])
                    if category.strip()
                ),
            )
            if req.ng_condition is not None
            else None
        ),
        free_text=req.free_text,
        execution=ExecutionCondition(
            mode=_map_execution_mode(execution.mode),
            top_k=top_k,
            candidate_limit=candidate_limit,
            include_reason=execution.include_reason,
            include_debug_info=execution.include_debug_info,
            eval_case_id=execution.eval_case_id,
            config_name=execution.config_name,
            version_label=execution.version_label,
            model_version_id=execution.model_version_id,
        ),
    )
