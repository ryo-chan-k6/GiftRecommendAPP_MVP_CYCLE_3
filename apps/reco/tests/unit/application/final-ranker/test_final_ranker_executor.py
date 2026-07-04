"""MOD-RECO-020 Final Ranker executor unit tests (module spec §14 unit)."""

from __future__ import annotations

import json

import pytest

from conftest import (
    _feature_match_entry,
    _final_score_entry,
    _sample_context,
    _sample_feature_match_result,
    _sample_final_score_result,
    build_ranker,
)
from reco.application.final_ranker import (
    MODULE_ID,
    PHASE_NAME,
    FinalRankerError,
    SURFACE_ERROR_CODE,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

_EXPECTED_LOG_ATTRIBUTE_KEYS = frozenset(
    {
        "final_ranker_feature_match_missing_count",
        "final_ranker_latency_ms",
        "final_ranker_mmr_applied",
        "final_ranker_selected_count",
        "mmr_applied",
        "mmr_rank_shift_count",
        "module_id",
        "top_k_clipped",
        "top_k_used",
    },
)


# §14 No.12 final_score_result 欠損
def test_execute_raises_grs_rec_012_when_final_score_result_missing() -> None:
    context = _sample_context()
    del context.final_score_result  # type: ignore[attr-defined]
    ranker = build_ranker()

    with pytest.raises(FinalRankerError) as exc_info:
        ranker.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.13 feature_match_result 欠損
def test_execute_raises_grs_rec_012_when_feature_match_result_missing() -> None:
    context = _sample_context()
    context.feature_match_result = None
    ranker = build_ranker()

    with pytest.raises(FinalRankerError) as exc_info:
        ranker.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.14 未対応 diversity_method
def test_execute_raises_grs_rec_012_for_unsupported_diversity_method() -> None:
    config_versions = {
        "ranking_config_id": "rc-1",
        "diversity_method": "cluster",
    }
    context = _sample_context(config_versions=config_versions)
    ranker = build_ranker()

    with pytest.raises(FinalRankerError) as exc_info:
        ranker.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_attaches_ranked_items_and_metrics_to_execution_context() -> None:
    context = _sample_context(run_id="run-final-ranker-handoff")
    ranker = build_ranker()

    result_context = ranker.execute(context)

    ranked_items = result_context.ranked_items
    assert ranked_items is not None
    assert ranked_items.total_selected == 1
    assert result_context.final_ranker_selected_count == 1
    assert result_context.final_ranker_latency_ms is not None
    assert result_context.final_ranker_mmr_applied is not None
    assert result_context.mmr_rank_shift_count is not None
    assert MODULE_ID in result_context.completed_modules


# §14 No.17 責務境界
def test_execute_does_not_mutate_final_score_result_entries() -> None:
    original_entry = _final_score_entry(item_id="item-001")
    original_diversity_penalty = original_entry.diversity_penalty
    original_breakdown = original_entry.score_breakdown
    context = _sample_context(
        final_score_result=_sample_final_score_result(entries=(original_entry,)),
        feature_match_result=_sample_feature_match_result(
            entries=(_feature_match_entry(item_id="item-001"),),
        ),
    )
    ranker = build_ranker()

    ranker.execute(context)

    stored_entry = context.final_score_result.entries[0]  # type: ignore[attr-defined]
    assert stored_entry.diversity_penalty == original_diversity_penalty
    assert stored_entry.score_breakdown == original_breakdown


# §14 No.18 上流 result 不変
def test_execute_does_not_mutate_input_result_references() -> None:
    context = _sample_context()
    original_final_score = context.final_score_result  # type: ignore[attr-defined]
    original_feature_match = context.feature_match_result
    ranker = build_ranker()

    ranker.execute(context)

    assert context.final_score_result is original_final_score  # type: ignore[attr-defined]
    assert context.feature_match_result is original_feature_match


# §14 No.20 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        run_id="run-final-ranker-log",
        trace_id="trace-mod-reco-020-unit",
    )
    logger = ScaffoldRecoLogger()
    ranker = build_ranker(logger=logger)

    ranker.execute(context)

    completion_logs = [record for record in logger.records if record.event == PHASE_NAME]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == "trace-mod-reco-020-unit"
    assert log_record.context.run_id == "run-final-ranker-log"
    assert log_record.attributes["final_ranker_selected_count"] == 1
    assert log_record.attributes["module_id"] == MODULE_ID
    assert set(log_record.attributes) == _EXPECTED_LOG_ATTRIBUTE_KEYS
    assert "entries" not in log_record.attributes
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "item-001" not in serialized
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
