"""MOD-RECO-013 post_hard_filter unit tests (module spec §14 unit)."""

from __future__ import annotations

import pytest

from conftest import (
    _sample_context,
    build_executor_with_repository,
    build_item_record,
)
from reco.application.candidate_retriever.models import (
    RetrievalCandidate,
    RetrievalCandidateItem,
)
from reco.application.post_hard_filter_executor import (
    InMemoryItemRepository,
    ItemSemanticConcept,
    NG_CONFIDENCE_THRESHOLD,
    PostHardFilterError,
    REASON_DISPLAY_VALIDATION,
    REASON_INCONSISTENCY,
    REASON_SEMANTIC_NG,
    SURFACE_ERROR_CODE,
    run_post_hard_filter,
)
from reco.domain.semantic_extraction.models import (
    ExtractedSemanticConcept,
    HardFilterCandidate,
)


def _run_filter(context, *, repo: InMemoryItemRepository):
    return run_post_hard_filter(context, item_repository=repo)


# §14 No.1 Semantic NG
def test_post_hard_filter_excludes_item_with_ng_candidate_concept_match() -> None:
    context = _sample_context(
        run_id="run-post-ng-match",
        concepts=(
            ExtractedSemanticConcept(
                concept_code="casual",
                confidence=0.8,
                input_intent="ng_candidate",
                extraction_method="rule",
                source_type="semantic",
            ),
        ),
        retrieval_candidate=RetrievalCandidate(
            candidates=(
                RetrievalCandidateItem(item_id="allowed", similarity_score=0.9),
                RetrievalCandidateItem(item_id="ng-match", similarity_score=0.8),
            ),
            total_retrieved=2,
        ),
    )
    repo = InMemoryItemRepository(
        items={
            "allowed": build_item_record(
                item_id="allowed",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="practical", confidence=0.9),
                ),
            ),
            "ng-match": build_item_record(
                item_id="ng-match",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="casual", confidence=0.85),
                ),
            ),
        },
    )

    result = _run_filter(context, repo=repo)

    assert result.post_filter_candidate_count == 1
    assert result.validated_retrieval_candidate.candidates[0].item_id == "allowed"
    assert result.excluded_candidate_log.summary_by_reason == {REASON_SEMANTIC_NG: 1}


# §14 No.2 Semantic NG 閾値
def test_post_hard_filter_skips_ng_candidate_below_confidence_threshold() -> None:
    context = _sample_context(
        run_id="run-post-ng-threshold",
        concepts=(
            ExtractedSemanticConcept(
                concept_code="casual",
                confidence=NG_CONFIDENCE_THRESHOLD - 0.01,
                input_intent="ng_candidate",
                extraction_method="rule",
                source_type="semantic",
            ),
        ),
        retrieval_candidate=RetrievalCandidate(
            candidates=(RetrievalCandidateItem(item_id="casual-item", similarity_score=0.9),),
            total_retrieved=1,
        ),
    )
    repo = InMemoryItemRepository(
        items={
            "casual-item": build_item_record(
                item_id="casual-item",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="casual", confidence=0.85),
                ),
            ),
        },
    )

    result = _run_filter(context, repo=repo)

    assert result.post_filter_candidate_count == 1
    assert result.excluded_candidate_log.summary_by_reason is None


# §14 No.3 avoid 観測 / No.4 avoid 委譲
def test_post_hard_filter_observes_avoid_overlap_without_excluding() -> None:
    context = _sample_context(
        run_id="run-post-avoid",
        concepts=(
            ExtractedSemanticConcept(
                concept_code="casual",
                confidence=0.8,
                input_intent="avoid",
                extraction_method="rule",
                source_type="semantic",
            ),
        ),
        retrieval_candidate=RetrievalCandidate(
            candidates=(
                RetrievalCandidateItem(item_id="avoid-overlap", similarity_score=0.9),
                RetrievalCandidateItem(item_id="no-overlap", similarity_score=0.8),
            ),
            total_retrieved=2,
        ),
    )
    repo = InMemoryItemRepository(
        items={
            "avoid-overlap": build_item_record(
                item_id="avoid-overlap",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="casual", confidence=0.85),
                ),
            ),
            "no-overlap": build_item_record(
                item_id="no-overlap",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="practical", confidence=0.9),
                ),
            ),
        },
    )

    result = _run_filter(context, repo=repo)

    assert result.post_filter_candidate_count == 2
    validated_ids = {
        candidate.item_id for candidate in result.validated_retrieval_candidate.candidates
    }
    assert validated_ids == {"avoid-overlap", "no-overlap"}
    avoid_summary = result.excluded_candidate_log.avoid_observation_summary
    assert avoid_summary is not None
    assert avoid_summary.observed_candidate_count == 1
    assert avoid_summary.overlapping_concept_count == 1


