"""MOD-RECO-010 Query Embedding Generator smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import (
    EMBEDDING_DIMENSIONS,
    _sample_context,
    _sample_user_context,
    build_generator_with_registered_run,
)
from reco.application.query_embedding_generator import (
    SURFACE_ERROR_CODE,
    QueryEmbeddingGenerationError,
)


def test_execute_generates_preferred_embedding_on_execution_context() -> None:
    context = _sample_context(run_id="run-smoke-success")
    generator, client, _ = build_generator_with_registered_run(context)

    result_context = generator.execute(context)

    query_embedding = result_context.query_embedding  # type: ignore[attr-defined]
    preferred = query_embedding.preferred_embedding

    assert len(preferred.vector) == EMBEDDING_DIMENSIONS
    assert preferred.dimensions == EMBEDDING_DIMENSIONS
    assert preferred.model_version_id == context.config_versions["model_versions.embedding"]
    assert preferred.source_text_hash is not None
    assert not hasattr(query_embedding, "non_preferred_embedding")
    assert len(client.generate_calls) == 1
    assert client.generate_calls[0]["text"] == (
        context.user_context.preferred_context.embedding_query_text  # type: ignore[attr-defined]
    )
    assert "MOD-RECO-010" in result_context.completed_modules


def test_execute_passes_embedding_query_text_unchanged_to_api() -> None:
    embedding_query_text = "上司へのお礼。"
    context = _sample_context(
        run_id="run-smoke-text",
        user_context=_sample_user_context(embedding_query_text=embedding_query_text),
    )
    generator, client, _ = build_generator_with_registered_run(context)

    generator.execute(context)

    assert client.generate_calls[0]["text"] == embedding_query_text


def test_execute_calls_embedding_api_once_even_with_avoid_query_text() -> None:
    context = _sample_context(run_id="run-smoke-single-api")
    generator, client, _ = build_generator_with_registered_run(context)

    generator.execute(context)

    assert len(client.generate_calls) == 1


def test_execute_raises_when_user_context_missing() -> None:
    context = _sample_context(run_id="run-smoke-no-user-context")
    generator, _, _ = build_generator_with_registered_run(context)
    del context.user_context  # type: ignore[attr-defined]

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "user_context is required" in exc_info.value.message


def test_execute_raises_when_embedding_query_text_empty() -> None:
    context = _sample_context(
        run_id="run-smoke-empty-text",
        user_context=_sample_user_context(embedding_query_text="   "),
    )
    generator, _, _ = build_generator_with_registered_run(context)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "embedding_query_text" in exc_info.value.message


def test_execute_raises_when_model_versions_embedding_missing() -> None:
    context = _sample_context(run_id="run-smoke-no-model-version")
    del context.config_versions["model_versions.embedding"]
    generator, _, _ = build_generator_with_registered_run(context)

    with pytest.raises(QueryEmbeddingGenerationError) as exc_info:
        generator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "model_versions.embedding" in exc_info.value.message
