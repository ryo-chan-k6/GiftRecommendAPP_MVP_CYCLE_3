"""MOD-RECO-012 Candidate Retriever smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import (
    PoolRepresentation,
    _sample_context,
    build_retriever_with_repository,
)
from reco.application.candidate_retriever import (
    InMemoryItemRecord,
    InMemoryItemRepository,
    PreHardFilterError,
    RetrievalError,
    SURFACE_ERROR_CODE_PRE_FILTER,
    SURFACE_ERROR_CODE_RETRIEVAL,
)


def test_execute_sets_pre_filtered_pool_and_retrieval_candidate() -> None:
    context = _sample_context(run_id="run-smoke-success")
    retriever, repo = build_retriever_with_repository(context)

    result_context = retriever.execute(context)

    pool = result_context.pre_filtered_item_pool  # type: ignore[attr-defined]
    candidate = result_context.retrieval_candidate  # type: ignore[attr-defined]

    assert pool.representation == PoolRepresentation.PREDICATE
    assert pool.total_after_filter == 1
    assert result_context.pre_filter_candidate_count == 1  # type: ignore[attr-defined]
    assert candidate.total_retrieved == 1
    assert len(candidate.candidates) == 1
    assert candidate.candidates[0].item_id == "item-001"
    assert "MOD-RECO-012" in result_context.completed_modules
    assert len(repo.search_calls) == 1


def test_execute_skips_vector_search_when_pre_filter_returns_zero() -> None:
    context = _sample_context(run_id="run-smoke-zero-pre")
    empty_repo = InMemoryItemRepository(items=())
    retriever, repo = build_retriever_with_repository(context, item_repository=empty_repo)

    result_context = retriever.execute(context)

    candidate = result_context.retrieval_candidate  # type: ignore[attr-defined]
    assert candidate.total_retrieved == 0
    assert candidate.candidates == ()
    assert len(repo.search_calls) == 0


def test_execute_excludes_ng_keyword_and_category_via_pre_filter() -> None:
    context = _sample_context(run_id="run-smoke-ng")
    repo_items = (
        InMemoryItemRecord(
            item_id="item-allowed",
            price=5000,
            is_active=True,
            active_status="active",
            keywords=("実用的",),
            categories=("gift",),
            embedding=(1.0, 0.0, 0.0, 0.0),
            model_version_id=context.config_versions["model_versions.embedding"],
        ),
        InMemoryItemRecord(
            item_id="item-ng-keyword",
            price=5000,
            is_active=True,
            active_status="active",
            keywords=("カジュアル",),
            categories=("gift",),
            embedding=(0.5, 0.0, 0.0, 0.0),
            model_version_id=context.config_versions["model_versions.embedding"],
        ),
        InMemoryItemRecord(
            item_id="item-ng-category",
            price=5000,
            is_active=True,
            active_status="active",
            keywords=("実用的",),
            categories=("fashion",),
            embedding=(0.3, 0.0, 0.0, 0.0),
            model_version_id=context.config_versions["model_versions.embedding"],
        ),
    )
    retriever, _ = build_retriever_with_repository(
        context,
        item_repository=InMemoryItemRepository(items=repo_items),
    )

    result_context = retriever.execute(context)

    pool = result_context.pre_filtered_item_pool  # type: ignore[attr-defined]
    assert pool.total_after_filter == 1
    candidate = result_context.retrieval_candidate  # type: ignore[attr-defined]
    assert candidate.total_retrieved == 1
    assert candidate.candidates[0].item_id == "item-allowed"


def test_execute_raises_pre_filter_error_when_semantic_extraction_missing() -> None:
    context = _sample_context(run_id="run-smoke-no-semantic")
    retriever, _ = build_retriever_with_repository(context)
    context.semantic_extraction_result = None

    with pytest.raises(PreHardFilterError) as exc_info:
        retriever.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE_PRE_FILTER
    assert "semantic_extraction_result" in exc_info.value.message


def test_execute_raises_retrieval_error_when_vector_search_fails() -> None:
    context = _sample_context(run_id="run-smoke-search-fail")
    retriever, repo = build_retriever_with_repository(context)
    repo.should_fail_search = True

    with pytest.raises(RetrievalError) as exc_info:
        retriever.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE_RETRIEVAL
