"""In-memory repository implementations for MOD-RECO-023."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from .constants import DEFAULT_TEMPLATE_NAME, DEFAULT_TEMPLATE_VERSION
from .models import (
    ItemSemanticRecord,
    ReasonTemplateRecord,
    RecommendationReasonInsertRow,
    SemanticEvidence,
)
from .ports import (
    ItemSemanticReadPort,
    ReasonTemplateReadPort,
    RecommendationReasonRepositoryPort,
)


@dataclass
class InMemoryReasonTemplateReadRepository(ReasonTemplateReadPort):
    """Scaffold reason_template 読取。"""

    templates: tuple[ReasonTemplateRecord, ...] = field(default_factory=tuple)

    def resolve_summary_template(
        self,
        *,
        relationship_code: str | None,
        occasion_code: str | None,
        feature_code: str | None,
    ) -> ReasonTemplateRecord | None:
        candidates = [
            template
            for template in self.templates
            if template.template_type == "summary" and template.template_body
        ]
        if not candidates:
            return None

        def score(template: ReasonTemplateRecord) -> tuple[int, int]:
            specificity = 0
            if template.relationship_code and template.relationship_code == relationship_code:
                specificity += 4
            elif template.relationship_code is None:
                specificity += 1
            else:
                specificity -= 4

            if template.occasion_code and template.occasion_code == occasion_code:
                specificity += 2
            elif template.occasion_code is None:
                specificity += 1
            else:
                specificity -= 2

            if template.feature_code and template.feature_code == feature_code:
                specificity += 1
            elif template.feature_code is None:
                specificity += 0
            else:
                specificity -= 1

            return (specificity, template.template_version)

        best = max(candidates, key=score)
        if score(best)[0] < 0:
            return None
        return best


@dataclass
class InMemoryItemSemanticReadRepository(ItemSemanticReadPort):
    """Scaffold item_semantic 読取。"""

    records_by_item_id: dict[str, ItemSemanticRecord] = field(default_factory=dict)

    def register(self, record: ItemSemanticRecord) -> None:
        self.records_by_item_id[record.item_id] = record

    def fetch_by_item_ids(
        self,
        item_ids: tuple[str, ...],
        *,
        semantic_config_version_id: str,
    ) -> dict[str, ItemSemanticRecord]:
        result: dict[str, ItemSemanticRecord] = {}
        for item_id in item_ids:
            record = self.records_by_item_id.get(item_id)
            if record is None:
                continue
            if record.semantic_config_version_id != semantic_config_version_id:
                continue
            result[item_id] = record
        return result


@dataclass
class InMemoryRecommendationReasonRepository(RecommendationReasonRepositoryPort):
    """Scaffold recommendation_reason INSERT。"""

    rows_by_result_item_id: dict[str, RecommendationReasonInsertRow] = field(
        default_factory=dict,
    )
    should_fail_on_insert: bool = False
    fail_once_for_item_ids: set[str] = field(default_factory=set)
    _failed_once: set[str] = field(default_factory=set, init=False, repr=False)

    def insert(self, row: RecommendationReasonInsertRow) -> RecommendationReasonInsertRow:
        if row.recommendation_result_item_id in self.rows_by_result_item_id:
            raise ValueError(
                "duplicate recommendation_reason for result item: "
                f"{row.recommendation_result_item_id}",
            )

        if self.should_fail_on_insert:
            raise RuntimeError("simulated recommendation_reason insert failure")

        item_id = row.recommendation_result_item_id
        if item_id in self.fail_once_for_item_ids and item_id not in self._failed_once:
            self._failed_once.add(item_id)
            raise RuntimeError("simulated one-time recommendation_reason insert failure")

        persisted = RecommendationReasonInsertRow(
            recommendation_reason_id=row.recommendation_reason_id or str(uuid4()),
            recommendation_result_item_id=row.recommendation_result_item_id,
            template_id=row.template_id,
            reason_summary=row.reason_summary,
            reason_detail=row.reason_detail,
            reason_points_json=row.reason_points_json,
            reason_badges_json=row.reason_badges_json,
            caution_note=row.caution_note,
            reason_basis_json=row.reason_basis_json,
        )
        self.rows_by_result_item_id[persisted.recommendation_result_item_id] = persisted
        return persisted


def build_default_in_memory_reason_template_repository() -> InMemoryReasonTemplateReadRepository:
    default_template_id = str(uuid4())
    return InMemoryReasonTemplateReadRepository(
        templates=(
            ReasonTemplateRecord(
                reason_template_id=default_template_id,
                template_name=DEFAULT_TEMPLATE_NAME,
                template_version=DEFAULT_TEMPLATE_VERSION,
                template_type="summary",
                template_body=(
                    "{relationship_label}への{occasion_label}として、"
                    "{primary_reason}がある候補です。"
                ),
            ),
        ),
    )


def build_default_in_memory_item_semantic_read_repository() -> InMemoryItemSemanticReadRepository:
    return InMemoryItemSemanticReadRepository()