# §14 No.6 データ不整合 — item_semantic 欠落
def test_post_hard_filter_excludes_item_when_semantic_missing_for_ng_candidate() -> None:
    context = _sample_context(
        run_id="run-post-inconsistency",
        concepts=(
            ExtractedSemanticConcept(
                concept_code="casual",
                confidence=0.8,
                input_intent="ng_candidate",
                extraction_method="rule",
                source_type="semantic",
            ),
        ),
        retrieval_candidate=RetrievalCandidate(
            candidates=(RetrievalCandidateItem(item_id="missing-semantic", similarity_score=0.9),),
            total_retrieved=1,
        ),
    )

    class SemanticMissingRepository(InMemoryItemRepository):
        def fetch_item_semantics(self, item_ids):  # type: ignore[no-untyped-def]
            return {}

    repo = SemanticMissingRepository(
        items={
            "missing-semantic": build_item_record(
                item_id="missing-semantic",
                semantic_concepts=(),
            ),
        },
    )

    result = _run_filter(context, repo=repo)

    assert result.post_filter_candidate_count == 0
    assert result.excluded_candidate_log.summary_by_reason == {REASON_INCONSISTENCY: 1}


# §14 No.6 DB 障害 — GRS-REC-010
def test_post_hard_filter_raises_grs_rec_010_on_repository_failure() -> None:
    context = _sample_context(run_id="run-post-db-failure")
    repo = InMemoryItemRepository(should_fail_fetch=True)

    with pytest.raises(PostHardFilterError) as exc_info:
        _run_filter(context, repo=repo)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.7 表示前 Validation
@pytest.mark.parametrize(
    ("field_overrides", "expected_reason_detail"),
    [
        ({"name": ""}, "missing item name"),
        ({"name": "   "}, "missing item name"),
        ({"has_image": False}, "missing item_image"),
        ({"is_active": False}, "inactive item"),
        ({"active_status": "inactive"}, "inactive item"),
        ({"price": None}, "missing price"),
    ],
)
def test_post_hard_filter_excludes_items_failing_display_validation(
    field_overrides: dict[str, object],
    expected_reason_detail: str,
) -> None:
    context = _sample_context(
        run_id="run-post-display-validation",
        concepts=(),
        hard_filter_candidates=(),
        retrieval_candidate=RetrievalCandidate(
            candidates=(RetrievalCandidateItem(item_id="invalid-item", similarity_score=0.9),),
            total_retrieved=1,
        ),
    )
    record = build_item_record(item_id="invalid-item")
    record_kwargs = {
        "item_id": record.item_id,
        "name": record.name,
        "price": record.price,
        "is_active": record.is_active,
        "active_status": record.active_status,
        "has_image": record.has_image,
        "semantic_concepts": record.semantic_concepts,
    }
    record_kwargs.update(field_overrides)
    repo = InMemoryItemRepository(items={"invalid-item": build_item_record(**record_kwargs)})

    result = _run_filter(context, repo=repo)

    assert result.post_filter_candidate_count == 0
    assert result.excluded_candidate_log.summary_by_reason == {REASON_DISPLAY_VALIDATION: 1}
    assert result.excluded_candidate_log.entries[0].reason_detail == expected_reason_detail


