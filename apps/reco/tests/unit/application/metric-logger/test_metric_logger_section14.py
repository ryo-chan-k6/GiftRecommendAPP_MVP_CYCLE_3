"""MOD-RECO-025 §14 unit test coverage (module spec No.1–11).

| §14 No | 観点 | テスト関数 |
| -----: | ---- | ---------- |
| 1 | Port 契約 | `test_record_metrics_accepts_execution_context` |
| 2 | Tier 1 マッピング | `test_section9_1_tier_1_metrics_map_to_persisted_record`, `test_final_result_count_uses_result_builder_item_count` |
| 3 | 0 件 Run | `test_zero_result_run_records_empty_flags` |
| 4 | trace / run | `test_trace_id_and_recommendation_run_id_match_execution_context` |
| 5 | run_id 欠落 | `test_missing_run_id_skips_persist_and_logs_warn_without_propagation` |
| 6 | 失敗非伝播 | `test_repository_save_failure_does_not_propagate` |
| 7 | Stub 互換 | `test_observation_includes_stub_compatible_keys_and_values` |
| 8 | InMemory Repository | `test_in_memory_repository_runs_without_external_db` |
| 9 | Tier 2 非混入 | `test_observation_excludes_tier_2_distribution_keys` |
| 10 | Orchestrator 連携 | out of scope（integration / Wiring 後） |
| 11 | 失敗 Run | out of scope（Orchestrator が `record_metrics()` を呼ばないこと） |
"""

from __future__ import annotations

from datetime import UTC, datetime

from conftest import (
    DEFAULT_RUN_ID,
    DEFAULT_TRACE_ID,
    STUB_COMPATIBLE_KEYS,
    TIER_1_KEYS,
    build_logger,
    sample_context,
    sample_rich_context,
)
from reco.application.metric_logger.constants import METRIC_SOURCE, TIER_2_METRIC_PREFIXES
from reco.application.metric_logger.mapper import build_metric_record
from reco.application.metric_logger.repository import InMemoryMetricLoggerRepository
from reco.application.recommendation_orchestrator.execution_context import ExecutionContext
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def test_record_metrics_accepts_execution_context() -> None:
    """§14 No.1: MetricLoggerPort.record_metrics() accepts ExecutionContext."""
    metric_logger, repo = build_logger()
    context = sample_context()

    assert isinstance(context, ExecutionContext)
    metric_logger.record_metrics(context)

    assert len(repo.records) == 1


def test_section9_1_tier_1_metrics_map_to_persisted_record() -> None:
    """§14 No.2: §9.1 Tier 1 metrics map from ExecutionContext to persisted row."""
    fixed_time = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)
    context = sample_rich_context()

    record = build_metric_record(context, recorded_at=fixed_time)

    assert record.recommendation_run_id == DEFAULT_RUN_ID
    assert record.trace_id == DEFAULT_TRACE_ID
    assert isinstance(record.recommendation_latency_ms, int)
    assert record.recommendation_latency_ms >= 0
    assert record.pre_filter_candidate_count == 42
    assert record.retrieval_candidate_count == 30
    assert record.post_filter_candidate_count == 18
    assert record.final_result_count == 2
    assert record.recommendation_empty is False
    assert record.reason_fallback_count == 2
    assert record.recorded_at == fixed_time
    assert record.metric_source == METRIC_SOURCE


def test_final_result_count_uses_result_builder_item_count() -> None:
    """§14 No.2: final_result_count falls back to result_builder_item_count."""
    fixed_time = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)
    context = sample_context()
    context.recommendation_result = None
    context.result_builder_item_count = 3

    record = build_metric_record(context, recorded_at=fixed_time)

    assert record.final_result_count == 3
    assert record.recommendation_empty is False


