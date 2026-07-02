"""MOD-RECO-014 Feature Matcher unit tests (module spec §14 unit)."""

from __future__ import annotations

import math

import pytest

from conftest import (
    TrackingItemFeatureRepository,
    _sample_context,
    _sample_internal_estimate,
    _sample_user_feature,
    _uniform_user_features,
    build_item_record,
    build_matcher_with_repository,
    run_matching_from_context,
)
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.feature_matcher import (
    FeatureMatcherError,
    IMPUTED_FEATURE_VALUE,
    MATCH_METHOD_ONE_MINUS_DISTANCE,
    SURFACE_ERROR_CODE,
)
from reco.application.post_hard_filter_executor.models import (
    ValidatedRetrievalCandidate,
    ValidatedRetrievalCandidateItem,
)
from reco.application.user_feature_generator.models import UserFeature
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES


# §14 No.1 正常系（8 軸一致度）
def test_run_feature_matching_computes_one_minus_distance_for_all_axes() -> None:
    user_value = 0.8
    item_value = 0.65
    context = _sample_context(
        user_feature=_sample_user_feature(features=_uniform_user_features(user_value)),
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(
                ValidatedRetrievalCandidateItem(item_id="item-001", similarity_score=0.9),
            ),
            total_validated=1,
            total_excluded=0,
        ),
    )
    repo = TrackingItemFeatureRepository(
        records={
            "item-001": build_item_record(
                item_id="item-001",
                features=_uniform_user_features(item_value),
            ),
        },
    )

    result, _ = run_matching_from_context(context, item_repository=repo)
    entry = result.entries[0]

    expected_distance = abs(user_value - item_value)
    expected_match = 1.0 - expected_distance
    for axis in MVP_FEATURE_CODES:
        axis_result = entry.features[axis]
        assert axis_result.distance == pytest.approx(expected_distance)
        assert axis_result.match == pytest.approx(expected_match)
        assert axis_result.match_method == MATCH_METHOD_ONE_MINUS_DISTANCE
        assert axis_result.imputed is False


# §14 No.2 正常系（候補複数）
def test_run_feature_matching_preserves_candidate_input_order() -> None:
    context = _sample_context(
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(
                ValidatedRetrievalCandidateItem(item_id="item-a", similarity_score=0.95),
                ValidatedRetrievalCandidateItem(item_id="item-b", similarity_score=0.80),
                ValidatedRetrievalCandidateItem(item_id="item-c", similarity_score=0.70),
            ),
            total_validated=3,
            total_excluded=0,
        ),
    )
    repo = TrackingItemFeatureRepository(
        records={
            item_id: build_item_record(item_id=item_id, features=_uniform_user_features(0.5))
            for item_id in ("item-a", "item-b", "item-c")
        },
    )

    result, metrics = run_matching_from_context(context, item_repository=repo)

    assert [entry.item_id for entry in result.entries] == ["item-a", "item-b", "item-c"]
    assert result.total_matched == 3
    assert metrics.feature_matcher_candidate_count == 3


# §14 No.3 境界値（完全一致）
def test_run_feature_matching_sets_zero_distance_and_unit_match_on_exact_alignment() -> None:
    aligned_value = 0.42
    context = _sample_context(
        user_feature=_sample_user_feature(features=_uniform_user_features(aligned_value)),
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(
                ValidatedRetrievalCandidateItem(item_id="item-exact", similarity_score=0.9),
            ),
            total_validated=1,
            total_excluded=0,
        ),
    )
    repo = TrackingItemFeatureRepository(
        records={
            "item-exact": build_item_record(
                item_id="item-exact",
                features=_uniform_user_features(aligned_value),
            ),
        },
    )

    result, _ = run_matching_from_context(context, item_repository=repo)
    entry = result.entries[0]

    for axis in MVP_FEATURE_CODES:
        assert entry.features[axis].distance == pytest.approx(0.0)
        assert entry.features[axis].match == pytest.approx(1.0)
    assert entry.meaning_distance == pytest.approx(0.0)


