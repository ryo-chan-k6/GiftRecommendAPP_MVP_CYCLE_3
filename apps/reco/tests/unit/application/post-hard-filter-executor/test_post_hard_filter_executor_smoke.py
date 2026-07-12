"""MOD-RECO-013 Post Hard Filter Executor smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import (
    _sample_context,
    build_executor_with_repository,
)
from reco.application.candidate_retriever.models import (
    RetrievalCandidate,
    RetrievalCandidateItem,
)
from reco.application.post_hard_filter_executor import (
    InMemoryItemRecord,
    InMemoryItemRepository,
    ItemSemanticConcept,
    PostHardFilterError,
    SURFACE_ERROR_CODE,
)
from reco.domain.semantic_extraction.models import ExtractedSemanticConcept


def test_execute_with_empty_retrieval_candidate_succeeds() -> None:
    context = _sample_context(
        retrieval_candidate=RetrievalCandidate(candidates=(), total_retrieved=0),
    )
    executor, _ = build_executor_with_repository(context)

    result_context = executor.execute(context)

    validated = result_context.validated_retrieval_candidate  # type: ignore[attr-defined]
    assert validated.total_validated == 0
    assert result_context.post_filter_candidate_count == 0  # type: ignore[attr-defined]
    assert "MOD-RECO-013" in result_context.completed_modules


def test_execute_excludes_semantic_ng_match() -> None:
    context = _sample_context(
        concepts=(
            ExtractedSemanticConcept(
                concept_code="casual",
                confidence=0.8,
                input_intent="ng_candidate",
                extraction_method="rule",
                source_type="semantic",
            ),
        ),
    )
    executor, _ = build_executor_with_repository(context)

    result_context = executor.execute(context)

    validated = result_context.validated_retrieval_candidate  # type: ignore[attr-defined]
    assert validated.total_validated == 1
    assert validated.candidates[0].item_id == "item-001"
    excluded = result_context.excluded_candidate_log  # type: ignore[attr-defined]
    assert excluded.summary_by_reason == {"semantic_ng": 1}


def test_execute_keeps_avoid_overlap_candidate() -> None:
    context = _sample_context(
        concepts=(
            ExtractedSemanticConcept(
                concept_code="casual",
                confidence=0.8,
                input_intent="avoid",
                extraction_method="rule",
                source_type="semantic",
            ),
        ),
    )
    executor, _ = build_executor_with_repository(context)

    result_context = executor.execute(context)

    validated = result_context.validated_retrieval_candidate  # type: ignore[attr-defined]
    assert validated.total_validated == 2
    excluded = result_context.excluded_candidate_log  # type: ignore[attr-defined]
    assert excluded.avoid_observation_summary is not None
    assert excluded.avoid_observation_summary.observed_candidate_count == 1


def test_execute_deduplicates_same_item_id() -> None:
    context = _sample_context(
        retrieval_candidate=RetrievalCandidate(
            candidates=(
                RetrievalCandidateItem(item_id="item-001", similarity_score=0.95),
                RetrievalCandidateItem(item_id="item-001", similarity_score=0.90),
            ),
            total_retrieved=2,
        ),
    )
    executor, _ = build_executor_with_repository(context)

    result_context = executor.execute(context)

    validated = result_context.validated_retrieval_candidate  # type: ignore[attr-defined]
    assert validated.total_validated == 1
    excluded = result_context.excluded_candidate_log  # type: ignore[attr-defined]
    assert excluded.summary_by_reason == {"duplicate": 1}


def test_execute_raises_on_repository_failure() -> None:
    context = _sample_context()
    repo = InMemoryItemRepository(
        items={
            "item-001": InMemoryItemRecord(
                item_id="item-001",
                name="実用的ギフト",
                price=5000,
                is_active=True,
                active_status="active",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="practical", confidence=0.9),
                ),
            ),
        },
        should_fail_fetch=True,
    )
    executor, _ = build_executor_with_repository(context, item_repository=repo)

    with pytest.raises(PostHardFilterError) as exc_info:
        executor.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
