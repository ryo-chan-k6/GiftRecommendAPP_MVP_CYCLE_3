"""MOD-RECO-021 Recommendation Result Builder executor unit tests (module spec §14 unit)."""

from __future__ import annotations

import json

import pytest

from conftest import (
    _sample_context,
    build_result_builder,
)
from reco.application.recommendation_result_builder import (
    MODULE_ID,
    PHASE_NAME,
    RecommendationResultBuilderError,
    SURFACE_ERROR_CODE,
)
from reco.application.recommendation_result_builder.in_memory_repository import (
    InMemoryRecommendationResultRepository,
)
from reco.domain.recommendation.result import ResultStatus
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

_EXPECTED_LOG_ATTRIBUTE_KEYS = frozenset(
    {
        "module_id",
        "result_builder_header_persisted",
        "result_builder_item_count",
        "result_builder_latency_ms",
        "result_status",
        "score_breakdown_partial_count",
        "zero_result_header_count",
    },
)


# §14 No.1 正常系（明細あり）: execute 経路でヘッダ INSERT と context 添付
def test_execute_persists_header_and_attaches_recommendation_result() -> None:
    repository = InMemoryRecommendationResultRepository()
    context = _sample_context(run_id="run-mod-reco-021-execute")
    builder = build_result_builder(repository=repository)

    result_context = builder.execute(context)

    assert len(repository.headers_by_run_id) == 1
    header = repository.headers_by_run_id["run-mod-reco-021-execute"]
    assert header.result_status.value == "generated"
    assert header.result_item_count == 1

    result = result_context.recommendation_result
    assert result is not None
    assert result.result_status == ResultStatus.COMPLETED
    assert result.item_count == 1
    assert MODULE_ID in result_context.completed_modules


# §14 No.7 境界値（0 件）: execute 経路でも GRS-REC-012 にならない
def test_execute_succeeds_with_empty_ranked_items_without_grs_rec_012() -> None:
    from reco.application.final_ranker.models import RankedItems

    context = _sample_context(
        ranked_items=RankedItems(
            entries=(),
            total_selected=0,
            top_k_used=10,
            mmr_candidate_pool_size=0,
            mmr_applied=False,
        ),
    )
    builder = build_result_builder()

    result_context = builder.execute(context)

    result = result_context.recommendation_result
    assert result is not None
    assert result.result_status == ResultStatus.EMPTY
    assert result.item_count == 0


# §14 No.9 ranked_items 欠損
def test_execute_raises_grs_rec_012_when_ranked_items_missing() -> None:
    context = _sample_context()
    context.ranked_items = None
    builder = build_result_builder()

    with pytest.raises(RecommendationResultBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.10 context_score JOIN 失敗
def test_execute_raises_grs_rec_012_when_context_score_join_fails() -> None:
    from reco.application.context_scorer.models import ContextScoreResult

    context = _sample_context(
        context_score_result=ContextScoreResult(
            entries=(),
            lambda_ctx_applied=0.5,
            total_scored=0,
        ),
    )
    builder = build_result_builder()

    with pytest.raises(RecommendationResultBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.11 ヘッダ INSERT 失敗
def test_execute_raises_grs_rec_012_when_header_insert_fails() -> None:
    repository = InMemoryRecommendationResultRepository(should_fail_on_insert=True)
    context = _sample_context()
    builder = build_result_builder(repository=repository)

    with pytest.raises(RecommendationResultBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_grs_rec_012_on_duplicate_header_insert() -> None:
    repository = InMemoryRecommendationResultRepository()
    context = _sample_context()
    builder = build_result_builder(repository=repository)

    builder.execute(context)

    with pytest.raises(RecommendationResultBuilderError) as exc_info:
        builder.execute(_sample_context())

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.14 責務境界
def test_execute_persists_header_only_without_item_detail_insert_or_snapshot_fetch() -> None:
    repository = InMemoryRecommendationResultRepository()
    context = _sample_context()
    builder = build_result_builder(repository=repository)

    builder.execute(context)

    assert hasattr(repository, "insert_header")
    assert not hasattr(repository, "insert_item")
    assert not hasattr(repository, "fetch_snapshot")
    assert len(repository.headers_by_run_id) == 1

    result = context.recommendation_result
    assert result is not None
    assert all(not hasattr(item, "reason_text") for item in result.items)


# §14 No.15 上流 result 不変
def test_execute_does_not_mutate_input_result_references() -> None:
    context = _sample_context()
    original_ranked = context.ranked_items
    original_context_score = context.context_score_result
    builder = build_result_builder()

    builder.execute(context)

    assert context.ranked_items is original_ranked
    assert context.context_score_result is original_context_score


# §14 No.17 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        run_id="run-mod-reco-021-log",
        trace_id="trace-mod-reco-021-unit",
    )
    logger = ScaffoldRecoLogger()
    builder = build_result_builder(logger=logger)

    builder.execute(context)

    completion_logs = [record for record in logger.records if record.event == PHASE_NAME]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == "trace-mod-reco-021-unit"
    assert log_record.context.run_id == "run-mod-reco-021-log"
    assert log_record.attributes["result_builder_item_count"] == 1
    assert log_record.attributes["module_id"] == MODULE_ID
    assert log_record.attributes["result_status"] == "generated"
    assert set(log_record.attributes) == _EXPECTED_LOG_ATTRIBUTE_KEYS
    assert "entries" not in log_record.attributes
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "item-001" not in serialized
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized


# §14 No.18 022 引き渡し: build_result 経路で item id が採番される
def test_build_result_returns_items_with_recommendation_result_item_ids() -> None:
    context = _sample_context()
    builder = build_result_builder()

    built, _metrics = builder.build_result(context)

    assert len(built.items) == 1
    assert built.items[0].recommendation_result_item_id
    assert built.items[0].recommendation_result_id == built.header.recommendation_result_id
