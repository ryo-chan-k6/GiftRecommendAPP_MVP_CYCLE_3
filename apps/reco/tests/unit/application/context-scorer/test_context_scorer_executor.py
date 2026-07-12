"""MOD-RECO-016 Context Scorer executor unit tests (module spec §14 unit)."""

from __future__ import annotations

import json

import pytest

from conftest import (
    _sample_context,
    build_scorer,
)
from reco.application.context_scorer import (
    MODULE_ID,
    PHASE_NAME,
    ContextScorerError,
    SURFACE_ERROR_CODE,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


# §14 No.19 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        run_id="run-context-scorer-log",
        trace_id="trace-mod-reco-016-unit",
    )
    logger = ScaffoldRecoLogger()
    scorer = build_scorer(logger=logger)

    scorer.execute(context)

    completion_logs = [record for record in logger.records if record.event == PHASE_NAME]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == "trace-mod-reco-016-unit"
    assert log_record.context.run_id == "run-context-scorer-log"
    assert log_record.attributes["context_scorer_candidate_count"] == 1
    assert log_record.attributes["module_id"] == MODULE_ID
    assert log_record.attributes["total_scored"] == 1
    assert log_record.attributes["lambda_ctx_applied"] == pytest.approx(0.4)
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized


def test_execute_attaches_context_score_result_and_metrics_to_execution_context() -> None:
    context = _sample_context(run_id="run-context-scorer-handoff")
    scorer = build_scorer()

    result_context = scorer.execute(context)

    result = result_context.context_score_result  # type: ignore[attr-defined]
    assert result.total_scored == 1
    assert result_context.context_scorer_candidate_count == 1  # type: ignore[attr-defined]
    assert result_context.context_scorer_latency_ms is not None  # type: ignore[attr-defined]
    assert result_context.context_score_value_out_of_range_count is not None  # type: ignore[attr-defined]
    assert result_context.lambda_ctx_applied == pytest.approx(0.4)  # type: ignore[attr-defined]
    assert MODULE_ID in result_context.completed_modules


def test_execute_raises_grs_rec_011_when_run_id_missing() -> None:
    context = _sample_context(run_id="run-context-scorer-no-run-id")
    context.recommendation_run = None  # type: ignore[assignment]
    scorer = build_scorer()

    with pytest.raises(ContextScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