# §14 No.8 入力 0 件
def test_post_hard_filter_succeeds_with_empty_retrieval_candidate() -> None:
    context = _sample_context(
        run_id="run-post-empty-input",
        retrieval_candidate=RetrievalCandidate(candidates=(), total_retrieved=0),
    )
    repo = InMemoryItemRepository()

    result = _run_filter(context, repo=repo)

    assert result.post_filter_candidate_count == 0
    assert result.validated_retrieval_candidate.total_validated == 0


# §14 No.9 全除外
def test_post_hard_filter_succeeds_when_all_candidates_excluded() -> None:
    context = _sample_context(
        run_id="run-post-all-excluded",
        concepts=(
            ExtractedSemanticConcept(
                concept_code="casual",
                confidence=0.8,
                input_intent="ng_candidate",
                extraction_method="rule",
                source_type="semantic",
            ),
        ),
        retrieval_candidate=RetrievalCandidate(
            candidates=(
                RetrievalCandidateItem(item_id="item-a", similarity_score=0.9),
                RetrievalCandidateItem(item_id="item-b", similarity_score=0.8),
            ),
            total_retrieved=2,
        ),
    )
    repo = InMemoryItemRepository(
        items={
            "item-a": build_item_record(
                item_id="item-a",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="casual", confidence=0.85),
                ),
            ),
            "item-b": build_item_record(
                item_id="item-b",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="casual", confidence=0.85),
                ),
            ),
        },
    )

    result = _run_filter(context, repo=repo)

    assert result.post_filter_candidate_count == 0
    assert result.validated_retrieval_candidate.total_validated == 0
    assert result.excluded_candidate_log.summary_by_reason == {REASON_SEMANTIC_NG: 2}


# §14 No.10 Pre 境界 — 構造化 NG は再適用しない
def test_post_hard_filter_does_not_reapply_structured_ng_conditions() -> None:
    context = _sample_context(
        run_id="run-post-pre-boundary",
        concepts=(),
        hard_filter_candidates=(
            HardFilterCandidate(
                filter_type="ng_category",
                filter_value="fashion",
                evidence_text="構造化 NG",
                confidence=0.9,
                source_type="semantic",
            ),
        ),
        ng_keywords=("カジュアル",),
        ng_categories=("fashion",),
        retrieval_candidate=RetrievalCandidate(
            candidates=(
                RetrievalCandidateItem(item_id="keyword-match", similarity_score=0.9),
                RetrievalCandidateItem(item_id="category-match", similarity_score=0.8),
            ),
            total_retrieved=2,
        ),
    )
    repo = InMemoryItemRepository(
        items={
            "keyword-match": build_item_record(
                item_id="keyword-match",
                name="カジュアル雑貨",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="practical", confidence=0.9),
                ),
            ),
            "category-match": build_item_record(
                item_id="category-match",
                name="ファッション小物",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="fashion", confidence=0.9),
                ),
            ),
        },
    )

    result = _run_filter(context, repo=repo)

    assert result.post_filter_candidate_count == 2
    assert REASON_SEMANTIC_NG not in (result.excluded_candidate_log.summary_by_reason or {})


def test_execute_all_excluded_sets_post_filter_candidate_count_to_zero() -> None:
    context = _sample_context(
        run_id="run-post-executor-all-excluded",
        concepts=(
            ExtractedSemanticConcept(
                concept_code="casual",
                confidence=0.8,
                input_intent="ng_candidate",
                extraction_method="rule",
                source_type="semantic",
            ),
        ),
        retrieval_candidate=RetrievalCandidate(
            candidates=(
                RetrievalCandidateItem(item_id="item-a", similarity_score=0.9),
                RetrievalCandidateItem(item_id="item-b", similarity_score=0.8),
            ),
            total_retrieved=2,
        ),
    )
    repo = InMemoryItemRepository(
        items={
            "item-a": build_item_record(
                item_id="item-a",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="casual", confidence=0.85),
                ),
            ),
            "item-b": build_item_record(
                item_id="item-b",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="casual", confidence=0.85),
                ),
            ),
        },
    )
    executor, _ = build_executor_with_repository(context, item_repository=repo)

    result_context = executor.execute(context)

    assert result_context.post_filter_candidate_count == 0  # type: ignore[attr-defined]
    assert "MOD-RECO-013" in result_context.completed_modules
