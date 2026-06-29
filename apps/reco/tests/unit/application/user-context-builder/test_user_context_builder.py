"""MOD-RECO-009 User Context Builder unit tests (module spec §14)."""

from __future__ import annotations

import json

import pytest

from conftest import (
    DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    _alternate_request,
    _minimal_request,
    _sample_context,
    _sample_semantic_extraction_result,
    _sample_user_feature,
    _sample_user_meaning_projection,
    _uniform_vector,
    _user_feature_rows_from_vector,
    build_builder_with_registered_run,
)
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.user_context_builder import (
    LAMBDA_CTX_FALLBACK,
    SURFACE_ERROR_CODE,
    UserContextBuildError,
    UserContextBuilder,
    assemble_user_context,
    build_context_query,
    build_embedding_query_text,
    build_preferred_query,
    build_semantic_query,
    finalize_lambda_ctx,
    guard_clip,
    resolve_lambda_ctx,
)
from reco.application.user_context_builder.in_memory_repository import (
    InMemoryLambdaContextRuleRepository,
)
from reco.domain import (
    NonPreferredCondition,
    OccasionCondition,
    PreferredCondition,
    RecommendationRequest,
    RelationshipCondition,
)
from reco.domain.semantic_extraction import ExtractedSemanticConcept
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def _retrieval_example_request() -> RecommendationRequest:
    return RecommendationRequest(
        request_id="req-retrieval-example",
        relationship=RelationshipCondition(
            relationship_code="boss",
            relationship_label="上司",
        ),
        occasion=OccasionCondition(
            occasion_code="thanks",
            occasion_label="お礼",
        ),
        preferred_condition=PreferredCondition(
            preferred_text="上品で感謝が伝わるもの",
        ),
        non_preferred_condition=NonPreferredCondition(
            non_preferred_text="カジュアルすぎるものは避けたい",
        ),
    )


# §14 No.1 正常系（context_query）
def test_build_context_query_from_relationship_and_occasion_labels() -> None:
    relationship = RelationshipCondition(
        relationship_code="lover",
        relationship_label="恋人",
    )
    occasion = OccasionCondition(
        occasion_code="birthday",
        occasion_label="誕生日",
    )

    context_query = build_context_query(relationship, occasion)

    assert context_query == "恋人 誕生日"


# §14 No.2 正常系（preferred_query）
def test_build_preferred_query_when_preferred_text_exists() -> None:
    preferred = PreferredCondition(preferred_text="実用的なギフト")

    preferred_query = build_preferred_query(preferred)

    assert preferred_query == "実用的なギフト"


# §14 No.3 正常系（semantic_query）
def test_build_semantic_query_orders_concepts_by_confidence_desc() -> None:
    concepts = (
        ExtractedSemanticConcept(
            concept_code="gift_low_confidence",
            confidence=0.2,
            input_intent="preferred",
            extraction_method="rule",
            source_type="preferred_text",
        ),
        ExtractedSemanticConcept(
            concept_code="gift_practical",
            confidence=0.9,
            input_intent="preferred",
            extraction_method="rule",
            source_type="preferred_text",
        ),
        ExtractedSemanticConcept(
            concept_code="gift_emotional",
            confidence=0.6,
            input_intent="preferred",
            extraction_method="rule",
            source_type="preferred_text",
        ),
    )

    semantic_query = build_semantic_query(concepts)

    assert semantic_query == "gift_practical gift_emotional gift_low_confidence"


# §14 No.4 正常系（embedding_query_text）
def test_build_embedding_query_text_matches_retrieval_section_9_3_pattern() -> None:
    request = _retrieval_example_request()
    assert request.relationship is not None
    assert request.occasion is not None

    embedding_query_text = build_embedding_query_text(
        relationship=request.relationship,
        occasion=request.occasion,
        preferred_text=request.preferred_condition.preferred_text
        if request.preferred_condition is not None
        else None,
        free_text=request.free_text,
    )

    assert embedding_query_text == "上司へのお礼。上品で感謝が伝わるもの。"


# §14 No.5 正常系（non_preferred 分離）
def test_assemble_user_context_keeps_non_preferred_out_of_embedding_query_text() -> None:
    request = _retrieval_example_request()
    extraction = _sample_semantic_extraction_result()

    user_context = assemble_user_context(
        request=request,
        concepts=extraction.concepts,
        lambda_ctx=0.5,
    )

    assert user_context.non_preferred_context.avoid_query_text == "カジュアルすぎるものは避けたい"
    assert "カジュアル" not in user_context.preferred_context.embedding_query_text
    assert "避けたい" not in user_context.preferred_context.embedding_query_text