# §14 No.4 境界値（最大不一致）
def test_run_feature_matching_sets_max_distance_and_zero_match_on_opposite_values() -> None:
    context = _sample_context(
        user_feature=_sample_user_feature(features=_uniform_user_features(0.0)),
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(
                ValidatedRetrievalCandidateItem(item_id="item-opposite", similarity_score=0.9),
            ),
            total_validated=1,
            total_excluded=0,
        ),
    )
    repo = TrackingItemFeatureRepository(
        records={
            "item-opposite": build_item_record(
                item_id="item-opposite",
                features=_uniform_user_features(1.0),
            ),
        },
    )

    result, _ = run_matching_from_context(context, item_repository=repo)
    entry = result.entries[0]

    for axis in MVP_FEATURE_CODES:
        assert entry.features[axis].distance == pytest.approx(1.0)
        assert entry.features[axis].match == pytest.approx(0.0)
    expected_meaning_distance = math.sqrt(len(MVP_FEATURE_CODES))
    assert entry.meaning_distance == pytest.approx(expected_meaning_distance)


# §14 No.5 user_feature 欠損
def test_run_feature_matching_raises_grs_rec_011_when_user_feature_axes_missing() -> None:
    base_user_feature = _sample_user_feature()
    context = _sample_context(
        user_feature=UserFeature(
            recommendation_run_id=base_user_feature.recommendation_run_id,
            features={},
            user_feature_raw=base_user_feature.user_feature_raw,
            feature_normalization_version_id=base_user_feature.feature_normalization_version_id,
            semantic_config_version_id=base_user_feature.semantic_config_version_id,
            generated_at=base_user_feature.generated_at,
        ),
    )
    matcher, _ = build_matcher_with_repository(context)

    with pytest.raises(FeatureMatcherError) as exc_info:
        matcher.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.6 item_feature 全欠損
def test_run_feature_matching_excludes_candidate_when_item_features_are_empty() -> None:
    context = _sample_context(
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(
                ValidatedRetrievalCandidateItem(item_id="item-empty", similarity_score=0.9),
            ),
            total_validated=1,
            total_excluded=0,
        ),
    )
    repo = TrackingItemFeatureRepository(
        records={
            "item-empty": build_item_record(item_id="item-empty", features={}),
        },
    )

    result, metrics = run_matching_from_context(context, item_repository=repo)

    assert result.entries == ()
    assert result.total_matched == 0
    assert result.total_excluded == 1
    assert metrics.feature_matcher_excluded_count == 1


# §14 No.7 item_feature 一部欠損
def test_run_feature_matching_imputes_missing_item_axes_with_half_and_flag() -> None:
    partial_features = {"formality": 0.7, "safety": 0.6}
    context = _sample_context(
        user_feature=_sample_user_feature(features=_uniform_user_features(0.8)),
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(
                ValidatedRetrievalCandidateItem(item_id="item-partial", similarity_score=0.9),
            ),
            total_validated=1,
            total_excluded=0,
        ),
    )
    repo = TrackingItemFeatureRepository(
        records={
            "item-partial": build_item_record(item_id="item-partial", features=partial_features),
        },
    )

    result, metrics = run_matching_from_context(context, item_repository=repo)
    entry = result.entries[0]

    assert entry.features["formality"].imputed is False
    assert entry.features["emotion"].imputed is True
    assert entry.features["emotion"].distance == pytest.approx(
        abs(0.8 - IMPUTED_FEATURE_VALUE),
    )
    assert metrics.feature_match_imputed_axis_count == len(MVP_FEATURE_CODES) - len(
        partial_features,
    )


# §14 No.8 値域外
@pytest.mark.parametrize("out_of_range_value", [-0.2, 1.2])
def test_run_feature_matching_clips_out_of_range_values_and_records_metric(
    out_of_range_value: float,
) -> None:
    features = _uniform_user_features(0.5)
    features["formality"] = out_of_range_value
    context = _sample_context(
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(
                ValidatedRetrievalCandidateItem(item_id="item-oor", similarity_score=0.9),
            ),
            total_validated=1,
            total_excluded=0,
        ),
    )
    repo = TrackingItemFeatureRepository(
        records={"item-oor": build_item_record(item_id="item-oor", features=features)},
    )

    result, metrics = run_matching_from_context(context, item_repository=repo)

    clipped = 0.0 if out_of_range_value < 0.0 else 1.0
    assert result.entries[0].features["formality"].distance == pytest.approx(
        abs(0.8 - clipped),
    )
    assert metrics.feature_value_out_of_range_count == 1


