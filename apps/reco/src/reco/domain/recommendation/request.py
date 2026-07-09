"""Recommendation Request aggregate root scaffold."""

from __future__ import annotations

from dataclasses import dataclass

from reco.domain.recommendation.inputs import (
    BudgetCondition,
    ExecutionCondition,
    NgCondition,
    NonPreferredCondition,
    OccasionCondition,
    PreferredCondition,
    RelationshipCondition,
)


def _has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _has_keywords(keywords: tuple[str, ...]) -> bool:
    return any(keyword.strip() for keyword in keywords)


@dataclass(frozen=True)
class RecommendationRequest:
    """Structured recommendation input (Phase4a placeholder).

    OpenAPI ``NormalizedRecommendationRequest`` および
    RecommendationRequest定義書 §4.1 に対応する型骨格。
    Phase4b 以降で validation・永続化 mapping を追加する。
    """

    request_id: str
    request_no: str | None = None
    idempotency_key: str | None = None
    relationship: RelationshipCondition | None = None
    occasion: OccasionCondition | None = None
    budget: BudgetCondition | None = None
    preferred_condition: PreferredCondition | None = None
    non_preferred_condition: NonPreferredCondition | None = None
    ng_condition: NgCondition | None = None
    free_text: str | None = None
    execution: ExecutionCondition | None = None

    def has_gift_context(self) -> bool:
        """贈答文脈（relationship / occasion）が指定されている。"""
        return self.relationship is not None or self.occasion is not None

    def has_search_condition(self) -> bool:
        """検索・絞り込み条件（予算 / 好み / NG / 自由文）が指定されている。"""
        if _has_text(self.free_text):
            return True

        if self.budget is not None and (
            self.budget.budget_min is not None or self.budget.budget_max is not None
        ):
            return True

        if self.preferred_condition is not None and (
            _has_text(self.preferred_condition.preferred_text)
            or _has_keywords(self.preferred_condition.preferred_keywords)
        ):
            return True

        if self.non_preferred_condition is not None and (
            _has_text(self.non_preferred_condition.non_preferred_text)
            or _has_keywords(self.non_preferred_condition.non_preferred_keywords)
        ):
            return True

        if self.ng_condition is not None and (
            _has_text(self.ng_condition.ng_text)
            or _has_keywords(self.ng_condition.ng_keywords)
            or _has_keywords(self.ng_condition.ng_categories)
        ):
            return True

        return False

    def has_minimum_input(self) -> bool:
        """RQ-01: 推薦要求は最低限、贈答文脈または検索条件を持つ。"""
        return self.has_gift_context() or self.has_search_condition()
