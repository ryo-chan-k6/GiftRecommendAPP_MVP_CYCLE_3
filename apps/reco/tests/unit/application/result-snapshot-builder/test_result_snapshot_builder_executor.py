"""MOD-RECO-022 Result Snapshot Builder executor unit tests (module spec §14 unit)."""

from __future__ import annotations

import json

import pytest

from conftest import (
    DEFAULT_RESULT_ID,
    _sample_context,
    build_snapshot_builder,
)
from reco.application.result_snapshot_builder import (
    ITEM_INFO_ERROR_CODE,
    MODULE_ID,
    PHASE_NAME,
    RESULT_ITEM_SAVE_ERROR_CODE,
    SURFACE_ERROR_CODE,
    ResultSnapshotBuilderError,
)
from reco.application.result_snapshot_builder.in_memory_repository import (
    InMemoryRecommendationResultItemRepository,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

_EXPECTED_LOG_ATTRIBUTE_KEYS = frozenset(
    {
        "module_id",
        "snapshot_builder_item_count",
        "snapshot_builder_items_persisted",
        "snapshot_builder_latency_ms",
        "snapshot_null_image_count",
        "snapshot_null_review_count",
    },
)


# 0 件 empty: Matching short-circuit 後も GRS-REC-012 にならない
def test_execute_succeeds_with_zero_result_item_count() -> None:
    item_repository = InMemoryRecommendationResultItemRepository()
    context = _sample_context(items=())
    builder = build_snapshot_builder(item_repository=item_repository)

    result_context = builder.execute(context)

    assert MODULE_ID in result_context.completed_modules
    assert result_context.snapshot_builder_item_count == 0
    assert result_context.snapshot_build_success is True
    assert DEFAULT_RESULT_ID not in item_repository.rows_by_result_id


# §14 No.1 正常系（execute 経路）
def test_execute_persists_item_snapshots_and_attaches_context_outputs() -> None:
    item_repository = InMemoryRecommendationResultItemRepository()
    context = _sample_context()
    builder = build_snapshot_builder(item_repository=item_repository)

    result_context = builder.execute(context)

    assert MODULE_ID in result_context.completed_modules
    assert DEFAULT_RESULT_ID in item_repository.rows_by_result_id
    result = result_context.recommendation_result
    assert result is not None
    version_info = result.version_info or {}
    assert version_info["snapshot_builder_items_persisted"] == "true"
    assert version_info["snapshot_builder_item_count"] == "1"


# §14 No.9 Item 不存在（execute 経路）
def test_execute_raises_grs_itm_006_when_item_missing() -> None:
    from reco.application.result_snapshot_builder.in_memory_repository import (
        InMemoryItemSnapshotReadRepository,
    )

    context = _sample_context()
    builder = build_snapshot_builder(item_reader=InMemoryItemSnapshotReadRepository())

    with pytest.raises(ResultSnapshotBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == ITEM_INFO_ERROR_CODE


# §14 No.11 INSERT 失敗（execute 経路）
def test_execute_raises_grs_res_003_when_item_insert_fails() -> None:
    item_repository = InMemoryRecommendationResultItemRepository(
        should_fail_on_insert=True,
    )
    context = _sample_context()
    builder = build_snapshot_builder(item_repository=item_repository)

    with pytest.raises(ResultSnapshotBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == RESULT_ITEM_SAVE_ERROR_CODE


# §14 No.12 入力件数不整合（execute 経路）
def test_execute_raises_grs_rec_012_when_result_item_count_mismatches_items() -> None:
    context = _sample_context()
    assert context.recommendation_result is not None
    context.recommendation_result.version_info["result_item_count"] = "2"
    builder = build_snapshot_builder()

    with pytest.raises(ResultSnapshotBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.16 責務境界
def test_execute_persists_item_rows_only_without_header_insert_or_ranking_side_effects() -> (
    None
):
    item_repository = InMemoryRecommendationResultItemRepository()
    context = _sample_context()
    original_ranked = context.ranked_items
    builder = build_snapshot_builder(item_repository=item_repository)

    builder.execute(context)

    assert hasattr(item_repository, "insert_items")
    assert not hasattr(item_repository, "insert_header")
    assert not hasattr(item_repository, "build_reason")
    assert len(item_repository.rows_by_result_id) == 1
    assert context.ranked_items is original_ranked


# §14 No.17 Snapshot 不変（Repository 契約）
def test_execute_does_not_update_inserted_snapshot_rows_after_persist() -> None:
    item_repository = InMemoryRecommendationResultItemRepository()
    context = _sample_context()
    builder = build_snapshot_builder(item_repository=item_repository)

    builder.execute(context)

    rows_after_insert = item_repository.rows_by_result_id[DEFAULT_RESULT_ID]
    assert not hasattr(item_repository, "update_items")
    assert not hasattr(item_repository, "update_snapshot")

    # 二重 INSERT は拒否され、既存行は変更されない
    with pytest.raises(RuntimeError, match="duplicate recommendation_result_item insert"):
        item_repository.insert_items(rows_after_insert)

    assert item_repository.rows_by_result_id[DEFAULT_RESULT_ID] == rows_after_insert


# §14 No.19 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        run_id="run-mod-reco-022-log",
        trace_id="trace-mod-reco-022-unit",
    )
    logger = ScaffoldRecoLogger()
    builder = build_snapshot_builder(logger=logger)

    builder.execute(context)

    completion_logs = [record for record in logger.records if record.event == PHASE_NAME]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == "trace-mod-reco-022-unit"
    assert log_record.context.run_id == "run-mod-reco-022-log"
    assert log_record.attributes["snapshot_builder_item_count"] == 1
    assert log_record.attributes["module_id"] == MODULE_ID
    assert set(log_record.attributes) == _EXPECTED_LOG_ATTRIBUTE_KEYS
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
