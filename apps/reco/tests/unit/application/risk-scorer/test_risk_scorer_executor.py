"""MOD-RECO-018 Risk Scorer executor unit tests (module spec §14 unit)."""

from __future__ import annotations

import json

import pytest

from conftest import (
    _sample_context,
    build_scorer,
)
from reco.application.risk_scorer import (
    MODULE_ID,
    PHASE_NAME,
    RiskScorerError,
    SURFACE_ERROR_CODE,
)

_EXPECTED_LOG_ATTRIBUTE_KEYS = frozenset(
    {
        "avoid_risk_nonzero_count",
        "module_id",
        "risk_missing_signal_count",
        "risk_penalty_value_out_of_range_count",
        "risk_scorer_candidate_count",
        "risk_scorer_latency_ms",
        "total_scored",
    },
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


# §14 No.12 popularity_score_result 欠損
def test_execute_raises_grs_rec_012_when_popularity_score_result_missing() -> None:
    context = _sample_context()
    del context.popularity_score_result  # type: ignore[attr-defined]
    scorer = build_scorer()

    with pytest.raises(RiskScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 外: feature / meaning 欠損は execute 経路の追加防御テスト
def test_execute_raises_grs_rec_012_when_feature_match_result_missing() -> None:
    context = _sample_context()
    context.feature_match_result = None
    scorer = build_scorer()

    with pytest.raises(RiskScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 外: feature / meaning 欠損は execute 経路の追加防御テスト
def test_execute_raises_grs_rec_012_when_meaning_match_result_missing() -> None:
    context = _sample_context()
    context.meaning_match_result = None
    scorer = build_scorer()

    with pytest.raises(RiskScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.17 補助: execute 経路で context へ metrics を添付（integration Metric 記録本体は別 Task）
def test_execute_attaches_risk_penalty_result_and_metrics_to_execution_context() -> None:
    context = _sample_context(run_id="run-risk-scorer-handoff")
    scorer = build_scorer()

    result_context = scorer.execute(context)

    result = result_context.risk_penalty_result  # type: ignore[attr-defined]
    assert result.total_scored == 1
    assert result_context.risk_scorer_candidate_count == 1  # type: ignore[attr-defined]
    assert result_context.risk_scorer_latency_ms is not None  # type: ignore[attr-defined]
    assert result_context.risk_missing_signal_count is not None  # type: ignore[attr-defined]
    assert result_context.risk_penalty_value_out_of_range_count is not None  # type: ignore[attr-defined]
    assert result_context.avoid_risk_nonzero_count is not None  # type: ignore[attr-defined]
    assert MODULE_ID in result_context.completed_modules


# §14 No.14 未対応 formula（execute 経路）
def test_execute_raises_grs_rec_012_for_unsupported_risk_formula() -> None:
    context = _sample_context(
        config_versions={
            "ranking_config_id": "rc-1",
            "risk_formula": "unsupported_formula",
        },
    )
    scorer = build_scorer()

    with pytest.raises(RiskScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.18 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        run_id="run-risk-scorer-log",
        trace_id="trace-mod-reco-018-unit",
    )
    logger = ScaffoldRecoLogger()
    scorer = build_scorer(logger=logger)

    scorer.execute(context)

    completion_logs = [record for record in logger.records if record.event == PHASE_NAME]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == "trace-mod-reco-018-unit"
    assert log_record.context.run_id == "run-risk-scorer-log"
    assert log_record.attributes["risk_scorer_candidate_count"] == 1
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
