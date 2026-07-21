"""MOD-RECO-015 Meaning Match Aggregator unit tests (module spec §14 unit)."""

from __future__ import annotations

from dataclasses import fields

import pytest

from conftest import (
    _default_config_versions,
    _feature_match_entry,
    _feature_match_entry_with_matches,
    _sample_context,
    _sample_feature_match_result,
    run_aggregation_from_context,
)
from reco.application.config_version_resolver import DEFAULT_MATCHING_CONFIG_ID
from reco.application.config_version_resolver.constants import (
    SOCIAL_FEATURE_WEIGHT_KEYS,
    SYMBOLIC_FEATURE_WEIGHT_KEYS,
)
from reco.application.feature_matcher.models import FeatureMatchResult
from reco.application.meaning_match_aggregator import (
    AGGREGATION_METHOD_WEIGHTED_AVERAGE,
    MeaningMatchAggregatorError,
    SURFACE_ERROR_CODE,
    run_meaning_match_aggregation,
)
from reco.application.meaning_match_aggregator.models import MeaningMatchEntry
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES


def _axis_matches_uniform(match_value: float) -> dict[str, float]:
    return {axis: match_value for axis in MVP_FEATURE_CODES}


def _expected_equal_weight_average(values: dict[str, float], feature_keys: tuple[str, ...]) -> float:
    return sum(values[key] for key in feature_keys) / len(feature_keys)


# §14 No.1 正常系（Social 集約）
def test_run_meaning_match_aggregation_computes_social_match_from_social_axes_only() -> None:
    axis_matches = {
        "formality": 0.9,
        "safety": 0.6,
        "brand_appropriateness": 0.3,
        "emotion": 0.0,
        "novelty": 0.0,
        "intimacy": 0.0,
        "symbolic_identity": 0.0,
        "story_richness": 0.0,
    }
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(
            entries=(_feature_match_entry_with_matches(item_id="item-social", axis_matches=axis_matches),),
        ),
    )

    result, _ = run_aggregation_from_context(context)
    entry = result.entries[0]

    expected_social = _expected_equal_weight_average(axis_matches, SOCIAL_FEATURE_WEIGHT_KEYS)
    assert entry.social_match == pytest.approx(expected_social)
    assert entry.symbolic_match == pytest.approx(0.0)


# §14 No.2 正常系（Symbolic 集約）
def test_run_meaning_match_aggregation_computes_symbolic_match_from_symbolic_axes_only() -> None:
    axis_matches = {
        "formality": 0.0,
        "safety": 0.0,
        "brand_appropriateness": 0.0,
        "emotion": 1.0,
        "novelty": 0.8,
        "intimacy": 0.6,
        "symbolic_identity": 0.4,
        "story_richness": 0.2,
    }
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(
            entries=(_feature_match_entry_with_matches(item_id="item-symbolic", axis_matches=axis_matches),),
        ),
    )

    result, _ = run_aggregation_from_context(context)
    entry = result.entries[0]

    expected_symbolic = _expected_equal_weight_average(axis_matches, SYMBOLIC_FEATURE_WEIGHT_KEYS)
    assert entry.symbolic_match == pytest.approx(expected_symbolic)
    assert entry.social_match == pytest.approx(0.0)


# §14 No.3 正常系（候補複数）
def test_run_meaning_match_aggregation_preserves_candidate_input_order() -> None:
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(
            entries=(
                _feature_match_entry(item_id="item-a", match_value=0.91),
                _feature_match_entry(item_id="item-b", match_value=0.82),
                _feature_match_entry(item_id="item-c", match_value=0.73),
            ),
        ),
    )

    result, metrics = run_aggregation_from_context(context)

    assert [entry.item_id for entry in result.entries] == ["item-a", "item-b", "item-c"]
    assert result.total_aggregated == 3
    assert metrics.meaning_match_aggregator_candidate_count == 3


# §14 No.4 matching_config 重み参照
def test_run_meaning_match_aggregation_applies_matching_config_weights() -> None:
    config_versions = _default_config_versions()
    config_versions["social_feature_weights.formality"] = "0.5"
    config_versions["social_feature_weights.safety"] = "0.3"
    config_versions["social_feature_weights.brand_appropriateness"] = "0.2"
    config_versions["symbolic_feature_weights.emotion"] = "0.4"
    config_versions["symbolic_feature_weights.novelty"] = "0.3"
    config_versions["symbolic_feature_weights.intimacy"] = "0.15"
    config_versions["symbolic_feature_weights.symbolic_identity"] = "0.1"
    config_versions["symbolic_feature_weights.story_richness"] = "0.05"

    axis_matches = {
        "formality": 1.0,
        "safety": 0.0,
        "brand_appropriateness": 0.0,
        "emotion": 1.0,
        "novelty": 0.0,
        "intimacy": 0.0,
        "symbolic_identity": 0.0,
        "story_richness": 0.0,
    }
    context = _sample_context(
        config_versions=config_versions,
        feature_match_result=_sample_feature_match_result(
            entries=(_feature_match_entry_with_matches(item_id="item-weighted", axis_matches=axis_matches),),
        ),
    )

    result, _ = run_aggregation_from_context(context)
    entry = result.entries[0]

    assert entry.social_match == pytest.approx(0.5)
    assert entry.symbolic_match == pytest.approx(0.4)
    assert entry.aggregation_method == AGGREGATION_METHOD_WEIGHTED_AVERAGE
    assert entry.matching_config_id == DEFAULT_MATCHING_CONFIG_ID


