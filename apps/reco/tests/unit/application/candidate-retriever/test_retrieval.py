"""MOD-RECO-012 retrieval unit tests (module spec §14.2)."""

from __future__ import annotations

import pytest

from conftest import (
    _sample_context,
    _sample_query_embedding,
    build_item_record,
)
from reco.application.candidate_retriever import (
    InMemoryItemRepository,
    PreFilteredItemPool,
    PoolRepresentation,
    RetrievalError,
    SURFACE_ERROR_CODE_RETRIEVAL,
)
from reco.application.candidate_retriever.models import FilterPredicate, MergedFilterConditions
from reco.application.candidate_retriever.pre_hard_filter.filter import run_pre_hard_filter
from reco.application.candidate_retriever.retrieval.retrieval_engine import (
    resolve_candidate_limit,
    run_retrieval,
)
from reco.domain import ExecutionMode


def _predicate_pool(*, total_after_filter: int = 3) -> PreFilteredItemPool:
    predicate = FilterPredicate(
        merged_filter_conditions=MergedFilterConditions(),
        active_only=True,
        data_quality_rules={"require_image": True, "require_url": True},
    )
    return PreFilteredItemPool(
        representation=PoolRepresentation.PREDICATE,
        total_before_filter=total_after_filter,
        total_after_filter=total_after_filter,
        filter_predicate=predicate,
    )


# §14 No.7 Vector 正常系
def test_retrieval_returns_candidates_ordered_by_similarity() -> None:
    context = _sample_context(
        run_id="run-retrieval-order",
        ng_keywords=(),
        hard_filter_candidates=(),
        candidate_limit=10,
    )
    repo = InMemoryItemRepository(
        items=(
            build_item_record(
                item_id="low-similarity",
                embedding=(0.0, 1.0, 0.0, 0.0),
            ),
            build_item_record(
                item_id="high-similarity",
                embedding=(1.0, 0.0, 0.0, 0.0),
            ),
            build_item_record(
                item_id="mid-similarity",
                embedding=(0.7, 0.7, 0.0, 0.0),
            ),
        ),
    )
    pool = run_pre_hard_filter(context, item_repository=repo)

    result = run_retrieval(context, pool, item_repository=repo)

    item_ids = [candidate.item_id for candidate in result.candidates]
    scores = [candidate.similarity_score for candidate in result.candidates]
    assert item_ids == ["high-similarity", "mid-similarity", "low-similarity"]
    assert scores == sorted(scores, reverse=True)


# §14 No.8 candidate_limit
@pytest.mark.parametrize(
    ("execution_mode", "expected_limit"),
    [
        (ExecutionMode.UI, 50),
        (ExecutionMode.EVALUATION, 50),
        (ExecutionMode.BATCH, 100),
    ],
)
def test_resolve_candidate_limit_defaults_by_execution_mode(
    execution_mode: ExecutionMode,
    expected_limit: int,
) -> None:
    context = _sample_context(
        run_id=f"run-retrieval-limit-default-{execution_mode.value}",
        execution_mode=execution_mode,
        candidate_limit=None,
    )

    assert resolve_candidate_limit(context) == expected_limit


def test_resolve_candidate_limit_corrects_when_limit_less_than_top_k() -> None:
    context = _sample_context(
        run_id="run-retrieval-limit-top-k",
        candidate_limit=20,
        top_k=30,
    )

    assert resolve_candidate_limit(context) == 30


def test_retrieval_passes_candidate_limit_to_repository() -> None:
    context = _sample_context(
        run_id="run-retrieval-limit-pass",
        ng_keywords=(),
        hard_filter_candidates=(),
        candidate_limit=2,
    )
    repo = InMemoryItemRepository(
        items=tuple(
            build_item_record(
                item_id=f"item-{index}",
                embedding=(1.0, float(index) * 0.1, 0.0, 0.0),
            )
            for index in range(5)
        ),
    )
    pool = run_pre_hard_filter(context, item_repository=repo)

    result = run_retrieval(context, pool, item_repository=repo)

    assert len(repo.search_calls) == 1
    assert repo.search_calls[0]["limit"] == 2
    assert result.total_retrieved == 2


# §14 No.9 model_version
def test_retrieval_raises_when_query_embedding_model_version_mismatch() -> None:
    context = _sample_context(
        run_id="run-retrieval-model-mismatch",
        embedding_model_version_id="config-model-v1",
    )
    context.query_embedding = _sample_query_embedding(model_version_id="query-model-v2")  # type: ignore[attr-defined]
    repo = InMemoryItemRepository(items=(build_item_record(item_id="item-1"),))
    pool = _predicate_pool()

    with pytest.raises(RetrievalError) as exc_info:
        run_retrieval(context, pool, item_repository=repo)

    assert "model_version_id mismatch" in exc_info.value.message


def test_retrieval_skips_items_with_mismatched_embedding_model_version() -> None:
    context = _sample_context(
        run_id="run-retrieval-item-model-mismatch",
        ng_keywords=(),
        hard_filter_candidates=(),
    )
    repo = InMemoryItemRepository(
        items=(
            build_item_record(
                item_id="matching-model",
                embedding=(1.0, 0.0, 0.0, 0.0),
                model_version_id=context.config_versions["model_versions.embedding"],
            ),
            build_item_record(
                item_id="other-model",
                embedding=(1.0, 0.0, 0.0, 0.0),
                model_version_id="other-model-version",
            ),
        ),
    )
    pool = run_pre_hard_filter(context, item_repository=repo)

    result = run_retrieval(context, pool, item_repository=repo)

    assert result.total_retrieved == 1
    assert result.candidates[0].item_id == "matching-model"


# §14 No.10 DB 失敗
def test_retrieval_raises_grs_rec_009_when_vector_search_fails() -> None:
    context = _sample_context(run_id="run-retrieval-search-fail")
    repo = InMemoryItemRepository(items=(build_item_record(item_id="item-1"),))
    repo.should_fail_search = True
    pool = _predicate_pool()

    with pytest.raises(RetrievalError) as exc_info:
        run_retrieval(context, pool, item_repository=repo)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE_RETRIEVAL


def test_retrieval_skips_vector_search_when_pre_filter_returns_zero() -> None:
    context = _sample_context(run_id="run-retrieval-zero-pool")
    repo = InMemoryItemRepository(items=(build_item_record(item_id="item-1"),))
    pool = _predicate_pool(total_after_filter=0)

    result = run_retrieval(context, pool, item_repository=repo)

    assert result.total_retrieved == 0
    assert result.candidates == ()
    assert len(repo.search_calls) == 0
