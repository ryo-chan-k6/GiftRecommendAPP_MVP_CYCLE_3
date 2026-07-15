"""MOD-RECO-012 pre_hard_filter unit tests (module spec §14.1)."""

from __future__ import annotations

import pytest

from conftest import (
    _sample_context,
    _sample_query_embedding,
    build_item_record,
)
from reco.application.candidate_retriever import (
    InMemoryItemRepository,
    PoolRepresentation,
    PreHardFilterError,
    SURFACE_ERROR_CODE_PRE_FILTER,
)
from reco.application.candidate_retriever.pre_hard_filter.filter import run_pre_hard_filter
from reco.domain.semantic_extraction.models import HardFilterCandidate


# §14 No.1 budget / ng / active
def test_pre_hard_filter_excludes_items_outside_budget_range() -> None:
    context = _sample_context(
        run_id="run-pre-budget",
        budget_min=4000,
        budget_max=9000,
        ng_keywords=(),
        hard_filter_candidates=(),
    )
    repo = InMemoryItemRepository(
        items=(
            build_item_record(item_id="below-budget", price=2000),
            build_item_record(item_id="in-budget", price=5000),
            build_item_record(item_id="above-budget", price=12000),
        ),
    )

    pool = run_pre_hard_filter(context, item_repository=repo)

    assert pool.total_after_filter == 1
    merged = pool.filter_predicate.merged_filter_conditions  # type: ignore[union-attr]
    assert merged.budget_min == 4000
    assert merged.budget_max == 9000


def test_pre_hard_filter_excludes_inactive_items() -> None:
    context = _sample_context(
        run_id="run-pre-active",
        ng_keywords=(),
        hard_filter_candidates=(),
    )
    repo = InMemoryItemRepository(
        items=(
            build_item_record(item_id="active-item", is_active=True, active_status="active"),
            build_item_record(
                item_id="inactive-flag",
                is_active=False,
                active_status="active",
            ),
            build_item_record(
                item_id="inactive-status",
                is_active=True,
                active_status="inactive",
            ),
        ),
    )

    pool = run_pre_hard_filter(context, item_repository=repo)

    assert pool.total_after_filter == 1
    assert pool.filter_predicate is not None
    assert pool.filter_predicate.active_only is True


def test_pre_hard_filter_excludes_items_matching_ng_keywords_and_categories() -> None:
    context = _sample_context(
        run_id="run-pre-ng",
        ng_keywords=("カジュアル",),
        ng_categories=("fashion",),
        hard_filter_candidates=(),
    )
    repo = InMemoryItemRepository(
        items=(
            build_item_record(item_id="allowed", keywords=("実用的",), categories=("gift",)),
            build_item_record(item_id="ng-keyword", keywords=("カジュアル",), categories=("gift",)),
            build_item_record(item_id="ng-category", keywords=("実用的",), categories=("fashion",)),
        ),
    )

    pool = run_pre_hard_filter(context, item_repository=repo)

    assert pool.total_after_filter == 1


# §14 No.2 merge
def test_pre_hard_filter_merges_request_ng_primary_and_dedupes_candidates() -> None:
    context = _sample_context(
        run_id="run-pre-merge",
        ng_keywords=("カジュアル",),
        ng_categories=("fashion",),
        hard_filter_candidates=(
            HardFilterCandidate(
                filter_type="ng_keyword",
                filter_value="カジュアル",
                evidence_text="重複",
                confidence=0.7,
                source_type="semantic",
            ),
            HardFilterCandidate(
                filter_type="ng_category",
                filter_value="fashion",
                evidence_text="重複",
                confidence=0.7,
                source_type="semantic",
            ),
            HardFilterCandidate(
                filter_type="ng_keyword",
                filter_value="スポーティ",
                evidence_text="追加",
                confidence=0.6,
                source_type="semantic",
            ),
        ),
    )
    repo = InMemoryItemRepository(items=(build_item_record(item_id="item-1"),))

    pool = run_pre_hard_filter(context, item_repository=repo)
    merged = pool.filter_predicate.merged_filter_conditions  # type: ignore[union-attr]

    assert merged.ng_keywords == ("カジュアル", "スポーティ")
    assert merged.ng_categories == ("fashion",)
    assert merged.hard_filter_values == ("カジュアル", "fashion", "スポーティ")


def test_pre_hard_filter_extracts_effective_keywords_from_alcohol_ng_text() -> None:
    context = _sample_context(
        run_id="run-pre-alcohol-ng-text",
        ng_keywords=(),
        ng_text="アルコールはNG",
        hard_filter_candidates=(),
    )
    repo = InMemoryItemRepository(
        items=(
            build_item_record(
                item_id="item_001",
                item_name="上品な焼き菓子ギフトセット",
                item_caption="焼き菓子の詰め合わせ",
                keywords=("焼き菓子",),
            ),
            build_item_record(
                item_id="item_003",
                item_name="プレミアムワインギフト",
                item_caption="ワインとグラスのギフトセット。アルコールを含む（NG 回避テスト用）。",
                keywords=("ワイン",),
            ),
        ),
    )

    pool = run_pre_hard_filter(context, item_repository=repo)
    merged = pool.filter_predicate.merged_filter_conditions  # type: ignore[union-attr]

    assert "アルコール" in merged.ng_keywords
    assert "アルコールはNG" not in merged.ng_keywords
    assert pool.total_after_filter == 1


