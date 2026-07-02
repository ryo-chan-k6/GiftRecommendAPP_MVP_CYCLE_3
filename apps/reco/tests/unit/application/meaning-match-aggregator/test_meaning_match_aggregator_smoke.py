"""MOD-RECO-015 Meaning Match Aggregator smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import (
    _default_config_versions,
    _feature_match_entry,
    _sample_context,
    _sample_feature_match_result,
    build_aggregator,
)
from reco.application.feature_matcher.models import FeatureMatchResult
from reco.application.meaning_match_aggregator import (
    AGGREGATION_METHOD_WEIGHTED_AVERAGE,
    MeaningMatchAggregatorError,
    SURFACE_ERROR_CODE,
)
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES


def test_execute_with_empty_feature_match_entries_succeeds() -> None:
    context = _sample_context(
        feature_match_result=FeatureMatchResult(
            entries=(),
            total_matched=0,
            total_excluded=0,
        ),
    )
    aggregator = build_aggregator()

    result_context = aggregator.execute(context)

    result = result_context.meaning_match_result  # type: ignore[attr-defined]
    assert result.total_aggregated == 0
    assert result.entries == ()
    assert result_context.meaning_match_aggregator_candidate_count == 0  # type: ignore[attr-defined]
    assert "MOD-RECO-015" in result_context.completed_modules


def test_execute_aggregates_social_and_symbolic_match_with_equal_weights() -> None:
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(
            entries=(
                _feature_match_entry(
                    item_id="item-001",
                    match_value=0.92,
                ),
            ),
        ),
    )
    aggregator = build_aggregator()

    result_context = aggregator.execute(context)

    entry = result_context.meaning_match_result.entries[0]  # type: ignore[attr-defined]
    assert entry.social_match == pytest.approx(0.92)
    assert entry.symbolic_match == pytest.approx(0.92)
    assert entry.aggregation_method == AGGREGATION_METHOD_WEIGHTED_AVERAGE
    assert entry.matching_config_id == context.config_versions["matching_config_id"]


def test_execute_preserves_candidate_order() -> None:
    context = _sample_context()
    aggregator = build_aggregator()

    result_context = aggregator.execute(context)

    item_ids = [
        entry.item_id
        for entry in result_context.meaning_match_result.entries  # type: ignore[attr-defined]
    ]
    assert item_ids == ["item-001", "item-002"]


def test_execute_does_not_mutate_feature_match_result() -> None:
    context = _sample_context()
    original = context.feature_match_result  # type: ignore[attr-defined]
    original_entry_count = len(original.entries)
    aggregator = build_aggregator()

    aggregator.execute(context)

    assert context.feature_match_result is original  # type: ignore[attr-defined]
    assert len(context.feature_match_result.entries) == original_entry_count  # type: ignore[attr-defined]


def test_execute_raises_when_feature_match_result_missing() -> None:
    context = _sample_context()
    del context.feature_match_result  # type: ignore[attr-defined]
    aggregator = build_aggregator()

    with pytest.raises(MeaningMatchAggregatorError) as exc_info:
        aggregator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_when_feature_axis_missing() -> None:
    entry = _feature_match_entry(item_id="item-001", match_value=0.8)
    partial_features = dict(entry.features)
    del partial_features["formality"]
    broken_entry = entry.__class__(
        item_id=entry.item_id,
        features=partial_features,
        meaning_distance=entry.meaning_distance,
        calculated_at=entry.calculated_at,
        matching_config_id=entry.matching_config_id,
    )
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(entries=(broken_entry,)),
    )
    aggregator = build_aggregator()

    with pytest.raises(MeaningMatchAggregatorError) as exc_info:
        aggregator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_when_matching_weights_missing() -> None:
    config_versions = _default_config_versions()
    del config_versions["social_feature_weights.formality"]
    context = _sample_context(config_versions=config_versions)
    aggregator = build_aggregator()

    with pytest.raises(MeaningMatchAggregatorError) as exc_info:
        aggregator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_clips_out_of_range_match_and_records_metric() -> None:
    entry = _feature_match_entry(item_id="item-001", match_value=1.2)
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(entries=(entry,)),
    )
    aggregator = build_aggregator()

    result_context = aggregator.execute(context)

    aggregated = result_context.meaning_match_result.entries[0]  # type: ignore[attr-defined]
    assert aggregated.social_match == pytest.approx(1.0)
    assert aggregated.symbolic_match == pytest.approx(1.0)
    assert result_context.meaning_match_value_out_of_range_count == len(  # type: ignore[attr-defined]
        MVP_FEATURE_CODES,
    )
