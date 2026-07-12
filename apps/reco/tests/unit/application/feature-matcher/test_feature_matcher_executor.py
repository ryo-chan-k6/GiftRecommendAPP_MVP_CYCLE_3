"""MOD-RECO-014 Feature Matcher executor unit tests (module spec §14 unit)."""

from __future__ import annotations

import json

import pytest

from conftest import (
    _sample_context,
    build_matcher_with_repository,
)
from reco.application.feature_matcher import MODULE_ID, PHASE_NAME
from reco.application.feature_matcher.errors import FeatureMatcherError
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


# §14 No.16 ログ — trace_id を含み secret を含まない
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        run_id="run-feature-matcher-log",
        trace_id="trace-mod-reco-014-unit",
    )
    logger = ScaffoldRecoLogger()
    matcher, _ = build_matcher_with_repository(context)
    matcher.logger = logger

    matcher.execute(context)

    completion_logs = [record for record in logger.records if record.event == PHASE_NAME]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == "trace-mod-reco-014-unit"
    assert log_record.context.run_id == "run-feature-matcher-log"
    assert log_record.attributes["feature_matcher_candidate_count"] == 2
    assert log_record.attributes["module_id"] == MODULE_ID
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized


def test_execute_attaches_feature_match_result_and_metrics_to_execution_context() -> None:
    context = _sample_context(run_id="run-feature-matcher-handoff")
    matcher, _ = build_matcher_with_repository(context)

    result_context = matcher.execute(context)

    result = result_context.feature_match_result  # type: ignore[attr-defined]
    assert result.total_matched == 2
    assert result_context.feature_matcher_candidate_count == 2  # type: ignore[attr-defined]
    assert result_context.feature_matcher_latency_ms is not None  # type: ignore[attr-defined]
    assert result_context.feature_match_imputed_axis_count is not None  # type: ignore[attr-defined]
    assert result_context.feature_value_out_of_range_count is not None  # type: ignore[attr-defined]
    assert "MOD-RECO-014" in result_context.completed_modules


def test_execute_raises_when_matching_config_id_missing() -> None:
    context = _sample_context(run_id="run-feature-matcher-no-matching-config")
    del context.config_versions["matching_config_id"]
    matcher, _ = build_matcher_with_repository(context)

    with pytest.raises(FeatureMatcherError, match="matching_config_id is required"):
        matcher.execute(context)
