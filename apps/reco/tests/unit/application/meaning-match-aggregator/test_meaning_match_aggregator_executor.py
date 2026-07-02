"""MOD-RECO-015 Meaning Match Aggregator executor unit tests (module spec §14 unit)."""

from __future__ import annotations

import json

import pytest

from conftest import (
    _sample_context,
    build_aggregator,
)
from reco.application.meaning_match_aggregator import (
    MODULE_ID,
    PHASE_NAME,
    MeaningMatchAggregatorError,
    SURFACE_ERROR_CODE,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


# §14 No.16 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        run_id="run-meaning-match-aggregator-log",
        trace_id="trace-mod-reco-015-unit",
    )
    logger = ScaffoldRecoLogger()
    aggregator = build_aggregator(logger=logger)

    aggregator.execute(context)

    completion_logs = [record for record in logger.records if record.event == PHASE_NAME]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == "trace-mod-reco-015-unit"
    assert log_record.context.run_id == "run-meaning-match-aggregator-log"
    assert log_record.attributes["meaning_match_aggregator_candidate_count"] == 2
    assert log_record.attributes["module_id"] == MODULE_ID
    assert log_record.attributes["total_aggregated"] == 2
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized


def test_execute_attaches_meaning_match_result_and_metrics_to_execution_context() -> None:
    context = _sample_context(run_id="run-meaning-match-aggregator-handoff")
    aggregator = build_aggregator()

    result_context = aggregator.execute(context)

    result = result_context.meaning_match_result  # type: ignore[attr-defined]
    assert result.total_aggregated == 2
    assert result_context.meaning_match_aggregator_candidate_count == 2  # type: ignore[attr-defined]
    assert result_context.meaning_match_aggregator_latency_ms is not None  # type: ignore[attr-defined]
    assert result_context.meaning_match_value_out_of_range_count is not None  # type: ignore[attr-defined]
    assert MODULE_ID in result_context.completed_modules


def test_execute_raises_grs_rec_011_when_matching_config_id_missing() -> None:
    context = _sample_context(run_id="run-meaning-match-aggregator-no-matching-config")
    del context.config_versions["matching_config_id"]
    aggregator = build_aggregator()

    with pytest.raises(MeaningMatchAggregatorError) as exc_info:
        aggregator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
