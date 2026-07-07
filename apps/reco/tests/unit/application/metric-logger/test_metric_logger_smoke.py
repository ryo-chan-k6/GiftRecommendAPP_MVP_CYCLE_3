"""MOD-RECO-025 Metric Logger smoke tests (implementation Task)."""

from __future__ import annotations

from conftest import (
    DEFAULT_RUN_ID,
    DEFAULT_TRACE_ID,
    STUB_COMPATIBLE_KEYS,
    TIER_1_KEYS,
    TIER_1B_KEYS,
    build_logger,
    sample_context,
    sample_rich_context,
)
from reco.application.metric_logger.constants import (
    METRIC_SOURCE,
    MODULE_ID,
    TIER_2_METRIC_PREFIXES,
)
from reco.application.metric_logger.repository import InMemoryMetricLoggerRepository


def test_record_metrics_persists_tier_1_metrics() -> None:
    metric_logger, repo = build_logger()
    context = sample_rich_context()

    metric_logger.record_metrics(context)

    assert len(repo.records) == 1
    record = repo.records[0]
    assert record.recommendation_run_id == DEFAULT_RUN_ID
    assert record.trace_id == DEFAULT_TRACE_ID
    assert record.pre_filter_candidate_count == 42
    assert record.retrieval_candidate_count == 30
    assert record.post_filter_candidate_count == 18
    assert record.final_result_count == 2
    assert record.recommendation_empty is False
    assert record.reason_fallback_count == 2
    assert record.retrieval_phase_latency_ms == 33
    assert record.matching_latency_ms == 60
    assert record.ranking_latency_ms == 70
    assert record.reason_generation_latency_ms == 40
    assert record.metric_source == METRIC_SOURCE
    assert record.recorded_at.tzinfo is not None


def test_record_metrics_appends_stub_compatible_observation_buffer() -> None:
    metric_logger, _repo = build_logger()
    context = sample_rich_context()

    metric_logger.record_metrics(context)

    assert len(metric_logger.recorded) == 1
    observation = metric_logger.recorded[0]
    assert STUB_COMPATIBLE_KEYS.issubset(observation.keys())
    assert observation["trace_id"] == DEFAULT_TRACE_ID
    assert observation["run_id"] == DEFAULT_RUN_ID
    assert observation["final_result_count"] == 2
    assert observation["reason_fallback_count"] == 2
    assert TIER_1_KEYS.issubset(observation.keys())
    assert TIER_1B_KEYS.issubset(observation.keys())


def test_record_metrics_sums_partial_tier_1b_latencies() -> None:
    metric_logger, repo = build_logger()
    context = sample_context()
    context.pre_hard_filter_latency_ms = 10
    context.feature_matcher_latency_ms = 25
    context.final_ranker_latency_ms = 30

    metric_logger.record_metrics(context)

    record = repo.records[0]
    assert record.retrieval_phase_latency_ms == 10
    assert record.matching_latency_ms == 25
    assert record.ranking_latency_ms == 30
    assert record.reason_generation_latency_ms is None


def test_record_metrics_tier_1b_latencies_are_none_when_all_inputs_missing() -> None:
    metric_logger, repo = build_logger()
    context = sample_context()

    metric_logger.record_metrics(context)

    record = repo.records[0]
    assert record.retrieval_phase_latency_ms is None
    assert record.matching_latency_ms is None
    assert record.ranking_latency_ms is None
    assert record.reason_generation_latency_ms is None


def test_record_metrics_records_zero_result_run() -> None:
    metric_logger, repo = build_logger()
    context = sample_context()
    context.recommendation_result = None
    context.result_builder_item_count = 0

    metric_logger.record_metrics(context)

    assert repo.records[0].final_result_count == 0
    assert repo.records[0].recommendation_empty is True
    assert metric_logger.recorded[0]["recommendation_empty"] is True


def test_record_metrics_skips_when_run_id_is_missing() -> None:
    metric_logger, repo = build_logger()
    context = sample_context(include_run=False)

    metric_logger.record_metrics(context)

    assert repo.records == []
    assert metric_logger.recorded == []


def test_record_metrics_does_not_propagate_repository_failure() -> None:
    repo = InMemoryMetricLoggerRepository(should_fail_on_save=True)
    metric_logger, _ = build_logger(repository=repo)
    context = sample_context()

    metric_logger.record_metrics(context)

    assert repo.records == []
    assert metric_logger.recorded == []


def test_metric_logger_exposes_module_id() -> None:
    metric_logger, _ = build_logger()

    assert metric_logger.module_id == MODULE_ID


def test_record_metrics_does_not_include_tier_2_distribution_keys() -> None:
    metric_logger, _repo = build_logger()
    context = sample_rich_context()

    metric_logger.record_metrics(context)

    observation = metric_logger.recorded[0]
    for key in observation:
        assert not any(
            key == prefix or key.startswith(f"{prefix}_")
            for prefix in TIER_2_METRIC_PREFIXES
        )
