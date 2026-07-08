"""MOD-RECO-008 User Meaning Projector unit tests (module spec §14)."""

from __future__ import annotations

import json
import math
from unittest.mock import patch

import pytest

from conftest import (
    DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    _alternate_request,
    _sample_context,
    _sample_user_feature,
    _uniform_vector,
    _user_feature_rows_from_vector,
    build_projector_with_registered_run,
)
from reco.application.user_meaning_projector import (
    InMemoryMeaningProjectionConfigRepository,
    SURFACE_ERROR_CODE,
    UserMeaningProjectionError,
    ensure_complete_normalized_features,
    project_user_meaning_coordinates,
)
from reco.application.user_meaning_projector.models import (
    MeaningProjectionWeights,
    UserFeatureRow,
)
from reco.domain.gift_meaning.features import (
    FEATURE_VALUE_MAX,
    FEATURE_VALUE_MIN,
    MVP_FEATURE_CODES,
    SOCIAL_FEATURE_CODES,
    SYMBOLIC_FEATURE_CODES,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def _social_features(
    *,
    formality: float,
    safety: float,
    brand_appropriateness: float,
) -> dict[str, float]:
    return {
        "formality": formality,
        "safety": safety,
        "brand_appropriateness": brand_appropriateness,
        "emotion": 0.0,
        "novelty": 0.0,
        "intimacy": 0.0,
        "symbolic_identity": 0.0,
        "story_richness": 0.0,
    }


def _symbolic_features(
    *,
    emotion: float,
    novelty: float,
    intimacy: float,
    symbolic_identity: float,
    story_richness: float,
) -> dict[str, float]:
    return {
        "formality": 0.0,
        "safety": 0.0,
        "brand_appropriateness": 0.0,
        "emotion": emotion,
        "novelty": novelty,
        "intimacy": intimacy,
        "symbolic_identity": symbolic_identity,
        "story_richness": story_richness,
    }


def _weighted_average(values: list[float], weights: list[float]) -> float:
    weight_sum = sum(weights)
    return sum(value * weight for value, weight in zip(values, weights, strict=True)) / weight_sum


# §14 No.1 正常系（Social 射影）
def test_social_projection_matches_gift_meaning_space_weighted_formula() -> None:
    features = _social_features(
        formality=0.8,
        safety=0.4,
        brand_appropriateness=0.6,
    )
    weights = MeaningProjectionWeights(
        w_formality=2.0,
        w_safety=1.0,
        w_brand_appropriateness=3.0,
    )
    expected_social = round(
        _weighted_average(
            [0.8, 0.4, 0.6],
            [2.0, 1.0, 3.0],
        ),
        4,
    )

    user_social, user_symbolic, stats = project_user_meaning_coordinates(features, weights)

    assert user_social == pytest.approx(expected_social)
    assert user_symbolic == pytest.approx(0.0)
    assert stats.guard_clip_applied_count == 0


# §14 No.2 正常系（Symbolic 射影）
def test_symbolic_projection_matches_gift_meaning_space_weighted_formula() -> None:
    features = _symbolic_features(
        emotion=0.2,
        novelty=0.4,
        intimacy=0.6,
        symbolic_identity=0.8,
        story_richness=1.0,
    )
    weights = MeaningProjectionWeights(
        w_emotion=1.0,
        w_novelty=2.0,
        w_intimacy=3.0,
        w_symbolic_identity=4.0,
        w_story_richness=5.0,
    )
    expected_symbolic = round(
        _weighted_average(
            [0.2, 0.4, 0.6, 0.8, 1.0],
            [1.0, 2.0, 3.0, 4.0, 5.0],
        ),
        4,
    )

    user_social, user_symbolic, stats = project_user_meaning_coordinates(features, weights)

    assert user_social == pytest.approx(0.0)
    assert user_symbolic == pytest.approx(expected_symbolic)
    assert stats.guard_clip_applied_count == 0


# §14 No.3 正常系（単純平均）
def test_project_user_meaning_coordinates_uses_simple_average_when_weights_unset() -> None:
    features = _uniform_vector(0.2)

    user_social, user_symbolic, stats = project_user_meaning_coordinates(
        features,
        MeaningProjectionWeights(),
    )

    assert user_social == pytest.approx(0.2)
    assert user_symbolic == pytest.approx(0.2)
    assert stats.guard_clip_applied_count == 0


# §14 No.4 正常系（加重平均）
def test_project_user_meaning_coordinates_normalizes_weighted_average() -> None:
    features = _social_features(formality=1.0, safety=0.0, brand_appropriateness=0.0)
    weights = MeaningProjectionWeights(
        w_formality=6.0,
        w_safety=2.0,
        w_brand_appropriateness=4.0,
    )
    expected_social = round(_weighted_average([1.0, 0.0, 0.0], [6.0, 2.0, 4.0]), 4)

    user_social, _, _ = project_user_meaning_coordinates(features, weights)

    assert user_social == pytest.approx(expected_social)
    assert user_social != pytest.approx(round(sum([1.0, 0.0, 0.0]) / 3, 4))


# §14 No.5 正常系（出力受け渡し）— unit 部分
def test_execute_attaches_user_meaning_to_execution_context() -> None:
    context = _sample_context(run_id="run-handoff")
    projector, _, _ = build_projector_with_registered_run(context)

    result_context = projector.execute(context)

    projection = result_context.user_meaning  # type: ignore[attr-defined]
    assert projection.user_social == pytest.approx(0.5)
    assert projection.user_symbolic == pytest.approx(0.5)
    assert projection.recommendation_run_id == context.run_id
    assert "MOD-RECO-008" in result_context.completed_modules


# §14 No.6 version 整合
def test_execute_preserves_feature_normalization_version_id_from_user_feature() -> None:
    context = _sample_context(run_id="run-version")
    projector, _, _ = build_projector_with_registered_run(context)

    result_context = projector.execute(context)

    projection = result_context.user_meaning  # type: ignore[attr-defined]
    user_feature = context.user_feature  # type: ignore[attr-defined]
    assert projection.feature_normalization_version_id == user_feature.feature_normalization_version_id
    assert projection.feature_normalization_version_id == DEFAULT_FEATURE_NORMALIZATION_VERSION_ID


# §14 No.7 境界値（全軸 0.0）
@pytest.mark.parametrize("group_axes", [SOCIAL_FEATURE_CODES, SYMBOLIC_FEATURE_CODES])
def test_project_user_meaning_coordinates_all_zero_axes(group_axes: tuple[str, ...]) -> None:
    features = _uniform_vector(0.0)

    user_social, user_symbolic, stats = project_user_meaning_coordinates(
        features,
        MeaningProjectionWeights(),
    )

    if group_axes == SOCIAL_FEATURE_CODES:
        assert user_social == pytest.approx(0.0)
    else:
        assert user_symbolic == pytest.approx(0.0)
    assert stats.guard_clip_applied_count == 0


def test_execute_projects_zero_user_meaning_when_all_axes_zero() -> None:
    features = _uniform_vector(0.0)
    context = _sample_context(
        run_id="run-all-zero",
        user_feature=_sample_user_feature(run_id="run-all-zero", features=features),
    )
    projector, _, _ = build_projector_with_registered_run(context)

    result_context = projector.execute(context)

    projection = result_context.user_meaning  # type: ignore[attr-defined]
    assert projection.user_social == pytest.approx(0.0)
    assert projection.user_symbolic == pytest.approx(0.0)


# §14 No.8 境界値（全軸 1.0）
def test_execute_projects_one_user_meaning_when_all_axes_one() -> None:
    features = _uniform_vector(1.0)
    context = _sample_context(
        run_id="run-all-one",
        user_feature=_sample_user_feature(run_id="run-all-one", features=features),
    )
    projector, _, _ = build_projector_with_registered_run(context)

    result_context = projector.execute(context)

    projection = result_context.user_meaning  # type: ignore[attr-defined]
    assert projection.user_social == pytest.approx(1.0)
    assert projection.user_symbolic == pytest.approx(1.0)


# §14 No.9 guard_clip 端点
def test_project_user_meaning_coordinates_clips_projection_above_one() -> None:
    features = _uniform_vector(0.5)
    weights = MeaningProjectionWeights()

    with patch(
        "reco.application.user_meaning_projector.projection_engine._project_group",
        side_effect=[1.00001, 0.5],
    ):
        user_social, user_symbolic, stats = project_user_meaning_coordinates(
            features,
            weights,
        )

    assert user_social == pytest.approx(1.0)
    assert user_symbolic == pytest.approx(0.5)
    assert stats.guard_clip_applied_count == 1


# §14 No.10 NaN / Inf
@pytest.mark.parametrize(
    "bad_value",
    [float("nan"), float("inf"), float("-inf")],
)
def test_project_user_meaning_coordinates_raises_for_non_finite_feature_values(
    bad_value: float,
) -> None:
    features = _uniform_vector(0.5)
    features["formality"] = bad_value

    with pytest.raises(UserMeaningProjectionError) as exc_info:
        project_user_meaning_coordinates(features, MeaningProjectionWeights())

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "non-finite" in exc_info.value.message


def test_project_user_meaning_coordinates_raises_when_projection_result_is_nan() -> None:
    features = _uniform_vector(0.5)

    with patch(
        "reco.application.user_meaning_projector.projection_engine._project_group",
        return_value=float("nan"),
    ):
        with pytest.raises(UserMeaningProjectionError) as exc_info:
            project_user_meaning_coordinates(features, MeaningProjectionWeights())

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.11 例外系（user_feature 欠落）
def test_execute_raises_when_user_feature_missing() -> None:
    context = _sample_context(run_id="run-no-user-feature")
    projector, _, _ = build_projector_with_registered_run(context)
    del context.user_feature  # type: ignore[attr-defined]

    with pytest.raises(UserMeaningProjectionError) as exc_info:
        projector.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "user_feature is required" in exc_info.value.message


# §14 No.12 例外系（8 軸キー欠落）
def test_ensure_complete_normalized_features_raises_when_axis_missing() -> None:
    incomplete = {"formality": 0.5}

    with pytest.raises(UserMeaningProjectionError) as exc_info:
        ensure_complete_normalized_features(incomplete)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "missing axes" in exc_info.value.message


def test_execute_raises_when_db_row_axis_missing() -> None:
    features = _uniform_vector(0.5)
    context = _sample_context(
        run_id="run-db-axis-missing",
        user_feature=_sample_user_feature(run_id="run-db-axis-missing", features=features),
    )
    rows = _user_feature_rows_from_vector(features)
    incomplete_rows = tuple(row for row in rows if row.feature_code != "story_richness")
    projector, _, _ = build_projector_with_registered_run(
        context,
        user_feature_rows=incomplete_rows,
    )

    with pytest.raises(UserMeaningProjectionError) as exc_info:
        projector.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "row count mismatch" in exc_info.value.message


# §14 No.13 例外系（値域外）
@pytest.mark.parametrize("bad_value", [-0.01, 1.01])
def test_ensure_complete_normalized_features_raises_when_value_out_of_range(
    bad_value: float,
) -> None:
    features = _uniform_vector(0.5)
    features["emotion"] = bad_value

    with pytest.raises(UserMeaningProjectionError) as exc_info:
        ensure_complete_normalized_features(features)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "out of range" in exc_info.value.message


# §14 No.14 例外系（DB 8 行欠落）— unit 部分
def test_execute_raises_when_db_has_fewer_than_eight_rows() -> None:
    features = _uniform_vector(0.5)
    context = _sample_context(
        run_id="run-db-row-shortage",
        user_feature=_sample_user_feature(run_id="run-db-row-shortage", features=features),
    )
    rows = _user_feature_rows_from_vector(features)[:7]
    projector, _, _ = build_projector_with_registered_run(
        context,
        user_feature_rows=rows,
    )

    with pytest.raises(UserMeaningProjectionError) as exc_info:
        projector.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "row count mismatch" in exc_info.value.message


# §14 No.15 例外系（version 不一致）
def test_execute_raises_when_db_version_ids_differ_across_rows() -> None:
    features = _uniform_vector(0.5)
    context = _sample_context(
        run_id="run-db-version-mismatch",
        user_feature=_sample_user_feature(run_id="run-db-version-mismatch", features=features),
    )
    rows = list(_user_feature_rows_from_vector(features))
    rows[0] = UserFeatureRow(
        feature_code=rows[0].feature_code,
        feature_value=rows[0].feature_value,
        feature_normalization_version_id="fnv-other",
    )
    projector, _, _ = build_projector_with_registered_run(
        context,
        user_feature_rows=tuple(rows),
    )

    with pytest.raises(UserMeaningProjectionError) as exc_info:
        projector.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "feature_normalization_version_id mismatch across DB rows" in exc_info.value.message


def test_execute_raises_when_context_version_differs_from_db() -> None:
    features = _uniform_vector(0.5)
    context = _sample_context(
        run_id="run-context-db-version",
        user_feature=_sample_user_feature(
            run_id="run-context-db-version",
            features=features,
            feature_normalization_version_id="fnv-context",
        ),
    )
    db_rows = _user_feature_rows_from_vector(
        features,
        feature_normalization_version_id=DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    )
    projector, _, _ = build_projector_with_registered_run(
        context,
        user_feature_rows=db_rows,
    )

    with pytest.raises(UserMeaningProjectionError) as exc_info:
        projector.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "feature_normalization_version_id mismatch between context and DB" in exc_info.value.message


# §14 No.16 例外系（Run 不整合）
def test_execute_raises_when_run_is_not_registered() -> None:
    context = _sample_context(run_id="run-missing")
    projector, _, _ = build_projector_with_registered_run(context, register_run=False)

    with pytest.raises(UserMeaningProjectionError) as exc_info:
        projector.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "not found" in exc_info.value.message


def test_execute_raises_when_run_version_mismatch() -> None:
    context = _sample_context(run_id="run-version-mismatch")
    projector, _, run_validation = build_projector_with_registered_run(context)
    run_validation.register_run("run-version-mismatch", "other-version")

    with pytest.raises(UserMeaningProjectionError) as exc_info:
        projector.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "mismatch" in exc_info.value.message


def test_execute_raises_when_projection_weights_not_found() -> None:
    context = _sample_context(run_id="run-no-weights")
    projection_config = InMemoryMeaningProjectionConfigRepository(
        semantic_config_version_id="missing-version",
    )
    projector, _, _ = build_projector_with_registered_run(
        context,
        projection_config=projection_config,
    )

    with pytest.raises(UserMeaningProjectionError) as exc_info:
        projector.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "projection weights not found" in exc_info.value.message


# §14 No.17 非再推定
def test_request_change_does_not_alter_projection_when_user_feature_unchanged() -> None:
    features = _uniform_vector(0.42)
    context_a = _sample_context(
        run_id="run-non-reestimate-a",
        user_feature=_sample_user_feature(run_id="run-non-reestimate-a", features=features),
    )
    context_b = _sample_context(
        run_id="run-non-reestimate-b",
        request=_alternate_request(),
        user_feature=_sample_user_feature(run_id="run-non-reestimate-b", features=features),
    )
    projector_a, _, _ = build_projector_with_registered_run(context_a)
    projector_b, _, _ = build_projector_with_registered_run(context_b)

    projection_a = projector_a.execute(context_a).user_meaning  # type: ignore[attr-defined]
    projection_b = projector_b.execute(context_b).user_meaning  # type: ignore[attr-defined]

    assert projection_a.user_social == pytest.approx(projection_b.user_social)
    assert projection_a.user_symbolic == pytest.approx(projection_b.user_symbolic)


# §14 No.18 lambda_ctx 非生成
def test_execute_does_not_set_lambda_ctx_on_user_meaning() -> None:
    context = _sample_context(run_id="run-no-lambda")
    projector, _, _ = build_projector_with_registered_run(context)

    result_context = projector.execute(context)

    projection = result_context.user_meaning  # type: ignore[attr-defined]
    assert getattr(projection, "lambda_ctx", None) is None


# §14 No.19 DB 非書込
def test_execute_does_not_mutate_user_feature_read_repository() -> None:
    context = _sample_context(run_id="run-no-write")
    projector, user_features, _ = build_projector_with_registered_run(context)
    rows_before = user_features.rows_by_run[context.run_id]

    projector.execute(context)

    rows_after = user_features.rows_by_run[context.run_id]
    assert rows_before == rows_after
    assert len(rows_after) == 8


# §14 No.21 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(run_id="run-log")
    logger = ScaffoldRecoLogger()
    projector, _, _ = build_projector_with_registered_run(context, logger=logger)

    projector.execute(context)

    completion_logs = [
        record
        for record in logger.records
        if record.event == "user_meaning_projection_completed"
    ]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == context.trace_id
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized


def test_execute_logs_guard_clip_count_when_clipping_applies() -> None:
    context = _sample_context(run_id="run-log-clip")
    logger = ScaffoldRecoLogger()
    projector, _, _ = build_projector_with_registered_run(context, logger=logger)

    with patch(
        "reco.application.user_meaning_projector.projection_engine._project_group",
        side_effect=[1.00001, 0.5],
    ):
        projector.execute(context)

    log_record = next(
        record
        for record in logger.records
        if record.event == "user_meaning_projection_completed"
    )
    assert log_record.attributes["guard_clip_applied_count"] == 1


def test_projection_engine_rejects_out_of_range_values_before_execute() -> None:
    features = _uniform_vector(0.5)
    features["formality"] = FEATURE_VALUE_MAX + 0.001
    assert math.isfinite(features["formality"])
    assert features["formality"] > FEATURE_VALUE_MAX

    with pytest.raises(UserMeaningProjectionError):
        ensure_complete_normalized_features(features)
