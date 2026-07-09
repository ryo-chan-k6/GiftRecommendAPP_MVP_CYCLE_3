"""Repository ports for MOD-RECO-023 Reason Generator."""

from __future__ import annotations

from typing import Protocol

from .models import ItemSemanticRecord, ReasonTemplateRecord, RecommendationReasonInsertRow


class ReasonTemplateReadPort(Protocol):
    """reason_template 読取 Port。"""

    def resolve_summary_template(
        self,
        *,
        relationship_code: str | None,
        occasion_code: str | None,
        feature_code: str | None,
    ) -> ReasonTemplateRecord | None: ...


class ItemSemanticReadPort(Protocol):
    """item_semantic 読取 Port（Batch 正本）。"""

    def fetch_by_item_ids(
        self,
        item_ids: tuple[str, ...],
        *,
        semantic_config_version_id: str,
    ) -> dict[str, ItemSemanticRecord]: ...


class RecommendationReasonRepositoryPort(Protocol):
    """recommendation_reason INSERT Port。"""

    def insert(self, row: RecommendationReasonInsertRow) -> RecommendationReasonInsertRow: ...