# §14 No.5 軸別 match 非重複
def test_run_meaning_match_aggregation_does_not_embed_axis_breakdown_in_result() -> None:
    context = _sample_context()
    original_feature_match = context.feature_match_result  # type: ignore[attr-defined]

    result, _ = run_aggregation_from_context(context)
    entry = result.entries[0]

    entry_field_names = {field.name for field in fields(MeaningMatchEntry)}
    assert "features" not in entry_field_names
    assert not hasattr(entry, "features")
    assert original_feature_match.entries[0].features["formality"].match == pytest.approx(0.92)


# §14 No.6 境界値（完全一致）
def test_run_meaning_match_aggregation_sets_unit_match_when_all_axes_are_one() -> None:
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(
            entries=(_feature_match_entry(item_id="item-perfect", match_value=1.0),),
        ),
    )

    result, _ = run_aggregation_from_context(context)
    entry = result.entries[0]

    assert entry.social_match == pytest.approx(1.0)
    assert entry.symbolic_match == pytest.approx(1.0)


# §14 No.7 境界値（最大不一致）
def test_run_meaning_match_aggregation_sets_zero_match_when_all_axes_are_zero() -> None:
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(
            entries=(_feature_match_entry(item_id="item-zero", match_value=0.0),),
        ),
    )

    result, _ = run_aggregation_from_context(context)
    entry = result.entries[0]

    assert entry.social_match == pytest.approx(0.0)
    assert entry.symbolic_match == pytest.approx(0.0)


# §14 No.8 feature_match_result 欠損
def test_run_meaning_match_aggregation_raises_grs_rec_011_when_feature_match_result_missing() -> None:
    context = _sample_context()
    del context.feature_match_result  # type: ignore[attr-defined]

    with pytest.raises(MeaningMatchAggregatorError) as exc_info:
        run_aggregation_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.9 8 軸 match 欠損
def test_run_meaning_match_aggregation_raises_grs_rec_011_when_feature_axis_missing() -> None:
    entry = _feature_match_entry(item_id="item-missing-axis", match_value=0.8)
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

    with pytest.raises(MeaningMatchAggregatorError) as exc_info:
        run_aggregation_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.10 重み欠損
def test_run_meaning_match_aggregation_raises_grs_rec_011_when_matching_weights_missing() -> None:
    config_versions = _default_config_versions()
    del config_versions["social_feature_weights.formality"]
    context = _sample_context(config_versions=config_versions)

    with pytest.raises(MeaningMatchAggregatorError) as exc_info:
        run_aggregation_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.11 入力 0 件
def test_run_meaning_match_aggregation_succeeds_with_empty_feature_match_entries() -> None:
    context = _sample_context(
        feature_match_result=FeatureMatchResult(
            entries=(),
            total_matched=0,
            total_excluded=0,
        ),
    )

    result, metrics = run_aggregation_from_context(context)

    assert result.total_aggregated == 0
    assert result.entries == ()
    assert metrics.meaning_match_aggregator_candidate_count == 0


# §14 No.12 値域外 match
@pytest.mark.parametrize("out_of_range_value", [-0.2, 1.2])
def test_run_meaning_match_aggregation_clips_out_of_range_match_and_records_metric(
    out_of_range_value: float,
) -> None:
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(
            entries=(_feature_match_entry(item_id="item-oor", match_value=out_of_range_value),),
        ),
    )

    result, metrics = run_aggregation_from_context(context)
    entry = result.entries[0]

    clipped = 0.0 if out_of_range_value < 0.0 else 1.0
    assert entry.social_match == pytest.approx(clipped)
    assert entry.symbolic_match == pytest.approx(clipped)
    assert metrics.meaning_match_value_out_of_range_count == len(MVP_FEATURE_CODES)


# §14 No.14 責務境界
def test_run_meaning_match_aggregation_trusts_feature_match_without_recalculation() -> None:
    trusted_match = 0.75
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(
            entries=(
                _feature_match_entry_with_matches(
                    item_id="item-trust-match",
                    axis_matches=_axis_matches_uniform(trusted_match),
                    distance_overrides={axis: 0.99 for axis in MVP_FEATURE_CODES},
                ),
            ),
        ),
    )

    result, _ = run_aggregation_from_context(context)
    entry = result.entries[0]

    assert entry.social_match == pytest.approx(trusted_match)
    assert entry.symbolic_match == pytest.approx(trusted_match)


def test_run_meaning_match_aggregation_does_not_compute_lambda_ctx_or_context_score() -> None:
    context = _sample_context()

    result, _ = run_meaning_match_aggregation(
        feature_match_result=context.feature_match_result,  # type: ignore[attr-defined]
        config_versions=context.config_versions,
        default_matching_config_id=context.config_versions["matching_config_id"],
    )

    entry_field_names = {field.name for field in fields(MeaningMatchEntry)}
    assert "lambda_ctx" not in entry_field_names
    assert "context_score" not in entry_field_names
    assert result.total_aggregated == len(context.feature_match_result.entries)  # type: ignore[attr-defined]


# §14 No.17 feature_match_result 不変
def test_run_meaning_match_aggregation_does_not_mutate_feature_match_result() -> None:
    context = _sample_context()
    original = context.feature_match_result  # type: ignore[attr-defined]
    original_entry_count = len(original.entries)
    original_formality_match = original.entries[0].features["formality"].match

    run_aggregation_from_context(context)

    assert context.feature_match_result is original  # type: ignore[attr-defined]
    assert len(context.feature_match_result.entries) == original_entry_count  # type: ignore[attr-defined]
    assert (
        context.feature_match_result.entries[0].features["formality"].match  # type: ignore[attr-defined]
        == original_formality_match
    )