# §14 No.9 入力 0 件
def test_run_feature_matching_succeeds_with_empty_validated_candidate() -> None:
    context = _sample_context(
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(),
            total_validated=0,
            total_excluded=0,
        ),
    )

    result, metrics = run_matching_from_context(context)

    assert result.entries == ()
    assert result.total_matched == 0
    assert metrics.feature_matcher_candidate_count == 0


def test_execute_with_empty_validated_candidate_does_not_raise_grs_rec_011() -> None:
    context = _sample_context(
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(),
            total_validated=0,
            total_excluded=0,
        ),
    )
    matcher, _ = build_matcher_with_repository(context)

    result_context = matcher.execute(context)

    assert result_context.feature_match_result.total_matched == 0  # type: ignore[attr-defined]
    assert "MOD-RECO-014" in result_context.completed_modules


# §14 No.10 全候補除外
def test_execute_succeeds_with_zero_candidates_when_all_items_are_excluded() -> None:
    context = _sample_context(
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(
                ValidatedRetrievalCandidateItem(item_id="missing-a", similarity_score=0.9),
                ValidatedRetrievalCandidateItem(item_id="missing-b", similarity_score=0.8),
            ),
            total_validated=2,
            total_excluded=0,
        ),
    )
    matcher, _ = build_matcher_with_repository(
        context,
        item_repository=TrackingItemFeatureRepository(records={}),
    )

    result_context = matcher.execute(context)

    assert result_context.feature_matcher_candidate_count == 0  # type: ignore[attr-defined]
    assert result_context.feature_match_result.total_matched == 0  # type: ignore[attr-defined]
    assert result_context.feature_match_result.total_excluded == 2  # type: ignore[attr-defined]


# §14 No.12 meaning_distance 常時
def test_run_feature_matching_sets_meaning_distance_for_every_matched_candidate() -> None:
    context = _sample_context()
    result, _ = run_matching_from_context(context)

    assert len(result.entries) == 2
    for entry in result.entries:
        assert entry.meaning_distance >= 0.0


# §14 No.13 avoid_similarity
def test_run_feature_matching_omits_avoid_similarity_when_all_avoid_delta_zero() -> None:
    context = _sample_context(internal_estimate=_sample_internal_estimate())
    result, _ = run_matching_from_context(context)

    for entry in result.entries:
        assert entry.avoid_similarity is None


def test_run_feature_matching_sets_avoid_similarity_when_avoid_delta_non_zero() -> None:
    avoid_delta = {axis: 0.0 for axis in MVP_FEATURE_CODES}
    avoid_delta["formality"] = 0.2
    context = _sample_context(
        internal_estimate=_sample_internal_estimate(avoid_delta=avoid_delta),
    )
    result, _ = run_matching_from_context(context)

    for entry in result.entries:
        assert entry.avoid_similarity is not None
        assert 0.0 <= entry.avoid_similarity <= 1.0


# §14 No.17 DB 読み取り（unit）
def test_run_feature_matching_fetches_item_features_with_semantic_config_version_id() -> None:
    context = _sample_context(
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(
                ValidatedRetrievalCandidateItem(item_id="item-001", similarity_score=0.9),
                ValidatedRetrievalCandidateItem(item_id="item-002", similarity_score=0.8),
            ),
            total_validated=2,
            total_excluded=0,
        ),
    )
    repo = TrackingItemFeatureRepository(
        records={
            "item-001": build_item_record(item_id="item-001"),
            "item-002": build_item_record(item_id="item-002"),
        },
    )

    run_matching_from_context(context, item_repository=repo)

    assert len(repo.fetch_calls) == 1
    item_ids, semantic_version_id = repo.fetch_calls[0]
    assert item_ids == ("item-001", "item-002")
    assert semantic_version_id == DEFAULT_SEMANTIC_CONFIG_VERSION_ID