def test_zero_result_run_records_empty_flags() -> None:
    """§14 No.3: zero-item run records final_result_count=0 and recommendation_empty=true."""
    metric_logger, repo = build_logger()
    context = sample_context()
    context.recommendation_result = None
    context.result_builder_item_count = 0

    metric_logger.record_metrics(context)

    record = repo.records[0]
    assert record.final_result_count == 0
    assert record.recommendation_empty is True
    assert metric_logger.recorded[0]["final_result_count"] == 0
    assert metric_logger.recorded[0]["recommendation_empty"] is True


def test_trace_id_and_recommendation_run_id_match_execution_context() -> None:
    """§14 No.4: trace_id and recommendation_run_id match ExecutionContext."""
    metric_logger, repo = build_logger()
    context = sample_rich_context()

    metric_logger.record_metrics(context)

    record = repo.records[0]
    observation = metric_logger.recorded[0]
    assert record.trace_id == DEFAULT_TRACE_ID
    assert record.recommendation_run_id == DEFAULT_RUN_ID
    assert observation["trace_id"] == DEFAULT_TRACE_ID
    assert observation["run_id"] == DEFAULT_RUN_ID
    assert observation["recommendation_run_id"] == DEFAULT_RUN_ID


def test_missing_run_id_skips_persist_and_logs_warn_without_propagation() -> None:
    """§14 No.5: missing run_id skips persist, logs warn, and does not propagate."""
    logger = ScaffoldRecoLogger()
    metric_logger, repo = build_logger(logger=logger)
    context = sample_context(include_run=False)

    metric_logger.record_metrics(context)

    assert repo.records == []
    assert metric_logger.recorded == []
    assert len(logger.records) == 1
    warn_record = logger.records[0]
    assert warn_record.event == "metric_log_skipped_missing_run_id"
    assert warn_record.attributes.get("severity") == "warn"


def test_repository_save_failure_does_not_propagate() -> None:
    """§14 No.6: repository save failure does not propagate to caller."""
    logger = ScaffoldRecoLogger()
    repo = InMemoryMetricLoggerRepository(should_fail_on_save=True)
    metric_logger, _ = build_logger(repository=repo, logger=logger)
    context = sample_context()

    metric_logger.record_metrics(context)

    assert repo.records == []
    assert metric_logger.recorded == []
    assert any(record.event == "metric_log_save_failed" for record in logger.records)


def test_observation_includes_stub_compatible_keys_and_values() -> None:
    """§14 No.7: observation buffer includes StubMetricLogger-compatible keys."""
    metric_logger, _repo = build_logger()
    context = sample_rich_context()

    metric_logger.record_metrics(context)

    observation = metric_logger.recorded[0]
    assert STUB_COMPATIBLE_KEYS.issubset(observation.keys())
    assert TIER_1_KEYS.issubset(observation.keys())
    assert isinstance(observation["recommendation_latency_ms"], int)
    assert observation["reason_fallback_count"] == 2
    assert observation["final_result_count"] == 2
    assert observation["trace_id"] == DEFAULT_TRACE_ID
    assert observation["run_id"] == DEFAULT_RUN_ID


def test_in_memory_repository_runs_without_external_db() -> None:
    """§14 No.8: InMemory repository enables pytest without production DB."""
    repo = InMemoryMetricLoggerRepository()
    metric_logger = build_logger(repository=repo)[0]
    context = sample_context()

    metric_logger.record_metrics(context)

    assert len(repo.records) == 1
    assert repo.records[0].recommendation_run_id == DEFAULT_RUN_ID


def test_observation_excludes_tier_2_distribution_keys() -> None:
    """§14 No.9: MVP observation excludes Tier 2 distribution metric keys."""
    metric_logger, _repo = build_logger()
    context = sample_rich_context()

    metric_logger.record_metrics(context)

    observation = metric_logger.recorded[0]
    for key in observation:
        assert not any(
            key == prefix or key.startswith(f"{prefix}_")
            for prefix in TIER_2_METRIC_PREFIXES
        )
