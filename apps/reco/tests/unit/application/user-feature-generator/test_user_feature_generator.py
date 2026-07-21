"""MOD-RECO-007 User Feature Generator unit tests (module spec §14)."""

from __future__ import annotations

import json
import math
from unittest.mock import patch

import pytest

from conftest import (
    _sample_context,
    _sample_external_estimate,
    _sample_internal_estimate,
    _uniform_vector,
    build_generator_with_registered_run,
)
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.user_feature_generator import (
    DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    SURFACE_ERROR_CODE,
    UserFeature,
    UserFeatureGenerationError,
    merge_user_feature_raw,
    normalize_user_features,
)
from reco.application.user_feature_generator.models import FeatureNormalizationParameters
from reco.application.user_feature_generator.rule_engine import (
    ensure_complete_feature_vector,
    guard_clip,
)
from reco.domain import (
    NonPreferredCondition,
    OccasionCondition,
    PreferredCondition,
    RecommendationRequest,
    RelationshipCondition,
)
from reco.domain.gift_meaning.features import FEATURE_VALUE_MAX, FEATURE_VALUE_MIN, MVP_FEATURE_CODES
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

DEFAULT_PARAMETERS = FeatureNormalizationParameters(
    center_feature=0.5,
    k_feature=4.0,
    normalization_method="sigmoid",
)


def _expected_sigmoid_normalized(raw: float) -> float:
    sigmoid_input = DEFAULT_PARAMETERS.k_feature * (raw - DEFAULT_PARAMETERS.center_feature)
    if sigmoid_input >= 0:
        sigmoid_value = 1.0 / (1.0 + math.exp(-sigmoid_input))
    else:
        exp_x = math.exp(sigmoid_input)
        sigmoid_value = exp_x / (1.0 + exp_x)
    clipped = guard_clip(sigmoid_value, 0.0, 1.0)
    return round(clipped, 6)


def _assert_feature_vector(actual: dict[str, float], expected: dict[str, float]) -> None:
    for axis in MVP_FEATURE_CODES:
        assert actual[axis] == pytest.approx(expected[axis])


# §14 No.1 正常系（統合式）
def test_merge_user_feature_raw_adds_external_and_internal_per_axis() -> None:
    external = {axis: 0.6 for axis in MVP_FEATURE_CODES}
    internal = {axis: 0.1 for axis in MVP_FEATURE_CODES}

    merged = merge_user_feature_raw(external, internal)

    for axis in MVP_FEATURE_CODES:
        assert merged[axis] == pytest.approx(0.7)


def test_execute_computes_user_feature_raw_from_external_and_internal() -> None:
    external_raw = _uniform_vector(0.6)
    internal_delta = _uniform_vector(0.1)
    context = _sample_context(
        run_id="run-integration-formula",
        external_feature_estimate=_sample_external_estimate(
            external_feature_raw=external_raw,
        ),
        internal_feature_estimate=_sample_internal_estimate(
            internal_feature_delta=internal_delta,
        ),
    )
    generator, _ = build_generator_with_registered_run(context)

    updated = generator.execute(context)

    user_feature = updated.user_feature
    assert user_feature is not None
    _assert_feature_vector(user_feature.user_feature_raw, _uniform_vector(0.7))


# §14 No.2 正常系（sigmoid）
@pytest.mark.parametrize(
    "raw_value",
    [0.0, 0.3, 0.5, 0.7, 1.0, 1.05, 1.3],
)
def test_normalize_user_features_matches_feature_rule_sigmoid_formula(
    raw_value: float,
) -> None:
    raw = _uniform_vector(raw_value)
    expected = _uniform_vector(_expected_sigmoid_normalized(raw_value))

    normalized, _ = normalize_user_features(raw, DEFAULT_PARAMETERS)

    _assert_feature_vector(normalized, expected)


