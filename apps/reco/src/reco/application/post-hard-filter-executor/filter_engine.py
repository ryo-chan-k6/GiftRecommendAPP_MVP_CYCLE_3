"""Post Hard Filter pipeline steps for MOD-RECO-013."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from reco.application.candidate_retriever.models import (
    RetrievalCandidate,
    RetrievalCandidateItem,
)
from reco.domain.semantic_extraction.models import ExtractedSemanticConcept

from .constants import (
    AVOID_CONFIDENCE_THRESHOLD,
    INPUT_INTENT_AVOID,
    INPUT_INTENT_NG_CANDIDATE,
    ITEM_SEMANTIC_CONFIDENCE_THRESHOLD,
    NG_CONFIDENCE_THRESHOLD,
    REASON_DISPLAY_VALIDATION,
    REASON_DUPLICATE,
    REASON_INCONSISTENCY,
    REASON_SEMANTIC_NG,
    VALIDATION_STATUS_PASSED,
)
from .errors import PostHardFilterError
from .models import (
    AvoidObservationSummary,
    ExcludedCandidateEntry,
    ExcludedCandidateLog,
    ItemSemanticRecord,
    ItemValidationRecord,
    PostHardFilterResult,
    ValidatedRetrievalCandidate,
    ValidatedRetrievalCandidateItem,
)
from .ports import ItemRepositoryPort

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


def run_post_hard_filter(
    context: ExecutionContext,
    *,
    item_repository: ItemRepositoryPort,
) -> PostHardFilterResult:
    """Execute Post Hard Filter steps (§8.2)."""
    retrieval_candidate = _require_retrieval_candidate(context)
    semantic_result = _require_semantic_extraction_result(context)
    semantic_config_version_id = _require_semantic_config_version_id(context)

    if retrieval_candidate.total_retrieved == 0 or not retrieval_candidate.candidates:
        return _empty_result()

    item_ids = tuple(candidate.item_id for candidate in retrieval_candidate.candidates)
    try:
        items_by_id = item_repository.fetch_items_for_validation(item_ids)
        semantics_by_id = item_repository.fetch_item_semantics(item_ids)
    except PostHardFilterError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PostHardFilterError(
            f"item reference failed for run: {context.run_id}",
        ) from exc

    ng_concepts = _select_ng_concepts(semantic_result.concepts)
    avoid_concepts = _select_avoid_concepts(semantic_result.concepts)
    has_ng_concepts = len(ng_concepts) > 0

    excluded_entries: list[ExcludedCandidateEntry] = []
    avoid_overlapping_concepts: set[str] = set()
    avoid_observed_candidates = 0

    working: list[RetrievalCandidateItem] = list(retrieval_candidate.candidates)

    # Step 3: Semantic NG 除外
    after_ng: list[RetrievalCandidateItem] = []
    for candidate in working:
        if _is_semantic_ng_match(
            candidate.item_id,
            ng_concepts=ng_concepts,
            semantics_by_id=semantics_by_id,
            semantic_config_version_id=semantic_config_version_id,
        ):
            excluded_entries.append(
                ExcludedCandidateEntry(
                    item_id=candidate.item_id,
                    reason_code=REASON_SEMANTIC_NG,
                ),
            )
            continue
        after_ng.append(candidate)
    working = after_ng

    # Step 4: avoid 類似検知（観測のみ・除外しない）
    for candidate in working:
        overlap = _avoid_concept_overlap(
            candidate.item_id,
            avoid_concepts=avoid_concepts,
            semantics_by_id=semantics_by_id,
            semantic_config_version_id=semantic_config_version_id,
        )
        if overlap:
            avoid_observed_candidates += 1
            avoid_overlapping_concepts.update(overlap)

    # Step 5: 重複除外（先勝ち）
    seen_item_ids: set[str] = set()
    after_duplicate: list[RetrievalCandidateItem] = []
    for candidate in working:
        if candidate.item_id in seen_item_ids:
            excluded_entries.append(
                ExcludedCandidateEntry(
                    item_id=candidate.item_id,
                    reason_code=REASON_DUPLICATE,
                ),
            )
            continue
        seen_item_ids.add(candidate.item_id)
        after_duplicate.append(candidate)
    working = after_duplicate

    # Step 6: データ不整合除外
    after_inconsistency: list[RetrievalCandidateItem] = []
    for candidate in working:
        reason = _inconsistency_reason(
            candidate.item_id,
            items_by_id=items_by_id,
            semantics_by_id=semantics_by_id,
            has_ng_concepts=has_ng_concepts,
            semantic_config_version_id=semantic_config_version_id,
        )
        if reason is not None:
            excluded_entries.append(
                ExcludedCandidateEntry(
                    item_id=candidate.item_id,
                    reason_code=REASON_INCONSISTENCY,
                    reason_detail=reason,
                ),
            )
            continue
        after_inconsistency.append(candidate)
    working = after_inconsistency

    # Step 7: 表示前 Validation
    validated_items: list[ValidatedRetrievalCandidateItem] = []
    for candidate in working:
        item_record = items_by_id.get(candidate.item_id)
        reason = _display_validation_reason(item_record)
        if reason is not None:
            excluded_entries.append(
                ExcludedCandidateEntry(
                    item_id=candidate.item_id,
                    reason_code=REASON_DISPLAY_VALIDATION,
                    reason_detail=reason,
                ),
            )
            continue
        validated_items.append(
            ValidatedRetrievalCandidateItem(
                item_id=candidate.item_id,
                similarity_score=candidate.similarity_score,
                validation_status=VALIDATION_STATUS_PASSED,
            ),
        )

    total_excluded = len(excluded_entries)
    summary = dict(Counter(entry.reason_code for entry in excluded_entries))
    avoid_summary = (
        AvoidObservationSummary(
            overlapping_concept_count=len(avoid_overlapping_concepts),
            observed_candidate_count=avoid_observed_candidates,
        )
        if avoid_observed_candidates > 0
        else None
    )

    validated = ValidatedRetrievalCandidate(
        candidates=tuple(validated_items),
        total_validated=len(validated_items),
        total_excluded=total_excluded,
    )
    excluded_log = ExcludedCandidateLog(
        entries=tuple(excluded_entries),
        summary_by_reason=summary or None,
        avoid_observation_summary=avoid_summary,
    )

    return PostHardFilterResult(
        validated_retrieval_candidate=validated,
        excluded_candidate_log=excluded_log,
        post_filter_candidate_count=len(validated_items),
        post_hard_filter_latency_ms=0,
    )


def _empty_result() -> PostHardFilterResult:
    validated = ValidatedRetrievalCandidate(
        candidates=(),
        total_validated=0,
        total_excluded=0,
    )
    excluded_log = ExcludedCandidateLog(entries=())
    return PostHardFilterResult(
        validated_retrieval_candidate=validated,
        excluded_candidate_log=excluded_log,
        post_filter_candidate_count=0,
        post_hard_filter_latency_ms=0,
    )


def _require_retrieval_candidate(context: ExecutionContext) -> RetrievalCandidate:
    retrieval_candidate = getattr(context, "retrieval_candidate", None)
    if retrieval_candidate is None:
        raise PostHardFilterError("retrieval_candidate is required on execution_context")
    return retrieval_candidate


def _require_semantic_extraction_result(context: ExecutionContext):
    if context.semantic_extraction_result is None:
        raise PostHardFilterError(
            "semantic_extraction_result is required on execution_context",
        )
    return context.semantic_extraction_result


def _require_semantic_config_version_id(context: ExecutionContext) -> str:
    version_id = context.config_versions.get("semantic_config_version_id")
    if not version_id:
        raise PostHardFilterError(
            "semantic_config_version_id is required on execution_context.config_versions",
        )
    return version_id


def _select_ng_concepts(
    concepts: tuple[ExtractedSemanticConcept, ...],
) -> tuple[ExtractedSemanticConcept, ...]:
    return tuple(
        concept
        for concept in concepts
        if concept.input_intent == INPUT_INTENT_NG_CANDIDATE
        and concept.confidence >= NG_CONFIDENCE_THRESHOLD
    )


def _select_avoid_concepts(
    concepts: tuple[ExtractedSemanticConcept, ...],
) -> tuple[ExtractedSemanticConcept, ...]:
    return tuple(
        concept
        for concept in concepts
        if concept.input_intent == INPUT_INTENT_AVOID
        and concept.confidence >= AVOID_CONFIDENCE_THRESHOLD
    )


def _resolved_semantic_record(
    item_id: str,
    semantics_by_id: dict[str, ItemSemanticRecord],
    semantic_config_version_id: str,
) -> ItemSemanticRecord | None:
    record = semantics_by_id.get(item_id)
    if record is None:
        return None
    if record.semantic_config_version_id != semantic_config_version_id:
        return None
    return record


def _item_concept_codes(record: ItemSemanticRecord | None) -> set[str]:
    if record is None:
        return set()
    return {
        concept.concept_code
        for concept in record.concepts
        if concept.confidence >= ITEM_SEMANTIC_CONFIDENCE_THRESHOLD
    }


def _is_semantic_ng_match(
    item_id: str,
    *,
    ng_concepts: tuple[ExtractedSemanticConcept, ...],
    semantics_by_id: dict[str, ItemSemanticRecord],
    semantic_config_version_id: str,
) -> bool:
    if not ng_concepts:
        return False

    record = _resolved_semantic_record(
        item_id,
        semantics_by_id,
        semantic_config_version_id,
    )
    if record is None:
        return False

    item_codes = _item_concept_codes(record)
    ng_codes = {concept.concept_code for concept in ng_concepts}
    return bool(item_codes & ng_codes)


def _avoid_concept_overlap(
    item_id: str,
    *,
    avoid_concepts: tuple[ExtractedSemanticConcept, ...],
    semantics_by_id: dict[str, ItemSemanticRecord],
    semantic_config_version_id: str,
) -> set[str]:
    if not avoid_concepts:
        return set()

    record = _resolved_semantic_record(
        item_id,
        semantics_by_id,
        semantic_config_version_id,
    )
    item_codes = _item_concept_codes(record)
    if not item_codes:
        return set()

    avoid_codes = {concept.concept_code for concept in avoid_concepts}
    return item_codes & avoid_codes


def _inconsistency_reason(
    item_id: str,
    *,
    items_by_id: dict[str, ItemValidationRecord],
    semantics_by_id: dict[str, ItemSemanticRecord],
    has_ng_concepts: bool,
    semantic_config_version_id: str,
) -> str | None:
    if item_id not in items_by_id:
        return "item row missing"

    semantic_record = semantics_by_id.get(item_id)
    if semantic_record is None:
        if has_ng_concepts:
            return "item_semantic missing for ng_candidate"
        return None

    if semantic_record.semantic_config_version_id != semantic_config_version_id:
        return "semantic_config_version_id mismatch"

    return None


def _display_validation_reason(item_record: ItemValidationRecord | None) -> str | None:
    if item_record is None:
        return "item row missing"

    if not item_record.name or not item_record.name.strip():
        return "missing item name"

    if not item_record.has_image:
        return "missing item_image"

    if not item_record.is_active or item_record.active_status != "active":
        return "inactive item"

    if item_record.price is None:
        return "missing price"

    return None
