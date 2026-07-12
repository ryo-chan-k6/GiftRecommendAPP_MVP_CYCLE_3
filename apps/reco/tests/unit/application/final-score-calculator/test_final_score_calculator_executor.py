"""MOD-RECO-019 Final Score Calculator executor unit tests (module spec §14 unit)."""

from __future__ import annotations

import json

import pytest

from conftest import (
    _sample_context,
    build_scorer,
)
from reco.application.final_score_calculator import (
    MODULE_ID,
    PHASE_NAME,
    FinalScoreCalculatorError,
    SURFACE_ERROR_CODE,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

_EXPECTED_LOG_ATTRIBUTE_KEYS = frozenset(
    {
        "final_score_calculator_candidate_count",
        "final_score_calculator_latency_ms",
        "final_score_excluded_candidate_count",
        "final_score_value_out_of_range_count",
        "module_id",
        "total_scored",
    },
)


def test_execute_raises_grs_rec_012_when_context_score_result_missing() -> None:
    context = _sample_context()
    del context.context_score_result  # type: ignore[attr-defined]
    scorer = build_scorer()

    with pytest.raises(FinalScoreCalculatorError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_grs_rec_012_when_popularity_score_result_missing() -> None:
    context = _sample_context()
    del context.popularity_score_result  # type: ignore[attr-defined]
    scorer = build_scorer()

    with pytest.raises(FinalScoreCalculatorError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_attaches_final_score_result_and_metrics_to_execution_context() -> None:
    context = _sample_context(run_id="run-final-score-calculator-handoff")
    scorer = build_scorer()

    result_context = scorer.execute(context)

    result = result_context.final_score_result  # type: ignore[attr-defined]
    assert result.total_scored == 1
    assert result_context.final_score_calculator_candidate_count == 1  # type: ignore[attr-defined]
    assert result_context.final_score_calculator_latency_ms is not None  # type: ignore[attr-defined]
    assert result_context.final_score_excluded_candidate_count is not None  # type: ignore[attr-defined]
    assert result_context.final_score_value_out_of_range_count is not None  # type: ignore[attr-defined]
    assert MODULE_ID in result_context.completed_modules


# §14 No.18 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        run_id="run-final-score-calculator-log",
        trace_id="trace-mod-reco-019-unit",
    )
    logger = ScaffoldRecoLogger()
    scorer = build_scorer(logger=logger)

    scorer.execute(context)

    completion_logs = [record for record in logger.records if record.event == PHASE_NAME]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == "trace-mod-reco-019-unit"
    assert log_record.context.run_id == "run-final-score-calculator-log"
    assert log_record.attributes["final_score_calculator_candidate_count"] == 1
    assert log_record.attributes["module_id"] == MODULE_ID
    assert log_record.attributes["total_scored"] == 1
    assert set(log_record.attributes) == _EXPECTED_LOG_ATTRIBUTE_KEYS
    assert "entries" not in log_record.attributes
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "item-001" not in serialized
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