# §14 No.6 正常系（lambda_ctx Rule）
def test_execute_uses_registered_lambda_ctx_rule() -> None:
    context = _sample_context(run_id="run-lambda-rule")
    rules = InMemoryLambdaContextRuleRepository()
    rules.register_rule(
        DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        "lover",
        "birthday",
        0.7,
    )
    builder, _, _, _ = build_builder_with_registered_run(
        context,
        lambda_ctx_rules=rules,
    )

    result_context = builder.execute(context)

    user_context = result_context.user_context  # type: ignore[attr-defined]
    user_meaning = result_context.user_meaning  # type: ignore[attr-defined]
    assert user_context.lambda_ctx == pytest.approx(0.7)
    assert user_meaning.lambda_ctx == pytest.approx(0.7)


# §14 No.7 正常系（lambda_ctx フォールバック）— unit 部分
def test_execute_uses_lambda_ctx_fallback_and_records_warning() -> None:
    context = _sample_context(run_id="run-lambda-fallback")
    builder, _, _, _ = build_builder_with_registered_run(context)

    result_context = builder.execute(context)

    user_context = result_context.user_context  # type: ignore[attr-defined]
    assert user_context.lambda_ctx == pytest.approx(LAMBDA_CTX_FALLBACK)
    warning_events = [
        event
        for event in result_context.error_log_events
        if event.get("level") == "warning"
    ]
    assert len(warning_events) == 1
    assert "fallback" in warning_events[0]["message"]
    assert warning_events[0]["trace_id"] == context.trace_id


# §14 No.10 正常系（出力受け渡し）
def test_execute_attaches_user_context_and_lambda_ctx_to_execution_context() -> None:
    context = _sample_context(run_id="run-handoff")
    builder, user_meaning_repo, _, _ = build_builder_with_registered_run(context)

    result_context = builder.execute(context)

    user_context = result_context.user_context  # type: ignore[attr-defined]
    user_meaning = result_context.user_meaning  # type: ignore[attr-defined]
    assert user_context.preferred_context.context_query
    assert user_meaning.lambda_ctx == pytest.approx(LAMBDA_CTX_FALLBACK)
    assert user_meaning.user_meaning_id == user_meaning_repo.ids_by_run[context.run_id]
    assert "MOD-RECO-009" in result_context.completed_modules


# §14 No.11 境界値（入力全空）
def test_execute_succeeds_with_minimal_context_when_preferred_inputs_empty() -> None:
    context = _sample_context(
        run_id="run-minimal-input",
        request=_minimal_request(),
    )
    builder, _, _, _ = build_builder_with_registered_run(context)

    result_context = builder.execute(context)

    user_context = result_context.user_context  # type: ignore[attr-defined]
    assert user_context.preferred_context.context_query == "上司 お礼"
    assert user_context.preferred_context.preferred_query is None
    assert user_context.preferred_context.free_text_query is None
    assert user_context.preferred_context.embedding_query_text == "上司へのお礼。"


# §14 No.12 境界値（lambda_ctx 端点）
@pytest.mark.parametrize("endpoint", [0.0, 1.0])
def test_resolve_lambda_ctx_preserves_endpoint_values(endpoint: float) -> None:
    rules = InMemoryLambdaContextRuleRepository()
    rules.register_rule(
        DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        "lover",
        "birthday",
        endpoint,
    )

    lambda_ctx, used_fallback = resolve_lambda_ctx(
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        relationship_code="lover",
        occasion_code="birthday",
        rule_repository=rules,
    )

    assert lambda_ctx == pytest.approx(endpoint)
    assert used_fallback is False


# §14 No.13 guard_clip
def test_finalize_lambda_ctx_clips_value_above_one() -> None:
    assert guard_clip(1.00001, 0.0, 1.0) == pytest.approx(1.0)
    assert finalize_lambda_ctx(1.00001) == pytest.approx(1.0)


# §14 No.14 NaN / Inf
@pytest.mark.parametrize(
    "bad_value",
    [float("nan"), float("inf"), float("-inf")],
)
def test_finalize_lambda_ctx_raises_for_non_finite_values(bad_value: float) -> None:
    with pytest.raises(UserContextBuildError) as exc_info:
        finalize_lambda_ctx(bad_value)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "non-finite" in exc_info.value.message


