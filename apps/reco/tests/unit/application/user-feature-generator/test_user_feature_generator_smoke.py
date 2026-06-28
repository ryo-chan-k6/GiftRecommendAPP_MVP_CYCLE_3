"""MOD-RECO-007 User Feature Generator minimal smoke tests."""

from __future__ import annotations

import pytest

from conftest import (
    _sample_context,
    _sample_external_estimate,
    _sample_internal_estimate,
    _uniform_vector,
    build_generator_with_registered_run,
)
from reco.application.user_feature_generator import (
    SURFACE_ERROR_CODE,
    UserFeatureGenerationError,
    merge_user_feature_raw,
    normalize_user_features,
)
from reco.application.user_feature_generator.models import FeatureNormalizationParameters
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES


def test_merge_user_feature_raw_adds_external_and_internal() -> None:
    external = _uniform_vector(0.6)
    internal = _uniform_vector(0.1)
    merged = merge_user_feature_raw(external, internal)
    for axis in MVP_FEATURE_CODES:
        assert merged[axis] == pytest.approx(0.7)


def test_normalize_user_features_center_raw_yields_half() -> None:
    parameters = FeatureNormalizationParameters(
        center_feature=0.5,
        k_feature=4.0,
        normalization_method="sigmoid",
    )
    normalized, stats = normalize_user_features(_uniform_vector(0.5), parameters)
    for axis in MVP_FEATURE_CODES:
        assert normalized[axis] == pytest.approx(0.5)
    assert stats.raw_out_of_range_count == 0
    assert stats.guard_clip_applied_count == 0


def test_execute_generates_user_feature_and_inserts_eight_rows() -> None:
    context = _sample_context(
        external_feature_estimate=_sample_external_estimate(
            external_feature_raw=_uniform_vector(0.5),
        ),
        internal_feature_estimate=_sample_internal_estimate(
            internal_feature_delta=_uniform_vector(0.0),
        ),
    )
    generator, user_features = build_generator_with_registered_run(context)

    updated = generator.execute(context)

    user_feature = updated.user_feature
    assert user_feature is not None
    assert user_feature.recommendation_run_id == context.run_id
    assert user_feature.features["formality"] == pytest.approx(0.5)
    assert user_feature.user_feature_raw["formality"] == pytest.approx(0.5)
    assert len(user_features.inserted_rows) == 8
    assert all(row.source_type == "aggregated" for row in user_features.inserted_rows)
    assert "MOD-RECO-007" in updated.completed_modules


def test_execute_fails_when_external_feature_estimate_missing() -> None:
    context = _sample_context()
    context.external_feature_estimate = None
    generator, _ = build_generator_with_registered_run(context)

    with pytest.raises(UserFeatureGenerationError) as exc_info:
        generator.generate(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