# §14 No.3 正常系（8 軸完備）
def test_execute_normalizes_all_eight_axes_within_valid_range() -> None:
    context = _sample_context(
        run_id="run-eight-axes",
        external_feature_estimate=_sample_external_estimate(
            external_feature_raw={
                "formality": 0.2,
                "safety": 0.4,
                "brand_appropriateness": 0.6,
                "emotion": 0.8,
                "novelty": 1.0,
                "intimacy": 0.3,
                "symbolic_identity": 0.7,
                "story_richness": 0.9,
            },
        ),
    )
    generator, _ = build_generator_with_registered_run(context)

    updated = generator.execute(context)

    user_feature = updated.user_feature
    assert user_feature is not None
    assert set(user_feature.features) == set(MVP_FEATURE_CODES)
    for value in user_feature.features.values():
        assert FEATURE_VALUE_MIN <= value <= FEATURE_VALUE_MAX


# §14 No.4 正常系（内部 Delta ゼロ）
def test_execute_succeeds_with_zero_internal_delta_using_external_raw_only() -> None:
    external_raw = _uniform_vector(0.65)
    context = _sample_context(
        run_id="run-zero-delta",
        external_feature_estimate=_sample_external_estimate(
            external_feature_raw=external_raw,
        ),
        internal_feature_estimate=_sample_internal_estimate(
            internal_feature_delta=_uniform_vector(0.0),
        ),
    )
    generator, user_features = build_generator_with_registered_run(context)

    updated = generator.execute(context)

    user_feature = updated.user_feature
    assert user_feature is not None
    assert user_feature.user_feature_raw["formality"] == pytest.approx(0.65)
    assert len(user_features.inserted_rows) == 8


