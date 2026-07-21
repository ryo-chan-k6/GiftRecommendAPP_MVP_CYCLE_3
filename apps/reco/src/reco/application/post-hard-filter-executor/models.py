"""Domain types for MOD-RECO-013 Post Hard Filter Executor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ItemSemanticConcept:
    """item_semantic.semantic_json.concepts[] の単一要素。"""

    concept_code: str
    confidence: float


@dataclass(frozen=True)
class ItemSemanticRecord:
    """item_semantic 行（§8.3.1 / §8.3.4）。"""

    item_id: str
    semantic_config_version_id: str
    concepts: tuple[ItemSemanticConcept, ...]


@dataclass(frozen=True)
class ItemValidationRecord:
    """表示前 Validation 用 item 行（§8.3.5）。"""

    item_id: str
    name: str | None
    price: int | None
    is_active: bool
    active_status: str
    has_image: bool


@dataclass(frozen=True)
class ValidatedRetrievalCandidateItem:
    """Post Filter 通過候補（§6.2.2）。"""

    item_id: str
    similarity_score: float
    validation_status: str = "passed"


@dataclass(frozen=True)
class ValidatedRetrievalCandidate:
    """Post Hard Filter 通過候補集合（§6.2.2）。"""

    candidates: tuple[ValidatedRetrievalCandidateItem, ...]
    total_validated: int
    total_excluded: int


@dataclass(frozen=True)
class ExcludedCandidateEntry:
    """除外レコード（§6.2.3）。"""

    item_id: str
    reason_code: str
    reason_detail: str | None = None


@dataclass(frozen=True)
class AvoidObservationSummary:
    """avoid concept 重複の観測サマリ（§6.2.3 / §8.3.2）。"""

    overlapping_concept_count: int
    observed_candidate_count: int


@dataclass(frozen=True)
class ExcludedCandidateLog:
    """除外ログ（§6.2.3）。"""

    entries: tuple[ExcludedCandidateEntry, ...]
    summary_by_reason: dict[str, int] | None = None
    avoid_observation_summary: AvoidObservationSummary | None = None


@dataclass(frozen=True)
class PostHardFilterResult:
    """MOD-RECO-013 モジュール全体の出力。"""

    validated_retrieval_candidate: ValidatedRetrievalCandidate
    excluded_candidate_log: ExcludedCandidateLog
    post_filter_candidate_count: int
    post_hard_filter_latency_ms: int
