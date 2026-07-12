"""Domain types for MOD-RECO-012 Candidate Retriever."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PoolRepresentation(StrEnum):
    """Logical representation of pre_filtered_item_pool (§6.2.1)."""

    PREDICATE = "predicate"
    SESSION_TABLE = "session_table"
    MATERIALIZED_IDS = "materialized_ids"


@dataclass(frozen=True)
class MergedFilterConditions:
    """Merge 済み NG / budget 等（§6.2.2 merged_filter_conditions）。"""

    budget_min: int | None = None
    budget_max: int | None = None
    ng_keywords: tuple[str, ...] = ()
    ng_categories: tuple[str, ...] = ()
    hard_filter_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class FilterPredicate:
    """DB predicate push-down 用 Filter 述語（§6.2.2）。"""

    merged_filter_conditions: MergedFilterConditions
    active_only: bool = True
    data_quality_rules: dict[str, bool] = field(default_factory=dict)
    repository_query_ref: str | None = None


@dataclass(frozen=True)
class PreFilteredItemPool:
    """Pre Hard Filter 結果の論理 pool（§6.2.1）。"""

    representation: PoolRepresentation
    total_before_filter: int
    total_after_filter: int
    filter_predicate: FilterPredicate | None = None
    filter_summary: dict[str, int] | None = None
    applied_conditions: dict[str, Any] | None = None
    materialized_item_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalCandidateItem:
    """単一 Retrieval 候補（§6.2.3）。"""

    item_id: str
    similarity_score: float
    retrieval_method: str = "vector"


@dataclass(frozen=True)
class RetrievalCandidate:
    """Vector Retrieval 結果（§6.2.3）。"""

    candidates: tuple[RetrievalCandidateItem, ...]
    total_retrieved: int


@dataclass(frozen=True)
class CandidateRetrieverResult:
    """MOD-RECO-012 モジュール全体の出力。"""

    pre_filtered_item_pool: PreFilteredItemPool
    retrieval_candidate: RetrievalCandidate
    pre_filter_candidate_count: int
    pre_hard_filter_latency_ms: int
    retrieval_latency_ms: int
    retrieval_candidate_count: int