# §14 No.5 正常系（DB INSERT）— unit 部分
def test_execute_inserts_eight_rows_with_matching_values_and_version() -> None:
    context = _sample_context(
        run_id="run-db-insert",
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
    assert len(user_features.inserted_rows) == 8
    assert all(row.source_type == "aggregated" for row in user_features.inserted_rows)
    assert all(
        row.feature_normalization_version_id == DEFAULT_FEATURE_NORMALIZATION_VERSION_ID
        for row in user_features.inserted_rows
    )
    for row in user_features.inserted_rows:
        assert row.feature_value == pytest.approx(user_feature.features[row.feature_code])
        assert row.recommendation_run_id == context.run_id


# §14 No.7 version 整合
def test_execute_sets_feature_normalization_version_id_from_binding() -> None:
    context = _sample_context(run_id="run-version")
    generator, _ = build_generator_with_registered_run(context)

    updated = generator.execute(context)

    user_feature = updated.user_feature
    assert user_feature is not None
    assert user_feature.feature_normalization_version_id == DEFAULT_FEATURE_NORMALIZATION_VERSION_ID
    assert user_feature.semantic_config_version_id == DEFAULT_SEMANTIC_CONFIG_VERSION_ID


# §14 No.8 境界値（raw 超域）
def test_execute_clamps_out_of_range_raw_via_sigmoid_and_guard_clip() -> None:
    context = _sample_context(
        run_id="run-raw-over-max",
        external_feature_estimate=_sample_external_estimate(
            external_feature_raw=_uniform_vector(1.3),
        ),
    )
    generator, user_features = build_generator_with_registered_run(context)

    updated = generator.execute(context)

    user_feature = updated.user_feature
    assert user_feature is not None
    expected = _expected_sigmoid_normalized(1.3)
    assert user_feature.features["formality"] == pytest.approx(expected)
    assert all(
        FEATURE_VALUE_MIN <= row.feature_value <= FEATURE_VALUE_MAX
        for row in user_features.inserted_rows
    )


# §14 No.9 境界値（center = 0.5）
def test_normalize_user_features_center_raw_yields_half() -> None:
    normalized, stats = normalize_user_features(_uniform_vector(0.5), DEFAULT_PARAMETERS)

    for axis in MVP_FEATURE_CODES:
        assert normalized[axis] == pytest.approx(0.5)
    assert stats.raw_out_of_range_count == 0
    assert stats.guard_clip_applied_count == 0


# §14 No.9a guard_clip 端点
def test_normalize_user_features_clips_sigmoid_output_above_one() -> None:
    raw = _uniform_vector(0.5)

    with patch(
        "reco.application.user_feature_generator.rule_engine.sigmoid",
        return_value=1.0000001,
    ):
        normalized, stats = normalize_user_features(raw, DEFAULT_PARAMETERS)

    assert normalized["formality"] == pytest.approx(1.0)
    assert stats.guard_clip_applied_count == 8


# §14 No.9b NaN / Inf
def test_normalize_user_features_raises_when_raw_is_nan() -> None:
    raw = _uniform_vector(0.5)
    raw["formality"] = float("nan")

    with pytest.raises(UserFeatureGenerationError) as exc_info:
        normalize_user_features(raw, DEFAULT_PARAMETERS)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_normalize_user_features_raises_when_sigmoid_is_infinite() -> None:
    raw = _uniform_vector(0.5)

    with patch(
        "reco.application.user_feature_generator.rule_engine.sigmoid",
        return_value=float("inf"),
    ):
        with pytest.raises(UserFeatureGenerationError) as exc_info:
            normalize_user_features(raw, DEFAULT_PARAMETERS)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.10 例外系（estimate 欠落）
def test_generate_raises_when_external_feature_estimate_missing() -> None:
    context = _sample_context(run_id="run-no-external")
    context.external_feature_estimate = None
    generator, _ = build_generator_with_registered_run(context)

    with pytest.raises(UserFeatureGenerationError) as exc_info:
        generator.generate(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_generate_raises_when_internal_feature_estimate_missing() -> None:
    context = _sample_context(run_id="run-no-internal")
    context.internal_feature_estimate = None  # type: ignore[attr-defined]
    generator, _ = build_generator_with_registered_run(context)

    with pytest.raises(UserFeatureGenerationError) as exc_info:
        generator.generate(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.11 例外系（8 軸キー欠落）
def test_merge_user_feature_raw_raises_when_external_axis_missing() -> None:
    incomplete = {"formality": 0.5}

    with pytest.raises(UserFeatureGenerationError) as exc_info:
        merge_user_feature_raw(incomplete, _uniform_vector(0.0))

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "external_feature_raw missing axes" in exc_info.value.message


def test_merge_user_feature_raw_raises_when_internal_axis_missing() -> None:
    incomplete = {"formality": 0.1}

    with pytest.raises(UserFeatureGenerationError) as exc_info:
        merge_user_feature_raw(_uniform_vector(0.5), incomplete)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "internal_feature_delta missing axes" in exc_info.value.message


def test_ensure_complete_feature_vector_raises_for_missing_axes() -> None:
    with pytest.raises(UserFeatureGenerationError) as exc_info:
        ensure_complete_feature_vector({"formality": 0.5}, vector_name="test_vector")

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.12 例外系（正規化 Rule 欠落）
def test_generate_raises_when_normalization_binding_missing() -> None:
    from reco.application.user_feature_generator import InMemoryNormalizationRuleRepository

    context = _sample_context(run_id="run-no-rule")
    generator, _ = build_generator_with_registered_run(
        context,
        normalization_rules=InMemoryNormalizationRuleRepository(binding=None),
    )

    with pytest.raises(UserFeatureGenerationError) as exc_info:
        generator.generate(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "normalization_rule not found" in exc_info.value.message


# §14 No.13 例外系（user_semantic 未存在）
def test_generate_raises_when_user_semantic_not_registered() -> None:
    context = _sample_context(run_id="run-no-user-semantic")
    generator, _ = build_generator_with_registered_run(
        context,
        register_user_semantic=False,
    )

    with pytest.raises(UserFeatureGenerationError) as exc_info:
        generator.generate(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "user_semantic not found" in exc_info.value.message


# §14 No.14 例外系（Run 不整合）
def test_generate_raises_when_run_is_not_registered() -> None:
    context = _sample_context(run_id="run-missing")
    generator, _ = build_generator_with_registered_run(context, register_run=False)

    with pytest.raises(UserFeatureGenerationError) as exc_info:
        generator.generate(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "not found" in exc_info.value.message


def test_generate_raises_when_run_version_mismatch() -> None:
    context = _sample_context(run_id="run-mismatch")
    generator, _ = build_generator_with_registered_run(context)
    generator.run_validation.register_run("run-mismatch", "other-version")

    with pytest.raises(UserFeatureGenerationError) as exc_info:
        generator.generate(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "mismatch" in exc_info.value.message


# §14 No.15 例外系（INSERT 失敗）
def test_generate_raises_when_user_feature_insert_fails() -> None:
    from reco.application.user_feature_generator import InMemoryUserFeatureRepository

    context = _sample_context(run_id="run-insert-fail")
    failing_repo = InMemoryUserFeatureRepository(should_fail_on_insert=True)
    generator, _ = build_generator_with_registered_run(
        context,
        user_features=failing_repo,
    )

    with pytest.raises(UserFeatureGenerationError) as exc_info:
        generator.generate(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "insert failed" in exc_info.value.message


# §14 No.16 非再推定
def test_request_change_does_not_alter_user_feature_when_estimates_unchanged() -> None:
    external = _sample_external_estimate(external_feature_raw=_uniform_vector(0.55))
    internal = _sample_internal_estimate(internal_feature_delta=_uniform_vector(0.05))
    request_a = RecommendationRequest(
        request_id="req-a",
        relationship=RelationshipCondition(relationship_code="lover"),
        occasion=OccasionCondition(occasion_code="birthday"),
    )
    request_b = RecommendationRequest(
        request_id="req-b",
        relationship=RelationshipCondition(relationship_code="lover"),
        occasion=OccasionCondition(occasion_code="birthday"),
        preferred_condition=PreferredCondition(preferred_text="別テキスト"),
        non_preferred_condition=NonPreferredCondition(
            non_preferred_text="避けたい特徴",
        ),
        free_text="追加の自由記述",
    )
    context_a = _sample_context(
        request=request_a,
        run_id="run-non-reestimate-a",
        external_feature_estimate=external,
        internal_feature_estimate=internal,
    )
    context_b = _sample_context(
        request=request_b,
        run_id="run-non-reestimate-b",
        external_feature_estimate=external,
        internal_feature_estimate=internal,
    )
    generator_a, _ = build_generator_with_registered_run(context_a)
    generator_b, _ = build_generator_with_registered_run(context_b)

    feature_a = generator_a.execute(context_a).user_feature
    feature_b = generator_b.execute(context_b).user_feature

    assert feature_a is not None
    assert feature_b is not None
    _assert_feature_vector(feature_a.features, feature_b.features)
    _assert_feature_vector(feature_a.user_feature_raw, feature_b.user_feature_raw)


# §14 No.17 raw 非永続化
def test_execute_does_not_persist_user_feature_raw_to_insert_rows() -> None:
    context = _sample_context(
        run_id="run-no-raw-persist",
        external_feature_estimate=_sample_external_estimate(
            external_feature_raw=_uniform_vector(0.62),
        ),
        internal_feature_estimate=_sample_internal_estimate(
            internal_feature_delta=_uniform_vector(0.03),
        ),
    )
    generator, user_features = build_generator_with_registered_run(context)

    updated = generator.execute(context)

    user_feature = updated.user_feature
    assert user_feature is not None
    assert user_feature.user_feature_raw["formality"] == pytest.approx(0.65)
    for row in user_features.inserted_rows:
        assert row.feature_value == pytest.approx(
            user_feature.features[row.feature_code],
        )
        assert row.feature_value != pytest.approx(0.65)


# §14 No.19 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(run_id="run-log")
    logger = ScaffoldRecoLogger()
    generator, _ = build_generator_with_registered_run(context, logger=logger)

    generator.execute(context)

    completion_logs = [
        record
        for record in logger.records
        if record.event == "user_feature_generation_completed"
    ]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == context.trace_id
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized


# §14 No.21 出力受け渡し
def test_execute_attaches_user_feature_to_execution_context() -> None:
    context = _sample_context(run_id="run-handoff")
    generator, _ = build_generator_with_registered_run(context)

    updated = generator.execute(context)

    user_feature = updated.user_feature
    assert isinstance(user_feature, UserFeature)
    assert user_feature.recommendation_run_id == context.run_id
    assert set(user_feature.features) == set(MVP_FEATURE_CODES)
    assert "MOD-RECO-007" in updated.completed_modules
