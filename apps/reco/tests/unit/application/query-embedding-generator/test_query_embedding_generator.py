"""MOD-RECO-010 Query Embedding Generator unit tests (module spec §14)."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field

import pytest

from conftest import (
    EMBEDDING_DIMENSIONS,
    _sample_context,
    _sample_user_context,
    build_generator_with_registered_run,
)
from reco.application.config_version_resolver import DEFAULT_EMBEDDING_MODEL_VERSION_ID
from reco.application.query_embedding_generator import (
    DETAIL_ERROR_GENERATION_FAILED,
    DETAIL_ERROR_RATE_LIMIT,
    DETAIL_ERROR_TIMEOUT,
    EmbeddingGenerationResult,
    InMemoryRunValidation,
    QueryEmbeddingGenerationError,
    QueryEmbeddingGenerator,
    SURFACE_ERROR_CODE,
    validate_embedding_vector,
)
from reco.application.user_context_builder.models import (
    NonPreferredContext,
    PreferredContext,
    UserContext,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def _uniform_vector(value: float, *, dimensions: int = EMBEDDING_DIMENSIONS) -> tuple[float, ...]:
    return tuple(value for _ in range(dimensions))


def _minimal_user_context(
    *,
    embedding_query_text: str = "上司へのお礼。",
) -> UserContext:
    return UserContext(
        preferred_context=PreferredContext(
            context_query="上司 お礼",
            embedding_query_text=embedding_query_text,
            preferred_query=None,
        ),
        non_preferred_context=NonPreferredContext(avoid_query_text=None),
        lambda_ctx=0.5,
    )


@dataclass
class StubEmbeddingApiClient:
    """Configurable Embedding API stub for error-path unit tests."""

    response: EmbeddingGenerationResult | None = None
    error: Exception | None = None
    generate_calls: list[dict[str, object]] = field(default_factory=list)

    def generate(
        self,
        text: str,
        model_version_id: str,
        metadata: dict[str, str],
    ) -> EmbeddingGenerationResult:
        self.generate_calls.append(
            {
                "text": text,
                "model_version_id": model_version_id,
                "metadata": dict(metadata),
            },
        )
        if self.error is not None:
            raise self.error
        if self.response is None:
            raise RuntimeError("stub response not configured")
        return self.response


# §14 No.1 正常系（preferred）
def test_execute_generates_1536_dim_preferred_embedding() -> None:
    context = _sample_context(run_id="run-preferred-dim")
    generator, _, _ = build_generator_with_registered_run(context)

    result_context = generator.execute(context)

    query_embedding = result_context.query_embedding  # type: ignore[attr-defined]
    preferred = query_embedding.preferred_embedding
    assert len(preferred.vector) == EMBEDDING_DIMENSIONS
    assert preferred.dimensions == EMBEDDING_DIMENSIONS
    assert all(math.isfinite(value) for value in preferred.vector)


# §14 No.2 正常系（model version）
def test_execute_sets_model_version_id_from_config_versions() -> None:
    model_version_id = "emb-model-v2"
    context = _sample_context(
        run_id="run-model-version",
        embedding_model_version_id=model_version_id,
    )
    generator, client, _ = build_generator_with_registered_run(context)

    result_context = generator.execute(context)

    preferred = result_context.query_embedding.preferred_embedding  # type: ignore[attr-defined]
    assert preferred.model_version_id == model_version_id
    assert client.generate_calls[0]["model_version_id"] == model_version_id


# §14 No.3 正常系（出力受け渡し）— unit 部分
def test_execute_attaches_query_embedding_to_execution_context() -> None:
    context = _sample_context(run_id="run-handoff")
    generator, _, _ = build_generator_with_registered_run(context)

    result_context = generator.execute(context)

    query_embedding = result_context.query_embedding  # type: ignore[attr-defined]
    assert query_embedding.preferred_embedding.vector
    assert query_embedding.preferred_embedding.source_text_hash
    assert "MOD-RECO-010" in result_context.completed_modules


# §14 No.4 正常系（API 1 回）
def test_execute_calls_embedding_api_once_even_with_avoid_query_text() -> None:
    context = _sample_context(run_id="run-single-api")
    generator, client, _ = build_generator_with_registered_run(context)

    generator.execute(context)

    assert len(client.generate_calls) == 1


# §14 No.5 正常系（non_preferred 非生成）
def test_execute_does_not_include_non_preferred_embedding() -> None:
    context = _sample_context(run_id="run-no-non-preferred")
    generator, _, _ = build_generator_with_registered_run(context)

    result_context = generator.execute(context)

    query_embedding = result_context.query_embedding  # type: ignore[attr-defined]
    assert not hasattr(query_embedding, "non_preferred_embedding")


# §14 No.7 テキスト再構成なし
def test_execute_passes_embedding_query_text_unchanged_to_api() -> None:
    embedding_query_text = "上司へのお礼。上品で感謝が伝わるもの。"
    context = _sample_context(
        run_id="run-text-unchanged",
        user_context=_sample_user_context(embedding_query_text=embedding_query_text),
    )
    generator, client, _ = build_generator_with_registered_run(context)

    generator.execute(context)

    assert client.generate_calls[0]["text"] == embedding_query_text


# §14 No.8 境界値（最小文脈）
def test_execute_succeeds_with_minimal_short_embedding_query_text() -> None:
    embedding_query_text = "上司へのお礼。"
    context = _sample_context(
        run_id="run-minimal-context",
        user_context=_minimal_user_context(embedding_query_text=embedding_query_text),
    )
    generator, client, _ = build_generator_with_registered_run(context)

    result_context = generator.execute(context)

    preferred = result_context.query_embedding.preferred_embedding  # type: ignore[attr-defined]
    assert client.generate_calls[0]["text"] == embedding_query_text
    assert len(preferred.vector) == EMBEDDING_DIMENSIONS


# §14 No.9 境界値（長文）
def test_execute_succeeds_with_truncated_512_char_embedding_query_text() -> None:
    embedding_query_text = "あ" * 512
    context = _sample_context(
        run_id="run-long-text",
        user_context=_sample_user_context(embedding_query_text=embedding_query_text),
    )
    generator, client, _ = build_generator_with_registered_run(context)

    result_context = generator.execute(context)

    assert client.generate_calls[0]["text"] == embedding_query_text
    assert len(result_context.query_embedding.preferred_embedding.vector) == EMBEDDING_DIMENSIONS  # type: ignore[attr-defined]


# §14 No.10 例外系（user_context 欠落）
def test_execute_raises_when_user_context_missing() -> None:
    context = _sample_context(run_id="run-no-user-context")
    generator, _, _ = build_generator_with_registered_run(context)
    del context.user_context  # type: ignore[attr-defined]

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "user_context is required" in exc_info.value.message


# §14 No.11 例外系（embedding_query_text 空）
@pytest.mark.parametrize("empty_text", ["", "   ", "\n\t"])
def test_execute_raises_when_embedding_query_text_empty(empty_text: str) -> None:
    context = _sample_context(
        run_id=f"run-empty-text-{hash(empty_text)}",
        user_context=_sample_user_context(embedding_query_text=empty_text),
    )
    generator, _, _ = build_generator_with_registered_run(context)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "embedding_query_text" in exc_info.value.message


# §14 No.12 例外系（model version 欠落）
def test_execute_raises_when_model_versions_embedding_missing() -> None:
    context = _sample_context(run_id="run-no-model-version")
    del context.config_versions["model_versions.embedding"]
    generator, _, _ = build_generator_with_registered_run(context, register_run=False)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "model_versions.embedding" in exc_info.value.message


# §14 No.13 例外系（次元不一致）
def test_execute_raises_when_api_returns_wrong_dimensions() -> None:
    context = _sample_context(run_id="run-dim-mismatch")
    wrong_vector = _uniform_vector(0.1, dimensions=128)
    client = StubEmbeddingApiClient(
        response=EmbeddingGenerationResult(
            vector=wrong_vector,
            model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION_ID,
            dimensions=EMBEDDING_DIMENSIONS,
        ),
    )
    generator, _, _ = build_generator_with_registered_run(context, embedding_client=client)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "dimension mismatch" in exc_info.value.message


def test_execute_raises_when_api_reports_mismatched_dimensions_field() -> None:
    context = _sample_context(run_id="run-dimensions-field")
    client = StubEmbeddingApiClient(
        response=EmbeddingGenerationResult(
            vector=_uniform_vector(0.1),
            model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION_ID,
            dimensions=128,
        ),
    )
    generator, _, _ = build_generator_with_registered_run(context, embedding_client=client)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "dimensions mismatch" in exc_info.value.message


# §14 No.14 例外系（NaN / Inf）
@pytest.mark.parametrize(
    "bad_value",
    [float("nan"), float("inf"), float("-inf")],
)
def test_validate_embedding_vector_raises_for_non_finite_values(bad_value: float) -> None:
    vector = list(_uniform_vector(0.1))
    vector[0] = bad_value

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        validate_embedding_vector(vector)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "non-finite" in exc_info.value.message


def test_execute_raises_when_api_returns_non_finite_vector() -> None:
    context = _sample_context(run_id="run-non-finite")
    vector = list(_uniform_vector(0.1))
    vector[10] = float("nan")
    client = StubEmbeddingApiClient(
        response=EmbeddingGenerationResult(
            vector=tuple(vector),
            model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION_ID,
            dimensions=EMBEDDING_DIMENSIONS,
        ),
    )
    generator, _, _ = build_generator_with_registered_run(context, embedding_client=client)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.15 例外系（API 失敗）— unit 部分
def test_execute_raises_when_embedding_api_raises_unexpected_error() -> None:
    context = _sample_context(run_id="run-api-failure")
    client = StubEmbeddingApiClient(error=RuntimeError("upstream unavailable"))
    generator, _, _ = build_generator_with_registered_run(context, embedding_client=client)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert exc_info.value.detail_error_code is None
    assert "embedding API call failed" in exc_info.value.message


def test_execute_propagates_query_embedding_generation_error_from_api_client() -> None:
    context = _sample_context(run_id="run-api-detail")
    client = StubEmbeddingApiClient(
        error=QueryEmbeddingGenerationError(
            "embedding generation rejected",
            detail_error_code=DETAIL_ERROR_GENERATION_FAILED,
        ),
    )
    generator, _, _ = build_generator_with_registered_run(context, embedding_client=client)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert exc_info.value.detail_error_code == DETAIL_ERROR_GENERATION_FAILED


# §14 No.16 例外系（API タイムアウト）
def test_execute_raises_with_timeout_detail_when_embedding_api_times_out() -> None:
    context = _sample_context(run_id="run-api-timeout")
    client = StubEmbeddingApiClient(
        error=QueryEmbeddingGenerationError(
            "embedding API client timeout",
            detail_error_code=DETAIL_ERROR_TIMEOUT,
        ),
    )
    generator, _, _ = build_generator_with_registered_run(context, embedding_client=client)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert exc_info.value.detail_error_code == DETAIL_ERROR_TIMEOUT


def test_execute_propagates_rate_limit_detail_from_api_client() -> None:
    context = _sample_context(run_id="run-api-rate-limit")
    client = StubEmbeddingApiClient(
        error=QueryEmbeddingGenerationError(
            "embedding API rate limited",
            detail_error_code=DETAIL_ERROR_RATE_LIMIT,
        ),
    )
    generator, _, _ = build_generator_with_registered_run(context, embedding_client=client)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert exc_info.value.detail_error_code == DETAIL_ERROR_RATE_LIMIT


# §14 No.17 DB 非書込
def test_execute_does_not_mutate_run_validation_store() -> None:
    context = _sample_context(run_id="run-no-write")
    run_validation = InMemoryRunValidation()
    run_validation.register_run(context.run_id, DEFAULT_EMBEDDING_MODEL_VERSION_ID)
    runs_before = dict(run_validation.runs_by_id)
    generator = QueryEmbeddingGenerator(
        embedding_client=StubEmbeddingApiClient(
            response=EmbeddingGenerationResult(
                vector=_uniform_vector(0.2),
                model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION_ID,
                dimensions=EMBEDDING_DIMENSIONS,
            ),
        ),
        run_validation=run_validation,
        logger=ScaffoldRecoLogger(),
    )

    generator.execute(context)

    assert run_validation.runs_by_id == runs_before


# §14 No.19 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    embedding_query_text = "恋人への誕生日。実用的なギフト。"
    context = _sample_context(
        run_id="run-log",
        user_context=_sample_user_context(embedding_query_text=embedding_query_text),
    )
    logger = ScaffoldRecoLogger()
    generator, _, _ = build_generator_with_registered_run(context, logger=logger)

    result_context = generator.execute(context)

    completion_logs = [
        record
        for record in logger.records
        if record.event == "query_embedding_generation_completed"
    ]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == context.trace_id
    assert "model_version_id" in log_record.attributes
    assert "dimensions" in log_record.attributes
    assert "duration_ms" in log_record.attributes
    assert "source_text_hash" in log_record.attributes
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert embedding_query_text not in serialized
    vector_literal = str(result_context.query_embedding.preferred_embedding.vector)  # type: ignore[attr-defined]
    assert vector_literal not in serialized


def test_execute_sets_source_text_hash_from_embedding_query_text() -> None:
    embedding_query_text = "固定テキストで hash を検証する。"
    context = _sample_context(
        run_id="run-hash",
        user_context=_sample_user_context(embedding_query_text=embedding_query_text),
    )
    generator, _, _ = build_generator_with_registered_run(context)

    result_context = generator.execute(context)

    preferred = result_context.query_embedding.preferred_embedding  # type: ignore[attr-defined]
    expected_hash = hashlib.sha256(embedding_query_text.encode()).hexdigest()
    assert preferred.source_text_hash == expected_hash


def test_execute_raises_when_run_id_missing() -> None:
    context = _sample_context(run_id="run-missing-id")
    generator, _, _ = build_generator_with_registered_run(context)
    context.recommendation_run = None  # type: ignore[assignment]

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "run_id is required" in exc_info.value.message


def test_execute_raises_when_recommendation_run_not_registered() -> None:
    context = _sample_context(run_id="run-not-registered")
    generator, _, _ = build_generator_with_registered_run(context, register_run=False)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "recommendation_run not found" in exc_info.value.message


def test_execute_raises_when_run_model_version_differs_from_context() -> None:
    context = _sample_context(run_id="run-model-mismatch")
    run_validation = InMemoryRunValidation()
    run_validation.register_run(context.run_id, "emb-model-run-only")
    generator, _, _ = build_generator_with_registered_run(
        context,
        register_run=False,
    )
    generator.run_validation = run_validation

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "model_versions.embedding mismatch" in exc_info.value.message


def test_execute_raises_when_api_model_version_differs_from_config() -> None:
    context = _sample_context(run_id="run-api-model-mismatch")
    client = StubEmbeddingApiClient(
        response=EmbeddingGenerationResult(
            vector=_uniform_vector(0.1),
            model_version_id="emb-model-api-only",
            dimensions=EMBEDDING_DIMENSIONS,
        ),
    )
    generator, _, _ = build_generator_with_registered_run(context, embedding_client=client)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "model_version_id mismatch" in exc_info.value.message