def test_pre_hard_filter_maps_attribute_hard_filter_ng_text_to_keywords() -> None:
    context = _sample_context(
        run_id="run-pre-alcohol-attribute",
        ng_keywords=(),
        hard_filter_candidates=(
            HardFilterCandidate(
                filter_type="attribute",
                filter_value="アルコールはNG",
                evidence_text="アルコールはNG",
                confidence=0.9,
                source_type="ng_condition",
            ),
        ),
    )
    repo = InMemoryItemRepository(
        items=(
            build_item_record(
                item_id="sweets",
                item_caption="お茶請けに最適",
            ),
            build_item_record(
                item_id="wine",
                item_name="プレミアムワインギフト",
                item_caption="アルコールを含むセット",
            ),
        ),
    )

    pool = run_pre_hard_filter(context, item_repository=repo)
    merged = pool.filter_predicate.merged_filter_conditions  # type: ignore[union-attr]

    assert "アルコール" in merged.ng_keywords
    assert pool.total_after_filter == 1


# §14 No.3 0 件 Pre
def test_pre_hard_filter_zero_items_succeeds_without_grs_rec_008() -> None:
    context = _sample_context(
        run_id="run-pre-zero",
        ng_keywords=(),
        hard_filter_candidates=(),
    )
    repo = InMemoryItemRepository(items=())

    pool = run_pre_hard_filter(context, item_repository=repo)

    assert pool.total_after_filter == 0
    assert pool.representation == PoolRepresentation.PREDICATE


def test_pre_hard_filter_zero_items_does_not_raise_pre_filter_error() -> None:
    context = _sample_context(run_id="run-pre-zero-no-error", ng_keywords=("全除外",))
    repo = InMemoryItemRepository(items=())

    try:
        pool = run_pre_hard_filter(context, item_repository=repo)
    except PreHardFilterError as exc:
        pytest.fail(f"zero pre-filter must not raise GRS-REC-008: {exc}")

    assert pool.total_after_filter == 0


# §14 No.4 predicate 表現
def test_pre_hard_filter_returns_predicate_representation() -> None:
    context = _sample_context(run_id="run-pre-predicate")
    repo = InMemoryItemRepository(items=(build_item_record(item_id="item-1"),))

    pool = run_pre_hard_filter(context, item_repository=repo)

    assert pool.representation == PoolRepresentation.PREDICATE
    assert pool.filter_predicate is not None
    assert pool.filter_predicate.repository_query_ref is None


# §14 No.5 non_preferred 除外
def test_pre_hard_filter_ignores_non_preferred_condition() -> None:
    context = _sample_context(
        run_id="run-pre-non-preferred",
        ng_keywords=(),
        hard_filter_candidates=(),
        non_preferred_text="カジュアルすぎるものは避けたい",
    )
    repo = InMemoryItemRepository(
        items=(
            build_item_record(item_id="casual-item", keywords=("カジュアル",)),
            build_item_record(item_id="practical-item", keywords=("実用的",)),
        ),
    )

    pool = run_pre_hard_filter(context, item_repository=repo)

    assert pool.total_after_filter == 2


# §14 No.6 query_embedding 非依存
def test_pre_hard_filter_result_independent_of_query_embedding() -> None:
    context = _sample_context(
        run_id="run-pre-embedding-independent",
        ng_keywords=(),
        hard_filter_candidates=(),
    )
    repo = InMemoryItemRepository(
        items=(
            build_item_record(item_id="item-a"),
            build_item_record(item_id="item-b"),
        ),
    )

    pool_before = run_pre_hard_filter(context, item_repository=repo)
    context.query_embedding = _sample_query_embedding(  # type: ignore[attr-defined]
        model_version_id="different-model-version",
    )
    pool_after = run_pre_hard_filter(context, item_repository=repo)

    assert pool_before.total_after_filter == pool_after.total_after_filter == 2


def test_pre_hard_filter_raises_grs_rec_008_when_count_fails() -> None:
    class FailingCountRepository(InMemoryItemRepository):
        def count_filtered_items(self, predicate: object) -> int:
            raise RuntimeError("simulated count failure")

    context = _sample_context(run_id="run-pre-count-fail")

    with pytest.raises(PreHardFilterError) as exc_info:
        run_pre_hard_filter(context, item_repository=FailingCountRepository(items=()))

    assert exc_info.value.error_code == SURFACE_ERROR_CODE_PRE_FILTER