def test_resolve_lambda_ctx_raises_when_rule_value_is_nan() -> None:
    rules = InMemoryLambdaContextRuleRepository()
    rules.register_rule(
        DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        "lover",
        "birthday",
        float("nan"),
    )

    with pytest.raises(UserContextBuildError) as exc_info:
        resolve_lambda_ctx(
            semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            relationship_code="lover",
            occasion_code="birthday",
            rule_repository=rules,
        )

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.15 例外系（user_meaning 欠落）
def test_execute_raises_when_user_meaning_missing() -> None:
    context = _sample_context(run_id="run-no-meaning")
    builder, _, _, _ = build_builder_with_registered_run(context)
    del context.user_meaning  # type: ignore[attr-defined]

    with pytest.raises(UserContextBuildError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "user_meaning is required" in exc_info.value.message


# §14 No.16 例外系（DB 8 行欠落）— unit 部分
def test_execute_raises_when_db_has_fewer_than_eight_rows() -> None:
    features = _uniform_vector(0.5)
    context = _sample_context(
        run_id="run-db-row-shortage",
        user_feature=_sample_user_feature(run_id="run-db-row-shortage", features=features),
    )
    rows = _user_feature_rows_from_vector(features)[:7]
    builder, _, _, _ = build_builder_with_registered_run(
        context,
        user_feature_rows=rows,
    )

    with pytest.raises(UserContextBuildError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "row count mismatch" in exc_info.value.message


# §14 No.17 例外系（INSERT 重複）— in-memory unit 部分
def test_execute_raises_when_user_meaning_already_exists_for_run() -> None:
    context = _sample_context(run_id="run-duplicate-insert")
    builder, user_meaning_repo, user_features, run_validation = (
        build_builder_with_registered_run(context)
    )
    builder.execute(context)

    duplicate_context = _sample_context(run_id="run-duplicate-insert")
    duplicate_builder = UserContextBuilder(
        lambda_ctx_rules=InMemoryLambdaContextRuleRepository(),
        user_meaning_repo=user_meaning_repo,
        user_features=user_features,
        run_validation=run_validation,
        logger=ScaffoldRecoLogger(),
    )

    with pytest.raises(UserContextBuildError) as exc_info:
        duplicate_builder.execute(duplicate_context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "already exists" in exc_info.value.message


# §14 No.18 非再推定
def test_request_change_does_not_alter_projection_coordinates_when_user_meaning_unchanged() -> None:
    projection = _sample_user_meaning_projection(
        user_social=0.31,
        user_symbolic=0.72,
    )
    context_a = _sample_context(
        run_id="run-non-reestimate-a",
        user_meaning=projection,
    )
    context_b = _sample_context(
        run_id="run-non-reestimate-b",
        request=_alternate_request(),
        user_meaning=projection,
    )
    builder_a, _, _, _ = build_builder_with_registered_run(context_a)
    builder_b, _, _, _ = build_builder_with_registered_run(context_b)

    meaning_a = builder_a.execute(context_a).user_meaning  # type: ignore[attr-defined]
    meaning_b = builder_b.execute(context_b).user_meaning  # type: ignore[attr-defined]

    assert meaning_a.user_social == pytest.approx(meaning_b.user_social)
    assert meaning_a.user_symbolic == pytest.approx(meaning_b.user_symbolic)
    assert context_a.user_context.preferred_context.context_query != (  # type: ignore[attr-defined]
        context_b.user_context.preferred_context.context_query  # type: ignore[attr-defined]
    )


# §14 No.20 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(run_id="run-log")
    logger = ScaffoldRecoLogger()
    builder, _, _, _ = build_builder_with_registered_run(context, logger=logger)

    builder.execute(context)

    completion_logs = [
        record
        for record in logger.records
        if record.event == "user_context_build_completed"
    ]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == context.trace_id
    assert "context_query_len" in log_record.attributes
    assert "lambda_ctx" in log_record.attributes
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert "実用的なギフト" not in serialized


def test_execute_raises_when_lambda_ctx_already_set_on_projection() -> None:
    context = _sample_context(run_id="run-pre-set-lambda")
    projection = _sample_user_meaning_projection()
    object.__setattr__(projection, "lambda_ctx", 0.3)
    context.user_meaning = projection  # type: ignore[attr-defined]
    builder, _, _, _ = build_builder_with_registered_run(context)

    with pytest.raises(UserContextBuildError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "must not be set before MOD-RECO-009" in exc_info.value.message


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
    builder, _, _, _ = build_builder_with_registered_run(
        context,
        user_feature_rows=db_rows,
    )

    with pytest.raises(UserContextBuildError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "feature_normalization_version_id mismatch between context and DB" in exc_info.value.message
