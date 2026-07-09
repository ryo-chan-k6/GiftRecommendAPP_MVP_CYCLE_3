"""MOD-RECO-013 Post Hard Filter Executor module unit tests (module spec §14)."""

from __future__ import annotations

import json

from conftest import (
    _sample_context,
    build_executor_with_repository,
)
from reco.application.post_hard_filter_executor import PHASE_NAME
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


# §14 No.13 ログ — trace_id を含み secret を含まない
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        run_id="run-post-log",
        trace_id="trace-mod-reco-013-unit",
    )
    logger = ScaffoldRecoLogger()
    executor, _ = build_executor_with_repository(context, logger=logger)

    executor.execute(context)

    completion_logs = [record for record in logger.records if record.event == PHASE_NAME]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == "trace-mod-reco-013-unit"
    assert log_record.context.run_id == "run-post-log"
    assert log_record.attributes["post_filter_candidate_count"] == 2
    assert log_record.attributes["module_id"] == "MOD-RECO-013"
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized


def test_execute_attaches_validated_retrieval_candidate_to_execution_context() -> None:
    context = _sample_context(run_id="run-post-handoff")
    executor, _ = build_executor_with_repository(context)

    result_context = executor.execute(context)

    validated = result_context.validated_retrieval_candidate  # type: ignore[attr-defined]
    excluded = result_context.excluded_candidate_log  # type: ignore[attr-defined]
    assert validated.total_validated == 2
    assert excluded.entries == ()
    assert result_context.post_filter_candidate_count == 2  # type: ignore[attr-defined]
    assert result_context.post_hard_filter_latency_ms is not None  # type: ignore[attr-defined]
    assert "MOD-RECO-013" in result_context.completed_modules
